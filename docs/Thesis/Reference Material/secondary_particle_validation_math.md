# Secondary Particle Validation Math
## Adjusting True Particle Counts After Secondary Validation (Stage 2)

This document defines a *Stage 1 -> Stage 2* statistical framework for particle counting.
Stage 1 detects **particle candidates** (typically from topography). Stage 2 performs
secondary validation (e.g., modulus/topography overlay) to estimate what fraction of
those candidates are **true SiNP particles**.

The key point: even if Stage 1 yields a high candidate count, the *true* particle yield
is reduced by the validation probability, and that changes the required number of scans.

---

## 1. Definitions

Per scan (one 5 um x 5 um image in the grid):

- $X_i$ = number of detected particle **candidates** in scan $i$ (Stage 1).
- $Y_i$ = number of **confirmed** true particles in scan $i$ (after Stage 2 validation).

Rates / parameters:

- $\\lambda$ = mean Stage 1 candidate count per scan.
- $p$ = probability a detected candidate is a true particle (Stage 2 confirmation rate).
- $N$ = number of scans (grid cells) acquired/processed.

---

## 2. Stage 1 Candidate Count Model (Poisson Baseline)

As a first-order model, treat candidate occurrences as a Poisson process across scans:

```math
X_i \\sim \\mathrm{Poisson}(\\lambda).
```

Then the total number of detected candidates across $N$ scans is:

```math
X_{\\mathrm{tot}} = \\sum_{i=1}^{N} X_i \\sim \\mathrm{Poisson}(N\\,\\lambda), \\qquad
\\mathbb{E}[X_{\\mathrm{tot}}] = N\\,\\lambda.
```

Notes:

- Poisson assumes spatial randomness + independence. If the data are overdispersed
  (clustering), a Negative Binomial model is often a better fit, but Poisson is the
  cleanest starting point for thesis math.

---

## 3. Stage 2 Validation as "Thinning"

If each detected candidate is independently confirmed with probability $p$,
then Stage 2 validation is *Poisson thinning*:

```math
Y_i\\mid X_i \\sim \\mathrm{Binomial}(X_i, p)
\\quad\\Rightarrow\\quad
Y_i \\sim \\mathrm{Poisson}(\\lambda p).
```

Define the **effective true-particle rate** per scan:

```math
\\lambda_{\\mathrm{true}} = \\lambda p.
```

---

## 4. Expected True Particle Yield Across N Scans

```math
Y_{\\mathrm{tot}} = \\sum_{i=1}^{N} Y_i \\sim \\mathrm{Poisson}(N\\,\\lambda p),
\\qquad
\\mathbb{E}[Y_{\\mathrm{tot}}] = N\\,\\lambda p.
```

---

## 5. "Back-of-the-Envelope" Scan Requirement Adjustment

If you only match *expected values* (not a confidence requirement), then to keep
the same expected true-particle total you need:

```math
N_{\\mathrm{adj}} \\approx \\frac{N}{p}.
```

This approximation is useful for intuition, but for rigor (thesis) use the confidence-based
calculation in Section 6.

---

## 6. Confidence-Based Scan Requirement for K True Particles

If the goal is to obtain **at least $K$ true isolated particles** with confidence
$1-\\alpha$ (e.g., 95%), model:

```math
Y_{\\mathrm{tot}} \\sim \\mathrm{Poisson}(N\\,\\lambda p).
```

Then:

```math
\\mathbb{P}(Y_{\\mathrm{tot}} \\ge K)
= 1 - F_{\\mathrm{Poisson}}(K-1;\\, N\\,\\lambda p),
```

and the required number of scans is the smallest $N$ such that:

```math
1 - F_{\\mathrm{Poisson}}(K-1;\\, N\\,\\lambda p) \\ge 1-\\alpha.
```

### Contrapositive / zero-yield risk (important for reporting)

Probability of collecting **zero** true particles after $N$ scans:

```math
\\mathbb{P}(Y_{\\mathrm{tot}} = 0) = \\exp(-N\\,\\lambda p).
```

This is a direct way to quantify the risk of spending time scanning and getting no usable
isolated particles.

---

## 7. Uncertainty in p From Finite Stage 2 Validation

In practice, $p$ is estimated from a finite number of validations:

- Validate $m$ candidates.
- Confirm $k$ are true particles.

A simple Bayesian model is:

```math
p \\sim \\mathrm{Beta}(\\alpha,\\beta),
\\qquad
p\\mid k,m \\sim \\mathrm{Beta}(k+\\alpha,\\, m-k+\\beta).
```

Using $\\alpha=\\beta=1$ (uniform prior) is common.
This gives a credible interval for $p$, which can be propagated to a *band* of required
$N$ values.

---

## 8. Stage 2 "Crossover" / Trigger Plot (What You Should Graph)

Define a target $K$ (e.g., $K=30$ isolated true particles) and a confidence $1-\\alpha$
(e.g., 95%). For each assumed (or estimated) $p$, compute:

```math
N_{\\mathrm{req}}(p) = \\min\\{N : \\mathbb{P}(Y_{\\mathrm{tot}}\\ge K) \\ge 1-\\alpha\\}.
```

**Crossover point** examples (choose one definition and state it explicitly):

- **Availability crossover:** $N_{\\mathrm{req}}(p)$ crosses the number of scans available
  in the Stage 1 dataset.
- **Cost crossover:** expected time/cost to reach $K$ validated particles with and without
  Stage 2 validation are equal (requires scan-time and validation-time inputs).
- **Risk crossover:** $\\mathbb{P}(Y_{\\mathrm{tot}}=0)$ (or $\\mathbb{P}(Y_{\\mathrm{tot}}<K)$)
  crosses an acceptable risk threshold.

This plot is the cleanest way to justify *when Stage 2 becomes necessary*.

---

## 9. Multi-Channel Validation Concept (Topo + Modulus Overlay)

If Stage 2 uses *features* (topography geometry + modulus contrast), then instead of a
single $p$ you can assign a posterior probability for each candidate $j$:

```math
p_j = \\mathbb{P}(\\text{true particle}\\mid \\text{features}_j).
```

An easy thesis-safe aggregation is:

```math
\\lambda_{\\mathrm{true}} \\approx \\frac{1}{N}\\sum_{j=1}^{X_{\\mathrm{tot}}} p_j,
```

and then proceed with Sections 6-8 using $\\lambda_{\\mathrm{true}}$ (or a credible band
around it).

---

## 10. Where This Goes in the Thesis

- Chapter 5: model definition (Sections 1-8) + note that Poisson is the baseline and
  alternative fits (NB/ZINB) can be checked.
- Chapter 6: report estimated $\\lambda$ and (if available) $p$ (or $p_j$ approach),
  plus the crossover plot and the final Stage 1 -> Stage 2 decision statement.

