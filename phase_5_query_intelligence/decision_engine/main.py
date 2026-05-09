from __future__ import annotations

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


def main() -> int:
    ensure_phase_directories()
    terminal = TerminalUI(RUNTIME_LOG_PATH)
    terminal.rule("GEW Intelligence OS - Phase 6 Decision Intelligence", style="bold blue")

    vector_index = _read_first(PHASE_5_VECTOR_INDEX_CANDIDATES, [])
    evidence_lookup = _read_first(PHASE_5_EVIDENCE_LOOKUP_CANDIDATES, {})
    call_analytics = _read_first(PHASE_5_CALL_ANALYTICS_CANDIDATES, {})
    _ = _read_first(PHASE_5_CHUNK_STORE_CANDIDATES, [])

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
            terminal.rule(f"QUERY {query_name}", style="bold blue")
            started_at = time.perf_counter()

            try:
                parsed = query_parser.parse(query_name, query_text)
                retrieved = retrieval_engine.retrieve(parsed.search_text, parsed.filters)
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
                    "evidence": evidence,
                    "model_info": {
                        "provider": reasoning.provider,
                        "model_name": reasoning.model_name,
                        "input_tokens": reasoning.input_tokens,
                        "output_tokens": reasoning.output_tokens,
                        "estimated_cost_usd": reasoning.estimated_cost_usd,
                    },
                    "processing_time_sec": round(time.perf_counter() - started_at, 2),
                }

                json_path = JSON_OUTPUT_DIR / f"{parsed.name}.json"
                report_path = REPORTS_OUTPUT_DIR / f"{parsed.name}.txt"
                evidence_path = EVIDENCE_OUTPUT_DIR / f"{parsed.name}.json"
                write_json(json_path, result)
                report_path.write_text(report_engine.build_report(result), encoding="utf-8")
                write_json(evidence_path, evidence)

                dashboard_rows.append(
                    {
                        "query_name": parsed.name,
                        "query_type": parsed.query_type,
                        "confidence": result["confidence"],
                        "matched_calls": analytics.get("matched_calls", 0),
                        "top_emotions": analytics.get("top_emotions", []),
                    }
                )
                append_csv_row(
                    QUERY_LOG_PATH,
                    QUERY_LOG_HEADERS,
                    {
                        "query_name": parsed.name,
                        "status": "SUCCESS",
                        "query_text": parsed.raw_query,
                        "retrieved_results": str(len(retrieved)),
                        "confidence": str(result["confidence"]),
                        "processing_time_sec": str(result["processing_time_sec"]),
                        "input_tokens": str(reasoning.input_tokens or ""),
                        "output_tokens": str(reasoning.output_tokens or ""),
                        "estimated_cost_usd": str(reasoning.estimated_cost_usd or ""),
                    },
                )
                append_csv_row(
                    DIAGNOSTICS_LOG_PATH,
                    DIAGNOSTICS_LOG_HEADERS,
                    {
                        "query_name": parsed.name,
                        "query_type": parsed.query_type,
                        "filters": str(parsed.filters),
                        "top_score": str(retrieved[0]["score"] if retrieved else ""),
                        "evidence_count": str(len(evidence)),
                    },
                )
                terminal.summary(
                    "Decision Query Summary",
                    [
                        ("Query", parsed.name),
                        ("Type", parsed.query_type),
                        ("Confidence", str(result["confidence"])),
                        ("Evidence", str(len(evidence))),
                        ("Report", str(report_path)),
                    ],
                )
            except Exception as exc:
                append_csv_row(
                    QUERY_LOG_PATH,
                    QUERY_LOG_HEADERS,
                    {
                        "query_name": query_name,
                        "status": "FAILED",
                        "query_text": query_text,
                        "retrieved_results": "0",
                        "confidence": "0",
                        "processing_time_sec": str(round(time.perf_counter() - started_at, 2)),
                        "input_tokens": "",
                        "output_tokens": "",
                        "estimated_cost_usd": "",
                    },
                )
                terminal.exception(query_name, str(exc), exc)
            finally:
                progress.advance(task)

    write_json(DASHBOARDS_OUTPUT_DIR / "decision_dashboard.json", dashboard_rows)
    terminal.success("Phase 6 completed. Decision-intelligence outputs are ready.")
    return 0


def _read_first(candidates: list[Path], default: Any) -> Any:
    for candidate in candidates:
        payload = read_json(candidate, default=None)
        if payload:
            return payload
    return default


def _slice_call_analytics(call_analytics: dict[str, Any], retrieved: list[dict[str, Any]]) -> dict[str, Any]:
    selected = {}
    for item in retrieved[:5]:
        call_id = str(item.get("metadata", {}).get("call_id", "")).strip()
        if call_id and call_id in call_analytics:
            selected[call_id] = call_analytics[call_id]
    return selected


if __name__ == "__main__":
    sys.exit(main())
