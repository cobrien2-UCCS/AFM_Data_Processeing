#!/usr/bin/env python3
"""
Generate a JSON job manifest for the pygwy (Python 2.7) processing step.

Workflow:
- Author/edit the YAML config in Python 3.x.
- Run this script in Python 3.x to emit a JSON manifest containing only the
  needed slices of config plus the TIFF file list.
- The Python 2.7 pygwy runner consumes the manifest and writes outputs.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Any

import yaml


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_modes(cfg: Dict[str, Any], profile: str, processing_mode: str, csv_mode: str) -> Dict[str, str]:
    """Resolve processing/csv modes using an optional profile with explicit overrides."""
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

    if "modes" not in cfg or chosen_processing not in cfg.get("modes", {}):
        raise ValueError("processing_mode '%s' not found in config.modes." % chosen_processing)
    if "csv_modes" not in cfg or chosen_csv not in cfg.get("csv_modes", {}):
        raise ValueError("csv_mode '%s' not found in config.csv_modes." % chosen_csv)

    return {"processing_mode": chosen_processing, "csv_mode": chosen_csv}


def collect_files(input_root: Path, pattern: str) -> Dict[str, Any]:
    patterns = [pat.strip() for pat in pattern.split(";") if pat.strip()]
    recursive = False
    if any(p.startswith("**/") for p in patterns):
        recursive = True
    base_patterns = []
    for p in patterns:
        base_patterns.append(p[3:] if p.startswith("**/") else p)
    if not patterns:
        patterns = [pattern]
    files = []
    for pat in base_patterns:
        if recursive:
            files.extend(str(p.resolve()) for p in input_root.rglob(pat) if p.is_file())
        else:
            files.extend(str(p.resolve()) for p in input_root.glob(pat) if p.is_file())
    files = sorted(set(files))
    return {"files": files, "input_root": str(input_root.resolve()), "pattern": pattern}


def build_manifest(cfg: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    mode_sel = resolve_modes(cfg, args.profile, args.processing_mode, args.csv_mode)
    files_info = collect_files(Path(args.input_root), args.pattern)

    output_csv = args.output_csv
    if not output_csv:
        output_csv = str(Path(args.output_dir).resolve() / "summary.csv")

    manifest = {
        "manifest_version": "1.0",
        "processing_mode": mode_sel["processing_mode"],
        "csv_mode": mode_sel["csv_mode"],
        "input_root": files_info["input_root"],
        "pattern": files_info["pattern"],
        "files": files_info["files"],
        "output_dir": str(Path(args.output_dir).resolve()),
        "output_csv": output_csv,
        # Minimal slices of config needed downstream.
        "grid": cfg.get("grid", {}),
        "channel_defaults": cfg.get("channel_defaults", {}),
        "mode_definition": cfg.get("modes", {}).get(mode_sel["processing_mode"], {}),
        "csv_mode_definition": cfg.get("csv_modes", {}).get(mode_sel["csv_mode"], {}),
        "unit_conversions": cfg.get("unit_conversions", {}),
    }
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a JSON manifest for the pygwy (Py2.7) runner.")
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    parser.add_argument("--input-root", required=True, help="Directory containing TIFF files.")
    parser.add_argument("--output-dir", required=True, help="Directory where the pygwy runner will write outputs.")
    parser.add_argument("--out", required=True, help="Path to write the manifest JSON.")
    parser.add_argument("--profile", help="Optional profile name from config.")
    parser.add_argument("--processing-mode", help="Processing mode (overrides profile).")
    parser.add_argument("--csv-mode", help="CSV mode (overrides profile).")
    parser.add_argument("--output-csv", help="Override output CSV path (default: <output_dir>/summary.csv).")
    parser.add_argument("--pattern", default="*.tif;*.tiff", help="Glob pattern(s) for TIFF files, ';' separated (default: *.tif;*.tiff).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(Path(args.config))
    manifest = build_manifest(cfg, args)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("Wrote manifest to %s with %d files" % (out_path, len(manifest.get("files", []))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
