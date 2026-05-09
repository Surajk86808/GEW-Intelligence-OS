from __future__ import annotations

from pathlib import Path

import ffmpeg

from transcription.config import TARGET_SAMPLE_RATE


def convert_to_wav_16k_mono(input_path: Path) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    temp_wav = input_path.with_suffix(".phase2.wav")
    try:
        (
            ffmpeg.input(str(input_path))
            .output(str(temp_wav), acodec="pcm_s16le", ac=1, ar=str(TARGET_SAMPLE_RATE))
            .overwrite_output()
            .global_args("-loglevel", "error")
            .run(capture_stdout=True, capture_stderr=True)
        )
        return temp_wav
    except Exception as exc:
        raise RuntimeError(f"Failed to normalize audio: {exc}") from exc
