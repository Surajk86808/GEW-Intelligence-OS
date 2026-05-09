from __future__ import annotations

import re
from typing import Any


class SynthesisEngine:
    """
    Post-processes raw LLM answers into a structured, refined business response.
    """

    def synthesize(self, question: str, intent: dict[str, Any], evidence: list[dict[str, Any]], raw_answer: str) -> dict[str, Any]:
        # 1. Clean Answer
        answer = self._clean_answer(raw_answer)

        # 2. Extract Insight Headline
        insight = self._extract_insight(answer)

        # 3. Calculate Confidence (Evidence-based)
        confidence = self._calculate_confidence(intent, evidence)

        # 4. Extract Unique Referenced Calls
        calls_referenced = sorted(list(set(str(e.get("call_id", "")) for e in evidence if e.get("call_id"))))

        # 5. Generate Follow-up Suggestions
        suggestions = self._get_suggestions(intent)

        return {
            "answer": answer,
            "insight": insight,
            "confidence": confidence,
            "calls_referenced": calls_referenced,
            "follow_up_suggestions": suggestions
        }

    def _clean_answer(self, text: str) -> str:
        """Strips technical artifacts and references to retrieval internals."""
        # Remove common technical phrases
        tech_phrases = [
            r"based on the (?:provided )?evidence (?:items?|chunks?)",
            r"in the (?:retrieved )?data",
            r"according to the (?:provided )?transcript snippets",
            r"the chunks show that",
            r"referenced calls indicate",
        ]
        cleaned = text
        for phrase in tech_phrases:
            cleaned = re.sub(phrase, "", cleaned, flags=re.IGNORECASE)

        # Strip JSON-like artifacts or excessive whitespace
        cleaned = re.sub(r"[\{\}\[\]]", "", cleaned)
        return cleaned.strip().capitalize()

    def _extract_insight(self, answer: str) -> str:
        """Extracts a one-sentence headline insight from the start of the answer."""
        if not answer:
            return "No insight available."
        
        # Take the first sentence
        first_sentence = answer.split('.')[0].strip()
        
        # Limit to ~15 words
        words = first_sentence.split()
        if len(words) > 15:
            return " ".join(words[:15]) + "..."
        
        return first_sentence

    def _calculate_confidence(self, intent: dict[str, Any], evidence: list[dict[str, Any]]) -> float:
        """Calculates a deterministic confidence score based on evidence density and intent type."""
        score = 0.5
        
        # Evidence density
        unique_calls = len(set(e.get("call_id") for e in evidence if e.get("call_id")))
        score += min(0.3, unique_calls * 0.1)
        
        # Volume check (if more than 5 results/calls found)
        if len(evidence) > 5:
            score += 0.1
            
        # Intent adjustments
        intent_type = intent.get("type", "casual")
        if intent_type == "retrieval":
            score += 0.1  # Direct data retrieval is more certain
        elif intent_type == "trend_analysis":
            score -= 0.1  # Trends are inferential/harder
            
        # Penalties
        if not evidence:
            score -= 0.2
            
        # Clamp and round
        return round(max(0.1, min(0.95, score)), 2)

    def _get_suggestions(self, intent: dict[str, Any]) -> list[str]:
        """Provides contextually relevant next questions based on the current intent."""
        intent_type = intent.get("type", "casual")
        entity = intent.get("entity", "")

        if intent_type == "greeting":
            return [
                "Which counselor has the highest conversion rate",
                "What objections are most common",
                "Show me failed calls from this week"
            ]
        elif intent_type == "entity_analysis":
            return [
                f"Show me all calls handled by {entity}" if entity else "Show calls for top performer",
                f"What objections does {entity} face most" if entity else "What are the most common objections",
                "Compare with other counselors"
            ]
        elif intent_type == "trend_analysis":
            return [
                "Which campaign is causing this",
                "Which counselor handles this best",
                "Show me specific calls where this happened"
            ]
        elif intent_type == "ranking":
            return [
                "What makes the top performer different",
                "Show coaching tips for bottom performers",
                "Break this down by campaign"
            ]
        
        # Default / Casual
        return [
            "Why are leads dropping",
            "Which counselor performs best",
            "What objections happen most"
        ]
