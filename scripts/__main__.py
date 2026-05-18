"""CLI entrypoint for Three-O platform. Run with: python3 -m scripts [command]."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import main  # noqa: E402

if __name__ == "__main__":
    main()
