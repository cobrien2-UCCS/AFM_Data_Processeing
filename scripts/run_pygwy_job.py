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
_STATS_SOURCE_WARNED = False
_DEBUG_SAVED = 0
_LINE_MATCH_METHODS = {
    "median": 0,
    "modus": 1,
    "polynomial": 2,
    "median_difference": 3,
    "matching": 4,
    "facet_level_tilt": 5,
    "trimmed_mean": 6,
    "trimmed_mean_difference": 7,
}
manifest_global_cfg = {}


def _is_finite(x):
    try:
        return (x == x) and (x != float("inf")) and (x != float("-inf"))
    except Exception:
        return True


def _field_stats_masked(field, mask, filter_cfg):
    """
    Compute mean/std/min/max on a DataField with optional mask + value filtering.

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

    count = 0
    mean_val = 0.0
    m2 = 0.0
    vmin = None
    vmax = None
    for i in range(n):
        if mask is not None and not mask[i]:
            continue
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

        count += 1
        if vmin is None or v < vmin:
            vmin = v
        if vmax is None or v > vmax:
            vmax = v

        # Welford online mean/std
        delta = v - mean_val
        mean_val += delta / float(count)
        m2 += delta * (v - mean_val)

    if not count:
        return 0.0, 0.0, 0.0, 0.0, 0

    std_val = math.sqrt(m2 / float(count))
    return float(mean_val), float(std_val), float(vmin), float(vmax), int(count)


def _field_stats_masked_debug(field, mask, filter_cfg):
    """Like _field_stats_masked, but also returns reason counters for exclusions."""
    data = field.get_data()
    n = len(data)
    reasons = {
        "n_total": int(n),
        "excluded_mask": 0,
        "excluded_nonfinite": 0,
        "excluded_zero": 0,
        "excluded_nonpositive": 0,
        "excluded_min": 0,
        "excluded_max": 0,
        "excluded_max_abs": 0,
        "kept": 0,
    }
    if not n:
        return 0.0, 0.0, 0.0, 0.0, 0, reasons

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

    count = 0
    mean_val = 0.0
    m2 = 0.0
    vmin = None
    vmax = None
    for i in range(n):
        if mask is not None and not mask[i]:
            reasons["excluded_mask"] += 1
            continue
        v = float(data[i])
        if not _is_finite(v):
            reasons["excluded_nonfinite"] += 1
            continue
        if exclude_zero and v == 0.0:
            reasons["excluded_zero"] += 1
            continue
        if exclude_nonpositive and v <= 0.0:
            reasons["excluded_nonpositive"] += 1
            continue
        if min_value is not None and v < min_value:
            reasons["excluded_min"] += 1
            continue
        if max_value is not None and v > max_value:
            reasons["excluded_max"] += 1
            continue
        if max_abs_value is not None and abs(v) > max_abs_value:
            reasons["excluded_max_abs"] += 1
            continue

        count += 1
        reasons["kept"] += 1
        if vmin is None or v < vmin:
            vmin = v
        if vmax is None or v > vmax:
            vmax = v
        delta = v - mean_val
        mean_val += delta / float(count)
        m2 += delta * (v - mean_val)

    if not count:
        return 0.0, 0.0, 0.0, 0.0, 0, reasons

    std_val = math.sqrt(m2 / float(count))
    return float(mean_val), float(std_val), float(vmin), float(vmax), int(count), reasons


def _field_stats_filtered(field, filter_cfg):
    return _field_stats_masked(field, None, filter_cfg or {})


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


def _normalize_method_name(name):
    if not name:
        return ""
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")

def _normalize_stats_source(name):
    # Default is explicit and deterministic (no auto switching).
    if not name:
        return "python"
    s = _normalize_method_name(name)
    if s in ("python", "py"):
        return "python"
    if s in ("gwyddion", "gwy", "pygwy"):
        return "gwyddion"
    if s in ("auto", "default"):
        return "python"
    return "python"


def _debug_cfg(manifest):
    return manifest.get("debug") or {}


def _debug_enabled(manifest):
    dbg = _debug_cfg(manifest)
    return bool(dbg.get("enable"))


def _debug_level(manifest):
    dbg = _debug_cfg(manifest)
    lvl = str(dbg.get("level", "info")).lower()
    return lvl


def _debug_should_save(manifest):
    global _DEBUG_SAVED
    dbg = _debug_cfg(manifest)
    if not dbg.get("enable"):
        return False
    limit = dbg.get("sample_limit")
    try:
        limit = int(limit)
    except Exception:
        limit = None
    if limit is None or limit <= 0:
        return True
    return _DEBUG_SAVED < limit


def _debug_out_dir(manifest):
    dbg = _debug_cfg(manifest)
    out_dir = dbg.get("out_dir")
    if out_dir:
        return out_dir
    out_dir = manifest.get("output_dir") or "."
    return os.path.join(out_dir, "debug")


def _save_field(path, field):
    """Save a DataField to a file using Pillow/NumPy (skip pygwy export to reduce noise)."""
    # Ensure output directory exists
    out_dir = os.path.dirname(path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    # Pillow/NumPy export (avoids pygwy "no exportable channel" noise)
    try:
        import numpy as np
        from PIL import Image
    except Exception as exc2:
        sys.stderr.write("WARN: debug save fallback unavailable (Pillow/NumPy missing): %s\n" % exc2)
        return False
    try:
        nx = int(field.get_xres())
        ny = int(field.get_yres())
        data = field.get_data()
        arr = np.array([float(x) for x in data], dtype=float).reshape((ny, nx))
        vmin = float(np.nanmin(arr)) if arr.size else 0.0
        vmax = float(np.nanmax(arr)) if arr.size else 1.0
        if vmax == vmin:
            vmax = vmin + 1.0
        norm = (arr - vmin) / (vmax - vmin)
        norm = np.clip(norm, 0.0, 1.0)
        img = Image.fromarray(np.uint8(norm * 255.0), mode="L")
        img.save(path)
        return True
    except Exception as exc3:
        sys.stderr.write("WARN: debug save fallback (Pillow) failed for %s: %s\n" % (path, exc3))
        return False


def _mask_field_from_bool(field, mask):
    """Create a DataField mask (0/1) from a boolean mask list."""
    try:
        mfield = field.duplicate()
        data = mfield.get_data()
        for i in range(len(data)):
            data[i] = 1.0 if mask[i] else 0.0
        return mfield
    except Exception:
        return None


def _apply_ops_sequence(container, field_key, field, ops, debug_artifacts, trace=None, trace_stats=False):
    """
    Apply a config-driven ordered list of pygwy/Gwyddion operations.
    Supported ops (name -> params):
      - plane_level: {method: fit_plane}
      - align_rows: {direction: horizontal|vertical, method: median|polynomial|matching|...}
      - median: {size: int}
      - clip_percentiles: {low: float, high: float}
    """
    f = field
    for op in ops:
        if not isinstance(op, dict):
            continue
        name = _normalize_method_name(op.get("op") or op.get("name"))
        params = op.get("params") or {}
        if name == "plane_level":
            try:
                pa, pbx, pby = f.fit_plane()
                f.plane_level(pa, pbx, pby)
                _trace_append(trace, "plane_level", True)
                if debug_artifacts is not None:
                    debug_artifacts["leveled"] = f.duplicate()
                if trace_stats:
                    _trace_stats(trace, f, "after_plane_level")
            except Exception as exc:
                _trace_append(trace, "plane_level", False, str(exc))
        elif name in ("align_rows", "line_correct", "line_match"):
            try:
                ok = _apply_line_correction(container, field_key, params)
                _trace_append(trace, "align_rows", ok, params)
                if ok and debug_artifacts is not None:
                    try:
                        f = container.get_object_by_name(field_key)
                        debug_artifacts["aligned"] = f.duplicate()
                    except Exception:
                        pass
                if ok and trace_stats:
                    _trace_stats(trace, f, "after_align_rows")
            except Exception as exc:
                _trace_append(trace, "align_rows", False, str(exc))
        elif name == "median":
            try:
                size = int(params.get("size", 3))
                f.filter_median(size)
                _trace_append(trace, "median", True, {"size": size})
                if debug_artifacts is not None:
                    debug_artifacts["filtered"] = f.duplicate()
                if trace_stats:
                    _trace_stats(trace, f, "after_median")
            except Exception as exc:
                _trace_append(trace, "median", False, str(exc))
        elif name == "clip_percentiles":
            try:
                low = float(params.get("low", 0.0))
                high = float(params.get("high", 100.0))
                _field_clip_percentiles(f, low, high)
                _trace_append(trace, "clip_percentiles", True, {"low": low, "high": high})
                if debug_artifacts is not None:
                    debug_artifacts["filtered"] = f.duplicate()
                if trace_stats:
                    _trace_stats(trace, f, "after_clip_percentiles")
            except Exception as exc:
                _trace_append(trace, "clip_percentiles", False, str(exc))
        else:
            _trace_append(trace, "op_ignored", False, {"op": name})
    return f


def _export_field_csv(field, mask, path):
    """Export the DataField values to a CSV (row, col, value, kept)."""
    out_dir = os.path.dirname(path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    nx = int(field.get_xres())
    ny = int(field.get_yres())
    data = field.get_data()
    total = len(data)
    with open(path, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["row", "col", "value", "kept"])
        for j in range(ny):
            for i in range(nx):
                idx = j * nx + i
                if idx >= total:
                    continue
                val = data[idx]
                keep = 1 if (mask is None or (idx < len(mask) and mask[idx])) else 0
                writer.writerow([j, i, val, keep])


def _apply_python_filters(field, base_mask, filter_cfg):
    """
    Apply optional Python-side value filters after Gwyddion preprocessing.

    Supported filters (applied in order):
      - three_sigma: keep values within mean ± sigma*std of current kept set
      - chauvenet: Chauvenet criterion (two-sided) against current kept set
      - min_max: keep values within [min_value, max_value]
    """
    if not filter_cfg or not filter_cfg.get("enable"):
        return base_mask, None, {}

    filters = filter_cfg.get("filters") or []
    if isinstance(filters, dict):
        filters = [filters]
    if not filters:
        return base_mask, None, {}

    data = field.get_data()
    n = len(data)
    if not n:
        return base_mask, None, {}

    mask = list(base_mask) if base_mask is not None else [True] * n
    total = len(mask)
    debug_notes = []

    def _kept_values(current_mask):
        vals = []
        for idx in range(min(len(data), len(current_mask))):
            if not current_mask[idx]:
                continue
            v = float(data[idx])
            if _is_finite(v):
                vals.append(v)
        return vals

    for filt in filters:
        ftype = _normalize_method_name(filt.get("type") or filt.get("name") or "")
        if not ftype:
            continue

        kept_before = sum(1 for m in mask if m)
        if kept_before == 0:
            break

        vals = _kept_values(mask)
        if not vals:
            break

        new_mask = list(mask)
        if ftype == "three_sigma":
            try:
                sigma = float(filt.get("sigma", 3.0))
            except Exception:
                sigma = 3.0
            m = _mean(vals)
            s = _std(vals)
            if s <= 0.0:
                debug_notes.append("three_sigma skipped (std<=0)")
            else:
                lo = m - sigma * s
                hi = m + sigma * s
                for idx in range(len(new_mask)):
                    if not new_mask[idx]:
                        continue
                    v = float(data[idx])
                    if not _is_finite(v):
                        new_mask[idx] = False
                        continue
                    if v < lo or v > hi:
                        new_mask[idx] = False
                mask = new_mask
        elif ftype == "chauvenet":
            m = _mean(vals)
            s = _std(vals)
            if s <= 0.0:
                debug_notes.append("chauvenet skipped (std<=0)")
            else:
                thr = 1.0 / (2.0 * float(len(vals)))
                for idx in range(len(new_mask)):
                    if not new_mask[idx]:
                        continue
                    v = float(data[idx])
                    if not _is_finite(v):
                        new_mask[idx] = False
                        continue
                    z = abs(v - m) / s if s > 0 else 0.0
                    prob = math.erfc(z / math.sqrt(2.0))
                    if prob < thr:
                        new_mask[idx] = False
                mask = new_mask
        elif ftype in ("min_max", "minmax"):
            try:
                lo = filt.get("min_value")
                hi = filt.get("max_value")
                lo = float(lo) if lo is not None else None
                hi = float(hi) if hi is not None else None
            except Exception:
                lo, hi = None, None
            for idx in range(len(new_mask)):
                if not new_mask[idx]:
                    continue
                v = float(data[idx])
                if not _is_finite(v):
                    new_mask[idx] = False
                    continue
                if lo is not None and v < lo:
                    new_mask[idx] = False
                if hi is not None and v > hi:
                    new_mask[idx] = False
            mask = new_mask

        kept_after = sum(1 for m in mask if m)
        debug_notes.append("%s %s/%s" % (ftype, kept_after, kept_before))

    kept_final = sum(1 for m in mask if m)
    debug_info = {
        "pyfilter.n_total": int(total),
        "pyfilter.n_kept": int(kept_final),
        "_debug.pyfilter_steps": "; ".join(debug_notes),
    }
    return mask, (total, kept_final), debug_info


def _debug_log_fields(manifest):
    dbg = _debug_cfg(manifest)
    fields = dbg.get("log_fields") or []
    if isinstance(fields, str):
        fields = [fields]
    return set([str(f).strip().lower() for f in fields if f])


def _trace_append(trace, step, ok=True, info=None):
    if trace is None:
        return
    rec = {"step": step, "ok": bool(ok)}
    if info is not None:
        rec["info"] = info
    trace.append(rec)


def _write_trace_file(manifest, path, trace):
    if not trace:
        return
    dbg = manifest.get("debug") or {}
    if not dbg.get("enable"):
        return
    trace_dir = dbg.get("trace_dir") or dbg.get("out_dir") or os.path.join(manifest.get("output_dir", "."), "debug")
    try:
        if not os.path.isdir(trace_dir):
            os.makedirs(trace_dir)
        base = os.path.splitext(os.path.basename(path))[0]
        out_path = os.path.join(trace_dir, "%s.trace.json" % base)
        with open(out_path, "w") as f:
            json.dump(trace, f, indent=2)
    except Exception:
        pass


def _quick_stats(field):
    """Return (min, max, p5, p50, p95) using Python-side data."""
    data = field.get_data()
    if not data:
        return None
    vals = [float(v) for v in data if _is_finite(v)]
    if not vals:
        return None
    vals_sorted = sorted(vals)
    n = len(vals_sorted)
    def pct(p):
        return _percentile_sorted(vals_sorted, p)
    return (min(vals_sorted), max(vals_sorted), pct(5), pct(50), pct(95))


def _trace_stats(trace, field, label):
    if trace is None:
        return
    info = {"label": label}
    try:
        info["avg"] = float(_field_get_avg(field))
    except Exception:
        info["avg"] = None
    try:
        info["rms"] = float(_field_get_rms(field))
    except Exception:
        info["rms"] = None
    stats = _quick_stats(field)
    if stats:
        info["min"] = float(stats[0])
        info["max"] = float(stats[1])
        info["p5"] = float(stats[2])
        info["p50"] = float(stats[3])
        info["p95"] = float(stats[4])
    _trace_append(trace, "stats_snapshot", True, info)


def _apply_unit_conversion_to_field(field, detected_unit, processing_mode, manifest):
    if not detected_unit:
        return field, detected_unit, None
    conversions = (manifest.get("unit_conversions") or {}).get(processing_mode, {})
    conversions = _normalize_unit_conversions(conversions)
    detected_unit = _normalize_unit_name(detected_unit)
    if not conversions or not detected_unit:
        return field, detected_unit, None
    conv = conversions.get(detected_unit)
    if not conv:
        return field, detected_unit, None
    try:
        factor = float(conv.get("factor", 1.0))
    except Exception:
        factor = 1.0
    target = conv.get("target", detected_unit)
    target = _normalize_unit_name(target) or target
    if factor != 1.0:
        data = field.get_data()
        for i in range(len(data)):
            data[i] = float(data[i]) * factor
    return field, target, {"source": detected_unit, "target": target, "factor": factor}


def _build_single_mask(field, mask_cfg):
    """Build a boolean mask list from a single mask config entry."""
    if not mask_cfg:
        return None, 0, 0
    if isinstance(mask_cfg, bool):
        if not mask_cfg:
            return None, 0, 0
        mask_cfg = {}

    enabled = bool(mask_cfg.get("enable", True))
    if not enabled:
        return None, 0, 0

    method = _normalize_method_name(mask_cfg.get("method") or mask_cfg.get("type") or "threshold")
    invert = bool(mask_cfg.get("invert"))
    include_equal = mask_cfg.get("include_equal", True)
    inclusive = bool(mask_cfg.get("inclusive", True))

    # Gwyddion-native mask helpers (via DataField methods), returned as a boolean list.
    # These operate on the (already preprocessed) DataField but do not depend on unit metadata.
    if method in ("gwy_outliers", "gwy_mask_outliers", "mask_outliers", "outliers"):
        try:
            thresh = float(mask_cfg.get("thresh"))
        except Exception:
            thresh = None
        if thresh is None:
            raise ValueError("mask_outliers requires 'thresh' (float)")
        try:
            mask_field = field.create_full_mask()
            field.mask_outliers(mask_field, float(thresh))
            data = mask_field.get_data()
            # Gwyddion mask convention is "1 == masked (excluded)".  Our mask convention is
            # "True == kept (included)", so we invert by default.
            base_mask = [not (float(v) > 0.5) for v in data]
        except Exception as exc:
            raise RuntimeError("gwyddion mask_outliers failed: %s" % exc)
        if invert:
            base_mask = [not m for m in base_mask]
        kept = sum(1 for m in base_mask if m)
        return base_mask, kept, len(base_mask)

    if method in ("gwy_outliers2", "gwy_mask_outliers2", "mask_outliers2", "outliers2"):
        try:
            thresh_low = float(mask_cfg.get("thresh_low"))
        except Exception:
            thresh_low = None
        try:
            thresh_high = float(mask_cfg.get("thresh_high"))
        except Exception:
            thresh_high = None
        if thresh_low is None or thresh_high is None:
            raise ValueError("mask_outliers2 requires 'thresh_low' and 'thresh_high' (float)")
        try:
            mask_field = field.create_full_mask()
            field.mask_outliers2(mask_field, float(thresh_low), float(thresh_high))
            data = mask_field.get_data()
            # Gwyddion mask convention is "1 == masked (excluded)".  Our mask convention is
            # "True == kept (included)", so we invert by default.
            base_mask = [not (float(v) > 0.5) for v in data]
        except Exception as exc:
            raise RuntimeError("gwyddion mask_outliers2 failed: %s" % exc)
        if invert:
            base_mask = [not m for m in base_mask]
        kept = sum(1 for m in base_mask if m)
        return base_mask, kept, len(base_mask)

    data = field.get_data()
    n = len(data)
    if not n:
        return None, 0, 0

    mask = [False] * n
    kept = 0

    if method == "threshold":
        if "threshold" not in mask_cfg:
            raise RuntimeError("mask.method=threshold requires mask.threshold")
        try:
            threshold = float(mask_cfg.get("threshold"))
        except Exception:
            raise RuntimeError("mask.threshold must be numeric")
        direction = _normalize_method_name(mask_cfg.get("direction") or "above")
        for i in range(n):
            v = float(data[i])
            if not _is_finite(v):
                continue
            if direction in ("above", "greater", "gt"):
                keep = v >= threshold if include_equal else v > threshold
            elif direction in ("below", "less", "lt"):
                keep = v <= threshold if include_equal else v < threshold
            else:
                raise RuntimeError("mask.direction must be 'above' or 'below'")
            if invert:
                keep = not keep
            if keep:
                mask[i] = True
                kept += 1

    elif method == "range":
        min_value = mask_cfg.get("min_value")
        max_value = mask_cfg.get("max_value")
        if min_value is None and max_value is None:
            raise RuntimeError("mask.method=range requires min_value and/or max_value")
        try:
            min_value = float(min_value) if min_value is not None else None
        except Exception:
            min_value = None
        try:
            max_value = float(max_value) if max_value is not None else None
        except Exception:
            max_value = None
        if min_value is None and max_value is None:
            raise RuntimeError("mask.method=range requires numeric min_value and/or max_value")

        for i in range(n):
            v = float(data[i])
            if not _is_finite(v):
                continue
            keep = True
            if min_value is not None:
                keep = keep and (v >= min_value if inclusive else v > min_value)
            if max_value is not None:
                keep = keep and (v <= max_value if inclusive else v < max_value)
            if invert:
                keep = not keep
            if keep:
                mask[i] = True
                kept += 1

    elif method == "percentile":
        pct_pair = mask_cfg.get("percentiles")
        low = mask_cfg.get("low_percentile")
        high = mask_cfg.get("high_percentile")
        if pct_pair and isinstance(pct_pair, (list, tuple)) and len(pct_pair) == 2:
            low, high = pct_pair[0], pct_pair[1]
        if low is None or high is None:
            raise RuntimeError("mask.method=percentile requires low/high percentiles")
        try:
            low = float(low)
            high = float(high)
        except Exception:
            raise RuntimeError("mask.percentiles must be numeric")

        vals = []
        for i in range(n):
            v = float(data[i])
            if _is_finite(v):
                vals.append(v)
        if not vals:
            return None, 0, n
        vals_sorted = sorted(vals)
        lo_val = _percentile_sorted(vals_sorted, low)
        hi_val = _percentile_sorted(vals_sorted, high)
        if hi_val < lo_val:
            lo_val, hi_val = hi_val, lo_val

        for i in range(n):
            v = float(data[i])
            if not _is_finite(v):
                continue
            keep = (v >= lo_val if inclusive else v > lo_val) and (v <= hi_val if inclusive else v < hi_val)
            if invert:
                keep = not keep
            if keep:
                mask[i] = True
                kept += 1

    else:
        raise RuntimeError("Unknown mask.method: %s" % method)

    return mask, kept, n


def _build_mask(field, mask_cfg):
    """
    Build a boolean mask list from config.

    Supports a single mask dict or a list/steps with combine policy.
    mask[i] == True means the value is included in summary stats.
    Supported methods: threshold, range, percentile.
    """
    if not mask_cfg:
        return None, None, None
    if isinstance(mask_cfg, list):
        steps = mask_cfg
        combine = "and"
        on_empty = "error"
    elif isinstance(mask_cfg, dict) and "steps" in mask_cfg:
        steps = mask_cfg.get("steps") or []
        combine = _normalize_method_name(mask_cfg.get("combine") or "and")
        on_empty = mask_cfg.get("on_empty", "error")
    else:
        steps = [mask_cfg]
        combine = "and"
        on_empty = mask_cfg.get("on_empty", "error") if isinstance(mask_cfg, dict) else "error"

    if not steps:
        return None, None, None

    data = field.get_data()
    n = len(data)
    if not n:
        return None, None, None

    combined = None
    for step in steps:
        step_mask, _, _ = _build_single_mask(field, step)
        if step_mask is None:
            continue
        if combined is None:
            combined = step_mask
        else:
            if combine in ("or", "union"):
                combined = [(combined[i] or step_mask[i]) for i in range(n)]
            else:
                combined = [(combined[i] and step_mask[i]) for i in range(n)]

    if combined is None:
        return None, None, None

    kept = sum(1 for m in combined if m)
    if kept == 0:
        if on_empty == "skip_row":
            return combined, kept, n
        if on_empty == "warn":
            sys.stderr.write("WARN: Mask stage produced 0 included pixels; continuing.\n")
        else:
            raise RuntimeError("Mask stage produced 0 included pixels.")
    return combined, kept, n


def _apply_line_correction(container, field_key, line_cfg, fallback_direction=None):
    """
    Apply scan-line correction using Gwyddion's Align Rows (linematch) module.

    Uses app settings keys documented in the Gwyddion user guide:
      /module/linematch/direction
      /module/linematch/method
      /module/linematch/do_extract
      /module/linematch/do_plot
    """
    if not line_cfg:
        return False
    if isinstance(line_cfg, bool):
        enabled = line_cfg
        line_cfg = {}
    else:
        enabled = bool(line_cfg.get("enable", True))
    if not enabled:
        return False

    try:
        import gwy  # type: ignore
    except Exception:
        return False

    method_id = line_cfg.get("method_id")
    name = _normalize_method_name(line_cfg.get("method"))
    if method_id is None and not name:
        name = "median"
    if method_id is None and name:
        method_id = _LINE_MATCH_METHODS.get(name)

    direction = line_cfg.get("direction") or fallback_direction
    dir_val = None
    if direction is not None:
        if isinstance(direction, (int, long)):
            dir_val = int(direction)
        else:
            d = str(direction).strip().lower()
            if d.startswith("h"):
                dir_val = int(gwy.ORIENTATION_HORIZONTAL)
            elif d.startswith("v"):
                dir_val = int(gwy.ORIENTATION_VERTICAL)

    try:
        gwy.gwy_app_data_browser_add(container)
        ids = gwy.gwy_app_data_browser_get_data_ids(container)
        target_id = None
        for i in ids:
            gwy.gwy_app_data_browser_select_data_field(container, i)
            try:
                key = gwy.gwy_app_data_browser_get_current(gwy.APP_DATA_FIELD_KEY)
            except Exception:
                key = None
            if key and str(key) == str(field_key):
                target_id = i
                break
        if target_id is None and ids:
            target_id = ids[0]
        if target_id is None:
            return False
        gwy.gwy_app_data_browser_select_data_field(container, target_id)

        settings = gwy.gwy_app_settings_get()
        try:
            settings.set_boolean_by_name("/module/linematch/do_extract", False)
            settings.set_boolean_by_name("/module/linematch/do_plot", False)
        except Exception:
            pass
        if dir_val is not None:
            try:
                settings.set_int32_by_name("/module/linematch/direction", int(dir_val))
            except Exception:
                pass
        if method_id is not None:
            try:
                settings.set_int32_by_name("/module/linematch/method", int(method_id))
            except Exception:
                pass

        gwy.gwy_process_func_run("align_rows", container, gwy.RUN_IMMEDIATE)
        return True
    except Exception as exc:
        sys.stderr.write("WARN: align_rows failed: %s\n" % exc)
        return False
    finally:
        try:
            gwy.gwy_app_data_browser_remove(container)
        except Exception:
            pass

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


def _normalize_unit_name(u):
    if not u:
        return None
    s = str(u).strip()
    s = s.replace(" ", "").replace("²", "2").replace("�", "")
    s_lower = s.lower()
    # Common variants
    aliases = {
        "pa": "Pa",
        "n/m2": "Pa",
        "nm-2": "Pa",
        "kpa": "kPa",
        "mpa": "MPa",
        "gpa": "GPa",
    }
    if s_lower in aliases:
        return aliases[s_lower]
    return s


def _normalize_unit_conversions(conversions):
    out = {}
    for k, v in (conversions or {}).items():
        nk = _normalize_unit_name(k) or k
        out[nk] = v
    return out


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


def _set_meta_key(meta, key_path, value):
    """Set a dotted key_path in the meta dict."""
    if meta is None:
        return
    parts = key_path.split(".")
    cur = meta
    for i, p in enumerate(parts):
        if i == len(parts) - 1:
            cur[p] = value
        else:
            if p not in cur or not isinstance(cur[p], dict):
                cur[p] = {}
            cur = cur[p]


def derive_grid_indices(path, grid_cfg, filename_parsing=None, meta=None):
    """
    Derive grid row/col from filename using config-driven parsing.
    Supports:
      - filename_parsing.patterns: list of {regex, map: {group->meta_key}}
      - legacy grid.filename_regex with row/col named groups.
    """
    global _GRID_REGEX_MISS_WARNED
    global _GRID_INDEX_BASE_WARNED
    base = os.path.basename(path)
    row_idx = None
    col_idx = None

    # Config-driven patterns
    patterns = (filename_parsing or {}).get("patterns") or []
    if patterns:
        for pat in patterns:
            rx = pat.get("regex")
            mapping = pat.get("map") or {}
            if not rx:
                continue
            try:
                m = re.search(rx, base)
            except Exception:
                continue
            if not m:
                continue
            gd = m.groupdict()
            if "row" in gd and "col" in gd and row_idx is None and col_idx is None:
                try:
                    rv = int(gd.get("row"))
                    cv = int(gd.get("col"))
                except Exception:
                    rv, cv = None, None
                else:
                    idx_base = int((grid_cfg or {}).get("index_base", 0))
                    if idx_base == 1:
                        rv -= 1
                        cv -= 1
                    row_idx, col_idx = rv, cv
            for k, key_path in mapping.items():
                if k in gd:
                    _set_meta_key(meta, key_path, gd.get(k))

    # Legacy fallback
    if row_idx is None or col_idx is None:
        pattern = None
        if grid_cfg:
            pattern = grid_cfg.get("filename_regex")
        if pattern:
            try:
                regex = re.compile(pattern)
                m = regex.search(base)
                if m:
                    row = m.groupdict().get("row")
                    col = m.groupdict().get("col")
                    row_val = int(row) if row is not None else None
                    col_val = int(col) if col is not None else None

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
                    row_idx, col_idx = row_val, col_val
                elif pattern not in _GRID_REGEX_MISS_WARNED:
                    sys.stderr.write(
                        "WARN: grid.filename_regex did not match '%s' (pattern=%s). "
                        "row_idx/col_idx will be -1. Update config and regenerate the manifest.\n"
                        % (base, pattern)
                    )
                    _GRID_REGEX_MISS_WARNED.add(pattern)
            except Exception:
                pass

    return row_idx, col_idx


def process_file(path, manifest, use_pygwy, allow_debug_save=False):
    mode_def = manifest.get("mode_definition", {}) or {}
    grid_cfg = manifest.get("grid", {}) or {}
    filename_parsing = manifest.get("filename_parsing", {}) or {}
    channel_defaults = manifest.get("channel_defaults", {}) or {}
    processing_mode = manifest.get("processing_mode")
    meta = {}
    row_idx, col_idx = derive_grid_indices(path, grid_cfg, filename_parsing=filename_parsing, meta=meta)

    if not use_pygwy:
        raise RuntimeError("pygwy required for processing; no fallback is executed.")
    result = _process_with_pygwy(path, processing_mode, mode_def, channel_defaults, manifest, allow_debug_save=allow_debug_save)
    if result is None:
        return None

    result.update(_parse_filename_basic_metadata(path))
    # Add parsed meta if present
    for k, v in meta.items():
        result[k] = v

    if row_idx is not None:
        result["grid.row_idx"] = row_idx
    if col_idx is not None:
        result["grid.col_idx"] = col_idx

    if _debug_enabled(manifest):
        lvl = _debug_level(manifest)
        log_fields = _debug_log_fields(manifest)
        # Default fields if none specified
        if not log_fields:
            log_fields = set(["units", "stats_source", "mask_counts", "stats_counts", "stats_reasons", "grid", "raw_stats", "pyfilter"])
        detected_unit = result.get("_debug.detected_unit")
        detected_unit_raw = result.get("_debug.detected_unit_raw")
        unit_source = result.get("_debug.unit_source")
        unit_conv = result.get("_debug.unit_conversion")
        final_unit = result.get("core.units")
        parts = ["[DEBUG] %s" % os.path.basename(path)]
        if "units" in log_fields:
            if detected_unit_raw:
                parts.append("unit_raw=%s" % detected_unit_raw)
            parts.append("unit=%s" % (detected_unit or "n/a"))
            if unit_source:
                parts.append("unit_source=%s" % unit_source)
            if detected_unit and final_unit and detected_unit != final_unit:
                parts.append("unit_out=%s" % final_unit)
        if "unit_conversion" in log_fields and unit_conv:
            try:
                parts.append("unit_conv=%s->%s x%s" % (unit_conv.get("source"), unit_conv.get("target"), unit_conv.get("factor")))
            except Exception:
                parts.append("unit_conv=%s" % str(unit_conv))
        if "stats_counts" in log_fields and "core.n_valid" in result:
            parts.append("n_valid=%s" % result.get("core.n_valid"))
        if "stats_source" in log_fields and result.get("_debug.stats_source"):
            parts.append("stats_source=%s" % result.get("_debug.stats_source"))
        if "mask_counts" in log_fields and "mask.n_kept" in result and "mask.n_total" in result:
            parts.append("mask=%s/%s" % (result.get("mask.n_kept"), result.get("mask.n_total")))
        if "pyfilter" in log_fields and "pyfilter.n_kept" in result and "pyfilter.n_total" in result:
            parts.append("pyfilter=%s/%s" % (result.get("pyfilter.n_kept"), result.get("pyfilter.n_total")))
        if "pyfilter_steps" in log_fields and "_debug.pyfilter_steps" in result:
            parts.append("pfsteps=%s" % result.get("_debug.pyfilter_steps"))
        if "stats_reasons" in log_fields and "_debug.stats_reasons" in result:
            try:
                parts.append("stats_reasons=%s" % json.dumps(result.get("_debug.stats_reasons")))
            except Exception:
                parts.append("stats_reasons=%s" % str(result.get("_debug.stats_reasons")))
        if "grid" in log_fields:
            r = result.get("grid.row_idx")
            c = result.get("grid.col_idx")
            if r is not None and c is not None:
                parts.append("grid=(%s,%s)" % (r, c))
        if "raw_stats" in log_fields:
            raw_min = result.get("_debug.raw_min")
            raw_max = result.get("_debug.raw_max")
            raw_p5 = result.get("_debug.raw_p5")
            raw_p50 = result.get("_debug.raw_p50")
            raw_p95 = result.get("_debug.raw_p95")
            if raw_min is not None and raw_max is not None:
                parts.append("raw[min=%.3g max=%.3g p5=%.3g p50=%.3g p95=%.3g]" % (raw_min, raw_max, raw_p5, raw_p50, raw_p95))
        msg = " ".join(parts)
        if lvl in ("info", "debug"):
            sys.stderr.write(msg + "\n")
    return result


def _process_with_pygwy(path, processing_mode, mode_def, channel_defaults, manifest, allow_debug_save=False):
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
    debug_artifacts = {}
    debug_notes = {}
    did_line_correct = False
    line_cfg = mode_def.get("line_correct") if mode_def else None
    if line_cfg:
        did_line_correct = _apply_line_correction(container, field_id, line_cfg)
    else:
        # Backwards-compat mapping for older configs
        if mode_def.get("line_level_x"):
            did_line_correct = _apply_line_correction(
                container,
                field_id,
                {"enable": True, "method": "median", "direction": "horizontal"},
                fallback_direction="horizontal",
            ) or did_line_correct
        if mode_def.get("line_level_y"):
            did_line_correct = _apply_line_correction(
                container,
                field_id,
                {"enable": True, "method": "median", "direction": "vertical"},
                fallback_direction="vertical",
            ) or did_line_correct

    if did_line_correct:
        try:
            field = container.get_object_by_name(field_id)
            if allow_debug_save:
                debug_artifacts["aligned"] = field.duplicate()
        except Exception:
            pass

    try:
        field_title = container.get_string_by_name(field_id + "/title") or ""
    except Exception:
        field_title = ""
    mode = processing_mode or "raw_noop"

    if mode in ("modulus_basic", "modulus_simple", "modulus_complex", "topography_flat"):
        f = field.duplicate()
        trace = []
        stats_debug = _debug_enabled(manifest) and (manifest.get("debug") or {}).get("stats_provenance")
        raw_stats = _quick_stats(f)
        if stats_debug:
            _trace_stats(trace, f, "initial")
        ops = mode_def.get("gwyddion_ops")
        if ops:
            f = _apply_ops_sequence(container, field_id, f, ops, debug_artifacts, trace, trace_stats=stats_debug)
        else:
            # Legacy behavior
            if mode_def.get("plane_level", True):
                try:
                    pa, pbx, pby = f.fit_plane()
                    f.plane_level(pa, pbx, pby)
                    _trace_append(trace, "plane_level", True)
                    if allow_debug_save:
                        debug_artifacts["leveled"] = f.duplicate()
                    if stats_debug:
                        _trace_stats(trace, f, "after_plane_level")
                except Exception as exc:
                    _trace_append(trace, "plane_level", False, str(exc))
                    sys.stderr.write("WARN: plane_level failed for %s: %s\n" % (path, exc))
            median_size = mode_def.get("median_size")
            if median_size:
                try:
                    f.filter_median(int(median_size))
                    _trace_append(trace, "median", True, {"size": median_size})
                    if allow_debug_save:
                        debug_artifacts["filtered"] = f.duplicate()
                    if stats_debug:
                        _trace_stats(trace, f, "after_median")
                except Exception as exc:
                    _trace_append(trace, "median", False, str(exc))
                    sys.stderr.write("WARN: median filter failed for %s: %s\n" % (path, exc))
            if mode_def.get("line_level_x"):
                sys.stderr.write("WARN: line_level_x requested for %s but is not implemented in this runner.\n" % path)
            if mode_def.get("line_level_y"):
                sys.stderr.write("WARN: line_level_y requested for %s but is not implemented in this runner.\n" % path)
            clip = mode_def.get("clip_percentiles")
            if clip and isinstance(clip, (list, tuple)) and len(clip) == 2:
                try:
                    low, high = float(clip[0]), float(clip[1])
                    _field_clip_percentiles(f, low, high)
                    _trace_append(trace, "clip_percentiles", True, {"low": low, "high": high})
                    if allow_debug_save:
                        debug_artifacts["filtered"] = f.duplicate()
                    if stats_debug:
                        _trace_stats(trace, f, "after_clip_percentiles")
                except Exception as exc:
                    _trace_append(trace, "clip_percentiles", False, str(exc))
                    sys.stderr.write("WARN: clip_percentiles failed for %s: %s\n" % (path, exc))

        # Detect units and apply unit normalization *before* masks/filters so any
        # value-based thresholds are interpreted in normalized units.
        detected_unit_raw = _get_field_units(f)
        unit_source = "file" if detected_unit_raw else "default"
        assume_units = mode_def.get("assume_units") if mode_def else None
        missing_units_policy = "warn"
        if mode_def:
            missing_units_policy = mode_def.get("on_missing_units", "warn")
        if not detected_unit_raw:
            if assume_units:
                detected_unit_raw = assume_units
                unit_source = "assumed"
            else:
                msg = "No units detected for %s" % path
                if missing_units_policy == "skip_row":
                    sys.stderr.write("WARN: %s; skipping row.\n" % msg)
                    return None
                if missing_units_policy == "error":
                    raise RuntimeError(msg)
                if missing_units_policy == "warn":
                    sys.stderr.write("WARN: %s; using mode units.\n" % msg)
        detected_unit = detected_unit_raw or mode_def.get("units") or None
        unit_conv = None
        if detected_unit_raw:
            f, detected_unit_norm, unit_conv = _apply_unit_conversion_to_field(f, detected_unit_raw, processing_mode, manifest)
            if detected_unit_norm:
                detected_unit = detected_unit_norm
            if unit_conv and stats_debug:
                _trace_append(trace, "unit_normalization", True, unit_conv)
                _trace_stats(trace, f, "after_unit_normalization")
        mask_cfg = mode_def.get("mask") if mode_def else None
        mask = None
        mask_counts = None
        pyfilter_debug = {}
        if mask_cfg:
            mask, kept, total = _build_mask(f, mask_cfg)
            if mask is not None:
                if kept == 0:
                    policy = mask_cfg.get("on_empty", "error")
                    msg = "Mask stage produced 0 included pixels for %s" % path
                    if policy == "skip_row":
                        sys.stderr.write("WARN: %s; skipping row.\n" % msg)
                        return None
                    if policy == "warn":
                        sys.stderr.write("WARN: %s; continuing.\n" % msg)
                    else:
                        raise RuntimeError(msg)
                mask_counts = (total, kept)
                if allow_debug_save:
                    try:
                        mask_field = _mask_field_from_bool(f, mask)
                        if mask_field:
                            debug_artifacts["mask"] = mask_field
                            if mask_cfg.get("gwyddion_export"):
                                out_dir = _debug_out_dir(manifest)
                                out_path = os.path.join(out_dir, "%s_mask.tiff" % os.path.splitext(os.path.basename(path))[0])
                                _save_field(out_path, mask_field)
                    except Exception:
                        pass
        py_filter_cfg = (mode_def.get("python_data_filtering") or mode_def.get("python_filtering") or {})
        base_name = os.path.splitext(os.path.basename(path))[0]
        pyfilter_export_dir = py_filter_cfg.get("export_dir") or os.path.join(_debug_out_dir(manifest), "pyfilter")
        if py_filter_cfg.get("export_raw_csv"):
            try:
                _export_field_csv(f, mask, os.path.join(pyfilter_export_dir, "%s_raw.csv" % base_name))
            except Exception as exc:
                sys.stderr.write("WARN: raw CSV export failed for %s: %s\n" % (path, exc))
        if py_filter_cfg.get("enable"):
            mask, mask_counts, pyfilter_debug = _apply_python_filters(f, mask, py_filter_cfg)
            if stats_debug and pyfilter_debug:
                _trace_append(trace, "pyfilter_summary", True, {
                    "filters": py_filter_cfg.get("filters"),
                    "kept": pyfilter_debug.get("pyfilter.n_kept"),
                    "total": pyfilter_debug.get("pyfilter.n_total"),
                    "steps": pyfilter_debug.get("_debug.pyfilter_steps"),
                })
            if py_filter_cfg.get("export_filtered_csv"):
                try:
                    _export_field_csv(f, mask, os.path.join(pyfilter_export_dir, "%s_filtered.csv" % base_name))
                except Exception as exc:
                    sys.stderr.write("WARN: filtered CSV export failed for %s: %s\n" % (path, exc))
        result = _to_mode_result(f, mode_def, mode, path, mask=mask, mask_counts=mask_counts)
        result["channel.key"] = field_id
        if field_title:
            result["channel.title"] = field_title
        if detected_unit_raw:
            result["channel.z_units"] = detected_unit_raw
            result["_debug.detected_unit_raw"] = detected_unit_raw
        elif detected_unit:
            result["channel.z_units"] = detected_unit
        if detected_unit:
            result["_debug.detected_unit"] = detected_unit
        elif mode_def.get("units"):
            result["_debug.detected_unit"] = mode_def.get("units")
        result["_debug.unit_source"] = unit_source
        if unit_conv:
            result["_debug.unit_conversion"] = unit_conv
        if raw_stats:
            result["_debug.raw_min"] = raw_stats[0]
            result["_debug.raw_max"] = raw_stats[1]
            result["_debug.raw_p5"] = raw_stats[2]
            result["_debug.raw_p50"] = raw_stats[3]
            result["_debug.raw_p95"] = raw_stats[4]
        if pyfilter_debug:
            result.update(pyfilter_debug)
        applied = _apply_units(result, processing_mode, mode_def, manifest, detected_unit)
        if stats_debug and applied is not None:
            _trace_append(trace, "stats_final", True, {
                "avg": applied.get("core.avg_value"),
                "std": applied.get("core.std_value"),
                "n_valid": applied.get("core.n_valid"),
                "units": applied.get("core.units"),
            })
            if applied.get("_debug.stats_reasons") is not None:
                _trace_append(trace, "stats_reasons", True, applied.get("_debug.stats_reasons"))
        if allow_debug_save and _debug_enabled(manifest):
            try:
                out_dir = _debug_out_dir(manifest)
                if not os.path.isdir(out_dir):
                    os.makedirs(out_dir)
                base = os.path.splitext(os.path.basename(path))[0]
                for key, df in debug_artifacts.items():
                    if df is None:
                        continue
                    out_path = os.path.join(out_dir, "%s_%s.tiff" % (base, key))
                    _save_field(out_path, df)
            except Exception as exc:
                sys.stderr.write("WARN: debug artifact save failed for %s: %s\n" % (path, exc))
        _write_trace_file(manifest, path, trace)
        return applied

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


def _to_mode_result(field, mode_def, processing_mode, src_path, mask=None, mask_counts=None):
    """Compute avg/std from a DataField."""
    global _STATS_WARNED
    global _STATS_SOURCE_WARNED
    stats_filter = mode_def.get("stats_filter") if mode_def else None
    stats_source_cfg = _normalize_stats_source(mode_def.get("stats_source") if mode_def else None)
    stats_source_used = "gwyddion"

    if stats_source_cfg == "gwyddion":
        if (mask is not None or stats_filter) and not _STATS_SOURCE_WARNED:
            sys.stderr.write("WARN: stats_source=gwyddion ignores mask/stats_filter; set stats_source=python to apply them.\n")
            _STATS_SOURCE_WARNED = True
        mean_val = _field_get_avg(field)
        std_val = _field_get_rms(field)
        vmin, vmax, n_valid, reasons = None, None, None, None
        stats_source_used = "gwyddion"
    elif stats_source_cfg == "python" or (mask is not None or stats_filter):
        if _debug_enabled(manifest_global_cfg) and (manifest_global_cfg.get("debug") or {}).get("stats_provenance"):
            mean_val, std_val, vmin, vmax, n_valid, reasons = _field_stats_masked_debug(field, mask, stats_filter or {})
        else:
            reasons = None
            mean_val, std_val, vmin, vmax, n_valid = _field_stats_masked(field, mask, stats_filter or {})
        stats_source_used = "python"
        if mask is not None or stats_filter:
            if n_valid == 0:
                policy = "error"
                if stats_filter and isinstance(stats_filter, dict):
                    policy = stats_filter.get("on_empty", "error")
                if policy == "skip_row":
                    sys.stderr.write("WARN: Stats filter removed all pixels; skipping row for %s\n" % src_path)
                    return None
                if policy == "blank":
                    sys.stderr.write("WARN: Stats filter removed all pixels; marking row blank for %s\n" % src_path)
                    mean_val = float("nan")
                    std_val = float("nan")
                elif policy == "warn":
                    sys.stderr.write("WARN: Stats filter removed all pixels; writing zeros for %s\n" % src_path)
                else:
                    raise RuntimeError("Stats filter removed all pixels for %s" % src_path)
            if not _STATS_WARNED:
                if mask is not None and stats_filter:
                    msg = "INFO: Using mask + stats_filter for summary statistics (config-driven masking). "
                elif mask is not None:
                    msg = "INFO: Using mask for summary statistics (config-driven masking). "
                else:
                    msg = "INFO: Using stats_filter for summary statistics (config-driven masking). "
                sys.stderr.write(
                    msg + "This affects avg/std values.\n"
                )
                _STATS_WARNED = True
    else:
        mean_val = _field_get_avg(field)
        std_val = _field_get_rms(field)
        vmin, vmax, n_valid, reasons = None, None, None, None
        stats_source_used = "gwyddion"

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
    out["_debug.stats_source"] = stats_source_used
    if vmin is not None:
        out["core.min_value"] = float(vmin)
    if vmax is not None:
        out["core.max_value"] = float(vmax)
    if n_valid is not None:
        out["core.n_valid"] = int(n_valid)
    if reasons:
        out["_debug.stats_reasons"] = reasons
    if mask_counts:
        total, kept = mask_counts
        out["mask.n_total"] = int(total)
        out["mask.n_kept"] = int(kept)
        if total:
            out["mask.frac_kept"] = float(kept) / float(total)
    return out


def _apply_units(result, processing_mode, mode_def, manifest, detected_unit):
    """Apply unit detection, conversion, and mismatch policy."""
    detected_unit = _normalize_unit_name(detected_unit)
    current_unit = detected_unit or _normalize_unit_name(result.get("core.units")) or _normalize_unit_name(mode_def.get("units"))
    conversions = (manifest.get("unit_conversions") or {}).get(processing_mode, {})
    conversions = _normalize_unit_conversions(conversions)
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
    global manifest_global_cfg
    manifest_global_cfg = manifest or {}
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

    dbg_cfg = _debug_cfg(manifest)

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
    global _DEBUG_SAVED
    for path in files:
        try:
            allow_debug_save = _debug_should_save(manifest)
            mode_result = process_file(path, manifest, use_pygwy, allow_debug_save=allow_debug_save)
            if mode_result is None:
                sys.stderr.write("INFO: Skipped %s due to policy.\n" % path)
                continue
            row = build_csv_row(mode_result, csv_def, processing_mode, csv_mode)
            if row is not None:
                rows.append(row)
            else:
                print("Skipped row for %s" % path)
            if allow_debug_save and _debug_enabled(manifest):
                _DEBUG_SAVED += 1
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
