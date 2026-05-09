from __future__ import annotations

from typing import Any

import librosa
import numpy as np

from enrichment.config import SILENCE_AWKWARD_THRESHOLD_SEC, SILENCE_HIGH_PRESSURE_THRESHOLD_SEC, SILENCE_TOP_DB, TARGET_SAMPLE_RATE
from enrichment.emotion_engine import timestamp


class SilenceEngine:
    def analyze(self, audio: np.ndarray, duration: float) -> dict[str, Any]:
        if len(audio) == 0:
            return self._empty_metrics()

        intervals = librosa.effects.split(audio, top_db=SILENCE_TOP_DB)
        silence_timeline: list[dict[str, Any]] = []
        silence_durations: list[float] = []
        last_end = 0

        for start, end in intervals:
            silence_samples = start - last_end
            if silence_samples > 0:
                silence_duration = silence_samples / TARGET_SAMPLE_RATE
                silence_durations.append(silence_duration)
                silence_timeline.append(
                    {
                        "start": timestamp(last_end / TARGET_SAMPLE_RATE),
                        "end": timestamp(start / TARGET_SAMPLE_RATE),
                        "duration_sec": round(silence_duration, 2),
                        "silence_type": classify_silence(silence_duration),
                    }
                )
            last_end = end

        trailing_silence_samples = len(audio) - last_end
        if trailing_silence_samples > 0:
            trailing_duration = trailing_silence_samples / TARGET_SAMPLE_RATE
            silence_durations.append(trailing_duration)
            silence_timeline.append(
                {
                    "start": timestamp(last_end / TARGET_SAMPLE_RATE),
                    "end": timestamp(duration),
                    "duration_sec": round(trailing_duration, 2),
                    "silence_type": classify_silence(trailing_duration),
                }
            )

        total_silence_sec = sum(silence_durations)
        longest_silence_sec = max(silence_durations) if silence_durations else 0.0
        awkward_silence_count = sum(1 for value in silence_durations if value >= SILENCE_AWKWARD_THRESHOLD_SEC)
        high_pressure_pause_count = sum(1 for value in silence_durations if value >= SILENCE_HIGH_PRESSURE_THRESHOLD_SEC)
        disengagement_pauses = sum(1 for value in silence_durations if value >= 2.0)
        hesitation_gaps = sum(1 for value in silence_durations if 0.8 <= value < 2.0)
        engagement_score = round(max(0.0, 1.0 - min(1.0, total_silence_sec / max(duration, 1.0))), 2)

        return {
            "total_silence_sec": round(total_silence_sec, 2),
            "longest_silence_sec": round(longest_silence_sec, 2),
            "awkward_silence_count": awkward_silence_count,
            "high_pressure_pause_count": high_pressure_pause_count,
            "disengagement_pause_count": disengagement_pauses,
            "hesitation_gap_count": hesitation_gaps,
            "silence_segments": len(silence_durations),
            "engagement_score": engagement_score,
            "silence_timeline": silence_timeline,
        }

    def _empty_metrics(self) -> dict[str, Any]:
        return {
            "total_silence_sec": 0.0,
            "longest_silence_sec": 0.0,
            "awkward_silence_count": 0,
            "high_pressure_pause_count": 0,
            "disengagement_pause_count": 0,
            "hesitation_gap_count": 0,
            "silence_segments": 0,
            "engagement_score": 0.0,
            "silence_timeline": [],
        }


def classify_silence(duration_sec: float) -> str:
    if duration_sec >= SILENCE_HIGH_PRESSURE_THRESHOLD_SEC:
        return "high_pressure_pause"
    if duration_sec >= SILENCE_AWKWARD_THRESHOLD_SEC:
        return "awkward_silence"
    if duration_sec >= 2.0:
        return "disengagement_pause"
    if duration_sec >= 0.8:
        return "hesitation_gap"
    return "micro_pause"
