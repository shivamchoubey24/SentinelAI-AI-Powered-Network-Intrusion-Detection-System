"""Dashboard tests: login logic, API client, and page rendering (offline, no API needed)."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from src.dashboard import auth  # noqa: E402
from src.dashboard.api_client import ApiError, SentinelClient  # noqa: E402

APP = str(Path(__file__).parent.parent / "src" / "dashboard" / "app_simple.py")


# ---------------------------------------------------------------- auth logic
def test_password_check(monkeypatch):
    monkeypatch.setenv("DASHBOARD_PASSWORD", "hunter2")
    assert auth.check_password("hunter2")
    assert not auth.check_password("hunter3")
    assert not auth.check_password("")


def test_no_password_configured_fails_closed(monkeypatch):
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    assert not auth.is_configured()
    assert not auth.check_password("anything")


def test_backoff_grows_and_caps():
    assert [auth.backoff_seconds(n) for n in (0, 1, 2)] == [0, 0, 0]
    assert auth.backoff_seconds(3) == 2
    assert auth.backoff_seconds(4) == 4
    assert auth.backoff_seconds(50) == 30


# ---------------------------------------------------------------- API client
class _Resp:
    def __init__(self, status, body):
        self.status_code, self._body, self.text = status, body, str(body)

    def json(self):
        return self._body


def test_client_sends_api_key_and_parses(monkeypatch):
    seen = {}

    def fake(method, url, headers=None, timeout=None, **kw):
        seen.update(method=method, url=url, headers=headers)
        return _Resp(200, {"status": "ok"})

    monkeypatch.setattr("src.dashboard.api_client.requests.request", fake)
    out = SentinelClient("http://api:8000/", "k123").health()
    assert out == {"status": "ok"}
    assert seen["url"] == "http://api:8000/health" and seen["headers"] == {"X-API-Key": "k123"}


def test_client_raises_readable_errors(monkeypatch):
    monkeypatch.setattr("src.dashboard.api_client.requests.request",
                        lambda *a, **k: _Resp(403, {"detail": "Requires role 'analyst' or higher"}))
    with pytest.raises(ApiError) as e:
        SentinelClient("http://x", "k").predict("a.csv", b"a\n1\n")
    assert e.value.status == 403 and "analyst" in str(e.value)


# ------------------------------------------------------------ page rendering
FAKE = {
    "health": {"status": "ok", "database": "ok"},
    "status": {"system": "operational", "audit_chain": "valid", "model": "trained", "model_trained_at": "t"},
    "summary": {"detection_batches": 2, "records_analyzed": 300, "threats_detected": 120,
                "last_detection_at": "2026-01-01T00:00:00", "alerts_total": 2, "alerts_open": 2,
                "alerts_by_severity": {"critical": 1, "low": 1}},
    "threats": [{"timestamp": "t", "threat_type": "x", "severity": "low", "source_ip": "n/a", "status": "open"}],
    "metrics": {"status": "trained", "trained_at": "t", "dataset": "d.csv", "model_accuracy": 0.9,
                "precision": 0.9, "recall": 0.9, "f1_score": 0.9, "confusion_matrix": [[9, 1], [1, 9]]},
    "held_out_metrics": {"status": "not_evaluated", "message": "Run scripts/evaluate_model.py"},
    "audit_verify": {"valid": True, "length": 3, "head_hash": "ab" * 32, "checkpoints_checked": 1},
    "audit_blocks": [{"index": 2, "timestamp": "t", "event_type": "X", "hash": "cd" * 32, "previous_hash": "ef" * 32}],
}


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("DASHBOARD_PASSWORD", "pw")
    monkeypatch.delenv("DASHBOARD_AUTH_DISABLED", raising=False)
    for name, value in FAKE.items():
        monkeypatch.setattr(SentinelClient, name, lambda self, *a, _v=value, **k: _v)
    return AppTest.from_file(APP, default_timeout=30)


def _login(at):
    at.run()
    at.text_input[0].set_value("pw")
    at.button[0].click().run()
    return at


def test_login_required_and_wrong_password_rejected(app):
    app.run()
    assert not app.metric                      # nothing visible before login
    app.text_input[0].set_value("nope")
    app.button[0].click().run()
    assert app.error and not app.metric


def test_unconfigured_dashboard_shows_no_data(app, monkeypatch):
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    app.run()
    assert app.error and not app.metric


def test_overview_shows_api_numbers(app):
    at = _login(app)
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Records analyzed"] == "300" and metrics["Threats detected"] == "120"
    assert metrics["Audit chain"] == "VALID"


@pytest.mark.parametrize("page", ["Model Performance", "Audit Log", "Threat Detection"])
def test_other_pages_render(app, page):
    at = _login(app)
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception and not at.error


def test_api_key_rejection_is_explained(app, monkeypatch):
    def boom(self, *a, **k):
        raise ApiError("Invalid API key", 401)
    monkeypatch.setattr(SentinelClient, "summary", boom)
    at = _login(app)
    assert any("API key was rejected" in e.value for e in at.error)


def test_no_simulated_numbers_left_in_dashboard_source():
    src = Path(APP).read_text()
    assert "np.random" not in src and "random." not in src
    assert "1247" not in src


def test_model_performance_shows_held_out_prompt_when_missing(app, monkeypatch):
    monkeypatch.setattr(SentinelClient, "held_out_metrics",
                        lambda self: {"status": "not_evaluated", "message": "Run scripts/evaluate_model.py"})
    at = _login(app)
    at.sidebar.radio[0].set_value("Model Performance").run()
    assert not at.exception
    assert any("evaluate_model.py" in i.value for i in at.info)


def test_model_performance_shows_held_out_metrics_when_present(app, monkeypatch):
    ho = {
        "status": "evaluated", "note": "held-out note",
        "test_plus": {"accuracy": 0.78, "recall": 0.67, "false_positive_rate": 0.06},
        "test_21": {"accuracy": 0.59},
        "per_family_recall": {"dos": {"detection_rate": 0.85}, "probe": {"detection_rate": 0.82},
                              "r2l": {"detection_rate": 0.08}, "u2r": {"detection_rate": 0.10}},
        "attack_types": {"novel_not_in_training": {"records": 3752, "detection_rate": 0.43}},
    }
    monkeypatch.setattr(SentinelClient, "held_out_metrics", lambda self: ho)
    at = _login(app)
    at.sidebar.radio[0].set_value("Model Performance").run()
    assert not at.exception
    labels = {m.label: m.value for m in at.metric}
    assert labels["Accuracy (held-out)"] == "78.0%"
    assert labels["KDDTest-21 accuracy"] == "59.0%"
