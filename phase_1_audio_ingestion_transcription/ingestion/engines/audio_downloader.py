from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import ffmpeg
import requests

from ingestion.config import AUDIO_OUTPUT_DIR, DOWNLOAD_RETRIES, DOWNLOAD_TIMEOUT_SECONDS


class DownloadError(Exception):
    pass


def download_audio(recording_url: str, call_id: str) -> Path:
    if not _is_valid_url(recording_url):
        raise DownloadError("download failed: invalid URL")

    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    final_audio_path = AUDIO_OUTPUT_DIR / f"{call_id}.mp3"
    temp_audio_path = AUDIO_OUTPUT_DIR / f"{call_id}.download"

    last_error = "download failed"
    for attempt in range(DOWNLOAD_RETRIES + 1):
        try:
            _download_file(recording_url, temp_audio_path)
            _normalize_to_mp3(temp_audio_path, final_audio_path)
            _validate_non_empty(final_audio_path)
            return final_audio_path
        except Exception as exc:
            last_error = str(exc)
            _safe_unlink(temp_audio_path)
            _safe_unlink(final_audio_path)
            if attempt >= DOWNLOAD_RETRIES:
                raise DownloadError(last_error) from exc
    raise DownloadError(last_error)


def get_cached_audio_path(call_id: str) -> Path:
    return AUDIO_OUTPUT_DIR / f"{call_id}.mp3"


def _download_file(recording_url: str, destination_path: Path) -> None:
    with requests.get(recording_url, stream=True, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        response.raise_for_status()
        with destination_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    handle.write(chunk)
    if not destination_path.exists() or destination_path.stat().st_size == 0:
        raise DownloadError("empty audio")


def _normalize_to_mp3(source_path: Path, destination_path: Path) -> None:
    try:
        ffmpeg.probe(str(source_path))
    except FileNotFoundError as exc:
        raise DownloadError("ffmpeg not found") from exc
    except ffmpeg.Error as exc:
        raise DownloadError("unsupported format") from exc

    try:
        (
            ffmpeg.input(str(source_path))
            .output(str(destination_path), acodec="libmp3lame", format="mp3")
            .overwrite_output()
            .global_args("-loglevel", "error")
            .run(capture_stdout=True, capture_stderr=True)
        )
    except FileNotFoundError as exc:
        raise DownloadError("ffmpeg not found") from exc
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else ""
        raise DownloadError(stderr.strip() or "unsupported format") from exc
    finally:
        _safe_unlink(source_path)


def _validate_non_empty(audio_path: Path) -> None:
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise DownloadError("empty audio")


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme and parsed.netloc)


def _safe_unlink(path: Path) -> None:
    if path.exists():
        path.unlink()
