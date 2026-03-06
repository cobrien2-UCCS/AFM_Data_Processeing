# Chapter 5 Writing Notes (Read Before Drafting)

## Chapter 5 Purpose (Do Not Drift)

- Core question: *Are there enough statistically representative, isolated particles to proceed to Stage 2?*
- Scope limit: do **not** claim interphase gradients, thickness, or mechanistic interphase behavior here.
- This is the correct chapter to define project-specific language so Chapter 6 can stay focused on results.

## Nomenclature Placement

- Add an early subsection titled **Nomenclature and Workflow Definitions**.
- Place it after the Chapter 5 introduction and before detailed preprocessing and workflow sections.
- The goal is to define the project vocabulary once, clearly, so later chapters can reference it instead of re-explaining it.
- If the thesis later gets a front-matter nomenclature or glossary section, this subsection can be moved there with minimal rewriting.

## Terminology (Use Consistently)

- Use **scan** for one grid-cell image (`5 um x 5 um`).
- Use **grid** for the `21 x 21` survey layout from which scans are drawn.
- Avoid **map** unless you explicitly define it; prefer **scan** in this thesis.
- Define **job** explicitly: one named execution route that applies a specific preprocessing and thresholding combination to a defined scan set and writes its own outputs.
- Define **profile** explicitly: the reusable recipe that a job points to.
- Define **processing mode** explicitly: the configured operation chain used by a profile.
- Define **primary route** and **comparison route** once, then use those names consistently.
- Define **candidate particle**, **isolated particle**, **confirmed particle**, and **grain** in one compact table.
- Define **baseline** carefully, since it can mean baseline method, baseline dataset, or baseline false-positive rate.

## Stage 1 vs Stage 2 (Be Explicit)

- Stage 1 outputs **candidate** particle counts from topography and grain-detection rules.
- Stage 2 provides confirmation probability `p` or per-candidate confirmation values `p_j` using multi-channel overlay.
- When you say **particles** in Chapter 5, specify whether you mean **candidate particles** or **confirmed true particles**.

## Must-Haves in Chapter 5

- All tables and figures separated by **wt% SiNP**.
- Isolation definition must be numeric and justified relative to the diameter band used.
- Include contrapositive / zero-risk language: the risk of scanning and getting zero isolated true particles.
- Include the Stage 2 crossover definition and plot, even if it is presented as a sensitivity analysis over `p`.
- Include the rationale for using **forward scans only** in the topo workflow.

## Math Hygiene

- Define every symbol the first time it appears.
- State what random variable is being modeled: per-scan count, per-scan event, or total-count accumulation.
- Do **not** use `N/p` as the main result; it is only intuition. Use the confidence-based Poisson CDF form for the reported scan requirement.
- State explicitly that Poisson is being used as the baseline count model and explain why it is acceptable for this Stage 1 feasibility question.
- Clarify that the validity of the Poisson approximation depends on the observed scan inventory being large enough to estimate the mean isolated-particle rate with stability.

## Recommended Nomenclature Table Contents

- `scan`: one AFM image associated with one indexed grid position
- `grid`: the survey layout from which scans are taken
- `sample set`: one grouped collection of scans belonging to one physical sample / surface condition
- `job`: one configured run instance that writes a dedicated result set
- `profile`: the reusable processing recipe used by a job
- `processing mode`: the underlying configured operation chain
- `candidate particle`: a Stage 1 retained topographic feature meeting the configured rules
- `isolated particle`: a candidate particle that also satisfies the isolation-distance rule
- `confirmed particle`: a Stage 2 validated particle after multi-channel confirmation
- `grain`: the segmented feature returned by the grain-analysis step; not automatically equivalent to a true particle
- `baseline`: the reference method or reference dataset used for comparison; specify which meaning applies each time

## Reader Guidance

- Assume the reader does **not** know the codebase vocabulary.
- Prefer one clear definition table over repeated ad hoc explanations later.
- Chapter 6 should point back to these definitions rather than redefining them unless a short reminder is necessary.

## Forward-Only Scan Justification

- Add a short method subsection or paragraph explaining why only **forward** scans were used in this Stage 1 topography workflow.
- The justification is that prior modulus baseline comparisons showed close agreement between forward and backward scan directions.
- Therefore, retaining only forward scans reduced redundancy without materially changing the Stage 1 feasibility question.
- This should be presented as a method-selection decision, not as a new Chapter 6 result.

## Dataset Description Notes

- Define the grouped sample inventory clearly:
  - `10 wt% SiNP`: 4 grouped sample sets total
  - `25 wt% SiNP`: 5 grouped sample sets total
- Clarify that the nominal survey grid is `21 x 21`, but the actual included scan inventory may be smaller for some grouped sample sets.
- State that the exact included scan counts are reported in Chapter 6 as part of the results inventory, not assumed from the nominal grid.

## Poisson Modeling Justification Notes

- Add a brief statement that the Poisson model is being used to answer a practical feasibility question: how many scans are required to achieve a target number of isolated particles with specified confidence.
- Note that a later discussion section should address the **minimum scan inventory needed to justify fitting or using a Poisson count model**.
- That discussion should distinguish:
  - minimum scans needed to estimate `lambda` with reasonable stability
  - minimum scans needed to achieve the target isolated-particle count
- Make clear that these are related but not identical questions.

Reference math file:

- `docs/Thesis/Reference Material/secondary_particle_validation_math.md`
