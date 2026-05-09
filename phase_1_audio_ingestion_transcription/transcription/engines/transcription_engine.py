from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable

from transcription.config import (
    WHISPER_BEST_OF,
    WHISPER_BEAM_SIZE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_CONDITION_PREVIOUS,
    WHISPER_DEVICE,
    WHISPER_LANGUAGE,
    WHISPER_MODEL_SIZE,
    WHISPER_TASK,
    WHISPER_TEMPERATURE,
    WHISPER_VAD_FILTER,
)
from transcription.engines.audio_preprocessing import convert_to_wav_16k_mono

_MODEL: Any | None = None


def get_model(logger: Any | None = None):
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    from faster_whisper import WhisperModel

    device = WHISPER_DEVICE
    compute_type = WHISPER_COMPUTE_TYPE
    try:
        if logger:
            logger.info(f"Initializing Whisper model '{WHISPER_MODEL_SIZE}' on {device} ({compute_type})")
        _MODEL = WhisperModel(WHISPER_MODEL_SIZE, device=device, compute_type=compute_type)
    except Exception as gpu_exc:
        if logger:
            logger.warning(f"Primary Whisper initialization failed: {gpu_exc}. Falling back to CPU int8.")
        _MODEL = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _MODEL


def transcribe_audio(audio_path: Path, on_segment: Callable[[float, str], None] | None = None, logger: Any | None = None) -> tuple[str, dict[str, Any]]:
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise RuntimeError("empty audio")

    wav_path = convert_to_wav_16k_mono(audio_path)
    try:
        model = get_model(logger)
        segments, info = model.transcribe(
            str(wav_path),
            language=WHISPER_LANGUAGE,
            task=WHISPER_TASK,
            beam_size=WHISPER_BEAM_SIZE,
            best_of=WHISPER_BEST_OF,
            temperature=WHISPER_TEMPERATURE,
            vad_filter=WHISPER_VAD_FILTER,
            condition_on_previous_text=WHISPER_CONDITION_PREVIOUS,
        )

        transcript_lines: list[str] = []
        confidence_samples: list[float] = []
        segment_count = 0
        word_count = 0

        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue
            segment_count += 1
            word_count += len(text.split())
            timestamp = _format_timestamp(segment.start)
            line = f"{timestamp} {text}"
            transcript_lines.append(line)
            avg_logprob = getattr(segment, "avg_logprob", None)
            if avg_logprob is not None:
                confidence_samples.append(max(0.0, min(1.0, math.exp(avg_logprob))))
            if on_segment:
                on_segment(segment.start, line)

        transcript_text = "\n".join(transcript_lines).strip()
        if not transcript_text:
            raise RuntimeError("whisper failed: empty transcript")

        metadata = {
            "word_count": word_count,
            "segment_count": segment_count,
            "detected_language": getattr(info, "language", ""),
            "language_probability": getattr(info, "language_probability", 0.0),
            "audio_duration": getattr(info, "duration", 0.0),
            "confidence_score": round(sum(confidence_samples) / len(confidence_samples), 4) if confidence_samples else None,
        }
        return transcript_text, metadata
    finally:
        if wav_path.exists():
            wav_path.unlink()


def release_model() -> None:
    global _MODEL
    _MODEL = None


def _format_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    remaining = int(seconds % 60)
    return f"[{minutes:02d}:{remaining:02d}]"
