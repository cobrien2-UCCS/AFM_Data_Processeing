# How To Run (One-Page)

This is the shortest path to run a full job end-to-end.

## Recommended: job-driven (one command)
1. Define a job under `jobs:` in your config (see `config.example.yaml`).
2. Run it:
   ```powershell
   .\scripts\run_pipeline.ps1 -Config config.yaml -Job example_modulus_job
   ```

That job can optionally:
- collect a subset of files first (fuzzy keyword matching)
- run pygwy processing
- plot results
- aggregate across scans

## Direct CLI (no PowerShell)
```powershell
py -3 scripts/run_job.py --config config.yaml --job example_modulus_job
```

Common overrides (no config edits):
```powershell
py -3 scripts/run_job.py --config config.yaml --job example_modulus_job --input-root "D:\data" --output-root out/jobs --no-collect
```

## Legacy: manual steps
If you want to run the steps yourself:
1) Generate manifest (Py3)
2) Run pygwy (Py2)
3) Plot (Py3)
4) Aggregate (Py3)

See `docs/USER_GUIDE.md` for full detail and flags.

Note: if your config defines normalized heatmap variants (log, symlog, or centered), include those plot modes in `plotting_modes` and re-run `scripts/cli_plot.py` against the same `summary.csv` to regenerate plots with consistent color ranges.
