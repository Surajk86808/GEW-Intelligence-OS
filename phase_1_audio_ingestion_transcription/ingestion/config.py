from __future__ import annotations

from pathlib import Path

from shared.constants import DATA_DIR, WORKSPACE_DIR
from shared.path_utils import ensure_directories

PROJECT_DIR = Path(__file__).resolve().parent

INPUTS_DIR = PROJECT_DIR / "input"
OUTPUTS_DIR = PROJECT_DIR / "outputs"
LOGS_DIR = PROJECT_DIR / "logs"

AUDIO_OUTPUT_DIR = PROJECT_DIR / "audio"
METADATA_OUTPUT_DIR = PROJECT_DIR / "mapped_calls"
WORKBOOK_OUTPUT_DIR = METADATA_OUTPUT_DIR / "workbook"

DEFAULT_INPUT_EXCEL = INPUTS_DIR / "calls.xlsx"
UPDATED_WORKBOOK_PATH = WORKBOOK_OUTPUT_DIR / "updated_calls.xlsx"
MAPPED_CALLS_PATH = METADATA_OUTPUT_DIR / "mapped_calls.csv"
CALL_MANIFEST_PATH = METADATA_OUTPUT_DIR / "call_manifest.json"
LEAD_PROFILES_DIR = METADATA_OUTPUT_DIR / "lead_profiles"
UNMATCHED_LOG_PATH = LOGS_DIR / "unmatched_numbers.csv"
INGESTION_LOG_PATH = LOGS_DIR / "ingestion_log.csv"
RUNTIME_LOG_PATH = LOGS_DIR / "runtime_terminal.log"

COMBINED_SHEET_NAME = "Combined"
CALLS_SHEET_NAME = "Sheet1"

COMBINED_NUMBER_COLUMN = "Number"
COMBINED_FALLBACK_NUMBER_COLUMN = "Concat"
COMBINED_OWNER_COLUMN = "owner"
COMBINED_CAMPAIGN_COLUMN = "Campaign"
COMBINED_WALKIN_STATUS_COLUMN = "Walkin Status"

CALL_RECORDING_URL_COLUMN = "recording_urls"
CALL_DURATION_COLUMN = "duration"
CALLER_PHONE_COLUMN = "caller_phone_number"

CALL_ID_COLUMN = "call_id"
LEAD_NUMBER_COLUMN = "lead_number"
NORMALIZED_PHONE_COLUMN = "normalized_phone"
AUDIO_PATH_COLUMN = "audio_path"
DOWNLOAD_STATUS_COLUMN = "audio_download_status"
DOWNLOAD_ERROR_COLUMN = "audio_download_error"
MATCHED_CALL_COUNT_COLUMN = "matched_call_count"

DOWNLOAD_TIMEOUT_SECONDS = 60
DOWNLOAD_RETRIES = 1

INGESTION_LOG_HEADERS = [
    "call_id",
    "status",
    "audio_path",
    "error_message",
]

UNMATCHED_LOG_HEADERS = [
    "combined_number",
    "concat_value",
    "reason_unmatched",
]


def ensure_phase_directories() -> None:
    ensure_directories(
        [
            INPUTS_DIR,
            OUTPUTS_DIR,
            LOGS_DIR,
            AUDIO_OUTPUT_DIR,
            METADATA_OUTPUT_DIR,
            WORKBOOK_OUTPUT_DIR,
            LEAD_PROFILES_DIR,
        ]
    )


def discover_input_excel(silent: bool = False) -> Path:
    if DEFAULT_INPUT_EXCEL.exists():
        return DEFAULT_INPUT_EXCEL

    candidates = sorted(path for path in DATA_DIR.glob("*.xlsx") if not path.name.startswith("~$"))
    if candidates:
        return candidates[0]
        
    if silent:
        return DEFAULT_INPUT_EXCEL
        
    raise FileNotFoundError(f"No Excel workbook found in {INPUTS_DIR} or {DATA_DIR}. Please provide a master sheet.")

