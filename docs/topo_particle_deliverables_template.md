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
Source: `particle_counts_by_map.csv` (use rows where `job = particle_forward_medianbg_mean`)

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

## Appendix: Files & Outputs

- Inventory: `scan_inventory.csv`
- Per-scan counts: `particle_counts_by_map.csv`
- Aggregate stats: `particle_summary_stats.csv`
- By job: `particle_summary_stats_by_job.csv`
- Grain summaries: `grain_summary_by_job.csv`, `grain_summary_by_sample_job.csv`
- Plots: `fig_particle_count_hist.png`, `fig_particle_diameter_hist.png`, `fig_isolated_count_hist.png`
- Per-job plots: `grain_plots/<job>/*`
- Fit outputs: `summary_outputs/fits/*`
- Grid issues: `grid_issues_by_sample.csv`, `grid_manual_review.csv`, `grid_manual_review_blacklist.txt`
- Report figures include a source caption line with the originating file path.

## LiTFSI Comparison (Not Applicable)
No PEGDA-LiTFSI-SiNP samples are present in this dataset, so LiTFSI comparisons are not applicable.

## PEGDA Particle Data (Not Applicable)
PEGDA has no SiNP particles. Particle count/size/isolation sections are not applicable for PEGDA.
