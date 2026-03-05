# Topography Particle Deliverables (Final Working File)

This file aggregates the deliverable template plus the current test matrix. The original template remains unchanged.

# Topography Particle Deliverables Template

Use this template to assemble the final Word document. Fill in values from the pipeline outputs.

## Summary
- Dataset scope: PEGDA and PEGDA-SiNP (forward scans only)
- Scan size: 5 um x 5 um
- Pixel grid: 512 x 512
- Lateral resolution: 9.7656 nm/px
- Map/grid area: 50 um x 50 um (21 x 21 grid, 5% overlap per scan)
- Processing config: `configs/TEST configs/Example configs/config.topo_particle_2jobs_masking.yaml`
- Baseline comparison method: `particle_forward_medianbg_mean` (used for the primary reported values)
- LiTFSI: not applicable (no LiTFSI samples in this dataset)

## Definitions
- Map (grid): the full scan grid for a sample (collection of scan positions), covering 50 um x 50 um with a 21 x 21 grid and 5% overlap per scan.
- Scan: a single AFM image at one grid index (one scan location).
- Isolated particle: center-to-center distance >= 900 nm from any other detected particle (per config isolation distance).

## 1) Scan Inventory
> **Note:** Default grid policy is `manual_review`. Use `grid_issues_by_sample.csv` to flag incomplete grids or duplicates. If `summary.grid_policy` is not `keep_all`, note the policy used and any excluded samples.

### PEGDA
> **Table Callout:** Insert "Scan Inventory - PEGDA" table here.
> Required fields: Total maps, scan size, pixel grid, lateral resolution.

| Metric | Value |
| --- | --- |
| Total AFM maps collected | 206 |
| Scan size (um x um) | 5 x 5 |
| Pixel grid | 512 x 512 |
| Lateral resolution (nm/px) | 9.7656 |

### PEGDA-SiNP
> **Table Callout:** Insert "Scan Inventory - PEGDA-SiNP" table here.
> Required fields: Total maps, scan size, pixel grid, lateral resolution.

| Metric | Value |
| --- | --- |
| Total AFM maps collected | 845 |
| Scan size (um x um) | 5 x 5 |
| Pixel grid | 512 x 512 |
| Lateral resolution (nm/px) | 9.7656 |

## 2) Particle Count Data (PEGDA-SiNP)
> **Table Callout:** Insert "Per-scan particle counts (PEGDA-SiNP)" table here.
> Required fields: Scan ID, total particles, isolated particles.

### Aggregate (All Maps)
| Metric | Value |
| --- | --- |
| Total particles detected | 3322 |
| Mean particles per scan | 4.205 |
| Std. dev. particles per scan | 2.807 |
| Min particles per scan | 0 |
| Max particles per scan | 16 |

### Per-Scan Particle Counts
Source: `particle_counts_by_map.csv` (use rows where `job = particle_forward_medianbg_mean`).
Note: file naming still uses "map"; interpret each row as a scan.

> **Table Callout:** Full per-scan particle table (790 rows) should be pulled from `particle_counts_by_map.csv`.

| Scan ID | Particles (Total) | Particles (Isolated) |
| --- | --- | --- |
|  |  |  |

### Distribution
> **Figure Callout:** Histogram of particles per scan (PEGDA-SiNP).
> Suggested file: `fig_particle_count_hist.png`.

### Per-Sample Summary
Source: `particle_summary_stats_by_sample.csv` (filter for `job = particle_forward_medianbg_mean`)

> **Table Callout:** Per-sample summary table (one row per sample).
> Required fields: Sample ID, total particles, mean particles/scan, std, mean isolated/scan, std.

## 3) Particle Size Distribution

### Aggregate (All Detected Particles)
| Metric | Value |
| --- | --- |
| Mean particle diameter (nm) | 447.434 |
| Std. dev. particle diameter (nm) | 28.964 |

### Filtering Criteria
- Diameter filter: 350-550 nm (current runs; update if config changes)
- Isolation distance: 900 nm (center-to-center)
- Edge exclusion: enabled

### Distribution
> **Figure Callout:** Histogram of particle diameter distribution.
> Suggested file: `fig_particle_diameter_hist.png`.

### Raw Diameter Values
Source: `*_particles.csv` files (per-job particle exports). If these files are missing for a job, only aggregate diameter stats are available.

## 4) Isolation Criteria

### Definition
- Isolated particle: center-to-center distance >= 900 nm

### Results
| Metric | Value |
| --- | --- |
| Mean isolated particles per scan | 2.529 |
| Std. dev. isolated particles per scan | 1.566 |
| % scans with >= 1 isolated particle | 92.025 |

### Distribution
> **Figure Callout:** Histogram of isolated particles per scan.
> Suggested file: `fig_isolated_count_hist.png`.

> **Figure Callout (optional):** Isolated particle count scatter by scan index.
> Suggested file: `fig_isolated_count_scatter.png`.

## 5) Method Comparison (Flatten Base vs Median-BG)

Use `particle_summary_stats_by_job.csv` to populate this section.

> **Table Callout:** Insert "Method comparison" table here (one row per job).
> Required fields: Job, mean particles/scan, std, mean isolated/scan, std, notes.

| Job | Mean Particles/Scan | Std | Mean Isolated/Scan | Std | Notes |
| --- | --- | --- | --- | --- | --- |
| median-bg + mean | 4.205 | 2.807 | 2.529 | 1.566 |  |
| median-bg + fixed(0) | 4.205 | 2.807 | 2.529 | 1.566 |  |
| median-bg + p95 | 4.205 | 2.807 | 2.529 | 1.566 |  |
| median-bg + max(mean,0,p95) | 4.205 | 2.807 | 2.529 | 1.566 |  |
| flatten + mean | 0.586 | 1.010 | 0.500 | 0.826 |  |
| flatten + fixed(0) | 0.586 | 1.010 | 0.500 | 0.826 |  |
| flatten + p95 | 0.586 | 1.010 | 0.500 | 0.826 |  |
| flatten + max(mean,0,p95) | 0.586 | 1.010 | 0.500 | 0.826 |  |

### Method Histogram Sensitivity
Source: `summary_outputs/fits/method_histograms.csv`, `summary_outputs/fits/method_histogram_distances.csv`,
`summary_outputs/fits/method_compare_metrics.csv`, `summary_outputs/fits/method_variance_summary.csv`.

> **Table Callout:** Method histogram distances (JS divergence, L1, Wasserstein-1) across jobs.
> **Table Callout:** Variance across methods (mean/variance/zero-rate).

## 6) Grain Property Summary (Gwyddion)

Use `grain_summary_by_job.csv` and `grain_summary_by_sample_job.csv`.

> **Table Callout:** Insert "Grain property summary" table here.
> Required fields: Job, grain counts (all/kept/isolated), key grain metrics.

| Job | Grain Count (All) | Grain Count (Kept) | Grain Count (Isolated) | Key Metric(s) |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

Figures (if used):
> **Figure Callout:** Per-grain histograms by job (all/kept/isolated).
> Suggested files: `grain_plots/<job>/grain_diameter_nm_all.png`, `grain_plots/<job>/grain_diameter_nm_kept.png`, `grain_plots/<job>/grain_diameter_nm_isolated.png`.

> **Figure Callout (recommended):** Cross-method grain diameter trends.
> Suggested files: `summary_outputs/grain_compare/fig_grain_diameter_nm_kept_mean_by_job.png`,
`summary_outputs/grain_compare/fig_grain_diameter_nm_kept_box_by_job.png`,
`summary_outputs/grain_compare/fig_grain_diameter_nm_isolated_mean_by_job.png`,
`summary_outputs/grain_compare/fig_grain_diameter_nm_isolated_box_by_job.png`.

## 7) Statistical Feasibility Statement

Based on the current Stage 1 dataset, approximately **12 scans** are required to obtain ~**30 isolated particles**, using the observed mean isolated count per scan.

### Risk Curves (Fit Models)
Source: `summary_outputs/fits/fit_summary.csv`, `summary_outputs/fits/fit_risk_curves.csv`,
`summary_outputs/fits/risk_*_*.png`, `summary_outputs/fits/risk_compare_*.png`.

> **Figure Callout:** Risk curves by model (Poisson/NB/ZINB) per wt% and method.
> **Figure Callout:** Uncertainty bands (bootstrap) for Poisson/NB.

## 8) Equations and Aggregations (Python)

All equations are computed using population statistics (Python `statistics.pstdev`), unless noted.

Let:
- \(x_i\) = per-scan count of total particles (or isolated particles), for \(i = 1 \ldots N\)
- \(d_j\) = diameter of particle \(j\), for \(j = 1 \ldots M\)
- \(N\) = number of scans
- \(M\) = number of kept particles

Mean per scan:
```math
\bar{x} = \frac{1}{N} \sum_{i=1}^{N} x_i
```

Population standard deviation:
```math
\sigma = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (x_i - \bar{x})^2}
```

Percent of scans with at least one isolated particle:
```math
\% = 100 \times \frac{\sum_{i=1}^{N} \mathbb{1}(x_i > 0)}{N}
```

Mean and population standard deviation of particle diameters:
```math
\bar{d} = \frac{1}{M} \sum_{j=1}^{M} d_j
```
```math
\sigma_d = \sqrt{\frac{1}{M} \sum_{j=1}^{M} (d_j - \bar{d})^2}
```

Scans required for target isolated particles:
```math
N_{\text{scans}} = \left\lceil \frac{T}{\bar{x}_{\text{iso}}} \right\rceil
```
Where \(T = 30\) isolated particles (rule-of-thumb target) and \(\bar{x}_{\text{iso}}\) is the mean isolated particles per scan.

Lateral resolution (nm/px):
```math
\text{resolution} = \frac{5000 \text{ nm}}{512} = 9.7656 \text{ nm/px}
```

## 8) Pending Rerun (Diameter Filter Update)

- Requested update: diameter filter 250-550 nm (not yet run).
- Estimated rerun time for full comparison sweep: ~1.5 hours wall-clock for PEGDA-SiNP forward, based on the 2026-03-03 batch log span of 1:22:40.
- Decision point: rerun after confirming the updated filter is required for the report.

## Appendix: Files & Outputs

- Inventory: `scan_inventory.csv`
- Per-scan counts: `particle_counts_by_map.csv` (file naming uses "map")
- Aggregate stats: `particle_summary_stats.csv`
- By job: `particle_summary_stats_by_job.csv`
- Grain summaries: `grain_summary_by_job.csv`, `grain_summary_by_sample_job.csv`
- Plots: `fig_particle_count_hist.png`, `fig_particle_diameter_hist.png`, `fig_isolated_count_hist.png`
- Per-job plots: `grain_plots/<job>/*`
- Fit outputs: `summary_outputs/fits/*`
- Grid issues: `grid_issues_by_sample.csv`, `grid_manual_review.csv`, `grid_manual_review_blacklist.txt`
- Report figures include a source caption line with the originating file path.

Output root (summary + figures):
- `C:\Users\Conor O'Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT`

## LiTFSI Comparison (Not Applicable)
No PEGDA-LiTFSI-SiNP samples are present in this dataset, so LiTFSI comparisons are not applicable.

## PEGDA Particle Data (Not Applicable)
PEGDA has no SiNP particles. Particle count/size/isolation sections are not applicable for PEGDA.

## Test Matrix (Reference)

This matrix defines the current topo particle preprocessing + masking sweep for forward scans.
Terminology note: "map/grid" refers to the collection of scan positions; each "scan" is one image at one grid index.

Defaults for all modes:
- Median filter size: 3
- Edge exclude: true
- Diameter filter: 350-550 nm (current runs)
- Isolation distance: 900 nm
- Review pack: optional (usually disabled for full runs)
- Grain export: per-grain properties for all scans (when `use_review_sample: false`)
- Grain summaries: `grain_summary_by_job.csv`, `grain_summary_by_sample_job.csv` (generated by `scripts/topo_particle_summary.py`)
- Grain trend plots: `summary_outputs/grain_compare/*` (generated by `scripts/topo_particle_summary.py`)

| Mode | Preprocessing | Threshold strategy | Fixed (nm) | Percentile | Notes |
| --- | --- | --- | --- | --- | --- |
| `particle_forward_medianbg_mean` | align_rows -> plane_level -> align_rows -> median-bg -> median(3) | mean | - | - | Background via median-bg |
| `particle_forward_medianbg_fixed0` | align_rows -> plane_level -> align_rows -> median-bg -> median(3) | fixed | 0.0 | - | Fixed threshold after bg removal |
| `particle_forward_medianbg_p95` | align_rows -> plane_level -> align_rows -> median-bg -> median(3) | percentile | - | 95 | Adaptive to scan contrast |
| `particle_forward_medianbg_max_fixed0_p95` | align_rows -> plane_level -> align_rows -> median-bg -> median(3) | max(mean,fixed,percentile) | 0.0 | 95 | Conservative combined threshold |
| `particle_forward_flatten_mean` | align_rows -> plane_level -> align_rows -> flatten_base -> median(3) | mean | - | - | Background via flatten_base |
| `particle_forward_flatten_fixed0` | align_rows -> plane_level -> align_rows -> flatten_base -> median(3) | fixed | 0.0 | - | Fixed threshold after bg removal |
| `particle_forward_flatten_p95` | align_rows -> plane_level -> align_rows -> flatten_base -> median(3) | percentile | - | 95 | Adaptive to scan contrast |
| `particle_forward_flatten_max_fixed0_p95` | align_rows -> plane_level -> align_rows -> flatten_base -> median(3) | max(mean,fixed,percentile) | 0.0 | 95 | Conservative combined threshold |

## Future Iterations (Planned Tests)

- Rerun the full comparison sweep with diameter filter 250-550 nm.
- Compare 250-550 nm vs 350-550 nm on the same dataset and report deltas.
- Evaluate alternate isolation distances (e.g., 2x nominal diameter = 900 nm vs 3x).
- Test repeated leveling passes (e.g., plane -> align -> plane) where needed for drifted scans.
- Add a fixed-threshold sweep beyond 0.0 (e.g., +25 nm, +50 nm) to quantify sensitivity.

## Data Availability Notes

- Per-scan table: `particle_counts_by_map.csv` (filter by job).
- Per-sample summary: `particle_summary_stats_by_sample.csv`.
- Per-job summary: `particle_summary_stats_by_job.csv`.
- Diameter raw values: `*_particles.csv` per job (if present).
- Figures: see Appendix list; plot labels still use "map" in the generated figures, but interpret as "scan".
