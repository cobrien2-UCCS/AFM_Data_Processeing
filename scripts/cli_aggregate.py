#!/usr/bin/env python3
"""
CLI entrypoint for dataset-level aggregation from summary.csv (Py3 layer).

Usage:
py -3 scripts/cli_aggregate.py --csv out/summary.csv --out-csv out/summary_aggregated.csv --group-by "mode,units"
"""

import sys
from pathlib import Path

# Allow running from a source checkout without `pip install -e .`
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from afm_pipeline.cli import main_aggregate as main  # re-export packaged entrypoint


if __name__ == "__main__":
    raise SystemExit(main())

