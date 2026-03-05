# Chapter 5/6 Gap Inventory (Stage 1 + Stage 2 Trigger)

This note is a writing checklist against `docs/Thesis/Reference Material/CRO Thesis Outline V2.docx`,
focused on what we still need (or need to clarify) to write Chapters 5 and 6 cleanly and defensibly.

## Terminology (Lock This In Early)

- **Scan** = one 5 um x 5 um AFM image acquired at a single grid cell (one row/col index).
- **Grid** = the 21 x 21 set of scans that tiles the nominal 50 um x 50 um area (with overlap).
- **Candidate particle** = a topography-detected object that passes diameter + masking rules.
- **Isolated particle** = candidate particle passing center-to-center separation threshold.
- **Stage 1** = topography-based survey + statistics for particle presence/isolation feasibility.
- **Stage 2** = conditional, higher-confidence validation/interrogation using multi-channel overlay
  (e.g., modulus + topo) on a reduced subset of regions.

## Chapter 5 (Framework) - What We Have vs Missing

### 5.1 Data Organization and Preprocessing

Have:

- Config-driven workflow (inputs -> preprocessing -> Gwyddion grain detection -> exports -> Python aggregation).
- Reproducibility + "raw preserved" language already exists in `docs/topo_particle_sop.md`.

Still missing / to tighten:

- A short "standard Gwyddion references" paragraph pointing readers to Gwyddion documentation
  (and explicitly stating we used median background / leveling + why).
- A clear statement of what is *not* corrected (e.g., we do not recover absolute tilt, only remove it
  to support particle segmentation).

### 5.2 Particle Detection and Counting

Have:

- Per-scan counts, totals, mean/std/min/max, and histograms (from pipeline outputs).

Still missing / to tighten:

- Explicit statement that Stage 1 counts are **candidate counts** (not yet fully validated).
- A formal definition of the detection rule used by Gwyddion grain analysis (what constitutes a "grain"
  in this pipeline) and the numeric thresholds used (diameter filter, height threshold strategy, edge exclusion).

### 5.3 Particle Diameter Distribution

Have:

- Raw diameter lists and per-job histograms (pipeline already exports/plots these).

Still missing / to tighten:

- Separate diameter distributions by **processing/masking method** and by **wt% SiNP**
  (so readers can see if a method is narrowing/widening the distribution).

### 5.4 Isolation Analysis

Have:

- Isolation defined as center-to-center distance threshold (currently using 2x nominal diameter was the starting point).
- Isolation counts per scan and percent scans with >= 1 isolated particle.

Still missing / to tighten:

- Isolation definition should explicitly reference the *filtered diameter band*
  (e.g., if filtering is 350-550 nm, then the isolation distance choice should be justified against that band).

### 5.5 Isolation Probability Model (Statistical Heart)

Have:

- Probability of >= 1 isolated particle per scan.
- Scan requirement for 95% confidence (Poisson-based risk curves exist in the pipeline outputs).

Still missing / to tighten:

- A dedicated paragraph about **zero-count risk** (contrapositive) and why it matters operationally
  (risk of wasting scan time).
- Clear "what random variable is modeled" (per-scan event vs per-scan count).

### 5.6 Processing Route Validation (Secondary)

Have:

- Cross-method comparisons (mean/std shifts, histogram distance metrics, etc.) from the method-compare framework.

Still missing / to tighten:

- Tie each validation plot/table back to a single claim:
  - "Processing choice changes particle yield by <= X%" (or not).
  - "Isolation feasibility conclusion is robust across methods" (or not).

### 5.7 Stage 1 Decision Statement

Have:

- The pipeline already generates explicit feasibility statements; we need to quote the correct one in the thesis.

Still missing / to tighten:

- The decision statement should be made **per wt%** (10% and 25% separately), not pooled.

## Chapter 6 (Results + Stage 2 Trigger) - What We Have vs Missing

### 6.1 Baseline Validation (PEGDA, no SiNP)

Have (mechanics/modulus side):

- Prior modulus processing validation work (forward/back comparison, method comparisons).

Likely missing (topography particle side):

- A baseline "false positive" estimate: if PEGDA has no SiNP, how many "particles" does the topo pipeline detect?
  That baseline directly informs the Stage 2 trigger logic (it is an empirical false-positive prior).

### 6.2 Stage 1 Particle Presence (PEGDA-SiNP)

Have:

- Inventory, counts, diameter distributions, isolation, and scan requirements.

Still missing / to tighten:

- Ensure all tables/figures are separated and labeled by **wt%** and include sample descriptors parsed from filenames.
- Captions should include: polymer, wt% SiNP, wt% TPO, and any other encoded metadata (and explicitly state "no coatings").

### 6.5 Processing Route Sensitivity

Have:

- Quantitative comparison outputs exist; this section is mostly organization + interpretation.

Still missing / to tighten:

- Present sensitivity in a format that supports the final decision:
  - baseline method = pick one "primary" method
  - show percent difference vs baseline for each alternative

### Stage 2 Trigger / Crossover (Needs to Be Added Explicitly)

This is the new "methods validation feature" requested for Chapter 6 synthesis.

Goal:

- Identify **when** Stage 2 is necessary to prevent wasted effort.

Model:

- Stage 1 yields candidate particles per scan with mean $\\lambda$.
- Stage 2 confirms a fraction $p$ of those candidates are true particles.

Deliverables:

- A **crossover plot**: required scan count vs assumed validation probability $p$
  (or vs a posterior band for $p$ if Stage 2 validation data exist).
- A **risk statement**: $P(\\text{0 true isolated particles after N scans})$ and/or
  $P(\\text{< K true isolated particles})$ for operationally relevant $N$ and $K$.

Math reference:

- Use `docs/Thesis/Reference Material/secondary_particle_validation_math.md` for the derivation and definitions.

Still missing:

- We need actual Stage 2 validation data (even a small subset) to estimate $p$ credibly.
- We need a formal definition of what "modulus/topo overlay confirmation" means (numeric rule or classifier).

## What Data/Work Is Required to Finish These Sections

- Confirm which scan sets truly have full 21 x 21 grids; decide how incomplete grids are handled in thesis
  (manual review default + blacklist is fine; just document it clearly).
- Add baseline PEGDA "false positive" rate for the topo pipeline (even if near zero, it must be stated).
- For Stage 2 crossover: either
  - include a sensitivity analysis over assumed $p \\in [0.1, 1.0]$, or
  - collect a small validated subset and compute a posterior for $p$ (recommended).

