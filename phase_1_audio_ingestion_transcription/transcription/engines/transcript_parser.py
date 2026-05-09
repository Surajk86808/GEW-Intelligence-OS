from __future__ import annotations

import re
from typing import Any

TIMESTAMPED_SEGMENT_PATTERN = re.compile(
    r"^(?P<start>\d{1,2}:\d{2})\s*-\s*(?P<end>\d{1,2}:\d{2})\s*:\s*(?P<body>.+)$"
)
SPEAKER_BODY_PATTERN = re.compile(
    r"^(?P<label>[^:]+?)\s*:\s*(?:(?P<emotion>\([^)]*\))\s*)?(?P<text>.+)$"
)


def parse_transcript_block(call_id: str, block_text: str) -> list[dict[str, Any]]:
    lines = [line.rstrip() for line in block_text.splitlines()]
    segments: list[dict[str, Any]] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.upper().startswith(call_id):
            continue

        timestamp_match = TIMESTAMPED_SEGMENT_PATTERN.match(stripped)
        if not timestamp_match:
            continue

        start_time = _normalize_mmss(timestamp_match.group("start"))
        end_time = _normalize_mmss(timestamp_match.group("end"))
        body = timestamp_match.group("body").strip()
        segments.append(_parse_body(start_time, end_time, body))

    return segments


def _parse_body(start_time: str, end_time: str, body: str) -> dict[str, Any]:
    if body.startswith("[") and body.endswith("]"):
        return {
            "timestamp": f"[{start_time} - {end_time}]",
            "start_time": start_time,
            "end_time": end_time,
            "type": "event",
            "speaker": None,
            "speaker_name": None,
            "speaker_label": None,
            "emotion": None,
            "text": body,
        }

    match = SPEAKER_BODY_PATTERN.match(body)
    if not match:
        return {
            "timestamp": f"[{start_time} - {end_time}]",
            "start_time": start_time,
            "end_time": end_time,
            "type": "dialogue",
            "speaker": "Unknown",
            "speaker_name": None,
            "speaker_label": "Unknown",
            "emotion": None,
            "text": _strip_wrapping_quotes(body),
        }

    raw_label = match.group("label").strip()
    raw_emotion = match.group("emotion")
    text = _strip_wrapping_quotes(match.group("text").strip())
    speaker_name = _extract_speaker_name(raw_label)
    speaker = _classify_speaker(raw_label, speaker_name)
    emotion = raw_emotion[1:-1].strip() if raw_emotion else None

    return {
        "timestamp": f"[{start_time} - {end_time}]",
        "start_time": start_time,
        "end_time": end_time,
        "type": "dialogue",
        "speaker": speaker,
        "speaker_name": speaker_name,
        "speaker_label": raw_label,
        "emotion": emotion,
        "text": text,
    }


def _normalize_mmss(value: str) -> str:
    minutes_text, seconds_text = value.split(":", maxsplit=1)
    minutes = int(minutes_text)
    seconds = int(seconds_text)
    return f"{minutes:02d}:{seconds:02d}"


def _extract_speaker_name(label: str) -> str | None:
    parenthetical = re.search(r"\(([^)]+)\)", label)
    if parenthetical:
        return parenthetical.group(1).strip()
    bare = label.strip()
    if bare.lower() in {"caller", "recipient", "counselor", "female counselor", "male counselor", "unknown"}:
        return None
    return bare


def _classify_speaker(label: str, speaker_name: str | None) -> str:
    normalized = label.strip().lower()
    if "caller" in normalized:
        return "Caller"
    if "recipient" in normalized or "counselor" in normalized:
        return "Counselor"
    if speaker_name:
        return "Counselor"
    return "Unknown"


def _strip_wrapping_quotes(text: str) -> str:
    stripped = text.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "'"}:
        return stripped[1:-1].strip()
    return stripped
