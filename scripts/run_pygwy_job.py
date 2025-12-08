#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Py2.7/pygwy runner stub that consumes a JSON manifest and performs processing.

This is intentionally minimal and Py2-compatible:
- Uses only stdlib json/argparse/os.
- Expects pygwy (`gwy` module) to be importable in this interpreter.
- Reads a manifest produced by scripts/make_job_manifest.py.

TODO: Implement actual pygwy processing per the spec's APPLY_MODE_PIPELINE.
"""

from __future__ import print_function
import argparse
import json
import os
import sys


def load_manifest(path):
    with open(path, "r") as f:
        return json.load(f)


def ensure_pygwy():
    try:
        import gwy  # noqa: F401
    except ImportError as exc:
        sys.stderr.write("ERROR: pygwy (gwy module) not available in this interpreter: %s\n" % exc)
        return False
    return True


def process_manifest(manifest, dry_run=False):
    files = manifest.get("files", [])
    out_dir = manifest.get("output_dir")
    if not out_dir:
        raise ValueError("output_dir missing from manifest")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    print("Manifest processing_mode: %s" % manifest.get("processing_mode"))
    print("Manifest csv_mode: %s" % manifest.get("csv_mode"))
    print("Input files: %d" % len(files))
    print("Output dir: %s" % out_dir)

    if dry_run:
        print("Dry run: no processing executed.")
        return

    # TODO: integrate pygwy processing here using manifest["mode_definition"] etc.
    for path in files:
        print("Would process: %s" % path)
    print("Processing stub complete (implement pygwy logic per spec).")


def parse_args():
    parser = argparse.ArgumentParser(description="Run pygwy processing from a JSON manifest (Py2.7).")
    parser.add_argument("--manifest", required=True, help="Path to manifest JSON.")
    parser.add_argument("--dry-run", action="store_true", help="List actions without running pygwy.")
    return parser.parse_args()


def main():
    args = parse_args()
    manifest = load_manifest(args.manifest)
    if not ensure_pygwy():
        return 1
    process_manifest(manifest, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
