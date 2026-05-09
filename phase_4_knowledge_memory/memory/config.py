from __future__ import annotations

from pathlib import Path

from shared.config_utils import get_env, get_env_float, get_env_int
from shared.path_utils import ensure_directories

PROJECT_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_DIR.parent.parent

INPUTS_DIR = PROJECT_DIR / "inputs"
INPUTS_TRANSCRIPTS_DIR = INPUTS_DIR / "transcripts"
INPUTS_REASONING_DIR = INPUTS_DIR / "reasoning"
INPUTS_EMOTIONS_DIR = INPUTS_DIR / "emotions"
INPUTS_CRM_DIR = INPUTS_DIR / "crm"

VECTOR_STORE_DIR = PROJECT_DIR / "vector_store"
METADATA_STORE_DIR = PROJECT_DIR / "metadata_store"
INDEXES_DIR = PROJECT_DIR / "indexes"
CACHE_DIR = PROJECT_DIR / "cache"
LOGS_DIR = PROJECT_DIR / "logs"

OUTPUTS_DIR = PROJECT_DIR / "outputs"
RETRIEVAL_OUTPUT_DIR = OUTPUTS_DIR / "retrieval"
ANALYTICS_OUTPUT_DIR = OUTPUTS_DIR / "analytics"
DEBUG_OUTPUT_DIR = OUTPUTS_DIR / "debug"
QUERY_OUTPUT_DIR = OUTPUTS_DIR / "query_responses"

RUNTIME_LOG_PATH = LOGS_DIR / "runtime_terminal.log"
PROCESSING_LOG_PATH = LOGS_DIR / "phase_5_processing_log.csv"
RETRIEVAL_LOG_PATH = LOGS_DIR / "retrieval_diagnostics.csv"
QUERY_LOG_PATH = LOGS_DIR / "query_intelligence_log.csv"
MEMORY_MANIFEST_PATH = METADATA_STORE_DIR / "memory_manifest.json"
CHUNK_STORE_PATH = METADATA_STORE_DIR / "chunk_store.json"
VECTOR_INDEX_PATH = VECTOR_STORE_DIR / "vector_index.json"
EMBEDDING_CACHE_PATH = CACHE_DIR / "embedding_cache.json"
CUSTOMER_INDEX_PATH = INDEXES_DIR / "customer_index.json"
SALESPERSON_INDEX_PATH = INDEXES_DIR / "salesperson_index.json"
OBJECTION_INDEX_PATH = INDEXES_DIR / "objection_index.json"
CALL_INDEX_PATH = INDEXES_DIR / "call_index.json"
SESSION_MEMORY_PATH = METADATA_STORE_DIR / "query_session_memory.json"
QUERY_HISTORY_PATH = METADATA_STORE_DIR / "query_history.json"
EVIDENCE_LOOKUP_PATH = DEBUG_OUTPUT_DIR / "evidence_lookup.json"
CALL_ANALYTICS_PATH = ANALYTICS_OUTPUT_DIR / "call_analytics.json"

LOCAL_TRANSCRIPT_MANIFEST_PATH = INPUTS_TRANSCRIPTS_DIR / "transcript_manifest.json"
LOCAL_REASONING_MANIFEST_PATH = INPUTS_REASONING_DIR / "reasoning_manifest.json"
LOCAL_EMOTION_MANIFEST_PATH = INPUTS_EMOTIONS_DIR / "emotion_manifest.json"
LOCAL_CALL_MANIFEST_PATH = INPUTS_CRM_DIR / "call_manifest.json"
DIRECT_ENRICHED_TRANSCRIPT_DIR_CANDIDATES = [
    REPO_ROOT
    / "phase_2_enrichment_structured_extraction"
    / "enrichment"
    / "transcripts"
    / "transcripit_enriched_by_gemini",
]

TRANSCRIPT_MANIFEST_CANDIDATES = [
    LOCAL_TRANSCRIPT_MANIFEST_PATH,
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "phase_2_transcription" / "outputs" / "metadata" / "transcript_manifest.json",
    REPO_ROOT / "phase_2_transcription" / "outputs" / "metadata" / "transcript_manifest.json",
]
REASONING_MANIFEST_CANDIDATES = [
    LOCAL_REASONING_MANIFEST_PATH,
    PROJECT_DIR / "outputs" / "metadata" / "reasoning_manifest.json",
    REPO_ROOT / "phase_3_ai_reasoning" / "phase_4_ai_reasoning" / "outputs" / "metadata" / "reasoning_manifest.json",
    REPO_ROOT / "phase_4_ai_reasoning" / "outputs" / "metadata" / "reasoning_manifest.json",
]
EMOTION_MANIFEST_CANDIDATES = [
    LOCAL_EMOTION_MANIFEST_PATH,
    REPO_ROOT / "phase_2_enrichment_structured_extraction" / "phase_3_voice_intelligence" / "outputs" / "metadata" / "emotion_manifest.json",
    REPO_ROOT / "phase_3_voice_intelligence" / "outputs" / "metadata" / "emotion_manifest.json",
]
CALL_MANIFEST_CANDIDATES = [
    LOCAL_CALL_MANIFEST_PATH,
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "phase_1_map_and_download" / "mapped_calls" / "call_manifest.json",
    REPO_ROOT / "phase_1_map_and_download" / "mapped_calls" / "call_manifest.json",
]
LEAD_PROFILE_DIR_CANDIDATES = [
    INPUTS_CRM_DIR / "lead_profiles",
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "phase_1_map_and_download" / "mapped_calls" / "lead_profiles",
    REPO_ROOT / "phase_1_map_and_download" / "mapped_calls" / "lead_profiles",
]

CHUNK_MAX_LINES = get_env_int("PHASE_5_CHUNK_MAX_LINES", 8)
MIN_CHUNK_LINES = get_env_int("PHASE_5_MIN_CHUNK_LINES", 3)
EMBEDDING_DIMENSION = get_env_int("PHASE_5_EMBEDDING_DIMENSION", 256)
MAX_BATCH_SIZE = get_env_int("PHASE_5_MAX_BATCH_SIZE", 100000)
TOP_K_RETRIEVAL = get_env_int("PHASE_5_TOP_K_RETRIEVAL", 10)
QUERY_TOP_K = get_env_int("PHASE_5_QUERY_TOP_K", 8)
MIN_RELEVANCE_SCORE = get_env_float("PHASE_5_MIN_RELEVANCE_SCORE", 0.08)
EMBEDDING_PROVIDER = get_env("PHASE_5_EMBEDDING_PROVIDER", "hashing").lower()
ENABLE_HYBRID_KEYWORD_BOOST = get_env("PHASE_5_ENABLE_HYBRID_KEYWORD_BOOST", "true").lower() in {"1", "true", "yes"}
QUERY_LLM_PROVIDER = get_env("PHASE_5_QUERY_LLM_PROVIDER", "gemini").lower()
QUERY_LLM_MODEL = get_env("PHASE_5_QUERY_LLM_MODEL", "gemini-2.0-flash")
QUERY_LLM_TEMPERATURE = get_env_float("PHASE_5_QUERY_LLM_TEMPERATURE", 0.1)
QUERY_MIN_CONFIDENCE = get_env_float("PHASE_5_QUERY_MIN_CONFIDENCE", 0.45)

PROCESSING_LOG_HEADERS = [
    "call_id",
    "status",
    "chunk_count",
    "vector_count",
    "error_message",
    "processing_time_sec",
]
RETRIEVAL_LOG_HEADERS = [
    "query_name",
    "result_count",
    "top_score",
    "filters",
]
QUERY_LOG_HEADERS = [
    "session_id",
    "query",
    "status",
    "retrieved_results",
    "confidence",
    "output_path",
    "error_message",
    "processing_time_sec",
]

SAMPLE_RETRIEVAL_QUERIES = [
    {
        "name": "pricing_objections_with_conversion",
        "query": "pricing objection converted customer budget price expensive follow up closed",
        "filters": {"reasoning_tags_any": ["pricing concern"], "min_conversion_probability": 0.5},
    },
    {
        "name": "frustrated_competitor_calls",
        "query": "frustrated competitor current provider comparison not happy",
        "filters": {"emotion_any": ["frustrated", "angry"], "reasoning_tags_any": ["competitor"]},
    },
    {
        "name": "positive_closing_conversations",
        "query": "interested confident closing send pricing next step convert",
        "filters": {"emotion_any": ["interested", "confident", "excited"], "min_conversion_probability": 0.5},
    },
]


def ensure_phase_directories() -> None:
    ensure_directories(
        [
            INPUTS_DIR,
            INPUTS_TRANSCRIPTS_DIR,
            INPUTS_REASONING_DIR,
            INPUTS_EMOTIONS_DIR,
            INPUTS_CRM_DIR,
            VECTOR_STORE_DIR,
            METADATA_STORE_DIR,
            INDEXES_DIR,
            CACHE_DIR,
            LOGS_DIR,
            OUTPUTS_DIR,
            RETRIEVAL_OUTPUT_DIR,
            ANALYTICS_OUTPUT_DIR,
            DEBUG_OUTPUT_DIR,
            QUERY_OUTPUT_DIR,
        ]
    )
