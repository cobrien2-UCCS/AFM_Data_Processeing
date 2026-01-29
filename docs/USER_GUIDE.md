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
  - Config files can live anywhere; always pass `--config <path>` to the scripts.
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
  - `plane_level`, `line_correct` (Align Rows), `median_size`, `line_level_x`, `line_level_y`, `clip_percentiles`.
  - `gwyddion_ops` (optional): explicit ordered list of pygwy/Gwyddion operations (preferred for complex pipelines). See `docs/gwyddion_ops.md`.
  - `mask` (optional): apply a config-driven mask and compute stats only on masked pixels (threshold/range/percentile/outliers/outliers2; supports multi-step AND/OR combine).
  - `stats_filter` (optional): include/exclude pixel values from stats without altering the image; `on_empty: error|warn|blank|skip_row`.
  - `stats_source` (optional): `gwyddion|python` (default: `python`; controls whether avg/std come from Gwyddion or Python; see §8.1).
  - `metric_type`, `units`, `expected_units`, `on_unit_mismatch` (`error|warn|skip_row`), `on_missing_units` (`error|warn|skip_row`), `assume_units` (force a unit when the file has none).
  - `threshold` (particle mode), other mode-specific params.
- `grid`: filename regex with named groups `row`/`col` to add grid indices. Optional `index_base: 1` converts SmartScan-style `RC001001` to zero-based indices stored in the CSV.
- `summarize`: `recursive: false|true` to control recursive search for TIFFs.
- `csv_modes`: column layout and mapping from ModeResultRecord keys.
- `result_schemas`: casting rules from CSV columns to typed fields for plotting.
- `plotting_modes`: schema + recipe + labels/bins/etc.
- `profiles`: presets tying together processing_mode, csv_mode, plotting_modes.
- `unit_conversions`: per-mode unit conversions `{ source_unit: {target, factor} }` (applied to the DataField before `mask`/`stats_filter`/`python_data_filtering`, so thresholds are in normalized units).
- `input_filters` (optional): include/exclude regex filters applied during manifest generation (useful for Forward/Backward duplicates).
- `debug` (optional): enable debug logging/artifacts. Keys: `enable`, `level` (`info|debug`), `artifacts` (`mask|leveled|aligned|filtered`), `sample_limit`, `out_dir`, `log_fields` (e.g., `units|unit_conversion|mask_counts|stats_counts|stats_reasons|pyfilter|pyfilter_steps|grid|raw_stats`; units logging also includes `unit_source`), `raise_on_warn`, `echo_config`.
- If units are missing from the file, the runner falls back to mode units (e.g., kPa for modulus) and logs that as detected. When pygwy export fails, a Pillow/NumPy fallback writes debug TIFFs to `debug.out_dir`.

## 3) Adding a new processing mode
1. Add a config block under `modes` (channel_family, filters, metric_type, units, expected_units, on_unit_mismatch, etc.).
2. If behavior matches existing branches (modulus/topography filters or particle counting), no code changes needed - just config.
3. If truly new behavior is required, add a branch in `scripts/run_pygwy_job.py` APPLY_MODE_PIPELINE to implement it (use Gwyddion/pygwy ops first, Python math only as supplement).

## 4) Adding CSV/plotting rules
- New CSV layout: add a block under `csv_modes` with `columns` and `on_missing_field`.
- New result schema: add under `result_schemas` with `fields` mapping columns -> typed fields.
- New plotting mode: add under `plotting_modes` with `result_schema`, `recipe`, and labels/bins/colorbar as needed. Supported recipes now include:
  - `sample_bar_with_error`, `histogram_avg`, `scatter_avg_vs_std`, `mode_comparison_bar`
  - `heatmap_grid` (supports `value_field`: `avg_value`, `std_value`, `cv_value = std/avg`, `range_value = max-min` when min/max present)
    - Optional overlays: `overlay_std` (sigma-colored text with legend), `overlay_alpha` (alpha driven by another field), `overlay_hatch` (flag cells above/below a threshold).
  - `heatmap_grid_bubbles` (mean background + bubble overlay sized/colored by sigma bins of another field, e.g., std)
  - `heatmap_two_panel` (side-by-side heatmaps, e.g., mean vs std)
- Use `profiles` to bundle processing_mode + csv_mode + plotting_modes for easy CLI use.

## 5) Unit handling
- Runner reads field units from pygwy, applies `unit_conversions[mode]` when the detected unit matches a key (normalizing the data before masks/filters), and enforces `expected_units` with `on_unit_mismatch` (`error|warn|skip_row`).
- If a file has no unit metadata, `on_missing_units` controls whether to skip, warn + continue, or error. Use `skip_row` for strict pipelines.
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
- Recommended preprocessing order (per Gwyddion user guide):
  1) Plane level (or polynomial/facet if needed)
  2) Align Rows (line correction) for scan-line artefacts
  3) Noise filters (median/denoise)
  4) Mask creation and masked statistics

## 8.1) Masking, stats_filter, and stats_source (include/exclude)
Two different mechanisms affect summary stats:
- `mask`: builds a boolean mask over the field; only pixels where `mask[i] == True` are included in avg/std. This is a Gwyddion-first step in the Py2 runner and is intended for ROI selection (e.g., threshold/range/percentile/outliers/outliers2).
- `stats_filter`: excludes values from stats based on value rules (min/max, nonpositive, zero). This does not change the image; it only affects the computed stats.
- `stats_source`:
  - `gwyddion`: compute avg/std via Gwyddion (masked stats supported; `mask` is respected).
    - `stats_filter` / `python_data_filtering` are considered Python-side filtering and are rejected unless `allow_mixed_processing: true`.
  - `python` (default): compute avg/std via Python (mask + stats_filter are applied in Python).
    - Gwyddion-native mask methods (`outliers`, `outliers2`) are rejected unless `allow_mixed_processing: true`.

To prevent ambiguous “half Gwyddion, half Python” pipelines, the runner enforces a strict default:
- `allow_mixed_processing: false` (default) → mixed routes error (fail fast)
- `allow_mixed_processing: true` → mixed routes run with warnings and `_debug.mixed_processing*` provenance

Example mask (threshold):
```yaml
modes:
  modulus_basic:
    mask:
      enable: true
      method: "threshold"
      threshold: 0.0
      direction: "above"   # keep values >= 0
      on_empty: "error"
```

Example multi-mask with AND combine:
```yaml
modes:
  modulus_basic:
    mask:
      combine: "and"          # or "or"
      steps:
        - { method: "threshold", threshold: 0.0, direction: "above" }
        - { method: "percentile", percentiles: [5, 95] }
      on_empty: "warn"        # error|warn|blank|skip_row if no pixels survive
```

Example stats_filter (include/exclude rules):
```yaml
modes:
  modulus_basic:
    stats_filter:
      min_value: 0.0       # exclude values below 0
      max_value: 1e12      # exclude values above 1e12
      exclude_zero: true   # exclude exact zeros
      exclude_nonpositive: true
      on_empty: "warn"     # error|warn|blank|skip_row if all pixels are excluded
```

## 9) Troubleshooting
- pygwy not found: run `scripts/check_env.py --require-pygwy` under Python 2.7 and ensure `GWY_BIN` is set (or Gwyddion `bin` is on PATH).
- Row/col indices are `-1`: `grid.filename_regex` in the manifest did not match your filenames; update `config.yaml` and regenerate the manifest.
- Duplicate heatmap cells: if you have multiple files with the same `(row_idx,col_idx)`, set `plotting_modes.heatmap_grid.duplicate_policy` to `warn_mean` (default), `warn_first`, `warn_last`, or `error`. Or filter inputs using `input_filters`.
- Unit mismatch errors: set `expected_units`/`on_unit_mismatch` in mode config and `unit_conversions` if needed.
- No files found: adjust `--pattern` for `scripts/make_job_manifest.py` (e.g. `**/*.tif;**/*.tiff`).
- Missing fields in CSV: ensure mode_result provides keys required by `csv_mode` or adjust `on_missing_field`.

## 10) LLM / agent prompts
- See `docs/llm_agent_formats.md` for ready-to-use templates to add modes, CSV layouts, schemas, plotting modes, unit conversions, and pygwy mode branches. Keep changes config-driven whenever possible.
