# Related Tools / Prior Art (Survey Notes)

Goal: find existing open-source and academic workflows that overlap with this repo's scope:
- Batch AFM/SPM image preprocessing (leveling, scan-line correction, filtering)
- Masking / ROI semantics and outlier rejection
- Per-image summary statistics export (avg/std/n_valid) and grid heatmaps
- Transparent provenance (what happened to each file/pixel)

This is a starting list to review. Treat items as candidates until verified.

## Park Systems ecosystem (XEI / SmartScan / SmartAnalysis)
- XEI is Park Systems' AFM data analysis software; it appears to support exporting loaded TIFF scan data to a text format (including the data array) in addition to image formats.
- SmartScan (acquisition/control software) is described as having "programmable scripting features" and "built-in macros"; some materials mention optional script-level control through external programs.
- Park SmartAnalysis is a newer Park image analytics product; likely overlaps with XEI-style processing and stats, but may not be scriptable in the same way.

What to look for (practical questions):
- Is there a documented automation interface (macro files, COM automation, DLL/SDK, CLI batch mode)?
- Can it export per-image stats (mean/std/n_valid) and/or per-pixel arrays with units preserved?
- Does it preserve Z-units in exported TIFFs consistently (or only in proprietary formats)?

## Closest overlap (Gwyddion ecosystem)
- Gwyddion (GUI application): baseline for preprocessing + masking definitions we want to match.
- pyGwy (Gwyddion Python bindings): scripting interface used by this repo (Py2 runner).
- Gwyddion batch processing: look for examples of running Gwyddion/pyGwy headless or scripted over directories.
- GWY container/file tooling: look for libraries that read/write `.gwy` containers and preserve units/metadata.

## Python AFM/SPM data libraries (candidates)
- Libraries for reading SPM formats and exporting arrays (Bruker/Veeco, JPK, Asylum, Nanoscope, etc.).
- Libraries for AFM force curve / indentation / modulus processing (if they include pixel-wise modulus maps).
- Image-analysis stacks used for SPM data (NumPy/SciPy/scikit-image) when combined with explicit provenance.

Concrete candidates to review:
- TopoStats (batch AFM image analysis + statistics): https://github.com/AFM-SPM/TopoStats
- AFMReader (I/O layer for many AFM file formats; used by TopoStats): https://github.com/AFM-SPM/AFMReader
- pySPM (read/plot multiple SPM formats; reverse engineered for some formats): https://github.com/scholi/pySPM
- nanoscope (Python reader for Bruker/Veeco Nanoscope formats): https://pypi.org/project/nanoscope/

## What we should compare against
- Definition matching:
- How do they define mask semantics (inclusive/exclusive, NaN vs 0, outlier criteria)?
- Do they use population std or sample std, and how do they handle missing/invalid pixels?
- Units handling:
- Do they preserve Z-units and scaling end-to-end? Can they repair units explicitly?
- Batch behavior:
- Are pipelines config-driven and deterministic, or do they rely on GUI state?
- Provenance:
- Do they output per-file/per-step traces explaining skips, exclusions, and conversions?

## Concrete search queries (GitHub)
- `gwyddion pygwy batch processing`
- `gwy_process_func_run align_rows`
- `linematch gwyddion python`
- `AFM modulus map gwyddion`
- `AFM TIFF gwyddion python`
- `SPM batch leveling align rows`
- `SPM modulus map outlier filtering`
- `Chauvenet criterion AFM`

## Concrete search queries (Scholar / literature)
- `Gwyddion pyGwy batch processing`
- `AFM modulus mapping statistical filtering`
- `scan line correction AFM align rows`
- `indentation modulus map outlier rejection`
- `SPM preprocessing pipeline provenance`

## Notes for thesis-style framing
- If we cite prior art, keep the comparison grounded:
- This repo's contribution is not a novel filter; it is a deterministic, config-driven, provenance-logged bridge between Gwyddion-standard preprocessing and downstream statistical reporting/plots.
- The core design choice is to make "what is truth" explicit (`stats_source`) and prevent ambiguous mixed pipelines unless explicitly allowed (`allow_mixed_processing`).
