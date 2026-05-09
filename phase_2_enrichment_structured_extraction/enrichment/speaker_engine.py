from __future__ import annotations

from typing import Any

import librosa
import numpy as np
from sklearn.cluster import KMeans

from enrichment.config import TARGET_SAMPLE_RATE


class SpeakerEngine:
    def analyze(self, audio: np.ndarray) -> dict[str, Any]:
        if len(audio) == 0:
            return self._empty_metrics()

        frame_length = 2048
        hop_length = 512
        mfccs = librosa.feature.mfcc(y=audio, sr=TARGET_SAMPLE_RATE, n_mfcc=13, hop_length=hop_length, n_fft=frame_length)
        features = mfccs.T
        if len(features) < 2:
            return self._empty_metrics()

        labels = KMeans(n_clusters=2, random_state=42, n_init=10).fit_predict(features)
        speaker_1_frames = int(np.sum(labels == 0))
        total_frames = max(len(labels), 1)
        speaker_1_ratio = round((speaker_1_frames / total_frames) * 100)
        speaker_2_ratio = 100 - speaker_1_ratio

        speaker_turns = np.where(np.diff(labels) != 0)[0]
        turn_timestamps = speaker_turns * hop_length / TARGET_SAMPLE_RATE
        response_latencies = np.diff(turn_timestamps) if len(turn_timestamps) > 1 else np.array([])
        interruptions = int(np.sum(response_latencies < 1.5)) if len(response_latencies) > 0 else 0
        overlap_proxy = round(float(np.sum(response_latencies < 0.35)) / max(len(response_latencies), 1), 2) if len(response_latencies) > 0 else 0.0

        dominance_gap = abs(speaker_1_ratio - speaker_2_ratio)
        conversation_balance = round(1.0 - (dominance_gap / 100.0), 2)

        return {
            "speaker_1_talk_ratio": speaker_1_ratio,
            "speaker_2_talk_ratio": speaker_2_ratio,
            "dominance_gap": dominance_gap,
            "interruptions": interruptions,
            "response_latency_sec_avg": round(float(np.mean(response_latencies)), 2) if len(response_latencies) > 0 else None,
            "response_latency_sec_median": round(float(np.median(response_latencies)), 2) if len(response_latencies) > 0 else None,
            "turn_changes": int(len(speaker_turns)),
            "overlap_speech_ratio_proxy": overlap_proxy,
            "conversation_balance": conversation_balance,
        }

    def _empty_metrics(self) -> dict[str, Any]:
        return {
            "speaker_1_talk_ratio": 0,
            "speaker_2_talk_ratio": 0,
            "dominance_gap": 0,
            "interruptions": 0,
            "response_latency_sec_avg": None,
            "response_latency_sec_median": None,
            "turn_changes": 0,
            "overlap_speech_ratio_proxy": 0.0,
            "conversation_balance": 0.0,
        }
