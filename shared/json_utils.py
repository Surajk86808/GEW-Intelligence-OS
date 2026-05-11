from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (np.int64, np.int32, np.int16, np.int8)):
            return int(o)
        if isinstance(o, (np.float64, np.float32, np.float16)):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.bool_)):
            return bool(o)
        return super().default(o)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temp_path = tempfile.mkstemp(prefix=f"{path.stem}_", suffix=path.suffix, dir=str(path.parent))
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, cls=EnhancedJSONEncoder)
            handle.flush()
            os.fsync(handle.fileno())
        
        # Robust move for Windows file locks
        _atomic_replace(Path(temp_path), path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    return path


def write_text_atomic(path: Path, content: str, encoding: str = "utf-8") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temp_path = tempfile.mkstemp(prefix=f"{path.stem}_", suffix=path.suffix, dir=str(path.parent))
    try:
        with os.fdopen(file_descriptor, "w", encoding=encoding) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        
        # Robust move for Windows file locks
        _atomic_replace(Path(temp_path), path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    return path


def _atomic_replace(src: Path, dst: Path, retries: int = 5, delay: float = 0.2) -> None:
    """Performs an atomic replacement with retries for Windows environments."""
    import time
    for i in range(retries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if i == retries - 1:
                # Last attempt failed, try a non-atomic copy as fallback if destination is locked
                # (risky but better than a crash in many cases, or just re-raise)
                raise
            time.sleep(delay)
        except OSError:
            if i == retries - 1:
                raise
            time.sleep(delay)
