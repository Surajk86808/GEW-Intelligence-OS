from __future__ import annotations

from pathlib import Path
from typing import Any

from reasoning.config import CALL_MANIFEST_CANDIDATES, LEAD_PROFILE_DIR_CANDIDATES
from shared.json_utils import read_json


class CRMEngine:
    def load_call_manifest(self) -> list[dict[str, Any]]:
        for candidate in CALL_MANIFEST_CANDIDATES:
            payload = read_json(candidate, default=None)
            if payload:
                return payload
        return []

    def load_lead_profile(self, lead_number: str) -> dict[str, Any]:
        for directory in LEAD_PROFILE_DIR_CANDIDATES:
            if not directory.exists():
                continue
            path = directory / f"lead_{lead_number}.json"
            payload = read_json(path, default=None)
            if payload:
                return payload
        return {}

    def build_crm_context(self, call_entry: dict[str, Any]) -> dict[str, Any]:
        lead_number = str(call_entry.get("lead_number", "")).strip()
        lead_profile = self.load_lead_profile(lead_number) if lead_number else {}
        return {
            "call_id": str(call_entry.get("call_id", "")).strip(),
            "lead_number": lead_number,
            "owner": str(call_entry.get("owner", "")).strip(),
            "campaign": str(call_entry.get("campaign", "")).strip(),
            "walkin_status": str(call_entry.get("walkin_status", "")).strip(),
            "recording_url": str(call_entry.get("recording_url", "")).strip(),
            "duration": call_entry.get("duration", ""),
            "lead_profile": lead_profile,
        }

