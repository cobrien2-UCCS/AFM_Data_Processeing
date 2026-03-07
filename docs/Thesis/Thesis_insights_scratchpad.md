# Thesis Insights Scratchpad

Use this file as a dumping ground for insights that occur while writing any chapter,
so they do not get lost (even if they belong in another chapter later).

## Results/Insights (paste + date)
- 
- Use agreed thesis nomenclature consistently across chapters, captions, tables, and report artifacts so the same workflow object is not renamed in different places.
- The one-file modulus unit-verification run produced a negative exported modulus value even though the broader modulus comparison CSV sets remain non-negative. Treat this as an unresolved validation issue and likely trigger for a targeted modulus rerun once the unit path is clarified.
- The absolute modulus magnitude also appears higher than expected for PEGDA. Because the field remains relatively uniform rather than chaotic, this looks more like a systematic offset issue than a random preprocessing artifact.
- The scraped/non-scraped grouping should be described as an AFM-access accommodation rather than a planned balanced experimental factor; future work should control that preparation state deliberately.
- Large all-method tables and other very wide result tables likely belong in appendix/supporting material so the chapter body can keep the main argument clear.
- The shared topo synthesis CSVs are the preferred bridge between source outputs, report generation, and Chapter 6 writing.

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
- Modulus future validation should also go back to raw pinpoint / force-curve data, AFM setpoints, calibration parameters, contact-model settings, and TIFF/export scaling to determine why the absolute modulus magnitude appears too high.
- Add a future figure idea: a workflow/data-flow chart to explain the pipeline architecture and report-generation path more clearly than prose alone.
- Add a future figure idea: fractured-surface versus manually flattened/scraped-surface example to explain why scraping was sometimes necessary for AFM access.
## Representative Particle Image Set

- Keep a small representative image set to visually explain what the Stage 1 particle workflow is doing.
- Purpose:
  - show the appearance of isolated particles
  - show clumped-particle fields
  - show dense but relatively non-clumped fields
  - show sparse / single-particle fields
  - show how the mask behaves on topography images
- These images are useful for Chapter 5 workflow explanation, Chapter 6 supporting context, and appendix/SOP material.
