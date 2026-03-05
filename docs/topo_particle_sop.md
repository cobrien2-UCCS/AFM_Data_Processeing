# Topo Particle SOP

This SOP describes how to run the topo particle pipeline and generate the draft report.

## 1) Inputs and Setup
- Ensure raw AFM topo scans are available in the input root(s).
- Confirm scan settings: 5 um x 5 um, 512 x 512 px (resolution 9.7656 nm/px).
- Confirm map/grid layout: 50 um x 50 um area, 21 x 21 grid, 5% overlap per scan.
- Confirm baseline job and diameter filter in config:
  - Baseline job: `particle_forward_medianbg_mean`
  - Current comparison diameter filter: 350-550 nm

## 2) Run the Pipeline (Config-Driven)
Use the config-driven jobs in:
- `configs/TEST configs/Example configs/config.topo_particle_2jobs_masking.yaml`

Typical flow per sample:
1. Collect files
2. Make job manifest
3. Run pygwy job(s)

Example (reference only):
- `scripts/collect_files.py`
- `scripts/make_job_manifest.py`
- `scripts/run_pygwy_job.py`

## 3) Generate Summary Outputs
Run the summary aggregation:
- `py -3 scripts/topo_particle_summary.py --config "configs/TEST configs/Example configs/config.topo_particle_summary.yaml"`

This writes to:
- `C:\Users\Conor O'Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT`

Key outputs:
- `scan_inventory.csv`
- `particle_counts_by_map.csv`
- `particle_summary_stats.csv`
- `particle_summary_stats_by_job.csv`
- `particle_summary_stats_by_sample.csv`
- `grain_summary_by_job.csv`
- `grain_summary_by_sample_job.csv`
- `grid_issues_by_sample.csv` (grid completeness + duplicates)
- Figures: `fig_particle_count_hist.png`, `fig_particle_diameter_hist.png`, `fig_isolated_count_hist.png`, etc.

Grid policy controls (in `config.topo_particle_summary.yaml`):
- `summary.grid_policy`: `manual_review` (default) | `keep_all` | `require_full_grid` | `intersect_grid`
- `summary.grid_rows`, `summary.grid_cols`, `summary.grid_index_base`
- `summary.exclude_samples`, `summary.exclude_source_files`

Manual review mode:
- Writes `grid_manual_review.csv` + `grid_manual_review_blacklist.txt`.
- Exits early so the user can remove or blacklist samples/files and rerun.

## 3.5) Check That Jobs Ran (Quick Verification)
Use the output root from `docs/File Locations for Data Grouped.txt`.
- Confirm run started: `scan_inventory.json` exists in the output root.
- Count completed jobs: `Get-ChildItem -Recurse -Filter summary.csv <OUT_ROOT> | Measure-Object`.
- Check most recent activity:
  - `Get-ChildItem -Recurse -File <OUT_ROOT> | Sort-Object LastWriteTime -Descending | Select-Object -First 5`
- Confirm per-sample outputs exist:
  - `...\PEGDA_SiNP\<sample>\<job>\summary.csv`
- If a report was generated, verify:
  - `topo_particle_report_*.docx` exists in the output root.

## 4) Generate the Draft Word Report
Run:
- `py -3 scripts/generate_topo_report_docx.py`

Output:
- `topo_particle_report_draft.docx` in the same OUT folder.

## 4.5) Fit Distributions (Risk Curves)
Run:
- `py -3 scripts/fit_particle_distributions.py --config "configs/TEST configs/Example configs/config.topo_particle_fits.yaml" --input-root "<OUT_ROOT>"`

Outputs:
- `summary_outputs/fits/fit_summary.csv`
- `summary_outputs/fits/fit_risk_curves.csv`
- `summary_outputs/fits/risk_*_*.png`, `summary_outputs/fits/risk_compare_*.png`

## 5) Review and Iterate
- Review the draft Word doc for table correctness and figure placements.
- If the diameter filter must be updated (e.g., 250-550 nm), rerun the comparison suite and regenerate the summary + report.
- Update `docs/topo_particle_deliverables_final.md` with any new notes and rerun timing.

## 6) Fit Models + Risk Equations (Used in Distribution Analysis)
These equations are used by `scripts/fit_particle_distributions.py` to estimate risk and required scans.

Definitions:
- Let `X_i` be the isolated particle count in scan `i`.
- Let `S_n = sum_{i=1..n} X_i` be total isolated particles after `n` scans.
- Target isolated count is `T` (config: `fit.target_total`).

Poisson model (counts per scan):
```text
X_i ~ Poisson(lambda)
P(X = k) = exp(-lambda) * lambda^k / k!
S_n ~ Poisson(n * lambda)
P(S_n >= T) = 1 - sum_{k=0..T-1} P(S_n = k)
```

Negative Binomial model (over-dispersed counts):
```text
Var(X) = mu + mu^2 / r
r = mu^2 / (Var(X) - mu)
p = r / (r + mu)
X ~ NB(r, p)
S_n ~ NB(n*r, p)
P(S_n >= T) = 1 - sum_{k=0..T-1} P_NB(S_n = k)
```

Zero-inflated Negative Binomial (excess zeros):
```text
P(X = 0) = pi + (1 - pi) * NB(0; r, p)
P(X = k) = (1 - pi) * NB(k; r, p), k > 0
```

Required scans for reliability level `q`:
```text
Find smallest n such that P(S_n >= T) >= q
```

Uncertainty band (bootstrap across scans):
```text
Resample the per-scan counts with replacement B times.
Fit each bootstrap sample and compute its risk curve.
Use the 5th and 95th percentiles at each n for the band.
```

Method sensitivity (cross-method variability):
```text
Compare per-method histograms and fitted risk curves.
Compute histogram distances (JS divergence, L1, Wasserstein-1).
Summarize variance across methods of mean/variance/zero-rate.
```

## 7) Notes
- Terminology: "map/grid" is the collection of scan positions; each "scan" is one AFM image.
- The draft report auto-fills from CSV outputs; ensure those outputs match the intended baseline job.
