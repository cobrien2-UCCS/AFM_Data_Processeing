#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Py2.7/pygwy runner that consumes a JSON manifest and writes a summary CSV.

Notes:
- Py2-only stdlib (json/argparse/os). Avoid Py3 constructs.
- Requires pygwy; no fallback will run to avoid producing invalid data.
- Philosophy: use Gwyddion/pygwy modules for core processing (leveling, filtering,
  grain ops). Use Python-side math only for small supplemental steps (e.g., clipping,
  unit conversions) when Gwyddion lacks a direct function.
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
        sys.stderr.write("ERROR: pygwy (gwy module) not importable; ensure 32-bit Gwyddion/pygwy is installed.\n")
        return False


def try_import_numpy():
    try:
        import numpy  # noqa: F401
        return True
    except ImportError:
        sys.stderr.write("ERROR: numpy missing in pygwy environment.\n")
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


def _get_field_units(field):
    """Best-effort retrieval of z-units from the DataField."""
    try:
        unit_obj = field.get_si_unit_z()
        if unit_obj:
            u = unit_obj.get_unit_string()
            if u:
                return u
    except Exception:
        return None
    return None


def _connected_components(mask):
    """Deprecated: no longer used; particle counting relies on pygwy grain stats."""
    return []


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

    channel_family = None
    if mode_def:
        channel_family = mode_def.get("channel_family")
    if channel_family:
        for key, field in data_dir.items():
            name = getattr(field, "get_title", lambda: "")()
            if name and channel_family.lower() in name.lower():
                return key, field

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
    if result is None:
        return None

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
    - particle_count_basic
    - raw_noop
    """
    try:
        import gwy  # type: ignore
    except ImportError:
        raise RuntimeError("pygwy (gwy module) not available.")

    container = gwy.gwy_file_load(path)
    if container is None:
        raise RuntimeError("Failed to load file with pygwy: %s" % path)

    field_id, field = _select_data_field(container, mode_def, channel_defaults)
    mode = processing_mode or "raw_noop"

    if mode in ("modulus_basic", "topography_flat"):
        f = field.duplicate()
        if mode_def.get("plane_level", True):
            try:
                # Prefer Gwyddion's plane-level module if available
                gwy.gwy_process_func_run("level", {"data": f, "method": 0})
            except Exception:
                try:
                    gwy.gwy_process_func_run("plane-level", {"data": f})
                except Exception as exc:
                    sys.stderr.write("WARN: plane_level failed for %s: %s\n" % (path, exc))
        median_size = mode_def.get("median_size")
        if median_size:
            try:
                gwy.gwy_process_func_run("median", {"data": f, "size": int(median_size)})
            except Exception as exc:
                sys.stderr.write("WARN: median filter failed for %s: %s\n" % (path, exc))
        if mode_def.get("line_level_x"):
            try:
                gwy.gwy_process_func_run("level-line", {"data": f, "direction": 0})
            except Exception as exc:
                sys.stderr.write("WARN: line_level_x failed for %s: %s\n" % (path, exc))
        if mode_def.get("line_level_y"):
            try:
                gwy.gwy_process_func_run("level-line", {"data": f, "direction": 1})
            except Exception as exc:
                sys.stderr.write("WARN: line_level_y failed for %s: %s\n" % (path, exc))
        # Python-side clipping is optional and used only when Gwyddion lacks a direct op.
        clip = mode_def.get("clip_percentiles")
        if clip and isinstance(clip, (list, tuple)) and len(clip) == 2:
            try:
                import numpy as np  # type: ignore
                arr = _field_to_numpy(f)
                low, high = float(clip[0]), float(clip[1])
                lo_val, hi_val = np.percentile(arr, [low, high])
                arr = np.clip(arr, lo_val, hi_val)
                f.set_data(arr.ravel().tolist())
            except Exception as exc:
                sys.stderr.write("WARN: clip_percentiles failed for %s: %s\n" % (path, exc))
        detected_unit = _get_field_units(f)
        result = _to_mode_result(f, mode_def, mode, path)
        return _apply_units(result, processing_mode, mode_def, manifest, detected_unit)

    if mode == "particle_count_basic":
        f = field.duplicate()
        try:
            import numpy as np  # type: ignore
        except ImportError:
            raise RuntimeError("numpy required for particle_count_basic.")

        arr = _field_to_numpy(f)

        thresh = mode_def.get("threshold")
        if thresh is None:
            thresh = float(np.mean(arr))

        grains_result = None
        try:
            mask_field = f.duplicate()
            mask_data = mask_field.get_data()
            for i in range(len(mask_data)):
                mask_data[i] = 1.0 if mask_data[i] > thresh else 0.0
            grains = mask_field.number_grains()
            sizes = mask_field.get_grain_sizes(grains)
            sizes_list = list(sizes)[1:] if len(sizes) > 0 else []
            count_total = len(sizes_list)
            # Prefer physical area for density if available
            try:
                area_real = float(f.get_xreal() * f.get_yreal())
            except Exception:
                area_real = 0.0
            pixel_area = float(f.get_xres() * f.get_yres()) if f.get_xres() and f.get_yres() else 0.0
            denom = area_real if area_real > 0 else pixel_area
            count_density = float(count_total) / denom if denom else 0.0
            sizes_arr = np.asarray(sizes_list, dtype=float)
            if sizes_arr.size:
                equiv_diam = 2.0 * np.sqrt(sizes_arr / np.pi)
                mean_diam = float(np.mean(equiv_diam))
                std_diam = float(np.std(equiv_diam))
            else:
                mean_diam = 0.0
                std_diam = 0.0
            mean_circ = None
            std_circ = None
            try:
                import gwy  # type: ignore
                circ_vals = f.grains_get_values(grains, gwy.GrainQuantity.CIRCULARITY)
                circ_list = list(circ_vals)[1:] if len(circ_vals) > 0 else []
                if circ_list:
                    circ_arr = np.asarray(circ_list, dtype=float)
                    mean_circ = float(np.mean(circ_arr))
                    std_circ = float(np.std(circ_arr))
            except Exception:
                pass
            grains_result = {
                "particle.count_total": int(count_total),
                "particle.count_density": float(count_density),
                "particle.mean_diameter_px": float(mean_diam),
                "particle.std_diameter_px": float(std_diam),
            }
            if mean_circ is not None:
                grains_result["particle.mean_circularity"] = float(mean_circ)
            if std_circ is not None:
                grains_result["particle.std_circularity"] = float(std_circ)
        except Exception as exc:
            sys.stderr.write("WARN: pygwy grain ops failed for %s: %s; skipping row.\n" % (path, exc))
            return None

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
        return _apply_units(result, processing_mode, mode_def, manifest, "count")

    if mode == "raw_noop":
        processed_field = field.duplicate()
        detected_unit = _get_field_units(processed_field)
        result = _to_mode_result(processed_field, mode_def, mode, path)
        return _apply_units(result, processing_mode, mode_def, manifest, detected_unit)

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


def _apply_units(result, processing_mode, mode_def, manifest, detected_unit):
    """Apply unit detection, conversion, and mismatch policy."""
    current_unit = detected_unit or result.get("core.units") or mode_def.get("units")
    conversions = (manifest.get("unit_conversions") or {}).get(processing_mode, {})
    if current_unit in conversions:
        conv = conversions.get(current_unit) or {}
        try:
            factor = float(conv.get("factor", 1.0))
        except Exception:
            factor = 1.0
        target_unit = conv.get("target", current_unit)
        try:
            result["core.avg_value"] = float(result.get("core.avg_value", 0.0)) * factor
            result["core.std_value"] = float(abs(factor)) * float(result.get("core.std_value", 0.0))
            current_unit = target_unit
        except Exception as exc:
            sys.stderr.write("WARN: unit conversion failed (%s): %s\n" % (current_unit, exc))

    expected = mode_def.get("expected_units")
    policy = mode_def.get("on_unit_mismatch", "error")
    if expected and current_unit != expected:
        msg = "Unit mismatch for %s: detected '%s', expected '%s'\n" % (processing_mode, current_unit, expected)
        if policy == "skip_row":
            sys.stderr.write("WARN: %s; skipping row.\n" % msg.strip())
            return None
        if policy == "warn":
            sys.stderr.write("WARN: %s; continuing.\n" % msg.strip())
        else:
            raise RuntimeError(msg)

    result["core.units"] = current_unit or result.get("core.units")
    return result


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
    if not use_pygwy:
        raise RuntimeError(
            "pygwy not available in this interpreter. Install 32-bit Gwyddion/pygwy "
            "and rerun. No fallback will be used to avoid producing invalid data."
        )
    rows = []
    for path in files:
        try:
            mode_result = process_file(path, manifest, use_pygwy)
            if mode_result is None:
                sys.stderr.write("INFO: Skipped %s due to unit mismatch policy.\n" % path)
                continue
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
