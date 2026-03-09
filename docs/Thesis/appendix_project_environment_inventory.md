# Appendix Planning Note: Project Environment Inventory

This appendix should store the reference information needed to reproduce the project environment without interrupting the flow of the main thesis chapters.

## Purpose

- Record the tools, equipment, programs, versions, and repositories used in the project.
- Provide one location for environment provenance instead of scattering that information across multiple chapters.
- Support later reproducibility and future reruns.

## Recommended Sections

## A.1 AFM Hardware

- AFM model
- controller
- probe or cantilever family
- spring constant source
- tip radius source
- calibration workflow reference
- acquisition mode used for each chapter dataset

## A.2 Experimental Equipment

- microscopes
- fracture preparation tools
- razor blade or scraping tools when relevant
- environmental controls if relevant

## A.3 Software

- AFM vendor software and version
- Gwyddion version
- pygwy environment version
- Python 2 version
- Python 3 version
- major Python package versions used for postprocessing and plotting

## A.4 Repositories and Local Project Structure

- main repository name and location
- linked Dropbox or working data locations
- report output location
- thesis draft location
- relationship between code repository and external data storage

## A.5 Configs and Active Workflows

- active topo particle configs
- active modulus comparison configs
- summary and report generation scripts
- representative image workflow config if used

## A.6 Versioning and Naming

- naming convention in use for reports, chapters, and appendix artifacts
- note that archived versions should be stored separately from active versions

## A.7 Known Validation Limits

- unit provenance still under broader verification for modulus datasets
- current data storage remains largely date organized
- future reruns should preserve environment metadata automatically where possible

