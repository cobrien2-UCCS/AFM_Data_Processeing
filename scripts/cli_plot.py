#!/usr/bin/env python3
"""
CLI entrypoint for plot_summary_from_csv (Py3 layer).

Usage:
python scripts/cli_plot.py --config config.yaml --csv summary.csv --plotting-mode sample_bar_with_error --out plots/
"""

import sys
from pathlib import Path

# Allow running from a source checkout without `pip install -e .`
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from afm_pipeline.cli import main_plot as main  # re-export packaged entrypoint


if __name__ == "__main__":
    raise SystemExit(main())
