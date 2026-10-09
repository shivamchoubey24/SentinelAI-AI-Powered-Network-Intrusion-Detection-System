#!/usr/bin/env python3
"""
Honest evaluation of the latest trained model on NSL-KDD's official held-out
KDDTest+ set (not the random split of the training file used during training).

Usage:
    python scripts/evaluate_model.py
    python scripts/evaluate_model.py --model data/models/threat_detector_XXXX

Writes data/models/latest_eval.json and prints a summary.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.evaluation import nsl_kdd_eval as ev  # noqa: E402
from src.models.threat_detector import MLPGRUModel  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402

logger = setup_logger(__name__)

TRAIN_RAW = "data/raw/nsl_kdd/KDDTrain+_20Percent.txt"
TEST_RAW = "data/raw/nsl_kdd/KDDTest+.txt"
PROCESSED_TRAIN = "data/processed/nsl_kdd_processed.csv"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="model path prefix; defaults to data/models/latest.json")
    ap.add_argument("--full", action="store_true", help="raw training file used the full KDDTrain+.txt")
    args = ap.parse_args()

    for p in (TEST_RAW, PROCESSED_TRAIN):
        if not Path(p).exists():
            logger.error(f"{p} not found. Run: python scripts/download_datasets.py first.")
            return 1

    if args.model:
        model_path = args.model
    else:
        latest = json.loads(Path("data/models/latest.json").read_text())
        model_path = latest["model_path"]

    train_name = "KDDTrain+.txt" if args.full else "KDDTrain+_20Percent.txt"
    train_raw_path = f"data/raw/nsl_kdd/{train_name}"
    if not Path(train_raw_path).exists():
        logger.error(f"{train_raw_path} not found (pass --full if you trained on the full set).")
        return 1

    logger.info(f"Evaluating {model_path} on the official KDDTest+ held-out set")
    model = MLPGRUModel({})
    model.load_model(model_path)

    cols = ev.feature_columns(PROCESSED_TRAIN)
    train_raw = ev.read_raw(train_raw_path)
    test_raw = ev.read_raw(TEST_RAW)
    result = ev.evaluate(model.predict, test_raw, train_raw["label"], cols)
    result["model_path"] = model_path
    result["note"] = ("Metrics here are on NSL-KDD's official held-out KDDTest+, which "
                      "includes attack types absent from training. They are typically much "
                      "lower than a random split of the training file, and are a more honest "
                      "estimate of real-world performance on this benchmark.")

    out_path = Path("data/models/latest_eval.json")
    out_path.write_text(json.dumps(result, indent=2))
    logger.info(f"Evaluation written to {out_path}")

    tp, t21 = result["test_plus"], result["test_21"]
    logger.info(f"KDDTest+   : n={tp['n']} acc={tp['accuracy']:.3f} prec={tp['precision']:.3f} "
               f"rec={tp['recall']:.3f} f1={tp['f1_score']:.3f} fpr={tp['false_positive_rate']:.3f}")
    logger.info(f"KDDTest-21 : n={t21['n']} acc={t21['accuracy']:.3f} rec={t21['recall']:.3f}")
    fam = result["per_family_recall"]
    logger.info("Per-family detection rate: " +
               ", ".join(f"{k}={v['detection_rate']:.2f}" if v["detection_rate"] is not None else f"{k}=n/a"
                         for k, v in fam.items()))
    novel = result["attack_types"]["novel_not_in_training"]
    logger.info(f"Novel attack types (not seen in training): {novel['records']} records, "
               f"detection_rate={novel['detection_rate']:.3f}" if novel["detection_rate"] is not None
               else "Novel attack types: none in this test set")

    try:
        from src.blockchain.blockchain_logger import BlockchainLogger
        BlockchainLogger().log_system_event({
            "event": "MODEL_EVALUATION_HELD_OUT", "model_path": model_path,
            "test_plus_accuracy": tp["accuracy"], "test_plus_recall": tp["recall"],
            "test_21_accuracy": t21["accuracy"],
        })
    except Exception as e:
        logger.warning(f"Could not audit-log the evaluation: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
