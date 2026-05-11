from __future__ import annotations

from pathlib import Path

from shared.config_utils import get_env, get_env_float, get_env_int
from shared.path_utils import ensure_directories

PROJECT_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_DIR.parent.parent

INPUTS_DIR = PROJECT_DIR / "inputs"
INPUTS_TRANSCRIPTS_DIR = INPUTS_DIR / "transcripts"
INPUTS_EMOTIONS_DIR = INPUTS_DIR / "emotions"
INPUTS_CRM_DIR = INPUTS_DIR / "crm"
INPUTS_METADATA_DIR = INPUTS_DIR / "metadata"

OUTPUTS_DIR = PROJECT_DIR / "outputs"
JSON_OUTPUT_DIR = OUTPUTS_DIR / "json"
REPORTS_DIR = OUTPUTS_DIR / "reports"
SUMMARIES_DIR = OUTPUTS_DIR / "summaries"
EVIDENCE_DIR = OUTPUTS_DIR / "evidence"

PROMPTS_DIR = PROJECT_DIR / "prompts"
LOGS_DIR = PROJECT_DIR / "logs"
VECTOR_STORE_DIR = PROJECT_DIR / "vector_store"
CACHE_DIR = VECTOR_STORE_DIR / "cache"
CHUNK_INDEX_DIR = VECTOR_STORE_DIR / "chunks"

RUNTIME_LOG_PATH = LOGS_DIR / "runtime_terminal.log"
PROCESSING_LOG_PATH = LOGS_DIR / "phase_4_processing_log.csv"
MALFORMED_OUTPUT_LOG_PATH = LOGS_DIR / "malformed_output_log.csv"
REASONING_MANIFEST_PATH = OUTPUTS_DIR / "metadata" / "reasoning_manifest.json"
OUTPUTS_METADATA_DIR = OUTPUTS_DIR / "metadata"

LOCAL_TRANSCRIPT_MANIFEST_PATH = INPUTS_METADATA_DIR / "transcript_manifest.json"
LOCAL_EMOTION_MANIFEST_PATH = INPUTS_METADATA_DIR / "emotion_manifest.json"
LOCAL_CALL_MANIFEST_PATH = INPUTS_METADATA_DIR / "call_manifest.json"

TRANSCRIPT_MANIFEST_CANDIDATES = [
    LOCAL_TRANSCRIPT_MANIFEST_PATH,
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "transcription" / "outputs" / "metadata" / "transcript_manifest.json",
]
EMOTION_MANIFEST_CANDIDATES = [
    LOCAL_EMOTION_MANIFEST_PATH,
    REPO_ROOT / "phase_2_enrichment_structured_extraction" / "enrichment" / "outputs" / "metadata" / "emotion_manifest.json",
]
CALL_MANIFEST_CANDIDATES = [
    LOCAL_CALL_MANIFEST_PATH,
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "ingestion" / "mapped_calls" / "call_manifest.json",
]
LEAD_PROFILE_DIR_CANDIDATES = [
    INPUTS_CRM_DIR / "lead_profiles",
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "ingestion" / "mapped_calls" / "lead_profiles",
]

LLM_PROVIDER = get_env("PHASE_4_LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = get_env("GEMINI_API_KEY", "")
PRIMARY_LLM_MODEL = get_env("PRIMARY_LLM_MODEL", "gemini-2.5-pro")
LLM_TEMPERATURE = get_env_float("LLM_TEMPERATURE", 0.1)
MAX_RETRIEVAL_CHUNKS = get_env_int("PHASE_4_MAX_RETRIEVAL_CHUNKS", 8)
TRANSCRIPT_CHUNK_LINE_COUNT = get_env_int("PHASE_4_CHUNK_LINE_COUNT", 12)
MAX_BATCH_SIZE = get_env_int("PHASE_4_MAX_BATCH_SIZE", 100000)
RESPONSE_CACHE_ENABLED = get_env("PHASE_4_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}
DEFAULT_INPUT_HASH_VERSION = "phase4-v1"

PROCESSING_LOG_HEADERS = [
    "call_id",
    "status",
    "json_output_path",
    "report_path",
    "error_message",
    "processing_time_sec",
    "input_tokens",
    "output_tokens",
    "estimated_cost_usd",
]
MALFORMED_OUTPUT_LOG_HEADERS = [
    "call_id",
    "error_message",
    "raw_output_excerpt",
]


def ensure_phase_directories() -> None:
    ensure_directories(
        [
            INPUTS_DIR,
            INPUTS_TRANSCRIPTS_DIR,
            INPUTS_EMOTIONS_DIR,
            INPUTS_CRM_DIR,
            INPUTS_METADATA_DIR,
            OUTPUTS_DIR,
            JSON_OUTPUT_DIR,
            REPORTS_DIR,
            SUMMARIES_DIR,
            EVIDENCE_DIR,
            OUTPUTS_METADATA_DIR,
            PROMPTS_DIR,
            LOGS_DIR,
            VECTOR_STORE_DIR,
            CACHE_DIR,
            CHUNK_INDEX_DIR,
        ]
    )

