#!/usr/bin/env python3
"""
TR-AIS entry point with ASCII art banner.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BANNER = r"""
  _______ _____            _____ _____  _____
 |__   __|  __ \          |  _  |_   _|/ ____|
    | |  | |__) |  ____   | |_| | | | | (___
    | |  |  _  /  |____|  |  _  | | |  \___ \
    | |  | | \ \          | | | |_| |_ ____) |
    |_|  |_|  \_\         |_| |_|_____|_____/

            🎹  Let's jam.  🥁
"""


def main():
    print(BANNER)

    from backend.cli import main as cli_main
    asyncio.run(cli_main())


if __name__ == "__main__":
    main()
