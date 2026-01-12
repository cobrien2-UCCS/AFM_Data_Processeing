# AFM Pipeline User Guide

This guide explains how to configure and extend the AFM TIFF -> summary CSV -> plotting pipeline.

## 1) Quick start (Windows / PowerShell)
- Install Py3 dependencies: `python -m pip install -r requirements.txt`
- Run the full pipeline (Py3 -> Py2/pygwy -> Py3):
  ```powershell
  cd "<repo root>"
  .\scripts\run_pipeline.ps1 -InputRoot "C:\path\to\your\tiffs" -Profile modulus_grid -Plot
  ```
- Optional (recommended): install the Py3 package for `python -m afm_pipeline.cli ...` and `afm-plot`/`afm-summarize`:
  `python -m pip install -e .`

## 1.1) Common CLI recipes
- Check environment (Py3): `python scripts/check_env.py`
- Check pygwy environment (Py2, PowerShell example):
  `& "C:\Python27\python.exe" scripts\check_env.py --require-pygwy`
- Generate manifest (Py3):
  `python scripts/make_job_manifest.py --config config.yaml --input-root scans/ --output-dir out/ --processing-mode modulus_basic --csv-mode default_scalar --out out/job_manifest.json`
  - Patterns: defaults to `*.tif;*.tiff`. Use `--pattern "**/*.tif;**/*.tiff"` to recurse.
  - If you have Forward/Backward duplicates, set `input_filters` in config to include/exclude by filename.
- Run pygwy processing (Py2, PowerShell example):
  `& "C:\Python27\python.exe" scripts\run_pygwy_job.py --manifest out/job_manifest.json`
- Plot from CSV (Py3):
  `python scripts/cli_plot.py --config config.yaml --csv out/summary.csv --plotting-mode heatmap_grid --out out/plots/`
- Use profiles (Py3 summarize/plot): add `--profile your_profile` to pull defaults from `config.profiles`.

## 2) Config anatomy
Top-level sections (see `config.example.yaml`):
- `channel_defaults`: hints to pick channels (e.g., `modulus_family`, `topography_family`).
- `modes`: processing modes (Gwyddion-first). Keys:
  - `channel_family`: which channel to select.
  - `plane_level`, `median_size`, `line_level_x`, `line_level_y`, `clip_percentiles` (optional post-processing).
  - `metric_type`, `units`, `expected_units`, `on_unit_mismatch` (`error|warn|skip_row`).
  - `threshold` (particle mode), other mode-specific params.
- `grid`: filename regex with named groups `row`/`col` to add grid indices. Optional `index_base: 1` converts SmartScan-style `RC001001` to zero-based indices stored in the CSV.
- `summarize`: `recursive: false|true` to control recursive search for TIFFs.
- `csv_modes`: column layout and mapping from ModeResultRecord keys.
- `result_schemas`: casting rules from CSV columns to typed fields for plotting.
- `plotting_modes`: schema + recipe + labels/bins/etc.
- `profiles`: presets tying together processing_mode, csv_mode, plotting_modes.
- `unit_conversions`: per-mode unit conversions `{ source_unit: {target, factor} }`.
- `input_filters` (optional): include/exclude regex filters applied during manifest generation (useful for Forward/Backward duplicates).

## 3) Adding a new processing mode
1. Add a config block under `modes` (channel_family, filters, metric_type, units, expected_units, on_unit_mismatch, etc.).
2. If behavior matches existing branches (modulus/topography filters or particle counting), no code changes needed - just config.
3. If truly new behavior is required, add a branch in `scripts/run_pygwy_job.py` APPLY_MODE_PIPELINE to implement it (use Gwyddion/pygwy ops first, Python math only as supplement).

## 4) Adding CSV/plotting rules
- New CSV layout: add a block under `csv_modes` with `columns` and `on_missing_field`.
- New result schema: add under `result_schemas` with `fields` mapping columns -> typed fields.
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
- Forward/Backward (and other) filename metadata: the pygwy runner attaches best-effort keys like `file.channel`, `file.direction`, `file.grid_id`, `file.date_code` which you can include as CSV columns via `csv_modes`.

## 8) Notes for pygwy (Py2) processing
- Requires 32-bit Python 2.7 and 32-bit Gwyddion/pygwy on Windows.
- No fallback processing if pygwy is missing; errors are raised.
- If `import gwy` fails, set `GWY_BIN` to your Gwyddion `bin` folder (e.g. `C:\Program Files (x86)\Gwyddion\bin`).

## 9) Troubleshooting
- pygwy not found: run `scripts/check_env.py --require-pygwy` under Python 2.7 and ensure `GWY_BIN` is set (or Gwyddion `bin` is on PATH).
- Row/col indices are `-1`: `grid.filename_regex` in the manifest did not match your filenames; update `config.yaml` and regenerate the manifest.
- Duplicate heatmap cells: if you have multiple files with the same `(row_idx,col_idx)`, set `plotting_modes.heatmap_grid.duplicate_policy` to `warn_mean` (default), `warn_first`, `warn_last`, or `error`. Or filter inputs using `input_filters`.
- Unit mismatch errors: set `expected_units`/`on_unit_mismatch` in mode config and `unit_conversions` if needed.
- No files found: adjust `--pattern` for `scripts/make_job_manifest.py` (e.g. `**/*.tif;**/*.tiff`).
- Missing fields in CSV: ensure mode_result provides keys required by `csv_mode` or adjust `on_missing_field`.

## 10) LLM / agent prompts
- See `docs/llm_agent_formats.md` for ready-to-use templates to add modes, CSV layouts, schemas, plotting modes, unit conversions, and pygwy mode branches. Keep changes config-driven whenever possible.
