from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

from .analytics_engine import AnalyticsEngine
from .citation_engine import CitationEngine
from .config import (
    DASHBOARDS_OUTPUT_DIR,
    DEFAULT_QUERIES_PATH,
    DIAGNOSTICS_LOG_HEADERS,
    DIAGNOSTICS_LOG_PATH,
    EVIDENCE_OUTPUT_DIR,
    JSON_OUTPUT_DIR,
    PHASE_5_CALL_ANALYTICS_CANDIDATES,
    PHASE_5_CHUNK_STORE_CANDIDATES,
    PHASE_5_EVIDENCE_LOOKUP_CANDIDATES,
    PHASE_5_VECTOR_INDEX_CANDIDATES,
    QUERY_LOG_HEADERS,
    QUERY_LOG_PATH,
    REPORTS_OUTPUT_DIR,
    RUNTIME_LOG_PATH,
    ensure_phase_directories,
)
from .evidence_engine import EvidenceEngine
from .query_parser import QueryParser
from .reasoning_engine import ReasoningEngine
from .recommendation_engine import RecommendationEngine
from .report_engine import ReportEngine
from .retrieval_engine import RetrievalEngine
from shared.json_utils import read_json, write_json
from shared.logging_utils import TerminalUI, append_csv_row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GEW Intelligence OS - Phase 6 Decision Intelligence")
    parser.add_argument("--call-id", type=str, help="Filter queries for a specific call ID.")
    parser.add_argument("--audio-id", type=str, help="Process using an existing audio file ID.")
    args = parser.parse_args(argv)

    ensure_phase_directories()
    terminal = TerminalUI(RUNTIME_LOG_PATH)
    terminal.rule("GEW Intelligence OS - Phase 6 Decision Intelligence", style="bold blue")

    vector_index = _read_first(PHASE_5_VECTOR_INDEX_CANDIDATES, [])
    evidence_lookup = _read_first(PHASE_5_EVIDENCE_LOOKUP_CANDIDATES, {})
    call_analytics = _read_first(PHASE_5_CALL_ANALYTICS_CANDIDATES, {})
    _ = _read_first(PHASE_5_CHUNK_STORE_CANDIDATES, [])

    effective_id = args.audio_id or args.call_id
    if effective_id:
        terminal.info(f"Context set for ID: {effective_id}")

    if not vector_index:
        terminal.warning("No Phase 5 vector index found. Nothing to query.")
        return 0

    queries = read_json(DEFAULT_QUERIES_PATH, default=[])
    if not queries:
        terminal.warning("No default queries configured.")
        return 0

    query_parser = QueryParser()
    retrieval_engine = RetrievalEngine(vector_index, evidence_lookup)
    evidence_engine = EvidenceEngine()
    citation_engine = CitationEngine()
    analytics_engine = AnalyticsEngine()
    reasoning_engine = ReasoningEngine()
    recommendation_engine = RecommendationEngine()
    report_engine = ReportEngine()

    dashboard_rows = []
    with terminal.build_progress() as progress:
        task = progress.add_task("Running decision-intelligence queries", total=len(queries))
        for item in queries:
            query_name = str(item.get("name", "query")).strip()
            query_text = str(item.get("query", "")).strip()
            
            # If ID is provided, inject it into the query context if not present
            if effective_id and effective_id not in query_text:
                query_text = f"{query_text} (Context: {effective_id})"
                
            terminal.rule(f"QUERY {query_name}", style="bold blue")
            started_at = time.perf_counter()

            try:
                parsed = query_parser.parse(query_name, query_text)
                retrieved = retrieval_engine.retrieve(parsed.search_text, parsed.filters)
                
                if effective_id:
                    retrieved = [item for item in retrieved if item.get("metadata", {}).get("call_id") == effective_id]

                analytics = analytics_engine.summarize(retrieved)
                analytics["call_analytics_snapshot"] = _slice_call_analytics(call_analytics, retrieved)
                evidence = evidence_engine.build(retrieved)
                evidence_issues = evidence_engine.ensure_traceable(evidence)
                if evidence_issues:
                    raise RuntimeError("; ".join(evidence_issues))
                reasoning = reasoning_engine.reason(parsed.raw_query, analytics, evidence)
                recommendations = recommendation_engine.recommend(parsed.query_type, analytics, evidence)
                citations = citation_engine.build(evidence)

                result = {
                    "query_name": parsed.name,
                    "query": parsed.raw_query,
                    "query_type": parsed.query_type,
                    "analysis_mode": parsed.analysis_mode,
                    "answer": reasoning.payload.get("answer", ""),
                    "confidence": reasoning.payload.get("confidence", 0.0),
                    "facts": reasoning.payload.get("facts", []),
                    "inferences": reasoning.payload.get("inferences", []),
                    "strategic_insights": reasoning.payload.get("strategic_insights", []),
                    "risk_alerts": reasoning.payload.get("risk_alerts", []),
                    "recommendations": recommendations,
                    "analytics": analytics,
                    "citations": citations,
                    "processing_time_sec": round(time.perf_counter() - started_at, 2),
                }

                output_path = JSON_OUTPUT_DIR / f"{parsed.name}.json"
                write_json(output_path, result)
                report_text = report_engine.build_report(result)
                report_path = REPORTS_OUTPUT_DIR / f"{parsed.name}.txt"
                report_path.write_text(report_text, encoding="utf-8")
                
                evidence_path = EVIDENCE_OUTPUT_DIR / f"{parsed.name}.json"
                write_json(evidence_path, evidence)

                dashboard_rows.append(
                    {
                        "query_name": parsed.name,
                        "query_type": parsed.query_type,
                        "answer_excerpt": (result["answer"][:100] + "...") if len(result["answer"]) > 100 else result["answer"],
                        "confidence": result["confidence"],
                        "recommendation_count": len(recommendations),
                        "processing_time": result["processing_time_sec"],
                    }
                )

                append_csv_row(
                    QUERY_LOG_PATH,
                    QUERY_LOG_HEADERS,
                    {
                        "query_name": parsed.name,
                        "status": "SUCCESS",
                        "processing_time_sec": str(result["processing_time_sec"]),
                        "error_message": "",
                    },
                )
            except Exception as exc:
                error_message = str(exc)
                terminal.exception(query_name, error_message, exc)
                append_csv_row(
                    QUERY_LOG_PATH,
                    QUERY_LOG_HEADERS,
                    {
                        "query_name": query_name,
                        "status": "FAILED",
                        "processing_time_sec": str(round(time.perf_counter() - started_at, 2)),
                        "error_message": error_message,
                    },
                )
            finally:
                progress.advance(task)

    _save_dashboard(dashboard_rows)
    terminal.success("Phase 6 completed. Decision intelligence results and reports are ready.")
    return 0


def _read_first(candidates: list[Path], default: Any) -> Any:
    for candidate in candidates:
        payload = read_json(candidate, default=None)
        if payload:
            return payload
    return default


def _slice_call_analytics(full_analytics: dict[str, Any], retrieved_items: list[dict[str, Any]]) -> dict[str, Any]:
    call_ids = {item.get("metadata", {}).get("call_id") for item in retrieved_items if item.get("metadata", {}).get("call_id")}
    return {call_id: full_analytics[call_id] for call_id in call_ids if call_id in full_analytics}


def _save_dashboard(rows: list[dict[str, Any]]) -> None:
    from shared.workbook_utils import save_csv_rows
    headers = ["query_name", "query_type", "answer_excerpt", "confidence", "recommendation_count", "processing_time"]
    save_csv_rows(DASHBOARDS_OUTPUT_DIR / "decision_intelligence_dashboard.csv", headers, rows)
