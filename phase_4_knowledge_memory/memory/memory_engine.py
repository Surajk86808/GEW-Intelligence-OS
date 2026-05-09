from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import (
    CALL_MANIFEST_CANDIDATES,
    DIRECT_ENRICHED_TRANSCRIPT_DIR_CANDIDATES,
    EMOTION_MANIFEST_CANDIDATES,
    INPUTS_CRM_DIR,
    INPUTS_EMOTIONS_DIR,
    INPUTS_REASONING_DIR,
    INPUTS_TRANSCRIPTS_DIR,
    LEAD_PROFILE_DIR_CANDIDATES,
    REASONING_MANIFEST_CANDIDATES,
    TRANSCRIPT_MANIFEST_CANDIDATES,
)
from shared.json_utils import read_json


class MemoryEngine:
    def load_inputs(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        local_inputs = self._load_local_phase_inputs()
        transcripts = self._read_first(TRANSCRIPT_MANIFEST_CANDIDATES, [])
        direct_records = self._load_direct_enriched_records()
        if not transcripts and direct_records:
            transcripts = self._build_transcript_entries(direct_records)

        reasoning = self._read_first(REASONING_MANIFEST_CANDIDATES, [])
        if not reasoning:
            reasoning = self._build_reasoning_entries(direct_records) if direct_records else []

        emotions = self._read_first(EMOTION_MANIFEST_CANDIDATES, [])
        calls = self._read_first(CALL_MANIFEST_CANDIDATES, [])
        if not calls and direct_records:
            calls = self._build_call_entries(direct_records)

        reasoning_by_call = {
            self._normalize_call_id(item): item
            for item in reasoning
            if isinstance(item, dict) and self._normalize_call_id(item)
        }

        if local_inputs is None:
            return transcripts, list(reasoning_by_call.values()), emotions, calls

        local_transcripts, local_reasoning, local_emotions, local_calls = local_inputs
        transcripts = self._merge_entries(transcripts, local_transcripts)
        reasoning = self._merge_entries(list(reasoning_by_call.values()), local_reasoning)
        emotions = self._merge_entries(emotions, local_emotions)
        calls = self._merge_entries(calls, local_calls)
        return transcripts, reasoning, emotions, calls

    def load_lead_profile(self, lead_number: str) -> dict[str, Any]:
        for directory in LEAD_PROFILE_DIR_CANDIDATES:
            if not directory.exists():
                continue
            payload = read_json(directory / f"lead_{lead_number}.json", default=None)
            if payload:
                return payload
        return {}

    def _read_first(self, candidates: list[Path], default: Any) -> Any:
        for candidate in candidates:
            payload = read_json(candidate, default=None)
            if payload:
                return payload
        return default

    def load_unified_input(self, path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        payload = read_json(path, default={}) or {}
        if not isinstance(payload, dict):
            payload = {}

        call_id = self._normalize_call_id(payload, fallback=path.stem)
        document_text = self._extract_indexable_text(payload)
        transcript_data = {
            "call_id": call_id,
            "transcript": document_text,
            "counselor_name": str(payload.get("counselor_name", "")).strip(),
            "call_duration_seconds": payload.get("call_duration_seconds", 0),
            "source_kind": "transcript" if str(payload.get("transcript", "")).strip() else "structured_document",
        }
        emotion_data = {
            "call_id": call_id,
            "engagement_score": payload.get("call_quality_analysis", {}).get("engagement_score", 0),
            "dominant_emotion": payload.get("caller_behavior", {}).get("dominant_emotion", "neutral"),
            "frustration_detected": payload.get("caller_behavior", {}).get("frustration_detected", False),
            "hesitation_detected": payload.get("caller_behavior", {}).get("hesitation_detected", False),
            "dialogue_exchange_count": payload.get("call_quality_analysis", {}).get("dialogue_exchange_count", 0),
        }
        reasoning_data = {
            "call_id": call_id,
            "conversion_probability": payload.get("conversion_analysis", {}).get("probability", 0),
            "conversion_signal": payload.get("conversion_analysis", {}).get("signal", ""),
            "funnel_stage": payload.get("conversion_analysis", {}).get("funnel_stage", ""),
            "sales_stage": payload.get("business_impact", {}).get("sales_stage", ""),
            "outcome": payload.get("call_summary", {}).get("outcome", ""),
            "follow_up_required": payload.get("call_summary", {}).get("follow_up_required", False),
            "one_line_summary": payload.get("call_summary", {}).get("one_line_summary", ""),
            "recommended_next_action": payload.get("recommended_next_action", {}),
        }
        crm_data = {
            "call_id": call_id,
            "counselor_name": str(payload.get("counselor_name", "")).strip(),
            "exam_targets": payload.get("exam_targets_detected", []),
            "locations": payload.get("locations_mentioned", []),
            "conversation_type": payload.get("conversation_type", {}).get("primary_category", ""),
            "priority_score": payload.get("conversation_pattern", {}).get("priority_score", 0),
        }
        return transcript_data, emotion_data, reasoning_data, crm_data

    def _load_local_phase_inputs(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]] | None:
        unified_paths = [
            path
            for path in sorted(INPUTS_TRANSCRIPTS_DIR.glob("*.json"))
            if path.name not in {"transcript_manifest.json", "reasoning_manifest.json", "emotion_manifest.json", "call_manifest.json"}
        ]
        if not unified_paths:
            return None

        transcripts: list[dict[str, Any]] = []
        emotions: list[dict[str, Any]] = []
        reasoning: list[dict[str, Any]] = []
        calls: list[dict[str, Any]] = []

        for transcript_path in unified_paths:
            transcript_data, emotion_data, reasoning_data, crm_data = self.load_unified_input(transcript_path)
            call_id = transcript_data["call_id"]
            if not call_id:
                continue

            emotion_path = INPUTS_EMOTIONS_DIR / f"{call_id}.json"
            reasoning_path = INPUTS_REASONING_DIR / f"{call_id}.json"
            crm_path = INPUTS_CRM_DIR / f"{call_id}.json"

            emotion_payload = self._merge_payloads(emotion_data, read_json(emotion_path, default={}) if emotion_path.exists() else {})
            reasoning_payload = self._merge_payloads(reasoning_data, read_json(reasoning_path, default={}) if reasoning_path.exists() else {})
            crm_payload = self._merge_payloads(crm_data, read_json(crm_path, default={}) if crm_path.exists() else {})

            transcripts.append(
                {
                    "call_id": call_id,
                    "source_path": str(transcript_path),
                    "output_path": str(transcript_path),
                    "transcript_text": transcript_data.get("transcript", ""),
                    "counselor_name": transcript_data.get("counselor_name", ""),
                    "call_duration_seconds": transcript_data.get("call_duration_seconds", 0),
                    "source_kind": transcript_data.get("source_kind", "transcript"),
                }
            )
            emotions.append(
                {
                    "call_id": call_id,
                    "source_path": str(emotion_path if emotion_path.exists() else transcript_path),
                    "output_path": str(emotion_path if emotion_path.exists() else transcript_path),
                    "payload": emotion_payload,
                }
            )
            reasoning.append(
                {
                    "call_id": call_id,
                    "source_path": str(reasoning_path if reasoning_path.exists() else transcript_path),
                    "output_path": str(reasoning_path if reasoning_path.exists() else transcript_path),
                    "payload": reasoning_payload,
                }
            )
            calls.append(
                {
                    "call_id": call_id,
                    "lead_number": str(crm_payload.get("lead_number", "")).strip(),
                    "owner": str(crm_payload.get("owner", crm_payload.get("counselor_name", ""))).strip(),
                    "campaign": str(crm_payload.get("campaign", "")).strip(),
                    "walkin_status": str(crm_payload.get("walkin_status", "")).strip(),
                    "recording_url": str(crm_payload.get("recording_url", "")).strip(),
                    "duration": crm_payload.get("duration", transcript_data.get("call_duration_seconds", 0)),
                    "exam_targets": crm_payload.get("exam_targets", []),
                    "locations": crm_payload.get("locations", []),
                    "conversation_type": crm_payload.get("conversation_type", ""),
                    "priority_score": crm_payload.get("priority_score", 0),
                    "source_path": str(crm_path if crm_path.exists() else transcript_path),
                    "payload": crm_payload,
                }
            )

        return transcripts, reasoning, emotions, calls

    def _merge_entries(self, manifest_entries: list[dict[str, Any]], local_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for entry in manifest_entries:
            call_id = self._normalize_call_id(entry)
            if call_id:
                merged[call_id] = entry
        for entry in local_entries:
            call_id = self._normalize_call_id(entry)
            if call_id:
                merged[call_id] = entry
        return list(merged.values())

    def _merge_payloads(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        if not isinstance(override, dict):
            return merged
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._merge_payloads(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _load_direct_enriched_records(self) -> list[dict[str, Any]]:
        for directory in DIRECT_ENRICHED_TRANSCRIPT_DIR_CANDIDATES:
            if not directory.exists():
                continue
            records = []
            for json_path in sorted(directory.glob("*.json")):
                payload = read_json(json_path, default=None)
                if not isinstance(payload, dict):
                    continue
                payload["_source_path"] = str(json_path)
                records.append(payload)
            if records:
                return records
        return []

    def _build_transcript_entries(self, direct_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        entries = []
        for item in direct_records:
            call_id = self._normalize_call_id(item)
            transcript_text = self._extract_indexable_text(item)
            if not call_id or not transcript_text:
                continue
            entries.append(
                {
                    "call_id": call_id,
                    "source_path": str(item.get("_source_path", "")),
                    "output_path": str(item.get("_source_path", "")),
                    "transcript_text": transcript_text,
                    "source_kind": "transcript" if str(item.get("transcript", "")).strip() else "structured_document",
                }
            )
        return entries

    def _build_reasoning_entries(self, direct_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        entries = []
        for item in direct_records:
            call_id = self._normalize_call_id(item)
            source_path = str(item.get("_source_path", "")).strip()
            if not call_id or not source_path:
                continue
            entries.append({"call_id": call_id, "output_path": source_path, "source_path": source_path})
        return entries

    def _build_call_entries(self, direct_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        entries = []
        for item in direct_records:
            call_id = self._normalize_call_id(item)
            if not call_id:
                continue
            entries.append(
                {
                    "call_id": call_id,
                    "lead_number": "",
                    "owner": str(item.get("counselor_name", "")).strip(),
                    "campaign": "",
                    "walkin_status": "",
                    "recording_url": "",
                    "duration": item.get("call_duration_seconds", ""),
                }
            )
        return entries

    def _normalize_call_id(self, item: dict[str, Any], fallback: str = "") -> str:
        raw_call_id = str(item.get("call_id", "")).strip()
        if raw_call_id:
            return raw_call_id.removesuffix(".mp3").strip()
        source_path = str(item.get("_source_path", "")).strip()
        if source_path:
            return Path(source_path).stem.replace(".mp3", "")
        return fallback.replace(".mp3", "").strip()

    def _extract_indexable_text(self, payload: dict[str, Any]) -> str:
        transcript_text = str(payload.get("transcript", "")).strip()
        if transcript_text:
            return transcript_text

        lines = self._flatten_payload(payload)
        return "\n".join(line for line in lines if line.strip())

    def _flatten_payload(self, value: Any, prefix: str = "") -> list[str]:
        if isinstance(value, dict):
            lines: list[str] = []
            for key, item in value.items():
                label = key.replace("_", " ").strip()
                next_prefix = f"{prefix} {label}".strip()
                nested = self._flatten_payload(item, next_prefix)
                if nested:
                    lines.extend(nested)
                elif item not in ({}, [], "", None):
                    lines.append(f"{next_prefix}: {item}".strip())
            return lines

        if isinstance(value, list):
            lines = []
            for index, item in enumerate(value, start=1):
                item_prefix = f"{prefix} item {index}".strip()
                nested = self._flatten_payload(item, item_prefix)
                if nested:
                    lines.extend(nested)
                elif item not in ("", None, {}, []):
                    lines.append(f"{item_prefix}: {item}".strip())
            return lines

        if value in ("", None):
            return []
        return [f"{prefix}: {value}".strip(": ").strip()]
