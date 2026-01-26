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
- Current state:
  - Per-file trace JSON records stats snapshots pre/post ops + final stats + exclusion reasons (see `out/debug/traces/*.trace.json`).
  - Python-side filter provenance is also emitted into the trace (`pyfilter_summary` step).
- Next:
  - Compare against a ground-truth run in Gwyddion GUI for a small sample set (same ops + same mask).
  - Validate that the selected channel matches the GUI-selected channel and that preprocessing ordering matches expectation.
  - Confirm unit detection/conversion matches the GUI-reported units (see unit gap below).

### 0.6) TIFF ingestion / “getting valid data” from TIFFs (critical)
- Problem statement: for the current SmartScan-exported modulus TIFFs, pygwy loads the data field but Z-units are missing (`get_si_unit_z().get_unit_string()` returns empty/None), so strict configs skip all files.
- Why this matters: if units/scaling are missing or wrong at ingest, downstream preprocessing, masks, filtering, and plots are not valid even if they “look” reasonable.
- What we know so far:
  - Container keys are minimal (typically `/0/data`, `/0/data/title`, `/0/data/log`, `/0/meta`).
  - `/0/meta` carries descriptive instrument metadata (e.g., “Source name: Modulus”) but does not include explicit Z-units for these samples.
  - Gwyddion/pygwy provides tools that could repair/assign units (`process_func_run("calibrate")`, `DataField.set_si_unit_z()`), but these require an explicit, dataset-scoped decision.
- Actions (exploration tasks):
  - Verify the export path: determine which tool produced the TIFFs and whether it can embed Z-units reliably (preferred fix).
  - Compare Gwyddion GUI vs pygwy: confirm whether the GUI is displaying inferred units (from metadata/channel type) vs units stored in the DataField.
  - Evaluate a “units repair” option (explicit, not silent):
    - Add a config-driven “calibrate/assign units” step (only used when the user opts in).
    - Log whether units were detected vs repaired, and fail/skip if neither is possible.
  - Document the recommended “known-good” ingestion path for modulus and topography TIFFs (so unit metadata and scaling are preserved).

### 1) Filename parsing + metadata (spec 5.7 intent)
- Current state: Py2 runner does best-effort filename metadata parsing (channel/date_code/grid_id/direction) plus config-driven `filename_parsing` patterns for dataset-specific extraction.
- Risk: hidden assumptions creep into code and may not match all datasets.
- Next: make all filename-derived metadata fully config-driven and keep code to “apply config only”.

### 2) Preprocessing / mode parity (spec 3.3.*)
- Current state: modulus/topography support plane level, Align Rows, median, percentile clipping, plus a config-driven ordered `gwyddion_ops` list (including repeated ops such as horizontal+vertical Align Rows).
- Risk: real AFM workflows often require more Gwyddion-native steps (multiple leveling/flattening variants, denoise pipelines, scar/line mismatch correction).
- Next:
  - Keep `docs/gwyddion_ops.md` as the single source of truth for supported ops + args + closest GUI equivalents.
  - Extend supported ops list (e.g., polynomial leveling, flatten base) once validated against GUI workflows.
  - Add “known good” presets for common workflows (simple vs complex) as profiles.

### 3) Masking (ROI) semantics
- Current state:
  - Config-driven masks control which pixels contribute to stats.
  - Runner supports Gwyddion-native outlier masking (`mask.method: outliers|outliers2`) and can export mask artifacts.
  - Example “row+col correction + outlier mask” config exists: `configs/TEST configs/Example configs/config.modulus_rowcol_mask.yaml`.
- Risk: mask semantics and ordering can diverge from interactive Gwyddion ROI workflows.
- Next:
  - Validate mask semantics vs GUI for representative samples.
  - Add additional Gwyddion-native masking methods if needed, and keep them config-driven.

### 4) Unit detection/normalization robustness (high impact)
- Current state:
  - Unit conversions work for common `Pa/kPa/MPa/GPa` strings; conversion is applied before filter thresholds (normalized units).
  - Missing-units behavior is explicit and configurable (`on_missing_units: error|warn|skip_row`).
- New finding:
  - The current test TIFFs load in pygwy with **no Z-unit metadata** (`field.get_si_unit_z().get_unit_string()` returns empty/None), so strict configs will skip them.
  - Evidence: see `out/provenance/missing_units/pygwy_run.log`.
- Next:
  - Confirm whether unit metadata can be preserved in the upstream export path for these TIFFs.
  - If TIFF cannot reliably carry units, decide on a dataset-scoped strategy (separate configs per known unit batch, or require a source format that carries units).

### 5) Plotting / uncertainty visualization (spec plotting intent)
- Current state: multiple plotting modes exist including heatmap overlays, bubbles, CV, and two-panel summaries.
- Risk: visual defaults need tuning per dataset; some modes depend on optional min/max presence.
- Next: add small “golden” tests for derived fields and overlay configurations; document recommended defaults per plot type.

### 6) Test coverage (including upcoming topography)
- Current state: Py3 tests exist; Py2/pygwy tests are limited by environment.
- Gap: **Topography statistics and topo-specific preprocessing need dedicated testing**.
- Plan: when you provide a topo test folder, add topo-focused configs + run suite outputs, and add Py3-side tests that validate plotting/parsing on topo CSVs (and sanity-check expected ranges).

### 7) Processing step trace / debug transparency
- Current state: per-file trace JSON exists when debug is enabled; debug logs include units, mask/stats counts, and filter provenance.
- Remaining risk: stakeholders may need a run-level report (aggregate counts and file lists by skip reason).
- Next: optionally write a JSON run report alongside `summary.csv` (aggregate counters + missing-units list).

## Out-of-scope note (per spec 1.7)
The spec lists “file manifest utilities” as out-of-scope for the core API. This repo includes optional helpers (`scripts/make_job_manifest.py`, `scripts/run_config_suite.py`) as wrappers; they should remain optional and not change the core data model.
