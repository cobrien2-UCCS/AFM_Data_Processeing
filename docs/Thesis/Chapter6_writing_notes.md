# Chapter 6 Writing Notes (Read Before Drafting)

## Chapter 6 Purpose (Do Not Drift)

- Core question: *Are particles present in statistically sufficient quantity and isolation to justify Stage 2?*
- This chapter is allowed limited interpretation, but keep it strictly about **measurement feasibility**.
- Scope limit: do **not** report interphase thickness, radial gradients, or modeling parameterization.

## Terminology Rule For Chapter 6

- Do **not** let Chapter 6 become the place where project vocabulary is first defined.
- Terms such as `job`, `profile`, `processing mode`, `candidate particle`, `isolated particle`, `grain`, and `baseline` should be defined in Chapter 5.
- In Chapter 6, use those terms consistently and add only short reminder phrases when needed.
- At the first use of specialized workflow language, add a brief pointer back to Chapter 5 definitions.
- Use the agreed nomenclature consistently across section text, captions, and tables; avoid swapping labels for the same object mid-chapter.

## Ordering Matters

1. Start with **baseline PEGDA validation**, and this should explicitly include the **modulus baseline workflow**.
2. Then move to particle presence and diameter distribution.
3. Then isolation, required scans, and the decision statement.
4. Then processing-route sensitivity.
5. Then Stage 2 trigger / crossover synthesis only if it remains tightly tied to feasibility.

## Must-Haves in Chapter 6

- Baseline PEGDA validation section must include modulus results, not just topography credibility language.
- Baseline PEGDA validation section must also state how units are carried through the workflow:
  - Gwyddion-derived outputs inherit the physical unit attached to the active data field.
  - In the current modulus baseline workflow, the source `summary.csv` files explicitly report `kPa`.
  - Any report-level rescaling for readability should be identified as a display conversion, not a change to the underlying source data.
- Scan inventory table: number of scans, scan size, pixels, nm/pixel, nominal grid size.
- Explicitly state whether zero-count scans exist and show the zero-rate in a table or statement.
- Required scans must be reported per wt% and, if multiple jobs are discussed, per method.
- Stage 2 crossover section must define the crossover rule clearly: availability, risk, or cost crossover.
- Whenever a mean is reported, include the standard deviation alongside it when available.
- Captions, headings, and tables should identify which wt% the result belongs to.
- Clearly distinguish between:
  - retained candidate-particle counts
  - isolated-particle counts
  - Stage 2 confirmed-particle counts (if discussed, likely as future validation only)

## Stage 2 Trigger Language

- Stage 1 provides candidate isolated-particle yield `lambda`.
- Stage 2 determines confirmation rate `p` or assigns `p_j` per candidate.
- Required scans depend on `lambda * p`; if `p` is unknown, show a sensitivity band or crossover plot.

## Captions and Traceability

- Every figure caption should include: polymer, wt% SiNP, wt% TPO, and state `no coating` if applicable.
- If plots are generated from pipeline outputs, include a short source-path line for traceability.
- If a figure is method-specific, state the job/profile directly in the caption.
- If a figure combines multiple methods, say that explicitly in the caption and identify whether it is full-matrix or primary-route only.

## Figure Placement Plan

### 6.1 Processing Validation - Baseline PEGDA (No SiNP)

- This subsection should be treated as **baseline PEGDA validation through the modulus workflow**.
- The purpose is not only to say the pipeline is credible, but to show that the prior modulus study established:
  - forward/backward agreement
  - route consistency
  - a defensible basis for carrying only forward scans into the present Stage 1 topography workflow
- Best figures/tables:
  - forward vs backward modulus comparison
  - modulus method-comparison summary table
  - one compact baseline validation bar plot or comparison figure
- If a separate modulus report artifact is generated, Chapter 6 should pull only the key summary outputs into the body.

### 6.2.1 Scan Inventory

- Put the scan inventory table first in this subsection.
- If a figure is used here, keep it simple:
  - one grid-layout reference figure or one schematic
- Do not clutter this subsection with result-heavy plots.

### 6.2.2 Particle Count Per Scan

- First figure:
  - histogram of particle counts per scan, separated by wt%
- Second figure:
  - grid count heatmap for each wt% using the primary or baseline method
- Best placement:
  - histogram immediately after reporting mean, std, min, and max
  - heatmap after the text that discusses spatial variability
- Purpose:
  - histogram = overall distribution
  - grid heatmap = spatial pattern and clustering

### 6.2.3 Particle Diameter Distribution

- Insert the diameter histogram directly after the paragraph that states the retained diameter band and mean/std.
- If multiple methods are shown, keep the chapter body to the primary method and move the full comparison set to later comparison text or appendix.
- Purpose:
  - confirm that the retained population is physically plausible

### 6.3.1 Isolation Count Per Scan

- First figure:
  - histogram of isolated particles per scan
- Second figure:
  - isolated-particle grid heatmap
- Best placement:
  - histogram after defining the isolation threshold and reporting percent of scans with `>= 1` isolated particle
  - heatmap after discussing where isolated particles occur spatially
- Purpose:
  - shift the chapter from particle presence to particle usability

### 6.3.2 Required Scans for 95% Confidence

- Put the required-scan table first.
- Follow immediately with the risk or scan-sufficiency figure.
- Best figure type:
  - Poisson risk curve or scan-sufficiency curve
  - zero-count-risk table or plot if available
- Purpose:
  - convert isolation statistics into an operational scan requirement

### 6.4 Processing Route Sensitivity

- Start with the method comparison table.
- Then insert:
  - per-job bar plot for mean isolated particles per scan
  - box plot if it materially helps show spread across scans
- Best placement:
  - bar plot after the paragraph stating whether the conclusion is robust to method choice
- Purpose:
  - quantify whether preprocessing and masking change the Stage 1 conclusion

### 6.5 Stage 2 Trigger / Crossover Decision

- This section needs the crossover figure as the main figure.
- Best figure type:
  - required scan count vs validation probability `p`
  - horizontal line for available scans
  - optional uncertainty band if `p` is treated probabilistically
- Best placement:
  - immediately after introducing `lambda`, `p`, and the Stage 2 sensitivity logic
- Purpose:
  - this is the synthesis figure of the chapter

### 6.6 Stage 1 Decision

- No figure required unless one compact summary table is needed.
- If anything is added here, prefer a short decision table over another plot.

### 6.7 Discussion

- Avoid introducing new heavy figures here.
- If needed, refer back to an earlier figure rather than adding a new one.

## Recommended Main-Text Figures for Chapter 6

- Figure 6.1: modulus baseline validation figure
- Figure 6.2: modulus forward/backward or route-comparison summary figure
- Figure 6.2: particle count histogram by wt%
- Figure 6.3: particle count grid heatmap by wt%
- Figure 6.4: particle diameter histogram by wt%
- Figure 6.5: isolated-particle histogram by wt%
- Figure 6.6: isolated-particle grid heatmap by wt%
- Figure 6.7: required scans or risk curve
- Figure 6.8: method comparison bar plot
- Figure 6.9: Stage 2 crossover plot

## What Stays Out of the Main Body Unless Needed

- Full per-job histogram sets
- Excess duplicate heatmaps
- All grain plots at once
- Full debugging artifact figures
- Full modulus companion-report detail beyond the key baseline validation summaries

These belong in appendices, supplementary material, or selective in-text callouts.

## Reader Clarity Checks

- If a result sentence would confuse someone who has not lived inside the pipeline, simplify the sentence or move the definition back to Chapter 5.
- Distinguish clearly between:
  - candidate count
  - isolated count
  - confirmed particle count
- Distinguish clearly between:
  - primary route results
  - full method-matrix comparisons
  - provisional method conclusions pending rerun/fix propagation

## New Points To Carry Into Drafting

- `6.1` must explicitly say that the baseline PEGDA validation was carried by the modulus workflow and that this section is the results-side counterpart to the Chapter 5 processing-route validation logic.
- The forward-only choice used in the topography Stage 1 workflow should be tied back to the baseline modulus forward/backward agreement here, but only briefly because the method rationale is already defined in Chapter 5.
- A separate modulus report artifact is acceptable and likely helpful, but Chapter 6 should use only the figures/tables needed to satisfy the outline's baseline-validation requirement.
- `6.1` should also make the unit provenance explicit:
  - modulus source summaries in this workflow currently carry `units = kPa`
  - a direct one-file verification run showed that pygwy did not detect embedded z-units for the tested modulus TIFF, so this should be framed as a workflow fallback/default assignment pending upstream metadata verification
  - count outputs are count-based and do not inherit a physical z-unit
  - particle/grain diameter outputs are derived geometric metrics reported in `nm`
- Keep the negative-value modulus verification issue separate from the validated modulus comparison outputs: the one-file unit-verification run exported a negative modulus value, but the broader modulus comparison CSV sets used for baseline validation remained non-negative. This should be framed as an open validation issue that may require a targeted modulus rerun.
- Add a second modulus caution: the absolute modulus magnitude currently appears higher than expected for PEGDA, even when the field remains relatively uniform spatially. This should be framed as a likely systematic-offset issue rather than a random map artifact.
- State that the present modulus baseline section remains useful for **relative route-consistency and forward/backward comparison**, but not yet as final proof of absolute PEGDA modulus magnitude.
- Candidate causes to note:
  - unit/metadata interpretation
  - AFM setpoints or force regime
  - calibration parameters
  - upstream force-model / pinpoint-processing settings
  - or another systematic offset in the measurement chain
- Recommended validation path:
  - inspect raw pinpoint / force-curve data
  - verify setpoints and force conditions
  - verify calibration parameters and model settings
  - confirm TIFF/export scaling before Gwyddion ingestion

- In the particle-count subsection, explain what the histogram **frequency** axis means:
  - it is the number of scans falling at each retained-particle count.
- In the particle-count subsection, explain that the current heatmaps are **mean count maps** across grouped sample sets and therefore do not show per-position standard deviation unless an explicit companion plot is added.
- In the isolation subsection, define `primary lambda` explicitly as the mean isolated-particle count per scan under the primary route.
- In the required-scan subsection, define `observed zero-isolated rate` explicitly as the fraction of scans with zero isolated particles.
- In the required-scan subsection, make explicit that `95%` refers to the modeled success probability of obtaining at least the target isolated-particle total.
- Carry the scraped/non-scraped interpretation into the processing-sensitivity discussion:
  - for the current Stage 1 fits, scraped subsets generally require more scans than non-scraped subsets to reach the 30-isolated-candidate, 95%-confidence target
  - this difference is much stronger for 10 wt% than for 25 wt%
  - the 25 wt% scraped subset shows substantial overlap across several submethods, which should be treated as a real feature of the current fitted outputs unless later reruns show otherwise
- In the grain section, clarify whether a figure is:
  - a single-method summary
  - or a full-method matrix summary
- Use the grain section as secondary support only:
  - grain summaries and box plots should be framed as evidence that the segmentation output is broadly consistent across methods
  - they should not replace the primary Stage 1 decision metrics, which remain isolated-particle yield and required scan count
- If the existing grain summary table plus grain box plots already show the intended distribution story clearly, keep them and avoid replacing them with a weaker mean-only bar summary.
- In the processing-sensitivity section, focus on the practical conclusion:
  - method choice changes isolated yield
  - which changes required scan count
  - which changes the practical scan-efficiency conclusion

## Inventory And Sufficiency Notes

- State explicitly that some `25 wt%` grouped sample sets had incomplete scan inventories relative to the nominal `21 x 21` grid.
- Also state explicitly that, despite unequal inventory between `10 wt%` and `25 wt%`, both datasets are well above the modeled minimum scan requirement for the current Stage 1 question.
- Make clear that fewer scans in `10 wt%` do **not** imply insufficient statistical support if the modeled sufficiency threshold has already been exceeded.

## Scraped Vs Non-Scraped Interpretation Notes

- State clearly that scraped versus non-scraped was not a planned balanced experimental factor.
- It was an AFM-access accommodation introduced when fracture topography was too severe for practical scanning.
- Therefore treat the scraped/non-scraped comparison as exploratory and observational, not as a definitive causal sample-preparation study.
- If the scraped grouped sample sets require more scans, interpret that as lower isolated-particle yield under Stage 1, not automatically lower or higher particle quality.
- Use that point to justify why Stage 2 remains necessary: Stage 1 count sufficiency does not establish the quality or validity of the retained targets.

## Crossover / Risk Figure Notes

- Figure 6.9 horizontal dashed lines are fixed probability reference levels (for example `0.90`, `0.95`, `0.99`), not uncertainty bands.
- Figure 6.10 must define the crossover quantity clearly. It is **not** the probability that a crossover occurs.
- The availability crossover `p` means the minimum Stage 2 confirmation fraction required for the currently available scan inventory to remain sufficient.
- Add explicit labels on the plots for:
  - the `0.95` success line
  - the available-scan line
  - the intersection / crossover point
- If Table 6.8 remains in the chapter, the surrounding text must explicitly connect the table values to the crossover figure.

## Discussion Section Notes
- Keep compact decision-driving tables in the chapter body and move very wide all-method detail tables to appendix/supporting material.
- Use the shared topo synthesis tables as the source for chapter tables so Chapter 6 and the topo report stay synchronized.

- Add a short discussion point on the **minimum scan inventory needed to justify use of the Poisson model**.
- That discussion should separate:
  - enough scans to fit or trust the count model
  - enough scans to reach the isolated-particle target
- This belongs in discussion/limits because it is about model justification, not just the observed result.

## Next Session Lock List For Chapter 6

- Treat the current chapter as mostly locked and focus only on targeted figure/table cleanup plus added discussion text.
- Figure 6.3:
  - pair the `10 wt%` mean map with its `10 wt%` standard-deviation companion
  - pair the `25 wt%` mean map with its `25 wt%` standard-deviation companion
  - do not separate them as `10 mean, 25 mean, 10 std, 25 std`
- Figure 6.4:
  - add explicit `10 wt%` and `25 wt%` wording in the titles
- Figure 6.5 / isolated-count figures:
  - keep the same mean-plus-std pairing logic used for Figure 6.3
- Table 6.7:
  - move the large method-level grain table to appendix/supporting material
- Grain section in the main body:
  - keep the compact grain summary table
  - keep the grain distribution / box-plot figure
- Table 6.8:
  - keep as a summary table, not the oversized all-detail version
- Figure 6.8:
  - use box plots rather than the old crowded all-method presentation
- Add more thesis-style discussion text throughout the chapter using the user's direct observations, rather than report/log phrasing.
- Keep a representative raw particle/topography image near the front of `6.2.2`, before the mean density maps.

## Uncertainty / Error Sources To Acknowledge (Chapter 6)

These points belong in results-side discussion/limits as context for why counts, modulus magnitudes, and filtering behavior can vary even under consistent pipeline settings.

- Instrument feedback/servo tracking quality:
  - If error channels are not exported, we cannot quantify tracking instability directly; treat as a limitation.
  - If available later, add a short QA table/plot summarizing per-scan error-channel percentiles and flagged scans.
- Calibration/systematic uncertainty (modulus):
  - Absolute modulus magnitude depends on calibration and model settings upstream; relative comparisons remain useful but absolute values may require independent validation.
- Setpoint/force-regime consistency:
  - If setpoint/force conditions differ between scans or days, those differences can dominate the absolute modulus spread even when maps look spatially uniform.
- Drift / scan distortion:
  - Distortion can affect perceived particle geometry and isolation distances; treat as a potential bias, especially when comparing across sample sets acquired on different days.
- Tip convolution / geometric bias for particles:
  - Particle sizing from topography should be described as effective/segmented geometry, not a direct measurement of true particle diameter.
- Workflow/method sensitivity:
  - Differences across preprocessing families and threshold variants represent workflow-induced uncertainty; interpret overlaps and separations as sensitivity bounds, not as a single "true" value.

## Statistical Assumptions / Limits (Thesis Language)

Use the following thesis-safe language to frame rigor without over-claiming:

- Scan quality screening:
  - Because instrument error/feedback channels were not exported in the present Stage 1 dataset, tracking stability cannot be quantified directly and remains a limitation of this feasibility analysis.
- Systematic modulus uncertainty:
  - Absolute modulus magnitudes depend on calibration and upstream model settings; therefore the modulus baseline validation is interpreted primarily as a relative route-consistency and direction-consistency check, not as final proof of absolute PEGDA modulus magnitude.
- Count-model assumptions:
  - The Poisson model is used as a baseline count model to convert observed isolated-candidate yield into scan requirements at fixed confidence. Method sensitivity and preparation-state effects are treated as additional uncertainty beyond the count-model variance.
- Geometry bias:
  - Particle diameter and isolation are computed from segmented topography features and should be interpreted as effective geometry subject to tip-convolution and scan-geometry bias.
