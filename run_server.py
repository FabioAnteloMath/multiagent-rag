"""Convenience launcher for the backend server.

Run from anywhere - it resolves paths relative to this file so the script
works on any machine without editing absolute paths.
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8011,
        log_level="info",
        reload=False,
    )
