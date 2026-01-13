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
    """Save a DataField to a file via gwy file save."""
    # Ensure output directory exists
    out_dir = os.path.dirname(path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    saved = False
    # First try pygwy export
    try:
        import gwy  # type: ignore
    except Exception as exc:
        sys.stderr.write("WARN: debug save skipped pygwy (cannot import gwy): %s\n" % exc)
    else:
        try:
            container = None
            if hasattr(gwy, "gwy_container_new"):
                container = gwy.gwy_container_new()
            elif hasattr(gwy, "Container"):
                container = gwy.Container()
            if container is None:
                raise AttributeError("gwy container constructor not available")
            container.set_object_by_name("/0/data", field)
            try:
                container.set_string_by_name("/0/data/title", os.path.basename(path))
            except Exception:
                pass
            gwy.gwy_file_save(container, path)
            saved = True
        except Exception as exc:
            sys.stderr.write("WARN: debug save failed for %s (pygwy): %s\n" % (path, exc))

    # Always attempt Pillow/NumPy fallback to guarantee an artifact
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


def _debug_log_fields(manifest):
    dbg = _debug_cfg(manifest)
    fields = dbg.get("log_fields") or []
    if isinstance(fields, str):
        fields = [fields]
    return set([str(f).strip().lower() for f in fields if f])


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


def process_file(path, manifest, use_pygwy, allow_debug_save=False):
    mode_def = manifest.get("mode_definition", {}) or {}
    grid_cfg = manifest.get("grid", {}) or {}
    channel_defaults = manifest.get("channel_defaults", {}) or {}
    processing_mode = manifest.get("processing_mode")
    row_idx, col_idx = derive_grid_indices(path, grid_cfg)

    if not use_pygwy:
        raise RuntimeError("pygwy required for processing; no fallback is executed.")
    result = _process_with_pygwy(path, processing_mode, mode_def, channel_defaults, manifest, allow_debug_save=allow_debug_save)
    if result is None:
        return None

    result.update(_parse_filename_basic_metadata(path))

    if row_idx is not None:
        result["grid.row_idx"] = row_idx
    if col_idx is not None:
        result["grid.col_idx"] = col_idx

    if _debug_enabled(manifest):
        lvl = _debug_level(manifest)
        log_fields = _debug_log_fields(manifest)
        # Default fields if none specified
        if not log_fields:
            log_fields = set(["units", "mask_counts", "stats_counts", "grid", "raw_stats"])
        detected_unit = result.get("_debug.detected_unit")
        final_unit = result.get("core.units")
        parts = ["[DEBUG] %s" % os.path.basename(path)]
        if "units" in log_fields:
            parts.append("unit=%s" % (detected_unit or "n/a"))
            if detected_unit and final_unit and detected_unit != final_unit:
                parts.append("->%s" % final_unit)
        if "stats_counts" in log_fields and "core.n_valid" in result:
            parts.append("n_valid=%s" % result.get("core.n_valid"))
        if "mask_counts" in log_fields and "mask.n_kept" in result and "mask.n_total" in result:
            parts.append("mask=%s/%s" % (result.get("mask.n_kept"), result.get("mask.n_total")))
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

    if mode in ("modulus_basic", "topography_flat"):
        f = field.duplicate()
        raw_stats = _quick_stats(f)
        if mode_def.get("plane_level", True):
            try:
                pa, pbx, pby = f.fit_plane()
                f.plane_level(pa, pbx, pby)
                if allow_debug_save:
                    debug_artifacts["leveled"] = f.duplicate()
            except Exception as exc:
                sys.stderr.write("WARN: plane_level failed for %s: %s\n" % (path, exc))
        median_size = mode_def.get("median_size")
        if median_size:
            try:
                f.filter_median(int(median_size))
                if allow_debug_save:
                    debug_artifacts["filtered"] = f.duplicate()
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
                if allow_debug_save:
                    debug_artifacts["filtered"] = f.duplicate()
            except Exception as exc:
                sys.stderr.write("WARN: clip_percentiles failed for %s: %s\n" % (path, exc))
        mask_cfg = mode_def.get("mask") if mode_def else None
        mask = None
        mask_counts = None
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
                    except Exception:
                        pass
        detected_unit = _get_field_units(f)
        if not detected_unit:
            detected_unit = mode_def.get("units") or None
        result = _to_mode_result(f, mode_def, mode, path, mask=mask, mask_counts=mask_counts)
        result["channel.key"] = field_id
        if field_title:
            result["channel.title"] = field_title
        if detected_unit:
            result["channel.z_units"] = detected_unit
            result["_debug.detected_unit"] = detected_unit
        elif mode_def.get("units"):
            result["_debug.detected_unit"] = mode_def.get("units")
        if raw_stats:
            result["_debug.raw_min"] = raw_stats[0]
            result["_debug.raw_max"] = raw_stats[1]
            result["_debug.raw_p5"] = raw_stats[2]
            result["_debug.raw_p50"] = raw_stats[3]
            result["_debug.raw_p95"] = raw_stats[4]
        applied = _apply_units(result, processing_mode, mode_def, manifest, detected_unit)
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
    stats_filter = mode_def.get("stats_filter") if mode_def else None
    if mask is not None or stats_filter:
        mean_val, std_val, vmin, vmax, n_valid = _field_stats_masked(field, mask, stats_filter or {})
        if n_valid == 0:
            policy = "error"
            if stats_filter and isinstance(stats_filter, dict):
                policy = stats_filter.get("on_empty", "error")
            if policy == "skip_row":
                sys.stderr.write("WARN: Stats filter removed all pixels; skipping row for %s\n" % src_path)
                return None
            if policy == "warn":
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
    if mask_counts:
        total, kept = mask_counts
        out["mask.n_total"] = int(total)
        out["mask.n_kept"] = int(kept)
        if total:
            out["mask.frac_kept"] = float(kept) / float(total)
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
                sys.stderr.write("INFO: Skipped %s due to unit mismatch policy.\n" % path)
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
