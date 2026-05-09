from __future__ import annotations

from typing import Any


class CitationEngine:
    def build(self, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        citations = []
        for index, item in enumerate(evidence, start=1):
            citations.append(
                {
                    "citation_id": f"CIT-{index:03d}",
                    "call_id": item.get("call_id", ""),
                    "timestamp": item.get("timestamp", ""),
                    "chunk_id": item.get("chunk_id", ""),
                    "speaker": item.get("salesperson", "unknown"),
                    "emotion": item.get("emotion", "neutral"),
                    "reference": f"{item.get('call_id', '')}@{item.get('timestamp', '')}",
                }
            )
        return citations

