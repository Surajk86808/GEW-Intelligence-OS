from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Patterns
TIMESTAMPED_SEGMENT_PATTERN = re.compile(
    r"^(?P<start>\d{1,2}:\d{2})\s*-\s*(?P<end>\d{1,2}:\d{2})\s*:\s*(?P<body>.+)$"
)
SPEAKER_BODY_PATTERN = re.compile(
    r"^(?P<label>[^:]+?)\s*:\s*(?:(?P<emotion>\([^)]*\))\s*)?(?P<text>.+)$"
)
CALL_HEADER_PATTERN = re.compile(r"^(CALL[_\-\s]?\d+)(?:\.\w+)?\s*$", re.IGNORECASE)

@dataclass(frozen=True)
class TranscriptBlock:
    call_id: str
    raw_header: str
    block_text: str

# ID Normalization
def normalize_call_id(raw_call_id: str) -> str:
    digits = re.sub(r"\D", "", raw_call_id)
    if digits:
        return f"CALL_{digits.zfill(4)}"
    return raw_call_id.strip().upper()

# Segment Normalization
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

# Parsing Logic
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
    if ":" not in value:
        return value
    minutes_text, seconds_text = value.split(":", maxsplit=1)
    try:
        minutes = int(minutes_text)
        seconds = int(seconds_text)
        return f"{minutes:02d}:{seconds:02d}"
    except ValueError:
        return value

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

# Splitter Logic
def split_combined_transcript(content: str) -> list[TranscriptBlock]:
    lines = content.splitlines()
    blocks: list[TranscriptBlock] = []
    current_call_id = ""
    current_header = ""
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        match = CALL_HEADER_PATTERN.match(stripped)
        if match:
            if current_call_id and current_lines:
                blocks.append(
                    TranscriptBlock(
                        call_id=normalize_call_id(current_call_id),
                        raw_header=current_header,
                        block_text="\n".join(current_lines).strip(),
                    )
                )
            current_call_id = match.group(1)
            current_header = stripped
            current_lines = [stripped]
            continue

        if current_call_id:
            current_lines.append(line)

    if current_call_id and current_lines:
        blocks.append(
            TranscriptBlock(
                call_id=normalize_call_id(current_call_id),
                raw_header=current_header,
                block_text="\n".join(current_lines).strip(),
            )
        )

    return blocks

# Structurer Logic
def build_structured_transcript(
    call_id: str,
    segments: list[dict[str, Any]],
    *,
    source: str,
    transcript_origin: str,
    source_path: str,
    audio_path: str = "",
    manifest_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    participants = _build_participants(segments)
    duration = segments[-1]["end_time"] if segments else "00:00"
    duration_sec = mmss_to_seconds(duration)
    manifest_context = manifest_context or {}

    metadata = {
        "call_id": call_id,
        "duration": duration,
        "duration_seconds": duration_sec,
        "total_segments": len(segments),
        "source": source,
        "transcript_origin": transcript_origin,
        "source_path": source_path,
        "audio_path": audio_path,
        "normalized": True,
        "json_converted": True,
        "enrichment_prepared": True,
        "has_audio": bool(audio_path),
        "owner": str(manifest_context.get("owner", "")).strip(),
        "campaign": str(manifest_context.get("campaign", "")).strip(),
        "lead_number": str(manifest_context.get("lead_number", "")).strip(),
        "walkin_status": str(manifest_context.get("walkin_status", "")).strip(),
    }

    return {
        "metadata": metadata,
        "participants": participants,
        "transcript": segments,
    }

def _build_participants(segments: list[dict[str, Any]]) -> dict[str, Any]:
    counselor_names = sorted({str(item["speaker_name"]) for item in segments if item.get("speaker") == "Counselor" and item.get("speaker_name")})
    caller_names = sorted({str(item["speaker_name"]) for item in segments if item.get("speaker") == "Caller" and item.get("speaker_name")})
    unique_speakers = sorted(
        {
            str(item["speaker_name"] or item["speaker"] or "Unknown")
            for item in segments
            if item.get("type") == "dialogue"
        }
    )

    return {
        "Counselor": {
            "present": any(item.get("speaker") == "Counselor" for item in segments),
            "names": counselor_names,
        },
        "Caller": {
            "present": any(item.get("speaker") == "Caller" for item in segments),
            "names": caller_names,
        },
        "total_unique_speakers": len(unique_speakers),
        "speaker_labels_detected": sorted(
            {str(item.get("speaker_label")) for item in segments if item.get("speaker_label")}
        ),
    }

def mmss_to_seconds(value: str) -> int:
    if not value or ":" not in value:
        return 0
    try:
        minutes_text, seconds_text = value.split(":", maxsplit=1)
        return int(minutes_text) * 60 + int(seconds_text)
    except ValueError:
        return 0
