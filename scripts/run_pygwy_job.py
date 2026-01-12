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
import math
import os
import re
import sys

_GRID_REGEX_MISS_WARNED = set()
_GRID_INDEX_BASE_WARNED = False
_STATS_WARNED = False


def _is_finite(x):
    try:
        return (x == x) and (x != float("inf")) and (x != float("-inf"))
    except Exception:
        return True


def _field_stats_filtered(field, filter_cfg):
    """
    Compute mean/std/min/max on a DataField with optional value filtering.

    This is a Python-side supplement intended for explicit, config-driven masking
    when Gwyddion does not provide the exact filtering needed for robust summary
    stats (e.g., excluding invalid/saturated pixels).
    """
    data = field.get_data()
    n = len(data)
    if not n:
        return 0.0, 0.0, 0.0, 0.0, 0

    min_value = filter_cfg.get("min_value") if filter_cfg else None
    max_value = filter_cfg.get("max_value") if filter_cfg else None
    max_abs_value = filter_cfg.get("max_abs_value") if filter_cfg else None
    exclude_zero = bool(filter_cfg.get("exclude_zero")) if filter_cfg else False
    exclude_nonpositive = bool(filter_cfg.get("exclude_nonpositive")) if filter_cfg else False

    try:
        min_value = float(min_value) if min_value is not None else None
    except Exception:
        min_value = None
    try:
        max_value = float(max_value) if max_value is not None else None
    except Exception:
        max_value = None
    try:
        max_abs_value = float(max_abs_value) if max_abs_value is not None else None
    except Exception:
        max_abs_value = None

    vals = []
    for i in range(n):
        v = float(data[i])
        if not _is_finite(v):
            continue
        if exclude_zero and v == 0.0:
            continue
        if exclude_nonpositive and v <= 0.0:
            continue
        if min_value is not None and v < min_value:
            continue
        if max_value is not None and v > max_value:
            continue
        if max_abs_value is not None and abs(v) > max_abs_value:
            continue
        vals.append(v)

    if not vals:
        return 0.0, 0.0, 0.0, 0.0, 0

    m = float(_mean(vals))
    s = float(_std(vals))
    vmin = min(vals)
    vmax = max(vals)
    return m, s, float(vmin), float(vmax), int(len(vals))


def _parse_filename_basic_metadata(path):
    """
    Best-effort filename parsing for common SmartScan exports.

    This stays intentionally lightweight and does not attempt to fully implement
    the spec's full parsing template. It exists mainly to:
    - surface Forward/Backward duplicates in the CSV
    - provide simple grouping keys (channel, date_code, grid_id)
    """
    base = os.path.basename(path)
    out = {}

    # e.g. "...-Modulus_Backward-251021-CRO.tiff"
    m = re.search(r"-(?P<channel>[^-]+?)_(?P<direction>Forward|Backward)-", base)
    if m:
        out["file.channel"] = m.group("channel")
        out["file.direction"] = m.group("direction")
    else:
        m = re.search(r"(?P<direction>Forward|Backward)", base)
        if m:
            out["file.direction"] = m.group("direction")

    m = re.search(r"_GrID(?P<grid_id>\d{3,})", base)
    if m:
        try:
            out["file.grid_id"] = int(m.group("grid_id"))
        except Exception:
            out["file.grid_id"] = m.group("grid_id")

    m = re.search(r"-(?P<date_code>\d{6})-", base)
    if m:
        out["file.date_code"] = m.group("date_code")

    return out

def load_manifest(path):
    with open(path, "r") as f:
        return json.load(f)


def try_import_pygwy():
    """
    Ensure pygwy is importable in this interpreter.

    On Windows, Gwyddion ships `gwy.pyd` and dependent DLLs in its `bin/` folder.
    For a system Python 2.7 install (e.g. `C:\\Python27\\python.exe`) you often
    need to add:
      - `C:\\Program Files (x86)\\Gwyddion\\bin` to PATH and sys.path
      - `C:\\Program Files (x86)\\Gwyddion\\share\\gwyddion\\pygwy` to sys.path (for `gwyutils.py`)

    This function tries to bootstrap those paths automatically (configurable via
    `GWY_BIN` env var). This is *not* a fallback processing path; it's just a
    convenience to locate the pygwy module.
    """
    try:
        import gwy  # noqa: F401
        return True
    except ImportError:
        pass

    candidates = []
    env_bin = os.environ.get("GWY_BIN") or os.environ.get("GWYDDION_BIN")
    if env_bin:
        candidates.append(env_bin)
    candidates.extend(
        [
            r"C:\Program Files (x86)\Gwyddion\bin",
            r"C:\Program Files\Gwyddion\bin",
        ]
    )

    for bin_dir in candidates:
        if not bin_dir or not os.path.isdir(bin_dir):
            continue
        if bin_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        if bin_dir not in sys.path:
            sys.path.insert(0, bin_dir)

        pygwy_dir = os.path.join(os.path.dirname(bin_dir), "share", "gwyddion", "pygwy")
        if os.path.isdir(pygwy_dir) and pygwy_dir not in sys.path:
            sys.path.insert(0, pygwy_dir)

        try:
            import gwy  # noqa: F401
            return True
        except Exception:
            continue

    sys.stderr.write(
        "ERROR: pygwy (gwy module) not importable.\n"
        "Hint: set GWY_BIN to your Gwyddion bin directory, e.g.\n"
        "  set GWY_BIN=C:\\Program Files (x86)\\Gwyddion\\bin\n"
    )
    return False


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


def _field_get_avg(field):
    """Average value from gwy.DataField."""
    try:
        return float(field.get_avg())
    except Exception:
        data = field.get_data()
        n = len(data)
        if not n:
            return 0.0
        s = 0.0
        for i in range(n):
            s += float(data[i])
        return s / float(n)


def _field_get_rms(field):
    """
    RMS (used as std proxy) from gwy.DataField.

    In Gwyddion terminology, `get_rms()` is typically the RMS roughness
    (sqrt(mean((z-mean)^2))), i.e. standard deviation after mean subtraction.
    """
    try:
        return float(field.get_rms())
    except Exception:
        data = field.get_data()
        n = len(data)
        if not n:
            return 0.0
        m = _field_get_avg(field)
        s2 = 0.0
        for i in range(n):
            dv = float(data[i]) - m
            s2 += dv * dv
        return math.sqrt(s2 / float(n))


def _percentile_sorted(sorted_vals, pct):
    """Linear-interpolated percentile for an already-sorted list."""
    n = len(sorted_vals)
    if not n:
        return 0.0
    if pct <= 0.0:
        return float(sorted_vals[0])
    if pct >= 100.0:
        return float(sorted_vals[-1])
    k = (n - 1) * (pct / 100.0)
    f = int(math.floor(k))
    c = int(math.ceil(k))
    if f == c:
        return float(sorted_vals[f])
    d0 = float(sorted_vals[f]) * (c - k)
    d1 = float(sorted_vals[c]) * (k - f)
    return d0 + d1


def _field_clip_percentiles(field, low, high):
    """Clip field data to [low, high] percentiles (Python-side helper)."""
    data = field.get_data()
    n = len(data)
    if not n:
        return
    vals = [float(data[i]) for i in range(n)]
    vals_sorted = sorted(vals)
    lo_val = _percentile_sorted(vals_sorted, float(low))
    hi_val = _percentile_sorted(vals_sorted, float(high))
    if hi_val < lo_val:
        lo_val, hi_val = hi_val, lo_val
    for i in range(n):
        v = vals[i]
        if v < lo_val:
            vals[i] = lo_val
        elif v > hi_val:
            vals[i] = hi_val
    field.set_data(vals)


def _mean(values):
    n = len(values)
    if not n:
        return 0.0
    s = 0.0
    for v in values:
        s += float(v)
    return s / float(n)


def _std(values):
    n = len(values)
    if not n:
        return 0.0
    m = _mean(values)
    s2 = 0.0
    for v in values:
        dv = float(v) - m
        s2 += dv * dv
    return math.sqrt(s2 / float(n))


def _connected_components(mask): # Why is this here? 
    """Deprecated: no longer used; particle counting relies on pygwy grain stats."""
    return [] # Empty List instead of a message or pass?


def _select_data_field(container, mode_def, channel_defaults):
    """
    Pick a data field from a container.

    Uses `mode_def.channel_family` (substring match against the data title) if
    provided; otherwise returns the first available `/N/data` entry.
    """
    names = []
    try:
        names = container.keys_by_name()
    except Exception:
        names = []

    data_names = []
    for n in names:
        if re.match(r"^/\d+/data$", str(n)):
            data_names.append(str(n))

    if not data_names:
        raise RuntimeError("No data fields found in container (expected keys like /0/data).")

    def _title_for(data_name):
        try:
            return container.get_string_by_name(data_name + "/title") or ""
        except Exception:
            return ""

    channel_family = None
    if mode_def:
        channel_family = mode_def.get("channel_family")

    if channel_family:
        for dn in data_names:
            title = _title_for(dn)
            if title and channel_family.lower() in title.lower():
                return dn, container.get_object_by_name(dn)

    first = data_names[0]
    return first, container.get_object_by_name(first)


def build_csv_row(mode_result, csv_def, processing_mode, csv_mode):
    """Py2-compatible csv row builder."""
    columns = csv_def.get("columns", [])
    on_missing = csv_def.get("on_missing_field", "warn_null")
    row = []
    for col_def in columns:
        key = col_def.get("from")
        has_default = "default" in col_def
        default = col_def.get("default", "")
        if key in mode_result:
            row.append(mode_result.get(key))
            continue
        if has_default:
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
    global _GRID_REGEX_MISS_WARNED
    global _GRID_INDEX_BASE_WARNED
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

            # Spec expects grid indices to be zero-based.
            # Filenames are commonly 1-based (e.g. RC001001). Allow explicit config,
            # and warn if we have to assume the base.
            index_base = None
            if grid_cfg:
                index_base = grid_cfg.get("index_base", None)
            if index_base is None:
                index_base = 1
                if not _GRID_INDEX_BASE_WARNED:
                    sys.stderr.write(
                        "WARN: grid.index_base not set; assuming filenames are 1-based and converting to zero-based indices. "
                        "Set grid.index_base explicitly (0 or 1) to silence this.\n"
                    )
                    _GRID_INDEX_BASE_WARNED = True
            try:
                index_base = int(index_base)
            except Exception:
                index_base = 1

            if row_val is not None:
                row_val = row_val - index_base
            if col_val is not None:
                col_val = col_val - index_base
            return row_val, col_val
        if pattern not in _GRID_REGEX_MISS_WARNED:
            sys.stderr.write(
                "WARN: grid.filename_regex did not match '%s' (pattern=%s). "
                "row_idx/col_idx will be -1. Update config and regenerate the manifest.\n"
                % (os.path.basename(path), pattern)
            )
            _GRID_REGEX_MISS_WARNED.add(pattern)
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

    result.update(_parse_filename_basic_metadata(path))

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
    try:
        field_title = container.get_string_by_name(field_id + "/title") or ""
    except Exception:
        field_title = ""
    mode = processing_mode or "raw_noop"

    if mode in ("modulus_basic", "topography_flat"):
        f = field.duplicate()
        if mode_def.get("plane_level", True):
            try:
                pa, pbx, pby = f.fit_plane()
                f.plane_level(pa, pbx, pby)
            except Exception as exc:
                sys.stderr.write("WARN: plane_level failed for %s: %s\n" % (path, exc))
        median_size = mode_def.get("median_size")
        if median_size:
            try:
                f.filter_median(int(median_size))
            except Exception as exc:
                sys.stderr.write("WARN: median filter failed for %s: %s\n" % (path, exc))
        if mode_def.get("line_level_x"):
            sys.stderr.write("WARN: line_level_x requested for %s but is not implemented in this runner.\n" % path)
        if mode_def.get("line_level_y"):
            sys.stderr.write("WARN: line_level_y requested for %s but is not implemented in this runner.\n" % path)
        # Python-side clipping is optional and used only when Gwyddion lacks a direct op.
        clip = mode_def.get("clip_percentiles")
        if clip and isinstance(clip, (list, tuple)) and len(clip) == 2:
            try:
                low, high = float(clip[0]), float(clip[1])
                _field_clip_percentiles(f, low, high)
            except Exception as exc:
                sys.stderr.write("WARN: clip_percentiles failed for %s: %s\n" % (path, exc))
        detected_unit = _get_field_units(f)
        result = _to_mode_result(f, mode_def, mode, path)
        result["channel.key"] = field_id
        if field_title:
            result["channel.title"] = field_title
        if detected_unit:
            result["channel.z_units"] = detected_unit
        return _apply_units(result, processing_mode, mode_def, manifest, detected_unit)

    if mode == "particle_count_basic":
        f = field.duplicate()
        thresh = mode_def.get("threshold")
        if thresh is None:
            try:
                thresh = _field_get_avg(f)
            except Exception:
                thresh = 0.0
        else:
            thresh = float(thresh)

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
            if sizes_list:
                equiv_diams = [2.0 * math.sqrt(float(a) / math.pi) for a in sizes_list]
                mean_diam = float(_mean(equiv_diams))
                std_diam = float(_std(equiv_diams))
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
                    circ_floats = [float(x) for x in circ_list]
                    mean_circ = float(_mean(circ_floats))
                    std_circ = float(_std(circ_floats))
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
        result["channel.key"] = field_id
        if field_title:
            result["channel.title"] = field_title
        det_u = _get_field_units(f)
        if det_u:
            result["channel.z_units"] = det_u
        result.update(grains_result)
        return _apply_units(result, processing_mode, mode_def, manifest, "count")

    if mode == "raw_noop":
        processed_field = field.duplicate()
        detected_unit = _get_field_units(processed_field)
        result = _to_mode_result(processed_field, mode_def, mode, path)
        result["channel.key"] = field_id
        if field_title:
            result["channel.title"] = field_title
        if detected_unit:
            result["channel.z_units"] = detected_unit
        return _apply_units(result, processing_mode, mode_def, manifest, detected_unit)

    raise ValueError("Unknown processing_mode: %s" % mode)


def _to_mode_result(field, mode_def, processing_mode, src_path):
    """Compute avg/std from a DataField."""
    global _STATS_WARNED
    stats_filter = mode_def.get("stats_filter") if mode_def else None
    if stats_filter:
        mean_val, std_val, vmin, vmax, n_valid = _field_stats_filtered(field, stats_filter or {})
        if not _STATS_WARNED:
            sys.stderr.write(
                "INFO: Using stats_filter for summary statistics (config-driven masking). "
                "This affects avg/std values.\n"
            )
            _STATS_WARNED = True
    else:
        mean_val = _field_get_avg(field)
        std_val = _field_get_rms(field)
        vmin, vmax, n_valid = None, None, None

    metric_type = mode_def.get("metric_type", processing_mode)
    units = mode_def.get("units", "a.u.")

    out = {
        "core.source_file": os.path.basename(src_path),
        "core.mode": processing_mode,
        "core.metric_type": metric_type,
        "core.avg_value": mean_val,
        "core.std_value": std_val,
        "core.units": units,
        "core.nx": int(field.get_xres()),
        "core.ny": int(field.get_yres()),
    }
    if vmin is not None:
        out["core.min_value"] = float(vmin)
    if vmax is not None:
        out["core.max_value"] = float(vmax)
    if n_valid is not None:
        out["core.n_valid"] = int(n_valid)
    return out


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
