from __future__ import annotations

import re
from typing import Any


def normalize_call_id(raw_call_id: str) -> str:
    digits = re.sub(r"\D", "", raw_call_id)
    if digits:
        return f"CALL_{digits.zfill(4)}"
    return raw_call_id.strip().upper()


def normalize_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, segment in enumerate(segments, start=1):
        text = _normalize_whitespace(str(segment.get("text", "")))
        emotion = segment.get("emotion")
        normalized.append(
            {
                "segment_id": index,
                "timestamp": str(segment.get("timestamp", "")),
                "start_time": str(segment.get("start_time", "")),
                "end_time": str(segment.get("end_time", "")),
                "type": str(segment.get("type", "dialogue")),
                "speaker": segment.get("speaker"),
                "speaker_name": segment.get("speaker_name"),
                "speaker_label": segment.get("speaker_label"),
                "emotion": _normalize_emotion(str(emotion)) if emotion else None,
                "text": text,
            }
        )
    return normalized


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_emotion(text: str) -> str:
    return _normalize_whitespace(text).lower().replace("/", "_")
