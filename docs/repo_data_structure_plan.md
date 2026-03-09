# Repository and Data Structure Plan

This note captures the intended storage structure for project code, reports, thesis material, and working data.

## Problem

The current working data are stored largely by date. That is usable during active analysis, but it is harder to navigate once multiple runs, reports, and reruns accumulate.

## Goal

Store project materials by function and provenance while still retaining acquisition date where it matters.

## Proposed Top Level Split

- `docs/`
  - user facing documentation
  - SOPs
  - thesis planning and drafting notes
- `scripts/`
  - processing
  - summary generation
  - report generation
- `configs/`
  - active configs
  - example configs
  - archived config snapshots for important runs
- `out/`
  - local generated outputs
  - validation runs
  - intermediate debug or verification artifacts
- external data root
  - large AFM inputs
  - large final report outputs
  - long term archived run folders

## Proposed External Data Split

- `AFM Raw Data/`
  - source exports grouped by instrument date and project
- `AFM Processed Runs/`
  - run folders grouped by project, then by run purpose, then by date
- `AFM Reports/`
  - active reports
  - archived reports
- `AFM Thesis Figures/`
  - curated images used in thesis chapters

## Recommended Naming Logic

- keep acquisition date where it is part of provenance
- avoid using date alone as the main organizing principle
- add project and run purpose in folder names

Example:

- `TopoParticle/wt10/run_full_grains_030426/`
- `TopoParticle/wt25/run_full_grains_030426/`
- `ModulusBaseline/forward_backward_compare_030626/`

## Recommended Metadata Files Per Run

Each important run folder should eventually contain:

- config snapshot
- manifest or grouped file input list
- environment summary
- report synthesis tables
- final report path reference

## Future Work

- automate environment and config capture for every major run
- standardize data storage by project and run purpose instead of date first
- add appendix references in the thesis pointing to the finalized structure
