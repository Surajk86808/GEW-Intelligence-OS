from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Any

from config import QUERY_LLM_MODEL, QUERY_LLM_PROVIDER, QUERY_LLM_TEMPERATURE, QUERY_MIN_CONFIDENCE

SYSTEM_PROMPT = """You are the Query Intelligence Engine of the GEW Intelligence OS.

ROLE
Your job is to answer user questions using ONLY the retrieved conversational memory, reasoning outputs, metadata, and indexed evidence provided to you.

You are the final intelligence layer sitting on top of:
- transcript memory
- reasoning layer outputs
- semantic retrieval
- CRM metadata
- emotional analysis
- objection indexing
- evidence records

You are NOT a generic chatbot.
You are an enterprise conversational intelligence analyst.

CORE RESPONSIBILITIES
1. Analyze retrieved conversational evidence.
2. Synthesize patterns across multiple calls.
3. Generate grounded answers using retrieved memory.
4. Explain WHY conclusions were reached.
5. Cite supporting evidence whenever possible.
6. Detect uncertainty and missing evidence.
7. Preserve factual consistency with retrieved data.
8. Maintain conversational session memory context.

STRICT RULES
- NEVER invent conversations.
- NEVER hallucinate unsupported facts.
- NEVER assume business outcomes without evidence.
- NEVER generate fake call IDs or timestamps.
- NEVER answer from general world knowledge if evidence is absent.
- NEVER treat missing data as negative evidence.

If evidence is insufficient, explicitly say:
"Insufficient evidence available in retrieved memory."

If multiple interpretations exist:
- explain competing possibilities
- provide confidence reasoning

REASONING PRIORITY
Always prioritize information in this order:
1. Retrieved evidence chunks
2. Reasoning layer outputs
3. CRM metadata
4. Emotional/contextual signals
5. Statistical or pattern analysis
6. Historical memory relationships

SESSION MEMORY HANDLING
You maintain conversational continuity.
You must remember:
- current investigation topic
- active filters
- referenced campaigns
- referenced counselors
- referenced customer segments
- previous analytical context

ANALYSIS MODES
You may perform:
- root cause analysis
- objection analysis
- conversion analysis
- counselor performance analysis
- emotional trend analysis
- campaign quality analysis
- multi-call pattern analysis
- temporal conversation analysis
- lead behavior analysis
- support quality analysis

EVIDENCE REQUIREMENTS
Whenever possible include:
- Call IDs
- Timestamps
- Supporting transcript excerpts
- Reasoning evidence
- Confidence explanations

Always distinguish between:
- observed evidence
- inferred patterns
- hypotheses
- uncertainty

IMPORTANT
You are NOT the retrieval engine.
You only reason over retrieved memory.

Response style:
- analytical
- concise but deep
- evidence-grounded
- operationally useful
- logically structured
- enterprise-grade

Return valid JSON only with this schema:
{
  "answer": "final grounded answer",
  "observed_evidence": ["..."],
  "inferred_patterns": ["..."],
  "hypotheses": ["..."],
  "uncertainty": ["..."],
  "reasoning_evidence": ["..."],
  "evidence": [{"call_id": "", "timestamp": "", "quote": "", "why_it_matters": ""}],
  "confidence": 0.0,
  "confidence_reasoning": "...",
  "operational_recommendation": "..."
}
"""


from shared.llm_client import LLMClient
from shared.settings import QUERY_MODEL

class QueryIntelligenceEngine:
    def __init__(self, logger: Any = None) -> None:
        self.logger = logger

    def answer(
        self,
        query: str,
        session_memory: dict[str, Any],
        retrieved_chunks: list[dict[str, Any]],
        reasoning_data: dict[str, Any],
        metadata: dict[str, Any],
        evidence_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not retrieved_chunks:
            return self._insufficient_response()

        prompt = self._build_prompt(query, session_memory, retrieved_chunks, reasoning_data, metadata, evidence_records)
        try:
            response_text = LLMClient.generate_content(
                model=QUERY_MODEL,
                prompt=prompt,
                system_instruction=SYSTEM_PROMPT,
                temperature=QUERY_LLM_TEMPERATURE,
                response_mime_type="application/json"
            )
            
            payload = json.loads(response_text)
            if not isinstance(payload, dict):
                return self._fallback_response(query, retrieved_chunks, reasoning_data, metadata, evidence_records)
            payload.setdefault("confidence", 0.5)
            payload.setdefault("observed_evidence", [])
            payload.setdefault("inferred_patterns", [])
            payload.setdefault("hypotheses", [])
            payload.setdefault("uncertainty", [])
            payload.setdefault("reasoning_evidence", [])
            payload.setdefault("evidence", [])
            payload.setdefault("confidence_reasoning", "Confidence reasoning not provided by model.")
            payload.setdefault("operational_recommendation", "")
            if float(payload.get("confidence", 0.0)) < QUERY_MIN_CONFIDENCE:
                payload.setdefault("uncertainty", []).append("Model confidence below operational threshold.")
            return payload
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"Query intelligence LLM fallback engaged: {exc}")
            import traceback
            print(traceback.format_exc())
            return self._fallback_response(query, retrieved_chunks, reasoning_data, metadata, evidence_records)

    def _build_prompt(
        self,
        query: str,
        session_memory: dict[str, Any],
        retrieved_chunks: list[dict[str, Any]],
        reasoning_data: dict[str, Any],
        metadata: dict[str, Any],
        evidence_records: list[dict[str, Any]],
    ) -> str:
        return "\n\n".join(
            [
                f"USER QUESTION:\n{query}",
                f"SESSION MEMORY:\n{json.dumps(session_memory, indent=2, ensure_ascii=False)}",
                f"RETRIEVED TRANSCRIPT CHUNKS:\n{json.dumps(retrieved_chunks, indent=2, ensure_ascii=False)}",
                f"REASONING OUTPUTS:\n{json.dumps(reasoning_data, indent=2, ensure_ascii=False)}",
                f"CRM & METADATA:\n{json.dumps(metadata, indent=2, ensure_ascii=False)}",
                f"EVIDENCE REFERENCES:\n{json.dumps(evidence_records, indent=2, ensure_ascii=False)}",
            ]
        )

    def _fallback_response(
        self,
        query: str,
        retrieved_chunks: list[dict[str, Any]],
        reasoning_data: dict[str, Any],
        metadata: dict[str, Any],
        evidence_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        call_ids = [record.get("call_id", "") for record in evidence_records if record.get("call_id")]
        call_count = len(set(call_ids))
        tag_counter: Counter[str] = Counter()
        emotion_counter: Counter[str] = Counter()
        conversion_scores: list[float] = []

        for result in retrieved_chunks:
            result_metadata = result.get("metadata", {})
            for tag in result_metadata.get("reasoning_tags", []):
                if tag:
                    tag_counter[str(tag)] += 1
            emotion = str(result_metadata.get("emotion", "")).strip()
            if emotion:
                emotion_counter[emotion] += 1

        for item in reasoning_data.values():
            conversion = item.get("conversion_insight", {}).get("conversion_probability")
            if conversion is not None:
                conversion_scores.append(float(conversion))

        observed = [
            f"Retrieved {len(retrieved_chunks)} chunks across {call_count} call(s).",
        ]
        if tag_counter:
            observed.append(
                "Most frequent reasoning tags: "
                + ", ".join(f"{tag} ({count})" for tag, count in tag_counter.most_common(3))
            )
        if emotion_counter:
            observed.append(
                "Most frequent emotional signals: "
                + ", ".join(f"{emotion} ({count})" for emotion, count in emotion_counter.most_common(3))
            )

        inferred: list[str] = []
        if conversion_scores:
            average_conversion = round(sum(conversion_scores) / len(conversion_scores), 2)
            inferred.append(f"Average retrieved conversion probability is {average_conversion}.")

        reasoning_evidence = []
        for call_id, item in list(reasoning_data.items())[:5]:
            objections = item.get("objections", [])
            risk_level = item.get("risk_assessment", {}).get("overall_risk_level", "")
            intent_score = item.get("intent_analysis", {}).get("primary_intent_score", "")
            evidence_parts = [f"Call {call_id}"]
            if objections:
                evidence_parts.append(f"{len(objections)} objection(s)")
            if risk_level:
                evidence_parts.append(f"risk={risk_level}")
            if intent_score != "":
                evidence_parts.append(f"intent_score={intent_score}")
            reasoning_evidence.append(", ".join(evidence_parts))

        evidence = []
        for record in evidence_records[:5]:
            evidence.append(
                {
                    "call_id": record.get("call_id", ""),
                    "timestamp": record.get("timestamp_start", ""),
                    "quote": record.get("quote", ""),
                    "why_it_matters": self._explain_evidence(record),
                }
            )

        uncertainty = []
        if len(retrieved_chunks) < 3:
            uncertainty.append("Small evidence set; pattern stability is limited.")
        if not evidence:
            uncertainty.append("Insufficient evidence available in retrieved memory.")

        answer_lines = [f"Query focus: {query}"]
        answer_lines.extend(observed)
        if inferred:
            answer_lines.append("Inferred pattern: " + " ".join(inferred))
        if uncertainty:
            answer_lines.append("Limitations: " + " ".join(uncertainty))

        return {
            "answer": " ".join(answer_lines) if evidence else "Insufficient evidence available in retrieved memory.",
            "observed_evidence": observed,
            "inferred_patterns": inferred,
            "hypotheses": [],
            "uncertainty": uncertainty,
            "reasoning_evidence": reasoning_evidence,
            "evidence": evidence,
            "confidence": 0.72 if evidence else 0.2,
            "confidence_reasoning": "Confidence is based on retrieved evidence coverage, not external knowledge.",
            "operational_recommendation": (
                "Use the cited calls and timestamps for manual validation before taking business action."
                if evidence
                else "Run a broader retrieval query or rebuild memory artifacts before drawing conclusions."
            ),
            "metadata_summary": metadata,
        }

    def _insufficient_response(self) -> dict[str, Any]:
        return {
            "answer": "Insufficient evidence available in retrieved memory.",
            "observed_evidence": [],
            "inferred_patterns": [],
            "hypotheses": [],
            "uncertainty": ["No retrieved chunks matched the current query."],
            "reasoning_evidence": [],
            "evidence": [],
            "confidence": 0.0,
            "confidence_reasoning": "No retrieval-grounded evidence was available.",
            "operational_recommendation": "Broaden the query or adjust filters to retrieve relevant memory.",
        }

    def _explain_evidence(self, record: dict[str, Any]) -> str:
        tags = record.get("reasoning_tags", [])
        if tags:
            return f"Reasoning tags: {', '.join(str(tag) for tag in tags)}"
        emotion = str(record.get("emotion", "")).strip()
        if emotion:
            return f"Emotion signal: {emotion}"
        return "Relevant retrieved transcript evidence."
