$ErrorActionPreference = "Stop"
py -3 scripts/topo_particle_batch.py --config "configs/TEST configs/Example configs/config.topo_particle_2jobs_masking.yaml" --out-base "C:\Users\Conor O''Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT\run_grains_full_wt10_20260304_145519" --only-wt 10
py -3 scripts/topo_particle_batch.py --config "configs/TEST configs/Example configs/config.topo_particle_2jobs_masking.yaml" --out-base "C:\Users\Conor O''Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT\run_grains_full_wt25_20260304_145519" --only-wt 25
