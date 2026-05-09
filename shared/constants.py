from __future__ import annotations

from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = WORKSPACE_DIR / "data"
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}

