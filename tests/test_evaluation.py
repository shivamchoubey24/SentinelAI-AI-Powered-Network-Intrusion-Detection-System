"""Held-out NSL-KDD evaluation: feature alignment and metric correctness (no TensorFlow needed)."""
import numpy as np
import pandas as pd

from src.evaluation import nsl_kdd_eval as ev


def _raw(rows):
    """Build a minimal raw-format frame with the 43 NSL-KDD columns."""
    base = {c: [0] * len(rows) for c in ev.COLUMNS}
    base["protocol_type"] = ["tcp"] * len(rows)
    base["service"] = ["http"] * len(rows)
    base["flag"] = ["SF"] * len(rows)
    base["difficulty"] = [10] * len(rows)
    for i, label in enumerate(rows):
        base["label"][i] = label
    df = pd.DataFrame(base)
    return df


def test_build_features_aligns_to_training_columns():
    train_cols = ["duration", "protocol_type_tcp", "protocol_type_udp", "service_http", "flag_SF"]
    raw = _raw(["normal", "neptune"])
    raw.loc[1, "protocol_type"] = "udp"           # a category absent from train_cols' "tcp" row
    X = ev.build_features(raw, train_cols)
    assert X.shape == (2, 5)
    assert list(X[0]) == [0, 1, 0, 1, 1]           # tcp -> protocol_type_tcp=1
    assert list(X[1]) == [0, 0, 1, 1, 1]           # udp -> protocol_type_udp=1


def test_evaluate_reports_expected_metrics_on_toy_data():
    raw = _raw(["normal", "normal", "neptune", "satan", "worm"])  # worm = novel, not in "train"
    train_cols = ["duration", "protocol_type_tcp", "service_http", "flag_SF"]
    train_labels = pd.Series(["normal", "neptune", "satan"])

    def predict_fn(X):
        # flag every non-"normal"-shaped row as attack (all rows identical here, so predict via index)
        preds = np.array([0, 0, 1, 1, 1])
        return preds, preds.astype(float)

    r = ev.evaluate(predict_fn, raw, train_labels, train_cols)
    assert r["test_plus"]["n"] == 5 and r["test_plus"]["accuracy"] == 1.0
    assert r["attack_types"]["novel_not_in_training"]["records"] == 1
    assert r["attack_types"]["novel_not_in_training"]["types"] == ["worm"]
    assert r["attack_types"]["seen_in_training"]["records"] == 2
    assert r["per_family_recall"]["dos"]["records"] == 1        # neptune
    assert r["per_family_recall"]["probe"]["records"] == 1      # satan


def test_test21_is_subset_of_test_plus():
    raw = _raw(["normal", "neptune", "neptune"])
    raw["difficulty"] = [21, 21, 5]
    train_cols = ["duration", "protocol_type_tcp", "service_http", "flag_SF"]

    def predict_fn(X):
        p = np.ones(len(X))
        return p, p

    r = ev.evaluate(predict_fn, raw, pd.Series(["normal", "neptune"]), train_cols)
    assert r["test_plus"]["n"] == 3 and r["test_21"]["n"] == 1


def test_per_attack_recall_filters_by_min_records():
    raw = _raw(["neptune"] * 25 + ["worm"] * 5)
    train_cols = ["duration", "protocol_type_tcp", "service_http", "flag_SF"]

    def predict_fn(X):
        p = np.zeros(len(X))
        return p, p

    out = ev.per_attack_recall(predict_fn, raw, train_cols, min_records=20)
    assert list(out.index) == ["neptune"]           # worm has only 5 records, filtered out
    assert out.loc["neptune", "records"] == 25
