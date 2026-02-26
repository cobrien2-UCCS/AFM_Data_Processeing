# Method Comparison Notes (2026-02-23)

This summarizes the forward/backward comparisons for the full modulus dataset (PEGDA1TPO00SiNP_Sam01_S1).

- Forward compare outputs: `out/method_compare/compare_20260223_173256/`
- Backward compare outputs: `out/method_compare/compare_20260223_173335/`
- Forward vs Backward paired summary: `out/method_compare/fwd_bwd_20260223_173826/`
- Baseline: `config.modulus_gwy_stats` (Gwyddion stats after Gwyddion preprocessing).
- Methods compared:
  - `gwy_ops_py_stats` (Gwyddion preprocessing, Python stats)
  - `raw_minmax` (raw export + Python min/max filter)
  - `raw_chauvenet` (raw export + Chauvenet)
  - `raw_three_sigma` (raw export + 3-sigma)
- Dataset: 107 scans per direction (Forward and Backward).

Key findings (mean ratio avg_value vs baseline):
- **Forward**: `gwy_ops_py_stats/raw_minmax ≈ 0.910`, `raw_chauvenet ≈ 0.944`, `raw_three_sigma ≈ 0.950`.
- **Backward**: `gwy_ops_py_stats/raw_minmax ≈ 0.913`, `raw_chauvenet ≈ 0.936`, `raw_three_sigma ≈ 0.938`.
- **n_valid impact**:
  - `gwy_ops_py_stats/raw_minmax`: no change in n_valid.
  - `raw_chauvenet`: mean delta ≈ -490 (min -2447) forward; mean delta ≈ -467 (min -2466) backward.
  - `raw_three_sigma`: mean delta ≈ -1189 (min -5060) forward; mean delta ≈ -1142 (min -4992) backward.
- **Largest |delta avg|**:
  - Forward: ~`-1.036e11` at GrID045 (row 9, col 11).
  - Backward: ~`-2.223e10` at GrID045 (row 9, col 11).

Takeaways:
- The ordering is consistent across directions: raw outlier filters reduce mean values less than the Gwyddion-vs-Python stats shift.
- Forward and Backward trends are similar; Backward is slightly closer to baseline on average.
- Baseline averages are heavily skewed by outliers (mean >> median), so medians are better for “typical” comparisons.
- Paired forward/backward medians are ~1.0 across methods (row/col matched), indicating directional consistency when matching tiles.

---

# Method Comparison Notes (2026-02-13)

This summarizes the `compare_methods.py` run that contrasted the Gwyddion-only baseline against Python-filter variants on the PEGDA modulus set.

- Command: `py -3 scripts/compare_methods.py --baseline-summary out/verify_raw_trunc_gwyddion_only/config.modulus_gwyddion_only/summary.csv --methods-root out/verify_raw_trunc_less_tuned --out-root out/method_compare --label-max-len 45`
- Outputs: `out/method_compare/compare_20260213_150349/comparison_wide.csv`, `comparison_long.csv`, plots in `.../plots/`.
- Baseline: `modulus_gwy_only` (Gwyddion stats, mask 1..1e9 kPa, no Python filtering).
- Methods compared (all stats_source=python):
  - `modulus_export_raw_only` (no Python filters, exports only)
  - `modulus_export_minmax` (value window 1..1e9 kPa)
  - `modulus_export_three_sigma`
  - `modulus_export_chauvenet`
  - `modulus_export_combo` (three_sigma + chauvenet + min_max)
- Dataset: 7 samples (grid TIFFs from the PEGDA run).

Key findings (vs baseline avg_value):
- Mean ratio of method/baseline avg_value:
  - raw_only, minmax: ~0.986
  - chauvenet: ~0.981
  - three_sigma: ~0.976
  - combo: ~0.973
- Largest observed delta_avg was negative (filters lowered means), as large as ~-2.2e7 in the worst single tile; medians were much smaller (e.g., -2.3e6 to -3.2e6).
- n_valid impact:
  - raw_only, minmax: no change in n_valid vs baseline.
  - chauvenet: up to 45 pixels removed in a tile.
  - three_sigma: up to 161 pixels removed.
  - combo: up to 622 pixels removed.

Takeaways:
- Outlier-style Python filters change means only a few percent on average for this set; the biggest drops come from the combo stack.
- If provenance clarity is critical, stick to `modulus_gwy_only` or `raw_only/minmax` (no n_valid changes). Use the filtered variants when you explicitly want reproducible outlier removal; set `allow_mixed_processing: true` if mixing with Gwyddion stats.
- For future runs, shorten exported basenames (`python_data_filtering.export_basename_max_len`) if path length is a concern.

## Addendum: Plot Normalization Options
To make cross-method plots visually comparable, the plotting system now supports:
- `norm: log` or `norm: symlog` for wide-range data.
- `norm: centered` with `center: mean|median|auto` to visualize deviation from the dataset mean.
- `range_csvs` / `range_csv_glob` to lock vmin/vmax across multiple `summary.csv` files.

Typical usage for cross-method comparison:
1. Pick a baseline `summary.csv` or a folder of summaries.
2. Set `range_csv_glob: "../*/summary.csv"` so all runs share the same color scale.
3. Use `heatmap_two_panel` with `left_norm` and `right_norm` if you want different normalization for mean vs std.
