#!/usr/bin/env python3
"""
CLI entrypoint for summarize_folder_to_csv (Py3 layer).

Usage:
python scripts/cli_summarize.py --config config.yaml --input-root scans/ --out-csv summary.csv --processing-mode modulus_basic --csv-mode default_scalar
"""

from afm_pipeline.cli import main_summarize as main  # re-export packaged entrypoint


if __name__ == "__main__":
    raise SystemExit(main())
