"""Phase 2 tests: persistence, audit chain, API security. No TensorFlow required."""
import io
import json

import pytest
from fastapi.testclient import TestClient

KEYS = "viewer1:viewerkey:viewer,analyst1:analystkey:analyst,admin1:adminkey:admin"


class FakeScaler:
    n_features_in_ = 3


class FakeModel:
    scaler = FakeScaler()

    def predict(self, X):
        probs = (X[:, :1] > 0.5).astype(float)          # first column drives the "attack" score
        return probs.flatten().astype(int), probs


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("SENTINEL_API_KEYS", KEYS)
    monkeypatch.delenv("SENTINEL_AUTH_DISABLED", raising=False)
    monkeypatch.setenv("AUDIT_CHAIN_FILE", str(tmp_path / "chain" / "chain.json"))
    from src.db import reset_engine
    reset_engine()
    yield tmp_path
    reset_engine()


@pytest.fixture
def client(env, monkeypatch):
    import src.api.main as api
    from src.security.rate_limit import RateLimiter
    monkeypatch.setattr(api, "limiter", RateLimiter(limit=1000))
    monkeypatch.setattr(api, "_load_latest_model",
                        lambda: (FakeModel(), {"model_path": "fake", "trained_at": "t"}))
    with TestClient(api.app) as c:
        yield c


def H(key):
    return {"X-API-Key": key}


def csv_bytes(rows, header="a,b,c"):
    return io.BytesIO((header + "\n" + "\n".join(rows) + "\n").encode())


# ------------------------------------------------------------- persistence
def test_save_dataframe_roundtrip(env):
    import pandas as pd
    from src.db import get_session, repository
    from src.db.models import SecurityLog
    n = repository.save_dataframe(pd.DataFrame({"x": [1, 2], "y": [0.5, float("nan")]}), "unit")
    assert n == 2
    with get_session() as s:
        assert s.query(SecurityLog).count() == 2


def test_model_run_persisted(env):
    from src.db import repository
    info = {"model_path": "p", "dataset": "d", "confusion_matrix": [[1, 0], [0, 1]],
            "metrics": {"accuracy": .9, "precision": .8, "recall": .7, "f1_score": .75}}
    repository.record_model_run(info)
    assert repository.latest_model_run()["metrics"]["accuracy"] == .9


def test_etl_loader_uses_database(env):
    import pandas as pd
    from src.etl.pipeline import DataLoader
    assert DataLoader({}).save_to_database(pd.DataFrame({"a": [1]}), "security_logs") is True


# ------------------------------------------------------------- audit chain
def test_audit_chain_detects_tampering(env):
    from src.blockchain.blockchain_logger import BlockchainLogger
    bc = BlockchainLogger()
    for i in range(3):
        bc.log_system_event({"event_type": f"e{i}"})
    assert bc.verify()["valid"]
    path = bc.chain_file
    chain = json.load(open(path))
    chain[2]["data"]["event_type"] = "tampered"
    json.dump(chain, open(path, "w"))
    result = BlockchainLogger().verify()
    assert not result["valid"] and result["bad_index"] == 2


def test_checkpoint_detects_truncation(env):
    from src.blockchain.blockchain_logger import BlockchainLogger
    bc = BlockchainLogger()
    for i in range(3):
        bc.log_system_event({"event_type": f"e{i}"})
    bc.create_checkpoint()
    chain = json.load(open(bc.chain_file))
    json.dump(chain[:2], open(bc.chain_file, "w"))      # drop the newest blocks
    result = BlockchainLogger().verify()
    assert not result["valid"] and "checkpoint" in result["error"]


# ------------------------------------------------------------- API security
def test_health_is_public(client):
    assert client.get("/health").json()["database"] == "ok"


def test_missing_and_invalid_key_rejected(client):
    assert client.get("/api/v1/status").status_code == 401
    assert client.get("/api/v1/status", headers=H("nope")).status_code == 401


def test_fail_closed_without_configured_keys(client, monkeypatch):
    monkeypatch.delenv("SENTINEL_API_KEYS")
    assert client.get("/api/v1/status", headers=H("viewerkey")).status_code == 503


def test_role_enforcement(client):
    f = {"file": ("d.csv", csv_bytes(["1,2,3"]), "text/csv")}
    assert client.post("/api/v1/predict", files=f, headers=H("viewerkey")).status_code == 403
    assert client.post("/api/v1/audit/checkpoint", headers=H("analystkey")).status_code == 403
    assert client.post("/api/v1/audit/checkpoint", headers=H("adminkey")).status_code == 200


def test_predict_persists_alert_and_audit(client):
    f = {"file": ("d.csv", csv_bytes(["1,2,3", "0,2,3", "0.9,1,1"]), "text/csv")}
    r = client.post("/api/v1/predict", files=f, headers=H("analystkey"))
    assert r.status_code == 200
    body = r.json()
    assert body["records_analyzed"] == 3 and body["threats_detected"] == 2
    alerts = client.get("/api/v1/threats", headers=H("viewerkey")).json()
    assert len(alerts) == 1 and alerts[0]["threat_type"] == "batch_intrusion_detected"
    assert client.get("/api/v1/audit/verify", headers=H("viewerkey")).json()["valid"]


@pytest.mark.parametrize("content,status", [
    (["1,2"], 422),                 # wrong feature count
    (["1,2,x"], 422),               # non numeric
    (["1,2,inf"], 422),             # non finite
])
def test_predict_input_validation(client, content, status):
    header = "a,b" if content == ["1,2"] else "a,b,c"
    f = {"file": ("d.csv", csv_bytes(content, header), "text/csv")}
    assert client.post("/api/v1/predict", files=f, headers=H("analystkey")).status_code == status


def test_predict_rejects_non_csv_and_oversize(client, monkeypatch):
    import src.api.main as api
    f = {"file": ("d.txt", csv_bytes(["1,2,3"]), "text/plain")}
    assert client.post("/api/v1/predict", files=f, headers=H("analystkey")).status_code == 415
    monkeypatch.setattr(api, "MAX_UPLOAD_BYTES", 10)
    f = {"file": ("d.csv", csv_bytes(["1,2,3"] * 10), "text/csv")}
    assert client.post("/api/v1/predict", files=f, headers=H("analystkey")).status_code == 413


def test_query_limit_validated(client):
    assert client.get("/api/v1/threats?limit=0", headers=H("viewerkey")).status_code == 422
    assert client.get("/api/v1/threats?limit=1000", headers=H("viewerkey")).status_code == 422


def test_rate_limit(client, monkeypatch):
    import src.api.main as api
    from src.security.rate_limit import RateLimiter
    monkeypatch.setattr(api, "limiter", RateLimiter(limit=2))
    codes = [client.get("/api/v1/status", headers=H("viewerkey")).status_code for _ in range(4)]
    assert codes[:2] == [200, 200] and codes[2:] == [429, 429]


def test_cors_not_wildcard_and_no_credentials(client):
    r = client.options("/api/v1/status", headers={"Origin": "https://evil.example",
                                                  "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") != "*"
    assert "access-control-allow-origin" not in r.headers


def test_metrics_endpoint_requires_key_and_exposes_counters(client):
    assert client.get("/metrics").status_code == 401
    body = client.get("/metrics", headers=H("viewerkey")).text
    assert "sentinel_http_requests_total" in body


# ------------------------------------------------------- dashboard endpoints
def test_summary_reflects_real_detections(client):
    empty = client.get("/api/v1/summary", headers=H("viewerkey")).json()
    assert empty["records_analyzed"] == 0 and empty["alerts_total"] == 0
    assert empty["last_detection_at"] is None

    rows = ["0.9,1,1", "0.1,1,1", "0.8,2,2"]
    r = client.post("/api/v1/predict", headers=H("analystkey"),
                    files={"file": ("x.csv", csv_bytes(rows), "text/csv")})
    assert r.status_code == 200
    s = client.get("/api/v1/summary", headers=H("viewerkey")).json()
    assert s["records_analyzed"] == 3 and s["threats_detected"] == 2
    assert s["alerts_total"] == 1 and s["alerts_open"] == 1
    assert sum(s["alerts_by_severity"].values()) == 1
    assert s["last_detection_at"]


def test_summary_and_blocks_require_auth(client):
    assert client.get("/api/v1/summary").status_code == 401
    assert client.get("/api/v1/audit/blocks").status_code == 401


def test_audit_blocks_newest_first_and_bounded(client):
    client.post("/api/v1/predict", headers=H("analystkey"),
                files={"file": ("x.csv", csv_bytes(["0.9,1,1"]), "text/csv")})
    blocks = client.get("/api/v1/audit/blocks?limit=5", headers=H("viewerkey")).json()
    assert blocks[0]["index"] > blocks[-1]["index"] or len(blocks) == 1
    assert blocks[0]["event_type"] == "THREAT_DETECTION"
    assert client.get("/api/v1/audit/blocks?limit=0", headers=H("viewerkey")).status_code == 422


def test_held_out_metrics_not_evaluated_by_default(client):
    r = client.get("/api/v1/metrics/held-out", headers=H("viewerkey"))
    assert r.status_code == 200 and r.json()["status"] == "not_evaluated"


def test_held_out_metrics_returned_when_present(client, tmp_path):
    import json
    from pathlib import Path
    Path("data/models").mkdir(parents=True, exist_ok=True)
    Path("data/models/latest_eval.json").write_text(json.dumps({"test_plus": {"accuracy": 0.78}}))
    r = client.get("/api/v1/metrics/held-out", headers=H("viewerkey"))
    assert r.status_code == 200 and r.json()["status"] == "evaluated"
    assert r.json()["test_plus"]["accuracy"] == 0.78


def test_held_out_metrics_requires_auth(client):
    assert client.get("/api/v1/metrics/held-out").status_code == 401
