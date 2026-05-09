from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .config import GEMINI_API_KEY, LLM_PROVIDER, LLM_TEMPERATURE, PRIMARY_LLM_MODEL
from shared.retry_utils import retry_on_transient_errors


@dataclass
class ReasoningResponse:
    payload: dict[str, Any]
    provider: str
    model_name: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None


SYSTEM_PROMPT = """
You are the GEW Intelligence OS Phase 6 Decision Intelligence Engine.

Answer only with evidence-backed, traceable conclusions.
Use the retrieved evidence and analytics. Do not invent facts.
Separate factual observations from inference.
Return strict JSON:
{
  "answer": "string",
  "confidence": 0.0,
  "facts": ["string"],
  "inferences": ["string"],
  "strategic_insights": ["string"],
  "risk_alerts": ["string"]
}
"""


class ReasoningEngine:
    def __init__(self) -> None:
        self.provider = LLM_PROVIDER
        self.model_name = PRIMARY_LLM_MODEL
        self.model = None
        if self.provider == "gemini":
            self._init_gemini()

    def reason(self, query: str, analytics: dict[str, Any], evidence: list[dict[str, Any]]) -> ReasoningResponse:
        if not evidence:
            return ReasoningResponse(
                payload={
                    "answer": "Insufficient evidence to answer the query confidently.",
                    "confidence": 0.0,
                    "facts": [],
                    "inferences": [],
                    "strategic_insights": [],
                    "risk_alerts": ["Evidence coverage was insufficient for a grounded answer."],
                },
                provider="deterministic",
                model_name="deterministic-fallback",
            )

        if self.provider == "gemini":
            return self._reason_with_gemini(query, analytics, evidence)
        if self.provider == "deterministic":
            return self._deterministic_reasoning(query, analytics, evidence)
        if self.provider in {"claude", "openai", "local"}:
            raise RuntimeError(f"LLM provider '{self.provider}' is not implemented yet.")
        raise RuntimeError(f"Unsupported LLM provider: {self.provider}")

    def _init_gemini(self) -> None:
        if not GEMINI_API_KEY:
            self.provider = "deterministic"
            self.model_name = "deterministic-fallback"
            return
        from google import genai
        from google.genai import types

        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.config = types.GenerateContentConfig(
            temperature=LLM_TEMPERATURE,
            response_mime_type="application/json",
        )

    @retry_on_transient_errors()
    def _reason_with_gemini(self, query: str, analytics: dict[str, Any], evidence: list[dict[str, Any]]) -> ReasoningResponse:
        if self.client is None:
            return self._deterministic_reasoning(query, analytics, evidence)

        payload = json.dumps({"query": query, "analytics": analytics, "evidence": evidence}, indent=2, ensure_ascii=False)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=f"{SYSTEM_PROMPT}\n\n--- INPUT DATA ---\n{payload}",
            config=self.config
        )
        response_text = (response.text or "").strip()
        if response_text.startswith("```json"):
            response_text = response_text.removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(response_text)
        usage = getattr(response, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        output_tokens = getattr(usage, "candidates_token_count", None) if usage else None
        estimated_cost = _estimate_cost(input_tokens, output_tokens)
        return ReasoningResponse(
            payload=parsed,
            provider="gemini",
            model_name=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost,
        )

    def _deterministic_reasoning(self, query: str, analytics: dict[str, Any], evidence: list[dict[str, Any]]) -> ReasoningResponse:
        top = evidence[0]
        payload = {
            "answer": f"The strongest evidence for '{query}' comes from {len(evidence)} retrieved conversation segment(s), led by call {top.get('call_id', '')} at {top.get('timestamp', '')}.",
            "confidence": round(min(0.95, max(0.2, sum(float(item.get('relevance_score', 0.0)) for item in evidence[:5]) / max(len(evidence[:5]), 1))), 2),
            "facts": [f"{item.get('call_id', '')} {item.get('timestamp', '')}: {item.get('quote', '')}" for item in evidence[:3]],
            "inferences": [f"Emotion patterns surfaced: {', '.join(item['label'] for item in analytics.get('top_emotions', [])) or 'none'}."],
            "strategic_insights": ["Review the cited calls before making broader operational changes."],
            "risk_alerts": [],
        }
        return ReasoningResponse(payload=payload, provider="deterministic", model_name="deterministic-fallback")


def _estimate_cost(input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None and output_tokens is None:
        return None
    return round((input_tokens or 0) * 0.00000125 + (output_tokens or 0) * 0.000005, 6)

