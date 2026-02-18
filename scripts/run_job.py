#!/usr/bin/env python3
"""
Run a config-defined job end-to-end (optional collect -> manifest -> pygwy -> plots -> aggregates).

Usage:
  py -3 scripts/run_job.py --config config.yaml --job my_job
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_config(path: Path) -> Dict[str, Any]:
    # Use the package loader if available, fall back to YAML/JSON.
    try:
        repo_root = Path(__file__).resolve().parents[1]
        src_root = repo_root / "src"
        if str(src_root) not in sys.path:
            sys.path.insert(0, str(src_root))
        from afm_pipeline.config import load_config  # type: ignore

        return load_config(path)
    except Exception:
        if path.suffix.lower() in (".yaml", ".yml"):
            import yaml  # type: ignore

            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return json.loads(path.read_text(encoding="utf-8"))


def _resolve_modes(cfg: Dict[str, Any], profile: str, processing_mode: str, csv_mode: str) -> Tuple[str, str, List[str], List[str]]:
    pm = processing_mode
    cm = csv_mode
    plotting = []
    aggregate_modes = []

    if profile:
        profiles = cfg.get("profiles", {}) or {}
        if profile not in profiles:
            raise ValueError("Unknown profile: %s" % profile)
        prof = profiles.get(profile) or {}
        pm = pm or prof.get("processing_mode")
        cm = cm or prof.get("csv_mode")
        plotting = prof.get("plotting_modes") or []
        aggregate_modes = prof.get("aggregate_modes") or []

    if not pm or not cm:
        raise ValueError("processing_mode and csv_mode are required (supply profile or explicit job fields).")

    return pm, cm, plotting, aggregate_modes


def _run(cmd: List[str], dry_run: bool) -> int:
    print(" ".join(cmd))
    if dry_run:
        return 0
    return subprocess.run(cmd).returncode


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run a config-defined job end-to-end.")
    ap.add_argument("--config", required=True, help="Path to config YAML.")
    ap.add_argument("--job", required=True, help="Job name under jobs.")
    ap.add_argument("--input-root", default="", help="Override jobs.<name>.input_root.")
    ap.add_argument("--output-root", default="", help="Override jobs.<name>.output_root.")
    ap.add_argument("--run-name", default="", help="Override jobs.<name>.run_name_template (exact folder name).")
    ap.add_argument("--profile", default="", help="Override jobs.<name>.profile.")
    ap.add_argument("--processing-mode", default="", help="Override jobs.<name>.processing_mode.")
    ap.add_argument("--csv-mode", default="", help="Override jobs.<name>.csv_mode.")
    ap.add_argument("--pattern", default="", help="Override jobs.<name>.pattern.")
    ap.add_argument("--plotting-modes", default="", help="Comma-separated plotting modes (override).")
    ap.add_argument("--aggregate-modes", default="", help="Comma-separated aggregate modes (override).")
    ap.add_argument("--collect-job", default="", help="Override jobs.<name>.collect.job.")
    ap.add_argument("--collect-out-root", default="", help="Override jobs.<name>.collect.out_root.")
    ap.add_argument("--no-collect", action="store_true", help="Disable collect step even if enabled in job.")
    ap.add_argument("--dry-run", action="store_true", help="Print commands only.")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    cfg_path = Path(args.config)
    cfg = _load_config(cfg_path)

    jobs = cfg.get("jobs") or {}
    if not isinstance(jobs, dict) or args.job not in jobs:
        raise ValueError("Unknown job '%s' (define under jobs in config)." % args.job)
    job = dict(jobs.get(args.job) or {})
    if not isinstance(job, dict):
        raise ValueError("jobs.%s must be a dict" % args.job)

    if args.input_root:
        job["input_root"] = args.input_root
    if args.output_root:
        job["output_root"] = args.output_root
    if args.run_name:
        job["run_name_template"] = args.run_name
    if args.profile:
        job["profile"] = args.profile
    if args.processing_mode:
        job["processing_mode"] = args.processing_mode
    if args.csv_mode:
        job["csv_mode"] = args.csv_mode
    if args.pattern:
        job["pattern"] = args.pattern
    if args.plotting_modes:
        job["plotting_modes"] = [m.strip() for m in args.plotting_modes.split(",") if m.strip()]
    if args.aggregate_modes:
        job["aggregate_modes"] = [m.strip() for m in args.aggregate_modes.split(",") if m.strip()]
    if args.collect_job or args.collect_out_root or args.no_collect:
        collect_cfg = dict(job.get("collect") or {})
        if args.collect_job:
            collect_cfg["job"] = args.collect_job
        if args.collect_out_root:
            collect_cfg["out_root"] = args.collect_out_root
        if args.no_collect:
            collect_cfg["enable"] = False
        job["collect"] = collect_cfg

    input_root = str(job.get("input_root") or "").strip()
    if not input_root:
        raise ValueError("jobs.%s.input_root is required" % args.job)

    out_root = str(job.get("output_root") or "out/jobs").strip()
    run_name_tpl = str(job.get("run_name_template") or "{job}_{timestamp}")
    stamp = _now_stamp()
    run_name = run_name_tpl.replace("{job}", args.job).replace("{timestamp}", stamp)
    out_dir = Path(out_root) / run_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Optional collect step
    collect_cfg = job.get("collect") or {}
    if isinstance(collect_cfg, dict) and collect_cfg.get("enable"):
        collect_job = collect_cfg.get("job")
        if not collect_job:
            raise ValueError("jobs.%s.collect.job is required when collect.enable is true" % args.job)
        collect_out_root = collect_cfg.get("out_root") or str(out_dir / "collect")
        collect_cmd = [
            sys.executable,
            "scripts/collect_files.py",
            "--config",
            str(cfg_path),
            "--job",
            str(collect_job),
            "--input-root",
            input_root,
            "--out-root",
            str(collect_out_root),
        ]
        if _run(collect_cmd, args.dry_run) != 0:
            raise RuntimeError("collect_files failed")
        if args.dry_run:
            print("Dry-run: stopping after collect step.")
            return 0
        # Find latest metadata to discover copied_root.
        collect_root = Path(collect_out_root)
        metas = sorted(collect_root.rglob("run_metadata.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not metas:
            raise RuntimeError("collect job ran but no run_metadata.json found under %s" % collect_root)
        meta = json.loads(metas[0].read_text(encoding="utf-8"))
        copied_root = meta.get("copied_root")
        if not copied_root:
            raise RuntimeError("collect job metadata missing copied_root: %s" % metas[0])
        input_root = str(Path(copied_root).resolve())

    profile = str(job.get("profile") or "")
    processing_mode = str(job.get("processing_mode") or "")
    csv_mode = str(job.get("csv_mode") or "")
    plotting_modes = job.get("plotting_modes")
    aggregate_modes = job.get("aggregate_modes")

    pm, cm, plotting_from_profile, agg_from_profile = _resolve_modes(cfg, profile, processing_mode, csv_mode)
    if plotting_modes is None:
        plotting_modes = plotting_from_profile
    if aggregate_modes is None:
        aggregate_modes = agg_from_profile

    pattern = str(job.get("pattern") or "*.tif;*.tiff")
    py2_exe = str(job.get("py2_exe") or os.environ.get("PYTHON2_EXE") or "C:\\Python27\\python.exe")

    manifest_path = out_dir / "job_manifest.json"
    summary_csv = out_dir / "summary.csv"
    plots_dir = out_dir / "plots"
    aggregates_dir = out_dir / "aggregates"
    plots_dir.mkdir(parents=True, exist_ok=True)
    aggregates_dir.mkdir(parents=True, exist_ok=True)

    # Manifest
    manifest_cmd = [
        sys.executable,
        "scripts/make_job_manifest.py",
        "--config",
        str(cfg_path),
        "--input-root",
        str(Path(input_root).resolve()),
        "--output-dir",
        str(out_dir.resolve()),
        "--processing-mode",
        pm,
        "--csv-mode",
        cm,
        "--out",
        str(manifest_path),
        "--pattern",
        pattern,
    ]
    if profile:
        manifest_cmd.extend(["--profile", profile])
    if _run(manifest_cmd, args.dry_run) != 0:
        raise RuntimeError("manifest generation failed")

    # pygwy processing (Py2)
    run_cmd = [
        py2_exe,
        "scripts/run_pygwy_job.py",
        "--manifest",
        str(manifest_path),
    ]
    if _run(run_cmd, args.dry_run) != 0:
        raise RuntimeError("pygwy processing failed")

    # Plotting
    if plotting_modes:
        for mode in plotting_modes:
            plot_cmd = [
                sys.executable,
                "scripts/cli_plot.py",
                "--config",
                str(cfg_path),
                "--csv",
                str(summary_csv),
                "--plotting-mode",
                str(mode),
                "--out",
                str(plots_dir),
            ]
            if _run(plot_cmd, args.dry_run) != 0:
                raise RuntimeError("plotting failed for mode %s" % mode)

    # Aggregation
    if aggregate_modes:
        agg_cmd = [
            sys.executable,
            "scripts/cli_aggregate_config.py",
            "--config",
            str(cfg_path),
            "--csv",
            str(summary_csv),
            "--aggregate-modes",
            ",".join(aggregate_modes),
            "--out-dir",
            str(aggregates_dir),
        ]
        if _run(agg_cmd, args.dry_run) != 0:
            raise RuntimeError("aggregation failed")

    print("Done. Output dir: %s" % out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
