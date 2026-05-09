from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
PHASE_MODULES = [
    "phase_1_audio_ingestion_transcription.main",
    "phase_2_enrichment_structured_extraction.main",
    "phase_3_ai_reasoning.main",
    "phase_4_knowledge_memory.main",
    "phase_5_query_intelligence.main",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="GEW Intelligence OS - Full Pipeline Orchestrator")
    parser.add_argument("--call-id", type=str, help="Process only a specific call ID (e.g., CALL_0006).")
    args = parser.parse_args()

    validation = subprocess.run([sys.executable, str(ROOT_DIR / "tools" / "validate_architecture.py")], cwd=ROOT_DIR)
    if validation.returncode != 0:
        return validation.returncode

    for module_name in PHASE_MODULES:
        print(f"Starting {module_name}...")
        cmd = [sys.executable, "-m", module_name]
        if args.call_id:
            cmd.extend(["--call-id", args.call_id])
            
        result = subprocess.run(cmd, cwd=ROOT_DIR)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
