from __future__ import annotations

import re
from pathlib import Path

from shared.json_utils import read_json

TIMESTAMP_PATTERN = re.compile(r"^\[(\d{2}):(\d{2})\]\s+(.*)$")
RANGED_TIMESTAMP_PATTERN = re.compile(r"^\[(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})\]\s+(.*)$")


def read_transcript_metrics(transcript_path: Path, transcript_metadata_path: Path | None) -> dict[str, float | int | None]:
    if transcript_path.suffix.lower() == ".json":
        return _read_json_transcript_metrics(transcript_path, transcript_metadata_path)

    transcript_text = transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else ""
    line_count = 0
    timestamped_segments = 0
    words = 0

    for raw_line in transcript_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line_count += 1
        match = RANGED_TIMESTAMP_PATTERN.match(line) or TIMESTAMP_PATTERN.match(line)
        if match:
            timestamped_segments += 1
            text = match.group(match.lastindex or 0)
        else:
            text = line
        words += len(text.split())

    metadata = read_json(transcript_metadata_path, default={}) if transcript_metadata_path else {}
    audio_duration = float(metadata.get("audio_duration", 0.0) or 0.0)
    speaking_rate_wpm = round((words / audio_duration) * 60, 2) if audio_duration > 0 else None

    return {
        "transcript_word_count": words,
        "transcript_line_count": line_count,
        "timestamped_segment_count": timestamped_segments,
        "transcript_confidence_score": metadata.get("confidence_score"),
        "detected_language": metadata.get("detected_language"),
        "speaking_rate_wpm": speaking_rate_wpm,
    }


def _read_json_transcript_metrics(transcript_path: Path, transcript_metadata_path: Path | None) -> dict[str, float | int | None]:
    payload = read_json(transcript_path, default={}) or {}
    transcript_segments = payload.get("transcript", [])
    words = sum(len(str(segment.get("text", "")).split()) for segment in transcript_segments)
    timestamped_segments = sum(1 for segment in transcript_segments if segment.get("start_time"))
    metadata = dict(payload.get("metadata", {}))
    if transcript_metadata_path:
        metadata.update(read_json(transcript_metadata_path, default={}) or {})
    audio_duration = float(metadata.get("audio_duration", metadata.get("duration_seconds", 0.0)) or 0.0)
    speaking_rate_wpm = round((words / audio_duration) * 60, 2) if audio_duration > 0 else None

    return {
        "transcript_word_count": words,
        "transcript_line_count": len(transcript_segments),
        "timestamped_segment_count": timestamped_segments,
        "transcript_confidence_score": metadata.get("confidence_score"),
        "detected_language": metadata.get("detected_language"),
        "speaking_rate_wpm": speaking_rate_wpm,
    }
