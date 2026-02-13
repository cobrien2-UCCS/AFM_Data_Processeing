# Modes & Options

Config-driven modes (see `modes` in `config.example.yaml`). Philosophy: use Gwyddion/pygwy for core ops; Python helpers only when needed.

## Common keys
- `channel_family`: select a data field (substring match on title/name).
- `plane_level`: apply plane leveling (Gwyddion).
- `gwyddion_ops`: ordered list of preprocessing operations (see `docs/gwyddion_ops.md`).
- `median_size`: odd int, apply median filter (Gwyddion).
- `line_correct`: Align Rows (scan-line correction) with explicit direction/method (preferred over legacy flags).
- `line_level_x` / `line_level_y`: flatten lines along X/Y (legacy flags; map to Align Rows).
- `clip_percentiles`: [low, high] optional Python-side percentile clip after filters.
- `mask`: optional ROI selection (threshold/range/percentile; supports AND/OR steps).
- `stats_filter`: optional include/exclude rules for stats (min/max/zero/nonpositive; `on_empty: error|warn|skip_row`).
- `python_data_filtering`: optional Python-side outlier/value filters and per-image CSV exports (Chauvenet, 3-sigma, min/max).
- `stats_source`: where avg/std are computed: `python` (default) or `gwyddion`.
- `allow_mixed_processing`: allow mixed routes (Gwyddion + Python filtering) for debugging only; default `false` (errors on mixed).
- `metric_type`: string stored in `core.metric_type`.
- `units`: default units; superseded by detected units when present.
- `expected_units`: enforce detected/converted units.
- `on_unit_mismatch`: `error | warn | skip_row`.
- `on_missing_units`: `error | warn | skip_row`.
- `assume_units`: explicit opt-in default unit string when TIFFs have no Z-units.

## Built-in modes
- `modulus_basic`: channel_family=modulus, plane_level=true, optional median/line/clip/mask, metric_type="modulus", units/expected_units="kPa" (conversions for MPa/GPa/Pa provided).
- `topography_flat`: channel_family=height, plane_level=true, optional median/line/clip/mask, metric_type="topography_height", units/expected_units="nm".
- `particle_count_basic`: channel_family=height, plane_level=false, threshold (default: mean), uses pygwy grain stats (count, density, equivalent diameter, optional circularity), units/expected_units="count".
- `raw_noop`: duplicate field; metric_type="raw", units="a.u.".

## Extending modes
1) Add a new block under `modes` with the keys above.
2) If behavior matches existing branches, no code change needed.
3) For new processing behavior, add a branch in `scripts/run_pygwy_job.py` APPLY_MODE_PIPELINE using pygwy ops first; only small Python math as supplement.

## Unit conversions
- Define under `unit_conversions`: per-mode map of source unit -> `{target, factor}`. Applied in the runner before unit mismatch policy. Defaults include kPa/MPa/GPa/Pa -> kPa for modulus.
