from __future__ import annotations

from pathlib import Path

from shared.config_utils import get_env, get_env_float, get_env_int
from shared.path_utils import ensure_directories

PROJECT_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_DIR.parent.parent

INPUTS_DIR = PROJECT_DIR / "inputs"
INPUTS_TRANSCRIPTS_DIR = INPUTS_DIR / "transcripts"
INPUTS_ENRICHED_JSON_DIR = INPUTS_DIR / "enriched_json"
INPUTS_MANUAL_REVIEWS_DIR = INPUTS_DIR / "manual_reviews"
INPUTS_CORRECTED_CALLS_DIR = INPUTS_DIR / "corrected_calls"
INPUTS_EXTERNAL_IMPORTS_DIR = INPUTS_DIR / "external_imports"
LOCAL_AUDIO_INPUT_DIR = PROJECT_DIR / "audio_input"
LOCAL_TRANSCRIPTS_DIR = PROJECT_DIR / "transcripts"
COMBINED_FALLBACK_DIR = LOCAL_TRANSCRIPTS_DIR / "combined_fallback"
OUTPUTS_DIR = PROJECT_DIR / "outputs"
LOGS_DIR = PROJECT_DIR / "logs"
MODELS_DIR = PROJECT_DIR / "models"
UTILS_DIR = PROJECT_DIR / "utils"

JSON_OUTPUT_DIR = OUTPUTS_DIR / "json"
SUMMARIES_DIR = OUTPUTS_DIR / "summaries"
TIMELINES_DIR = OUTPUTS_DIR / "timelines"
METADATA_DIR = OUTPUTS_DIR / "metadata"

RUNTIME_LOG_PATH = LOGS_DIR / "runtime_terminal.log"
EMOTION_MANIFEST_PATH = METADATA_DIR / "emotion_manifest.json"
PROCESSING_LOG_PATH = LOGS_DIR / "phase_3_processing_log.csv"

AUDIO_SOURCE_CANDIDATES = [
    LOCAL_AUDIO_INPUT_DIR,
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "ingestion" / "audio",
    REPO_ROOT / "phase_1_transcription" / "audio",
    REPO_ROOT / "phase_1_map & download" / "audio",
]

ENRICHED_TRANSCRIPT_SOURCE_CANDIDATES = [
    LOCAL_TRANSCRIPTS_DIR,
    LOCAL_TRANSCRIPTS_DIR / "transcripit_enriched_by_gemini",
]
MANUAL_INPUT_SOURCE_CANDIDATES = [
    INPUTS_MANUAL_REVIEWS_DIR,
    INPUTS_CORRECTED_CALLS_DIR,
    INPUTS_ENRICHED_JSON_DIR,
    INPUTS_TRANSCRIPTS_DIR,
    INPUTS_EXTERNAL_IMPORTS_DIR,
]
STRUCTURED_TRANSCRIPT_SOURCE_CANDIDATES = [
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "transcription" / "structured_output",
]
TRANSCRIPT_TEXT_SOURCE_CANDIDATES = [
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "transcription" / "outputs" / "transcripts",
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "transcription" / "transcripts",
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "transcription" / "transcripts" / "transcript from gemini",
]
COMBINED_TRANSCRIPT_CANDIDATES = [
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "transcription" / "transcripts" / "transcript from gemini" / "ALL_CALLS_COMBINED.txt",
]
CALL_MANIFEST_CANDIDATES = [
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "ingestion" / "mapped_calls" / "call_manifest.json",
    REPO_ROOT / "phase_1_ingestion" / "outputs" / "metadata" / "call_manifest.json",
]
LEAD_PROFILES_DIR_CANDIDATES = [
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "ingestion" / "mapped_calls" / "lead_profiles",
    REPO_ROOT / "phase_1_ingestion" / "outputs" / "metadata" / "lead_profiles",
]

TARGET_SAMPLE_RATE = 16000
CHUNK_LENGTH_SEC = get_env_float("EMOTION_CHUNK_LENGTH_SEC", 3.0)
EMOTION_MODEL_ID = get_env("EMOTION_MODEL_ID", "superb/wav2vec2-base-superb-er")
DEVICE = get_env("EMOTION_DEVICE", "cuda")
FALLBACK_DEVICE = "cpu"
SILENCE_TOP_DB = get_env_int("SILENCE_TOP_DB", 30)
SILENCE_AWKWARD_THRESHOLD_SEC = get_env_float("SILENCE_AWKWARD_THRESHOLD_SEC", 3.0)
SILENCE_HIGH_PRESSURE_THRESHOLD_SEC = get_env_float("SILENCE_HIGH_PRESSURE_THRESHOLD_SEC", 5.0)
MIN_EMOTION_CHUNK_SEC = get_env_float("MIN_EMOTION_CHUNK_SEC", 1.0)
MAX_BATCH_SIZE = get_env_int("PHASE_3_MAX_BATCH_SIZE", 100000)

SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}
PROCESSING_LOG_HEADERS = [
    "call_id",
    "status",
    "audio_path",
    "transcript_path",
    "json_output_path",
    "error_message",
    "processing_time_sec",
]


def ensure_phase_directories() -> None:
    ensure_directories(
        [
            INPUTS_DIR,
            INPUTS_TRANSCRIPTS_DIR,
            INPUTS_ENRICHED_JSON_DIR,
            INPUTS_MANUAL_REVIEWS_DIR,
            INPUTS_CORRECTED_CALLS_DIR,
            INPUTS_EXTERNAL_IMPORTS_DIR,
            LOCAL_AUDIO_INPUT_DIR,
            LOCAL_TRANSCRIPTS_DIR,
            COMBINED_FALLBACK_DIR,
            OUTPUTS_DIR,
            LOGS_DIR,
            MODELS_DIR,
            UTILS_DIR,
            JSON_OUTPUT_DIR,
            SUMMARIES_DIR,
            TIMELINES_DIR,
            METADATA_DIR,
        ]
    )
