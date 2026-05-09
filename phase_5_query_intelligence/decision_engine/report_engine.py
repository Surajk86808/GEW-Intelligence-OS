from __future__ import annotations

from typing import Any


class ReportEngine:
    def build_report(self, result: dict[str, Any]) -> str:
        lines = [
            f"DECISION INTELLIGENCE REPORT: {result.get('query_name', '')}",
            f"Query: {result.get('query', '')}",
            f"Confidence: {result.get('confidence', 0)}",
            "",
            "[ANSWER]",
            str(result.get("answer", "")),
            "",
            "[FACTS]",
        ]
        facts = result.get("facts", [])
        lines.extend(f"- {fact}" for fact in facts) if facts else lines.append("No facts returned.")
        lines.extend(["", "[STRATEGIC INSIGHTS]"])
        insights = result.get("strategic_insights", [])
        lines.extend(f"- {insight}" for insight in insights) if insights else lines.append("No strategic insights returned.")
        lines.extend(["", "[CITATIONS]"])
        citations = result.get("citations", [])
        lines.extend(f"- {citation.get('citation_id')} {citation.get('reference')}" for citation in citations) if citations else lines.append("No citations returned.")
        return "\n".join(lines)

