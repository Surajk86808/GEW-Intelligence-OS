from __future__ import annotations

import sys

from .decision_engine.main import main as decision_main


def main() -> int:
    return decision_main()


if __name__ == "__main__":
    sys.exit(main())
