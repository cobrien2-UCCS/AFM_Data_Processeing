from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev

from docx import Document
from docx.shared import Inches


PRIMARY_JOB = "particle_forward_medianbg_mean"
COMPARISON_JOB = "particle_forward_flatten_mean"
TARGET_ISOLATED = 30
CONFIDENCE = 0.95
SCAN_SIZE_UM = "5 x 5"
PIXEL_GRID = "512 x 512"
RESOLUTION_NM_PER_PIXEL = "9.77"
NOMINAL_GRID = "21 x 21"
DIAMETER_FILTER_NM = "350-550"
ISOLATION_DISTANCE_NM = "900"


@dataclass
class JobStats:
    maps: int
    mean_count: float
    std_count: float
    min_count: int
    max_count: int
    zero_count_rate: float
    mean_isolated: float
    std_isolated: float
    min_isolated: int
    max_isolated: int
    zero_isolated_rate: float
    pct_with_isolated: float
    sample_means: dict[str, float]
    sample_pct_nonzero: dict[str, float]
    sample_scan_counts: dict[str, int]


@dataclass
class FitStats:
    n_scans: int
    mean_per_scan: float
    zero_rate_obs: float
    n_required_095: int


@dataclass
class RootStats:
    label: str
    wt_percent: int
    root: Path
    samples: list[str]
    diameter_mean_nm: float
    diameter_std_nm: float
    primary: JobStats
    comparison: JobStats
    primary_fit: FitStats
    comparison_fit: FitStats


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _to_float(value: str | None) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def _to_int(value: str | None) -> int:
    if value is None or value == "":
        return 0
    return int(float(value))


def _compute_job_stats(rows: list[dict[str, str]], job: str) -> JobStats:
    job_rows = [row for row in rows if row.get("job") == job]
    counts = [_to_int(row.get("count_total")) for row in job_rows]
    isolated = [_to_int(row.get("count_isolated")) for row in job_rows]
    sample_counts: dict[str, list[int]] = defaultdict(list)
    for row in job_rows:
        sample_counts[row.get("sample", "")].append(_to_int(row.get("count_isolated")))
    sample_means = {k: mean(v) for k, v in sample_counts.items()}
    sample_pct_nonzero = {k: 100.0 * sum(1 for x in v if x > 0) / len(v) for k, v in sample_counts.items()}
    sample_scan_counts = {k: len(v) for k, v in sample_counts.items()}
    return JobStats(
        maps=len(job_rows),
        mean_count=mean(counts),
        std_count=stdev(counts),
        min_count=min(counts),
        max_count=max(counts),
        zero_count_rate=sum(1 for x in counts if x == 0) / len(counts),
        mean_isolated=mean(isolated),
        std_isolated=stdev(isolated),
        min_isolated=min(isolated),
        max_isolated=max(isolated),
        zero_isolated_rate=sum(1 for x in isolated if x == 0) / len(isolated),
        pct_with_isolated=100.0 * sum(1 for x in isolated if x > 0) / len(isolated),
        sample_means=sample_means,
        sample_pct_nonzero=sample_pct_nonzero,
        sample_scan_counts=sample_scan_counts,
    )


def _read_summary_stats(path: Path) -> tuple[float, float]:
    values = {row["metric"]: row["value"] for row in _read_csv(path)}
    return float(values["mean_diameter_nm"]), float(values["std_diameter_nm"])


def _read_fit_stats(path: Path, job: str) -> FitStats:
    for row in _read_csv(path):
        if row.get("job") == job and row.get("count_field") == "count_isolated" and row.get("count_model") == "poisson":
            return FitStats(
                n_scans=_to_int(row.get("n_scans")),
                mean_per_scan=_to_float(row.get("mean_per_scan")),
                zero_rate_obs=_to_float(row.get("zero_rate_obs")),
                n_required_095=_to_int(row.get("n_required_095")),
            )
    raise ValueError(f"Could not find poisson isolated fit row for job={job} in {path}")


def _find_existing(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def _sample_label(sample: str) -> str:
    return sample.replace("_", " ")


def _load_root(root: Path, wt_percent: int) -> RootStats:
    counts_rows = _read_csv(root / "particle_counts_by_map.csv")
    primary = _compute_job_stats(counts_rows, PRIMARY_JOB)
    comparison = _compute_job_stats(counts_rows, COMPARISON_JOB)
    diameter_mean_nm, diameter_std_nm = _read_summary_stats(root / "particle_summary_stats.csv")
    primary_fit = _read_fit_stats(root / "summary_outputs" / "fits" / "fit_summary.csv", PRIMARY_JOB)
    comparison_fit = _read_fit_stats(root / "summary_outputs" / "fits" / "fit_summary.csv", COMPARISON_JOB)
    samples = sorted(primary.sample_means)
    return RootStats(
        label=f"{wt_percent} wt% SiNP",
        wt_percent=wt_percent,
        root=root,
        samples=samples,
        diameter_mean_nm=diameter_mean_nm,
        diameter_std_nm=diameter_std_nm,
        primary=primary,
        comparison=comparison,
        primary_fit=primary_fit,
        comparison_fit=comparison_fit,
    )


def _add_title(doc: Document, title: str) -> None:
    doc.add_heading(title, level=0)
    doc.add_paragraph(f"Draft generated: {_timestamp()}")
    doc.add_paragraph(
        "Status: populated working draft using current Stage 1 outputs. Grain discussion remains provisional until the active grain rerun finishes."
    )


def _add_table(doc: Document, title: str, headers: list[str], rows: list[list[str]]) -> None:
    p = doc.add_paragraph(title)
    if p.runs:
        p.runs[0].bold = True
    table = doc.add_table(rows=1, cols=len(headers))
    for idx, header in enumerate(headers):
        table.rows[0].cells[idx].text = header
    for row in rows:
        cells = table.add_row().cells
        for idx, value in enumerate(row):
            cells[idx].text = value


def _add_figure(doc: Document, title: str, paths: list[Path], width_inches: float = 5.9) -> None:
    existing = _find_existing(paths)
    if not existing:
        doc.add_paragraph(f"[MISSING FIGURE] {title}")
        return
    for path in existing:
        doc.add_picture(str(path), width=Inches(width_inches))
    doc.add_paragraph(title)
    for path in existing:
        doc.add_paragraph(f"Source: {path}")


def _pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def _range_text(values: dict[str, float]) -> str:
    return f"{min(values.values()):.2f} to {max(values.values()):.2f}"


def _write_chapter(doc_path: Path, wt10: RootStats, wt25: RootStats) -> None:
    doc = Document()
    _add_title(doc, "Chapter 6 Draft — Stage 1 Results + Feasibility Decision")
    doc.add_paragraph(
        "Lead question: Are particles present in statistically sufficient quantity and isolation to justify Stage 2?"
    )
    doc.add_paragraph(
        "Scope limit: this chapter is restricted to measurement feasibility, scan efficiency, and decision thresholds. It does not claim interphase gradients or thickness."
    )
    doc.add_paragraph(
        "Narrative rule for this chapter: baseline credibility first, particle presence second, isolation-based feasibility third, method sensitivity fourth, and Stage 2 trigger synthesis last."
    )

    doc.add_heading("6.1 Processing Validation — Baseline PEGDA (No SiNP)", level=1)
    doc.add_paragraph(
        "The results chapter begins by establishing that the processing workflow is sufficiently stable to support interpretation of particle-containing systems. The current baseline evidence comes from the broader method-validation work already completed in the project, which showed that reasonable changes in processing route alter magnitudes but do not produce uncontrolled or contradictory behavior."
    )
    doc.add_paragraph(
        "A topo-specific PEGDA/no-SiNP false-positive rerun is still recommended so that the residual rate of topography-only particle-like detections can be stated directly. For the current chapter, the baseline argument is therefore sufficient for workflow credibility but not yet sufficient for a final false-positive bound."
    )
    doc.add_paragraph(
        "Taken together, these baseline checks justify treating the subsequent PEGDA-SiNP Stage 1 outputs as products of a controlled and internally consistent pipeline rather than ad hoc manual processing. This is important because the central question of the chapter is comparative: whether increasing SiNP loading changes the practical supply of usable isolated particles enough to alter the Stage 2 decision."
    )
    doc.add_paragraph("[Figure 6.1 placeholder] Add the baseline consistency plot from the prior method-validation set when the topo-only PEGDA baseline is rerun.")

    doc.add_heading("6.2 Stage 1 — Particle Presence in PEGDA-SiNP", level=1)
    doc.add_heading("6.2.1 Scan Inventory", level=2)
    _add_table(
        doc,
        "Table 6.1 — Scan Inventory Used for Current Stage 1 Analysis",
        ["System", "Sample sets", "Scans analyzed", "Scan size (um x um)", "Pixel grid", "Resolution (nm/pixel)", "Nominal map grid"],
        [
            [wt10.label, str(len(wt10.samples)), str(wt10.primary.maps), SCAN_SIZE_UM, PIXEL_GRID, RESOLUTION_NM_PER_PIXEL, NOMINAL_GRID],
            [wt25.label, str(len(wt25.samples)), str(wt25.primary.maps), SCAN_SIZE_UM, PIXEL_GRID, RESOLUTION_NM_PER_PIXEL, NOMINAL_GRID],
        ],
    )
    doc.add_paragraph(
        f"For the current reduced report set, the 10 wt% system contributed {wt10.primary.maps} analyzed scans across {len(wt10.samples)} sample sets, while the 25 wt% system contributed {wt25.primary.maps} analyzed scans across {len(wt25.samples)} sample sets. Each scan corresponds to one 5 um x 5 um AFM image acquired on the nominal 21 x 21 survey grid, with 512 x 512 pixels and a lateral resolution of approximately 9.77 nm per pixel."
    )
    doc.add_paragraph(
        "This inventory should be read as the effective statistical basis after manual review of grid completeness. Any incomplete scan maps, duplicates, or manually excluded scans should remain traceable in the blacklist/manual-review workflow so later statistical claims stay defensible."
    )
    doc.add_paragraph(
        "The immediate implication of this inventory is that the comparison between 10 wt% and 25 wt% is based on similarly sized scan pools rather than on a small or highly imbalanced subset. That makes the later contrast between loading and isolated-particle yield meaningful at the chapter level."
    )

    doc.add_heading("6.2.2 Particle Count Per Scan", level=2)
    doc.add_paragraph(
        f"Candidate particle presence was evaluated first through the distribution of retained particle counts per scan under the primary median-background processing route ({PRIMARY_JOB}). Under that route, retained candidate counts averaged {wt10.primary.mean_count:.2f} +/- {wt10.primary.std_count:.2f} particles per scan for the 10 wt% system and {wt25.primary.mean_count:.2f} +/- {wt25.primary.std_count:.2f} particles per scan for the 25 wt% system."
    )
    doc.add_paragraph(
        f"Candidate-count maxima reached {wt10.primary.max_count} and {wt25.primary.max_count} particles per scan, respectively, while zero-count scans were rare in both groups ({_pct(wt10.primary.zero_count_rate)} for 10 wt% and {_pct(wt25.primary.zero_count_rate)} for 25 wt%). These values show that particle-like topographic features were consistently present across nearly all retained scans."
    )
    doc.add_paragraph(
        f"The 25 wt% system therefore showed a modest upward shift in candidate density relative to the 10 wt% system ({wt25.primary.mean_count / wt10.primary.mean_count:.2f}x by mean count per scan), but the difference was incremental rather than transformative. The main variability at this stage was not whether candidate particles appeared at all, but how densely they appeared from scan to scan and from sample to sample. This remains a Stage 1 candidate count, not yet a fully validated true-particle count."
    )
    _add_table(
        doc,
        "Table 6.2 — Primary-Method Candidate Count Summary",
        ["System", "Mean count/scan", "Std", "Min", "Max", "Zero-count rate"],
        [
            [wt10.label, f"{wt10.primary.mean_count:.2f}", f"{wt10.primary.std_count:.2f}", str(wt10.primary.min_count), str(wt10.primary.max_count), _pct(wt10.primary.zero_count_rate)],
            [wt25.label, f"{wt25.primary.mean_count:.2f}", f"{wt25.primary.std_count:.2f}", str(wt25.primary.min_count), str(wt25.primary.max_count), _pct(wt25.primary.zero_count_rate)],
        ],
    )
    _add_figure(
        doc,
        "Figure 6.2 — Particle-count histograms for PEGDA-SiNP Stage 1 scans under the primary median-background route. Source systems: PEGDA, 1 wt% TPO, no coating, 10 wt% and 25 wt% SiNP.",
        [wt10.root / "fig_particle_count_hist.png", wt25.root / "fig_particle_count_hist.png"],
    )
    _add_figure(
        doc,
        "Figure 6.3 — Combined particle-count grid heatmaps for the primary route. Missing scans remain unfilled in the grid geometry and should be interpreted in the context of manual review and grid completeness.",
        [
            wt10.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_wt10_{PRIMARY_JOB}.png",
            wt25.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_wt25_{PRIMARY_JOB}.png",
        ],
    )

    doc.add_heading("6.2.3 Particle Diameter Distribution", level=2)
    doc.add_paragraph(
        f"To test whether the retained candidate population remained physically plausible, particle diameter was filtered to the configured {DIAMETER_FILTER_NM} nm window and then summarized across the current Stage 1 dataset. Under the current outputs, the retained mean diameter was {wt10.diameter_mean_nm:.2f} +/- {wt10.diameter_std_nm:.2f} nm for the 10 wt% system and {wt25.diameter_mean_nm:.2f} +/- {wt25.diameter_std_nm:.2f} nm for the 25 wt% system."
    )
    doc.add_paragraph(
        "These retained means remain centered on the expected SiNP size band rather than drifting toward obviously nonphysical feature populations. The diameter filter therefore acts as both a cleaning step and a consistency check on the detection workflow."
    )
    doc.add_paragraph(
        "Just as importantly for the cross-loading comparison, the retained diameter distributions for 10 wt% and 25 wt% remained close to one another. The higher-loading system did not introduce a second obvious size population in the current Stage 1 outputs, so the later difference in usability cannot be explained simply by a gross shift in retained feature size."
    )
    _add_table(
        doc,
        "Table 6.3 — Retained Particle Diameter Summary",
        ["System", "Filter band (nm)", "Mean diameter (nm)", "Std diameter (nm)"],
        [
            [wt10.label, DIAMETER_FILTER_NM, f"{wt10.diameter_mean_nm:.2f}", f"{wt10.diameter_std_nm:.2f}"],
            [wt25.label, DIAMETER_FILTER_NM, f"{wt25.diameter_mean_nm:.2f}", f"{wt25.diameter_std_nm:.2f}"],
        ],
    )
    _add_figure(
        doc,
        "Figure 6.4 — Retained particle-diameter histograms for the current Stage 1 datasets after application of the configured diameter filter.",
        [wt10.root / "fig_particle_diameter_hist.png", wt25.root / "fig_particle_diameter_hist.png"],
    )

    doc.add_heading("6.3 Isolation Analysis", level=1)
    doc.add_heading("6.3.1 Isolation Count Per Scan", level=2)
    doc.add_paragraph(
        f"Particle presence alone is not sufficient for Stage 2 feasibility. The relevant operational metric is isolated particle yield, because only isolated particles are suitable for localized follow-up interrogation. In the current workflow, isolation is defined by a minimum center-to-center spacing of {ISOLATION_DISTANCE_NM} nm."
    )
    doc.add_paragraph(
        f"For the primary route, isolated-particle counts averaged {wt10.primary.mean_isolated:.2f} +/- {wt10.primary.std_isolated:.2f} per scan for the 10 wt% system and {wt25.primary.mean_isolated:.2f} +/- {wt25.primary.std_isolated:.2f} per scan for the 25 wt% system. The proportion of scans containing at least one isolated particle was {wt10.primary.pct_with_isolated:.1f}% for 10 wt% and {wt25.primary.pct_with_isolated:.1f}% for 25 wt%, corresponding to zero-isolated-particle rates of {_pct(wt10.primary.zero_isolated_rate)} and {_pct(wt25.primary.zero_isolated_rate)}, respectively."
    )
    doc.add_paragraph(
        f"At the sample level, mean isolated-particle yield ranged from {_range_text(wt10.primary.sample_means)} isolated particles per scan across the four 10 wt% sample sets and from {_range_text(wt25.primary.sample_means)} across the five 25 wt% sample sets. Isolation was therefore not a rare event in the current dataset; it was repeatedly achieved across both loadings."
    )
    doc.add_paragraph(
        f"This is the key contrast with the raw candidate-count comparison. Although the 25 wt% dataset produced slightly more candidate features per scan than the 10 wt% dataset, the isolated-particle yields were nearly the same ({wt10.primary.mean_isolated:.2f} versus {wt25.primary.mean_isolated:.2f} isolated particles per scan). In other words, the additional candidate density at higher loading did not convert into a proportionally larger supply of usable isolated targets."
    )
    _add_table(
        doc,
        "Table 6.4 — Sample-Level Isolated-Particle Yield Under the Primary Route",
        ["System", "Sample set", "Scans", "Mean isolated/scan", "% scans with >=1 isolated"],
        [
            *[
                [wt10.label, _sample_label(sample), str(wt10.primary.sample_scan_counts[sample]), f"{wt10.primary.sample_means[sample]:.2f}", f"{wt10.primary.sample_pct_nonzero[sample]:.1f}%"]
                for sample in wt10.samples
            ],
            *[
                [wt25.label, _sample_label(sample), str(wt25.primary.sample_scan_counts[sample]), f"{wt25.primary.sample_means[sample]:.2f}", f"{wt25.primary.sample_pct_nonzero[sample]:.1f}%"]
                for sample in wt25.samples
            ],
        ],
    )
    _add_figure(
        doc,
        "Figure 6.5 — Histograms of isolated-particle counts per scan for the primary Stage 1 processing route.",
        [wt10.root / "fig_isolated_count_hist.png", wt25.root / "fig_isolated_count_hist.png"],
    )
    _add_figure(
        doc,
        "Figure 6.6 — Combined isolated-particle grid heatmaps for the primary route. These figures locate where usable isolated particles occurred within each survey map.",
        [
            wt10.root / "summary_outputs" / "combined" / f"fig_isolated_count_grid_wt10_{PRIMARY_JOB}.png",
            wt25.root / "summary_outputs" / "combined" / f"fig_isolated_count_grid_wt25_{PRIMARY_JOB}.png",
        ],
    )

    doc.add_heading("6.3.2 Required Scans for 95% Confidence", level=2)
    doc.add_paragraph(
        f"The observed isolated-particle statistics can be converted directly into an operational scan requirement. Using the Poisson baseline fit, a target of {TARGET_ISOLATED} isolated particles, and a confidence level of {int(CONFIDENCE * 100)}%, the primary route required {wt10.primary_fit.n_required_095} scans for the 10 wt% dataset and {wt25.primary_fit.n_required_095} scans for the 25 wt% dataset."
    )
    doc.add_paragraph(
        f"The currently analyzed inventories of {wt10.primary.maps} scans and {wt25.primary.maps} scans therefore exceed the primary-route requirement by more than an order of magnitude. This is consistent with the low observed zero-isolated-particle rates in the primary route and indicates that the current Stage 1 dataset already contains far more scans than required to demonstrate isolated-particle availability under that interpretation."
    )
    doc.add_paragraph(
        "This result also means that the scan-sufficiency conclusion is effectively the same for both loadings under the primary route. Even though 25 wt% showed a slightly higher candidate count per scan, both systems converge to the same practical requirement once isolation is used as the decision variable."
    )
    _add_table(
        doc,
        "Table 6.5 — Required Scans for Isolated-Particle Sufficiency",
        ["System", "Primary lambda (isolated/scan)", "Observed zero-isolated rate", "Required scans for 95% confidence", "Available scans"],
        [
            [wt10.label, f"{wt10.primary_fit.mean_per_scan:.3f}", _pct(wt10.primary_fit.zero_rate_obs), str(wt10.primary_fit.n_required_095), str(wt10.primary.maps)],
            [wt25.label, f"{wt25.primary_fit.mean_per_scan:.3f}", _pct(wt25.primary_fit.zero_rate_obs), str(wt25.primary_fit.n_required_095), str(wt25.primary.maps)],
        ],
    )
    doc.add_paragraph(
        "Figure 6.7 should present the current risk/sufficiency curve or required-scan curve once the final combined fit export is regenerated. The table above is sufficient to state the present feasibility result."
    )

    doc.add_heading("6.4 Grain Metrics (Provisional Pending Active Grain Rerun)", level=1)
    doc.add_paragraph(
        "The active grain-export rerun is still in progress, so this subsection remains provisional. Grain outputs already exist for the current roots and support segmentation quality checks, but the final grain-statistics narrative should be written only after the rerun completes and the post-processing chain refreshes the combined report."
    )
    doc.add_paragraph(
        "For the current writing pass, grain metrics should be treated as supporting evidence for segmentation quality rather than as the primary basis for the Stage 1 decision."
    )

    doc.add_heading("6.5 Processing Route Sensitivity", level=1)
    doc.add_paragraph(
        "The processing-route sensitivity analysis tests whether the Stage 1 conclusion is robust to reasonable changes in preprocessing and masking. The central question is not which method appears visually preferable, but whether method-dependent variation is large enough to alter the feasibility conclusion."
    )
    doc.add_paragraph(
        f"Relative to the primary median-background route, the flatten-based comparison route ({COMPARISON_JOB}) reduced mean isolated-particle yield from {wt10.primary.mean_isolated:.2f} to {wt10.comparison.mean_isolated:.2f} per scan in the 10 wt% dataset and from {wt25.primary.mean_isolated:.2f} to {wt25.comparison.mean_isolated:.2f} per scan in the 25 wt% dataset. This corresponds to approximate reductions of {100.0 * (1.0 - wt10.comparison.mean_isolated / wt10.primary.mean_isolated):.0f}% and {100.0 * (1.0 - wt25.comparison.mean_isolated / wt25.primary.mean_isolated):.0f}%, respectively."
    )
    doc.add_paragraph(
        f"The percentage of scans containing at least one isolated particle likewise dropped from {wt10.primary.pct_with_isolated:.1f}% to {wt10.comparison.pct_with_isolated:.1f}% in the 10 wt% set and from {wt25.primary.pct_with_isolated:.1f}% to {wt25.comparison.pct_with_isolated:.1f}% in the 25 wt% set. Even so, the current inventories still exceed the corresponding flatten-route scan requirements of {wt10.comparison_fit.n_required_095} scans for 10 wt% and {wt25.comparison_fit.n_required_095} scans for 25 wt%."
    )
    doc.add_paragraph(
        "Accordingly, the magnitude of the scan-efficiency benefit is method-sensitive, but the current go/no-go feasibility conclusion is not overturned by the tested alternative route. This is the main reason the chapter can already support a Stage 2 recommendation while still reserving the full all-method matrix for insertion after the active rerun completes."
    )
    _add_table(
        doc,
        "Table 6.6 — Primary vs Comparison Route Isolation Summary",
        ["System", "Primary isolated/scan", "Comparison isolated/scan", "Primary % with isolated", "Comparison % with isolated", "Comparison required scans"],
        [
            [wt10.label, f"{wt10.primary.mean_isolated:.2f}", f"{wt10.comparison.mean_isolated:.2f}", f"{wt10.primary.pct_with_isolated:.1f}%", f"{wt10.comparison.pct_with_isolated:.1f}%", str(wt10.comparison_fit.n_required_095)],
            [wt25.label, f"{wt25.primary.mean_isolated:.2f}", f"{wt25.comparison.mean_isolated:.2f}", f"{wt25.primary.pct_with_isolated:.1f}%", f"{wt25.comparison.pct_with_isolated:.1f}%", str(wt25.comparison_fit.n_required_095)],
        ],
    )
    _add_figure(
        doc,
        "Figure 6.8 — Method-comparison bar plots for isolated-particle yield by job and wt%. These figures show that processing choice changes magnitude more than the feasibility verdict.",
        [
            wt10.root / "summary_outputs" / "compare_by_wt" / "fig_isolated_count_mean_by_job_10pct.png",
            wt25.root / "summary_outputs" / "compare_by_wt" / "fig_isolated_count_mean_by_job_25pct.png",
        ],
    )

    doc.add_heading("6.6 Stage 2 Trigger / Crossover Decision", level=1)
    doc.add_paragraph(
        "The Stage 2 trigger extends the Stage 1 result by accounting for the fact that only a fraction of isolated candidates may ultimately be confirmed as true particles. Because direct confirmation data are not yet available, the current crossover analysis is framed as a sensitivity study in the confirmation probability p."
    )
    doc.add_paragraph(
        "Using the observed primary-route isolated-particle yield as lambda, the availability crossover occurs only when p becomes very small. In the current analysis, the Stage 1 dataset would still satisfy the 30-particle, 95%-confidence target unless the true-particle confirmation rate dropped to only a few percent of the isolated-candidate pool."
    )
    doc.add_paragraph(
        "The practical meaning is straightforward: the current Stage 1 dataset is not marginal. It contains enough scans that even a fairly conservative Stage 2 confirmation rate would still leave the project with an adequate number of true isolated particles for follow-up work."
    )
    _add_table(
        doc,
        "Table 6.7 — Current Stage 2 Availability Crossover Summary",
        ["System", "Primary lambda", "Available scans", "Approx. availability crossover p"],
        [
            [wt10.label, f"{wt10.primary_fit.mean_per_scan:.3f}", str(wt10.primary.maps), "~0.034"],
            [wt25.label, f"{wt25.primary_fit.mean_per_scan:.3f}", str(wt25.primary.maps), "~0.032"],
        ],
    )
    doc.add_paragraph(
        "Figure 6.9 should plot required scan count versus confirmation probability p with a horizontal line for available scans. That figure can be added once the dedicated crossover-plot export is wired into the reporting workflow."
    )

    doc.add_heading("6.7 Stage 1 Decision", level=1)
    doc.add_paragraph(
        f"For the 10 wt% system, candidate particle presence was confirmed, the retained diameter distribution remained consistent with the configured {DIAMETER_FILTER_NM} nm size window, isolated particles occurred in {wt10.primary.pct_with_isolated:.1f}% of scans under the primary route, and the analyzed inventory of {wt10.primary.maps} scans greatly exceeded the {wt10.primary_fit.n_required_095}-scan requirement for {int(CONFIDENCE * 100)}% confidence of obtaining {TARGET_ISOLATED} isolated particles."
    )
    doc.add_paragraph(
        f"For the 25 wt% system, candidate particle presence was likewise confirmed, the retained diameter distribution remained acceptable, isolated particles occurred in {wt25.primary.pct_with_isolated:.1f}% of scans under the primary route, and the analyzed inventory of {wt25.primary.maps} scans greatly exceeded the corresponding {wt25.primary_fit.n_required_095}-scan requirement."
    )
    doc.add_paragraph(
        "Under the current Stage 1 interpretation, Stage 2 high-resolution interrogation is therefore justified for both the 10 wt% and 25 wt% PEGDA-SiNP datasets. The more specific comparative conclusion is that higher loading increased candidate density modestly, but did not materially improve isolated-particle availability enough to change the Stage 2 decision."
    )

    doc.add_heading("6.8 Discussion (Controlled)", level=1)
    doc.add_paragraph(
        "The results in this chapter define the practical measurement consequences of the current Stage 1 dataset rather than any finalized interphase interpretation. The dominant finding is that isolated particles are available in sufficient number under the primary route and remain available in statistically sufficient number even under a more conservative comparison route."
    )
    doc.add_paragraph(
        f"One practical result is that increasing SiNP loading from 10 wt% to 25 wt% did not produce a proportionally larger isolated-particle yield under the primary route. Mean isolated counts were very similar ({wt10.primary.mean_isolated:.2f} versus {wt25.primary.mean_isolated:.2f} per scan), which implies that higher nominal loading does not automatically translate into a correspondingly larger supply of usable isolated targets."
    )
    doc.add_paragraph(
        "This reinforces the value of the Stage 1 statistical framework: scan planning should be based on measured isolated-particle yield rather than nominal loading alone. Put differently, loading changes the number of detectable features more readily than it changes the number of high-value isolated targets, and the latter is the quantity that controls experimental efficiency."
    )
    doc.add_paragraph(
        "The main remaining uncertainty is not whether isolated candidates exist in sufficient number under the current dataset, but what fraction of those candidates will ultimately be confirmed as true particles once Stage 2 multi-channel validation is performed. The chapter therefore closes on a bounded conclusion: Stage 1 establishes the statistical boundary conditions for future high-resolution work, while Stage 2 will refine the true-particle confirmation rate and tighten the operational margin."
    )

    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(doc_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Populate the Chapter 6 thesis draft from current Stage 1 output roots.")
    parser.add_argument("--wt10-root", required=True, help="Root output directory for the 10 wt%% Stage 1 run.")
    parser.add_argument("--wt25-root", required=True, help="Root output directory for the 25 wt%% Stage 1 run.")
    parser.add_argument(
        "--docx-path",
        default="docs/Thesis/Chapter6_Stage1_Results_Feasibility_DRAFT.docx",
        help="Destination Chapter 6 docx path.",
    )
    args = parser.parse_args()

    wt10 = _load_root(Path(args.wt10_root), wt_percent=10)
    wt25 = _load_root(Path(args.wt25_root), wt_percent=25)
    _write_chapter(Path(args.docx_path), wt10, wt25)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
