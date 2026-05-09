from __future__ import annotations

from typing import Any


class EvidenceEngine:
    def build_evidence_record(
        self,
        chunk: dict[str, Any],
        metadata: dict[str, Any],
        reasoning_payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "call_id": chunk["call_id"],
            "chunk_id": chunk["chunk_id"],
            "timestamp_start": chunk["start_time"],
            "timestamp_end": chunk["end_time"],
            "quote": chunk["text"],
            "emotion": chunk["emotion"],
            "reasoning_tags": chunk.get("reasoning_tags", []),
            "conversion_probability": reasoning_payload.get("conversion_probability", 0.0),
            "salesperson": metadata.get("salesperson", ""),
            "customer_id": metadata.get("customer_id", ""),
        }

    def attach_evidence(self, results: list[dict[str, Any]], evidence_lookup: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        attached = []
        seen_keys: set[str] = set()
        for result in results:
            chunk_id = result["chunk_id"]
            if chunk_id in seen_keys:
                continue
            seen_keys.add(chunk_id)
            enriched = dict(result)
            enriched["evidence"] = evidence_lookup.get(chunk_id, {})
            attached.append(enriched)
        return attached

