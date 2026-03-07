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

## Ordering Matters

1. Start with **baseline PEGDA validation**, and this should explicitly include the **modulus baseline workflow**.
2. Then move to particle presence and diameter distribution.
3. Then isolation, required scans, and the decision statement.
4. Then processing-route sensitivity.
5. Then Stage 2 trigger / crossover synthesis only if it remains tightly tied to feasibility.

## Must-Haves in Chapter 6

- Baseline PEGDA validation section must include modulus results, not just topography credibility language.
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

- In the particle-count subsection, explain what the histogram **frequency** axis means:
  - it is the number of scans falling at each retained-particle count.
- In the particle-count subsection, explain that the current heatmaps are **mean count maps** across grouped sample sets and therefore do not show per-position standard deviation unless an explicit companion plot is added.
- In the isolation subsection, define `primary lambda` explicitly as the mean isolated-particle count per scan under the primary route.
- In the required-scan subsection, define `observed zero-isolated rate` explicitly as the fraction of scans with zero isolated particles.
- In the required-scan subsection, make explicit that `95%` refers to the modeled success probability of obtaining at least the target isolated-particle total.
- In the grain section, clarify whether a figure is:
  - a single-method summary
  - or a full-method matrix summary
- In the processing-sensitivity section, focus on the practical conclusion:
  - method choice changes isolated yield
  - which changes required scan count
  - which changes the practical scan-efficiency conclusion

## Inventory And Sufficiency Notes

- State explicitly that some `25 wt%` grouped sample sets had incomplete scan inventories relative to the nominal `21 x 21` grid.
- Also state explicitly that, despite unequal inventory between `10 wt%` and `25 wt%`, both datasets are well above the modeled minimum scan requirement for the current Stage 1 question.
- Make clear that fewer scans in `10 wt%` do **not** imply insufficient statistical support if the modeled sufficiency threshold has already been exceeded.

## Scraped Vs Non-Scraped Interpretation Notes

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

- Add a short discussion point on the **minimum scan inventory needed to justify use of the Poisson model**.
- That discussion should separate:
  - enough scans to fit or trust the count model
  - enough scans to reach the isolated-particle target
- This belongs in discussion/limits because it is about model justification, not just the observed result.
