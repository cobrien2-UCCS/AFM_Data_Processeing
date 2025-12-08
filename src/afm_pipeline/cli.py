"""
CLI entrypoints for summarize and plot (packaged).
"""

import argparse
import sys
from pathlib import Path

from . import load_config, summarize_folder_to_csv, plot_summary_from_csv


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


def parse_args_summarize(argv=None):
    p = argparse.ArgumentParser(description="Summarize a folder of TIFFs into CSV.")
    p.add_argument("--config", required=True, help="Path to config YAML/JSON.")
    p.add_argument("--input-root", required=True, help="Directory containing TIFF files.")
    p.add_argument("--out-csv", required=True, help="Output CSV path.")
    p.add_argument("--processing-mode", help="Processing mode name.")
    p.add_argument("--csv-mode", help="CSV mode name.")
    p.add_argument("--profile", help="Profile name to pull defaults from config.profiles.")
    return p.parse_args(argv)


def main_summarize(argv=None):
    args = parse_args_summarize(argv)
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


def parse_args_plot(argv=None):
    p = argparse.ArgumentParser(description="Plot from a summary CSV using plotting_mode.")
    p.add_argument("--config", required=True, help="Path to config YAML/JSON.")
    p.add_argument("--csv", required=True, help="Path to summary CSV.")
    p.add_argument("--plotting-mode", help="Plotting mode name.")
    p.add_argument("--profile", help="Profile name to pull plotting_modes from config.profiles.")
    p.add_argument("--out", required=True, help="Output directory for plots.")
    return p.parse_args(argv)


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


def main_plot(argv=None):
    args = parse_args_plot(argv)
    cfg = load_config(args.config)
    plotting_mode = resolve_plotting_mode(cfg, args.profile, args.plotting_mode)
    plot_summary_from_csv(args.csv, plotting_mode, cfg, args.out)
    print("Wrote plots to %s" % args.out)
    return 0


def main():
    # Simple dispatcher if called as module
    parser = argparse.ArgumentParser(description="AFM pipeline CLI")
    parser.add_argument("command", choices=["summarize", "plot"], help="Command to run")
    args, remaining = parser.parse_known_args()
    if args.command == "summarize":
        return main_summarize(remaining)
    return main_plot(remaining)


if __name__ == "__main__":
    sys.exit(main())
