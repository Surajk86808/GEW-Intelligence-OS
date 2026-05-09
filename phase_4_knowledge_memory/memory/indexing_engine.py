from __future__ import annotations

from typing import Any


class IndexingEngine:
    def build_call_summary(self, chunk_records: list[dict[str, Any]]) -> dict[str, Any]:
        summary: dict[str, Any] = {}
        for record in chunk_records:
            call_id = record["call_id"]
            call_summary = summary.setdefault(
                call_id,
                {
                    "chunk_count": 0,
                    "emotions": {},
                    "reasoning_tags": {},
                    "salesperson": record.get("salesperson", ""),
                    "customer_id": record.get("customer_id", ""),
                },
            )
            call_summary["chunk_count"] += 1
            emotion = str(record.get("emotion", "neutral"))
            call_summary["emotions"][emotion] = call_summary["emotions"].get(emotion, 0) + 1
            for tag in record.get("reasoning_tags", []):
                call_summary["reasoning_tags"][tag] = call_summary["reasoning_tags"].get(tag, 0) + 1
        return summary

