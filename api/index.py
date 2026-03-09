"""Vercel serverless entry point for the RevTry warm dashboard.

Vercel's Python runtime expects a FastAPI/ASGI app exposed from api/index.py.
This module adds src/ to the Python path so all internal imports work correctly,
then re-exports the FastAPI app instance.
"""

import sys
from pathlib import Path

# Add src/ to Python path so imports like "from dashboard.app import app" work
src_dir = str(Path(__file__).resolve().parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from dashboard.app import app  # noqa: E402, F401
