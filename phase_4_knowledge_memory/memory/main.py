from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from .chunking_engine import ChunkingEngine
from .config import (
    ANALYTICS_OUTPUT_DIR,
    DEBUG_OUTPUT_DIR,
    MAX_BATCH_SIZE,
    MEMORY_MANIFEST_PATH,
    PROCESSING_LOG_HEADERS,
    PROCESSING_LOG_PATH,
    RETRIEVAL_LOG_HEADERS,
    RETRIEVAL_LOG_PATH,
    RETRIEVAL_OUTPUT_DIR,
    RUNTIME_LOG_PATH,
    SAMPLE_RETRIEVAL_QUERIES,
    ensure_phase_directories,
)
from .embedding_engine import EmbeddingEngine
from .evidence_engine import EvidenceEngine
from .indexing_engine import IndexingEngine
from .memory_engine import MemoryEngine
from .metadata_engine import MetadataEngine
from .retrieval_engine import RetrievalEngine
from .vector_engine import VectorEngine
from shared.json_utils import read_json, write_json
from shared.logging_utils import TerminalUI, append_csv_row
from shared.schema_utils import PhaseOutputEntry


def main() -> int:
    ensure_phase_directories()
    terminal = TerminalUI(RUNTIME_LOG_PATH)
    terminal.rule("GEW Intelligence OS - Phase 5 Knowledge Layer", style="bold white")

    memory_engine = MemoryEngine()
    transcripts, reasoning_entries, emotion_entries, call_entries = memory_engine.load_inputs()
    if not transcripts:
        terminal.warning("No transcript inputs found. Nothing to index.")
        return 0

    reasoning_by_call = {_normalize_call_id(item.get("call_id", "")): item for item in reasoning_entries if _normalize_call_id(item.get("call_id", ""))}
    emotions_by_call = {_normalize_call_id(item.get("call_id", "")): item for item in emotion_entries if _normalize_call_id(item.get("call_id", ""))}
    calls_by_call = {_normalize_call_id(item.get("call_id", "")): item for item in call_entries if _normalize_call_id(item.get("call_id", ""))}

    chunking_engine = ChunkingEngine()
    embedding_engine = EmbeddingEngine()
    vector_engine = VectorEngine()
    metadata_engine = MetadataEngine()
    indexing_engine = IndexingEngine()
    evidence_engine = EvidenceEngine()
    retrieval_engine = RetrievalEngine(embedding_engine, vector_engine)

    chunk_records: list[dict[str, Any]] = []
    evidence_lookup: dict[str, dict[str, Any]] = {}
    manifest: list[dict[str, object]] = []
    workload = transcripts[:MAX_BATCH_SIZE]

    with terminal.build_progress() as progress:
        task = progress.add_task("Building conversational memory", total=len(workload))
        for sequence, transcript_entry in enumerate(workload, start=1):
            call_id = _normalize_call_id(transcript_entry.get("call_id", ""))
            terminal.rule(f"[{sequence}/{len(workload)}] INDEX {call_id}", style="bold white")
            started_at = time.perf_counter()
            try:
                transcript_path = _optional_path(transcript_entry.get("output_path", ""))
                reasoning_entry = reasoning_by_call.get(call_id, {})
                emotion_entry = emotions_by_call.get(call_id, {})
                reasoning_path = _optional_path(reasoning_entry.get("output_path", ""))
                emotion_path = _optional_path(emotion_entry.get("output_path", ""))

                transcript_text = str(transcript_entry.get("transcript_text", "")).strip()
                if not transcript_text and transcript_path and transcript_path.exists():
                    transcript_text = transcript_path.read_text(encoding="utf-8")
                reasoning_payload = dict(reasoning_entry.get("payload", {})) if isinstance(reasoning_entry.get("payload"), dict) else {}
                if not reasoning_payload and reasoning_path and reasoning_path.exists():
                    reasoning_payload = read_json(reasoning_path, default={}) or {}
                reasoning_payload = _normalize_reasoning_payload(reasoning_payload)
                phase3_payload = dict(emotion_entry.get("payload", {})) if isinstance(emotion_entry.get("payload"), dict) else {}
                if not phase3_payload and emotion_path and emotion_path.exists():
                    phase3_payload = read_json(emotion_path, default={}) or {}
                phase3_payload = _normalize_emotion_payload(phase3_payload, transcript_entry)
                crm_context = _build_crm_context(memory_engine, calls_by_call.get(call_id, {}))

                chunks = chunking_engine.chunk_conversation(call_id, transcript_text, phase3_payload, reasoning_payload, crm_context)
                for chunk in chunks:
                    metadata = metadata_engine.build_chunk_metadata(chunk, crm_context, phase3_payload, reasoning_payload)
                    vector = embedding_engine.embed_text(_embedding_payload(chunk, metadata, reasoning_payload))
                    vector_engine.upsert(chunk["chunk_id"], vector, metadata)
                    chunk_records.append(metadata)
                    evidence_lookup[chunk["chunk_id"]] = evidence_engine.build_evidence_record(chunk, metadata, reasoning_payload)

                processing_time = round(time.perf_counter() - started_at, 2)
                append_csv_row(
                    PROCESSING_LOG_PATH,
                    PROCESSING_LOG_HEADERS,
                    {
                        "call_id": call_id,
                        "status": "SUCCESS",
                        "chunk_count": str(len(chunks)),
                        "vector_count": str(len(chunks)),
                        "error_message": "",
                        "processing_time_sec": str(processing_time),
                    },
                )
                manifest.append(
                    PhaseOutputEntry(
                        call_id=call_id,
                        source_path=str(transcript_path or ""),
                        output_path="",
                        metadata_path="",
                        extra={
                            "chunk_count": len(chunks),
                            "reasoning_path": str(reasoning_path or ""),
                            "emotion_path": str(emotion_path or ""),
                        },
                    ).to_dict()
                )
                terminal.summary(
                    "Knowledge Summary",
                    [
                        ("Call ID", call_id),
                        ("Chunks", str(len(chunks))),
                        ("Customer", str(crm_context.get("lead_number", ""))),
                        ("Campaign", str(crm_context.get("campaign", ""))),
                    ],
                )
            except Exception as exc:
                append_csv_row(
                    PROCESSING_LOG_PATH,
                    PROCESSING_LOG_HEADERS,
                    {
                        "call_id": call_id,
                        "status": "FAILED",
                        "chunk_count": "0",
                        "vector_count": "0",
                        "error_message": str(exc),
                        "processing_time_sec": str(round(time.perf_counter() - started_at, 2)),
                    },
                )
                terminal.exception(call_id, str(exc), exc)
            finally:
                progress.advance(task)

    metadata_engine.persist_metadata(chunk_records)
    vector_engine.persist()
    embedding_engine.persist_cache()
    write_json(MEMORY_MANIFEST_PATH, manifest)
    write_json(DEBUG_OUTPUT_DIR / "evidence_lookup.json", evidence_lookup)

    call_summary = indexing_engine.build_call_summary(chunk_records)
    write_json(ANALYTICS_OUTPUT_DIR / "call_analytics.json", call_summary)

    retrieval_results = {}
    for retrieval_query in SAMPLE_RETRIEVAL_QUERIES:
        name = retrieval_query["name"]
        results = retrieval_engine.retrieve(retrieval_query["query"], filters=retrieval_query.get("filters"))
        results = evidence_engine.attach_evidence(results, evidence_lookup)
        retrieval_results[name] = results
        append_csv_row(
            RETRIEVAL_LOG_PATH,
            RETRIEVAL_LOG_HEADERS,
            {
                "query_name": name,
                "result_count": str(len(results)),
                "top_score": str(results[0]["score"] if results else ""),
                "filters": str(retrieval_query.get("filters", {})),
            },
        )

    write_json(RETRIEVAL_OUTPUT_DIR / "sample_retrieval_results.json", retrieval_results)
    terminal.success("Phase 5 completed. Conversational memory, metadata indexes, and retrieval outputs are ready.")
    return 0


def _build_crm_context(memory_engine: MemoryEngine, call_entry: dict[str, Any]) -> dict[str, Any]:
    lead_number = str(call_entry.get("lead_number", "")).strip()
    lead_profile = memory_engine.load_lead_profile(lead_number) if lead_number else {}
    return {
        "call_id": _normalize_call_id(call_entry.get("call_id", "")),
        "lead_number": lead_number,
        "owner": str(call_entry.get("owner", "")).strip(),
        "campaign": str(call_entry.get("campaign", "")).strip(),
        "walkin_status": str(call_entry.get("walkin_status", "")).strip(),
        "recording_url": str(call_entry.get("recording_url", "")).strip(),
        "duration": call_entry.get("duration", ""),
        "exam_targets": call_entry.get("exam_targets", []),
        "locations": call_entry.get("locations", []),
        "conversation_type": call_entry.get("conversation_type", ""),
        "priority_score": call_entry.get("priority_score", 0),
        "lead_profile": lead_profile,
    }


def _embedding_payload(chunk: dict[str, Any], metadata: dict[str, Any], reasoning_payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            chunk["text"],
            f"emotion:{chunk['emotion']}",
            f"campaign:{metadata.get('campaign', '')}",
            f"salesperson:{metadata.get('salesperson', '')}",
            f"reasoning_tags:{' '.join(metadata.get('reasoning_tags', []))}",
            f"strategic_summary:{_strategic_summary(reasoning_payload)}",
        ]
    )


def _strategic_summary(reasoning_payload: dict[str, Any]) -> str:
    if reasoning_payload.get("strategic_summary"):
        return str(reasoning_payload.get("strategic_summary", ""))
    call_summary = reasoning_payload.get("call_summary", {})
    if isinstance(call_summary, dict):
        return str(call_summary.get("one_line_summary", ""))
    return ""


def _normalize_reasoning_payload(reasoning_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(reasoning_payload, dict):
        return {}

    normalized = dict(reasoning_payload)
    tags = []

    conversation_type = reasoning_payload.get("conversation_type", {})
    if isinstance(conversation_type, dict):
        primary_category = str(conversation_type.get("primary_category", "")).strip()
        if primary_category:
            tags.append(primary_category)
        for tag in conversation_type.get("secondary_tags", []):
            tag_value = str(tag).strip()
            if tag_value:
                tags.append(tag_value)

    conversation_pattern = reasoning_payload.get("conversation_pattern", {})
    if isinstance(conversation_pattern, dict):
        pattern = str(conversation_pattern.get("pattern", "")).strip()
        if pattern:
            tags.append(pattern)
    elif str(reasoning_payload.get("outcome", "")).strip():
        tags.append(str(reasoning_payload.get("outcome", "")).strip())

    conversion_analysis = reasoning_payload.get("conversion_analysis", {})
    if isinstance(conversion_analysis, dict):
        signal = str(conversion_analysis.get("signal", "")).strip()
        funnel_stage = str(conversion_analysis.get("funnel_stage", "")).strip()
        if signal:
            tags.append(signal)
        if funnel_stage:
            tags.append(funnel_stage)
    else:
        conversion_signal = str(reasoning_payload.get("conversion_signal", "")).strip()
        funnel_stage = str(reasoning_payload.get("funnel_stage", "")).strip()
        sales_stage = str(reasoning_payload.get("sales_stage", "")).strip()
        if conversion_signal:
            tags.append(conversion_signal)
        if funnel_stage:
            tags.append(funnel_stage)
        if sales_stage:
            tags.append(sales_stage)

    caller_behavior = reasoning_payload.get("caller_behavior", {})
    if isinstance(caller_behavior, dict):
        dominant_emotion = str(caller_behavior.get("dominant_emotion", "")).strip()
        if dominant_emotion:
            tags.append(dominant_emotion)

    call_summary = reasoning_payload.get("call_summary", {})
    if isinstance(call_summary, dict):
        one_line_summary = str(call_summary.get("one_line_summary", "")).strip()
        if one_line_summary:
            normalized.setdefault("strategic_summary", one_line_summary)
    elif str(reasoning_payload.get("one_line_summary", "")).strip():
        normalized.setdefault("strategic_summary", str(reasoning_payload.get("one_line_summary", "")).strip())

    if "conversion_probability" in normalized:
        try:
            normalized["conversion_probability"] = float(normalized.get("conversion_probability", 0.0))
        except (TypeError, ValueError):
            normalized["conversion_probability"] = 0.0

    normalized["reasoning_tags"] = list(dict.fromkeys(tag for tag in tags if tag))
    return normalized


def _normalize_emotion_payload(phase3_payload: dict[str, Any], transcript_entry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(phase3_payload, dict):
        return {}

    normalized = dict(phase3_payload)
    if normalized.get("emotion_timeline"):
        return normalized

    dominant_emotion = str(normalized.get("dominant_emotion", "")).strip() or "neutral"
    normalized.setdefault("emotion_summary", {dominant_emotion: 1})

    duration_seconds = transcript_entry.get("call_duration_seconds", 0) or 0
    end_minutes = max(int(duration_seconds) // 60, 0)
    end_seconds = max(int(duration_seconds) % 60, 0)
    normalized["emotion_timeline"] = [
        {
            "start": "00:00",
            "end": f"{end_minutes:02d}:{end_seconds:02d}",
            "emotion": dominant_emotion,
        }
    ]
    return normalized


def _normalize_call_id(value: object) -> str:
    return str(value or "").strip().removesuffix(".mp3")


def _optional_path(value: object) -> Path | None:
    path_value = str(value or "").strip()
    if not path_value:
        return None
    return Path(path_value)


if __name__ == "__main__":
    sys.exit(main())
