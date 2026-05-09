from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from reasoning.config import CACHE_DIR, DEFAULT_INPUT_HASH_VERSION, PROMPTS_DIR, RESPONSE_CACHE_ENABLED
from reasoning.crm_engine import CRMEngine
from reasoning.llm_engine import LLMEngine, LLMResponse
from reasoning.retrieval_engine import RetrievalEngine
from shared.json_utils import read_json, write_json


class ReasoningEngine:
    def __init__(self) -> None:
        self.llm = LLMEngine()
        self.crm_engine = CRMEngine()
        self.retrieval_engine = RetrievalEngine()
        self.system_prompt = (PROMPTS_DIR / "system_prompt.txt").read_text(encoding="utf-8")

    def analyze_call(
        self,
        call_id: str,
        transcript_path: Path,
        phase3_json_path: Path,
        crm_context: dict[str, Any],
    ) -> tuple[dict[str, Any], LLMResponse]:
        transcript_text = transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else ""
        phase3_payload = read_json(phase3_json_path, default={}) if phase3_json_path.exists() else {}
        retrieved_chunks = self.retrieval_engine.retrieve(
            call_id,
            transcript_text,
            self._build_search_terms(crm_context, phase3_payload),
        )
        payload = self._compile_payload(call_id, transcript_text, phase3_payload, crm_context, retrieved_chunks)
        cached = self._load_cache(call_id, payload)
        if cached:
            return cached["analysis"], LLMResponse(
                payload=cached["analysis"],
                raw_text=json.dumps(cached["analysis"], ensure_ascii=False),
                model_name=cached.get("model_name", "cache"),
                provider=cached.get("provider", "cache"),
                input_tokens=cached.get("input_tokens"),
                output_tokens=cached.get("output_tokens"),
                estimated_cost_usd=cached.get("estimated_cost_usd"),
            )

        response = self.llm.analyze(self.system_prompt, payload)
        analysis = response.payload
        self._save_cache(
            call_id,
            payload,
            {
                "analysis": analysis,
                "model_name": response.model_name,
                "provider": response.provider,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "estimated_cost_usd": response.estimated_cost_usd,
            },
        )
        return analysis, response

    def _compile_payload(
        self,
        call_id: str,
        transcript_text: str,
        phase3_payload: dict[str, Any],
        crm_context: dict[str, Any],
        retrieved_chunks: list[dict[str, Any]],
    ) -> str:
        payload = {
            "call_id": call_id,
            "crm_context": crm_context,
            "voice_intelligence": phase3_payload,
            "retrieved_transcript_chunks": retrieved_chunks,
            "transcript": transcript_text,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _build_search_terms(self, crm_context: dict[str, Any], phase3_payload: dict[str, Any]) -> list[str]:
        terms = [
            str(crm_context.get("campaign", "")),
            str(crm_context.get("walkin_status", "")),
        ]
        for emotion in phase3_payload.get("emotion_summary", {}).keys():
            terms.append(str(emotion))
        return [term for term in terms if term.strip()]

    def _cache_path(self, call_id: str, payload: str) -> Path:
        digest = hashlib.sha256(f"{DEFAULT_INPUT_HASH_VERSION}:{call_id}:{payload}".encode("utf-8")).hexdigest()
        return CACHE_DIR / f"{call_id}_{digest[:16]}.json"

    def _load_cache(self, call_id: str, payload: str) -> dict[str, Any] | None:
        if not RESPONSE_CACHE_ENABLED:
            return None
        return read_json(self._cache_path(call_id, payload), default=None)

    def _save_cache(self, call_id: str, payload: str, response_payload: dict[str, Any]) -> None:
        if not RESPONSE_CACHE_ENABLED:
            return
        write_json(self._cache_path(call_id, payload), response_payload)

