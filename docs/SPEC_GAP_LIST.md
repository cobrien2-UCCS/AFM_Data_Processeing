# Spec Alignment + Gap List (Working Checklist)

This document maps the current repo implementation to the design intents in `AFM TIFF to Summary Stats & Plotting Pipeline v3.md` and tracks what to shore up next.

## Still aligned with the spec (core intent)
- Config-first behavior: processing/CSV/schema/plotting behavior is controlled by config (`modes`, `csv_modes`, `result_schemas`, `plotting_modes`, `profiles`, `unit_conversions`).
- Dataflow matches the mental model: TIFF → pygwy/Gwyddion processing → ModeResultRecord → CSV (csv_mode) → typed rows (result_schema) → plots (plotting_mode).
- Gwyddion-first philosophy: pygwy is used for core preprocessing; Python-side math is explicit and config-driven.

## Gaps / weak areas to shore up

### 0) Plotting bugs (low priority)
- Current state: plotting works and is config-driven; some layout warnings (tight_layout with extra axes) and legend placement ergonomics remain.
- Next: treat as low priority; address once processing/stats validity is confirmed.

### 0.5) Validate Gwyddion stats correctness (highest priority)
- Goal: confirm pygwy/Gwyddion-derived values (avg/std) are meaningful **before** applying Python-side filters or using results for conclusions.
- Rationale: if preprocessing or units are wrong, downstream filtering/plotting “looks” plausible but is not valid.
- Actions:
  - Add an explicit “stats provenance” debug report per file: raw stats (min/max/pct), post-op stats, n_valid after each filter step.
  - Compare against a ground-truth run in Gwyddion GUI for a small sample set (same ops + same mask).
  - Confirm unit detection/conversion matches the GUI-reported units for those samples.

### 1) Filename parsing + metadata (spec 5.7 intent)
- Current state: Py2 runner does “best-effort” filename metadata parsing (channel/date_code/grid_id/direction).
- Risk: “hidden assumptions” creep into code and may not match all datasets.
- Next: move filename parsing to a fully config-driven pattern/template so metadata extraction is declarative and dataset-specific.

### 2) Preprocessing / mode parity (spec 3.3.*)
- Current state: modulus/topography are minimal (plane level, optional align rows, median, optional clip, optional mask, value filtering).
- Risk: real AFM workflows often require more Gwyddion-native steps (multiple leveling, flattening variants, denoise pipelines, scar/line mismatch correction).
- Next: expose a config-driven ordered list of Gwyddion ops (module calls + params) per mode so you can replicate interactive Gwyddion workflows without code edits.

### 3) Masking (ROI) semantics
- Current state: config-driven value masks affect which pixels contribute to stats; this is not yet a full “Gwyddion mask channel” workflow.
- Risk: mismatch vs what you do interactively in Gwyddion when masking ROIs.
- Next: add a Gwyddion-native mask stage option (create/apply masks, export mask artifacts) and clarify mask composition ordering in config.

### 4) Unit detection/normalization robustness
- Current state: unit conversions work for common `Pa/kPa/MPa/GPa` strings.
- Risk: Gwyddion unit strings can vary; normalization should handle common variants to avoid silent unit mismatch.
- Next: harden unit normalization, document expected unit strings, and add warnings when conversions do not apply.

### 5) Plotting / uncertainty visualization (spec plotting intent)
- Current state: multiple plotting modes exist including heatmap overlays, bubbles, CV, two-panel.
- Risk: visual defaults need tuning per dataset; some modes (range) depend on optional min/max presence.
- Next: add small “golden” tests for derived fields and overlay configurations; document recommended defaults per plot type.

### 6) Test coverage (including upcoming topography)
- Current state: Py3 tests exist; Py2/pygwy tests are limited by environment.
- Gap: **Topography statistics and topo-specific preprocessing need dedicated testing**.
- Plan: when you provide a topo test folder, add topo-focused configs + run suite outputs, and add Py3-side tests that validate plotting and parsing on topo CSVs (and sanity-check expected ranges).

### 7) Processing step trace / debug transparency
- Current state: debug logging includes units, mask/stats counts, pyfilter counts, and some artifacts.
- Risk: stakeholders may need “what Gwyddion did” per file (a step-by-step trace).
- Next: add a per-file step trace log (ops executed + parameters + success/fail) and optionally write a JSON “run report” alongside summary.csv.

## Out-of-scope note (per spec 1.7)
The spec lists “file manifest utilities” as out-of-scope for the *core* API. This repo includes optional helpers (`scripts/make_job_manifest.py`, `scripts/run_config_suite.py`) as wrappers; they should remain optional and not change the core data model.
