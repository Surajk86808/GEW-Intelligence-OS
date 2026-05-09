from __future__ import annotations

from pathlib import Path
from typing import Any

from enrichment.config import JSON_OUTPUT_DIR, SUMMARIES_DIR, TIMELINES_DIR
from shared.json_utils import write_json


class ExportEngine:
    def export(self, call_id: str, payload: dict[str, Any]) -> tuple[Path, Path, Path]:
        json_path = JSON_OUTPUT_DIR / f"{call_id}.json"
        timeline_path = TIMELINES_DIR / f"{call_id}.json"
        summary_path = SUMMARIES_DIR / f"{call_id}.txt"

        write_json(json_path, payload)
        write_json(timeline_path, payload["emotion_timeline"])
        summary_path.write_text(self._build_summary(payload), encoding="utf-8")
        return json_path, summary_path, timeline_path

    def _build_summary(self, payload: dict[str, Any]) -> str:
        top_emotions = ", ".join(payload["emotion_summary"].keys()) if payload["emotion_summary"] else "none_detected"
        return "\n".join(
            [
                f"VOICE INTELLIGENCE SUMMARY: {payload['call_id']}",
                f"Duration: {payload['duration_sec']} sec",
                f"Transcript Source: {payload.get('transcript_source', '')}",
                f"Primary Intent: {payload.get('conversation_intelligence', {}).get('primary_intent', '')}",
                f"Top Emotions: {top_emotions}",
                "--------------------------------------------------",
                "[ENGAGEMENT]",
                f"Engagement Score: {payload['engagement_score']}",
                f"Stress Score: {payload['stress_score']}",
                f"Confidence Score: {payload['confidence_score']}",
                f"Escalation Detected: {payload['escalation_detected']}",
                "",
                "[SPEAKER METRICS]",
                f"Speaker 1 Talk Ratio: {payload['speaker_metrics']['speaker_1_talk_ratio']}%",
                f"Speaker 2 Talk Ratio: {payload['speaker_metrics']['speaker_2_talk_ratio']}%",
                f"Interruptions: {payload['speaker_metrics']['interruptions']}",
                f"Response Latency Avg: {payload['speaker_metrics']['response_latency_sec_avg']}",
                "",
                "[SILENCE]",
                f"Longest Silence: {payload['silence_metrics']['longest_silence_sec']} sec",
                f"Awkward Silences: {payload['silence_metrics']['awkward_silence_count']}",
                f"High Pressure Pauses: {payload['silence_metrics']['high_pressure_pause_count']}",
                "",
                "[ACOUSTICS]",
                f"Average Speaking Rate WPM: {payload['acoustic_metrics']['average_speaking_rate_wpm']}",
                f"Pitch Variation: {payload['acoustic_metrics']['pitch_variation']}",
                f"Energy Fluctuation: {payload['acoustic_metrics']['energy_fluctuation']}",
                "--------------------------------------------------",
            ]
        )
