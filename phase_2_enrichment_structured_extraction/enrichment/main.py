from __future__ import annotations

import argparse
import sys
import time

import librosa

from enrichment.acoustic_engine import AcousticEngine
from enrichment.config import (
    EMOTION_MANIFEST_PATH,
    PROCESSING_LOG_HEADERS,
    PROCESSING_LOG_PATH,
    RUNTIME_LOG_PATH,
    TARGET_SAMPLE_RATE,
    ensure_phase_directories,
)
from enrichment.emotion_engine import EmotionEngine
from enrichment.export_engine import ExportEngine
from enrichment.silence_engine import SilenceEngine
from enrichment.speaker_engine import SpeakerEngine
from enrichment.timeline_engine import TimelineEngine
from enrichment.transcript_enrichment_engine import TranscriptEnrichmentEngine
from enrichment.utils.audio_preprocessing import normalize_audio_for_analysis
from enrichment.utils.discovery import discover_inputs
from enrichment.utils.transcript_metrics import read_transcript_metrics
from shared.json_utils import write_json
from shared.logging_utils import TerminalUI, append_csv_row
from shared.schema_utils import PhaseOutputEntry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GEW Intelligence OS - Phase 3 Enrichment")
    parser.add_argument("--call-id", type=str, help="Process only a specific call ID.")
    parser.add_argument("--audio-id", type=str, help="Process using an existing audio file ID.")
    args = parser.parse_args(argv)

    ensure_phase_directories()
    terminal = TerminalUI(RUNTIME_LOG_PATH)
    terminal.rule("GEW Intelligence OS - Phase 3 Transcript Enrichment & Voice Intelligence", style="bold green")

    discovered_inputs, discovery_warnings = discover_inputs()

    effective_id = args.audio_id or args.call_id
    if effective_id:
        terminal.info(f"Filtering for ID: {effective_id}")
        discovered_inputs = [item for item in discovered_inputs if item.call_id == effective_id]
        discovery_warnings = [w for w in discovery_warnings if effective_id in w]

    for warning in discovery_warnings:
        terminal.warning(warning)

    if not discovered_inputs:
        terminal.warning("No transcript inputs found. Nothing to analyze.")
        return 0

    try:
        emotion_engine = EmotionEngine(terminal)
        acoustic_engine = AcousticEngine()
        speaker_engine = SpeakerEngine()
        silence_engine = SilenceEngine()
        timeline_engine = TimelineEngine()
        export_engine = ExportEngine()
        transcript_enrichment_engine = TranscriptEnrichmentEngine()
    except Exception as exc:
        terminal.exception("PHASE_3", f"Failed to initialize Phase 3 engines: {exc}", exc)
        return 1

    manifest: list[dict[str, object]] = []
    with terminal.build_progress() as progress:
        task = progress.add_task("Analyzing voice intelligence", total=len(discovered_inputs))
        for sequence, phase_input in enumerate(discovered_inputs, start=1):
            call_id = phase_input.call_id
            terminal.rule(f"[{sequence}/{len(discovered_inputs)}] ANALYZE {call_id}", style="bold green")
            started_at = time.perf_counter()
            normalized_audio_path = None

            try:
                transcript_metrics = read_transcript_metrics(phase_input.transcript_path, phase_input.transcript_metadata_path)
                enriched_transcript = transcript_enrichment_engine.enrich(
                    call_id,
                    phase_input.transcript_path,
                    phase_input.transcript_format,
                    transcript_source=phase_input.transcript_source,
                    reviewed=phase_input.reviewed,
                    enrichment_level=phase_input.enrichment_level,
                    pipeline_stage=phase_input.pipeline_stage,
                )

                if phase_input.audio_path is not None and phase_input.audio_path.exists():
                    normalized_audio_path = normalize_audio_for_analysis(phase_input.audio_path)
                    audio, sample_rate = librosa.load(str(normalized_audio_path), sr=TARGET_SAMPLE_RATE, mono=True)
                    duration = float(librosa.get_duration(y=audio, sr=sample_rate))
                    emotion_timeline, emotion_summary = emotion_engine.analyze(audio, duration)
                    unified_timeline = timeline_engine.build(emotion_timeline)
                    silence_metrics = silence_engine.analyze(audio, duration)
                    speaker_metrics = speaker_engine.analyze(audio)
                    acoustic_metrics = acoustic_engine.analyze(audio, duration, transcript_metrics)
                else:
                    duration = float(enriched_transcript.get("metadata", {}).get("duration_seconds", 0.0) or 0.0)
                    emotion_summary = {}
                    unified_timeline = []
                    silence_metrics = silence_engine._empty_metrics()
                    speaker_metrics = speaker_engine._empty_metrics()
                    acoustic_metrics = acoustic_engine._empty_metrics()

                processing_time_sec = round(time.perf_counter() - started_at, 2)
                payload = {
                    "call_id": call_id,
                    "duration_sec": round(duration, 2),
                    "emotion_summary": emotion_summary,
                    "emotion_timeline": unified_timeline,
                    "speaker_metrics": speaker_metrics,
                    "silence_metrics": silence_metrics,
                    "acoustic_metrics": acoustic_metrics,
                    "engagement_score": silence_metrics["engagement_score"],
                    "stress_score": acoustic_metrics["stress_score"],
                    "confidence_score": acoustic_metrics["confidence_score"],
                    "escalation_detected": acoustic_metrics["escalation_detected"],
                    "processing_time_sec": processing_time_sec,
                    "audio_path": str(phase_input.audio_path) if phase_input.audio_path else "",
                    "transcript_path": str(phase_input.transcript_path),
                    "transcript_metadata_path": str(phase_input.transcript_metadata_path) if phase_input.transcript_metadata_path else "",
                    "transcript_metrics": transcript_metrics,
                    "transcript_source": phase_input.transcript_source,
                    "transcript_format": phase_input.transcript_format,
                    "participants": enriched_transcript.get("participants", {}),
                    "conversation_intelligence": enriched_transcript.get("conversation_intelligence", {}),
                    "crm_context": enriched_transcript.get("crm_context", {}),
                    "metadata": enriched_transcript.get("metadata", {}),
                    "transcript": enriched_transcript.get("transcript", []),
                    "source_tracking": enriched_transcript.get("source_tracking", {}),
                }
                
                # Preserve any extra fields from the enriched transcript (e.g., conversion_analysis, business_impact)
                for key, value in enriched_transcript.items():
                    if key not in payload:
                        payload[key] = value
                        
                json_path, summary_path, timeline_path = export_engine.export(call_id, payload)
                manifest.append(
                    PhaseOutputEntry(
                        call_id=call_id,
                        source_path=str(phase_input.audio_path) if phase_input.audio_path else str(phase_input.transcript_path),
                        output_path=str(json_path),
                        metadata_path=str(summary_path),
                        extra={
                            "timeline_path": str(timeline_path),
                            "transcript_path": str(phase_input.transcript_path),
                        },
                    ).to_dict()
                )
                append_csv_row(
                    PROCESSING_LOG_PATH,
                    PROCESSING_LOG_HEADERS,
                    {
                        "call_id": call_id,
                        "status": "SUCCESS",
                        "audio_path": str(phase_input.audio_path) if phase_input.audio_path else "",
                        "transcript_path": str(phase_input.transcript_path),
                        "json_output_path": str(json_path),
                        "error_message": "",
                        "processing_time_sec": str(processing_time_sec),
                    },
                )
                terminal.summary(
                    "Voice Intelligence Summary",
                    [
                        ("Call ID", call_id),
                        ("Intent", str(payload["conversation_intelligence"].get("primary_intent", ""))),
                        ("Emotion Segments", str(len(unified_timeline))),
                        ("Audio Available", "yes" if phase_input.audio_path else "no"),
                        ("JSON", str(json_path)),
                    ],
                )
            except Exception as exc:
                error_message = str(exc)
                terminal.exception(call_id, error_message, exc)
                append_csv_row(
                    PROCESSING_LOG_PATH,
                    PROCESSING_LOG_HEADERS,
                    {
                        "call_id": call_id,
                        "status": "FAILED",
                        "audio_path": str(phase_input.audio_path) if phase_input.audio_path else "",
                        "transcript_path": str(phase_input.transcript_path),
                        "json_output_path": "",
                        "error_message": error_message,
                        "processing_time_sec": str(round(time.perf_counter() - started_at, 2)),
                    },
                )
            finally:
                if normalized_audio_path is not None and normalized_audio_path.exists():
                    normalized_audio_path.unlink()
                progress.advance(task)

    write_json(EMOTION_MANIFEST_PATH, manifest)
    terminal.success("Phase 3 completed. Transcript enrichment and voice intelligence outputs are ready for Phase 4.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
