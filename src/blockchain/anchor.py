"""
Optional public-chain anchoring of the audit log's head hash.

Why: the audit chain lives on one machine, so someone with write access to
the chain file, checkpoints.jsonl *and* anchors.jsonl could rewrite history.
An anchor is a zero-value transaction (sender -> itself) on an Ethereum
network whose data field carries (chain length, head hash). Once mined, it is
outside the control of whoever runs this server; verify_anchors() compares
what is on the public chain with the local log and reports any mismatch.

Configuration (all via environment; nothing is anchored unless set):
  ANCHOR_RPC_URL        JSON-RPC endpoint of a *testnet* (e.g. Sepolia via any provider)
  ANCHOR_PRIVATE_KEY    key of a funded testnet account (never logged)
  ANCHOR_ALLOW_MAINNET  must be "true" to anchor on chain id 1 (real money!)

Payload layout (45 bytes): b"SNTL1" | length (8 bytes, big endian) | head hash (32 bytes)

Limits, stated plainly: this proves the log's head existed no later than the
block that included the transaction, and that earlier entries were not
rewritten since. It says nothing about whether the entries were truthful when
written, and it needs a funded wallet + RPC provider you control.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

MAGIC = b"SNTL1"
MAINNET_CHAIN_ID = 1


class AnchorError(Exception):
    pass


def _redact(text: str) -> str:
    """Remove secrets (RPC URL often embeds a provider key; the private key) from messages."""
    for name in ("ANCHOR_RPC_URL", "ANCHOR_PRIVATE_KEY"):
        secret = os.environ.get(name)
        if secret:
            text = text.replace(secret, "[redacted]")
    return text


def is_configured() -> bool:
    return bool(os.environ.get("ANCHOR_RPC_URL") and os.environ.get("ANCHOR_PRIVATE_KEY"))


def encode_payload(length: int, head_hash: str) -> bytes:
    raw = bytes.fromhex(head_hash)
    if len(raw) != 32:
        raise AnchorError("head hash must be a 32-byte SHA-256 hex digest")
    return MAGIC + int(length).to_bytes(8, "big") + raw


def decode_payload(data: bytes) -> Dict[str, Any]:
    if len(data) != 45 or data[:5] != MAGIC:
        raise AnchorError("transaction data is not a SentinelAI anchor")
    return {"length": int.from_bytes(data[5:13], "big"), "head_hash": data[13:].hex()}


def _connect(w3=None):
    if w3 is not None:
        return w3
    if not os.environ.get("ANCHOR_RPC_URL"):
        raise AnchorError("ANCHOR_RPC_URL is not set")
    from web3 import Web3
    return Web3(Web3.HTTPProvider(os.environ["ANCHOR_RPC_URL"], request_kwargs={"timeout": 30}))


def _anchors_file(audit_logger) -> Path:
    return Path(audit_logger.chain_file).with_name("anchors.jsonl")


def read_anchors(audit_logger) -> List[Dict[str, Any]]:
    path = _anchors_file(audit_logger)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def anchor_head(audit_logger, w3=None, private_key: Optional[str] = None) -> Dict[str, Any]:
    """Checkpoint the audit chain and publish (length, head hash) on-chain."""
    key = private_key or os.environ.get("ANCHOR_PRIVATE_KEY")
    if not key:
        raise AnchorError("ANCHOR_PRIVATE_KEY is not set")
    w3 = _connect(w3)
    try:
        chain_id = int(w3.eth.chain_id)
        if chain_id == MAINNET_CHAIN_ID and os.environ.get("ANCHOR_ALLOW_MAINNET", "").lower() != "true":
            raise AnchorError("Refusing to anchor on Ethereum mainnet (real funds). Use a testnet, "
                              "or set ANCHOR_ALLOW_MAINNET=true if you really mean it.")

        cp = audit_logger.create_checkpoint()               # local checkpoint written at the same point
        payload = encode_payload(cp["length"], cp["head_hash"])

        account = w3.eth.account.from_key(key)
        priority = int(w3.eth.max_priority_fee)
        base_fee = int(w3.eth.get_block("latest")["baseFeePerGas"])
        tx = {
            "to": account.address, "value": 0, "data": payload,
            "nonce": w3.eth.get_transaction_count(account.address),
            "chainId": chain_id,
            "maxPriorityFeePerGas": priority, "maxFeePerGas": 2 * base_fee + priority,
        }
        tx["gas"] = int(w3.eth.estimate_gas({**tx, "from": account.address}))
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        if receipt["status"] != 1:
            raise AnchorError("Anchor transaction was mined but failed")
    except AnchorError:
        raise
    except Exception as e:  # network / RPC / funding problems: never leak the key
        raise AnchorError(_redact(f"Anchoring failed: {e.__class__.__name__}: {e}")) from None

    record = {
        "length": cp["length"], "head_hash": cp["head_hash"],
        "tx_hash": tx_hash.hex() if isinstance(tx_hash, (bytes, bytearray)) else str(tx_hash),
        "chain_id": chain_id, "block_number": int(receipt["blockNumber"]),
        "from": account.address, "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(_anchors_file(audit_logger), "a") as f:
        f.write(json.dumps(record) + "\n")
    logger.info(f"Anchored audit head (length {cp['length']}) in tx {record['tx_hash']}")
    return record


def verify_anchors(audit_logger, w3=None, tx_hashes: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Compare public-chain anchors with the local log.

    Uses anchors.jsonl, or pass `tx_hashes` you saved elsewhere (safer: an
    attacker who can edit local files can also delete anchors.jsonl).
    """
    w3 = _connect(w3)
    local = audit_logger.verify()  # also loads the chain into audit_logger.blockchain
    chain = audit_logger.blockchain.chain
    hashes = tx_hashes or [a["tx_hash"] for a in read_anchors(audit_logger)]
    results = []
    for h in hashes:
        item: Dict[str, Any] = {"tx_hash": h}
        try:
            tx = w3.eth.get_transaction(h)
            data = tx["input"]
            data = bytes(data) if not isinstance(data, str) else bytes.fromhex(data[2:] if data.startswith("0x") else data)
            onchain = decode_payload(data)
            n = onchain["length"]
            item.update(length=n, onchain_head_hash=onchain["head_hash"])
            if len(chain) < n:
                item.update(ok=False, reason="local chain is shorter than the anchored length (truncated)")
            elif chain[n - 1].hash != onchain["head_hash"]:
                item.update(ok=False, reason="local block does not match the anchored hash (rewritten)")
            else:
                item["ok"] = True
        except Exception as e:
            item.update(ok=False, reason=_redact(f"{e.__class__.__name__}: {e}"))
        results.append(item)
    return {
        "anchors_checked": len(results),
        "local_chain_valid": bool(local["valid"]),
        "local_chain_error": local.get("error"),
        # every anchor must match AND the local chain must be internally consistent
        "all_ok": bool(results) and all(r["ok"] for r in results) and bool(local["valid"]),
        "results": results,
    }
