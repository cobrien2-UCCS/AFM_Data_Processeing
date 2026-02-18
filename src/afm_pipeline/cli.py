"""
CLI entrypoints for summarize and plot (packaged).
"""

import argparse
import sys
from pathlib import Path

from . import load_config, summarize_folder_to_csv, plot_summary_from_csv
from .summarize import load_csv_table, aggregate_summary_table, write_aggregated_csv


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


def parse_args_aggregate(argv=None):
    p = argparse.ArgumentParser(description="Aggregate per-scan summary stats into dataset-level stats.")
    p.add_argument("--csv", required=True, help="Path to summary CSV (per-scan rows).")
    p.add_argument("--out-csv", required=True, help="Output CSV path for aggregated rows.")
    p.add_argument(
        "--group-by",
        default="",
        help="Comma-separated list of CSV columns to group by (e.g., mode,metric_type,units). Default: no grouping.",
    )
    p.add_argument("--allow-mixed-units", action="store_true", help="Allow aggregating mixed units (sets units='MIXED').")
    p.add_argument("--value-col", default="avg_value", help="Column name for per-scan mean (default: avg_value).")
    p.add_argument("--std-col", default="std_value", help="Column name for per-scan std (default: std_value).")
    p.add_argument("--n-col", default="n_valid", help="Column name for per-scan n_valid (default: n_valid).")
    p.add_argument("--units-col", default="units", help="Column name for units (default: units).")
    return p.parse_args(argv)


def main_aggregate(argv=None):
    args = parse_args_aggregate(argv)
    group_by = [c.strip() for c in str(args.group_by).split(",") if c.strip()]
    table = load_csv_table(args.csv)
    aggregated = aggregate_summary_table(
        table,
        value_col=args.value_col,
        std_col=args.std_col,
        n_col=args.n_col,
        units_col=args.units_col,
        group_by=group_by,
        allow_mixed_units=bool(args.allow_mixed_units),
    )
    write_aggregated_csv(args.out_csv, aggregated)
    print("Wrote aggregated CSV to %s" % args.out_csv)
    return 0


def parse_args_aggregate_config(argv=None):
    p = argparse.ArgumentParser(description="Aggregate using aggregate_modes definitions from a config/profile.")
    p.add_argument("--config", required=True, help="Path to config YAML/JSON.")
    p.add_argument("--csv", required=True, help="Path to summary CSV (per-scan rows).")
    p.add_argument(
        "--profile",
        help="Profile name to pull aggregate_modes list from config.profiles (unless --aggregate-modes is given).",
    )
    p.add_argument(
        "--aggregate-modes",
        default="",
        help="Comma-separated aggregate_modes names to run (overrides profile).",
    )
    p.add_argument(
        "--out-dir",
        default="",
        help="Output directory base for aggregate outputs. If empty, uses each mode's out_relpath as-is (relative to CSV parent).",
    )
    return p.parse_args(argv)


def main_aggregate_config(argv=None):
    args = parse_args_aggregate_config(argv)
    cfg = load_config(args.config)

    requested = [c.strip() for c in str(args.aggregate_modes).split(",") if c.strip()]
    if not requested:
        if not args.profile:
            raise ValueError("Pass --profile or --aggregate-modes.")
        profiles = cfg.get("profiles", {}) or {}
        if args.profile not in profiles:
            raise ValueError("Unknown profile: %s" % args.profile)
        prof = profiles.get(args.profile) or {}
        requested = list(prof.get("aggregate_modes") or [])

    if not requested:
        raise ValueError("No aggregate modes requested (profile has no aggregate_modes).")

    modes_def = cfg.get("aggregate_modes", {}) or {}
    table = load_csv_table(args.csv)
    csv_parent = Path(args.csv).resolve().parent
    out_dir = Path(args.out_dir).resolve() if args.out_dir else None

    for name in requested:
        if name not in modes_def:
            raise ValueError("Unknown aggregate_mode: %s" % name)
        mdef = modes_def.get(name) or {}
        group_by = mdef.get("group_by") or []
        if isinstance(group_by, str):
            group_by = [c.strip() for c in group_by.split(",") if c.strip()]
        if not isinstance(group_by, list):
            raise ValueError("aggregate_modes.%s.group_by must be a list or string" % name)

        out_relpath = str(mdef.get("out_relpath") or ("aggregates/%s.csv" % name))
        if out_dir is not None:
            out_csv = out_dir / Path(out_relpath).name
        else:
            out_csv = csv_parent / Path(out_relpath)

        aggregated = aggregate_summary_table(
            table,
            value_col=str(mdef.get("value_col") or "avg_value"),
            std_col=str(mdef.get("std_col") or "std_value"),
            n_col=str(mdef.get("n_col") or "n_valid"),
            units_col=str(mdef.get("units_col") or "units"),
            group_by=[str(x) for x in group_by],
            allow_mixed_units=bool(mdef.get("allow_mixed_units", False)),
        )
        write_aggregated_csv(out_csv, aggregated)
        print("Wrote aggregated CSV to %s" % out_csv)

    return 0


def main():
    # Simple dispatcher if called as module
    parser = argparse.ArgumentParser(description="AFM pipeline CLI")
    parser.add_argument("command", choices=["summarize", "plot", "aggregate", "aggregate-config"], help="Command to run")
    args, remaining = parser.parse_known_args()
    if args.command == "summarize":
        return main_summarize(remaining)
    if args.command == "plot":
        return main_plot(remaining)
    if args.command == "aggregate":
        return main_aggregate(remaining)
    return main_aggregate_config(remaining)


if __name__ == "__main__":
    sys.exit(main())
