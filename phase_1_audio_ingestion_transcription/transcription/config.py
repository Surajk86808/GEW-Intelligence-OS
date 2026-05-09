from __future__ import annotations

from pathlib import Path

from shared.config_utils import get_env, get_env_int
from shared.path_utils import ensure_directories

PROJECT_DIR = Path(__file__).resolve().parent

INPUTS_DIR = PROJECT_DIR / "inputs"
OUTPUTS_DIR = PROJECT_DIR / "outputs"
LOGS_DIR = PROJECT_DIR / "logs"
ENGINES_DIR = PROJECT_DIR / "engines"
LEGACY_TRANSCRIPTS_DIR = PROJECT_DIR / "transcripts"
GEMINI_TRANSCRIPTS_DIR = LEGACY_TRANSCRIPTS_DIR / "transcript from gemini"

TRANSCRIPTS_DIR = OUTPUTS_DIR / "transcripts"
METADATA_DIR = OUTPUTS_DIR / "metadata"
STATE_DIR = OUTPUTS_DIR / "state"
STRUCTURED_OUTPUT_DIR = PROJECT_DIR / "structured_output"
STRUCTURED_METADATA_DIR = OUTPUTS_DIR / "structured_metadata"

CALL_MANIFEST_CANDIDATES = [
    PROJECT_DIR.parent / "ingestion" / "mapped_calls" / "call_manifest.json",
    PROJECT_DIR.parent / "phase_1_ingestion" / "outputs" / "metadata" / "call_manifest.json",
]
LEAD_PROFILES_DIR_CANDIDATES = [
    PROJECT_DIR.parent / "ingestion" / "mapped_calls" / "lead_profiles",
    PROJECT_DIR.parent / "phase_1_ingestion" / "outputs" / "metadata" / "lead_profiles",
]
COMBINED_TRANSCRIPT_CANDIDATES = [
    GEMINI_TRANSCRIPTS_DIR / "ALL_CALLS_COMBINED.txt",
]
RUNTIME_LOG_PATH = LOGS_DIR / "runtime_terminal.log"
TRANSCRIPTION_TEXT_LOG_PATH = LOGS_DIR / "transcription.log"
PROGRESS_LOG_PATH = LOGS_DIR / "progress.log"
FAILURES_LOG_PATH = LOGS_DIR / "failures.log"
RUNTIME_METRICS_PATH = LOGS_DIR / "runtime_metrics.log"
TRANSCRIPTION_LOG_PATH = LOGS_DIR / "transcription_log.csv"
TRANSCRIPT_MANIFEST_PATH = METADATA_DIR / "transcript_manifest.json"
STRUCTURED_TRANSCRIPT_MANIFEST_PATH = STRUCTURED_METADATA_DIR / "structured_transcript_manifest.json"
TRANSCRIPT_CATALOG_PATH = METADATA_DIR / "transcript_catalog.json"
PROCESSED_CALLS_PATH = STATE_DIR / "processed_calls.json"
PROCESS_LOCK_PATH = STATE_DIR / "processing.lock"

WHISPER_MODEL_SIZE = get_env("WHISPER_MODEL_SIZE", "large-v3")
WHISPER_DEVICE = get_env("WHISPER_DEVICE", "cuda")
WHISPER_COMPUTE_TYPE = get_env("WHISPER_COMPUTE_TYPE", "float16")
WHISPER_LANGUAGE = get_env("WHISPER_LANGUAGE", "hi")
WHISPER_TASK = get_env("WHISPER_TASK", "transcribe")
WHISPER_BEAM_SIZE = get_env_int("WHISPER_BEAM_SIZE", 5)
WHISPER_BEST_OF = get_env_int("WHISPER_BEST_OF", 5)
WHISPER_TEMPERATURE = 0
WHISPER_VAD_FILTER = False
WHISPER_CONDITION_PREVIOUS = False
TARGET_SAMPLE_RATE = 16000

TRANSCRIPTION_LOG_HEADERS = [
    "call_id",
    "status",
    "audio_path",
    "transcript_path",
    "error_message",
]


def ensure_phase_directories() -> None:
    ensure_directories(
        [
            INPUTS_DIR,
            OUTPUTS_DIR,
            LOGS_DIR,
            LEGACY_TRANSCRIPTS_DIR,
            GEMINI_TRANSCRIPTS_DIR,
            TRANSCRIPTS_DIR,
            METADATA_DIR,
            STATE_DIR,
            STRUCTURED_OUTPUT_DIR,
            STRUCTURED_METADATA_DIR,
        ]
    )
