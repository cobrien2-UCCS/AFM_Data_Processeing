"""
Summarization helpers for the AFM pipeline.

Core rules from the spec:
- CSV layout comes from cfg["csv_modes"][csv_mode] (no hard-coded columns).
- Result schemas define casting from CSV rows to typed dicts.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, Any, List, Callable, Iterable, Tuple, Optional

log = logging.getLogger(__name__)


def load_csv_table(csv_path: str) -> List[Dict[str, str]]:
    """Read a CSV into a list of dictionaries."""
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def build_result_object_from_csv_row(row: Dict[str, str], schema_name: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Cast a CSV row into a typed dict per result_schemas."""
    schemas = cfg.get("result_schemas", {})
    if schema_name not in schemas:
        raise ValueError(f"Unknown result schema: {schema_name}")
    schema_def = schemas[schema_name]
    fields = schema_def.get("fields", [])
    obj: Dict[str, Any] = {}
    for field_def in fields:
        field = field_def["field"]
        col = field_def["column"]
        typ = field_def.get("type", "string")
        raw_val = row.get(col)
        obj[field] = _cast_value(raw_val, typ)
    return obj


def _cast_value(val: str | None, typ: str):
    if val is None:
        return None
    if typ == "int":
        try:
            return int(val)
        except ValueError:
            return None
    if typ == "float":
        try:
            return float(val)
        except ValueError:
            return None
    return val


def build_csv_row(mode_result: Dict[str, Any], csv_def: Dict[str, Any], processing_mode: str, csv_mode: str):
    """
    Map a mode_result dict into CSV row values per csv_def.columns.

    csv_def.on_missing_field behavior:
    - "warn_null": insert empty string, log warning
    - "error": raise
    - "skip_row": return None
    """
    columns = csv_def.get("columns", [])
    on_missing = csv_def.get("on_missing_field", "warn_null")
    row_values: List[Any] = []

    for col_def in columns:
        key = col_def.get("from")
        default = col_def.get("default", "")
        if key in mode_result:
            row_values.append(mode_result[key])
            continue
        if default != "":
            row_values.append(default)
            continue
        if on_missing == "error":
            raise KeyError(f"Missing field '{key}' for csv_mode={csv_mode}, processing_mode={processing_mode}")
        if on_missing == "skip_row":
            log.warning("Skipping row: missing field '%s' for mode=%s csv_mode=%s", key, processing_mode, csv_mode)
            return None
        # warn_null
        log.warning("Missing field '%s' for mode=%s csv_mode=%s; writing empty", key, processing_mode, csv_mode)
        row_values.append("")

    return row_values


def summarize_folder_to_csv(
    input_root: str | Path,
    output_csv_path: str | Path,
    processing_mode: str,
    csv_mode: str,
    cfg: Dict[str, Any],
    processor: Callable[[Path, str, Dict[str, Any]], Dict[str, Any]] | None = None,
) -> None:
    """
    Walk a folder of TIFFs, process each with processing_mode, map to CSV via csv_mode.

    processor: injectable function for processing a single TIFF; defaults to processing.process_tiff_with_gwyddion.
    """
    from . import processing as processing_mod

    proc_fn = processor or processing_mod.process_tiff_with_gwyddion

    csv_def = cfg.get("csv_modes", {}).get(csv_mode)
    if not csv_def:
        raise ValueError(f"Unknown csv_mode: {csv_mode}")

    input_root = Path(input_root)
    # Search patterns: both .tif and .tiff; optional recursion via cfg["summarize"].get("recursive")
    recursive = cfg.get("summarize", {}).get("recursive", False)
    patterns = ["*.tif", "*.tiff"]
    tiff_files: list[Path] = []
    for pat in patterns:
        if recursive:
            tiff_files.extend(input_root.rglob(pat))
        else:
            tiff_files.extend(input_root.glob(pat))
    tiff_files = sorted({p.resolve() for p in tiff_files})
    if not tiff_files:
        log.warning("No TIFF files found in %s", input_root)

    out_path = Path(output_csv_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    header_cols = [col["name"] for col in csv_def.get("columns", [])]
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header_cols)

        for path in tiff_files:
            try:
                mode_result = proc_fn(path, processing_mode, cfg)
                row = build_csv_row(mode_result, csv_def, processing_mode, csv_mode)
                if row is None:
                    continue
                writer.writerow(row)
            except Exception as exc:  # keep looping other files
                log.error("Failed processing %s: %s", path, exc)


def _to_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        x = float(s)
    except ValueError:
        return None
    if not (x == x):  # NaN
        return None
    return x


def _to_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def aggregate_summary_table(
    rows: List[Dict[str, str]],
    *,
    value_col: str = "avg_value",
    std_col: str = "std_value",
    n_col: str = "n_valid",
    units_col: str = "units",
    group_by: Optional[List[str]] = None,
    allow_mixed_units: bool = False,
) -> List[Dict[str, Any]]:
    """
    Aggregate per-scan mean/std into dataset-level (or group-level) mean/std.

    This is designed for summary.csv outputs that already contain per-image:
    - avg_value (mean)
    - std_value (population std; matches runner behavior)
    - n_valid (number of included pixels)

    Output fields (per group):
    - n_scans: number of rows/scans aggregated
    - n_valid_total: sum of n_valid over included scans (pooled stats)
    - avg_value_pooled, std_value_pooled: pooled mean/std over all pixels (requires n_valid + std)
    - avg_value_scan_mean, std_value_scan_mean: mean/std across scan means (unweighted; ignores n_valid)

    Notes:
    - Pooled std is computed as population std:
      Var = sum_i n_i * (std_i^2 + (mu_i - mu)^2) / N
    - Rows missing value_col are skipped for both pooled and scan-mean aggregates.
    - Rows missing n_col or std_col are excluded from pooled stats but still contribute to scan-mean stats.
    """
    group_by = group_by or []

    buckets: Dict[Tuple[str, ...], List[Dict[str, str]]] = {}
    for r in rows:
        key = tuple((r.get(col) or "").strip() for col in group_by)
        buckets.setdefault(key, []).append(r)

    out: List[Dict[str, Any]] = []
    for key, rs in buckets.items():
        # Units policy: either enforce single unit per group, or allow.
        units_seen = {str((r.get(units_col) or "")).strip() for r in rs if (r.get(units_col) or "").strip()}
        units_val = ""
        if units_seen:
            if len(units_seen) == 1:
                units_val = next(iter(units_seen))
            elif allow_mixed_units:
                units_val = "MIXED"
            else:
                raise ValueError(
                    f"Mixed units in group {key}: {sorted(units_seen)}. "
                    f"Group by '{units_col}' or pass allow_mixed_units=True."
                )

        # Scan-mean aggregates (unweighted).
        scan_means: List[float] = []
        for r in rs:
            mu = _to_float(r.get(value_col))
            if mu is None:
                continue
            scan_means.append(mu)

        if scan_means:
            mean_scan_mean = sum(scan_means) / float(len(scan_means))
            # Population std across scan means (consistent with runner's std convention).
            var_scan_mean = sum((m - mean_scan_mean) ** 2 for m in scan_means) / float(len(scan_means))
            std_scan_mean = var_scan_mean ** 0.5
        else:
            mean_scan_mean = None
            std_scan_mean = None

        # Pooled aggregates across pixels (weighted by n_valid).
        pooled_parts: List[Tuple[int, float, float]] = []
        # tuples of (n, mu, std)
        for r in rs:
            mu = _to_float(r.get(value_col))
            if mu is None:
                continue
            n = _to_int(r.get(n_col))
            sd = _to_float(r.get(std_col))
            if n is None or n <= 0 or sd is None:
                continue
            pooled_parts.append((n, mu, sd))

        if pooled_parts:
            n_total = sum(n for n, _, _ in pooled_parts)
            mu_total = sum(n * mu for n, mu, _ in pooled_parts) / float(n_total)
            var_total = (
                sum(n * ((sd ** 2) + ((mu - mu_total) ** 2)) for n, mu, sd in pooled_parts) / float(n_total)
            )
            sd_total = var_total ** 0.5
        else:
            n_total = 0
            mu_total = None
            sd_total = None

        rec: Dict[str, Any] = {}
        for i, col in enumerate(group_by):
            rec[col] = key[i]
        if units_col and units_col not in rec:
            rec[units_col] = units_val
        rec["n_scans"] = int(len(rs))
        rec["n_scans_with_mean"] = int(len(scan_means))
        rec["n_scans_with_pooled"] = int(len(pooled_parts))
        rec["n_valid_total"] = int(n_total)
        rec["avg_value_pooled"] = mu_total
        rec["std_value_pooled"] = sd_total
        rec["avg_value_scan_mean"] = mean_scan_mean
        rec["std_value_scan_mean"] = std_scan_mean
        out.append(rec)

    return out


def write_aggregated_csv(out_csv: str | Path, rows: Iterable[Dict[str, Any]]) -> None:
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = list(rows)
    if not rows:
        raise ValueError("No rows to write.")

    # Deterministic field order: group keys first, then known metrics, then extras.
    preferred = [
        "units",
        "n_scans",
        "n_scans_with_mean",
        "n_scans_with_pooled",
        "n_valid_total",
        "avg_value_pooled",
        "std_value_pooled",
        "avg_value_scan_mean",
        "std_value_scan_mean",
    ]
    fieldnames = []
    for k in rows[0].keys():
        if k not in preferred:
            fieldnames.append(k)
    fieldnames += [k for k in preferred if k in rows[0]]

    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
