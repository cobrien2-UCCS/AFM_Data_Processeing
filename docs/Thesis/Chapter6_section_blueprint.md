# Chapter 6 Section Blueprint

This file is a prose blueprint for drafting Chapter 6 quickly from the current Stage 1 outputs.

## 6.1 Processing Validation - Baseline PEGDA (No SiNP)

Opening sentence:
The results chapter begins by establishing that the processing workflow is sufficiently stable to support interpretation of particle-containing systems.

Evidence to include:
- baseline method-comparison figure
- short statement on internal consistency
- note on any false-positive topo detections if available

Closing sentence:
Taken together, the baseline results justify treating the subsequent Stage 1 particle statistics as products of a controlled and internally consistent workflow.

## 6.2.1 Scan Inventory

Opening sentence:
With the workflow established, the PEGDA-SiNP Stage 1 dataset was first summarized in terms of scan inventory and spatial coverage.

Evidence to include:
- scan inventory table
- number of scans per wt%
- scan size, pixels, resolution, nominal grid
- note on incomplete grids / blacklist handling

Closing sentence:
This inventory defines the spatial sampling basis for all subsequent particle-count and isolation results.

## 6.2.2 Particle Count Per Scan

Opening sentence:
Candidate particle presence was evaluated first through the distribution of retained particle counts per scan.

Evidence to include:
- mean, std, min, max by wt%
- count histogram
- grid heatmap

Closing sentence:
These results confirm that particle-like features were present across the Stage 1 dataset, although their spatial frequency was not uniform from scan to scan.

## 6.2.3 Particle Diameter Distribution

Opening sentence:
To evaluate whether the retained candidate population remained physically plausible, the particle diameter distribution was examined after filtering.

Evidence to include:
- diameter histogram
- mean and std diameter
- explicit numeric filter band

Closing sentence:
The retained diameter distribution therefore serves as a consistency check on the detection pipeline rather than as a claim of complete particle identity.

## 6.3.1 Isolation Count Per Scan

Opening sentence:
Because Stage 2 interrogation requires spatially separable targets, particle isolation rather than gross particle presence is the primary feasibility metric.

Evidence to include:
- isolation threshold definition
- isolated-particle histogram
- isolated-particle heatmap
- percent of scans with >= 1 isolated particle

Closing sentence:
This shifts the feasibility question from whether particles are present to whether usable particles are present often enough to support targeted follow-up measurements.

## 6.3.2 Required Scans for 95% Confidence

Opening sentence:
The observed isolated-particle statistics were then converted into an operational scan requirement using the Stage 1 probability model.

Evidence to include:
- table of required scans by wt% and method
- risk/sufficiency figure
- zero-count risk statement

Closing sentence:
This provides the first direct answer to the Stage 1 feasibility question in terms of required scanning effort rather than descriptive particle counts alone.

## 6.5 Processing Route Sensitivity

Opening sentence:
To test whether the Stage 1 conclusion was robust, the same datasets were compared across multiple reasonable preprocessing and masking routes.

Evidence to include:
- method comparison table
- isolated-count bar plot
- percent difference vs baseline

Closing sentence:
The purpose of this comparison is not to select a visually preferred workflow, but to determine whether method-dependent variation is large enough to alter the feasibility conclusion.

## 6.6 Stage 2 Trigger / Crossover Decision

Opening sentence:
The Stage 1 results were next extended into a Stage 2 trigger framework by accounting for the possibility that only a fraction of isolated candidates will be confirmed as true particles.

Evidence to include:
- crossover figure
- definition of lambda and p
- statement about assumed vs measured p

Closing sentence:
This crossover analysis converts Stage 2 from a qualitative next step into a quantitative decision threshold tied to available scans and acceptable risk.

## 6.7 Stage 1 Decision

Opening sentence:
Based on the observed candidate, diameter, and isolation statistics, a direct Stage 1 decision can now be stated for each SiNP loading.

Evidence to include:
- short decision table or paragraph by wt%

Closing sentence:
This section should end with an explicit justified / not justified statement for Stage 2.

## 6.8 Discussion

Opening sentence:
The results define the practical measurement consequences of the current Stage 1 dataset rather than any finalized interphase interpretation.

Evidence to include:
- what the scan-efficiency result means experimentally
- what uncertainty remains
- what Stage 2 would resolve

Closing sentence:
The chapter should close by emphasizing that Stage 1 establishes statistical feasibility boundaries, not interphase property claims.
