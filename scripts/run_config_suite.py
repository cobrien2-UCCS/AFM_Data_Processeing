#!/usr/bin/env python3
"""
Run a suite of configs end-to-end: manifest -> pygwy (Py2) -> plots (Py3).

Usage example (PowerShell):
  py -3 scripts/run_config_suite.py --configs configs\\*.yaml --input-root scans\\ --output-root out\\suite --py2-exe "C:\\Python27\\python.exe" --profile modulus_grid

Notes:
- Config files can live anywhere; pass a glob or directory.
- Each config is run into its own output folder: <output-root>/<config-stem>/...
- Requires the Py2 pygwy environment for the processing step.
"""

import argparse
import glob
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def load_config(path: Path) -> dict:
    import yaml

    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_modes(cfg: dict, profile: str, processing_mode: str, csv_mode: str) -> Tuple[str, str, List[str], List[str]]:
    """Pick processing/csv/plotting_modes from profile or explicit args."""
    pm = processing_mode
    cm = csv_mode
    plotting = []
    aggregate_modes = []

    if profile:
        profiles = cfg.get("profiles", {}) or {}
        prof = profiles.get(profile) or {}
        pm = pm or prof.get("processing_mode")
        cm = cm or prof.get("csv_mode")
        plotting = prof.get("plotting_modes") or []
        aggregate_modes = prof.get("aggregate_modes") or []

    if not pm or not cm:
        raise ValueError("processing_mode and csv_mode are required (supply --profile or explicit --processing-mode/--csv-mode).")

    # If user passed plotting_modes explicitly, caller will override.
    return pm, cm, plotting, aggregate_modes


def collect_configs(config_args: List[str]) -> List[Path]:
    paths: List[Path] = []
    for arg in config_args:
        p = Path(arg)
        if p.is_dir():
            paths.extend(sorted(p.glob("*.yaml")))
            paths.extend(sorted(p.glob("*.yml")))
        else:
            matches = glob.glob(str(p))
            if matches:
                paths.extend([Path(m) for m in matches])
            else:
                raise FileNotFoundError("Config not found: %s" % arg)
    seen = []
    for p in paths:
        if p not in seen:
            seen.append(p)
    return seen


def run_cmd(cmd: List[str], dry_run: bool):
    print(" ".join(cmd))
    if dry_run:
        return 0
    proc = subprocess.run(cmd)
    return proc.returncode


def parse_args():
    ap = argparse.ArgumentParser(description="Run a suite of configs through manifest -> pygwy -> plotting.")
    ap.add_argument("--configs", nargs="+", required=True, help="Config paths or globs, or directories containing *.yaml.")
    ap.add_argument("--profiles", nargs="*", help="Optional per-config profiles (aligned to --configs list). If omitted, --profile applies to all.")
    ap.add_argument("--input-root", required=True, help="Input TIFF folder.")
    ap.add_argument("--output-root", default="out/suite", help="Root for outputs (per-config subfolders).")
    ap.add_argument("--py2-exe", default="C:\\Python27\\python.exe", help="Python 2.7 executable for pygwy step.")
    ap.add_argument("--profile", help="Profile name to use for all configs (ignored when --profiles is given).")
    ap.add_argument("--processing-mode", help="Processing mode (overrides profile).")
    ap.add_argument("--csv-mode", help="CSV mode (overrides profile).")
    ap.add_argument("--plotting-modes", nargs="*", help="Plotting modes to render (overrides profile plotting_modes).")
    ap.add_argument("--aggregate-modes", nargs="*", help="Aggregate modes to run (overrides profile aggregate_modes).")
    ap.add_argument("--collect-job", help="Optional file_collect_jobs job name to run before processing (uses fuzzy matching to stage inputs).")
    ap.add_argument("--pattern", default="*.tif;*.tiff", help="Glob pattern(s) for TIFFs, ';' separated.")
    ap.add_argument("--dry-run", action="store_true", help="Print commands only.")
    return ap.parse_args()


def main():
    args = parse_args()
    cfg_paths = collect_configs(args.configs)
    print("Configs to run: %d" % len(cfg_paths))

    profiles_for_configs: List[str] = []
    if args.profiles:
        if len(args.profiles) != len(cfg_paths):
            raise ValueError("If --profiles is provided, it must have the same length as --configs.")
        profiles_for_configs = args.profiles
    else:
        profiles_for_configs = [args.profile] * len(cfg_paths)

    for cfg_path in cfg_paths:
        cfg = load_config(cfg_path)
        profile_for_cfg = profiles_for_configs[cfg_paths.index(cfg_path)]
        pm, cm, plotting, agg_modes = resolve_modes(cfg, profile_for_cfg, args.processing_mode, args.csv_mode)
        if args.plotting_modes is not None:
            plotting = args.plotting_modes
        if args.aggregate_modes is not None:
            agg_modes = args.aggregate_modes

        out_root = Path(args.output_root)
        out_dir = out_root / cfg_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = out_dir / "job_manifest.json"
        summary_csv = out_dir / "summary.csv"
        plots_dir = out_dir / "plots"
        plots_dir.mkdir(parents=True, exist_ok=True)

        input_root_for_cfg = str(Path(args.input_root).resolve())
        if args.collect_job:
            collect_root = out_dir / "collect"
            collect_root.mkdir(parents=True, exist_ok=True)
            collect_cmd = [
                sys.executable,
                "scripts/collect_files.py",
                "--config",
                str(cfg_path),
                "--job",
                args.collect_job,
                "--input-root",
                input_root_for_cfg,
                "--out-root",
                str(collect_root.resolve()),
            ]
            if run_cmd(collect_cmd, args.dry_run) != 0:
                print("File collection failed; skipping this config.")
                continue
            if not args.dry_run:
                # Pick the newest run_metadata.json under collect_root.
                metas = sorted(collect_root.rglob("run_metadata.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                if not metas:
                    raise RuntimeError("collect-job ran but no run_metadata.json found under %s" % collect_root)
                meta = json.loads(metas[0].read_text(encoding="utf-8"))
                copied_root = meta.get("copied_root")
                if not copied_root:
                    raise RuntimeError("collect-job metadata missing copied_root: %s" % metas[0])
                input_root_for_cfg = str(Path(copied_root).resolve())

        manifest_cmd = [
            sys.executable,
            "scripts/make_job_manifest.py",
            "--config",
            str(cfg_path),
            "--input-root",
            input_root_for_cfg,
            "--output-dir",
            str(out_dir.resolve()),
            "--processing-mode",
            pm,
            "--csv-mode",
            cm,
            "--out",
            str(manifest_path),
            "--pattern",
            args.pattern,
        ]
        if args.profile:
            manifest_cmd.extend(["--profile", args.profile])

        print(f"\n=== {cfg_path.name} ===")
        if run_cmd(manifest_cmd, args.dry_run) != 0:
            print("Manifest generation failed; skipping this config.")
            continue

        run_cmd(
            [
                args.py2_exe,
                "scripts/run_pygwy_job.py",
                "--manifest",
                str(manifest_path),
            ],
            args.dry_run,
        )

        if plotting:
            for mode in plotting:
                run_cmd(
                    [
                        sys.executable,
                        "scripts/cli_plot.py",
                        "--config",
                        str(cfg_path),
                        "--csv",
                        str(summary_csv),
                        "--plotting-mode",
                        mode,
                        "--out",
                        str(plots_dir),
                    ],
                    args.dry_run,
                )

        if agg_modes:
            aggs_dir = out_dir / "aggregates"
            aggs_dir.mkdir(parents=True, exist_ok=True)
            run_cmd(
                [
                    sys.executable,
                    "scripts/cli_aggregate_config.py",
                    "--config",
                    str(cfg_path),
                    "--csv",
                    str(summary_csv),
                    "--aggregate-modes",
                    ",".join(agg_modes),
                    "--out-dir",
                    str(aggs_dir),
                ],
                args.dry_run,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
