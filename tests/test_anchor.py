"""On-chain anchoring, tested against web3's in-memory Ethereum test chain (no network)."""
import pytest

web3 = pytest.importorskip("web3")
pytest.importorskip("eth_tester")

from web3 import EthereumTesterProvider, Web3  # noqa: E402

from src.blockchain import anchor  # noqa: E402
from src.blockchain.blockchain_logger import BlockchainLogger  # noqa: E402


@pytest.fixture
def w3():
    return Web3(EthereumTesterProvider())


@pytest.fixture
def key(w3):
    return "0x" + w3.provider.ethereum_tester.backend.account_keys[0].to_hex()[2:]


@pytest.fixture
def audit(tmp_path):
    a = BlockchainLogger(config={}, chain_file=str(tmp_path / "chain.json"))
    for i in range(3):
        a.log_system_event({"event": f"e{i}"})
    return a


def test_payload_roundtrip():
    h = "ab" * 32
    assert anchor.decode_payload(anchor.encode_payload(7, h)) == {"length": 7, "head_hash": h}
    with pytest.raises(anchor.AnchorError):
        anchor.decode_payload(b"junk")


def test_anchor_then_verify_ok(audit, w3, key):
    rec = anchor.anchor_head(audit, w3=w3, private_key=key)
    assert rec["length"] == len(audit.blockchain.chain) and rec["block_number"] >= 1
    out = anchor.verify_anchors(audit, w3=w3)
    assert out["all_ok"] and out["anchors_checked"] == 1
    # appending more blocks later is fine: the anchored prefix is still intact
    audit.log_system_event({"event": "later"})
    assert anchor.verify_anchors(audit, w3=w3)["all_ok"]


def _rewrite_history(tmp_path, recompute_hashes: bool):
    """Simulate an attacker editing block 1 in the chain file."""
    from src.blockchain.blockchain_logger import Blockchain
    path = tmp_path / "chain.json"
    bc = Blockchain(difficulty=2)
    bc.load_chain(str(path))
    bc.chain[1].data["event"] = "tampered"
    if recompute_hashes:                                   # a careful attacker fixes every later link
        for i in range(1, len(bc.chain)):
            bc.chain[i].previous_hash = bc.chain[i - 1].hash
            bc.chain[i].nonce = 0
            bc.chain[i].hash = bc.chain[i].calculate_hash()
            bc.chain[i].mine_block(2)
    bc.save_chain(str(path))
    return path


def test_plain_edit_caught_by_local_validity(audit, w3, key, tmp_path):
    anchor.anchor_head(audit, w3=w3, private_key=key)
    path = _rewrite_history(tmp_path, recompute_hashes=False)
    out = anchor.verify_anchors(BlockchainLogger(config={}, chain_file=str(path)), w3=w3)
    assert not out["local_chain_valid"] and not out["all_ok"]


def test_fully_recomputed_rewrite_caught_by_onchain_anchor(audit, w3, key, tmp_path):
    anchor.anchor_head(audit, w3=w3, private_key=key)
    path = _rewrite_history(tmp_path, recompute_hashes=True)
    (tmp_path / "checkpoints.jsonl").unlink()              # attacker also wipes local checkpoints
    fresh = BlockchainLogger(config={}, chain_file=str(path))
    assert fresh.verify()["valid"]                          # local checks alone are now fooled...
    out = anchor.verify_anchors(fresh, w3=w3)
    assert out["local_chain_valid"] and not out["all_ok"]   # ...the public chain is not
    assert "rewritten" in out["results"][0]["reason"]


def test_truncation_caught_using_saved_tx_hash(audit, w3, key, tmp_path):
    from src.blockchain.blockchain_logger import Blockchain
    rec = anchor.anchor_head(audit, w3=w3, private_key=key)
    path = tmp_path / "chain.json"
    bc = Blockchain(difficulty=2)
    bc.load_chain(str(path))
    bc.chain = bc.chain[:2]
    bc.save_chain(str(path))
    for name in ("anchors.jsonl", "checkpoints.jsonl"):     # attacker deletes local evidence
        (tmp_path / name).unlink()
    fresh = BlockchainLogger(config={}, chain_file=str(path))
    out = anchor.verify_anchors(fresh, w3=w3, tx_hashes=[rec["tx_hash"]])
    assert not out["all_ok"] and "truncated" in out["results"][0]["reason"]


def test_non_anchor_transaction_is_not_accepted(audit, w3, key):
    acct = w3.eth.account.from_key(key)
    tx_hash = w3.eth.send_transaction({"from": w3.eth.accounts[0], "to": acct.address, "value": 1})
    out = anchor.verify_anchors(audit, w3=w3, tx_hashes=[tx_hash.hex()])
    assert not out["all_ok"] and "not a SentinelAI anchor" in out["results"][0]["reason"]


def test_mainnet_refused_by_default(audit, w3, key, monkeypatch):
    monkeypatch.delenv("ANCHOR_ALLOW_MAINNET", raising=False)

    class Fake:
        class eth:
            chain_id = 1
    with pytest.raises(anchor.AnchorError, match="mainnet"):
        anchor.anchor_head(audit, w3=Fake(), private_key=key)


def test_not_configured_by_default(monkeypatch):
    monkeypatch.delenv("ANCHOR_RPC_URL", raising=False)
    monkeypatch.delenv("ANCHOR_PRIVATE_KEY", raising=False)
    assert not anchor.is_configured()


# ------------------------------------------------------------------ API layer
KEYS = "v:viewerkey:viewer,r:adminkey:admin"


@pytest.fixture
def api_client(tmp_path, monkeypatch, w3, key):
    from fastapi.testclient import TestClient

    import src.api.main as api
    from src.db import reset_engine
    from src.security.rate_limit import RateLimiter
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("SENTINEL_API_KEYS", KEYS)
    monkeypatch.setenv("AUDIT_CHAIN_FILE", str(tmp_path / "chain.json"))
    monkeypatch.delenv("SENTINEL_AUTH_DISABLED", raising=False)
    monkeypatch.setattr(api, "limiter", RateLimiter(limit=1000))
    reset_engine()
    with TestClient(api.app) as c:
        yield c, monkeypatch, w3, key
    reset_engine()


def test_api_anchor_not_configured_is_501(api_client):
    c, mp, _, _ = api_client
    mp.delenv("ANCHOR_RPC_URL", raising=False)
    mp.delenv("ANCHOR_PRIVATE_KEY", raising=False)
    assert c.post("/api/v1/audit/anchor", headers={"X-API-Key": "adminkey"}).status_code == 501


def test_api_anchor_requires_admin(api_client):
    c, *_ = api_client
    assert c.post("/api/v1/audit/anchor", headers={"X-API-Key": "viewerkey"}).status_code == 403
    assert c.post("/api/v1/audit/anchor").status_code == 401


def test_api_anchor_and_verify_flow(api_client):
    c, mp, w3, key = api_client
    mp.setenv("ANCHOR_RPC_URL", "http://unused.invalid")
    mp.setenv("ANCHOR_PRIVATE_KEY", key)
    mp.setattr(anchor, "_connect", lambda w3_=None: w3)
    r = c.post("/api/v1/audit/anchor", headers={"X-API-Key": "adminkey"})
    assert r.status_code == 200 and r.json()["tx_hash"]
    out = c.get("/api/v1/audit/anchors?verify=true", headers={"X-API-Key": "viewerkey"}).json()
    assert out["verified"]["all_ok"] and len(out["anchors"]) == 1
    assert c.get("/api/v1/audit/anchors", headers={"X-API-Key": "viewerkey"}).json()["verified"] is None


def test_errors_never_leak_rpc_url_or_key(monkeypatch):
    monkeypatch.setenv("ANCHOR_RPC_URL", "https://rpc.example/v3/SECRETPROJECTKEY")
    monkeypatch.setenv("ANCHOR_PRIVATE_KEY", "0xdeadbeef")
    msg = anchor._redact("boom at https://rpc.example/v3/SECRETPROJECTKEY using 0xdeadbeef")
    assert "SECRETPROJECTKEY" not in msg and "deadbeef" not in msg


def test_checkpoint_of_never_saved_chain_stays_valid(tmp_path):
    """Regression: genesis used to be regenerated (new hash) on every load until a block was appended."""
    a = BlockchainLogger(config={}, chain_file=str(tmp_path / "fresh.json"))
    a.create_checkpoint()
    v = BlockchainLogger(config={}, chain_file=str(tmp_path / "fresh.json")).verify()
    assert v["valid"] and v["checkpoints_checked"] == 1
