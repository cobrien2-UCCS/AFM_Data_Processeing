#!/usr/bin/env python3
"""
CLI entrypoint for plot_summary_from_csv (Py3 layer).

Usage:
python scripts/cli_plot.py --config config.yaml --csv summary.csv --plotting-mode sample_bar_with_error --out plots/
"""

from afm_pipeline.cli import main_plot as main  # re-export packaged entrypoint


if __name__ == "__main__":
    raise SystemExit(main())
