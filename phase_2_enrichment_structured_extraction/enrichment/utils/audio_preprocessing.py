from __future__ import annotations

from pathlib import Path

import ffmpeg

from enrichment.config import TARGET_SAMPLE_RATE


def normalize_audio_for_analysis(input_path: Path) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    normalized_path = input_path.with_suffix(".phase3.wav")
    try:
        (
            ffmpeg.input(str(input_path))
            .output(
                str(normalized_path),
                acodec="pcm_s16le",
                ac=1,
                ar=str(TARGET_SAMPLE_RATE),
            )
            .overwrite_output()
            .global_args("-loglevel", "error")
            .run(capture_stdout=True, capture_stderr=True)
        )
        return normalized_path
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg not found") from exc
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else ""
        raise RuntimeError(stderr.strip() or "ffmpeg normalization failed") from exc
