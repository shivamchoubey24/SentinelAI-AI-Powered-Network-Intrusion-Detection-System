#!/usr/bin/env python3
"""
One-time migration: convert legacy pickle scaler/encoder files to the safe
JSON format used by Phase 3. Only run this on model files YOU produced -
loading a pickle executes whatever code it contains.

Usage:
    python scripts/migrate_model_artifacts.py            # all models in data/models
    python scripts/migrate_model_artifacts.py --delete   # also remove the .pkl files
"""
import argparse
import json
import pickle
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.models.threat_detector import MLPGRUModel  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models-dir", default="data/models")
    ap.add_argument("--delete", action="store_true", help="remove .pkl files after converting")
    args = ap.parse_args()

    converted = 0
    for scaler_pkl in sorted(Path(args.models_dir).glob("*_scaler.pkl")):
        prefix = str(scaler_pkl)[: -len("_scaler.pkl")]
        model_file, enc_pkl, out = f"{prefix}_model.h5", Path(f"{prefix}_encoder.pkl"), Path(f"{prefix}_preproc.json")
        if out.exists() or not Path(model_file).exists():
            continue
        w = MLPGRUModel({})
        with open(scaler_pkl, "rb") as f:
            w.scaler = pickle.load(f)  # trusted, locally produced files only
        if enc_pkl.exists():
            with open(enc_pkl, "rb") as f:
                w.label_encoder = pickle.load(f)
        out.write_text(json.dumps(w._preproc_to_dict(model_file)))
        print(f"converted {prefix}")
        converted += 1
        if args.delete:
            scaler_pkl.unlink()
            enc_pkl.unlink(missing_ok=True)
    print(f"{converted} model(s) converted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
