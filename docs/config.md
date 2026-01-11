# Config Schema Overview

See `config.example.yaml` for a concrete example.

## Sections
- `channel_defaults`: hints to pick channels (e.g., modulus_family, topography_family).
- `modes`: processing modes (Gwyddion-first). Common keys:
  - `channel_family`, `plane_level`, `median_size`, `line_level_x`, `line_level_y`, `clip_percentiles`
  - `metric_type`, `units`, `expected_units`, `on_unit_mismatch`
  - mode-specific (e.g., `threshold` for particle mode)
- `grid`: `filename_regex` with named groups `row`/`col` to set grid indices. Optional `index_base` (0 or 1) converts filename indices to zero-based values stored in `grid.row_idx`/`grid.col_idx`.
- `summarize`: `recursive` flag for TIFF search.
- `csv_modes`: column layout mapping keys (e.g., `core.avg_value`, `grid.row_idx`) to CSV columns.
- `result_schemas`: casting CSV columns to typed fields for plotting/analysis.
- `plotting_modes`: schema + recipe + labels/bins/colorbar/title.
- `profiles`: presets tying processing_mode, csv_mode, plotting_modes.
- `unit_conversions`: per-mode unit conversions `{source: {target, factor}}`.

## Patterns and recursion
- Summarize defaults: `*.tif;*.tiff` (non-recursive). Set `summarize.recursive: true` to recurse.
- Manifest patterns: `*.tif;*.tiff` by default; use `**/*.tif` etc. to recurse when generating manifests.

## Policies
- `on_unit_mismatch`: `error | warn | skip_row` (enforced in Py2 runner).
- `on_missing_field` (csv_modes): `error | warn_null | skip_row`.

## Outputs
- Summary CSV columns follow `csv_modes`.
- Plots filenames follow plotting_mode (e.g., `sample_bar_with_error.png`).
- Units propagated to CSV and used for default plot labels.
