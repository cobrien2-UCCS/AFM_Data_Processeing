# AFM Pipeline User Guide

This guide explains how to configure and extend the AFM TIFF → summary CSV → plotting pipeline.

## 1) Quick start
- Author `config.yaml` using the structures below.
- Py3 summarize: `python -m afm_pipeline.cli summarize --config config.yaml --input-root scans/ --out-csv summary.csv --processing-mode modulus_basic --csv-mode default_scalar`
- Py3 plot: `python -m afm_pipeline.cli plot --config config.yaml --csv summary.csv --plotting-mode sample_bar_with_error --out plots/`
- Py2 (pygwy) processing: `python2 scripts/run_pygwy_job.py --manifest job_manifest.json` (manifest generated via `scripts/make_job_manifest.py`).

## 2) Config anatomy
Top-level sections (see `config.example.yaml`):
- `channel_defaults`: hints to pick channels (e.g., `modulus_family`, `topography_family`).
- `modes`: processing modes (Gwyddion-first). Keys:
  - `channel_family`: which channel to select.
  - `plane_level`, `median_size`, `line_level_x`, `line_level_y`, `clip_percentiles` (optional post-processing).
  - `metric_type`, `units`, `expected_units`, `on_unit_mismatch` (`error|warn|skip_row`).
  - `threshold` (particle mode), other mode-specific params.
- `grid`: filename regex with named groups `row`/`col` to add grid indices.
- `summarize`: `recursive: false|true` to control recursive search for TIFFs.
- `csv_modes`: column layout and mapping from ModeResultRecord keys.
- `result_schemas`: casting rules from CSV columns to typed fields for plotting.
- `plotting_modes`: schema + recipe + labels/bins/etc.
- `profiles`: presets tying together processing_mode, csv_mode, plotting_modes.
- `unit_conversions`: per-mode unit conversions `{ source_unit: {target, factor} }`.

## 3) Adding a new processing mode
1. Add a config block under `modes` (channel_family, filters, metric_type, units, expected_units, on_unit_mismatch, etc.).
2. If behavior matches existing branches (modulus/topography filters or particle counting), no code changes needed—just config.
3. If truly new behavior is required, add a branch in `scripts/run_pygwy_job.py` APPLY_MODE_PIPELINE to implement it (use Gwyddion/pygwy ops first, Python math only as supplement).

## 4) Adding CSV/plotting rules
- New CSV layout: add a block under `csv_modes` with `columns` and `on_missing_field`.
- New result schema: add under `result_schemas` with `fields` mapping columns → typed fields.
- New plotting mode: add under `plotting_modes` with `result_schema`, `recipe` (e.g., `sample_bar_with_error`, `histogram_avg`, `scatter_avg_vs_std`, `mode_comparison_bar`, `heatmap_grid`), plus labels/bins/colorbar as needed.
- Use `profiles` to bundle processing_mode + csv_mode + plotting_modes for easy CLI use.

## 5) Unit handling
- Runner reads field units from pygwy, applies `unit_conversions[mode]` when the detected unit matches a key, and enforces `expected_units` with `on_unit_mismatch` (`error|warn|skip_row`).
- Include `units` column in CSV modes so plots can infer axis labels.

## 6) Patterns and recursion
- Summarize default patterns: `*.tif`, `*.tiff` (non-recursive).
- Set `summarize.recursive: true` to recurse for summarize.
- Manifest generator accepts patterns like `*.tif;*.tiff` (default) or `**/*.tif` to recurse on the Py2 runner side.

## 7) Expected outputs
- Summary CSV columns follow the chosen `csv_mode` definition.
- Plots are written to the specified output directory with filenames = plotting_mode names (`sample_bar_with_error.png`, `heatmap_grid.png`, etc.).
- pygwy runner writes `summary.csv` (or `--output-csv`) and enforces unit policies.

## 8) Notes for pygwy (Py2) processing
- Requires 32-bit Python 2.7 with PyGTK2 and pygwy/Gwyddion installed.
- No fallback processing if pygwy is missing; errors are raised.
- Particle metrics use pygwy grain tools; plane/median/line filters use Gwyddion modules; clipping is optional Python-side.

