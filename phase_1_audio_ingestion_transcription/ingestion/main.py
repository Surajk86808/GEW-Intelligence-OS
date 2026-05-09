from __future__ import annotations

import sys

from ingestion.config import (
    AUDIO_PATH_COLUMN,
    CALL_MANIFEST_PATH,
    CALLS_SHEET_NAME,
    COMBINED_SHEET_NAME,
    DOWNLOAD_ERROR_COLUMN,
    DOWNLOAD_STATUS_COLUMN,
    INGESTION_LOG_HEADERS,
    INGESTION_LOG_PATH,
    LEAD_NUMBER_COLUMN,
    LEAD_PROFILES_DIR,
    MAPPED_CALLS_PATH,
    RUNTIME_LOG_PATH,
    UNMATCHED_LOG_HEADERS,
    UNMATCHED_LOG_PATH,
    UPDATED_WORKBOOK_PATH,
    discover_input_excel,
    ensure_phase_directories,
)
from ingestion.engines.audio_downloader import DownloadError, download_audio, get_cached_audio_path
from ingestion.engines.crm_mapping import map_leads_to_calls, prepare_workbook
from shared.json_utils import write_json
from shared.logging_utils import TerminalUI, append_csv_row, write_csv_rows
from shared.schema_utils import CallManifestEntry
from shared.workbook_utils import load_workbook_sheets, save_updated_workbook


def main() -> int:
    ensure_phase_directories()
    terminal = TerminalUI(RUNTIME_LOG_PATH)
    terminal.rule("GEW Intelligence OS - Phase 1 Ingestion", style="bold magenta")

    try:
        input_path = discover_input_excel()
        combined_df, calls_df = load_workbook_sheets(input_path, COMBINED_SHEET_NAME, CALLS_SHEET_NAME)
        combined_df, calls_df = prepare_workbook(combined_df, calls_df)
        mapped_df, unmatched_rows, lead_profiles = map_leads_to_calls(combined_df, calls_df)
    except Exception as exc:
        terminal.exception("PHASE_1", f"Failed to initialize ingestion: {exc}", exc)
        return 1

    terminal.info(f"Matched {len(mapped_df.index)} call(s) across {len(lead_profiles)} lead(s).")
    write_csv_rows(UNMATCHED_LOG_PATH, UNMATCHED_LOG_HEADERS, unmatched_rows)

    manifest_entries: list[dict[str, object]] = []
    with terminal.build_progress() as progress:
        task = progress.add_task("Downloading mapped audio", total=len(mapped_df.index))
        for sequence, mapped_index in enumerate(mapped_df.index, start=1):
            mapped_row = mapped_df.loc[mapped_index]
            call_id = str(mapped_row["call_id"]).strip()
            lead_number = str(mapped_row["lead_number"]).strip()
            recording_url = str(mapped_row["recording_url"]).strip()
            call_row_index = int(mapped_row["call_row_index"])

            terminal.rule(f"[{sequence}/{len(mapped_df.index)}] INGEST {call_id}", style="bold magenta")

            try:
                cached_audio_path = get_cached_audio_path(call_id)
                if cached_audio_path.exists() and cached_audio_path.stat().st_size > 0:
                    audio_path = cached_audio_path
                    terminal.success(f"Audio already available: {audio_path}")
                else:
                    terminal.step("DOWNLOAD", "Downloading audio...", "bold magenta")
                    audio_path = download_audio(recording_url, call_id)
                    terminal.success(f"Audio saved: {audio_path}")

                calls_df.at[call_row_index, LEAD_NUMBER_COLUMN] = lead_number
                calls_df.at[call_row_index, AUDIO_PATH_COLUMN] = str(audio_path)
                calls_df.at[call_row_index, DOWNLOAD_STATUS_COLUMN] = "DOWNLOADED"
                calls_df.at[call_row_index, DOWNLOAD_ERROR_COLUMN] = ""
                mapped_df.at[mapped_index, "audio_path"] = str(audio_path)
                mapped_df.at[mapped_index, "download_status"] = "DOWNLOADED"
                mapped_df.at[mapped_index, "download_error"] = ""

                manifest_entries.append(
                    CallManifestEntry(
                        call_id=call_id,
                        lead_number=lead_number,
                        recording_url=recording_url,
                        audio_path=str(audio_path),
                        duration=mapped_row.get("duration", ""),
                        owner=str(mapped_row.get("owner", "")).strip(),
                        campaign=str(mapped_row.get("campaign", "")).strip(),
                        walkin_status=str(mapped_row.get("walkin_status", "")).strip(),
                    ).to_dict()
                )

                lead_profiles[lead_number]["calls"].append(
                    {
                        "call_id": call_id,
                        "recording_url": recording_url,
                        "audio_path": str(audio_path),
                        "duration": mapped_row.get("duration", ""),
                    }
                )
                append_csv_row(
                    INGESTION_LOG_PATH,
                    INGESTION_LOG_HEADERS,
                    {
                        "call_id": call_id,
                        "status": "DOWNLOADED",
                        "audio_path": str(audio_path),
                        "error_message": "",
                    },
                )
            except (DownloadError, ValueError) as exc:
                error_message = str(exc)
                terminal.exception(call_id, error_message, exc)
                calls_df.at[call_row_index, DOWNLOAD_STATUS_COLUMN] = "FAILED"
                calls_df.at[call_row_index, DOWNLOAD_ERROR_COLUMN] = error_message
                mapped_df.at[mapped_index, "download_status"] = "FAILED"
                mapped_df.at[mapped_index, "download_error"] = error_message
                append_csv_row(
                    INGESTION_LOG_PATH,
                    INGESTION_LOG_HEADERS,
                    {
                        "call_id": call_id,
                        "status": "FAILED",
                        "audio_path": "",
                        "error_message": error_message,
                    },
                )
            finally:
                progress.advance(task)

    mapped_df.drop(columns=["call_row_index"], errors="ignore").to_csv(MAPPED_CALLS_PATH, index=False)
    write_json(CALL_MANIFEST_PATH, manifest_entries)

    for lead_number, profile in lead_profiles.items():
        write_json(LEAD_PROFILES_DIR / f"lead_{lead_number}.json", profile)

    save_updated_workbook(
        combined_df.drop(columns=["normalized_phone"], errors="ignore"),
        calls_df.drop(columns=["normalized_phone"], errors="ignore"),
        UPDATED_WORKBOOK_PATH,
        discover_input_excel(),
        COMBINED_SHEET_NAME,
        CALLS_SHEET_NAME,
    )
    terminal.success("Phase 1 completed. Metadata and audio assets are ready for downstream phases.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
