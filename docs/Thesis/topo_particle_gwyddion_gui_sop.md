# Topography Particle Workflow SOP (Gwyddion GUI Parity)

## Purpose

This SOP describes how a human can reproduce, on a **single AFM scan**, the same topography-particle workflow that the batch pipeline applies through `pygwy`.

Use this document for:
- Chapter 5 method explanation
- appendix material
- one-off GUI validation against pipeline outputs

Do **not** use this SOP as the preferred production workflow for large datasets. The config-driven pipeline remains the authoritative execution path for reportable results.

## Scope

This SOP covers the Stage 1 topography particle workflow used for forward `Z Height` scans:
- preprocessing
- threshold-based particle masking
- grain detection
- diameter filtering
- edge exclusion
- isolation filtering
- manual extraction of per-scan outputs

It does **not** cover:
- Stage 2 multi-channel confirmation
- batch automation
- modulus analysis

## Reader Notes

- In this project, a **scan** is one `5 um x 5 um` AFM image.
- The larger `21 x 21` survey layout is the **grid**.
- A **candidate particle** is a thresholded topographic grain that survives the configured diameter filter.
- An **isolated particle** is a candidate particle whose nearest kept neighbor is at least `900 nm` away center-to-center.
- A **grain** is the segmented feature returned by Gwyddion grain analysis. A grain is not automatically a true particle.

## Forward-Only Rationale

Only **forward** scans are used in this Stage 1 topography workflow. This was a method-selection decision based on the prior modulus validation work, where forward and backward scans were found to correlate closely enough that including both directions would add redundancy without materially changing the Stage 1 feasibility question.

## Pipeline-to-GUI Crosswalk

| Pipeline concept | Config / code name | Manual GUI equivalent | Notes |
| --- | --- | --- | --- |
| Row alignment | `align_rows` | `Data Process -> Correct Data -> Align Rows` | Use horizontal direction and `median` method unless a different method is explicitly being tested. |
| Plane leveling | `plane_level` | `Data Process -> Level -> Plane Level` | Removes global tilt. |
| Median background removal | `median_level` / `median-bg` | Gwyddion median background / median leveling tool | Used in the `medianbg` route. |
| Flatten base | `flatten_base` | `Data Process -> Level -> Flatten Base` | Used in the `flatten` route. |
| Median filter | `median` with `size: 3` | Basic filters -> Median | Use size `3`. |
| Threshold mask | `threshold_strategy` | Grain marking by threshold | Threshold value depends on job/profile. |
| Grain counting | `number_grains()` | Grain analysis / grain marking results | Produces raw segmented grains. |
| Diameter filter | `particle_diameter_min_nm`, `particle_diameter_max_nm` | Grain statistics + manual keep/reject | Keep only grains in the configured diameter band. |
| Edge exclusion | `edge_exclude: true` | Exclude grains touching image boundary | Manual in GUI unless a dedicated border-selection tool is used. |
| Isolation filter | `isolation_min_dist_nm: 900` | Export grain centers, compute nearest-neighbor distance | This is the main step that is not a simple one-click GUI operation. |

## Current Job Families

The current topography particle runs use two preprocessing families:

### 1. Median-background family

Job names:
- `particle_forward_medianbg_mean`
- `particle_forward_medianbg_fixed0`
- `particle_forward_medianbg_p95`
- `particle_forward_medianbg_max_fixed0_p95`

Processing sequence:
1. Align Rows, horizontal, median
2. Plane Level
3. Align Rows, horizontal, median
4. Median background / median level
5. Median filter, size `3`

### 2. Flatten-base family

Job names:
- `particle_forward_flatten_mean`
- `particle_forward_flatten_fixed0`
- `particle_forward_flatten_p95`
- `particle_forward_flatten_max_fixed0_p95`

Processing sequence:
1. Align Rows, horizontal, median
2. Plane Level
3. Align Rows, horizontal, median
4. Flatten Base
5. Median filter, size `3`

## Threshold Definitions

These are the definitions used by the pipeline after preprocessing:

| Threshold route | Config meaning | Manual meaning |
| --- | --- | --- |
| `mean` | `threshold_strategy: mean` | Threshold equals the arithmetic mean of the processed height field. |
| `fixed0` | `threshold_strategy: fixed`, `threshold_fixed: 0.0` | Threshold equals `0.0` in the processed height units. |
| `p95` | `threshold_strategy: percentile`, `threshold_percentile: 95` | Threshold equals the 95th percentile of processed field values. |
| `max_fixed0_p95` | `threshold_strategy: max`, `threshold_fixed: 0.0`, `threshold_percentile: 95` | Threshold equals `max(mean, 0.0, p95)`. |

## Diameter and Isolation Definitions

### Diameter

The pipeline computes an **equivalent circular diameter** from grain area:

\[
d_{eq,px} = 2\sqrt{\frac{A_{px}}{\pi}}
\]

and converts to nanometers using the lateral pixel size.

Use the diameter band from the active run config.

Important note:
- earlier report drafts used `350-550 nm`
- the current corrected rerun config uses `250-550 nm`

So when doing manual GUI validation, always read the active config first.

### Isolation

A kept particle is counted as **isolated** only if the minimum center-to-center distance to every other kept particle is at least:

\[
d_{min} \ge 900\ \text{nm}
\]

This step is not a single native Gwyddion filtering action in the current workflow. In practice, the user should export grain centers and compute nearest-neighbor distances in a spreadsheet or Python.

## Manual SOP Per Scan

## 1. Open the scan

1. Launch Gwyddion.
2. Open the forward `Z Height` scan of interest.
3. Confirm you are using the **forward** topography channel, not backward and not modulus.
4. Duplicate the data field before processing so you preserve the raw scan for visual comparison.

Recommended naming in the GUI:
- `raw`
- `preprocessed`
- `thresholded`

## 2. Apply the shared preprocessing

Choose the preprocessing family you want to reproduce.

### Median-background route

Apply:
1. `Align Rows` -> direction `horizontal`, method `median`
2. `Plane Level`
3. `Align Rows` -> direction `horizontal`, method `median`
4. `Median background` / `Median level`
5. `Median filter`, size `3`

### Flatten-base route

Apply:
1. `Align Rows` -> direction `horizontal`, method `median`
2. `Plane Level`
3. `Align Rows` -> direction `horizontal`, method `median`
4. `Flatten Base`
5. `Median filter`, size `3`

## 3. Determine the threshold value

Read the threshold route from the job/profile being reproduced.

### Mean threshold

1. Read the processed field mean value from Gwyddion statistics.
2. Use that mean as the grain-marking threshold.

### Fixed 0 threshold

1. Use threshold `0.0`.

### 95th percentile threshold

1. Determine the 95th percentile of the processed field values.
2. Use that percentile as the grain-marking threshold.

Practical note:
- If the GUI tool in use does not expose the percentile directly, export the processed field values and compute the percentile outside Gwyddion.

### Combined max threshold

1. Compute:
   - mean
   - fixed `0.0`
   - 95th percentile
2. Use the largest of those values as the threshold.

## 4. Mark grains above threshold

1. Use the grain-marking / threshold tool to mark pixels **above** the threshold.
2. Generate the grain mask.
3. Save or visually inspect the mask next to the processed image.

At this point, the raw segmented grain count corresponds most closely to:
- `count_total_raw`

## 5. Export grain statistics

Use Grain Analysis to obtain at least:
- grain ID
- projected area or pixel area
- equivalent diameter if available
- center coordinates

If equivalent diameter is not reported directly, export area and calculate equivalent diameter yourself.

Recommended fields to retain:
- `grain_id`
- `area_px`
- `diameter_px` or `diameter_nm`
- `center_x`
- `center_y`

## 6. Apply diameter filtering

1. Convert grain diameter to nanometers if needed.
2. Keep only grains inside the active diameter band.

Examples:
- old comparison band: `350-550 nm`
- current corrected rerun band: `250-550 nm`

The number of grains left after this step corresponds most closely to:
- `count_total_filtered`

## 7. Apply edge exclusion

Reject any kept grain that touches the image border.

Operational definition used by the pipeline:
- if grain center minus radius falls outside the image
- or center plus radius exceeds the image extent
- the grain is excluded

Manual GUI approximation:
- remove grains visibly touching or crossing the image boundary
- if needed, use center and diameter values to make the decision numerically

## 8. Apply isolation filtering

1. For each kept grain, compute the center-to-center distance to every other kept grain.
2. Find the nearest neighbor distance.
3. Keep the grain as **isolated** only if:

\[
\min(d_{ij}) \ge 900\ \text{nm}
\]

The count after this step corresponds to:
- `count_isolated`

## 9. Record per-scan outputs

For one manually processed scan, record:
- `count_total_raw`
- `count_total_filtered`
- `count_isolated`
- mean kept particle diameter
- standard deviation of kept particle diameter
- threshold used
- preprocessing route used
- notes on edge removals and ambiguous grains

## Expected Output Mapping

| Manual output | Pipeline field |
| --- | --- |
| raw thresholded grain count | `count_total_raw` |
| count after diameter + edge filters | `count_total_filtered` |
| count after isolation rule | `count_isolated` |
| mean kept diameter | `mean_diam_nm` |
| std kept diameter | `std_diam_nm` |
| threshold value | `threshold` |
| threshold method | `threshold_source` |

## Practical Validation Strategy

For GUI parity checks, do not start with all scans.

Recommended workflow:
1. choose one representative scan
2. reproduce one job manually
3. compare:
   - threshold value
   - raw grain count
   - kept count
   - isolated count
   - kept diameter statistics
4. if that matches, repeat on one harder scan with clustered particles

This is sufficient to validate the manual interpretation of the pipeline without rebuilding the entire dataset by hand.

## Known Limitations of Manual GUI Parity

1. The GUI can reproduce the preprocessing route directly, but some threshold and filtering decisions still require external arithmetic.
2. Isolation filtering is not currently a one-click native Gwyddion action in this workflow.
3. The batch pipeline is still more reproducible because it:
   - applies the same threshold rule every time
   - writes particle and grain CSVs automatically
   - avoids human inconsistency when deciding edge cases

## Recommended Thesis Use

Use this SOP in an appendix and refer to it from Chapter 5 with language like:

> A manual Gwyddion GUI parity SOP was also prepared so that the Stage 1 topography particle workflow could be reproduced on individual scans outside the automated batch pipeline. That SOP is provided in the appendix and was used as a validation aid rather than as the primary production workflow.

