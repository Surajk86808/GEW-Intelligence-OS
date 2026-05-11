from __future__ import annotations

import logging
from typing import Any

import numpy as np

from enrichment.config import CHUNK_LENGTH_SEC, DEVICE, EMOTION_MODEL_ID, FALLBACK_DEVICE, MIN_EMOTION_CHUNK_SEC, TARGET_SAMPLE_RATE

logging.getLogger("transformers").setLevel(logging.ERROR)


class EmotionEngine:
    def __init__(self, logger: Any):
        self.logger = logger
        self.pipeline = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        try:
            from transformers import pipeline
            import torch
            
            device_name = DEVICE
            if device_name == "cuda" and not torch.cuda.is_available():
                device_name = FALLBACK_DEVICE

            device_id = 0 if device_name == "cuda" else -1
            if device_id == 0:
                self.logger.info(f"Loading emotion model {EMOTION_MODEL_ID} on CUDA")
            else:
                self.logger.warning(f"Loading emotion model {EMOTION_MODEL_ID} on CPU fallback")
            self.pipeline = pipeline("audio-classification", model=EMOTION_MODEL_ID, device=device_id)
        except ImportError:
            self.logger.warning(f"PyTorch or Transformers not fully installed. Emotion analysis will be skipped.")
            self.pipeline = None

    def analyze(self, audio: np.ndarray, duration: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if self.pipeline is None:
            return [], {}
            
        timeline: list[dict[str, Any]] = []
        chunk_samples = int(CHUNK_LENGTH_SEC * TARGET_SAMPLE_RATE)
        min_chunk_samples = int(MIN_EMOTION_CHUNK_SEC * TARGET_SAMPLE_RATE)
        emotion_counts: dict[str, int] = {}
        emotion_confidence_sums: dict[str, float] = {}

        for start_idx in range(0, len(audio), chunk_samples):
            end_idx = min(start_idx + chunk_samples, len(audio))
            chunk = audio[start_idx:end_idx]
            if len(chunk) < min_chunk_samples:
                continue

            start_sec = start_idx / TARGET_SAMPLE_RATE
            end_sec = min(end_idx / TARGET_SAMPLE_RATE, duration)
            predictions = self.pipeline(chunk)
            top_prediction = predictions[0]
            mapped_emotion = map_emotion_label(str(top_prediction["label"]))
            confidence = round(float(top_prediction["score"]), 2)

            emotion_counts[mapped_emotion] = emotion_counts.get(mapped_emotion, 0) + 1
            emotion_confidence_sums[mapped_emotion] = emotion_confidence_sums.get(mapped_emotion, 0.0) + confidence
            timeline.append(
                {
                    "start": timestamp(start_sec),
                    "end": timestamp(end_sec),
                    "emotion": mapped_emotion,
                    "confidence": confidence,
                }
            )

        summary = {
            emotion: {
                "segments": count,
                "average_confidence": round(emotion_confidence_sums[emotion] / count, 2),
            }
            for emotion, count in sorted(emotion_counts.items())
        }
        return timeline, summary


def map_emotion_label(label: str) -> str:
    normalized = label.strip().lower()
    label_map = {
        "neu": "neutral",
        "neutral": "neutral",
        "hap": "excited",
        "happy": "excited",
        "excited": "excited",
        "ang": "angry",
        "anger": "angry",
        "angry": "angry",
        "frustrated": "frustrated",
        "sad": "hesitant",
        "hesitant": "hesitant",
        "fear": "confused",
        "confused": "confused",
        "calm": "calm",
        "interested": "interested",
        "confidence": "confident",
        "confident": "confident",
        "disgust": "disengaged",
        "disengaged": "disengaged",
    }
    return label_map.get(normalized, "neutral")


def timestamp(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    minutes, remaining = divmod(total_seconds, 60)
    return f"{minutes:02d}:{remaining:02d}"
