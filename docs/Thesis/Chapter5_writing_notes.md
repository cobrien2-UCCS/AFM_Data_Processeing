# Chapter 5 Writing Notes (Read Before Drafting)

## Chapter 5 Purpose (Do Not Drift)

- Core question: *Are there enough statistically representative, isolated particles to proceed to Stage 2?*
- Scope limit: do **not** claim interphase gradients, thickness, or mechanistic interphase behavior here.
- This is the correct chapter to define project-specific language so Chapter 6 can stay focused on results.

## Outline Verification

- The thesis outline defines Chapter 5 as:
  - **"Statistical Validation Framework (Stage 1)"**
  - specifically: **particle counting workflow, diameter filtering, isolation criteria, isolation probability modeling, and required map count for 95% confidence**
- The Chapter 1 roadmap also adds **processing-route consistency** as part of Chapter 5's role.
- Therefore Chapter 5 should stay tightly centered on the Stage 1 framework and should not drift too far into broad preprocessing-comparison discussion unless it directly supports the validation framework.
- Sections on preprocessing and threshold routes are still needed, but they should be written as inputs to the counting / validation framework, not as stand-alone results.

## Strict Chapter 5 Structure

- To match the outline as closely as possible, Chapter 5 should be organized as:
  - **5.1 Particle Counting Workflow**
  - **5.2 Diameter Filtering**
  - **5.3 Isolation Criteria**
  - **5.4 Isolation Probability Modeling**
  - **5.5 Required Map Count for 95% Confidence**
  - **5.6 Processing-Route Validation**
- Keep nomenclature, software environment, and default parameters as supporting material inside `5.1`, not as large stand-alone numbered sections.
- Use the agreed thesis nomenclature as consistently as possible once a term has been defined; avoid renaming the same workflow object across sections, captions, and tables.
- Keep appendix SOP material out of the numbered section flow.

## Nomenclature Placement

- Nomenclature is still needed, but if Chapter 5 is kept strict to the outline it should be a compact support table inside `5.1`, not a major stand-alone section.
- If the thesis later gets a front-matter nomenclature or glossary section, that material can be moved there with minimal rewriting.
- The goal is still to define the project vocabulary once, clearly, so later chapters can reference it instead of re-explaining it.
- Modulus unit handling remains under validation. A one-file modulus verification run produced a negative exported modulus value while the broader modulus comparison CSV sets remained non-negative; treat this as an unresolved processing/data-validation issue rather than a settled physical result.

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

## Appendix Support Material

- Add an appendix-style SOP for reproducing the topography particle workflow manually in the Gwyddion GUI.
- The SOP should be framed as **manual parity / validation guidance**, not as the preferred production workflow.
- Include a short statement that the batch pipeline is the authoritative execution path for the reported results, while the GUI SOP exists so a human can reproduce one scan at a time and understand the operations.
- Include a table that separates:
  - steps with a direct Gwyddion GUI equivalent
  - steps that require export + manual calculation outside Gwyddion (especially isolation filtering)
- Reference appendix file:
  - `docs/Thesis/topo_particle_gwyddion_gui_sop.md`
- When mentioned in Chapter 5, refer to the SOP only as a **verification artifact** or **appendix aid**.

## Forward-Only Scan Justification

- Add a short method subsection or paragraph explaining why only **forward** scans were used in this Stage 1 topography workflow.
- The justification is that prior modulus baseline comparisons showed close agreement between forward and backward scan directions.
- Therefore, retaining only forward scans reduced redundancy without materially changing the Stage 1 feasibility question.
- This should be presented as a method-selection decision, not as a new Chapter 6 result.
- Keep the wording conservative: this is a **method-selection basis from prior comparison work**, not a claim that all future forward/backward scans are universally interchangeable.
- In the strict outline-aligned version of Chapter 5, this belongs in **5.6 Processing-Route Validation**, not as a major dataset-description section.

## Dataset Description Notes

- Define the grouped sample inventory clearly:
  - `10 wt% SiNP`: 4 grouped sample sets total
  - `25 wt% SiNP`: 5 grouped sample sets total
- Clarify that the nominal survey grid is `21 x 21`, but the actual included scan inventory may be smaller for some grouped sample sets.
- State that the exact included scan counts are reported in Chapter 6 as part of the results inventory, not assumed from the nominal grid.

## Relationship to Chapters 3 and 4

- Chapter 5 should not re-explain all sample fabrication or AFM hardware details.
- Use Chapter 5 to reference prior chapters when needed:
  - Chapter 3 for sample preparation, composition, and fracture-surface generation
  - Chapter 4 for AFM acquisition procedure and nominal scan-grid setup
- Images of the nominal `21 x 21` survey grid and scraped vs non-scraped surfaces can be referenced in Chapter 5 only if they directly support the Stage 1 validation framework; otherwise they belong primarily in Chapters 3-4.
- Chapter 5 may still include one compact schematic if it helps the reader connect scan, grid, and grouped sample-set terminology.
- Add a figure placeholder in the dataset-structure section for:
  - nominal scan-grid structure
  - grouped sample / scan-selection structure
  - or both if needed

## Software Environment Notes

- Somewhere early in Chapter 5, explicitly state the software environment used to generate the Stage 1 outputs.
- This should include:
  - Gwyddion version
  - pygwy / Python 2.7 dependency
  - Python 3 environment used for postprocessing, report generation, and plotting
  - note that Gwyddion/pygwy is Python-2.7-bound in the current implementation
- The dual-environment design should be explained briefly:
  - Python 2.7 for Gwyddion-backed per-scan processing
  - Python 3 for aggregation, fitting, plotting, and report generation
- This can be a small subsection or a compact methods table; do not let it overwhelm the main validation framework.
- Current environment values verified on the working machine:
  - Gwyddion `2.70.20260111 (2025-12-28 build string shown by --version)`
  - Python 2.7.16 for the pygwy runner
  - Python 3.14.2 for postprocessing/report generation
- Also note that the shell-default `python` on this machine points to Python 2.7, so Chapter 5 should state that the Python 3 stage was invoked explicitly.

## Section 5.3 Revision Notes

- The current second paragraph of 5.3 needs to be rewritten in cleaner thesis language.
- 5.3 should contain a figure insert / placeholder for:
  - nominal scan-grid structure
  - grouped scan-selection structure
  - data-flow structure if helpful
- 5.3 is also a reasonable place for a compact "active defaults / software context" table if that keeps the chapter easier to follow, but this may alternatively sit at the start of 5.4.
- If nomenclature is later moved to thesis front matter, 5.3 should still remain understandable without it.

## Section 5.4 Revision Notes

- The current job-family table is too coarse.
- Replace or follow it with a full active job table listing all tested routes:
  - medianbg_mean
  - medianbg_fixed0
  - medianbg_p95
  - medianbg_max_fixed0_p95
  - flatten_mean
  - flatten_fixed0
  - flatten_p95
  - flatten_max_fixed0_p95
- Include compact parameter/default tables that explicitly state:
  - threshold strategy
  - threshold source / fixed threshold / percentile where applicable
  - diameter band
  - isolation distance
  - median filter size
  - edge exclusion
  - particle/grain export behavior
- Keep the prose focused on what was actually run for the current Stage 1 design; broader design variants can be named as future work if they were not active in the current reported run.

## Processing Method Definitions

- Chapter 5 must explicitly define the processing methods in reader-facing language, not just by config/job name.
- Put the short-form definitions in **5.1 Particle Counting Workflow** so the reader can interpret later tables and figures without reading code or config files.
- Add a short unit-provenance note in `5.1`: a direct one-file modulus verification run showed missing detected z-units in pygwy for the current TIFF path, so the present `kPa` label should be described as a workflow fallback/normalization assumption pending upstream metadata verification.
- At minimum, define:
  - `medianbg_mean`
  - `medianbg_fixed0`
  - `medianbg_p95`
  - `medianbg_max_fixed0_p95`
  - `flatten_mean`
  - `flatten_fixed0`
  - `flatten_p95`
  - `flatten_max_fixed0_p95`
- For each method, state:
  - preprocessing family
  - threshold rule
  - what that threshold is intended to do
  - whether it is the primary route or a comparison/validation route
- Use the same idea for the modulus workflow definitions in the modulus baseline report so the baseline-validation section in Chapter 6 uses consistent language.

## Workflow Figure Placeholder

- A flow chart will likely be the clearest way to explain the end-to-end data flow for readers.
- Add a Chapter 5 figure placeholder for a workflow diagram, e.g.:
  - **Insert Figure 5.x - Stage 1 workflow / data-flow chart**
- The figure should eventually show:
  - scan input selection
  - job/profile routing
  - preprocessing family
  - thresholding / filtering
  - particle/grain exports
  - aggregation / model fitting
  - report and chapter outputs
- This should stay as a placeholder for now if the final diagram is not ready.

## Parameter Reporting Notes

- Chapter 5 should include a compact table of the active default parameters used in the Stage 1 particle workflow.
- Include at minimum:
  - scan size
  - pixel grid
  - row-alignment method/direction
  - median filter size
  - diameter band
  - isolation distance
  - edge exclusion rule
  - threshold routes tested
  - exported outputs
- Also include a table that lists the active jobs explicitly, not just the two preprocessing families.
- The family-level table is still useful, but it should be followed by a job-level table because the threshold variants are part of the actual design under test.
- These tables should live inside **5.1 Particle Counting Workflow** to keep the numbered sections aligned to the outline.

## Processing-Route Validation Scope

- `5.6 Processing-Route Validation` should be narrow.
- It should do three things only:
  - explain why route consistency matters for Stage 1
  - justify forward-only scan use via prior modulus forward/backward comparison
  - state that topography route variants were retained as controlled validation / sensitivity checks
- It should **not** become a full modulus-results section.
- The modulus method-comparison study should be used only as method-selection precedent and direction-consistency support.
- The topography route-comparison results themselves belong mainly in Chapter 6.

## What to Write as Active Methods vs Future Work

- The active Chapter 5 methods should focus on the workflow actually used in the current Stage 1 analysis.
- For the processing-method comparison section, treat the current default / primary route as the active method and describe additional route comparisons as validation or sensitivity checks.
- If a broader method sweep is out of scope for this chapter version, state that explicitly and move expanded comparisons or design alternatives to future work.

## Proof-of-Concept Reference

- Reference `AFM TIFF to Summary Stats & Plotting Pipeline v3.md` as a design-origin document when writing the Chapter 5 workflow narrative.
- Use it to preserve the original architecture intent:
  - config-driven processing
  - reproducible TIFF -> summary -> plot flow
  - separation of processing, CSV schema, and plotting layers
- Do not cite it as the thesis method source by itself; instead use it as an internal project design reference that helps keep the written methods aligned with the implemented system.

## Poisson Modeling Justification Notes

- Add a brief statement that the Poisson model is being used to answer a practical feasibility question: how many scans are required to achieve a target number of isolated particles with specified confidence.
- Note that a later discussion section should address the **minimum scan inventory needed to justify fitting or using a Poisson count model**.
- That discussion should distinguish:
  - minimum scans needed to estimate `lambda` with reasonable stability
  - minimum scans needed to achieve the target isolated-particle count
- Make clear that these are related but not identical questions.

Reference math file:

- `docs/Thesis/Reference Material/secondary_particle_validation_math.md`
