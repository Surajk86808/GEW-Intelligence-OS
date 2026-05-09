from __future__ import annotations

from typing import Any


class AnalyticsEngine:
    def summarize(self, retrieval_results: list[dict[str, Any]]) -> dict[str, Any]:
        call_counts: dict[str, int] = {}
        emotion_counts: dict[str, int] = {}
        salesperson_counts: dict[str, int] = {}
        for item in retrieval_results:
            metadata = item["metadata"]
            call_id = str(metadata.get("call_id", "")).strip()
            emotion = str(metadata.get("emotion", "neutral")).strip()
            salesperson = str(metadata.get("salesperson", "")).strip()
            if call_id:
                call_counts[call_id] = call_counts.get(call_id, 0) + 1
            if emotion:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            if salesperson:
                salesperson_counts[salesperson] = salesperson_counts.get(salesperson, 0) + 1
        return {
            "matched_calls": len(call_counts),
            "top_emotions": _top_items(emotion_counts),
            "top_salespeople": _top_items(salesperson_counts),
        }


def _top_items(counts: dict[str, int]) -> list[dict[str, Any]]:
    return [{"label": label, "count": count} for label, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5]]

