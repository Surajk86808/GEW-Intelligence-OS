from __future__ import annotations

from typing import Any

import librosa
import numpy as np

from enrichment.config import TARGET_SAMPLE_RATE


class AcousticEngine:
    def analyze(self, audio: np.ndarray, duration: float, transcript_metrics: dict[str, Any]) -> dict[str, Any]:
        if len(audio) == 0:
            return self._empty_metrics()

        rms = librosa.feature.rms(y=audio)[0]
        mean_energy = float(np.mean(rms))
        peak_energy = float(np.max(rms))
        energy_volatility = float(np.std(rms))

        pitches, magnitudes = librosa.piptrack(y=audio, sr=TARGET_SAMPLE_RATE)
        pitch_values = pitches[magnitudes > np.median(magnitudes)]
        pitch_mean = float(np.mean(pitch_values)) if len(pitch_values) > 0 else 0.0
        pitch_variation = float(np.std(pitch_values)) if len(pitch_values) > 0 else 0.0

        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        avg_zcr = float(np.mean(zcr))

        speaking_rate_wpm = transcript_metrics.get("speaking_rate_wpm")
        tempo_score = min(1.0, float(speaking_rate_wpm or 0.0) / 180.0) if speaking_rate_wpm is not None else 0.0
        energy_score = min(1.0, mean_energy * 8)
        stress_score = min(1.0, (energy_volatility * 10) + (pitch_variation / 120.0))
        confidence_score = min(1.0, max(0.0, (energy_score * 0.45) + (1.0 - stress_score) * 0.55))
        emotional_volatility = min(1.0, (energy_volatility * 8) + (pitch_variation / 150.0))

        return {
            "average_speaking_rate_wpm": speaking_rate_wpm,
            "mean_energy": round(mean_energy, 4),
            "peak_energy": round(peak_energy, 4),
            "energy_fluctuation": round(energy_volatility, 4),
            "pitch_mean_hz": round(pitch_mean, 2),
            "pitch_variation": round(pitch_variation, 4),
            "avg_speaking_rate_proxy": round(avg_zcr, 4),
            "conversation_tempo_score": round(tempo_score, 2),
            "emotional_volatility": round(emotional_volatility, 2),
            "stress_score": round(stress_score, 2),
            "confidence_score": round(confidence_score, 2),
            "escalation_detected": bool(stress_score > 0.75 and energy_volatility > 0.05),
            "duration_sec": round(duration, 2),
        }

    def _empty_metrics(self) -> dict[str, Any]:
        return {
            "average_speaking_rate_wpm": None,
            "mean_energy": 0.0,
            "peak_energy": 0.0,
            "energy_fluctuation": 0.0,
            "pitch_mean_hz": 0.0,
            "pitch_variation": 0.0,
            "avg_speaking_rate_proxy": 0.0,
            "conversation_tempo_score": 0.0,
            "emotional_volatility": 0.0,
            "stress_score": 0.0,
            "confidence_score": 0.0,
            "escalation_detected": False,
            "duration_sec": 0.0,
        }
