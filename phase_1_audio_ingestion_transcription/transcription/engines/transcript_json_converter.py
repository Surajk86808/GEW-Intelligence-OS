from __future__ import annotations

from typing import Any


def structured_transcript_to_text(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    for segment in payload.get("transcript", []):
        timestamp = str(segment.get("timestamp", "")).strip()
        speaker = segment.get("speaker_label") or segment.get("speaker") or "Unknown"
        emotion = segment.get("emotion")
        text = str(segment.get("text", "")).strip()
        if segment.get("type") == "event":
            lines.append(f"{timestamp} {text}".strip())
            continue
        emotion_prefix = f" ({emotion})" if emotion else ""
        lines.append(f"{timestamp} {speaker}{emotion_prefix}: {text}".strip())
    return "\n".join(lines).strip()


def build_transcript_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(payload.get("metadata", {}))
    words = sum(len(str(segment.get("text", "")).split()) for segment in payload.get("transcript", []))
    metadata.update(
        {
            "word_count": words,
            "segment_count": len(payload.get("transcript", [])),
            "detected_language": metadata.get("detected_language") or "mixed",
            "confidence_score": metadata.get("confidence_score"),
            "structured": True,
        }
    )
    return metadata
