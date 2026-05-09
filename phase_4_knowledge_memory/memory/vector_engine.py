from __future__ import annotations

import math
from typing import Any

from .config import VECTOR_INDEX_PATH
from shared.json_utils import read_json, write_json


class VectorEngine:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = read_json(VECTOR_INDEX_PATH, default=[]) or []

    def upsert(self, chunk_id: str, vector: list[float], metadata: dict[str, Any]) -> None:
        payload = {"chunk_id": chunk_id, "vector": vector, "metadata": metadata}
        for index, record in enumerate(self.records):
            if record["chunk_id"] == chunk_id:
                self.records[index] = payload
                return
        self.records.append(payload)

    def search(self, query_vector: list[float], top_k: int, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        for record in self.records:
            metadata = record["metadata"]
            if filters and not _matches_filters(metadata, filters):
                continue
            score = cosine_similarity(query_vector, record["vector"])
            matches.append(
                {
                    "chunk_id": record["chunk_id"],
                    "score": round(score, 6),
                    "metadata": metadata,
                }
            )
        matches.sort(key=lambda item: item["score"], reverse=True)
        return matches[:top_k]

    def persist(self) -> None:
        write_json(VECTOR_INDEX_PATH, self.records)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _matches_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
    if "reasoning_tags_any" in filters:
        tags = set(metadata.get("reasoning_tags", []))
        if not tags.intersection(filters["reasoning_tags_any"]):
            return False
    if "emotion_any" in filters:
        if metadata.get("emotion") not in filters["emotion_any"]:
            return False
    if "min_conversion_probability" in filters:
        if float(metadata.get("conversion_probability", 0.0)) < float(filters["min_conversion_probability"]):
            return False
    if "campaign" in filters:
        if str(metadata.get("campaign", "")).strip().lower() != str(filters["campaign"]).strip().lower():
            return False
    if "salesperson" in filters:
        if str(metadata.get("salesperson", "")).strip().lower() != str(filters["salesperson"]).strip().lower():
            return False
    if "customer_id" in filters:
        if str(metadata.get("customer_id", "")).strip() != str(filters["customer_id"]).strip():
            return False
    return True
