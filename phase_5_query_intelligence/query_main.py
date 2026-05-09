from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from config import (
    CALL_ANALYTICS_PATH,
    EVIDENCE_LOOKUP_PATH,
    QUERY_LOG_HEADERS,
    QUERY_LOG_PATH,
    QUERY_OUTPUT_DIR,
    QUERY_TOP_K,
    REASONING_MANIFEST_CANDIDATES,
    RUNTIME_LOG_PATH,
    ensure_phase_directories,
)
from embedding_engine import EmbeddingEngine
from evidence_engine import EvidenceEngine
from memory_engine import MemoryEngine
from query_intelligence_engine import QueryIntelligenceEngine
from query_session import SessionMemoryStore
from retrieval_engine import RetrievalEngine
from vector_engine import VectorEngine
from shared.json_utils import read_json, write_json
from shared.logging_utils import TerminalUI, append_csv_row


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    ensure_phase_directories()
    terminal = TerminalUI(RUNTIME_LOG_PATH)
    terminal.rule("GEW Intelligence OS - Query Intelligence Engine", style="bold cyan")
    started_at = time.perf_counter()

    try:
        filters = json.loads(args.filters) if args.filters else {}
        if not isinstance(filters, dict):
            raise ValueError("--filters must decode to a JSON object")

        session_store = SessionMemoryStore()
        session_memory = session_store.load(args.session_id)

        embedding_engine = EmbeddingEngine()
        vector_engine = VectorEngine()
        retrieval_engine = RetrievalEngine(embedding_engine, vector_engine)
        evidence_engine = EvidenceEngine()
        query_engine = QueryIntelligenceEngine(logger=terminal)
        memory_engine = MemoryEngine()

        raw_results = retrieval_engine.retrieve(args.query, filters=filters)
        retrieved_results = evidence_engine.attach_evidence(raw_results[:QUERY_TOP_K], _load_evidence_lookup())

        reasoning_data = _load_reasoning_payloads(memory_engine)
        relevant_reasoning = _select_reasoning_by_results(retrieved_results, reasoning_data)
        metadata = _build_metadata_snapshot(retrieved_results)
        evidence_records = [item.get("evidence", {}) for item in retrieved_results if item.get("evidence")]

        response = query_engine.answer(
            query=args.query,
            session_memory=session_memory,
            retrieved_chunks=retrieved_results,
            reasoning_data=relevant_reasoning,
            metadata=metadata,
            evidence_records=evidence_records,
        )

        updated_session = session_store.update(
            args.session_id,
            args.query,
            filters,
            retrieved_results,
            response.get("answer", ""),
        )

        payload = {
            "session_id": args.session_id,
            "query": args.query,
            "filters": filters,
            "session_memory": updated_session,
            "retrieved_results": retrieved_results,
            "reasoning_data": relevant_reasoning,
            "metadata": metadata,
            "response": response,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        output_path = QUERY_OUTPUT_DIR / f"query_{time.strftime('%Y%m%d_%H%M%S')}.json"
        write_json(output_path, payload)

        append_csv_row(
            QUERY_LOG_PATH,
            QUERY_LOG_HEADERS,
            {
                "session_id": args.session_id,
                "query": args.query,
                "status": "SUCCESS",
                "retrieved_results": str(len(retrieved_results)),
                "confidence": str(response.get("confidence", 0.0)),
                "output_path": str(output_path),
                "error_message": "",
                "processing_time_sec": str(round(time.perf_counter() - started_at, 2)),
            },
        )

        terminal.summary(
            "Query Intelligence Summary",
            [
                ("Session", args.session_id),
                ("Results", str(len(retrieved_results))),
                ("Confidence", str(response.get("confidence", 0.0))),
                ("Output", str(output_path)),
            ],
        )
        return 0
    except Exception as exc:
        append_csv_row(
            QUERY_LOG_PATH,
            QUERY_LOG_HEADERS,
            {
                "session_id": args.session_id if args else "unknown",
                "query": args.query if args else "",
                "status": "FAILED",
                "retrieved_results": "0",
                "confidence": "0",
                "output_path": "",
                "error_message": str(exc),
                "processing_time_sec": str(round(time.perf_counter() - started_at, 2)),
            },
        )
        terminal.exception("QUERY_INTELLIGENCE", str(exc), exc)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run GEW Query Intelligence over retrieved conversational memory.")
    parser.add_argument("--query", required=True, help="User question to answer.")
    parser.add_argument("--session-id", default="default", help="Session identifier for contextual memory.")
    parser.add_argument("--filters", default="", help="Optional JSON object of retrieval filters.")
    return parser


def _load_evidence_lookup() -> dict[str, dict[str, Any]]:
    return read_json(EVIDENCE_LOOKUP_PATH, default={}) or {}


def _load_reasoning_payloads(memory_engine: MemoryEngine) -> dict[str, dict[str, Any]]:
    reasoning_manifest = memory_engine._read_first(REASONING_MANIFEST_CANDIDATES, [])
    payloads: dict[str, dict[str, Any]] = {}
    for item in reasoning_manifest:
        if not isinstance(item, dict):
            continue
        call_id = str(item.get("call_id", "")).strip()
        output_path = Path(str(item.get("output_path", "")).strip())
        if not call_id:
            continue
        payloads[call_id] = read_json(output_path, default={}) if output_path.exists() else dict(item)
    return payloads


def _select_reasoning_by_results(
    retrieved_results: list[dict[str, Any]],
    reasoning_data: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    call_ids = {
        str(result.get("metadata", {}).get("call_id", "")).strip()
        for result in retrieved_results
        if str(result.get("metadata", {}).get("call_id", "")).strip()
    }
    return {call_id: reasoning_data.get(call_id, {}) for call_id in call_ids if call_id in reasoning_data}


def _build_metadata_snapshot(retrieved_results: list[dict[str, Any]]) -> dict[str, Any]:
    analytics = read_json(CALL_ANALYTICS_PATH, default={}) or {}
    call_ids = []
    campaigns = set()
    counselors = set()
    for result in retrieved_results:
        metadata = result.get("metadata", {})
        call_id = str(metadata.get("call_id", "")).strip()
        if call_id:
            call_ids.append(call_id)
        campaign = str(metadata.get("campaign", "")).strip()
        salesperson = str(metadata.get("salesperson", "")).strip()
        if campaign:
            campaigns.add(campaign)
        if salesperson:
            counselors.add(salesperson)
    return {
        "call_ids": sorted(set(call_ids)),
        "campaigns": sorted(campaigns),
        "counselors": sorted(counselors),
        "call_analytics": {call_id: analytics.get(call_id, {}) for call_id in sorted(set(call_ids))},
    }


if __name__ == "__main__":
    sys.exit(main())
