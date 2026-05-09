from __future__ import annotations

import sys
from pathlib import Path

PHASE_DIR = Path(__file__).resolve().parent
if str(PHASE_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE_DIR))

from reasoning.main import main as reasoning_main


def main() -> int:
    return reasoning_main()


if __name__ == "__main__":
    sys.exit(main())
