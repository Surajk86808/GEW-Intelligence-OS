from __future__ import annotations

from pathlib import Path

from shared.config_utils import get_env, get_env_int
from shared.path_utils import ensure_directories

PROJECT_DIR = Path(__file__).resolve().parent

OUTPUTS_DIR = PROJECT_DIR / "outputs"
REASONING_OUTPUT_DIR = OUTPUTS_DIR / "reasoning"
METADATA_DIR = OUTPUTS_DIR / "metadata"
LOGS_DIR = PROJECT_DIR / "logs"

EMOTION_MANIFEST_CANDIDATES = [
    PROJECT_DIR.parent / "phase_3_voice_intelligence" / "outputs" / "metadata" / "emotion_manifest.json",
    PROJECT_DIR.parent / "phase_3_ai_reasoning_enrichment_layer" / "outputs" / "metadata" / "emotion_manifest.json",
]
TRANSCRIPT_MANIFEST_CANDIDATES = [
    PROJECT_DIR.parent / "phase_2_transcription" / "outputs" / "metadata" / "transcript_manifest.json",
]

REASONING_MANIFEST_PATH = METADATA_DIR / "reasoning_manifest.json"
FLAGGED_CALLS_PATH = METADATA_DIR / "flagged_calls.json"
RUNTIME_LOG_PATH = LOGS_DIR / "runtime_terminal.log"
PROCESSING_LOG_PATH = LOGS_DIR / "processing.log"

PROCESSING_LOG_HEADERS = [
    "call_id",
    "status",
    "objection_count",
    "intent_score",
    "risk_level",
    "conversion_probability",
    "quality_passed",
    "processing_time_sec",
    "error_message",
]

GEMINI_API_KEY = get_env("GEMINI_API_KEY", "")
PRIMARY_LLM_MODEL = get_env("PRIMARY_LLM_MODEL", "gemini-2.0-flash")
LLM_TEMPERATURE = get_env_int("LLM_TEMPERATURE", 15) / 100.0


def ensure_phase_directories() -> None:
    ensure_directories(
        [
            OUTPUTS_DIR,
            REASONING_OUTPUT_DIR,
            METADATA_DIR,
            LOGS_DIR,
        ]
    )
