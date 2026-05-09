from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from shared.transcript_utils import (
    normalize_segments,
    parse_transcript_block,
    build_structured_transcript,
)
from enrichment.config import CALL_MANIFEST_CANDIDATES, LEAD_PROFILES_DIR_CANDIDATES
from shared.json_utils import read_json


class TranscriptEnrichmentEngine:
    def __init__(self) -> None:
        self.call_manifest_lookup = self._load_call_manifest_lookup()
        self.lead_profiles_lookup = self._load_lead_profiles_lookup()

    def enrich(
        self,
        call_id: str,
        transcript_path: Path,
        transcript_format: str,
        *,
        transcript_source: str = "",
        reviewed: bool = False,
        enrichment_level: str = "medium",
        pipeline_stage: str = "phase_3",
    ) -> dict[str, Any]:
        payload = self._load_payload(call_id, transcript_path, transcript_format)
        manifest_context = self.call_manifest_lookup.get(call_id, {})
        lead_number = str(manifest_context.get("lead_number", "")).strip()
        lead_profile = self.lead_profiles_lookup.get(lead_number, {})

        # If transcript is a string, it means it was a pre-enriched JSON with a raw text field
        if isinstance(payload.get("transcript"), str):
            raw_text = payload["transcript"]
            payload["transcript"] = self._parse_text_transcript(call_id, raw_text)

        transcript_segments = [self._enrich_segment(segment) for segment in payload.get("transcript", [])]
        payload["transcript"] = transcript_segments
        payload["participants"] = payload.get("participants", {})
        payload["crm_context"] = {
            "lead_number": lead_number,
            "owner": str(manifest_context.get("owner", "")).strip(),
            "campaign": str(manifest_context.get("campaign", "")).strip(),
            "walkin_status": str(manifest_context.get("walkin_status", "")).strip(),
            "lead_profile_available": bool(lead_profile),
        }
        
        # Merge existing intelligence if present
        intelligence = self._build_conversation_intelligence(transcript_segments)
        existing_intelligence = payload.get("conversation_intelligence", {})
        if isinstance(existing_intelligence, dict):
            intelligence.update(existing_intelligence)
        payload["conversation_intelligence"] = intelligence

        metadata = dict(payload.get("metadata", {}))
        metadata.update(
            {
                "call_id": call_id,
                "crm_enriched": bool(payload["crm_context"]["lead_profile_available"] or lead_number),
                "transcript_enriched": True,
                "transcript_format": transcript_format,
                "fidelity_preserved": True,
            }
        )
        payload["metadata"] = metadata
        payload["source_tracking"] = self._build_source_tracking(
            transcript_path=transcript_path,
            transcript_format=transcript_format,
            transcript_source=transcript_source,
            reviewed=reviewed,
            enrichment_level=enrichment_level,
            pipeline_stage=pipeline_stage,
            existing=payload.get("source_tracking", {}),
        )
        return payload

    def _load_payload(self, call_id: str, transcript_path: Path, transcript_format: str) -> dict[str, Any]:
        if transcript_path.suffix.lower() == ".json":
            payload = read_json(transcript_path, default={}) or {}
            payload.setdefault("metadata", {})
            payload.setdefault("participants", {})
            payload.setdefault("transcript", [])
            return payload

        raw_text = transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else ""
        segments = self._parse_text_transcript(call_id, raw_text)
        manifest_context = self.call_manifest_lookup.get(call_id, {})
        payload = build_structured_transcript(
            call_id,
            segments,
            source="external_transcript" if transcript_format != "normalized_txt" else "normalized_transcript",
            transcript_origin=transcript_format,
            source_path=str(transcript_path),
            audio_path=str(manifest_context.get("audio_path", "")).strip(),
            manifest_context=manifest_context,
        )
        return payload

    def _build_source_tracking(
        self,
        *,
        transcript_path: Path,
        transcript_format: str,
        transcript_source: str,
        reviewed: bool,
        enrichment_level: str,
        pipeline_stage: str,
        existing: Any,
    ) -> dict[str, Any]:
        existing = dict(existing or {})
        origin = existing.get("origin")
        if not origin:
            if reviewed:
                origin = "manual_review"
            elif transcript_source in {"enriched_json", "external_imports"}:
                origin = "external_import"
            else:
                origin = transcript_format
        return {
            "origin": origin,
            "pipeline_stage": existing.get("pipeline_stage", pipeline_stage),
            "source_file": str(transcript_path),
            "reviewed": bool(existing.get("reviewed", reviewed)),
            "enrichment_level": str(existing.get("enrichment_level", enrichment_level)),
            "transcript_source": transcript_source,
            "transcript_format": transcript_format,
        }

    def _parse_text_transcript(self, call_id: str, raw_text: str) -> list[dict[str, Any]]:
        if re.search(r"^\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}:", raw_text, flags=re.MULTILINE):
            return normalize_segments(parse_transcript_block(call_id, raw_text))
        return self._parse_normalized_text(raw_text)

    def _parse_normalized_text(self, raw_text: str) -> list[dict[str, Any]]:
        pattern = re.compile(
            r"^\[(?P<start>\d{2}:\d{2})(?:\s*-\s*(?P<end>\d{2}:\d{2}))?\]\s*(?:(?P<label>[^:]+?)\s*:\s*)?(?P<text>.*)$"
        )
        segments: list[dict[str, Any]] = []
        for index, line in enumerate(raw_text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            match = pattern.match(stripped)
            if not match:
                continue
            start_time = match.group("start")
            end_time = match.group("end") or start_time
            label = (match.group("label") or "Unknown").strip()
            text = match.group("text").strip()
            segments.append(
                {
                    "segment_id": index,
                    "timestamp": f"[{start_time} - {end_time}]",
                    "start_time": start_time,
                    "end_time": end_time,
                    "type": "dialogue",
                    "speaker": _classify_label(label),
                    "speaker_name": None,
                    "speaker_label": label,
                    "emotion": None,
                    "text": text,
                }
            )
        return segments

    def _enrich_segment(self, segment: dict[str, Any]) -> dict[str, Any]:
        if segment.get("type") != "dialogue":
            return dict(segment)
        enriched = dict(segment)
        text_lower = str(segment.get("text", "")).lower()
        enriched.setdefault("emotion", _infer_emotion(text_lower))
        enriched["intent"] = _classify_intent(text_lower)
        enriched["interaction_tag"] = _classify_interaction_tag(text_lower, str(segment.get("speaker", "")))
        return enriched

    def _build_conversation_intelligence(self, segments: list[dict[str, Any]]) -> dict[str, Any]:
        intents = [segment.get("intent") for segment in segments if segment.get("intent") and segment.get("intent") != "general_query"]
        caller_emotions = [str(segment.get("emotion")) for segment in segments if segment.get("speaker") == "Caller" and segment.get("emotion")]
        transcript_text = " ".join(str(segment.get("text", "")) for segment in segments)
        objections = []
        if "comfortable nahi" in transcript_text.lower() or "doori" in transcript_text.lower():
            objections.append("distance_concern")
        if "call aa jayega" in transcript_text.lower() or "share kar deti hoon" in transcript_text.lower():
            followup_required = True
        else:
            followup_required = False
        urgency_level = "high" if any(keyword in transcript_text.lower() for keyword in ["aaj", "abhi", "turant"]) else "low"
        primary_intent = intents[0] if intents else "general_query"
        conversion_signal = "positive" if any(
            keyword in transcript_text.lower()
            for keyword in ["visit", "demo", "join", "enrolled", "share your number", "guide kar degi"]
        ) else "neutral"
        return {
            "primary_intent": primary_intent,
            "customer_emotion_flow": caller_emotions or ["neutral"],
            "conversion_signal": conversion_signal,
            "followup_required": followup_required,
            "objections_detected": objections,
            "urgency_level": urgency_level,
        }

    def _load_call_manifest_lookup(self) -> dict[str, dict[str, Any]]:
        for candidate in CALL_MANIFEST_CANDIDATES:
            payload = read_json(candidate, default=None)
            if payload:
                return {
                    self._normalize_call_id(str(item.get("call_id", "")).strip()): item
                    for item in payload
                    if str(item.get("call_id", "")).strip()
                }
        return {}

    def _load_lead_profiles_lookup(self) -> dict[str, dict[str, Any]]:
        lookup: dict[str, dict[str, Any]] = {}
        for candidate_dir in LEAD_PROFILES_DIR_CANDIDATES:
            if not candidate_dir.exists():
                continue
            for path in candidate_dir.glob("lead_*.json"):
                payload = read_json(path, default={}) or {}
                lead_number = str(payload.get("lead_number", "")).strip()
                if lead_number:
                    lookup[lead_number] = payload
        return lookup

    def _normalize_call_id(self, raw_call_id: str) -> str:
        digits = "".join(character for character in raw_call_id if character.isdigit())
        if digits:
            return f"CALL_{digits.zfill(4)}"
        return raw_call_id.strip().upper()


def _classify_label(label: str) -> str:
    lowered = label.lower()
    if "caller" in lowered:
        return "Caller"
    if "counselor" in lowered or "recipient" in lowered:
        return "Counselor"
    return "Unknown"


def _infer_emotion(text_lower: str) -> str | None:
    if any(keyword in text_lower for keyword in ["thank you", "thik hai", "okay"]):
        return "neutral"
    if any(keyword in text_lower for keyword in ["help", "guide", "share kar", "inform"]):
        return "professional"
    if any(keyword in text_lower for keyword in ["nahi", "issue", "problem", "confused"]):
        return "hesitant"
    return None


def _classify_intent(text_lower: str) -> str:
    if "online team" in text_lower or "online department" in text_lower or "online classes" in text_lower:
        return "online_redirection"
    if "offline" in text_lower and "center" in text_lower:
        return "offline_center_inquiry"
    if "batch" in text_lower:
        return "batch_inquiry"
    if "library" in text_lower:
        return "facility_inquiry"
    if "judiciary" in text_lower or "jee" in text_lower or "neet" in text_lower:
        return "wrong_department_query"
    if "demo" in text_lower or "visit" in text_lower:
        return "center_visit_consideration"
    return "general_query"


def _classify_interaction_tag(text_lower: str, speaker: str) -> str:
    if speaker == "Counselor" and "share" in text_lower and "number" in text_lower:
        return "followup_commitment"
    if speaker == "Counselor" and "guide" in text_lower:
        return "guidance"
    if speaker == "Caller" and "chahiye" in text_lower:
        return "requirement_expression"
    if speaker == "Caller" and "kab tak" in text_lower:
        return "followup_timing_check"
    return "conversation_step"
