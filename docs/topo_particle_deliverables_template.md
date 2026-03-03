# Topography Particle Deliverables Template

Use this template to assemble the final Word document. Fill in values from the pipeline outputs.

## Summary
- Dataset scope: PEGDA and PEGDA–SiNP (forward scans only)
- Scan size: 5 µm × 5 µm
- Pixel grid: 512 × 512
- Lateral resolution: 9.7656 nm/px
- Processing config: `configs/TEST configs/Example configs/config.topo_particle_2jobs_masking.yaml`
- LiTFSI: not applicable (no LiTFSI samples in this dataset)

## 1) Scan Inventory

### PEGDA
> **Table Callout:** Insert “Scan Inventory — PEGDA” table here.
> Required fields: Total maps, scan size, pixel grid, lateral resolution.

| Metric | Value |
| --- | --- |
| Total AFM maps collected |  |
| Scan size (µm × µm) | 5 × 5 |
| Pixel grid | 512 × 512 |
| Lateral resolution (nm/px) | 9.7656 |

### PEGDA–SiNP
> **Table Callout:** Insert “Scan Inventory — PEGDA–SiNP” table here.
> Required fields: Total maps, scan size, pixel grid, lateral resolution.

| Metric | Value |
| --- | --- |
| Total AFM maps collected |  |
| Scan size (µm × µm) | 5 × 5 |
| Pixel grid | 512 × 512 |
| Lateral resolution (nm/px) | 9.7656 |

## 2) Particle Count Data (PEGDA–SiNP)
> **Table Callout:** Insert “Per‑map particle counts (PEGDA–SiNP)” table here.
> Required fields: Map ID, total particles, isolated particles.

### Aggregate (All Maps)
| Metric | Value |
| --- | --- |
| Total particles detected |  |
| Mean particles per map |  |
| Std. dev. particles per map |  |
| Min particles per map |  |
| Max particles per map |  |

### Per‑Map Particle Counts
Source: `particle_counts_by_map.csv`

| Map ID | Particles (Total) | Particles (Isolated) |
| --- | --- | --- |
|  |  |  |

### Distribution
> **Figure Callout:** Histogram of particles per map (PEGDA–SiNP).
> Suggested file: `fig_particle_count_hist.png`.

## 3) Particle Size Distribution

### Aggregate (All Detected Particles)
| Metric | Value |
| --- | --- |
| Mean particle diameter (nm) |  |
| Std. dev. particle diameter (nm) |  |

### Filtering Criteria
- Diameter filter: 400–500 nm
- Isolation distance: 900 nm (center‑to‑center)
- Edge exclusion: enabled

### Distribution
> **Figure Callout:** Histogram of particle diameter distribution.
> Suggested file: `fig_particle_diameter_hist.png`.

## 4) Isolation Criteria

### Definition
- Isolated particle: center‑to‑center distance ≥ 900 nm

### Results
| Metric | Value |
| --- | --- |
| Mean isolated particles per map |  |
| Std. dev. isolated particles per map |  |
| % maps with ≥ 1 isolated particle |  |

### Distribution
> **Figure Callout:** Histogram of isolated particles per map.
> Suggested file: `fig_isolated_count_hist.png`.

## 5) Method Comparison (Flatten Base vs Median‑BG)

Use `particle_summary_stats_by_job.csv` to populate this section.

> **Table Callout:** Insert “Method comparison” table here (one row per job).
> Required fields: Job, mean particles/map, std, mean isolated/map, std, notes.

| Job | Mean Particles/Map | Std | Mean Isolated/Map | Std | Notes |
| --- | --- | --- | --- | --- | --- |
| median‑bg + mean |  |  |  |  |  |
| median‑bg + fixed(0) |  |  |  |  |  |
| median‑bg + p95 |  |  |  |  |  |
| median‑bg + max(mean,0,p95) |  |  |  |  |  |
| flatten + mean |  |  |  |  |  |
| flatten + fixed(0) |  |  |  |  |  |
| flatten + p95 |  |  |  |  |  |
| flatten + max(mean,0,p95) |  |  |  |  |  |

## 6) Grain Property Summary (Gwyddion)

Use `grain_summary_by_job.csv` and `grain_summary_by_sample_job.csv`.

> **Table Callout:** Insert “Grain property summary” table here.
> Required fields: Job, grain counts (all/kept/isolated), key grain metrics.

| Job | Grain Count (All) | Grain Count (Kept) | Grain Count (Isolated) | Key Metric(s) |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

Figures (if used):
> **Figure Callout:** Per‑grain histograms by job (all/kept/isolated).
> Suggested files: `grain_plots/<job>/grain_diameter_nm_all.png`, `grain_plots/<job>/grain_diameter_nm_kept.png`, `grain_plots/<job>/grain_diameter_nm_isolated.png`.

## 7) Statistical Feasibility Statement

Based on the current Stage 1 dataset, approximately **[N] maps** are required to obtain ~**[TARGET] isolated particles**, using the observed mean isolated count per map.

## Appendix: Files & Outputs

- Inventory: `scan_inventory.csv`
- Per‑map counts: `particle_counts_by_map.csv`
- Aggregate stats: `particle_summary_stats.csv`
- By job: `particle_summary_stats_by_job.csv`
- Grain summaries: `grain_summary_by_job.csv`, `grain_summary_by_sample_job.csv`
- Plots: `fig_particle_count_hist.png`, `fig_particle_diameter_hist.png`, `fig_isolated_count_hist.png`
- Per‑job plots: `grain_plots/<job>/*`

## LiTFSI Comparison (Not Applicable)
No PEGDA–LiTFSI–SiNP samples are present in this dataset, so LiTFSI comparisons are not applicable.

## PEGDA Particle Data (Not Applicable)
PEGDA has no SiNP particles. Particle count/size/isolation sections are not applicable for PEGDA.
