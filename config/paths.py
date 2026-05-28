"""
Single source of truth for the project root.
Set CIPHER_DIR env var to override (useful on CI, remote machines, Docker).
Falls back to auto-detection from this file's location.
"""
import os
from pathlib import Path

BASE_DIR: Path = Path(os.environ.get("CIPHER_DIR", Path(__file__).resolve().parent.parent))
