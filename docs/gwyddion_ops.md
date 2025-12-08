# Gwyddion/pygwy Ops Cheat Sheet

Reference for the pygwy/Gwyddion functions used by the pipeline (Py2 runner).

## Leveling & filters
- Plane level (preferred): `gwy.gwy_process_func_run("level", {"data": field, "method": 0})`
- Plane level (fallback): `gwy.gwy_process_func_run("plane-level", {"data": field})`
- Median filter: `gwy.gwy_process_func_run("median", {"data": field, "size": N})` (N odd int)
- Line flatten (X): `gwy.gwy_process_func_run("level-line", {"data": field, "direction": 0})`
- Line flatten (Y): `gwy.gwy_process_func_run("level-line", {"data": field, "direction": 1})`
- Optional Python-side clipping: percentile clip after filters (config `clip_percentiles`).

## Grain / particle
- Threshold mask: duplicate field, set `1.0`/`0.0` by threshold.
- Label grains: `mask_field.number_grains()`
- Grain sizes: `mask_field.get_grain_sizes(grains)` (skip grain 0)
- Circularity: `field.grains_get_values(grains, gwy.GrainQuantity.CIRCULARITY)`

## Units
- Z units: `field.get_si_unit_z().get_unit_string()`
- Area (real units): `field.get_xreal() * field.get_yreal()`
- Grid: filename regex with named groups `row`/`col` to set `grid.row_idx`/`grid.col_idx`.
