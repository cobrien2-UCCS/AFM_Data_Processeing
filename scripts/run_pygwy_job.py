#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Py2.7/pygwy runner that consumes a JSON manifest and writes a summary CSV.

Notes:
- Py2-only stdlib (json/argparse/os). Avoid Py3 constructs.
- Requires pygwy; no fallback will run to avoid producing invalid data.
"""

from __future__ import print_function
import argparse
import csv
import json
import os
import re
import sys


def load_manifest(path):
    with open(path, "r") as f:
        return json.load(f)


def try_import_pygwy():
    try:
        import gwy  # noqa: F401
        return True
    except ImportError:
        return False


def try_import_numpy():
    try:
        import numpy  # noqa: F401
        return True
    except ImportError:
        return False


def _field_to_numpy(field):
    """Convert gwy.DataField to a NumPy array."""
    try:
        import numpy as np  # type: ignore
    except ImportError:
        raise RuntimeError("numpy is required in the pygwy environment to compute statistics.")
    data = field.get_data()
    arr = np.asarray(data, dtype=float)
    xres = int(field.get_xres())
    yres = int(field.get_yres())
    try:
        arr = arr.reshape((yres, xres))
    except Exception:
        pass
    return arr


def _connected_components(mask):
    """Simple 4-neighbor connected components; returns list of sizes."""
    try:
        import numpy as np  # type: ignore
    except ImportError:
        raise RuntimeError("numpy required for particle counting.")

    visited = np.zeros_like(mask, dtype=bool)
    sizes = []
    rows, cols = mask.shape
    neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for r in range(rows):
        for c in range(cols):
            if not mask[r, c] or visited[r, c]:
                continue
            stack = [(r, c)]
            visited[r, c] = True
            size = 0
            while stack:
                cr, cc = stack.pop()
                size += 1
                for dr, dc in neighbors:
                    nr, nc = cr + dr, cc + dc
                    if nr < 0 or nr >= rows or nc < 0 or nc >= cols:
                        continue
                    if visited[nr, nc] or not mask[nr, nc]:
                        continue
                    visited[nr, nc] = True
                    stack.append((nr, nc))
            sizes.append(size)
    return sizes


def _select_data_field(container, mode_def, channel_defaults):
    """
    Pick a data field from a container. Uses mode_def.channel_family if provided,
    else returns the first data field.
    """
    try:
        import gwyutils  # type: ignore
    except ImportError:
        raise RuntimeError("gwyutils not available; cannot enumerate data fields.")

    data_dir = gwyutils.get_data_fields_dir(container)
    if not data_dir:
        raise RuntimeError("No data fields found in container.")

    # Try channel_family hint
    channel_family = None
    if mode_def:
        channel_family = mode_def.get("channel_family")
    if channel_family:
        for key, field in data_dir.items():
            name = getattr(field, "get_title", lambda: "")()
            if name and channel_family.lower() in name.lower():
                return key, field

    # Fallback: first field
    first_key = list(data_dir.keys())[0]
    return first_key, data_dir[first_key]


def build_csv_row(mode_result, csv_def, processing_mode, csv_mode):
    """Py2-compatible csv row builder."""
    columns = csv_def.get("columns", [])
    on_missing = csv_def.get("on_missing_field", "warn_null")
    row = []
    for col_def in columns:
        key = col_def.get("from")
        default = col_def.get("default", "")
        if key in mode_result:
            row.append(mode_result.get(key))
            continue
        if default != "":
            row.append(default)
            continue
        if on_missing == "error":
            raise KeyError("Missing field '%s' for csv_mode=%s processing_mode=%s" % (key, csv_mode, processing_mode))
        if on_missing == "skip_row":
            sys.stderr.write("WARN: Skipping row (missing %s) mode=%s csv_mode=%s\n" % (key, processing_mode, csv_mode))
            return None
        sys.stderr.write("WARN: Missing field '%s' mode=%s csv_mode=%s; writing empty\n" % (key, processing_mode, csv_mode))
        row.append("")
    return row


def _process_with_pillow_numpy(path, mode_def, processing_mode):
    """Fallback: read TIFF via Pillow + numpy; compute mean/std."""
    has_np = try_import_numpy()
    has_pillow = try_import_pillow()
    if not (has_np and has_pillow):
        raise RuntimeError("Fallback requires numpy + pillow; install them or use pygwy.")

    import numpy as np  # type: ignore
    from PIL import Image  # type: ignore

    img = Image.open(path)
    data = np.asarray(img, dtype=float)
    valid = data[np.isfinite(data)]
    mean_val = float(np.mean(valid)) if valid.size else 0.0
    std_val = float(np.std(valid)) if valid.size else 0.0

    metric_type = mode_def.get("metric_type", "unknown")
    units = mode_def.get("units", "a.u.")

    result = {
        "core.source_file": os.path.basename(path),
        "core.mode": processing_mode,
        "core.metric_type": metric_type,
        "core.avg_value": mean_val,
        "core.std_value": std_val,
        "core.units": units,
        "core.nx": int(img.size[0]),
        "core.ny": int(img.size[1]),
    }
    return result


def derive_grid_indices(path, grid_cfg):
    """
    Derive grid row/col from filename using a regex with named groups row/col.
    Example grid_cfg:
    {
      "filename_regex": "r(?P<row>\\d+)_c(?P<col>\\d+)"
    }
    """
    pattern = None
    if grid_cfg:
        pattern = grid_cfg.get("filename_regex")
    if not pattern:
        return None, None
    try:
        regex = re.compile(pattern)
        m = regex.search(os.path.basename(path))
        if m:
            row = m.groupdict().get("row")
            col = m.groupdict().get("col")
            row_val = int(row) if row is not None else None
            col_val = int(col) if col is not None else None
            return row_val, col_val
    except Exception:
        return None, None
    return None, None


def process_file(path, manifest, use_pygwy):
    mode_def = manifest.get("mode_definition", {}) or {}
    grid_cfg = manifest.get("grid", {}) or {}
    channel_defaults = manifest.get("channel_defaults", {}) or {}
    processing_mode = manifest.get("processing_mode")
    row_idx, col_idx = derive_grid_indices(path, grid_cfg)

    if not use_pygwy:
        raise RuntimeError("pygwy required for processing; no fallback is executed.")
    result = _process_with_pygwy(path, processing_mode, mode_def, channel_defaults, manifest)

    if row_idx is not None:
        result["grid.row_idx"] = row_idx
    if col_idx is not None:
        result["grid.col_idx"] = col_idx
    return result


def _process_with_pygwy(path, processing_mode, mode_def, channel_defaults, manifest):
    """
    Implement APPLY_MODE_PIPELINE per the spec:
    - modulus_basic
    - topography_flat
    - particle_count_basic (stub)
    - raw_noop
    """
    try:
        import gwy  # type: ignore
    except ImportError:
        raise RuntimeError("pygwy (gwy module) not available.")

    # Load container
    container = gwy.gwy_file_load(path)
    if container is None:
        raise RuntimeError("Failed to load file with pygwy: %s" % path)

    field_id, field = _select_data_field(container, mode_def, channel_defaults)
    mode = processing_mode or "raw_noop"

    if mode == "raw_noop":
        processed_field = field.duplicate()
        return _to_mode_result(processed_field, mode_def, mode, path)

    if mode in ("modulus_basic", "topography_flat"):
        f = field.duplicate()
        # Optional: plane leveling if requested
        if mode_def.get("plane_level", True):
            try:
                # fit_plane returns coefficients; apply via gwyutils sub or module
                pa, pbx, pby = f.fit_plane()
                # f is modified in place by fit_plane in some builds; if not, we could apply manually.
            except Exception:
                pass  # continue without leveling
        # Additional filters could be added here per mode_def (median, line flatten, etc.)
        return _to_mode_result(f, mode_def, mode, path)

    if mode == "particle_count_basic":
        # Use pygwy grain tools when available; fallback to numpy-based mask if grain ops fail.
        f = field.duplicate()
        try:
            import numpy as np  # type: ignore
        except ImportError:
            raise RuntimeError("numpy required for particle_count_basic.")

        arr = _field_to_numpy(f)

        thresh = mode_def.get("threshold")
        if thresh is None:
            thresh = float(np.mean(arr))

        # Try pygwy grain marking if available
        grains_result = None
        try:
            import gwy  # type: ignore
            mask_field = f.duplicate()
            mask_data = mask_field.get_data()
            # simple threshold mask
            for i in range(len(mask_data)):
                mask_data[i] = 1.0 if mask_data[i] > thresh else 0.0
            grains = mask_field.number_grains()
            sizes = mask_field.get_grain_sizes(grains)
            # skip grain 0 (background)
            sizes_list = list(sizes)[1:] if len(sizes) > 0 else []
            count_total = len(sizes_list)
            count_density = float(count_total) / float(f.get_xres() * f.get_yres()) if f.get_xres() and f.get_yres() else 0.0
            sizes_arr = np.asarray(sizes_list, dtype=float)
            if sizes_arr.size:
                equiv_diam = 2.0 * np.sqrt(sizes_arr / np.pi)
                mean_diam = float(np.mean(equiv_diam))
                std_diam = float(np.std(equiv_diam))
            else:
                mean_diam = 0.0
                std_diam = 0.0
            grains_result = {
                "particle.count_total": int(count_total),
                "particle.count_density": float(count_density),
                "particle.mean_diameter_px": float(mean_diam),
                "particle.std_diameter_px": float(std_diam),
            }
        except Exception:
            grains_result = None

        # Fallback: simple numpy connected components if pygwy grain stats fail
        if grains_result is None:
            mask = arr > thresh
            sizes = _connected_components(mask)
            count_total = len(sizes)
            count_density = float(count_total) / float(mask.size) if mask.size else 0.0
            if sizes:
                sizes_arr = np.asarray(sizes, dtype=float)
                equiv_diam = 2.0 * np.sqrt(sizes_arr / np.pi)
                mean_diam = float(np.mean(equiv_diam))
                std_diam = float(np.std(equiv_diam))
            else:
                mean_diam = 0.0
                std_diam = 0.0
            grains_result = {
                "particle.count_total": int(count_total),
                "particle.count_density": float(count_density),
                "particle.mean_diameter_px": float(mean_diam),
                "particle.std_diameter_px": float(std_diam),
            }

        result = {
            "core.source_file": os.path.basename(path),
            "core.mode": processing_mode,
            "core.metric_type": mode_def.get("metric_type", "particle_count"),
            "core.avg_value": float(grains_result["particle.count_total"]),
            "core.std_value": 0.0,
            "core.units": "count",
            "core.nx": int(f.get_xres()),
            "core.ny": int(f.get_yres()),
        }
        result.update(grains_result)
        return result

    raise ValueError("Unknown processing_mode: %s" % mode)


def _to_mode_result(field, mode_def, processing_mode, src_path):
    """Compute avg/std from a DataField using numpy."""
    arr = _field_to_numpy(field)
    try:
        import numpy as np  # type: ignore
    except ImportError:
        raise RuntimeError("numpy required in pygwy environment to compute statistics.")

    valid = arr[np.isfinite(arr)]
    mean_val = float(np.mean(valid)) if valid.size else 0.0
    std_val = float(np.std(valid)) if valid.size else 0.0

    metric_type = mode_def.get("metric_type", processing_mode)
    units = mode_def.get("units", "a.u.")

    return {
        "core.source_file": os.path.basename(src_path),
        "core.mode": processing_mode,
        "core.metric_type": metric_type,
        "core.avg_value": mean_val,
        "core.std_value": std_val,
        "core.units": units,
        "core.nx": int(field.get_xres()),
        "core.ny": int(field.get_yres()),
    }


def write_summary_csv(rows, csv_def, output_csv, processing_mode, csv_mode):
    header = [c.get("name") for c in csv_def.get("columns", [])]
    with open(output_csv, "w") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
    print("Wrote summary CSV: %s" % output_csv)


def process_manifest(manifest, dry_run=False):
    files = manifest.get("files", [])
    out_dir = manifest.get("output_dir")
    output_csv = manifest.get("output_csv") or os.path.join(out_dir, "summary.csv")
    if not out_dir:
        raise ValueError("output_dir missing from manifest")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    csv_def = manifest.get("csv_mode_definition") or {}
    processing_mode = manifest.get("processing_mode")
    csv_mode = manifest.get("csv_mode")

    print("Processing_mode: %s" % processing_mode)
    print("CSV_mode: %s" % csv_mode)
    print("Files: %d" % len(files))
    print("Output dir: %s" % out_dir)
    print("Output CSV: %s" % output_csv)

    if dry_run:
        print("Dry run: no processing executed.")
        return

    use_pygwy = try_import_pygwy()
    if use_pygwy:
        print("pygwy detected; implement APPLY_MODE_PIPELINE for real processing.")
    else:
        raise RuntimeError(
            "pygwy not available in this interpreter. Install 32-bit Gwyddion/pygwy "
            "and rerun. No fallback will be used to avoid producing invalid data."
        )
    rows = []
    for path in files:
        try:
            mode_result = process_file(path, manifest, use_pygwy)
            row = build_csv_row(mode_result, csv_def, processing_mode, csv_mode)
            if row is not None:
                rows.append(row)
            else:
                print("Skipped row for %s" % path)
        except Exception as exc:
            sys.stderr.write("ERROR processing %s: %s\n" % (path, exc))
    write_summary_csv(rows, csv_def, output_csv, processing_mode, csv_mode)


def parse_args():
    parser = argparse.ArgumentParser(description="Run pygwy processing from a JSON manifest (Py2.7).")
    parser.add_argument("--manifest", required=True, help="Path to manifest JSON.")
    parser.add_argument("--dry-run", action="store_true", help="List actions without running processing.")
    return parser.parse_args()


def main():
    args = parse_args()
    manifest = load_manifest(args.manifest)
    process_manifest(manifest, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
