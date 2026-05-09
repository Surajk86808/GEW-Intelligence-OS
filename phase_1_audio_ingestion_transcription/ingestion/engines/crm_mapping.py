from __future__ import annotations

from typing import Any

import pandas as pd

from ingestion.config import (
    AUDIO_PATH_COLUMN,
    CALLER_PHONE_COLUMN,
    CALL_DURATION_COLUMN,
    CALL_ID_COLUMN,
    CALL_RECORDING_URL_COLUMN,
    COMBINED_CAMPAIGN_COLUMN,
    COMBINED_FALLBACK_NUMBER_COLUMN,
    COMBINED_NUMBER_COLUMN,
    COMBINED_OWNER_COLUMN,
    COMBINED_WALKIN_STATUS_COLUMN,
    DOWNLOAD_ERROR_COLUMN,
    DOWNLOAD_STATUS_COLUMN,
    LEAD_NUMBER_COLUMN,
    MATCHED_CALL_COUNT_COLUMN,
    NORMALIZED_PHONE_COLUMN,
)
from shared.phone_utils import normalize_phone_number


def prepare_workbook(combined_df: pd.DataFrame, calls_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    combined_df = combined_df.copy()
    calls_df = calls_df.copy()

    _validate_combined_sheet(combined_df)
    _validate_calls_sheet(calls_df)

    combined_df[COMBINED_NUMBER_COLUMN] = combined_df[COMBINED_NUMBER_COLUMN].fillna("").astype(str)
    combined_df[COMBINED_FALLBACK_NUMBER_COLUMN] = combined_df[COMBINED_FALLBACK_NUMBER_COLUMN].fillna("").astype(str)
    combined_df[LEAD_NUMBER_COLUMN] = combined_df.apply(_derive_lead_number, axis=1)
    combined_df[NORMALIZED_PHONE_COLUMN] = combined_df[LEAD_NUMBER_COLUMN].apply(normalize_phone_number)
    if MATCHED_CALL_COUNT_COLUMN not in combined_df.columns:
        combined_df[MATCHED_CALL_COUNT_COLUMN] = ""

    calls_df[CALL_RECORDING_URL_COLUMN] = calls_df[CALL_RECORDING_URL_COLUMN].fillna("").astype(str)
    calls_df[CALLER_PHONE_COLUMN] = calls_df[CALLER_PHONE_COLUMN].fillna("").astype(str)
    calls_df[NORMALIZED_PHONE_COLUMN] = calls_df[CALLER_PHONE_COLUMN].apply(normalize_phone_number)

    for column in (LEAD_NUMBER_COLUMN, AUDIO_PATH_COLUMN, DOWNLOAD_STATUS_COLUMN, DOWNLOAD_ERROR_COLUMN):
        if column not in calls_df.columns:
            calls_df[column] = ""
        else:
            calls_df[column] = calls_df[column].fillna("").astype(str)

    if CALL_ID_COLUMN not in calls_df.columns:
        calls_df.insert(0, CALL_ID_COLUMN, "")
    calls_df[CALL_ID_COLUMN] = calls_df[CALL_ID_COLUMN].fillna("").astype(str)

    for index in calls_df.index:
        if not str(calls_df.at[index, CALL_ID_COLUMN]).strip():
            calls_df.at[index, CALL_ID_COLUMN] = f"CALL_{index + 1:04d}"

    return combined_df, calls_df


def map_leads_to_calls(combined_df: pd.DataFrame, calls_df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, str]], dict[str, dict[str, Any]]]:
    call_lookup: dict[str, list[int]] = {}
    for call_index, call_row in calls_df.iterrows():
        normalized = str(call_row.get(NORMALIZED_PHONE_COLUMN, "")).strip()
        if normalized:
            call_lookup.setdefault(normalized, []).append(call_index)

    mapped_rows: list[dict[str, Any]] = []
    unmatched_rows: list[dict[str, str]] = []
    lead_profiles: dict[str, dict[str, Any]] = {}
    mapped_lead_numbers: set[str] = set()

    for combined_index, lead_row in combined_df.iterrows():
        normalized_lead_number = str(lead_row.get(NORMALIZED_PHONE_COLUMN, "")).strip()
        original_number = str(lead_row.get(COMBINED_NUMBER_COLUMN, "")).strip()
        fallback_number = str(lead_row.get(COMBINED_FALLBACK_NUMBER_COLUMN, "")).strip()

        if not normalized_lead_number:
            unmatched_rows.append(
                {
                    "combined_number": original_number,
                    "concat_value": fallback_number,
                    "reason_unmatched": "missing normalized phone number",
                }
            )
            continue

        matched_calls = call_lookup.get(normalized_lead_number, [])
        if not matched_calls:
            unmatched_rows.append(
                {
                    "combined_number": original_number,
                    "concat_value": fallback_number,
                    "reason_unmatched": "no call records matched",
                }
            )
            continue

        lead_profile = lead_profiles.setdefault(
            normalized_lead_number,
            {
                "lead_number": normalized_lead_number,
                "owner": str(lead_row.get(COMBINED_OWNER_COLUMN, "")).strip(),
                "campaign": str(lead_row.get(COMBINED_CAMPAIGN_COLUMN, "")).strip(),
                "walkin_status": str(lead_row.get(COMBINED_WALKIN_STATUS_COLUMN, "")).strip(),
                "combined_indices": [],
                "calls": [],
            },
        )
        lead_profile["combined_indices"].append(combined_index)

        if normalized_lead_number in mapped_lead_numbers:
            continue

        mapped_lead_numbers.add(normalized_lead_number)
        for call_index in matched_calls:
            call_row = calls_df.loc[call_index]
            mapped_rows.append(
                {
                    "lead_number": normalized_lead_number,
                    "owner": lead_profile["owner"],
                    "campaign": lead_profile["campaign"],
                    "walkin_status": lead_profile["walkin_status"],
                    "call_id": str(call_row.get(CALL_ID_COLUMN, "")).strip(),
                    "recording_url": str(call_row.get(CALL_RECORDING_URL_COLUMN, "")).strip(),
                    "duration": call_row.get(CALL_DURATION_COLUMN, ""),
                    "audio_path": str(call_row.get(AUDIO_PATH_COLUMN, "")).strip(),
                    "download_status": str(call_row.get(DOWNLOAD_STATUS_COLUMN, "")).strip(),
                    "download_error": str(call_row.get(DOWNLOAD_ERROR_COLUMN, "")).strip(),
                    "call_row_index": call_index,
                }
            )

    for lead_number, lead_profile in lead_profiles.items():
        call_count = sum(1 for row in mapped_rows if row["lead_number"] == lead_number)
        for combined_index in lead_profile["combined_indices"]:
            combined_df.at[combined_index, MATCHED_CALL_COUNT_COLUMN] = str(call_count)

    return pd.DataFrame(mapped_rows), unmatched_rows, lead_profiles


def _derive_lead_number(row: pd.Series) -> str:
    primary = str(row.get(COMBINED_NUMBER_COLUMN, "")).strip()
    if primary:
        return primary
    return str(row.get(COMBINED_FALLBACK_NUMBER_COLUMN, "")).strip()


def _validate_combined_sheet(dataframe: pd.DataFrame) -> None:
    required_columns = {COMBINED_NUMBER_COLUMN, COMBINED_FALLBACK_NUMBER_COLUMN}
    missing = sorted(required_columns - set(dataframe.columns))
    if missing:
        raise ValueError(f"Missing required columns in combined sheet: {', '.join(missing)}")


def _validate_calls_sheet(dataframe: pd.DataFrame) -> None:
    required_columns = {CALL_RECORDING_URL_COLUMN, CALLER_PHONE_COLUMN}
    missing = sorted(required_columns - set(dataframe.columns))
    if missing:
        raise ValueError(f"Missing required columns in calls sheet: {', '.join(missing)}")
