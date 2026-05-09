from __future__ import annotations

from typing import Any


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
    duration_sec = _mmss_to_seconds(duration)
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


def _mmss_to_seconds(value: str) -> int:
    if not value or ":" not in value:
        return 0
    minutes_text, seconds_text = value.split(":", maxsplit=1)
    return int(minutes_text) * 60 + int(seconds_text)
