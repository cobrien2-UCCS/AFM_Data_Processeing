# Chapter 5 Writing Notes (Read Before Drafting)

## Chapter 5 Purpose (Do Not Drift)

- Core question: *Are there enough statistically representative, isolated particles to proceed to Stage 2?*
- Scope limit: do **not** claim interphase gradients, thickness, or mechanistic interphase behavior here.

## Terminology (Use Consistently)

- Use **scan** for one grid cell image (5 um x 5 um).
- Use **grid** for the 21 x 21 scan set.
- Avoid “map” unless you explicitly define it (prefer “scan” in this thesis).

## Stage 1 vs Stage 2 (Be Explicit)

- Stage 1 outputs **candidate** particle counts (from topography + grain detection rules).
- Stage 2 provides confirmation probability `p` (or per-candidate `p_j`) using multi-channel overlay.
- When you say “particles” in Chapter 5, specify whether you mean **candidates** or **confirmed true particles**.

## Must-Haves in Chapter 5

- All tables/figures separated by **wt% SiNP** (10% and 25% are different populations).
- Isolation definition must be numeric and justified relative to the diameter band used.
- Include contrapositive / zero-risk language (risk of scanning and getting 0 isolated true particles).
- Include the Stage 2 crossover definition and plot (even if it is a sensitivity analysis over `p`).

## Math Hygiene

- Define every symbol the first time it appears.
- State what random variable is being modeled (per-scan count vs per-scan event).
- Don’t use `N/p` as the main result; it’s only intuition. Use the confidence-based Poisson CDF form.

Reference math file:

- `docs/Thesis/Reference Material/secondary_particle_validation_math.md`

