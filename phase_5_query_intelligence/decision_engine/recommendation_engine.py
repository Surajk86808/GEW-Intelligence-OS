from __future__ import annotations

from typing import Any


class RecommendationEngine:
    def recommend(self, query_type: str, analytics: dict[str, Any], evidence: list[dict[str, Any]]) -> list[str]:
        recommendations = []
        top_emotions = {item["label"] for item in analytics.get("top_emotions", [])}
        if "frustrated" in top_emotions or "angry" in top_emotions:
            recommendations.append("Prioritize de-escalation playbooks and proof-oriented follow-ups for emotionally tense conversations.")
        if query_type == "coaching_intelligence":
            recommendations.append("Use the cited conversations as coaching examples and compare handling patterns across salespeople.")
        if query_type == "strategic_analytics":
            recommendations.append("Review campaign-level messaging against the retrieved evidence before scaling spend.")
        if not recommendations and evidence:
            recommendations.append("Use the top cited calls as immediate review material for operational follow-up.")
        if not recommendations:
            recommendations.append("No strong recommendation available because evidence coverage was limited.")
        return recommendations

