# Next Steps (Project Plan)

This is the current thesis-facing and pipeline-facing work list after the March 6 report/chapter refresh cycle.
Change policy: see `docs/change_control.md`.

## 1) Thesis integration (current)
- Keep Chapter 6 focused on compact, story-driving tables and figures.
- Move very wide all-method tables to appendix/supporting material instead of leaving them in the main chapter body.
- Add the planned workflow/data-flow figure to Chapter 5.
- Add a fracture-vs-scraped preparation figure in Chapter 5 to explain why scraped/non-scraped exists operationally.

## 2) Topo report polish
- Finalize the main-body figure set and captions for the topo particle report and Chapter 6.
- Keep the shared synthesis outputs as the authoritative report/chapter handoff layer:
  - `topo_report_synthesis.json`
  - `topo_report_table_6_5_sample_isolated.csv`
  - `topo_report_table_6_6_required_scans.csv`
  - `topo_report_table_6_7_grain_summary.csv`
  - `topo_report_table_6_8_method_comparison.csv`
  - `topo_report_table_6_9_crossover.csv`

## 3) Representative-image workflow
- Use the representative-review config and SOP to generate curated topography+mask figure panels.
- Keep categories for:
  - isolated particles
  - clumped particles
  - dense fields with limited clumping
  - sparse / single-particle fields
- Preserve these as visual validation artifacts, not just decorative images.

## 4) Modulus integrity + units (critical future work)
- Resolve modulus TIFF unit provenance and verify what Gwyddion/pygwy is actually reading.
- Keep the new modulus provenance fields in future modulus CSVs:
  - `avg_value_original`
  - `std_value_original`
  - `units_original`
  - `unit_source`
  - `unit_conversion_factor`
- Investigate the negative one-file modulus export and the unexpectedly high PEGDA modulus magnitude.
- Validate modulus against raw pinpoint data, setpoints, calibration parameters, and upstream fit/model settings.

## 5) Sample-preparation control
- Treat scraped/non-scraped as exploratory for the current thesis.
- In future work, control surface-preparation state explicitly so scraped/non-scraped can be evaluated as a deliberate factor rather than an AFM-access accommodation.

## 6) Reproducible pipeline refactor
- Refactor the current workflow into a more predictable, lower-overhead, end-to-end pipeline.
- Keep run-time estimates, progress reporting, and standardized outputs as part of the normal interface rather than ad hoc operator work.

## 7) Validation + provenance
- Lock down a small golden set of scans for GUI-vs-pygwy parity checks.
- Maintain appendix/SOP artifacts for manual verification and figure generation.
