"""PyInstaller entry script (kept outside the package so relative imports resolve)."""

import sys

from desktop.main import main

if __name__ == "__main__":
    sys.exit(main())
