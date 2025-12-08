"""AFM pipeline package scaffold.

This package follows the architecture defined in:
- AFM TIFF -> ModeResultRecord -> CSV (csv_modes) -> result_schemas -> plotting_modes

Only minimal scaffolding lives here; processing/plotting logic will be filled in subsequent steps.
"""

from .config import load_config
from .summarize import (
    build_csv_row,
    build_result_object_from_csv_row,
    load_csv_table,
    summarize_folder_to_csv,
)
from .plotting import plot_summary_from_csv, APPLY_PLOTTING_MODE
from . import processing

__all__ = [
    "load_config",
    "build_csv_row",
    "build_result_object_from_csv_row",
    "summarize_folder_to_csv",
    "load_csv_table",
    "plot_summary_from_csv",
    "APPLY_PLOTTING_MODE",
    "processing",
]
