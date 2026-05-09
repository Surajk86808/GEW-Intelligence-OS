from __future__ import annotations

import re
from typing import Any

from .config import CHUNK_MAX_LINES, MIN_CHUNK_LINES

BRACKET_TIMESTAMP_PATTERN = re.compile(r"^\[(\d{2}:\d{2})\]\s+(.*)$")
RANGE_TIMESTAMP_PATTERN = re.compile(r"^(\d{1,2}:\d{2})\s*-\s*\d{1,2}:\d{2}:\s*(.*)$")


class ChunkingEngine:
    def chunk_conversation(
        self,
        call_id: str,
        transcript_text: str,
        phase3_payload: dict[str, Any],
        reasoning_payload: dict[str, Any],
        crm_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        transcript_lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]
        if not transcript_lines:
            return []

        emotion_timeline = phase3_payload.get("emotion_timeline", [])
        objection_markers = {item.get("timestamp", "") for item in reasoning_payload.get("objections", []) if item.get("timestamp")}

        chunks: list[dict[str, Any]] = []
        bucket: list[dict[str, str]] = []
        for line in transcript_lines:
            parsed = self._parse_line(line)
            bucket.append(parsed)
            boundary_hit = (
                len(bucket) >= CHUNK_MAX_LINES
                or (parsed["timestamp"] in objection_markers and len(bucket) >= MIN_CHUNK_LINES)
                or self._emotion_shift_detected(bucket, emotion_timeline)
            )
            if boundary_hit:
                chunks.append(self._build_chunk(call_id, len(chunks), bucket, emotion_timeline, crm_context, reasoning_payload))
                bucket = []

        if bucket:
            chunks.append(self._build_chunk(call_id, len(chunks), bucket, emotion_timeline, crm_context, reasoning_payload))
        return chunks

    def _build_chunk(
        self,
        call_id: str,
        index: int,
        bucket: list[dict[str, str]],
        emotion_timeline: list[dict[str, Any]],
        crm_context: dict[str, Any],
        reasoning_payload: dict[str, Any],
    ) -> dict[str, Any]:
        start_time = bucket[0]["timestamp"]
        end_time = bucket[-1]["timestamp"]
        text = "\n".join(item["text"] for item in bucket)
        primary_emotion = self._resolve_emotion(start_time, emotion_timeline)
        reasoning_tags = self._resolve_reasoning_tags(text, reasoning_payload)
        return {
            "call_id": call_id,
            "chunk_id": f"{call_id}_chunk_{index + 1:03d}",
            "start_time": start_time,
            "end_time": end_time,
            "speaker": "unknown",
            "text": text,
            "emotion": primary_emotion,
            "crm_context": crm_context,
            "reasoning_tags": reasoning_tags,
        }

    def _parse_line(self, line: str) -> dict[str, str]:
        bracket_match = BRACKET_TIMESTAMP_PATTERN.match(line)
        if bracket_match:
            return {"timestamp": bracket_match.group(1), "text": bracket_match.group(2)}

        range_match = RANGE_TIMESTAMP_PATTERN.match(line)
        if range_match:
            return {"timestamp": self._normalize_timestamp(range_match.group(1)), "text": range_match.group(2)}
        return {"timestamp": "", "text": line}

    def _resolve_emotion(self, timestamp: str, emotion_timeline: list[dict[str, Any]]) -> str:
        if not timestamp:
            return "neutral"
        for item in emotion_timeline:
            start = item.get("start", item.get("start_time", ""))
            end = item.get("end", item.get("end_time", ""))
            if start <= timestamp <= end:
                return str(item.get("emotion", "neutral"))
        return "neutral"

    def _resolve_reasoning_tags(self, text: str, reasoning_payload: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        lower_text = text.lower()
        for objection in reasoning_payload.get("objections", []):
            objection_type = str(objection.get("type", "")).strip()
            evidence = str(objection.get("evidence", "")).strip().lower()
            if objection_type and evidence and evidence[:40] in lower_text:
                tags.append(objection_type)
        intent_level = str(reasoning_payload.get("customer_intent", {}).get("level", "")).strip()
        if intent_level:
            tags.append(intent_level)
        for tag in reasoning_payload.get("reasoning_tags", []):
            tag_value = str(tag).strip()
            if tag_value:
                tags.append(tag_value)
        unique = []
        for tag in tags:
            if tag not in unique:
                unique.append(tag)
        return unique

    def _emotion_shift_detected(self, bucket: list[dict[str, str]], emotion_timeline: list[dict[str, Any]]) -> bool:
        if len(bucket) < MIN_CHUNK_LINES:
            return False
        first_timestamp = bucket[0]["timestamp"]
        last_timestamp = bucket[-1]["timestamp"]
        if not first_timestamp or not last_timestamp:
            return False
        first_emotion = self._resolve_emotion(first_timestamp, emotion_timeline)
        last_emotion = self._resolve_emotion(last_timestamp, emotion_timeline)
        return first_emotion != last_emotion

    def _normalize_timestamp(self, timestamp: str) -> str:
        minutes, seconds = timestamp.split(":", maxsplit=1)
        return f"{int(minutes):02d}:{seconds}"
