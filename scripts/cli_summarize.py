#!/usr/bin/env python3
"""
CLI entrypoint for summarize_folder_to_csv (Py3 layer).

Usage:
python scripts/cli_summarize.py --config config.yaml --input-root scans/ --out-csv summary.csv --processing-mode modulus_basic --csv-mode default_scalar
"""

import argparse
import sys
from pathlib import Path

# Allow running without installing the package
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from afm_pipeline import load_config, summarize_folder_to_csv  # noqa: E402


def resolve_modes(cfg, profile, processing_mode, csv_mode):
    """Resolve processing/csv modes using profile overrides."""
    chosen_processing = processing_mode
    chosen_csv = csv_mode

    if profile:
        profiles = cfg.get("profiles", {})
        if profile not in profiles:
            raise ValueError("Unknown profile: %s" % profile)
        prof = profiles[profile] or {}
        chosen_processing = chosen_processing or prof.get("processing_mode")
        chosen_csv = chosen_csv or prof.get("csv_mode")

    if not chosen_processing:
        raise ValueError("processing_mode is required (pass --processing-mode or a profile).")
    if not chosen_csv:
        raise ValueError("csv_mode is required (pass --csv-mode or a profile).")

    return chosen_processing, chosen_csv


def parse_args():
    p = argparse.ArgumentParser(description="Summarize a folder of TIFFs into CSV.")
    p.add_argument("--config", required=True, help="Path to config YAML/JSON.")
    p.add_argument("--input-root", required=True, help="Directory containing TIFF files.")
    p.add_argument("--out-csv", required=True, help="Output CSV path.")
    p.add_argument("--processing-mode", help="Processing mode name.")
    p.add_argument("--csv-mode", help="CSV mode name.")
    p.add_argument("--profile", help="Profile name to pull defaults from config.profiles.")
    return p.parse_args()


def main():
    args = parse_args()
    cfg = load_config(args.config)
    processing_mode, csv_mode = resolve_modes(cfg, args.profile, args.processing_mode, args.csv_mode)

    summarize_folder_to_csv(
        input_root=Path(args.input_root),
        output_csv_path=Path(args.out_csv),
        processing_mode=processing_mode,
        csv_mode=csv_mode,
        cfg=cfg,
    )
    print("Wrote CSV to %s" % args.out_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
