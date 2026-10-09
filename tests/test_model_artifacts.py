"""Model artifact safety tests (need TensorFlow; skipped when it is absent)."""

import json

import numpy as np
import pytest

pytest.importorskip("tensorflow")

from src.models.threat_detector import MLPGRUModel  # noqa: E402


@pytest.fixture()
def trained(tmp_path):
    w = MLPGRUModel({"model": {"hidden_layers": [8], "gru_units": 4}})
    X = np.random.RandomState(0).rand(60, 5)
    y = (X[:, 0] > 0.5).astype(int)
    w.scaler.fit(X)
    w.build_model(5)
    w.model.fit(w.scaler.transform(X), y, epochs=1, verbose=0)
    prefix = str(tmp_path / "m")
    w.save_model(prefix)
    return w, prefix, X


def test_roundtrip_json_no_pickle(trained):
    w, prefix, X = trained
    import os
    assert os.path.exists(prefix + "_preproc.json")
    assert not os.path.exists(prefix + "_scaler.pkl")
    w2 = MLPGRUModel({})
    w2.load_model(prefix)
    assert w2.scaler.n_features_in_ == 5
    assert np.allclose(w.scaler.transform(X), w2.scaler.transform(X))
    assert (w.predict(X)[0] == w2.predict(X)[0]).all()


def test_tampered_model_rejected(trained):
    _, prefix, _ = trained
    with open(prefix + "_model.h5", "ab") as f:
        f.write(b"tamper")
    with pytest.raises(ValueError, match="hash mismatch"):
        MLPGRUModel({}).load_model(prefix)


def test_legacy_pickle_refused_by_default(trained, monkeypatch):
    import os
    import pickle
    _, prefix, _ = trained
    os.remove(prefix + "_preproc.json")
    for suffix in ("_scaler.pkl", "_encoder.pkl"):
        with open(prefix + suffix, "wb") as f:
            pickle.dump({}, f)
    monkeypatch.delenv("SENTINEL_ALLOW_LEGACY_PICKLE", raising=False)
    with pytest.raises(RuntimeError, match="legacy pickle"):
        MLPGRUModel({}).load_model(prefix)


# ------------------------------------------------------------- monitoring
def _monitor_setup(trained, tmp_path, monkeypatch, baseline_acc):
    import pandas as pd
    w, prefix, X = trained
    y = (X[:, 0] > 0.5).astype(int)
    csv = tmp_path / "eval.csv"
    df = pd.DataFrame(X, columns=list("abcde"))
    df["label"] = y
    df.to_csv(csv, index=False)
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps({"model_path": prefix,
                                  "metrics": {"accuracy": baseline_acc, "f1_score": baseline_acc}}))
    monkeypatch.setenv("AUDIT_CHAIN_FILE", str(tmp_path / "chain.json"))
    from src.mlops.auto_retrainer import AutoRetrainer
    return AutoRetrainer(), str(csv), str(latest)


def test_monitoring_evaluates_real_model(trained, tmp_path, monkeypatch):
    rt, csv, latest = _monitor_setup(trained, tmp_path, monkeypatch, baseline_acc=0.0)
    r = rt.run_monitoring_cycle(csv, latest)
    assert r["monitoring_completed"] and r["samples_evaluated"] == 60
    assert 0.0 <= r["current_metrics"]["accuracy"] <= 1.0
    assert r["performance_drift"] is False          # baseline 0.0 can't be beaten by degradation


def test_monitoring_flags_drift_when_baseline_was_much_higher(trained, tmp_path, monkeypatch):
    rt, csv, latest = _monitor_setup(trained, tmp_path, monkeypatch, baseline_acc=5.0)  # impossible baseline
    r = rt.run_monitoring_cycle(csv, latest)
    assert r["performance_drift"] is True and r["needs_retraining"] is True


def test_monitoring_reports_error_instead_of_fake_success(tmp_path):
    from src.mlops.auto_retrainer import AutoRetrainer
    r = AutoRetrainer().run_monitoring_cycle(str(tmp_path / "missing.csv"), str(tmp_path / "none.json"))
    assert "error" in r and "monitoring_completed" not in r
