from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedQuery:
    name: str
    raw_query: str
    query_type: str
    filters: dict[str, Any]
    search_text: str
    analysis_mode: str


class QueryParser:
    def parse(self, name: str, query: str) -> ParsedQuery:
        lower = query.lower()
        query_type = "general_intelligence"
        filters: dict[str, Any] = {}
        analysis_mode = "decision_support"

        if any(term in lower for term in ("pricing", "budget", "expensive", "price")):
            filters["reasoning_tags_any"] = ["pricing concern"]
            query_type = "sales_intelligence"
        if "competitor" in lower:
            filters.setdefault("reasoning_tags_any", []).append("competitor")
            query_type = "customer_analytics"
        if any(term in lower for term in ("frustrated", "angry", "hesitant", "interested", "disengaged")):
            emotion_terms = [term for term in ("frustrated", "angry", "hesitant", "interested", "disengaged", "confident", "excited") if term in lower]
            if emotion_terms:
                filters["emotion_any"] = emotion_terms
            query_type = "emotion_aware_intelligence"
        if "salesperson" in lower or "agent" in lower:
            query_type = "coaching_intelligence"
            analysis_mode = "comparison"
        if "campaign" in lower or "region" in lower:
            query_type = "strategic_analytics"
            analysis_mode = "comparison"
        if any(term in lower for term in ("compare", "best", "most", "which")) and query_type == "general_intelligence":
            analysis_mode = "comparative"

        return ParsedQuery(
            name=name,
            raw_query=query,
            query_type=query_type,
            filters=filters,
            search_text=query,
            analysis_mode=analysis_mode,
        )

