# Chapter 5 Section Blueprint

## Chapter Role

Chapter 5 is the **Stage 1 statistical validation framework** chapter.

Its job is to define:
- how particle candidates were identified
- how candidate particles were filtered
- how isolation was defined
- how the count model was constructed
- how required scan counts were calculated

It should **not** read like a results chapter.

It should **not** contain:
- final per-wt% outcome claims
- extended interpretation of scraped vs non-scraped behavior
- Stage 2 conclusions
- broad discussion that belongs in Chapter 6

## 5.1 Particle Counting Workflow

### Purpose
- Define the operational Stage 1 path from scan input to exported particle-count outputs.

### Must include
- a short opening paragraph tying Chapter 5 to the Stage 1 validation framework
- compact terminology definitions only as needed to avoid ambiguity
- config-driven workflow summary
- software environment note
- active job table
- processing-method definition table written in reader-facing language
- active default-parameter table
- relationship between per-scan outputs and exported CSV fields

### Keep / defer
- Keep: workflow definition and reproducibility-critical settings
- Defer: comparative performance outcomes to Chapter 6

### Closing sentence target
- End by stating that the raw particle-count workflow still requires physical filtering before the counts are meaningful for Stage 2 feasibility.

## 5.2 Diameter Filtering

### Purpose
- Define how raw grains become retained candidate particles.

### Must include
- equivalent circular diameter definition
- conversion from area to equivalent diameter
- active diameter band
- edge exclusion rule
- clear distinction between raw grains and retained candidate particles

### Keep / defer
- Keep: numeric filtering rules
- Defer: whether the retained diameter distribution is acceptable to Chapter 6

### Closing sentence target
- End by stating that retained candidate particles were then evaluated for spatial isolation.

## 5.3 Isolation Criteria

### Purpose
- Define what makes a retained candidate particle useful for Stage 2.

### Must include
- numeric center-to-center distance rule
- nearest-neighbor logic
- why isolation is the relevant Stage 1 criterion
- clarify scan vs grid if needed, but do not spin this into a glossary section

### Keep / defer
- Keep: isolation definition and rationale
- Defer: isolation frequencies and group differences to Chapter 6

### Closing sentence target
- End by stating that isolated-particle count per scan is the key random variable used in the statistical model.

## 5.4 Isolation Probability Modeling

### Purpose
- Define the baseline count model used to convert isolated-particle frequency into scan sufficiency.

### Must include
- random variable definition for isolated particles per scan
- Poisson baseline model
- zero-count risk concept
- total-count accumulation across scans
- distinction between estimating the isolated-particle rate and achieving a target total isolated-particle count

### Keep / defer
- Keep: model form and assumptions
- Defer: fitted values and per-group outcomes to Chapter 6

### Closing sentence target
- End by stating that the model enables a confidence-based required scan count.

## 5.5 Required Map Count for 95% Confidence

### Purpose
- Define the decision calculation used to determine scan sufficiency.

### Must include
- target isolated-particle count
- confidence level
- smallest-n definition satisfying the 95% confidence threshold
- contrapositive / zero-isolated-particle framing
- clear note that the thesis result is confidence-based, not just a heuristic shortcut

### Keep / defer
- Keep: equations, symbols, and decision rule
- Defer: actual required map counts by system to Chapter 6

### Closing sentence target
- End by stating that this scan-sufficiency rule is later applied to the Stage 1 dataset in Chapter 6.

## 5.6 Processing-Route Validation

### Purpose
- Explain why route consistency was checked and how prior direction-comparison work informed the active Stage 1 design.

### Must include
- why multiple topography processing routes were retained as validation support
- forward-only selection rationale tied to prior modulus forward/backward comparison
- statement that route validation is about consistency of the Stage 1 conclusion, not exhaustive optimization
- brief note that broader route-comparison outcomes are presented in Chapter 6 or future work as appropriate

### Keep / defer
- Keep: method-selection and validation rationale
- Defer: route-by-route quantitative outcomes to Chapter 6

### Closing sentence target
- End by stating that, with workflow, filtering, isolation, and validation logic defined, Chapter 6 can present the Stage 1 feasibility results.

## Writing Order Recommendation

Write these sections in this order:

1. 5.1 Particle Counting Workflow
2. 5.2 Diameter Filtering
3. 5.3 Isolation Criteria
4. 5.4 Isolation Probability Modeling
5. 5.5 Required Map Count for 95% Confidence
6. 5.6 Processing-Route Validation
6. 5.8 Required Scan Count for 95% Confidence
7. 5.3 Dataset Structure and Scan Selection
8. 5.9 Processing Sensitivity and Validation Scope
9. 5.10 Reproducibility and Validation Artifacts
10. 5.1 Chapter Purpose and Scope
11. 5.11 Chapter Summary

That order usually produces cleaner initial draft text because the definitional core is written first, and the framing sections can then be written around it.
