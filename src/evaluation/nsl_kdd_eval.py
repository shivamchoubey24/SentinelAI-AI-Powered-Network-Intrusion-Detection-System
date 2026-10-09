"""
Honest evaluation of a trained model on NSL-KDD's official held-out test set.

Why this exists: the training script reports metrics from a random split of the
*same* file it trains on, which is the most flattering way to score NSL-KDD.
KDDTest+ has a different distribution and contains attack types absent from
training, so it is a much better proxy for "will this work on traffic it has
not seen". Reported here:

  * KDDTest+        the full official test set
  * KDDTest-21      the harder subset (drops the records that are easy for
                    almost every classifier, difficulty level 21)
  * seen / novel    detection rate on attack types present in the training
                    file vs attack types the model never saw
  * per family      recall for DoS / Probe / R2L / U2R

Test features are aligned to the TRAINING feature columns (one-hot columns
missing from the test file become 0; categories never seen in training are
dropped), otherwise the model would receive misaligned inputs.
"""
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)

COLUMNS = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
    "land", "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in",
    "num_compromised", "root_shell", "su_attempted", "num_root", "num_file_creations",
    "num_shells", "num_access_files", "num_outbound_cmds", "is_host_login",
    "is_guest_login", "count", "srv_count", "serror_rate", "srv_serror_rate",
    "rerror_rate", "srv_rerror_rate", "same_srv_rate", "diff_srv_rate",
    "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate", "dst_host_same_src_port_rate",
    "dst_host_srv_diff_host_rate", "dst_host_serror_rate", "dst_host_srv_serror_rate",
    "dst_host_rerror_rate", "dst_host_srv_rerror_rate", "label", "difficulty",
]

FAMILIES = {
    "dos": ["back", "land", "neptune", "pod", "smurf", "teardrop", "mailbomb",
            "apache2", "processtable", "udpstorm"],
    "probe": ["satan", "ipsweep", "nmap", "portsweep", "mscan", "saint"],
    "r2l": ["guess_passwd", "ftp_write", "imap", "phf", "multihop", "warezmaster",
            "warezclient", "spy", "xlock", "xsnoop", "snmpguess", "snmpgetattack",
            "httptunnel", "sendmail", "named", "worm"],
    "u2r": ["buffer_overflow", "loadmodule", "rootkit", "perl", "sqlattack", "xterm", "ps"],
}
ATTACK_TO_FAMILY = {a: fam for fam, names in FAMILIES.items() for a in names}


def read_raw(path: str) -> pd.DataFrame:
    return pd.read_csv(path, names=COLUMNS)


def feature_columns(processed_train_csv: str) -> List[str]:
    """Feature names (label excluded) in the exact order the model was trained on."""
    cols = list(pd.read_csv(processed_train_csv, nrows=0).columns)
    return cols[:-1]


def build_features(raw: pd.DataFrame, train_columns: List[str]) -> np.ndarray:
    """One-hot encode like preprocessing does, then align to the training columns."""
    df = raw.drop(columns=["label", "difficulty"])
    df = pd.get_dummies(df, columns=["protocol_type", "service", "flag"])
    df = df.reindex(columns=train_columns, fill_value=0)
    return df.astype(float).to_numpy()


def _binary_metrics(y_true: np.ndarray, y_pred: np.ndarray, proba: np.ndarray) -> Dict[str, Any]:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = (int(v) for v in cm.ravel())
    out = {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if (fn + tp) else 0.0,
        "confusion_matrix": cm.tolist(),
    }
    out["roc_auc"] = float(roc_auc_score(y_true, proba)) if len(set(y_true.tolist())) == 2 else None
    return out


def evaluate(predict_fn: Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]],
             test_raw: pd.DataFrame, train_raw_labels: pd.Series,
             train_columns: List[str]) -> Dict[str, Any]:
    """
    Score `predict_fn` (X -> (binary predictions, attack probabilities)) on a raw
    NSL-KDD test frame. `train_raw_labels` are the attack names in the training file.
    """
    X = build_features(test_raw, train_columns)
    y = (test_raw["label"] != "normal").astype(int).to_numpy()
    pred, proba = predict_fn(X)
    pred = np.asarray(pred).astype(int).flatten()
    proba = np.asarray(proba, dtype=float).flatten()

    result: Dict[str, Any] = {"test_plus": _binary_metrics(y, pred, proba)}

    hard = (test_raw["difficulty"] < 21).to_numpy()
    result["test_21"] = _binary_metrics(y[hard], pred[hard], proba[hard])

    labels = test_raw["label"].to_numpy()
    seen_names = set(train_raw_labels.unique()) - {"normal"}
    is_attack = y == 1
    novel = is_attack & ~np.isin(labels, list(seen_names))
    seen = is_attack & np.isin(labels, list(seen_names))
    result["attack_types"] = {
        "seen_in_training": {"records": int(seen.sum()),
                             "detection_rate": float(pred[seen].mean()) if seen.any() else None},
        "novel_not_in_training": {"records": int(novel.sum()),
                                  "detection_rate": float(pred[novel].mean()) if novel.any() else None,
                                  "types": sorted(set(labels[novel].tolist()))},
    }

    fams: Dict[str, Any] = {}
    for fam in FAMILIES:
        mask = np.array([ATTACK_TO_FAMILY.get(l) == fam for l in labels])
        fams[fam] = {"records": int(mask.sum()),
                     "detection_rate": float(pred[mask].mean()) if mask.any() else None}
    result["per_family_recall"] = fams
    return result


def per_attack_recall(predict_fn, test_raw: pd.DataFrame, train_columns: List[str], min_records: int = 20):
    """Detection rate for each individual attack name (for finding blind spots)."""
    X = build_features(test_raw, train_columns)
    pred = np.asarray(predict_fn(X)[0]).astype(int).flatten()
    df = pd.DataFrame({"label": test_raw["label"], "pred": pred})
    df = df[df["label"] != "normal"]
    g = df.groupby("label")["pred"].agg(records="count", detection_rate="mean")
    return g[g["records"] >= min_records].sort_values("detection_rate")
