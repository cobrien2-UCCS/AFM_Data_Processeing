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

## 5.1 Data Organization and Preprocessing

### Purpose
- Define the Stage 1 dataset organization, preprocessing environment, and the path from scan input to processed analysis-ready scans.

### Must include
- a short opening paragraph tying Chapter 5 to the Stage 1 validation framework
- compact terminology definitions only as needed to avoid ambiguity
- grouped scan structure and nominal grid description
- config-driven workflow summary
- software environment note
- image or figure showing the nominal grid or grouped scan structure

### Keep / defer
- Keep: workflow definition and reproducibility-critical settings
- Defer: comparative performance outcomes to Chapter 6

### Closing sentence target
- End by stating that the preprocessed scans then enter the particle detection and counting workflow.

## 5.2 Particle Detection and Counting

### Purpose
- Define how processed scans are segmented and how raw segmented features become exported Stage 1 count fields.

### Must include
- active job table
- processing-method definition table written in reader-facing language
- active default-parameter table
- relationship between per-scan outputs and exported CSV fields
- clear distinction between raw grain count, retained candidate count, and isolated count

### Keep / defer
- Keep: workflow definitions and exported fields
- Defer: route comparison outcomes to Chapter 6

### Closing sentence target
- End by stating that the retained raw features are then constrained by the particle diameter rules.

## 5.3 Particle Diameter Distribution

### Purpose
- Define how raw grains become retained candidate particles.

### Must include
- equivalent circular diameter definition
- conversion from area to equivalent diameter
- active diameter band (`350-550 nm` for the current Stage 1 dataset)
- edge exclusion rule
- clear distinction between raw grains and retained candidate particles
- note that equivalent circular diameter is an area-based simplification and does not prove the retained grain is circular
- brief statement on whether circularity filtering was or was not active in the current workflow

### Keep / defer
- Keep: numeric filtering rules
- Keep: a short caution that topography measures an apparent surface feature after fracture, not the full three-dimensional particle geometry
- Defer: whether the retained diameter distribution is acceptable to Chapter 6
- Defer: any fuller discussion of fracture geometry to Chapters 3 and 4

### Closing sentence target
- End by stating that retained candidate particles were then evaluated for spatial isolation.

## 5.4 Isolation Analysis

### Purpose
- Define what makes a retained candidate particle useful for Stage 2.

### Must include
- numeric center-to-center distance rule
- `900 nm` rationale
- nearest-neighbor logic
- why isolation is the relevant Stage 1 criterion
- clarify scan vs grid if needed, but do not spin this into a glossary section

### Keep / defer
- Keep: isolation definition and rationale
- Defer: isolation frequencies and group differences to Chapter 6

### Closing sentence target
- End by stating that isolated-particle count per scan is the key random variable used in the statistical model.

## 5.5 Isolation Probability Model

### Purpose
- Define the baseline count model used to convert isolated-particle frequency into scan sufficiency.

### Must include
- random variable definition for isolated particles per scan
- Poisson baseline model
- why the Poisson model is needed for the Stage 1 feasibility question
- zero-count risk concept
- total-count accumulation across scans
- distinction between estimating the isolated-particle rate and achieving a target total isolated-particle count
- plain-language explanation of why this is a Poisson count model rather than a "Poisson ratio" trend
- required scan count at 95% confidence
- clear explanation of the difference between standard deviation and standard error where both particle and modulus summaries are referenced nearby

### Keep / defer
- Keep: model form and assumptions
- Defer: fitted values and per-group outcomes to Chapter 6

### Closing sentence target
- End by stating that the model yields the confidence based Stage 1 decision rule.

## 5.6 Processing Route Validation

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
- End by stating that route validation supports the use of the final Stage 1 decision rule rather than replacing it.

## 5.7 Stage 1 Decision Statement

### Purpose
- State the explicit Chapter 5 rule that determines when the Stage 1 dataset is considered sufficient to justify Stage 2 follow-up.

### Must include
- target isolated-particle count
- confidence level
- smallest-n definition satisfying the 95% confidence threshold
- contrapositive or zero-isolated-particle framing
- plain-language restatement of what it means to satisfy the Stage 1 requirement

### Keep / defer
- Keep: the formal decision rule and its interpretation
- Defer: actual system-by-system outcomes to Chapter 6

### Closing sentence target
- End by stating that Chapter 6 applies this rule to the reported datasets.

## Writing Order Recommendation

Write these sections in this order:

1. 5.1 Data Organization and Preprocessing
2. 5.2 Particle Detection and Counting
3. 5.3 Particle Diameter Distribution
4. 5.4 Isolation Analysis
5. 5.5 Isolation Probability Model
6. 5.6 Processing-Route Validation
7. 5.7 Stage 1 Decision Statement

That order usually produces cleaner draft text because the definitional core is written first and the route-validation section is then written as the bridge into Chapter 6.
