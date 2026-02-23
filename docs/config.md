# Config Schema Overview

See `config.example.yaml` for a concrete example.

## Sections
- `channel_defaults`: hints to pick channels (e.g., modulus_family, topography_family).
- `modes`: processing modes (Gwyddion-first). Common keys:
  - `channel_family`, `plane_level`, `median_size`, `line_level_x`, `line_level_y`, `clip_percentiles`
  - `line_correct` (optional): Gwyddion Align Rows settings for scan-line artefacts (`method`, `direction`, `method_id`)
  - `gwyddion_ops` (optional ordered list): e.g., `[{op: plane_level}, {op: align_rows, params: {direction: horizontal, method: median}}, {op: median, params: {size: 3}}, {op: clip_percentiles, params: {low: 0.5, high: 99.5}}]`. If absent, legacy plane_level/median/clip flags are used. See `docs/gwyddion_ops.md` for supported ops, args, and GUI equivalents.
  - `mask` (optional): config-driven mask (threshold/range/percentile/outliers/outliers2); supports multi-step `steps` with `combine: and|or`; `on_empty: error|warn|blank|skip_row`
    - `gwyddion_export: true` to write the mask as a TIFF artifact.
  - `stats_filter` (optional): exclude invalid/saturated pixels from stats (Python-side value rules); `on_empty: error|warn|blank|skip_row`
  - `python_data_filtering` (optional): post-Gwyddion value filtering + CSV export; `filters` list supports `three_sigma (sigma)`, `chauvenet`, `min_max (min_value/max_value)`; `export_raw_csv|export_filtered_csv`, `export_dir`.
    - If `export_dir` is omitted, exports go to `<output_dir>/debug/pyfilter/` when `debug.enable: true`, otherwise `<output_dir>/pyfilter/`.
    - Optional filename safety knobs: `export_basename_max_len` and `export_path_max_len` (helps avoid Windows path length errors).
    - If filtering produces 0 kept pixels, final handling is governed by `stats_filter.on_empty` (e.g., `blank`).
  - `stats_source` (optional): `gwyddion|python` (default: `python`)
    - `gwyddion`: compute avg/std via Gwyddion (masked stats are supported; `mask` is respected).
      - `stats_filter` / `python_data_filtering` are considered Python-side filtering; they are rejected unless `allow_mixed_processing: true`.
    - `python`: compute avg/std via Python (mask + stats_filter are applied in Python).
      - Gwyddion-native mask methods (`outliers`, `outliers2`) are rejected unless `allow_mixed_processing: true`.
  - `allow_mixed_processing` (optional, default `false`): allow mixed Gwyddion+Python combinations for debugging.
    - When false, the runner errors on ambiguous mixes (fail fast).
    - When true, the runner continues but emits warnings and records `_debug.mixed_processing*` fields.
  - `metric_type`, `units`, `expected_units`, `on_unit_mismatch`, `on_missing_units` (`error|warn|skip_row`), `assume_units` (optional: force a unit when the file has none)
  - mode-specific (e.g., `threshold` for particle mode)
  - `review_pack` (optional, particle mode): emit a simple human-review pack (PNG panels + `review.csv` template)
    - `enable: true|false`
    - `out_dir` (optional, default `<output_dir>/review`)
    - `image_format` (optional, default `png`)
    - `panel_basename_max_len` (optional, default `120`)
    - `csv_name` (optional, default `review.csv`)
- `grid`: `filename_regex` with named groups `row`/`col` to set grid indices. Optional `index_base` (0 or 1) converts filename indices to zero-based values stored in `grid.row_idx`/`grid.col_idx`.
- `filename_parsing` (optional): list of regex -> key maps for filename metadata (e.g., `patterns: [{ regex: "LOC_RC(?P<row>\\d{3})(?P<col>\\d{3})", map: {row: "grid.row_idx", col: "grid.col_idx"} }, ...]`). Falls back to `grid.filename_regex`.
- `summarize`: `recursive` flag for TIFF search.
- `input_filters` (optional): include/exclude regex filters applied during manifest generation (useful to exclude Forward or Backward duplicates).
- `csv_modes`: column layout mapping keys (e.g., `core.avg_value`, `grid.row_idx`) to CSV columns.
- `file.*` keys (provided by runner): best-effort filename metadata such as `file.channel`, `file.direction`, `file.grid_id`, `file.date_code` (include via `csv_modes` if needed).
- `result_schemas`: casting CSV columns to typed fields for plotting/analysis.
- `plotting_modes`: schema + recipe + labels/bins/colorbar/title. For `heatmap_grid`, `duplicate_policy` controls how duplicate (row_idx,col_idx) cells are handled.
  - Variants supported: `value_field` can be derived (`avg_value`, `std_value`, `cv_value = std/avg`, `range_value = max-min` if provided).
  - Overlays: `overlay_std` (sigma-colored text), `overlay_alpha` (alpha driven by a field), `overlay_hatch` (flag cells above/below a threshold with hatching), `overlay_bubbles` (bubble size/color by sigma bins), `overlay_std.legend: true|false`.
  - Recipes: `heatmap_grid` (base), `heatmap_grid_bubbles` (mean background + bubble overlay), `heatmap_two_panel` (side-by-side mean/std).
  - Label/unit formatting (all plot recipes):
    - `label_units_mode`: `auto|manual` (auto injects units into labels/titles).
    - `xaxis_format` / `yaxis_format` / `axis_format`: `engineering|scientific|plain`.
    - `xaxis_places` / `yaxis_places` / `axis_places`: significant places for tick formatting.
    - `axis_integer` (or `xaxis_integer`/`yaxis_integer`): force integer tick labels (useful for heatmap grid axes).
  - Bar chart labels (`sample_bar_with_error` and `mode_comparison_bar`):
    - `label_mode`: `grid_rowcol` or `rowcol` to build labels from grid indices.
    - `label_template`: string formatting with row fields (e.g., `{grid_id} R{row_idx}C{col_idx}`).
    - `label_fields`: list of fields to join; `label_join` controls separator.
  - Heatmap colorbar formatting:
    - `colorbar_format`: `engineering|scientific|plain` to format colorbar ticks.
    - `colorbar_places`: number of significant places for colorbar tick formatting.
    - Two-panel overrides: `left_colorbar_format`/`right_colorbar_format`, `left_colorbar_places`/`right_colorbar_places`.
  - Heatmap normalization:
    - `norm` (or `scale`): `linear|log|symlog|centered`.
    - `center` / `center_mode` / `center_value`: numeric or `mean|median|auto` for centered normalization.
    - `vmin` / `vmax`: explicit range override (single-panel).
    - `linthresh` / `linscale`: symlog parameters (single-panel).
  - Range locking across datasets:
    - `range_csvs` or `range_csv_glob`: list or glob of CSVs to compute a shared vmin/vmax for consistent color scales.
    - Two-panel overrides: `left_norm`/`right_norm`, `left_center`/`right_center`, `left_vmin`/`right_vmin`, `left_linthresh`/`right_linthresh`, `left_range_csvs`/`right_range_csvs`, `left_range_csv_glob`/`right_range_csv_glob`.
- `profiles`: presets tying processing_mode, csv_mode, plotting_modes.
- `aggregate_modes`: dataset-level aggregation definitions for per-scan `summary.csv` (pooled mean/std using `n_valid`, plus scan-mean stats).
  - Profiles can opt in via `profiles.<name>.aggregate_modes: [<aggregate_mode_name>, ...]`.
  - `aggregate_modes.<name>.out_relpath` controls where the aggregated CSV is written (relative to the summary CSV folder when run via `cli_aggregate_config.py`).
- `file_collect_jobs`: optional file collection/copy jobs (fuzzy keyword matching) for organizing mixed folders prior to processing.
  - Used by `scripts/collect_files.py`.
  - Required: `input_root` and `output.out_root` (or pass `--input-root`/`--out-root` on the CLI).
  - Keys: `recursive`, `patterns`, `include_keywords`, `exclude_keywords`, `include_mode (any|all)`, `min_similarity`.
  - `on_empty: error|warn|ok` controls what happens when 0 files match (default `error`).
  - Output naming: `preserve_tree` or `output.dest_subdir_template` + `output.rename_template`, plus `basename_max_len`/`path_max_len` for Windows path safety.
- `jobs`: end-to-end run definitions (collect -> manifest -> pygwy -> plots -> aggregates).
  - Required: `input_root` and `output_root` (or override via CLI).
  - Common keys: `profile`, `processing_mode`, `csv_mode`, `plotting_modes`, `aggregate_modes`, `pattern`.
  - Optional collect pre-step: `collect: { enable: true, job: "<file_collect_jobs name>", out_root: "..." }`.
  - CLI overrides (see `scripts/run_job.py`):
    - `--input-root`, `--output-root`, `--run-name`
    - `--profile`, `--processing-mode`, `--csv-mode`, `--pattern`
    - `--plotting-modes`, `--aggregate-modes`
    - `--collect-job`, `--collect-out-root`, `--no-collect`
- `unit_conversions`: per-mode unit conversions `{source: {target, factor}}`. When a conversion applies, the DataField is scaled before `mask`/`stats_filter`/`python_data_filtering`, so thresholds are interpreted in normalized units.
- `debug` (optional): diagnostics/logging/artifacts:
  - `enable` (bool), `level` (`info|debug`), `artifacts` (`["mask","leveled","aligned","filtered"]`), `sample_limit`, `out_dir`.
  - `log_fields` (e.g., `units|unit_conversion|mask_counts|stats_counts|stats_reasons|pyfilter|pyfilter_steps|grid|raw_stats`; units logging also includes `unit_source` when available), `raise_on_warn` (treat WARN as errors), `echo_config` (log active mode/csv config snippet).
  - `trace_dir` (optional): where to write per-file step traces (JSON) when debug is enabled.

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
