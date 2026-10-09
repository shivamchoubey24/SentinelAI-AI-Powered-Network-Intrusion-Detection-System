#!/usr/bin/env python3
"""
Train the threat detection model on real, processed data and record the
resulting metrics + model path in data/models/latest.json so the API and
dashboard can load the most recently trained model instead of hardcoded
numbers.

Usage:
    python scripts/train_model.py
    python scripts/train_model.py --data data/processed/nsl_kdd_processed.csv
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from src.models.threat_detector import ThreatDetector
from src.utils.logger import setup_logger
from src.blockchain.blockchain_logger import BlockchainLogger

logger = setup_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Train the IDS model on real data")
    parser.add_argument(
        "--data", default="data/processed/nsl_kdd_processed.csv",
        help="Path to processed, labeled CSV (last column = binary label)"
    )
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        logger.error(
            f"{data_path} not found. Run: python scripts/download_datasets.py first."
        )
        sys.exit(1)

    logger.info(f"Training on real dataset: {data_path}")
    detector = ThreatDetector()
    result = detector.train_model(str(data_path))

    # Persist a pointer + metrics so the API/dashboard can find the latest
    # real model instead of relying on hardcoded numbers.
    latest_info = {
        "model_path": result["model_path"],
        "trained_at": datetime.now().isoformat(),
        "dataset": str(data_path),
        "metrics": {
            k: v for k, v in result["metrics"].items() if k != "confusion_matrix"
        },
        "confusion_matrix": result["metrics"]["confusion_matrix"],
    }

    latest_path = Path("data/models/latest.json")
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(latest_path, "w") as f:
        json.dump(latest_info, f, indent=2)

    logger.info(f"Latest model pointer written to {latest_path}")

    # Persist the run (real metrics) in the database as well
    try:
        from src.db import repository
        run_id = repository.record_model_run(latest_info)
        logger.info(f"Model run stored in database (id={run_id})")
    except Exception as e:
        logger.warning(f"Could not store model run in database: {e}")
    logger.info(f"Real metrics: {latest_info['metrics']}")

    # Log the training event to the audit chain (real event, real metrics)
    try:
        bc_logger = BlockchainLogger()
        bc_logger.log_model_update({
            "operation": "MODEL_TRAIN",
            "model_path": result["model_path"],
            "dataset": str(data_path),
            **latest_info["metrics"],
        })
    except Exception as e:
        logger.warning(f"Could not log training event to blockchain: {e}")

    logger.info("Training complete.")


if __name__ == "__main__":
    main()
