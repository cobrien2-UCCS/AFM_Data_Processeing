# Chapter 8 Writing Notes (Read Before Drafting)

## Purpose
- Define conditional next steps after Stage 1 feasibility determination.

## Must-Haves
- Explicit Stage 2 trigger/crossover criteria (availability/risk/cost).
- Define how Stage 2 estimates confirmation probability p (or per-candidate p_j).
- State uncertainty propagation requirements.
- Add a future-work item to refactor the current analysis into a more reproducible, robust, and user-predictable pipeline.
- Note that the present workflow still depends on substantial operator-guided orchestration, ad hoc reruns, and report-specific legwork even though the underlying processing logic is now largely established.
- Frame the future need as: reduce manual intervention, improve run predictability, standardize artifacts and naming, and package the workflow so other users can run it with consistent outcomes.
- Mirror the modulus-baseline scope note here:
  - the current modulus baseline validation was performed on one PEGDA sample and one fracture-surface side
  - it should be repeated across more grouped samples and separated by side before broad generalization
  - the same comparison framework should later be extended to composite PEGDA-SiNP and Li-containing systems
- Add a modulus-validation future-work note that the absolute modulus magnitude currently appears higher than expected for PEGDA and may reflect a systematic offset rather than a random processing artifact.
- State that future work should validate modulus magnitude against:
  - raw pinpoint / force-curve data
  - AFM setpoints / force regime
  - calibration parameters
  - upstream contact-model / fit settings
  - and TIFF/export scaling before Gwyddion ingestion
- Add a future-work figure item for a workflow/data-flow chart that explains the pipeline architecture at a reader-facing level.
