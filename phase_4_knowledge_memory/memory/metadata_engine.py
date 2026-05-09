from __future__ import annotations

from typing import Any

from .config import CALL_INDEX_PATH, CHUNK_STORE_PATH, CUSTOMER_INDEX_PATH, OBJECTION_INDEX_PATH, SALESPERSON_INDEX_PATH
from shared.json_utils import write_json


class MetadataEngine:
    def build_chunk_metadata(
        self,
        chunk: dict[str, Any],
        crm_context: dict[str, Any],
        phase3_payload: dict[str, Any],
        reasoning_payload: dict[str, Any],
    ) -> dict[str, Any]:
        lead_number = str(crm_context.get("lead_number", "")).strip()
        owner = str(crm_context.get("owner", "")).strip()
        campaign = str(crm_context.get("campaign", "")).strip()
        customer_id = lead_number or str(crm_context.get("call_id", "")).strip()
        return {
            "call_id": chunk["call_id"],
            "chunk_id": chunk["chunk_id"],
            "customer_id": customer_id,
            "salesperson": owner,
            "lead_source": campaign,
            "campaign": campaign,
            "emotion": chunk["emotion"],
            "reasoning_tags": chunk.get("reasoning_tags", []),
            "conversion_probability": _conversion_probability(reasoning_payload),
            "engagement_level": phase3_payload.get("engagement_score", 0.0),
            "start_time": chunk["start_time"],
            "end_time": chunk["end_time"],
            "crm_context": crm_context,
            "text": chunk["text"],
        }

    def persist_metadata(self, chunk_records: list[dict[str, Any]]) -> None:
        write_json(CHUNK_STORE_PATH, chunk_records)
        write_json(CALL_INDEX_PATH, self._group(chunk_records, "call_id"))
        write_json(CUSTOMER_INDEX_PATH, self._group(chunk_records, "customer_id"))
        write_json(SALESPERSON_INDEX_PATH, self._group(chunk_records, "salesperson"))
        write_json(OBJECTION_INDEX_PATH, self._group_tags(chunk_records))

    def _group(self, chunk_records: list[dict[str, Any]], key: str) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for record in chunk_records:
            value = str(record.get(key, "")).strip()
            if not value:
                continue
            grouped.setdefault(value, []).append(record["chunk_id"])
        return grouped

    def _group_tags(self, chunk_records: list[dict[str, Any]]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for record in chunk_records:
            for tag in record.get("reasoning_tags", []):
                grouped.setdefault(str(tag), []).append(record["chunk_id"])
        return grouped


def _conversion_probability(reasoning_payload: dict[str, Any]) -> float:
    if "conversion_probability" in reasoning_payload:
        try:
            return float(reasoning_payload.get("conversion_probability", 0.0))
        except (TypeError, ValueError):
            return 0.0
    conversion_analysis = reasoning_payload.get("conversion_analysis", {})
    if isinstance(conversion_analysis, dict):
        try:
            return float(conversion_analysis.get("probability", 0.0))
        except (TypeError, ValueError):
            return 0.0
    return 0.0
