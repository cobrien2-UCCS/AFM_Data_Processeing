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

## Topo particle summary + fits
```powershell
py -3 scripts/topo_particle_summary.py --config "configs/TEST configs/Example configs/config.topo_particle_summary.yaml" --out-base "<out_root>"
py -3 scripts/fit_particle_distributions.py --config "configs/TEST configs/Example configs/config.topo_particle_fits.yaml" --input-root "<out_root>"
```

Note: grain/particle exports (`*_grains.csv`, `*_particles.csv`) are written by the Py2 runner under `<out_root>/<system>/<sample>/<job>/grains|particles/`. If they are missing, check for Windows path-length constraints.

## Curated representative image pack

For thesis figures or appendix review images, the current codebase already supports a simple mask-overlay panel workflow:

1. Put the selected TIFFs into a curated directory.
2. Point a dedicated particle job at that directory via `jobs.<name>.input_root`.
3. Enable `modes.<particle_mode>.review_pack`.
4. Run the job normally.

The runner will write:
- `review/review.csv`
- `review/panels/*_particle_panel.png`

This is the recommended current path for:
- isolated-particle examples
- clumped-particle examples
- dense non-clumped examples
- sparse/single-particle examples

## Legacy: manual steps
If you want to run the steps yourself:
1) Generate manifest (Py3)
2) Run pygwy (Py2)
3) Plot (Py3)
4) Aggregate (Py3)

See `docs/USER_GUIDE.md` for full detail and flags.

Note: if your config defines normalized heatmap variants (log, symlog, or centered), include those plot modes in `plotting_modes` and re-run `scripts/cli_plot.py` against the same `summary.csv` to regenerate plots with consistent color ranges.
