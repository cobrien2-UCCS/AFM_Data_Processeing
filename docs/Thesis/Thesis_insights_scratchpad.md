# Thesis Insights Scratchpad

Use this file as a dumping ground for insights that occur while writing any chapter,
so they do not get lost (even if they belong in another chapter later).

## Results/Insights (paste + date)
- 
- Use agreed thesis nomenclature consistently across chapters, captions, tables, and report artifacts so the same workflow object is not renamed in different places.
- The one-file modulus unit-verification run produced a negative exported modulus value even though the broader modulus comparison CSV sets remain non-negative. Treat this as an unresolved validation issue and likely trigger for a targeted modulus rerun once the unit path is clarified.

## Figures/Tables To Add Later
- 

## Open Questions
- 

## Future Work Notes
- The current analysis stack should be refactored into a more reproducible, robust, and predictable pipeline.
- Right now the workflow still relies on substantial operator-guided legwork, restart handling, artifact inspection, and report-specific postprocessing.
- Future work should package the existing logic into a cleaner user-facing workflow with predictable run behavior, standardized outputs, and lower dependence on expert intervention.
- The modulus baseline validation should be described as a limited-scope method-validation artifact:
  - one PEGDA sample
  - one fracture-surface side
  - not yet sufficient for broad modulus generalization
- A fuller modulus comparison should later be repeated across more grouped samples, separated by side, and then extended to composite PEGDA-SiNP and Li-containing systems.
- Add a future figure idea: a workflow/data-flow chart to explain the pipeline architecture and report-generation path more clearly than prose alone.
