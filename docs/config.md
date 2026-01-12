# Config Schema Overview

See `config.example.yaml` for a concrete example.

## Sections
- `channel_defaults`: hints to pick channels (e.g., modulus_family, topography_family).
- `modes`: processing modes (Gwyddion-first). Common keys:
  - `channel_family`, `plane_level`, `median_size`, `line_level_x`, `line_level_y`, `clip_percentiles`
  - `line_correct` (optional): Gwyddion Align Rows settings for scan-line artefacts (`method`, `direction`, `method_id`)
  - `mask` (optional): config-driven mask (threshold/range/percentile); supports multi-step `steps` with `combine: and|or`; `on_empty: error|warn|skip_row`
  - `stats_filter` (optional): exclude invalid/saturated pixels from stats (Python-side value rules); `on_empty: error|warn|skip_row`
  - `metric_type`, `units`, `expected_units`, `on_unit_mismatch`
  - mode-specific (e.g., `threshold` for particle mode)
- `grid`: `filename_regex` with named groups `row`/`col` to set grid indices. Optional `index_base` (0 or 1) converts filename indices to zero-based values stored in `grid.row_idx`/`grid.col_idx`.
- `summarize`: `recursive` flag for TIFF search.
- `input_filters` (optional): include/exclude regex filters applied during manifest generation (useful to exclude Forward or Backward duplicates).
- `csv_modes`: column layout mapping keys (e.g., `core.avg_value`, `grid.row_idx`) to CSV columns.
- `file.*` keys (provided by runner): best-effort filename metadata such as `file.channel`, `file.direction`, `file.grid_id`, `file.date_code` (include via `csv_modes` if needed).
- `result_schemas`: casting CSV columns to typed fields for plotting/analysis.
- `plotting_modes`: schema + recipe + labels/bins/colorbar/title. For `heatmap_grid`, `duplicate_policy` controls how duplicate (row_idx,col_idx) cells are handled.
- `profiles`: presets tying processing_mode, csv_mode, plotting_modes.
- `unit_conversions`: per-mode unit conversions `{source: {target, factor}}`.
- `debug` (optional): diagnostics/logging/artifacts:
  - `enable` (bool), `level` (`info|debug`), `artifacts` (`["mask","leveled","aligned","filtered"]`), `sample_limit`, `out_dir`.
  - `log_fields` (`units|mask_counts|stats_counts`), `raise_on_warn` (treat WARN as errors), `echo_config` (log active mode/csv config snippet).

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
