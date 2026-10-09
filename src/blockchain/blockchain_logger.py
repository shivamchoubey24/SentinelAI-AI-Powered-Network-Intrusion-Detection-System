"""
Tamper-evident audit log (hash chain).

WHAT THIS IS: an append-only, SHA-256 hash-linked log. Each entry commits to
the previous entry's hash, so editing or deleting an entry in the middle of
the file is detectable by `verify()`.

WHAT THIS IS NOT: a distributed blockchain. It runs on a single node, has no
consensus and no peers. Someone with write access to the whole chain file can
rewrite *every* block consistently and verification alone will not notice.
To narrow that gap we write periodic *checkpoints* (chain length + head hash)
to a separate file, which `verify()` cross-checks. For stronger guarantees,
copy checkpoints to somewhere the log writer cannot modify (write-once
storage, a remote syslog, or - as a future step - a public testnet
transaction). Class names (Blockchain, Block) are kept for backwards
compatibility with Phase 1.

The `nonce`/`mine_block` proof-of-work is kept only for compatibility; on a
single node it provides no security, so it is not enforced during verification.
"""

import hashlib
import json
import logging
import os
import pickle
import sys
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.config_loader import ConfigLoader  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402

try:  # POSIX file locking so several API workers do not corrupt the chain
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None

logger = setup_logger(__name__)

DEFAULT_CHAIN_FILE = "data/blockchain/security_chain.json"
LEGACY_PICKLE_FILE = "data/blockchain/security_chain.pkl"
CHECKPOINT_EVERY = 25  # blocks

_thread_lock = threading.Lock()


class Block:
    """A single entry in the hash chain."""

    def __init__(self, index: int, timestamp: str, data: Dict, previous_hash: str, nonce: int = 0,
                 hash: Optional[str] = None):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = hash if hash is not None else self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }, sort_keys=True, default=str)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty: int = 2) -> None:
        """Legacy proof-of-work (not security-relevant on a single node)."""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self) -> Dict:
        return {
            "index": self.index, "timestamp": self.timestamp, "data": self.data,
            "previous_hash": self.previous_hash, "nonce": self.nonce, "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Block":
        return cls(d["index"], d["timestamp"], d["data"], d["previous_hash"], d.get("nonce", 0), d["hash"])


class _LegacyUnpickler(pickle.Unpickler):
    """Only allows unpickling Phase 1 Block objects (one-time migration)."""

    def find_class(self, module, name):
        if name == "Block" and module.endswith("blockchain_logger"):
            return _LegacyBlock
        raise pickle.UnpicklingError(f"Refusing to unpickle {module}.{name}")


class _LegacyBlock:
    """Plain attribute bag that receives the pickled Phase 1 Block state."""


class Blockchain:
    """Append-only hash-chained log."""

    def __init__(self, difficulty: int = 2):
        self.chain: List[Block] = []
        self.difficulty = difficulty
        self.create_genesis_block()

    def create_genesis_block(self) -> None:
        genesis = Block(0, datetime.now(timezone.utc).isoformat(), {"message": "Genesis Block"}, "0")
        genesis.mine_block(self.difficulty)
        self.chain.append(genesis)

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_block(self, data: Dict) -> Block:
        block = Block(len(self.chain), datetime.now(timezone.utc).isoformat(), data,
                      self.get_latest_block().hash)
        block.mine_block(self.difficulty)
        self.chain.append(block)
        return block

    def verify(self) -> Dict[str, Any]:
        """Full verification. Returns {'valid', 'length', 'head_hash', 'error', 'bad_index'}."""
        result = {"valid": True, "length": len(self.chain),
                  "head_hash": self.chain[-1].hash if self.chain else None,
                  "error": None, "bad_index": None}

        def fail(idx: int, msg: str) -> Dict[str, Any]:
            result.update(valid=False, error=msg, bad_index=idx)
            return result

        if not self.chain:
            return fail(0, "chain is empty")
        if self.chain[0].previous_hash != "0" or self.chain[0].index != 0:
            return fail(0, "invalid genesis block")
        for i, block in enumerate(self.chain):
            if block.index != i:
                return fail(i, "block index out of sequence")
            if block.hash != block.calculate_hash():
                return fail(i, "block contents do not match stored hash")
            if i > 0 and block.previous_hash != self.chain[i - 1].hash:
                return fail(i, "previous_hash link broken")
        return result

    def is_chain_valid(self) -> bool:
        return self.verify()["valid"]

    def get_chain(self) -> List[Dict]:
        return [b.to_dict() for b in self.chain]

    # -- persistence (JSON, atomic write) ------------------------------------
    def save_chain(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        tmp = f"{filepath}.tmp"
        with open(tmp, "w") as f:
            json.dump(self.get_chain(), f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, filepath)

    def load_chain(self, filepath: str) -> bool:
        """Load chain from JSON. Migrates a Phase 1 pickle file on first use."""
        try:
            if os.path.exists(filepath):
                with open(filepath) as f:
                    self.chain = [Block.from_dict(d) for d in json.load(f)]
                return True
            legacy = str(Path(filepath).with_name(Path(LEGACY_PICKLE_FILE).name))
            if filepath == DEFAULT_CHAIN_FILE and os.path.exists(legacy):
                with open(legacy, "rb") as f:
                    legacy_blocks = _LegacyUnpickler(f).load()
                self.chain = [Block(b.index, b.timestamp, b.data, b.previous_hash,
                                    getattr(b, "nonce", 0), b.hash) for b in legacy_blocks]
                self.save_chain(filepath)
                logger.warning(f"Migrated legacy pickle chain ({len(self.chain)} blocks) to {filepath}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading chain from {filepath}: {e}")
            raise


@contextmanager
def _exclusive_lock(path: str) -> Iterator[None]:
    """Thread + cross-process lock around read-modify-write of the chain file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with _thread_lock:
        fh = open(path + ".lock", "a+")
        try:
            if fcntl:
                fcntl.flock(fh, fcntl.LOCK_EX)
            yield
        finally:
            if fcntl:
                fcntl.flock(fh, fcntl.LOCK_UN)
            fh.close()


class BlockchainLogger:
    """High-level interface for appending security events to the audit log."""

    def __init__(self, config: Optional[Dict] = None, chain_file: Optional[str] = None):
        if config is None:
            config = ConfigLoader.load_config()
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.chain_file = chain_file or os.environ.get("AUDIT_CHAIN_FILE", DEFAULT_CHAIN_FILE)
        self.checkpoint_file = str(Path(self.chain_file).with_name("checkpoints.jsonl"))
        self.blockchain = Blockchain(difficulty=2)
        self.blockchain.load_chain(self.chain_file)

    # -- internal -----------------------------------------------------------
    def _append(self, event_type: str, payload: Dict) -> Dict:
        """Reload latest chain under a lock, append, persist. Returns the block dict."""
        entry = {"type": event_type, "timestamp": datetime.now(timezone.utc).isoformat(), **payload}
        with _exclusive_lock(self.chain_file):
            self.blockchain = Blockchain(difficulty=2)
            self.blockchain.load_chain(self.chain_file)
            block = self.blockchain.add_block(entry)
            self.blockchain.save_chain(self.chain_file)
            if block.index % CHECKPOINT_EVERY == 0:
                self._write_checkpoint()
        return block.to_dict()

    def _safe_append(self, event_type: str, payload: Dict) -> Dict:
        try:
            block = self._append(event_type, payload)
            self.logger.info(f"{event_type} logged to block #{block['index']}")
            return block
        except Exception as e:
            self.logger.error(f"Error logging {event_type}: {e}")
            return {}

    def _write_checkpoint(self) -> Dict:
        head = self.blockchain.get_latest_block()
        cp = {"length": len(self.blockchain.chain), "head_hash": head.hash,
              "created_at": datetime.now(timezone.utc).isoformat()}
        with open(self.checkpoint_file, "a") as f:
            f.write(json.dumps(cp) + "\n")
        return cp

    # -- public logging API (unchanged signatures) --------------------------
    def log_etl_operation(self, operation_data: Dict) -> Dict:
        return self._safe_append("ETL_OPERATION", operation_data)

    def log_threat_detection(self, threat_data: Dict) -> Dict:
        return self._safe_append("THREAT_DETECTION", threat_data)

    def log_model_update(self, model_data: Dict) -> Dict:
        return self._safe_append("MODEL_UPDATE", model_data)

    def log_system_event(self, event_data: Dict) -> Dict:
        return self._safe_append("SYSTEM_EVENT", event_data)

    def create_checkpoint(self) -> Dict:
        """Record (length, head hash). Store copies of this file somewhere the log writer cannot edit."""
        with _exclusive_lock(self.chain_file):
            self.blockchain = Blockchain(difficulty=2)
            self.blockchain.load_chain(self.chain_file)
            if not os.path.exists(self.chain_file):
                # A fresh chain gets a new (timestamped) genesis block on every load, so it
                # must be persisted first or the checkpointed hash could never match again.
                self.blockchain.save_chain(self.chain_file)
            return self._write_checkpoint()

    # -- verification -------------------------------------------------------
    def verify(self) -> Dict[str, Any]:
        """Verify chain integrity and cross-check it against saved checkpoints."""
        try:
            self.blockchain = Blockchain(difficulty=2)
            self.blockchain.load_chain(self.chain_file)
            result = self.blockchain.verify()
            result["checkpoints_checked"] = 0
            if result["valid"] and os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file) as f:
                    for line in f:
                        if not line.strip():
                            continue
                        cp = json.loads(line)
                        result["checkpoints_checked"] += 1
                        n = cp["length"]
                        if len(self.blockchain.chain) < n or self.blockchain.chain[n - 1].hash != cp["head_hash"]:
                            result.update(valid=False, bad_index=n - 1,
                                          error="chain does not match a saved checkpoint (truncated or rewritten)")
                            break
            result["scope"] = "single-node hash chain; not a distributed ledger"
            return result
        except Exception as e:
            self.logger.error(f"Error verifying chain: {e}")
            return {"valid": False, "error": str(e), "length": 0, "head_hash": None,
                    "bad_index": None, "checkpoints_checked": 0,
                    "scope": "single-node hash chain; not a distributed ledger"}

    def verify_integrity(self) -> bool:
        return bool(self.verify()["valid"])

    # -- reading ------------------------------------------------------------
    def get_audit_trail(self, start_date: Optional[str] = None, end_date: Optional[str] = None,
                        event_type: Optional[str] = None) -> List[Dict]:
        try:
            self.blockchain = Blockchain(difficulty=2)
            self.blockchain.load_chain(self.chain_file)
            out = []
            for block in self.blockchain.get_chain()[1:]:
                data = block["data"]
                if event_type and data.get("type") != event_type:
                    continue
                ts = data.get("timestamp", "")
                if start_date and ts < start_date:
                    continue
                if end_date and ts > end_date:
                    continue
                out.append(block)
            return out
        except Exception as e:
            self.logger.error(f"Error retrieving audit trail: {e}")
            return []

    def export_audit_report(self, output_path: str, start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> bool:
        try:
            v = self.verify()
            report = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_blocks": v["length"], "integrity_verified": v["valid"],
                "head_hash": v["head_hash"], "start_date": start_date, "end_date": end_date,
                "audit_logs": self.get_audit_trail(start_date, end_date),
            }
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Error exporting audit report: {e}")
            return False


def main():
    """Smoke test."""
    bc = BlockchainLogger()
    bc.log_system_event({"event_type": "SELF_TEST"})
    print(json.dumps(bc.verify(), indent=2))


if __name__ == "__main__":
    main()
