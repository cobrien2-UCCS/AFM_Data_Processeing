# Next Steps (Project Plan)

This is a concise, thesis-friendly list of what remains and why it matters.

## 1) Topography pipeline (priority)
- Build and validate a `topography_flat` config set (plane level, align rows, median).
- Run a small GUI parity check in Gwyddion to confirm preprocessing order and stats match.
- Define default masks (if any) that make physical sense for height data.

## 2) Particle counting (priority)
- Move beyond `particle_count_basic` to a repeatable, higher-confidence workflow:
- Add size and shape filtering (min/max grain size, circularity thresholds).
- Add multi-channel mask fusion (consensus mask from topo + modulus + other channels).
- Use the existing `review_pack` outputs to build a manual verification loop.

## 3) Units + scaling (critical integrity)
- Resolve missing Z-units for SmartScan TIFFs.
- Decide on a policy: reliable export with units, or explicit calibration in config.
- Document the chosen path as the standard ingestion recipe.

## 4) Validation + provenance (thesis defensibility)
- Pick a small “golden” set of scans and lock down:
- Same processing in GUI vs pygwy (trace + manual match).
- Same summary values across multiple runs (determinism).
- Update `docs/method_compare_notes.md` if new filters change results.

## 5) Job templates for future runs
- Add per‑dataset `jobs` entries (input_root, collect, profile, plots, aggregates).
- Keep one “minimal” and one “full” job for quick runs vs full reporting.

## 6) Deliverable docs
- One‑page “method summary” for the thesis appendix.
- One‑page “how to run” for lab users (job-driven workflow).
