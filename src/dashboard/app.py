"""Deprecated entry point: the full dashboard now lives in app_simple.py.

The old app.py mixed real and simulated numbers. It is kept as a shim so
`streamlit run src/dashboard/app.py` (used by older scripts) still works.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.dashboard.app_simple import main  # noqa: E402

main()
