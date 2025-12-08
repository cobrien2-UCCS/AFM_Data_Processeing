# Modes & Options

Config-driven modes (see `modes` in `config.example.yaml`). Philosophy: use Gwyddion/pygwy for core ops; Python helpers only when needed.

## Common keys
- `channel_family`: string to select a data field (name contains this substring).
- `plane_level`: bool, apply plane leveling (Gwyddion module).
- `median_size`: odd int, apply median filter (Gwyddion).
- `line_level_x` / `line_level_y`: flatten lines along X/Y (Gwyddion).
- `clip_percentiles`: [low, high] optional Python-side percentile clip after filters.
- `metric_type`: string stored in `core.metric_type`.
- `units`: default units; superseded by detected units when present.
- `expected_units`: enforce detected/converted units.
- `on_unit_mismatch`: `error | warn | skip_row`.

## Built-in modes
- `modulus_basic`: channel_family=modulus, plane_level=true, optional median/line/clip, metric_type="modulus", units/expected_units="GPa".
- `topography_flat`: channel_family=height, plane_level=true, optional median/line/clip, metric_type="topography_height", units/expected_units="nm".
- `particle_count_basic`: channel_family=height, plane_level=false, threshold (default: mean), uses pygwy grain stats (count, density, equivalent diameter, optional circularity), units/expected_units="count".
- `raw_noop`: duplicate field; metric_type="raw", units="a.u.".

## Extending modes
1) Add a new block under `modes` with the keys above.
2) If behavior matches existing branches, no code change needed.
3) For new processing behavior, add a branch in `scripts/run_pygwy_job.py` APPLY_MODE_PIPELINE using pygwy ops first; only small Python math as supplement.

## Unit conversions
- Define under `unit_conversions`: per-mode map of source unit → `{target, factor}`. Applied in the runner before unit mismatch policy.
