from __future__ import annotations

from pathlib import Path

from shared.config_utils import get_env, get_env_float, get_env_int
from shared.path_utils import ensure_directories

PROJECT_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_DIR.parent.parent

QUERY_ENGINE_DIR = PROJECT_DIR / "query_engine"
RETRIEVAL_DIR = PROJECT_DIR / "retrieval"
REASONING_DIR = PROJECT_DIR / "reasoning"
EVIDENCE_DIR = PROJECT_DIR / "evidence"
ANALYTICS_DIR = PROJECT_DIR / "analytics"
REPORTS_DIR = PROJECT_DIR / "reports"
PROMPTS_DIR = PROJECT_DIR / "prompts"
LOGS_DIR = PROJECT_DIR / "logs"

OUTPUTS_DIR = PROJECT_DIR / "outputs"
JSON_OUTPUT_DIR = OUTPUTS_DIR / "json"
REPORTS_OUTPUT_DIR = OUTPUTS_DIR / "reports"
EVIDENCE_OUTPUT_DIR = OUTPUTS_DIR / "evidence"
DASHBOARDS_OUTPUT_DIR = OUTPUTS_DIR / "dashboards"

RUNTIME_LOG_PATH = LOGS_DIR / "runtime_terminal.log"
QUERY_LOG_PATH = LOGS_DIR / "query_log.csv"
DIAGNOSTICS_LOG_PATH = LOGS_DIR / "diagnostics_log.csv"
DEFAULT_QUERIES_PATH = QUERY_ENGINE_DIR / "default_queries.json"

PHASE_5_CHUNK_STORE_CANDIDATES = [
    REPO_ROOT / "phase_4_knowledge_memory" / "memory" / "metadata_store" / "chunk_store.json",
    REPO_ROOT / "phase_4_knowledge_memory" / "phase_5_knowledge_layer" / "metadata_store" / "chunk_store.json",
    REPO_ROOT / "phase_5_knowledge_layer" / "metadata_store" / "chunk_store.json",
]
PHASE_5_VECTOR_INDEX_CANDIDATES = [
    REPO_ROOT / "phase_4_knowledge_memory" / "memory" / "vector_store" / "vector_index.json",
    REPO_ROOT / "phase_4_knowledge_memory" / "phase_5_knowledge_layer" / "vector_store" / "vector_index.json",
    REPO_ROOT / "phase_5_knowledge_layer" / "vector_store" / "vector_index.json",
]
PHASE_5_EVIDENCE_LOOKUP_CANDIDATES = [
    REPO_ROOT / "phase_4_knowledge_memory" / "memory" / "outputs" / "debug" / "evidence_lookup.json",
    REPO_ROOT / "phase_4_knowledge_memory" / "phase_5_knowledge_layer" / "outputs" / "debug" / "evidence_lookup.json",
    REPO_ROOT / "phase_5_knowledge_layer" / "outputs" / "debug" / "evidence_lookup.json",
]
PHASE_5_CALL_ANALYTICS_CANDIDATES = [
    REPO_ROOT / "phase_4_knowledge_memory" / "memory" / "outputs" / "analytics" / "call_analytics.json",
    REPO_ROOT / "phase_4_knowledge_memory" / "phase_5_knowledge_layer" / "outputs" / "analytics" / "call_analytics.json",
    REPO_ROOT / "phase_5_knowledge_layer" / "outputs" / "analytics" / "call_analytics.json",
]
PHASE_4_MANIFEST_CANDIDATES = [
    REPO_ROOT / "phase_3_ai_reasoning" / "reasoning" / "outputs" / "metadata" / "reasoning_manifest.json",
]
PHASE_1_CALL_MANIFEST_CANDIDATES = [
    REPO_ROOT / "phase_1_audio_ingestion_transcription" / "ingestion" / "mapped_calls" / "call_manifest.json",
]

LLM_PROVIDER = get_env("PHASE_6_LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = get_env("GEMINI_API_KEY", "")
PRIMARY_LLM_MODEL = get_env("PRIMARY_LLM_MODEL", "gemini-2.5-flash")
LLM_TEMPERATURE = get_env_float("PHASE_6_LLM_TEMPERATURE", 0.1)
MAX_RETRIEVAL_RESULTS = get_env_int("PHASE_6_MAX_RETRIEVAL_RESULTS", 12)
MAX_EVIDENCE_ITEMS = get_env_int("PHASE_6_MAX_EVIDENCE_ITEMS", 8)
QUERY_TIMEOUT_SEC = get_env_int("PHASE_6_QUERY_TIMEOUT_SEC", 60)
MIN_CONFIDENCE = get_env_float("PHASE_6_MIN_CONFIDENCE", 0.2)

QUERY_LOG_HEADERS = [
    "query_name",
    "status",
    "query_text",
    "retrieved_results",
    "confidence",
    "processing_time_sec",
    "error_message",
    "input_tokens",
    "output_tokens",
    "estimated_cost_usd",
]
DIAGNOSTICS_LOG_HEADERS = [
    "query_name",
    "query_type",
    "filters",
    "top_score",
    "evidence_count",
]


def ensure_phase_directories() -> None:
    ensure_directories(
        [
            QUERY_ENGINE_DIR,
            RETRIEVAL_DIR,
            REASONING_DIR,
            EVIDENCE_DIR,
            ANALYTICS_DIR,
            REPORTS_DIR,
            PROMPTS_DIR,
            LOGS_DIR,
            OUTPUTS_DIR,
            JSON_OUTPUT_DIR,
            REPORTS_OUTPUT_DIR,
            EVIDENCE_OUTPUT_DIR,
            DASHBOARDS_OUTPUT_DIR,
        ]
    )

