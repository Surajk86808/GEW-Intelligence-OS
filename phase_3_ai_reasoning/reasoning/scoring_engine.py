from __future__ import annotations

from typing import Any


class ScoringEngine:
    def score(self, analysis: dict[str, Any], phase3_payload: dict[str, Any], crm_context: dict[str, Any]) -> dict[str, Any]:
        objections = analysis.get("objections", [])
        engagement_score = _as_float(analysis.get("engagement_analysis", {}).get("engagement_score", phase3_payload.get("engagement_score", 0.0)))
        stress_score = _as_float(phase3_payload.get("stress_score", 0.0))
        intent_level = str(analysis.get("customer_intent", {}).get("level", "low")).lower()

        intent_weight = {
            "high intent": 0.9,
            "moderate intent": 0.7,
            "low intent": 0.35,
            "exploratory": 0.45,
            "negative": 0.1,
        }.get(intent_level, 0.3)

        objection_penalty = min(0.4, len(objections) * 0.06)
        trust_bonus = 0.05 if "walkin" in str(crm_context.get("walkin_status", "")).lower() else 0.0
        conversion_probability = max(0.0, min(1.0, intent_weight + (engagement_score * 0.2) - (stress_score * 0.2) - objection_penalty + trust_bonus))
        lead_quality_score = int(round(conversion_probability * 100))

        analysis["conversion_probability"] = round(conversion_probability, 2)
        analysis["lead_quality_score"] = lead_quality_score
        return analysis


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0

