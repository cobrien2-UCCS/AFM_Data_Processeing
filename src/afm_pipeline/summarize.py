"""
Summarization helpers for the AFM pipeline.

Core rules from the spec:
- CSV layout comes from cfg["csv_modes"][csv_mode] (no hard-coded columns).
- Result schemas define casting from CSV rows to typed dicts.
"""

import csv
import logging
from typing import Dict, Any, List

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
