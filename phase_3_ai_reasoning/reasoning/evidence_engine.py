from __future__ import annotations

from typing import Any

from shared.json_utils import write_json


class EvidenceEngine:
    def validate_analysis(self, analysis: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        for required_key in (
            "customer_intent",
            "objections",
            "sales_agent_analysis",
            "engagement_analysis",
            "emotional_insights",
            "follow_up_recommendation",
            "conversion_probability",
            "evidence",
            "risk_flags",
            "strategic_summary",
        ):
            if required_key not in analysis:
                issues.append(f"Missing required field: {required_key}")

        for evidence_item in analysis.get("evidence", []):
            if not evidence_item.get("quote") or not evidence_item.get("timestamp"):
                issues.append("Evidence item missing quote or timestamp")
        return issues

    def normalize_evidence(self, analysis: dict[str, Any], fallback_emotion: str = "neutral") -> dict[str, Any]:
        normalized = []
        for item in analysis.get("evidence", []):
            normalized.append(
                {
                    "insight": item.get("insight", ""),
                    "timestamp": item.get("timestamp", ""),
                    "quote": item.get("quote", ""),
                    "emotion": item.get("emotion", fallback_emotion),
                    "confidence": _clamp(item.get("confidence", 0.0)),
                }
            )
        analysis["evidence"] = normalized
        return analysis

    def export_evidence(self, output_path, evidence: list[dict[str, Any]]) -> None:
        write_json(output_path, evidence)

    def build_report(self, analysis: dict[str, Any]) -> str:
        lines = [
            f"AI REASONING REPORT: {analysis.get('call_id', '')}",
            f"Intent Level: {analysis.get('customer_intent', {}).get('level', 'unknown')}",
            f"Lead Quality Score: {analysis.get('lead_quality_score', 0)}",
            f"Conversion Probability: {analysis.get('conversion_probability', 0)}",
            "",
            "[STRATEGIC SUMMARY]",
            str(analysis.get("strategic_summary", "")),
            "",
            "[RISK FLAGS]",
        ]
        risk_flags = analysis.get("risk_flags", [])
        lines.extend(f"- {flag}" for flag in risk_flags) if risk_flags else lines.append("No major risk flags.")
        lines.extend(
            [
                "",
                "[OBJECTIONS]",
            ]
        )
        objections = analysis.get("objections", [])
        if objections:
            for objection in objections:
                lines.append(
                    f"- {objection.get('timestamp', '')} | {objection.get('type', 'other')} | {objection.get('evidence', '')} | emotion={objection.get('emotion_context', 'neutral')}"
                )
        else:
            lines.append("No major objections detected.")
        lines.extend(
            [
                "",
                "[FOLLOW UP]",
                str(analysis.get("follow_up_recommendation", {})),
            ]
        )
        return "\n".join(lines)


def _clamp(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except Exception:
        return 0.0

