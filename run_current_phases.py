from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
PHASE_MODULES = [
    "phase_4_knowledge_memory.main",
    "phase_5_query_intelligence.main",
]


def main() -> int:
    validation = subprocess.run([sys.executable, str(ROOT_DIR / "tools" / "validate_architecture.py")], cwd=ROOT_DIR)
    if validation.returncode != 0:
        return validation.returncode

    for module_name in PHASE_MODULES:
        print(f"Starting {module_name}...")
        result = subprocess.run([sys.executable, "-m", module_name], cwd=ROOT_DIR)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
