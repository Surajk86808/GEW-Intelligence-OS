"""
Audio Classification Module
Categorizes audio files into successful and unsuccessful directories
based on CRM Walking Status.
"""

import sys
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
from tqdm import tqdm

# Configuration Paths
INGESTION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = INGESTION_DIR.parent.parent
EXCEL_FILE = PROJECT_ROOT / "data" / "Inbound Calls GEW - Mastersheet.xlsx"

AUDIO_DIR = INGESTION_DIR / "audio"
SUCCESSFUL_DIR = INGESTION_DIR / "successful_audio"
UNSUCCESSFUL_DIR = INGESTION_DIR / "unsuccessful_audio"
OUTPUTS_DIR = INGESTION_DIR / "outputs"
REPORT_PATH = OUTPUTS_DIR / "call_classification_report.json"
LOG_FILE = OUTPUTS_DIR / "audio_classification.log"


def setup_environment() -> None:
    """Create necessary directories and configure logging."""
    SUCCESSFUL_DIR.mkdir(parents=True, exist_ok=True)
    UNSUCCESSFUL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def find_column_dynamically(df: pd.DataFrame, keywords: list[str]) -> Optional[str]:
    """
    Finds a column in the DataFrame that contains all the specified keywords.
    Case-insensitive search.
    """
    for col in df.columns:
        col_str = str(col).lower()
        if all(kw in col_str for kw in keywords):
            return col
    return None


def is_empty_status(status: Any) -> bool:
    """Check if the walking status is empty, null, or blank."""
    if pd.isna(status):
        return True
    status_str = str(status).strip().lower()
    return status_str in ["", "nan", "none", "null", "nat"]


def get_audio_files_mapping(audio_dir: Path) -> Dict[str, Path]:
    """
    Scans the audio directory and returns a mapping of
    Call ID (filename stem) to the actual Path object.
    """
    if not audio_dir.exists():
        logging.error(f"Source audio directory not found: {audio_dir}")
        return {}
    return {f.stem: f for f in audio_dir.iterdir() if f.is_file()}


def process_call_classification(
    df: pd.DataFrame,
    walking_status_col: str,
    call_id_col: str,
    audio_map: Dict[str, Path]
) -> Dict[str, Any]:
    """
    Iterate through the DataFrame and classify audio files based on walking status.
    Returns a detailed report dictionary.
    """
    report = {
        "total_processed": 0,
        "successful_calls": 0,
        "unsuccessful_calls": 0,
        "empty_walking_status_skipped": 0,
        "missing_audio_files": [],
        "unmatched_call_ids": [],
        "duplicate_entries": []
    }

    processed_call_ids = set()

    for index, row in tqdm(df.iterrows(), total=len(df), desc="Classifying Audio"):
        walk_status = row.get(walking_status_col)
        call_id_raw = row.get(call_id_col)

        # 1. Ignore rows where Walking Status is empty/null/blank
        if is_empty_status(walk_status):
            report["empty_walking_status_skipped"] += 1
            continue

        report["total_processed"] += 1
        walk_status_str = str(walk_status).strip()

        # Safe parsing of CALL_ID
        call_id = str(call_id_raw).strip() if pd.notna(call_id_raw) else ""
        if not call_id or call_id.lower() == "nan":
            report["unmatched_call_ids"].append(f"Row {index}: Missing Call ID")
            continue

        # Match CALL_ID logic -> using filename stem exactly like crm_mapping IDs
        clean_call_id = Path(call_id).stem

        # 2. Handle duplicates
        if clean_call_id in processed_call_ids:
            report["duplicate_entries"].append(clean_call_id)
            continue
        processed_call_ids.add(clean_call_id)

        # 3. Match Audio File
        source_audio_path = audio_map.get(clean_call_id)
        if not source_audio_path:
            report["missing_audio_files"].append(clean_call_id)
            continue

        # 4. Classification Rule
        if walk_status_str.lower() == "visited":
            classification = "successful"
            dest_dir = SUCCESSFUL_DIR
            report["successful_calls"] += 1
        else:
            classification = "unsuccessful"
            dest_dir = UNSUCCESSFUL_DIR
            report["unsuccessful_calls"] += 1

        dest_audio_path = dest_dir / source_audio_path.name

        # 5. Copy file to categorized directory safely
        try:
            shutil.copy2(source_audio_path, dest_audio_path)
        except Exception as e:
            logging.error(f"Failed to copy {source_audio_path.name}: {e}")
            continue

        # 6. Generate per-call metadata JSON
        metadata = {
            "call_id": clean_call_id,
            "walking_status": walk_status_str,
            "classification": classification,
            "audio_file": source_audio_path.name,
            "source_path": str(source_audio_path.resolve()),
            "destination_path": str(dest_audio_path.resolve())
        }

        metadata_path = dest_dir / f"{clean_call_id}_metadata.json"
        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to write metadata for {clean_call_id}: {e}")

    return report


def main():
    setup_environment()
    logging.info("Starting Audio Classification based on CRM Walking Status...")

    if not EXCEL_FILE.exists():
        logging.error(f"Excel file not found at {EXCEL_FILE}. Exiting.")
        return

    # Inject project root and phase root to sys.path to allow GEW engine imports
    phase_root = INGESTION_DIR.parent
    
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    if str(phase_root) not in sys.path:
        sys.path.insert(0, str(phase_root))

    try:
        from ingestion.engines.crm_mapping import map_leads_to_calls, prepare_workbook
        from shared.workbook_utils import load_workbook_sheets
        from ingestion.config import COMBINED_SHEET_NAME, CALLS_SHEET_NAME
    except ImportError as e:
        logging.error(f"Failed to import GEW core modules: {e}")
        logging.error("Make sure your project structure is intact at P:\\Gew")
        return

    logging.info("Loading CRM Master Sheet using GEW mapping engine...")
    try:
        combined_df, calls_df = load_workbook_sheets(EXCEL_FILE, COMBINED_SHEET_NAME, CALLS_SHEET_NAME)
        combined_df, calls_df = prepare_workbook(combined_df, calls_df)
        df, _, _ = map_leads_to_calls(combined_df, calls_df)
    except Exception as e:
        logging.error(f"Failed to process CRM mapping: {e}")
        return

    walking_status_col = find_column_dynamically(df, ["walk", "status"])
    call_id_col = find_column_dynamically(df, ["call", "id"])

    if not walking_status_col:
        logging.error("Could not dynamically detect 'Walking Status' column. Exiting.")
        return

    if not call_id_col:
        logging.warning("Could not dynamically detect 'Call ID' column. Checking fallback...")
        call_id_col = "call_id" # Default fallback for the mapped dataframe

    logging.info(f"Targeting Columns -> Status: '{walking_status_col}', Call ID: '{call_id_col}'")

    audio_map = get_audio_files_mapping(AUDIO_DIR)
    logging.info(f"Loaded {len(audio_map)} source audio files.")

    report = process_call_classification(df, walking_status_col, call_id_col, audio_map)

    # Save Detailed JSON Report
    try:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logging.info(f"Report generated successfully at {REPORT_PATH}")
    except Exception as e:
        logging.error(f"Failed to generate output report: {e}")

    logging.info("Audio Classification Process Completed.")


if __name__ == "__main__":
    main()