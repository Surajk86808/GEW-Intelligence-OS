from __future__ import annotations

import re
from typing import Any

from .config import MAX_EVIDENCE_ITEMS

BRACKET_TIMESTAMP_PATTERN = re.compile(r"^\[(\d{2}:\d{2})\]")
RANGE_TIMESTAMP_PATTERN = re.compile(r"^(\d{1,2}:\d{2})\s*-\s*\d{1,2}:\d{2}:")


class EvidenceEngine:
    def build(self, retrieval_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        evidence = []
        for item in retrieval_results[:MAX_EVIDENCE_ITEMS]:
            metadata = item["metadata"]
            source = item.get("evidence", {})
            quote = source.get("quote", metadata.get("text", ""))
            timestamp = source.get("timestamp_start", metadata.get("start_time", "")) or self._extract_timestamp(str(quote)) or "unknown"
            evidence.append(
                {
                    "call_id": metadata.get("call_id", ""),
                    "timestamp": timestamp,
                    "quote": quote,
                    "emotion": source.get("emotion", metadata.get("emotion", "neutral")),
                    "salesperson": source.get("salesperson", metadata.get("salesperson", "")),
                    "customer_id": source.get("customer_id", metadata.get("customer_id", "")),
                    "relevance_score": item.get("score", 0.0),
                    "chunk_id": item.get("chunk_id", ""),
                }
            )
        return evidence

    def ensure_traceable(self, evidence: list[dict[str, Any]]) -> list[str]:
        issues = []
        for item in evidence:
            if not item.get("call_id") or not item.get("quote") or not item.get("timestamp"):
                issues.append("Evidence item missing call_id, quote, or timestamp")
        return issues

    def _extract_timestamp(self, quote: str) -> str:
        first_line = next((line.strip() for line in quote.splitlines() if line.strip()), "")
        bracket_match = BRACKET_TIMESTAMP_PATTERN.match(first_line)
        if bracket_match:
            return bracket_match.group(1)
        range_match = RANGE_TIMESTAMP_PATTERN.match(first_line)
        if range_match:
            minutes, seconds = range_match.group(1).split(":", maxsplit=1)
            return f"{int(minutes):02d}:{seconds}"
        return ""

