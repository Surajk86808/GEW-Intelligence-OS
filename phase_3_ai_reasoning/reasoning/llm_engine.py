from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from reasoning.config import GEMINI_API_KEY, LLM_PROVIDER, LLM_TEMPERATURE, PRIMARY_LLM_MODEL
from shared.retry_utils import retry_on_transient_errors


@dataclass
class LLMResponse:
    payload: dict[str, Any]
    raw_text: str
    model_name: str
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None


class Provider(Protocol):
    def analyze(self, system_prompt: str, user_payload: str) -> LLMResponse:
        ...


class GeminiProvider:
    def __init__(self) -> None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        from google import genai
        from google.genai import types

        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.config = types.GenerateContentConfig(
            temperature=LLM_TEMPERATURE,
            response_mime_type="application/json",
        )
        self.model_name = PRIMARY_LLM_MODEL

    @retry_on_transient_errors()
    def analyze(self, system_prompt: str, user_payload: str) -> LLMResponse:
        from google.genai import types
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=f"{system_prompt}\n\n--- INPUT DATA ---\n{user_payload}",
            config=self.config
        )
        response_text = (response.text or "").strip()
        if response_text.startswith("```json"):
            response_text = response_text.removeprefix("```json").removesuffix("```").strip()
        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"LLM returned invalid JSON. Content: {response.text}") from exc

        usage = getattr(response, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        output_tokens = getattr(usage, "candidates_token_count", None) if usage else None
        estimated_cost = _estimate_gemini_cost(input_tokens, output_tokens)
        return LLMResponse(
            payload=payload,
            raw_text=response_text,
            model_name=self.model_name,
            provider="gemini",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost,
        )


class LLMEngine:
    def __init__(self) -> None:
        self.provider = self._build_provider()

    def analyze(self, system_prompt: str, user_payload: str) -> LLMResponse:
        return self.provider.analyze(system_prompt, user_payload)

    def _build_provider(self) -> Provider:
        if LLM_PROVIDER == "gemini":
            return GeminiProvider()
        if LLM_PROVIDER in {"claude", "openai", "local"}:
            raise RuntimeError(f"LLM provider '{LLM_PROVIDER}' is not implemented yet, but the architecture supports adding it cleanly.")
        raise RuntimeError(f"Unsupported LLM provider: {LLM_PROVIDER}")


def _estimate_gemini_cost(input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None and output_tokens is None:
        return None
    # Conservative placeholder estimate for observability only.
    input_cost = (input_tokens or 0) * 0.00000125
    output_cost = (output_tokens or 0) * 0.000005
    return round(input_cost + output_cost, 6)

