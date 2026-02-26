# Method Comparison Study (Modulus)

This document defines why we run the method-comparison tests, what each test is doing, and where to record results. It is written as a living methods/results scaffold that you can paste into a thesis or manuscript with minimal edits.

**Purpose**
- Verify that different processing routes (Gwyddion-only vs Python stats/filtering) produce consistent, defensible modulus summaries.
- Quantify how much outlier handling changes mean/std and n_valid, and document when those changes are acceptable.
- Compare Forward vs Backward scans under identical preprocessing to check directional bias.
- Establish a reproducible baseline pipeline and highlight any method-driven deltas that should be reported.

**Scope**
- Metric: modulus only (kPa normalized via `unit_conversions`).
- Directions: Forward and Backward, analyzed separately and compared.
- Outputs: per-scan summaries, dataset-level aggregates, plots, and method comparisons.

**Test Matrix**
1. **Gwyddion preprocessing, Python stats**
   - Gwyddion ops: leveling, align rows, median/clip, optional masks.
   - Stats: computed in Python (mask + stats_filter applied in Python).
2. **Gwyddion preprocessing, Gwyddion stats**
   - Same preprocessing as (1).
   - Stats: computed in Gwyddion (mask respected).
3. **Raw export, Gwyddion-equivalent filters (Python)**
   - Export raw pixel data from pygwy.
   - Apply Python filters that mirror the Gwyddion run (e.g., min/max, zero/nonpositive).
4. **Raw export, outlier filters (Python)**
   - Export raw pixel data from pygwy.
   - Apply outlier filters (Chauvenet, 3-sigma), optionally stacked with min/max.

**Common Preprocessing**
- Plane leveling (baseline).
- Align Rows (scan-line correction).
- Optional median filter and/or percentile clipping (when configured).
- Any explicit Gwyddion ops defined in `gwyddion_ops` are applied before the branch.

**Outputs Per Test**
- `summary.csv`: per-scan stats (avg, std, n_valid, units, grid indices, file metadata).
- `plots/`: bar charts and heatmaps (linear and normalized variants).
- `aggregate_summary.csv`: pooled and scan-mean aggregates across the dataset.
- `comparison_long.csv` and `comparison_wide.csv` when using `scripts/compare_methods.py`.
- Debug artifacts when `debug.enable: true` (mask, leveled, aligned, filtered, pyfilter exports).

**Analysis Guidance (Results Section Scaffold)**
- **Mean shift vs baseline**
  - Report mean ratio and mean delta vs the chosen baseline (Gwyddion-only or raw-only).
  - Note whether shifts are within experimental tolerance.
- **Std shift and variability**
  - Compare std and coefficient of variation across methods.
  - Flag if outlier filters reduce std in a way that changes interpretation.
- **n_valid impact**
  - Count how many pixels are excluded per method (filters and masks).
  - Document the largest exclusions and whether they are expected (e.g., inclusions).
- **Forward vs Backward**
  - Compare F/B deltas across the same method.
  - Highlight directional bias if present or confirm consistency if absent.
- **Visual patterns**
  - Use heatmaps to show spatial distribution and any systematic bias.
  - Use centered normalization for "relative-to-mean" deviations and locked ranges for cross-method comparability.
- **Units and masks**
  - Confirm unit conversions and mask rules were applied consistently.
  - Note any cases where unit metadata was missing or inferred.

**Suggested Figures**
- Bar chart of per-scan mean with std error bars by method.
- Two-panel heatmaps (mean and std) for each method.
- Forward vs Backward comparison plot (mean and delta).
- Optional centered-normalization heatmap to emphasize deviations from dataset mean.

**Latest Run Summary (2026-02-23)**
- Compare outputs:
  - Forward: `out/method_compare/compare_20260223_173256/`
  - Backward: `out/method_compare/compare_20260223_173335/`
  - Forward vs Backward paired: `out/method_compare/fwd_bwd_20260223_173826/`
- Baseline: `config.modulus_gwy_stats` (Gwyddion stats after preprocessing).
- Mean ratio avg (method/baseline):
  - Forward range: ~0.910–0.950
  - Backward range: ~0.913–0.938
- n_valid change range:
  - Forward: 0 to -5060
  - Backward: 0 to -4992
- Largest |delta avg|:
  - Forward: ~-1.036e11 (GrID045, row 9, col 11)
  - Backward: ~-2.223e10 (GrID045, row 9, col 11)
- Directional conclusion: Forward and Backward follow the same ordering; Backward is slightly closer to baseline on average.
- Paired F/B medians are ~1.0 across methods (row/col matched), supporting directional consistency.

**AI Component (Methods Note)**
- AI-assisted tasks are limited to configuration scaffolding, documentation drafts, and QA checklists.
- All processing logic remains config-driven and deterministic; AI does not alter raw data or decide scientific interpretations.
- AI suggestions are reviewed and approved before use, and all runs are recorded via config + debug logs for provenance.

**Equations Used**
Notation:
- Let $x_i$ be the pixel value for the $i$th included pixel after masking and filtering.
- Let $N$ be the count of included pixels (reported as `n_valid`).
- Baseline quantities use subscript $b$, method quantities use subscript $m$.

Included pixel count:
$$
N = \sum_{i=1}^{M} \mathbf{1}\{x_i \text{ passes mask and filters}\}
$$

Mean (population):
$$
\mu = \frac{1}{N} \sum_{i=1}^{N} x_i
$$

Standard deviation (population, RMS about mean):
$$
\sigma = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (x_i - \mu)^2}
$$

Coefficient of variation (used in some plots):
$$
CV = \frac{\sigma}{\mu}
$$

Min/Max value filter (Python `min_max`):
$$
\text{keep } x_i \text{ if } \min \le x_i \le \max
$$

Three-sigma filter (Python `three_sigma`, $k=\text{sigma}$):
$$
\text{keep } x_i \text{ if } |x_i - \mu| \le k\sigma
$$

Chauvenet criterion (Python `chauvenet`, two-sided):
$$
z_i = \frac{|x_i - \mu|}{\sigma}, \quad
P_i = \operatorname{erfc}\left(\frac{z_i}{\sqrt{2}}\right)
$$
$$
\text{keep } x_i \text{ if } P_i \ge \frac{1}{2N}
$$

Delta and ratio vs baseline (per scan):
$$
\Delta \mu = \mu_m - \mu_b, \quad R_{\mu} = \frac{\mu_m}{\mu_b}
$$
$$
\Delta \sigma = \sigma_m - \sigma_b, \quad R_{\sigma} = \frac{\sigma_m}{\sigma_b}
$$
$$
\Delta N = N_m - N_b, \quad R_{N} = \frac{N_m}{N_b}
$$

Notes:
- The Python implementation uses Welford's online algorithm for $\mu$ and $\sigma$, with denominator $N$ (population std).
- Gwyddion stats use RMS about the mean, equivalent to the population standard deviation.
- Ratio values are only computed when the baseline is nonzero; otherwise the ratio field is left blank.

**Placeholders for Results**
- Baseline method chosen: `modulus_gwy_stats` (Gwyddion stats after preprocessing).
- Mean ratio range across methods: Forward ~0.910–0.950; Backward ~0.913–0.938.
- Largest delta_avg observed: Forward ~-1.036e11; Backward ~-2.223e10.
- n_valid change range: Forward 0 to -5060; Backward 0 to -4992.
- Forward vs Backward conclusion: same ordering, Backward slightly closer to baseline.
- Notes on masks/units: units normalized to kPa; mask + stats_filter rules applied consistently across methods.
