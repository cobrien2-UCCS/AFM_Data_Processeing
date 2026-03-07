# Representative Particle Image SOP (Median-Background Route)

## Purpose

This SOP defines how to generate a small, thesis-ready image set showing representative topography and mask results for particle categories that are easy for a reader to interpret.

Use this SOP for:
- appendix/supporting material
- figure preparation
- manual validation of the Stage 1 topography workflow
- creation of curated mask-overlay image sets from a selected directory

Do **not** treat this SOP as the primary production workflow for the full dataset. The config-driven batch pipeline remains the authoritative route for reportable statistics.

These representative-image panels are intended to:
- show what the program is doing visually
- show what retained particle fields actually look like in the scan data
- show how the particle mask behaves on real images
- illustrate common particle arrangements within the sample set

A thesis-facing framing sentence is:

> Representative topography-and-mask image panels were retained to provide visual context for the Stage 1 workflow, illustrate the appearance of isolated and clustered particle fields, and show how the detection mask behaves across common particle arrangements.

## Scope

This SOP is intentionally narrow. It covers:
- forward topography scans
- the **median-background** preprocessing family
- threshold-based particle masks
- generation of side-by-side image panels with the mask overlaid
- selection of representative scans for thesis figures

It does **not** cover:
- modulus analysis
- Stage 2 confirmation
- full batch statistics
- multi-channel fused masks

## Recommended Representative Categories

Build the representative image set around four broad categories:

1. **Single isolated particle**
   - one clear retained particle
   - not visibly clumped
   - good candidate for Stage 2 follow-up

2. **Clumped particles**
   - clear local aggregation
   - particles are present but not isolated
   - useful for explaining why count alone is not sufficient

3. **Many particles with little or no clumping**
   - higher-density field
   - multiple retained particles
   - still visually separated enough to explain the isolation logic

4. **Sparse / SiNP-alone example**
   - very sparse retained-particle field
   - useful for showing an example where only one or a few candidates remain after filtering

If the actual dataset suggests a better label than "SiNP-alone", use a clearer thesis-facing name such as:
- `Sparse single-particle field`
- `Low-density retained-particle field`

## Current Base Processing Route

This SOP is based on the **median-background** family used in the current topography particle workflow.

Use one of these job variants:
- `particle_forward_medianbg_mean`
- `particle_forward_medianbg_fixed0`
- `particle_forward_medianbg_p95`
- `particle_forward_medianbg_max_fixed0_p95`

Shared preprocessing sequence:
1. Align Rows, horizontal, median
2. Plane Level
3. Align Rows, horizontal, median
4. Median background / median level
5. Median filter, size `3`

The threshold rule then depends on the chosen job variant.

## Manual GUI Workflow (Single Image)

For one scan in Gwyddion:

1. Open the forward `Z Height` scan.
2. Duplicate the field so the raw scan is preserved.
3. Apply the median-background preprocessing sequence.
4. Determine the threshold for the chosen route:
   - `mean`
   - `fixed0`
   - `p95`
   - `max(mean, fixed0, p95)`
5. Mark grains above threshold.
6. Inspect the binary mask against the processed image.
7. Export or screenshot:
   - processed image only
   - processed image with mask
8. Record whether the scan belongs to one of the representative categories above.

For the detailed GUI parity workflow, see:
- [topo_particle_gwyddion_gui_sop.md](/Users/Conor%20O'Brien/Documents/GitHub/AFM-Data-Management/docs/Thesis/topo_particle_gwyddion_gui_sop.md)

## Config-Driven Image Pack Workflow

The current pipeline can already generate simple mask-overlay panels from a curated directory without new code.

### What already exists

The Py2 runner supports:
- `review_pack.enable: true`
- side-by-side PNG panels
  - left: processed grayscale scan
  - right: same scan with the particle mask overlaid in red
- `review.csv` output listing the panel files

The current review panel path is implemented in:
- [run_pygwy_job.py](/Users/Conor%20O'Brien/Documents/GitHub/AFM-Data-Management/scripts/run_pygwy_job.py)

### Recommended directory structure

Create a curated input folder with one subfolder per image category, for example:

```text
C:\AFM_REVIEW_INPUT\
  single_isolated\
  clumped\
  many_not_clumped\
  sparse_single\
```

Copy the selected TIFF files into the appropriate category folders.

### Recommended config pattern

Use a dedicated job whose `input_root` points at the curated directory and whose particle mode enables `review_pack`.

Operationally, this means:
- the selected TIFFs are processed with the same particle workflow
- the mask-overlay panels are written under the job output
- the curated set stays separated from the full statistics run

### Example behavior

For a dedicated curated-image job:
- input: curated directory only
- processing: `particle_forward_medianbg_*`
- output:
  - `summary.csv`
  - `particles/*.csv`
  - optional `grains/*.csv`
  - `review/review.csv`
  - `review/panels/*_particle_panel.png`

## What to Keep for Thesis Figures

For each selected image, keep:
- the original filename
- the job/method used
- the category label
- the processed grayscale image
- the overlay panel with mask
- a note on whether the retained particle(s) are isolated or clumped

Recommended caption components:
- sample composition / wt%
- scraped or non-scraped condition
- forward topography scan
- preprocessing route
- threshold route
- whether the panel shows a representative isolated, clumped, or sparse field

## Current Config-Driven Option

Yes, this can already be handled in the main config **without changing core code**, provided you use a dedicated curated-image job.

Current supported approach:
- point `jobs.<name>.input_root` at the curated directory
- use a particle profile/job under the median-background family
- enable `modes.<particle_mode>.review_pack`

This is the cleanest current solution because it:
- stays config-driven
- uses the same mask-generation logic as the reported workflow
- produces reproducible panel outputs

## Current Limitation

The current `review_pack` implementation is intentionally simple.

It does **not** yet:
- automatically carry the category label from the parent folder into `review.csv`
- generate multi-panel figure boards grouped by category
- add text annotations directly on the panel image
- choose representative examples automatically from particle statistics

## Future Config Extensions (Recommended)

Later, if you want this to be more automatic, the cleanest additions would be:

1. `review_pack.category_from_parent_dir: true`
   - writes the immediate parent folder name into `review.csv`

2. `review_pack.copy_category_panels: true`
   - writes panels into category-specific subfolders

3. `review_pack.include_source_mask_metrics: true`
   - carries threshold, retained count, isolated count, and diameter summary into `review.csv`

4. `review_pack.selection_csv`
   - optional explicit file list with category labels
   - avoids relying on folder names alone

5. `review_pack.contact_sheet.enable: true`
   - builds grouped figure boards automatically for thesis figures

## Thesis Placement

This SOP is best used as:
- appendix/supporting material
- a verification artifact for Chapter 5
- a practical figure-generation guide for Chapter 6 and later chapters

The main Chapter 5 text should only reference this SOP briefly and keep the statistical workflow itself in the chapter body.
