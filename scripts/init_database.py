#!/usr/bin/env python3
"""
Create project directories and initialise the database schema.

Uses DATABASE_URL (default: sqlite:///data/sentinel.db). Idempotent - safe
to run repeatedly.
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import setup_logger  # noqa: E402
from src.db import init_db, get_engine  # noqa: E402

logger = setup_logger(__name__)

DIRECTORIES = [
    "data/raw", "data/processed", "data/models", "data/blockchain", "logs", "outputs",
]


def create_directories() -> None:
    for d in DIRECTORIES:
        os.makedirs(d, exist_ok=True)
        logger.info(f"Directory ready: {d}")


def main() -> int:
    create_directories()
    try:
        init_db()
        engine = get_engine()
        logger.info(f"Database ready: {engine.url.render_as_string(hide_password=True)}")
        return 0
    except Exception as e:
        logger.error(f"Database initialisation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
