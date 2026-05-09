from __future__ import annotations

from typing import Any


class RecommendationEngine:
    def enrich(self, analysis: dict[str, Any], phase3_payload: dict[str, Any]) -> dict[str, Any]:
        recommendations: list[str] = []
        if phase3_payload.get("stress_score", 0) > 0.7:
            recommendations.append("Reduce pressure in the follow-up and use reassurance-based messaging.")
        if phase3_payload.get("engagement_score", 0) < 0.4:
            recommendations.append("Use a short-value recap before the next outreach to rebuild engagement.")
        if analysis.get("objections"):
            recommendations.append("Address objections in the next follow-up with direct proof points and price framing.")
        if not recommendations:
            recommendations.append("Send a timely follow-up that reinforces momentum and confirms the next step.")

        analysis["follow_up_recommendation"] = {
            "priority": "high" if analysis.get("conversion_probability", 0) >= 0.65 else "medium",
            "recommended_actions": recommendations,
        }
        return analysis

