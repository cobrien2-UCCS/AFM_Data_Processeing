#!/usr/bin/env python3
"""
CLI entrypoint for plot_summary_from_csv (Py3 layer).

Usage:
python scripts/cli_plot.py --config config.yaml --csv summary.csv --plotting-mode sample_bar_with_error --out plots/
"""

import argparse
import sys
from pathlib import Path

# Allow running without installing the package
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from afm_pipeline import load_config, plot_summary_from_csv  # noqa: E402


def resolve_plotting_mode(cfg, profile, plotting_mode):
    if plotting_mode:
        return plotting_mode
    if profile:
        profiles = cfg.get("profiles", {})
        if profile not in profiles:
            raise ValueError("Unknown profile: %s" % profile)
        prof = profiles[profile] or {}
        modes = prof.get("plotting_modes") or []
        if modes:
            return modes[0]
    raise ValueError("plotting_mode is required (pass --plotting-mode or a profile with plotting_modes).")


def parse_args():
    p = argparse.ArgumentParser(description="Plot from a summary CSV using plotting_mode.")
    p.add_argument("--config", required=True, help="Path to config YAML/JSON.")
    p.add_argument("--csv", required=True, help="Path to summary CSV.")
    p.add_argument("--plotting-mode", help="Plotting mode name.")
    p.add_argument("--profile", help="Profile name to pull plotting_modes from config.profiles.")
    p.add_argument("--out", required=True, help="Output directory for plots.")
    return p.parse_args()


def main():
    args = parse_args()
    cfg = load_config(args.config)
    plotting_mode = resolve_plotting_mode(cfg, args.profile, args.plotting_mode)
    plot_summary_from_csv(args.csv, plotting_mode, cfg, args.out)
    print("Wrote plots to %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
