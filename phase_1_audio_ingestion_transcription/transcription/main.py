from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any

from transcription.config import (
    CALL_MANIFEST_CANDIDATES,
    FAILURES_LOG_PATH,
    PROCESS_LOCK_PATH,
    PROCESSED_CALLS_PATH,
    PROGRESS_LOG_PATH,
    RUNTIME_LOG_PATH,
    RUNTIME_METRICS_PATH,
    STRUCTURED_OUTPUT_DIR,
    STRUCTURED_TRANSCRIPT_MANIFEST_PATH,
    TRANSCRIPTION_LOG_HEADERS,
    TRANSCRIPTION_LOG_PATH,
    TRANSCRIPTION_TEXT_LOG_PATH,
    TRANSCRIPT_CATALOG_PATH,
    TRANSCRIPT_MANIFEST_PATH,
    TRANSCRIPTS_DIR,
    ensure_phase_directories,
)
from transcription.engines.transcript_ingestion_engine import IngestedTranscript, TranscriptIngestionEngine
from transcription.engines.transcript_structurer import build_structured_transcript
from transcription.engines.transcription_engine import get_model, release_model, transcribe_audio
from shared.batch_runtime import (
    ProcessLock,
    ProgressTracker,
    RuntimeMetricsMonitor,
    RuntimeOptions,
    ShutdownController,
    SleepInhibitor,
    collect_runtime_warnings,
    run_cleanup,
)
from shared.json_utils import read_json, write_json, write_text_atomic
from shared.logging_utils import TerminalUI, append_csv_row
from shared.schema_utils import PhaseOutputEntry


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    ensure_phase_directories()
    options = RuntimeOptions(
        background=args.background,
        resume=args.resume,
        quiet=args.quiet,
        minimal_ui=args.minimal_ui or args.background,
        allow_display_sleep=not args.keep_display_awake,
        metrics_interval_seconds=args.metrics_interval,
    )
    terminal = TerminalUI(
        RUNTIME_LOG_PATH,
        quiet=options.quiet,
        minimal_ui=options.minimal_ui,
        log_to_console=not args.no_console,
    )
    terminal.rule("GEW Intelligence OS - Phase 2 Transcript Infrastructure", style="bold cyan")
    terminal.info(f"Phase 2 mode: {args.mode}")
    if options.background:
        terminal.info("Background batch mode is active. Processing continues if the screen turns off, Windows locks, or the terminal is minimized.")
        terminal.warning("Processing still stops if the whole laptop enters sleep, hibernation, or shutdown.")

    call_manifest = _read_first_json(CALL_MANIFEST_CANDIDATES, default=[])
    manifest_lookup = {
        _normalize_call_id(str(item.get("call_id", "")).strip()): item
        for item in call_manifest
        if str(item.get("call_id", "")).strip()
    }

    process_lock = ProcessLock(
        PROCESS_LOCK_PATH,
        metadata={
            "phase": "transcription",
            "mode": args.mode,
            "background": options.background,
        },
    )
    tracker = ProgressTracker(PROCESSED_CALLS_PATH, "transcription")
    shutdown = ShutdownController(tracker, terminal)
    sleep_inhibitor = SleepInhibitor(enabled=True, logger=terminal, allow_display_sleep=options.allow_display_sleep)
    session_progress = {"completed": 0, "total": 1}

    try:
        process_lock.acquire()
        shutdown.install()
        for warning in collect_runtime_warnings():
            terminal.warning(warning)

        predicted_external = _predict_external_workload(args.external_transcript_file)
        predicted_asr = _predict_asr_workload(call_manifest, args.resume, terminal)
        tracker.initialize(total_calls=predicted_external + predicted_asr, resume=args.resume)
        session_progress["total"] = max(predicted_external + predicted_asr, 1)
        sleep_inhibitor.activate()

        metrics_monitor = RuntimeMetricsMonitor(
            RUNTIME_METRICS_PATH,
            total_items=session_progress["total"],
            processed_counter=lambda: int(session_progress["completed"]),
            started_at=time.perf_counter(),
            logger=terminal,
            interval_seconds=options.metrics_interval_seconds,
        )
        metrics_monitor.start()

        exit_code = 0
        final_status = "completed"
        try:
            if args.mode in {"external", "hybrid"}:
                _run_external_ingestion(
                    explicit_sources=[Path(path) for path in args.external_transcript_file],
                    manifest_lookup=manifest_lookup,
                    tracker=tracker,
                    terminal=terminal,
                    session_progress=session_progress,
                )

            if args.mode in {"asr", "hybrid"}:
                _run_asr_ingestion(
                    manifest=call_manifest,
                    tracker=tracker,
                    shutdown=shutdown,
                    terminal=terminal,
                    options=options,
                    session_progress=session_progress,
                )
        except KeyboardInterrupt as exc:
            final_status = "interrupted"
            exit_code = 130
            terminal.warning(str(exc))
        finally:
            metrics_monitor.stop()

        tracker.finalize(final_status)
        _rebuild_transcript_manifests()
        if exit_code == 0:
            terminal.success("Phase 2 completed. Hybrid transcript assets are ready for downstream phases.")
        else:
            terminal.warning("Phase 2 stopped before completion. Use --resume to continue remaining files only.")
        return exit_code
    except Exception as exc:
        terminal.exception("PHASE_2", f"Hybrid transcript infrastructure run failed: {exc}", exc)
        tracker.finalize("failed")
        return 1
    finally:
        _rebuild_transcript_manifests()
        sleep_inhibitor.restore()
        process_lock.release()
        release_model()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GEW Intelligence OS - Phase 2 Transcript Infrastructure")
    parser.add_argument("--mode", choices=["hybrid", "asr", "external"], default="hybrid", help="Choose ASR-only, external-only, or hybrid transcript processing.")
    parser.add_argument("--external-transcript-file", action="append", default=[], help="Additional external transcript file to ingest.")
    parser.add_argument("--background", action="store_true", help="Run in long-duration background batch mode with reduced console overhead.")
    parser.add_argument("--batch", action="store_true", help="Alias for --background.")
    parser.add_argument("--resume", action="store_true", help="Resume from the last saved progress state and skip completed transcripts.")
    parser.add_argument("--quiet", action="store_true", help="Suppress most console output while keeping file logs active.")
    parser.add_argument("--minimal-ui", action="store_true", help="Disable Rich progress rendering and use lightweight console logging.")
    parser.add_argument("--no-console", action="store_true", help="Write logs to files only.")
    parser.add_argument("--metrics-interval", type=int, default=30, help="Seconds between runtime metric snapshots.")
    parser.add_argument("--keep-display-awake", action="store_true", help="Prevent the display from sleeping during processing as well.")
    args = parser.parse_args(argv)
    if args.batch:
        args.background = True
    return args


def _run_external_ingestion(
    *,
    explicit_sources: list[Path],
    manifest_lookup: dict[str, dict[str, Any]],
    tracker: ProgressTracker,
    terminal: TerminalUI,
    session_progress: dict[str, int],
) -> None:
    engine = TranscriptIngestionEngine(logger=terminal)
    skip_existing_call_ids = tracker.processed_set() | {path.stem.upper() for path in STRUCTURED_OUTPUT_DIR.glob("CALL_*.json")}
    results = engine.ingest_external_sources(
        explicit_sources=explicit_sources,
        manifest_lookup=manifest_lookup,
        skip_existing_call_ids=skip_existing_call_ids,
    )
    if not results:
        terminal.info("No external transcript sources were discovered for ingestion.")
        return

    for result in results:
        tracker.mark_success(result.call_id)
        _record_ingested_transcript(result, terminal)
        session_progress["completed"] += 1
        run_cleanup(terminal)
    _rebuild_transcript_manifests()


def _run_asr_ingestion(
    *,
    manifest: list[dict[str, Any]],
    tracker: ProgressTracker,
    shutdown: ShutdownController,
    terminal: TerminalUI,
    options: RuntimeOptions,
    session_progress: dict[str, int],
) -> None:
    workload = _build_asr_workload(manifest, tracker, terminal)
    if not workload:
        terminal.info("No calls require ASR transcription after hybrid source resolution.")
        return

    get_model(terminal)
    with terminal.build_progress() as progress:
        task = progress.add_task("Building ASR transcripts", total=len(workload))
        for sequence, call in enumerate(workload, start=1):
            shutdown.raise_if_requested()
            call_id = _normalize_call_id(str(call.get("call_id", "")).strip())
            audio_path = str(call.get("audio_path", "")).strip()
            transcript_path = TRANSCRIPTS_DIR / f"{call_id}.txt"
            metadata_path = TRANSCRIPTS_DIR / f"{call_id}.metadata.json"
            tracker.mark_active(call_id)
            terminal.rule(f"[{sequence}/{len(workload)}] ASR {call_id}", style="bold cyan")

            try:
                transcript_text, metadata = transcribe_audio(
                    Path(audio_path),
                    on_segment=None if options.background or options.quiet else terminal.segment,
                    logger=terminal,
                )
                write_text_atomic(transcript_path, transcript_text, encoding="utf-8")
                write_json(metadata_path, metadata)
                structured_payload = _build_structured_payload_from_asr(call_id, transcript_text, metadata, call)
                structured_json_path = STRUCTURED_OUTPUT_DIR / f"{call_id}.json"
                write_json(structured_json_path, structured_payload)
                tracker.mark_success(call_id)
                _record_manifest_entry(
                    call_id=call_id,
                    source_path=audio_path,
                    transcript_path=transcript_path,
                    metadata_path=metadata_path,
                    structured_json_path=structured_json_path,
                    metadata=metadata,
                    source="native_asr",
                    transcript_origin="faster_whisper",
                )
                _append_log_line(
                    TRANSCRIPTION_TEXT_LOG_PATH,
                    f"{_now()} | SUCCESS | {call_id} | source=native_asr | words={metadata['word_count']} | transcript={transcript_path}",
                )
                append_csv_row(
                    TRANSCRIPTION_LOG_PATH,
                    TRANSCRIPTION_LOG_HEADERS,
                    {
                        "call_id": call_id,
                        "status": "SUCCESS",
                        "audio_path": audio_path,
                        "transcript_path": str(transcript_path),
                        "error_message": "",
                    },
                )
                _append_log_line(PROGRESS_LOG_PATH, f"{_now()} | SUCCESS | {call_id} | {transcript_path}")
                terminal.summary(
                    "ASR Transcript Summary",
                    [
                        ("Call ID", call_id),
                        ("Words", str(metadata["word_count"])),
                        ("Language", str(metadata["detected_language"])),
                        ("Transcript", str(transcript_path)),
                    ],
                )
            except Exception as exc:
                error_message = str(exc)
                terminal.exception(call_id, error_message, exc)
                tracker.mark_failure(call_id, error_message)
                append_csv_row(
                    TRANSCRIPTION_LOG_PATH,
                    TRANSCRIPTION_LOG_HEADERS,
                    {
                        "call_id": call_id,
                        "status": "FAILED",
                        "audio_path": audio_path,
                        "transcript_path": "",
                        "error_message": error_message,
                    },
                )
                _append_log_line(TRANSCRIPTION_TEXT_LOG_PATH, f"{_now()} | FAILED | {call_id} | {audio_path} | {error_message}")
                _append_log_line(FAILURES_LOG_PATH, f"{_now()} | FAILED | {call_id} | {audio_path} | {error_message}")
            finally:
                session_progress["completed"] += 1
                progress.advance(task)
                _rebuild_transcript_manifests()
                run_cleanup(terminal)


def _predict_external_workload(explicit_sources: list[str]) -> int:
    engine = TranscriptIngestionEngine()
    return engine.count_discoverable_calls(explicit_sources=[Path(path) for path in explicit_sources])


def _predict_asr_workload(manifest: list[dict[str, Any]], resume: bool, terminal: TerminalUI) -> int:
    tracker = ProgressTracker(PROCESSED_CALLS_PATH, "transcription")
    if not resume:
        tracker.payload["processed_calls"] = []
    return len(_build_asr_workload(manifest, tracker, terminal, log_skips=False))


def _build_asr_workload(
    manifest: list[dict[str, Any]],
    tracker: ProgressTracker,
    terminal: TerminalUI,
    *,
    log_skips: bool = True,
) -> list[dict[str, Any]]:
    processed_calls = tracker.processed_set()
    existing_structured = {path.stem.upper() for path in STRUCTURED_OUTPUT_DIR.glob("CALL_*.json")}
    workload: list[dict[str, Any]] = []

    for call in manifest:
        call_id = _normalize_call_id(str(call.get("call_id", "")).strip())
        audio_path = str(call.get("audio_path", "")).strip()
        if not call_id or not audio_path:
            continue
        transcript_path = TRANSCRIPTS_DIR / f"{call_id}.txt"
        metadata_path = TRANSCRIPTS_DIR / f"{call_id}.metadata.json"
        if call_id in processed_calls or call_id in existing_structured or (transcript_path.exists() and metadata_path.exists()):
            tracker.mark_success(call_id)
            tracker.mark_skipped(call_id)
            if log_skips:
                terminal.info(f"Skipping ASR for {call_id} because a transcript asset already exists.")
            continue
        workload.append(call)
    return workload


def _record_ingested_transcript(result: IngestedTranscript, terminal: TerminalUI) -> None:
    metadata = read_json(result.metadata_path, default={}) or {}
    _record_manifest_entry(
        call_id=result.call_id,
        source_path=str(result.source_path),
        transcript_path=result.transcript_path,
        metadata_path=result.metadata_path,
        structured_json_path=result.structured_json_path,
        metadata=metadata,
        source=result.source_type,
        transcript_origin=result.origin,
    )
    append_csv_row(
        TRANSCRIPTION_LOG_PATH,
        TRANSCRIPTION_LOG_HEADERS,
        {
            "call_id": result.call_id,
            "status": "SUCCESS",
            "audio_path": metadata.get("audio_path", ""),
            "transcript_path": str(result.transcript_path),
            "error_message": "",
        },
    )
    _append_log_line(
        TRANSCRIPTION_TEXT_LOG_PATH,
        f"{_now()} | SUCCESS | {result.call_id} | source={result.origin} | words={result.word_count} | transcript={result.transcript_path}",
    )
    _append_log_line(PROGRESS_LOG_PATH, f"{_now()} | SUCCESS | {result.call_id} | {result.transcript_path}")
    terminal.summary(
        "External Transcript Summary",
        [
            ("Call ID", result.call_id),
            ("Words", str(result.word_count)),
            ("Segments", str(result.segment_count)),
            ("Structured JSON", str(result.structured_json_path)),
        ],
    )


def _record_manifest_entry(
    *,
    call_id: str,
    source_path: str,
    transcript_path: Path,
    metadata_path: Path,
    structured_json_path: Path,
    metadata: dict[str, Any],
    source: str,
    transcript_origin: str,
) -> None:
    existing_manifest = read_json(TRANSCRIPT_MANIFEST_PATH, default=[]) or []
    manifest_by_call = {str(item.get("call_id", "")).strip(): item for item in existing_manifest}
    manifest_by_call[call_id] = PhaseOutputEntry(
        call_id=call_id,
        source_path=source_path,
        output_path=str(transcript_path),
        metadata_path=str(metadata_path),
        extra={
            **dict(metadata),
            "structured_json_path": str(structured_json_path),
            "source": source,
            "transcript_origin": transcript_origin,
        },
    ).to_dict()
    ordered_entries = [manifest_by_call[key] for key in sorted(manifest_by_call.keys())]
    write_json(TRANSCRIPT_MANIFEST_PATH, ordered_entries)


def _rebuild_transcript_manifests() -> None:
    entries: list[dict[str, Any]] = []
    catalog_entries: list[dict[str, Any]] = []
    for structured_json_path in sorted(STRUCTURED_OUTPUT_DIR.glob("CALL_*.json")):
        payload = read_json(structured_json_path, default={}) or {}
        metadata = dict(payload.get("metadata", {}))
        call_id = str(metadata.get("call_id", structured_json_path.stem)).strip() or structured_json_path.stem
        transcript_path = TRANSCRIPTS_DIR / f"{call_id}.txt"
        metadata_path = TRANSCRIPTS_DIR / f"{call_id}.metadata.json"
        entries.append(
            PhaseOutputEntry(
                call_id=call_id,
                source_path=str(metadata.get("source_path", "")),
                output_path=str(transcript_path),
                metadata_path=str(metadata_path),
                extra={
                    **metadata,
                    "structured_json_path": str(structured_json_path),
                },
            ).to_dict()
        )
        catalog_entries.append(
            {
                "call_id": call_id,
                "source": metadata.get("source", ""),
                "transcript_origin": metadata.get("transcript_origin", ""),
                "structured_json_path": str(structured_json_path),
                "transcript_path": str(transcript_path),
                "metadata_path": str(metadata_path),
                "has_audio": bool(metadata.get("audio_path")),
            }
        )
    write_json(TRANSCRIPT_MANIFEST_PATH, entries)
    write_json(STRUCTURED_TRANSCRIPT_MANIFEST_PATH, catalog_entries)
    write_json(TRANSCRIPT_CATALOG_PATH, catalog_entries)


def _build_structured_payload_from_asr(
    call_id: str,
    transcript_text: str,
    metadata: dict[str, Any],
    manifest_entry: dict[str, Any],
) -> dict[str, Any]:
    segments = _segments_from_asr_text(transcript_text)
    payload = build_structured_transcript(
        call_id,
        segments,
        source="native_asr",
        transcript_origin="faster_whisper",
        source_path=str(manifest_entry.get("audio_path", "")).strip(),
        audio_path=str(manifest_entry.get("audio_path", "")).strip(),
        manifest_context=manifest_entry,
    )
    payload["metadata"]["duration_seconds"] = float(metadata.get("audio_duration", 0.0) or 0.0)
    payload["metadata"]["duration"] = _seconds_to_mmss(float(metadata.get("audio_duration", 0.0) or 0.0))
    payload["metadata"]["detected_language"] = metadata.get("detected_language")
    payload["metadata"]["confidence_score"] = metadata.get("confidence_score")
    payload["metadata"]["total_segments"] = len(segments)
    return payload


def _segments_from_asr_text(transcript_text: str) -> list[dict[str, Any]]:
    pattern = re.compile(r"^\[(\d{2}:\d{2})\]\s+(.*)$")
    parsed: list[tuple[str, str]] = []
    for line in transcript_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = pattern.match(stripped)
        if not match:
            continue
        parsed.append((match.group(1), match.group(2).strip()))

    segments: list[dict[str, Any]] = []
    for index, (start_time, text) in enumerate(parsed, start=1):
        next_start = parsed[index][0] if index < len(parsed) else start_time
        segments.append(
            {
                "segment_id": index,
                "timestamp": f"[{start_time} - {next_start}]",
                "start_time": start_time,
                "end_time": next_start,
                "type": "dialogue",
                "speaker": "Unknown",
                "speaker_name": None,
                "speaker_label": "Unknown",
                "emotion": None,
                "text": text,
            }
        )
    return segments


def _read_first_json(candidates: list[Path], default: Any) -> Any:
    for candidate in candidates:
        payload = read_json(candidate, default=None)
        if payload:
            return payload
    return default


def _append_log_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _normalize_call_id(raw_call_id: str) -> str:
    digits = re.sub(r"\D", "", raw_call_id)
    if digits:
        return f"CALL_{digits.zfill(4)}"
    return raw_call_id.strip().upper()


def _seconds_to_mmss(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    minutes, remaining = divmod(total_seconds, 60)
    return f"{minutes:02d}:{remaining:02d}"


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    sys.exit(main())
