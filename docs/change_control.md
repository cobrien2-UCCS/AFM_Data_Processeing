# Change Control (Code + Config)

Purpose: keep the pipeline stable and defensible for thesis use.

## Ground rules
- No code or config changes unless explicitly requested by Conor.
- Any requested change starts with a short, agreed plan (scope + reason + expected impact).
- Prefer config-only changes over code changes whenever possible.

## When a change is allowed
- A documented gap in `docs/SPEC_GAP_LIST.md` blocks progress.
- A new dataset or channel requires a new mode/profile.
- A validation issue is found (GUI parity or unit handling).
- A reproducibility or provenance issue is identified.

## What must be recorded
- The reason for the change (link to a gap or a decision).
- The exact config or code section modified.
- Any effect on outputs (stats, plots, counts).

## What should not change without evidence
- Default processing order.
- Units and normalization behavior.
- Masking/filters that affect stats.

## Process summary
1) Request change
2) Agree on plan
3) Make change
4) Update docs (if outputs/behavior changed)
