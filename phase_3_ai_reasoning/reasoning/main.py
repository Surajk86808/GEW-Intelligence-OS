from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

from reasoning.config import (
    CALL_MANIFEST_CANDIDATES,
    EMOTION_MANIFEST_CANDIDATES,
    MALFORMED_OUTPUT_LOG_HEADERS,
    MALFORMED_OUTPUT_LOG_PATH,
    MAX_BATCH_SIZE,
    PROCESSING_LOG_HEADERS,
    PROCESSING_LOG_PATH,
    JSON_OUTPUT_DIR,
    REASONING_MANIFEST_PATH,
    REPORTS_DIR,
    RUNTIME_LOG_PATH,
    SUMMARIES_DIR,
    EVIDENCE_DIR,
    TRANSCRIPT_MANIFEST_CANDIDATES,
    ensure_phase_directories,
)
from reasoning.crm_engine import CRMEngine
from reasoning.evidence_engine import EvidenceEngine
from reasoning.objection_engine import ObjectionEngine
from reasoning.reasoning_engine import ReasoningEngine
from reasoning.recommendation_engine import RecommendationEngine
from reasoning.scoring_engine import ScoringEngine
from shared.json_utils import read_json, write_json
from shared.logging_utils import TerminalUI, append_csv_row
from shared.schema_utils import PhaseOutputEntry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GEW Intelligence OS - Phase 4 Reasoning")
    parser.add_argument("--call-id", type=str, help="Process only a specific call ID.")
    parser.add_argument("--audio-id", type=str, help="Process using an existing audio file ID.")
    args = parser.parse_args(argv)

    ensure_phase_directories()
    terminal = TerminalUI(RUNTIME_LOG_PATH)
    terminal.rule("GEW Intelligence OS - Phase 4 AI Reasoning", style="bold yellow")

    transcript_manifest = _read_first_json(TRANSCRIPT_MANIFEST_CANDIDATES, [])
    emotion_manifest = _read_first_json(EMOTION_MANIFEST_CANDIDATES, [])
    call_manifest = _read_first_json(CALL_MANIFEST_CANDIDATES, [])

    if not transcript_manifest:
        terminal.warning("No transcript manifest found. Nothing to reason over.")
        return 0

    effective_id = args.audio_id or args.call_id
    if effective_id:
        terminal.info(f"Filtering for ID: {effective_id}")
        transcript_manifest = [item for item in transcript_manifest if str(item.get("call_id", "")).strip() == effective_id]
        if not transcript_manifest:
            terminal.warning(f"No match found for ID: {effective_id}")
            return 0

    phase3_by_call = {str(item.get("call_id", "")).strip(): item for item in emotion_manifest}
    phase1_by_call = {str(item.get("call_id", "")).strip(): item for item in call_manifest}

    try:
        reasoning_engine = ReasoningEngine()
        crm_engine = CRMEngine()
        objection_engine = ObjectionEngine()
        evidence_engine = EvidenceEngine()
        scoring_engine = ScoringEngine()
        recommendation_engine = RecommendationEngine()
    except Exception as exc:
        terminal.exception("PHASE_4", f"Failed to initialize reasoning subsystem: {exc}", exc)
        return 1

    output_manifest: list[dict[str, object]] = []
    workload = transcript_manifest[:MAX_BATCH_SIZE]
    with terminal.build_progress() as progress:
        task = progress.add_task("Generating conversational intelligence", total=len(workload))
        for sequence, transcript_entry in enumerate(workload, start=1):
            call_id = str(transcript_entry.get("call_id", "")).strip()
            transcript_path = Path(str(transcript_entry.get("output_path", "")).strip())
            phase3_json_path = Path(str(phase3_by_call.get(call_id, {}).get("output_path", "")).strip())
            terminal.rule(f"[{sequence}/{len(workload)}] REASON {call_id}", style="bold yellow")
            started_at = time.perf_counter()

            try:
                crm_context = crm_engine.build_crm_context(phase1_by_call.get(call_id, {}))
                analysis, llm_response = reasoning_engine.analyze_call(call_id, transcript_path, phase3_json_path, crm_context)
                phase3_payload = read_json(phase3_json_path, default={}) if phase3_json_path.exists() else {}

                analysis["call_id"] = call_id
                analysis["crm_context"] = crm_context
                analysis["objections"] = objection_engine.validate(analysis.get("objections", []))
                analysis["rule_based_objection_signals"] = objection_engine.detect_rule_based_signals(
                    transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else ""
                )
                analysis = evidence_engine.normalize_evidence(analysis, fallback_emotion=_fallback_emotion(phase3_payload))
                analysis = scoring_engine.score(analysis, phase3_payload, crm_context)
                analysis = recommendation_engine.enrich(analysis, phase3_payload)
                analysis["model_info"] = {
                    "provider": llm_response.provider,
                    "model_name": llm_response.model_name,
                    "input_tokens": llm_response.input_tokens,
                    "output_tokens": llm_response.output_tokens,
                    "estimated_cost_usd": llm_response.estimated_cost_usd,
                }
                analysis["processing_time_sec"] = round(time.perf_counter() - started_at, 2)

                issues = evidence_engine.validate_analysis(analysis)
                if issues:
                    raise RuntimeError("; ".join(issues))

                json_path = JSON_OUTPUT_DIR / f"{call_id}.json"
                report_path = REPORTS_DIR / f"{call_id}.txt"
                summary_path = SUMMARIES_DIR / f"{call_id}.txt"
                evidence_path = EVIDENCE_DIR / f"{call_id}.json"
                write_json(json_path, analysis)
                report_text = evidence_engine.build_report(analysis)
                report_path.write_text(report_text, encoding="utf-8")
                summary_path.write_text(_build_summary(analysis), encoding="utf-8")
                evidence_engine.export_evidence(evidence_path, analysis.get("evidence", []))

                output_manifest.append(
                    PhaseOutputEntry(
                        call_id=call_id,
                        source_path=str(transcript_path),
                        output_path=str(json_path),
                        metadata_path=str(report_path),
                        extra={
                            "summary_path": str(summary_path),
                            "evidence_path": str(evidence_path),
                        },
                    ).to_dict()
                )
                append_csv_row(
                    PROCESSING_LOG_PATH,
                    PROCESSING_LOG_HEADERS,
                    {
                        "call_id": call_id,
                        "status": "SUCCESS",
                        "json_output_path": str(json_path),
                        "report_path": str(report_path),
                        "error_message": "",
                        "processing_time_sec": str(analysis["processing_time_sec"]),
                        "input_tokens": str(llm_response.input_tokens or ""),
                        "output_tokens": str(llm_response.output_tokens or ""),
                        "estimated_cost_usd": str(llm_response.estimated_cost_usd or ""),
                    },
                )
                terminal.summary(
                    "Reasoning Summary",
                    [
                        ("Call ID", call_id),
                        ("Intent", str(analysis.get("customer_intent", {}).get("level", ""))),
                        ("Lead Score", str(analysis.get("lead_quality_score", 0))),
                        ("Conversion", str(analysis.get("conversion_probability", 0))),
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
                        "json_output_path": "",
                        "report_path": "",
                        "error_message": error_message,
                        "processing_time_sec": str(round(time.perf_counter() - started_at, 2)),
                        "input_tokens": "",
                        "output_tokens": "",
                        "estimated_cost_usd": "",
                    },
                )
                append_csv_row(
                    MALFORMED_OUTPUT_LOG_PATH,
                    MALFORMED_OUTPUT_LOG_HEADERS,
                    {
                        "call_id": call_id,
                        "error_message": error_message,
                        "raw_output_excerpt": "",
                    },
                )
            finally:
                progress.advance(task)

    write_json(REASONING_MANIFEST_PATH, output_manifest)
    terminal.success("Phase 4 completed. Evidence-backed conversational intelligence outputs are ready.")
    return 0


def _read_first_json(candidates: list[Path], default: Any) -> Any:
    for candidate in candidates:
        payload = read_json(candidate, default=None)
        if payload:
            return payload
    return default


def _fallback_emotion(phase3_payload: dict[str, Any]) -> str:
    emotion_summary = phase3_payload.get("emotion_summary", {})
    if emotion_summary:
        return next(iter(emotion_summary.keys()))
    return "neutral"


def _build_summary(analysis: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"EXECUTIVE SUMMARY: {analysis.get('call_id', '')}",
            f"Intent: {analysis.get('customer_intent', {}).get('level', 'unknown')}",
            f"Lead Quality Score: {analysis.get('lead_quality_score', 0)}",
            f"Conversion Probability: {analysis.get('conversion_probability', 0)}",
            f"Strategic Summary: {analysis.get('strategic_summary', '')}",
        ]
    )


if __name__ == "__main__":
    sys.exit(main())

