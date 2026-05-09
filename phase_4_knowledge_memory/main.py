from __future__ import annotations

import sys

from .memory.main import main as knowledge_main


def main() -> int:
    return knowledge_main()


if __name__ == "__main__":
    sys.exit(main())
