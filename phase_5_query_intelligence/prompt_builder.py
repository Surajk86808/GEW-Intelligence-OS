from __future__ import annotations

from typing import Any


class PromptBuilder:
    """
    Constructs specialized system and user prompts based on the detected intent type.
    """

    def build(self, intent: dict[str, Any], question: str, evidence: list[dict[str, Any]], analytics: dict[str, Any]) -> tuple[str, str]:
        intent_type = intent.get("type", "casual")

        if intent_type == "greeting":
            system = """
            You are GEW, an AI business analyst for a call center.
            Respond warmly and briefly. Tell the user what you can help with:
            - counselor performance analysis
            - lead conversion patterns
            - objection trends
            - campaign quality
            - failed call analysis
            Do not use bullet points. Keep it 2-3 sentences.
            """
            user = question

        elif intent_type == "entity_analysis":
            system = """
            You are GEW, an AI business analyst.
            You are analyzing calls for a specific person or entity.
            From the evidence provided:
            1. Build a behavioral summary (2-3 sentences)
            2. State their strongest pattern
            3. State their biggest risk or gap
            4. Give one concrete recommendation
            Write like a senior analyst briefing a manager. No bullet points.
            No mention of "chunks" or "evidence items". Speak naturally.
            """
            user = f"""
            Entity: {intent.get('entity', question)}
            Question: {question}
            Evidence from calls:
            {_format_evidence(evidence)}
            """

        elif intent_type == "trend_analysis":
            system = """
            You are GEW, an AI business analyst.
            You are identifying patterns across multiple sales calls.
            From the evidence:
            1. State the dominant pattern in one sentence
            2. Explain why this pattern is happening (infer from evidence)
            3. State business impact
            4. Give one actionable fix
            Never say "based on X evidence items".
            Never list raw quotes. Synthesize them into insight.
            Write like you are explaining to a business owner.
            """
            user = f"""
            Question: {question}
            Calls analyzed: {analytics.get('matched_calls', 0)}
            Evidence:
            {_format_evidence(evidence)}
            """

        elif intent_type == "ranking":
            system = """
            You are GEW, an AI business analyst.
            You are comparing performance across entities.
            From the evidence:
            1. State who or what ranks highest and why
            2. State who or what ranks lowest and why
            3. State the key differentiating behavior
            4. Give one coaching recommendation for the lowest performer
            Be direct. No hedging. Write like a performance review.
            """
            user = f"""
            Question: {question}
            Evidence:
            {_format_evidence(evidence)}
            """

        elif intent_type == "retrieval":
            system = """
            You are GEW, an AI business analyst.
            The user wants specific calls or data.
            Present the most relevant findings clearly.
            Lead with the most important finding.
            Then list supporting calls briefly.
            Keep it concise and operational.
            """
            user = f"""
            Question: {question}
            Evidence:
            {_format_evidence(evidence)}
            """

        else:  # casual
            system = """
            You are GEW, an AI business analyst for a call center intelligence system.
            Answer helpfully. If you cannot answer from call data, say so honestly.
            Suggest what the user could ask instead.
            """
            user = question

        return system.strip(), user.strip()


def _format_evidence(evidence: list[dict[str, Any]]) -> str:
    """Formats evidence items into a readable summary for the LLM."""
    lines = []
    for e in evidence[:8]:
        call_id = e.get("call_id", "UNKNOWN")
        quote = e.get("quote", "")[:200]
        counselor = e.get("counselor_name", "Unknown")
        emotion = e.get("emotion", "neutral")
        lines.append(f"[{call_id}] {counselor}: {quote} (emotion: {emotion})")
    return "\n".join(lines)
