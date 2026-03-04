# Topo Particle SOP

This SOP describes how to run the topo particle pipeline and generate the draft report.

## 1) Inputs and Setup
- Ensure raw AFM topo scans are available in the input root(s).
- Confirm scan settings: 5 um x 5 um, 512 x 512 px (resolution 9.7656 nm/px).
- Confirm map/grid layout: 50 um x 50 um area, 21 x 21 grid, 5% overlap per scan.
- Confirm baseline job and diameter filter in config:
  - Baseline job: `particle_forward_medianbg_mean`
  - Current comparison diameter filter: 400-500 nm

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
- `py -3 scripts/topo_particle_summary.py`

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
- Figures: `fig_particle_count_hist.png`, `fig_particle_diameter_hist.png`, `fig_isolated_count_hist.png`, etc.

## 4) Generate the Draft Word Report
Run:
- `py -3 scripts/generate_topo_report_docx.py`

Output:
- `topo_particle_report_draft.docx` in the same OUT folder.

## 5) Review and Iterate
- Review the draft Word doc for table correctness and figure placements.
- If the diameter filter must be updated (e.g., 250-550 nm), rerun the comparison suite and regenerate the summary + report.
- Update `docs/topo_particle_deliverables_final.md` with any new notes and rerun timing.

## 6) Notes
- Terminology: "map/grid" is the collection of scan positions; each "scan" is one AFM image.
- The draft report auto-fills from CSV outputs; ensure those outputs match the intended baseline job.
