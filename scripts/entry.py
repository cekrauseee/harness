"""Run the package directly from an installed plugin, without pip."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from harness.cli import main

raise SystemExit(main())
