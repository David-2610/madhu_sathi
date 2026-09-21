"""
API entry point for Honey Chain / Madhu Sathi backend (Root api/index.py for Vercel).
Exports the FastAPI application instance by importing from backend/app/main.py.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app

__all__ = ["app"]
