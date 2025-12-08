"""
Summarization helpers for the AFM pipeline.

Core rules from the spec:
- CSV layout comes from cfg["csv_modes"][csv_mode] (no hard-coded columns).
- Result schemas define casting from CSV rows to typed dicts.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, Any, List, Callable

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
