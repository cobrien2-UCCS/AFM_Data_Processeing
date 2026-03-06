# Chapter 6 Writing Notes (Read Before Drafting)

## Chapter 6 Purpose (Do Not Drift)

- Core question: *Are particles present in statistically sufficient quantity and isolation to justify Stage 2?*
- This chapter is allowed limited interpretation, but keep it strictly about *measurement feasibility*.
- Scope limit: do **not** report interphase thickness, radial gradients, or modeling parameterization.

## Ordering Matters

1. Start with baseline validation (pipeline credibility).
2. Then particle presence + diameter distribution.
3. Then isolation + required scans + decision statement.
4. Then processing route sensitivity.
5. Then Stage 2 trigger / crossover synthesis.

## Must-Haves in Chapter 6

- Scan inventory table: number of scans, scan size, pixels, nm/pixel, nominal grid size.
- Explicitly state whether zero-count scans exist and show the zero-rate in a table or statement.
- Required scans must be reported per wt% and, if multiple jobs are discussed, per method.
- Stage 2 crossover section must define the crossover rule clearly: availability, risk, or cost crossover.

## Stage 2 Trigger Language

- Stage 1 provides candidate isolated particle yield `lambda`.
- Stage 2 determines confirmation rate `p` or assigns `p_j` per candidate.
- Required scans depend on `lambda * p`; if `p` is unknown, show a sensitivity band.

## Captions and Traceability

- Every figure caption should include: polymer, wt% SiNP, wt% TPO, and state `no coating` if applicable.
- If plots are generated from pipeline outputs, include a short source-path line for traceability.
- If a figure is method-specific, state the job/profile directly in the caption.

## Figure Placement Plan

### 6.1 Processing Validation - Baseline PEGDA (No SiNP)

- Insert one baseline validation figure near the end of the subsection, after the paragraph that establishes workflow credibility.
- Best figure type:
  - baseline method-comparison bar plot, or
  - forward/backward comparison if that is the clearest baseline validation
- Purpose:
  - show that the workflow is stable before any particle-containing claims are made

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

- Figure 6.1: baseline validation figure
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

These belong in appendices, supplementary material, or selective in-text callouts.
