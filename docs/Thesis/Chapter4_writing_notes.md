# Chapter 4 Writing Notes (Read Before Drafting)

## Purpose
- Define the acquisition protocol for Stage 1 survey mapping and the stopping/trigger logic.

## Must-Haves
- Grid geometry (50 um x 50 um, 21 x 21 grid, overlap) and per-scan parameters.
- Channel list (topography; later channels if applicable).
- Clear handoff to Ch.5 for processing + statistics.
- Add a short acquisition-side note that AFM scanning only measures the visible accessible surface.
- State that steep local topography, overhang-like shadowing, or particles sitting below the effective fracture plane can prevent the scan from representing the full particle geometry or full near-surface population.
- Use this as a bridge into why Stage 1 candidate particles remain provisional until later validation.

## New Points To Carry Forward

- State clearly that the nominal Stage 1 survey area was `50 um x 50 um` and the intended survey grid was `21 x 21`.
- Define the practical grouped surface conditions used later in Chapters 5 and 6:
  - scraped
  - non scraped
- Make clear that these surface states were practical acquisition conditions rather than idealized acquisition factors.
- Add a short note that only forward topography scans were carried into the reported Stage 1 dataset.
- Tie that forward-only choice back to the prior modulus forward/backward validation, but keep the detailed method justification in Chapter 5.
- Add a short image-quality note:
  - if a scan contains strong scars, distortion, or other artefacts, acquisition quality may limit what later preprocessing can recover
  - this should be framed as an acquisition-to-processing limitation, not only a processing failure
- Keep the chapter focused on acquisition choices and handoff logic rather than code architecture or software-environment detail.
