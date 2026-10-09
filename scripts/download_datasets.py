#!/usr/bin/env python3
"""
Script to download security datasets.

Downloads the NSL-KDD intrusion-detection dataset (a real, labeled,
benchmark IDS dataset — not synthetic data). We use NSL-KDD instead of
CIC-IDS2017 / UNSW-NB15 because those require manual authenticated
download from their host institutions, while NSL-KDD is small (a 20%
subset is ~25k rows), freely mirrored, and widely used as an IDS
benchmark, which makes it a good fit for training on a laptop.

KDDTrain+_20Percent.txt (the 20% subset) is used by default to keep
training fast and laptop-friendly. Pass --full to fetch the complete
KDDTrain+.txt (~125k rows) instead.
"""

import os
import sys
import argparse
from pathlib import Path

import requests

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

NSL_KDD_BASE = "https://raw.githubusercontent.com/jmnwong/NSL-KDD-Dataset/master"

# 41 feature names + 'label' + 'difficulty', per the NSL-KDD documentation
NSL_KDD_COLUMNS = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
    "land", "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in",
    "num_compromised", "root_shell", "su_attempted", "num_root", "num_file_creations",
    "num_shells", "num_access_files", "num_outbound_cmds", "is_host_login",
    "is_guest_login", "count", "srv_count", "serror_rate", "srv_serror_rate",
    "rerror_rate", "srv_rerror_rate", "same_srv_rate", "diff_srv_rate",
    "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate", "dst_host_same_src_port_rate",
    "dst_host_srv_diff_host_rate", "dst_host_serror_rate", "dst_host_srv_serror_rate",
    "dst_host_rerror_rate", "dst_host_srv_rerror_rate", "label", "difficulty"
]


def _download_file(url: str, dest_path: str) -> bool:
    """Download a single file over HTTP(S) and save it to dest_path."""
    try:
        logger.info(f"Downloading {url} ...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(response.content)
        logger.info(f"Saved to {dest_path} ({len(response.content) / 1024:.1f} KB)")
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False


def download_nsl_kdd(use_full: bool = False) -> bool:
    """
    Download the real NSL-KDD intrusion detection dataset.

    Args:
        use_full: if True, download the full ~125k-row training set instead
                   of the 20% (~25k-row) subset used by default.

    Returns:
        True if both train and test files were downloaded successfully.
    """
    out_dir = "data/raw/nsl_kdd"
    train_name = "KDDTrain+.txt" if use_full else "KDDTrain+_20Percent.txt"
    train_url = f"{NSL_KDD_BASE}/{train_name.replace('+', '%2B')}"
    test_url = f"{NSL_KDD_BASE}/KDDTest%2B.txt"

    ok_train = _download_file(train_url, f"{out_dir}/{train_name}")
    ok_test = _download_file(test_url, f"{out_dir}/KDDTest+.txt")

    if ok_train and ok_test:
        logger.info(
            "NSL-KDD download complete. This is a real, labeled intrusion "
            "detection benchmark dataset (not synthetic)."
        )
    return ok_train and ok_test


def preprocess_nsl_kdd(use_full: bool = False) -> str:
    """
    Convert the raw NSL-KDD text files into a single labeled CSV that the
    existing ThreatDetector pipeline can train on directly:
    - Assigns real column names
    - Collapses the multi-class attack label into a binary label
      (0 = normal, 1 = attack), matching what MLPGRUModel expects
    - One-hot encodes the categorical columns (protocol_type, service, flag)
    - Drops the 'difficulty' column (not a feature)

    Returns:
        Path to the processed CSV file.
    """
    import pandas as pd

    out_dir = "data/raw/nsl_kdd"
    train_name = "KDDTrain+.txt" if use_full else "KDDTrain+_20Percent.txt"
    train_path = f"{out_dir}/{train_name}"

    if not os.path.exists(train_path):
        raise FileNotFoundError(
            f"{train_path} not found — run download_nsl_kdd() first."
        )

    logger.info(f"Preprocessing {train_path} ...")
    df = pd.read_csv(train_path, names=NSL_KDD_COLUMNS)

    # Binary label: 'normal' -> 0, any attack type -> 1
    df["label"] = (df["label"] != "normal").astype(int)
    df = df.drop(columns=["difficulty"])

    # One-hot encode categoricals so everything is numeric for the model
    df = pd.get_dummies(df, columns=["protocol_type", "service", "flag"])

    # Move label to the last column (ThreatDetector assumes this)
    label_col = df.pop("label")
    df["label"] = label_col

    os.makedirs("data/processed", exist_ok=True)
    processed_path = "data/processed/nsl_kdd_processed.csv"
    df.to_csv(processed_path, index=False)

    logger.info(
        f"Processed dataset saved to {processed_path} "
        f"({len(df)} records, {df.shape[1] - 1} features, "
        f"{int(df['label'].sum())} attack / {int((df['label'] == 0).sum())} normal)"
    )
    return processed_path


def main():
    parser = argparse.ArgumentParser(description="Download real IDS datasets")
    parser.add_argument(
        "--full", action="store_true",
        help="Download the full NSL-KDD training set (~125k rows) instead of "
             "the 20%% subset (~25k rows, default — faster on a laptop)"
    )
    parser.add_argument(
        "--no-preprocess", action="store_true",
        help="Only download raw files, skip generating the processed CSV"
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Security Dataset Downloader (NSL-KDD)")
    logger.info("=" * 60)

    if not download_nsl_kdd(use_full=args.full):
        logger.error("Dataset download failed. Check your network connection.")
        sys.exit(1)

    if not args.no_preprocess:
        preprocess_nsl_kdd(use_full=args.full)

    logger.info("=" * 60)
    logger.info("Dataset setup completed! Ready for training:")
    logger.info("  python -m src.models.threat_detector")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
