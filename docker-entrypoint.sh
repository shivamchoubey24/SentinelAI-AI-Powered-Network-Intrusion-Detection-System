#!/bin/sh
set -e
# Create tables (idempotent) before the API starts.
python scripts/init_database.py
exec "$@"
