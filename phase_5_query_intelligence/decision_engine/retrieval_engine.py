from __future__ import annotations

from typing import Any

from .config import MAX_RETRIEVAL_RESULTS


class RetrievalEngine:
    def __init__(self, vector_index: list[dict[str, Any]], evidence_lookup: dict[str, Any]) -> None:
        self.vector_index = vector_index
        self.evidence_lookup = evidence_lookup

    def retrieve(self, query: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        query_terms = {term.lower() for term in query.split() if term.strip()}
        scored: list[dict[str, Any]] = []
        for record in self.vector_index:
            metadata = record.get("metadata", {})
            if not _matches_filters(metadata, filters):
                continue
            text = str(metadata.get("text", "")).lower()
            keyword_hits = sum(1 for term in query_terms if term in text)
            score = float(keyword_hits) / max(len(query_terms), 1)
            reasoning_tags = {str(tag).lower() for tag in metadata.get("reasoning_tags", [])}
            score += min(0.25, 0.05 * sum(1 for term in query_terms if term in reasoning_tags))
            if score <= 0:
                continue
            scored.append(
                {
                    "chunk_id": record.get("chunk_id", ""),
                    "score": round(score, 6),
                    "metadata": metadata,
                    "evidence": self.evidence_lookup.get(record.get("chunk_id", ""), {}),
                }
            )
        scored.sort(key=lambda item: item["score"], reverse=True)
        deduped = []
        seen = set()
        for item in scored:
            key = (item["metadata"].get("call_id", ""), item["metadata"].get("start_time", ""), item["metadata"].get("text", ""))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= MAX_RETRIEVAL_RESULTS:
                break
        return deduped


def _matches_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
    if "reasoning_tags_any" in filters:
        tags = {str(tag).lower() for tag in metadata.get("reasoning_tags", [])}
        wanted = {str(tag).lower() for tag in filters["reasoning_tags_any"]}
        if not tags.intersection(wanted):
            return False
    if "emotion_any" in filters:
        if str(metadata.get("emotion", "")).lower() not in {str(value).lower() for value in filters["emotion_any"]}:
            return False
    return True

