# LLM / Agent Formats (Prompts and Templates)

Use these templates to add or modify config-driven behavior without altering core code. Focus changes on `modes`, `csv_modes`, `result_schemas`, `plotting_modes`, `unit_conversions`, and optional new mode branches in the pygwy runner.

## Add a processing mode (config-only)
```
Add to modes:
  <mode_name>:
    channel_family: "<channel_hint>"
    plane_level: true|false
    gwyddion_ops: []              # ordered ops; see docs/gwyddion_ops.md
    median_size: <odd_int|null>
    line_level_x: true|false
    line_level_y: true|false
    clip_percentiles: [low, high] | null
    stats_source: "python|gwyddion"
    allow_mixed_processing: true|false
    # Optional python_data_filtering: post-stats value filters + per-image CSV exports.
    # python_data_filtering:
    #   enable: true
    #   export_raw_csv: true
    #   export_filtered_csv: true
    #   export_dir: "<optional override>"
    #   export_basename_max_len: 80
    #   export_path_max_len: 220
    #   on_empty: "warn|skip_row|error"
    #   filters:
    #     - { type: "three_sigma", sigma: 3.0 }
    #     - { type: "chauvenet" }
    #     - { type: "min_max", min_value: 1.0, max_value: 1e9 }
    metric_type: "<metric>"
    units: "<unit>"
    expected_units: "<unit>"
    on_unit_mismatch: "error|warn|skip_row"
    on_missing_units: "error|warn|skip_row"
    assume_units: "<unit>"        # explicit opt-in when TIFF Z-units are missing
    threshold: <num|null>  # if particle mode
```
If behavior matches existing branches (modulus/topography filters or particle counting), no code change is needed.

## Add CSV layout and schema
```
Add to csv_modes:
  <csv_mode>:
    columns:
      - { name: "<col_name>", from: "<key_path>", default: <opt> }
    on_missing_field: "error|warn_null|skip_row"

Add to result_schemas:
  <schema_name>:
    from_csv_mode: "<csv_mode>"
    fields:
      - { field: "<field_name>", type: "string|int|float", column: "<col_name>" }
```

## Add a plotting mode
```
Add to plotting_modes:
  <plot_mode>:
    result_schema: "<schema>"
    recipe: "sample_bar_with_error|histogram_avg|scatter_avg_vs_std|mode_comparison_bar|heatmap_grid|heatmap_grid_bubbles|heatmap_two_panel"
    title: "..."
    xlabel/ylabel/colorbar_label: "..."   # optional, defaults include units
    bins/point_size/alpha/cmap/show_colorbar: <as needed>
```

## Add unit conversions
```
Add to unit_conversions:
  <mode_name>:
    <source_unit>:
      target: "<target_unit>"
      factor: <multiplier>
```

## Add a new pygwy processing branch (code change)
Request a branch in `scripts/run_pygwy_job.py` APPLY_MODE_PIPELINE with:
- Gwyddion/pygwy ops for leveling/filtering/grain stats.
- Optional Python-side math only if Gwyddion lacks the function.
- Honor units: detect, convert via `unit_conversions`, enforce `expected_units`/`on_unit_mismatch`.

Prompt template:
```
Implement a new mode "<mode_name>" in scripts/run_pygwy_job.py:
- channel_family: "<hint>"
- steps: [describe filters/ops]
- outputs: keys added to ModeResultRecord
- units: <unit>, expected_units: <unit>, on_unit_mismatch: <policy>
```

## General guardrails for LLM/agents
- Do not hard-code CSV columns or plotting field positions; use config.
- Do not add new global state; keep behavior in config or mode branches.
- Prefer Gwyddion/pygwy ops; use Python helpers only when necessary.
- Preserve function signatures described in the spec.

## Compare outputs across methods (script)
Use `scripts/compare_methods.py` to compare multiple `summary.csv` outputs against a baseline.

Template:
```
py -3 scripts/compare_methods.py --baseline-summary <baseline_summary.csv> --methods-root <root_of_runs> --out-root out/method_compare --label-max-len 45
```
This writes `comparison_wide.csv`, `comparison_long.csv`, and quick plots under `out/method_compare/compare_<timestamp>/plots/`.
