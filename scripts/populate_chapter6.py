from __future__ import annotations

import argparse
import csv
import math
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
ASSET_DIR = Path("docs/Thesis/generated_assets")
MODULUS_ASSET_DIR = Path(r"C:\Users\Conor O'Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT\modulus_baseline_assets")
MODULUS_PAIRED_SUMMARY = Path("out/method_compare/fwd_bwd_20260223_173826/fwd_bwd_summary.csv")
MODULUS_FORWARD_COMPARE_DIR = Path("out/method_compare/compare_20260306_180402")
MODULUS_BACKWARD_COMPARE_DIR = Path("out/method_compare/compare_20260306_180452")

JOB_ORDER = [
    "particle_forward_medianbg_mean",
    "particle_forward_medianbg_fixed0",
    "particle_forward_medianbg_p95",
    "particle_forward_medianbg_max_fixed0_p95",
    "particle_forward_flatten_mean",
    "particle_forward_flatten_fixed0",
    "particle_forward_flatten_p95",
    "particle_forward_flatten_max_fixed0_p95",
]

JOB_LABELS = {
    "particle_forward_medianbg_mean": "Median BG + mean threshold",
    "particle_forward_medianbg_fixed0": "Median BG + fixed 0",
    "particle_forward_medianbg_p95": "Median BG + p95 threshold",
    "particle_forward_medianbg_max_fixed0_p95": "Median BG + fixed 0 + p95",
    "particle_forward_flatten_mean": "Flatten + mean threshold",
    "particle_forward_flatten_fixed0": "Flatten + fixed 0",
    "particle_forward_flatten_p95": "Flatten + p95 threshold",
    "particle_forward_flatten_max_fixed0_p95": "Flatten + fixed 0 + p95",
}
JOB_STYLES = {
    "particle_forward_medianbg_mean": {"color": "#1f77b4", "linestyle": "-", "marker": "o", "linewidth": 2.5},
    "particle_forward_medianbg_fixed0": {"color": "#2ca02c", "linestyle": "--", "marker": "s", "linewidth": 1.8},
    "particle_forward_medianbg_p95": {"color": "#d62728", "linestyle": "-.", "marker": "^", "linewidth": 1.8},
    "particle_forward_medianbg_max_fixed0_p95": {"color": "#9467bd", "linestyle": ":", "marker": "D", "linewidth": 1.8},
    "particle_forward_flatten_mean": {"color": "#ff7f0e", "linestyle": "-", "marker": "P", "linewidth": 2.5},
    "particle_forward_flatten_fixed0": {"color": "#8c564b", "linestyle": "--", "marker": "X", "linewidth": 1.8},
    "particle_forward_flatten_p95": {"color": "#e377c2", "linestyle": "-.", "marker": "v", "linewidth": 1.8},
    "particle_forward_flatten_max_fixed0_p95": {"color": "#7f7f7f", "linestyle": ":", "marker": "<", "linewidth": 1.8},
}


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
    sample_stds: dict[str, float]
    sample_pct_nonzero: dict[str, float]
    sample_scan_counts: dict[str, int]


@dataclass
class FitStats:
    n_scans: int
    mean_per_scan: float
    variance_per_scan: float
    zero_rate_obs: float
    n_required_095: int


@dataclass
class GrainStats:
    grain_total: int
    grain_kept: int
    grain_isolated: int
    kept_mean_diameter_nm: float
    kept_std_diameter_nm: float
    isolated_mean_diameter_nm: float
    isolated_std_diameter_nm: float


@dataclass
class RootStats:
    label: str
    wt_percent: int
    root: Path
    samples: list[str]
    diameter_mean_nm: float
    diameter_std_nm: float
    method_stats: dict[str, JobStats]
    method_fits: dict[str, FitStats]
    grain_stats: dict[str, GrainStats]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _f(value: str | None) -> float:
    return 0.0 if value in (None, "") else float(value)


def _i(value: str | None) -> int:
    return 0 if value in (None, "") else int(float(value))


def _pct(rate: float) -> str:
    return f"{100.0 * rate:.1f}%"


def _pm(value: float, std: float, unit: str = "") -> str:
    suffix = f" {unit}" if unit else ""
    return f"{value:.2f} +/- {std:.2f}{suffix}"


def _job_label(job: str) -> str:
    return JOB_LABELS.get(job, job)


def _job_stats(rows: list[dict[str, str]], job: str) -> JobStats:
    rows = [r for r in rows if r.get("job") == job]
    counts = [_i(r.get("count_total")) for r in rows]
    isolated = [_i(r.get("count_isolated")) for r in rows]
    sample_counts: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        sample_counts[row.get("sample", "")].append(_i(row.get("count_isolated")))
    return JobStats(
        maps=len(rows),
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
        sample_means={k: mean(v) for k, v in sample_counts.items()},
        sample_stds={k: (stdev(v) if len(v) > 1 else 0.0) for k, v in sample_counts.items()},
        sample_pct_nonzero={k: 100.0 * sum(1 for x in v if x > 0) / len(v) for k, v in sample_counts.items()},
        sample_scan_counts={k: len(v) for k, v in sample_counts.items()},
    )


def _fit_map(path: Path) -> dict[str, FitStats]:
    out: dict[str, FitStats] = {}
    for row in _read_csv(path):
        if row.get("count_field") != "count_isolated" or row.get("count_model") != "poisson":
            continue
        out[row["job"]] = FitStats(
            n_scans=_i(row.get("n_scans")),
            mean_per_scan=_f(row.get("mean_per_scan")),
            variance_per_scan=_f(row.get("variance_per_scan")),
            zero_rate_obs=_f(row.get("zero_rate_obs")),
            n_required_095=_i(row.get("n_required_095")),
        )
    return out


def _grain_map(path: Path) -> dict[str, GrainStats]:
    out: dict[str, GrainStats] = {}
    for row in _read_csv(path):
        out[row["job"]] = GrainStats(
            grain_total=_i(row.get("grain_total")),
            grain_kept=_i(row.get("grain_kept")),
            grain_isolated=_i(row.get("grain_isolated")),
            kept_mean_diameter_nm=_f(row.get("kept_mean_diameter_nm")),
            kept_std_diameter_nm=_f(row.get("kept_std_diameter_nm")),
            isolated_mean_diameter_nm=_f(row.get("isolated_mean_diameter_nm")),
            isolated_std_diameter_nm=_f(row.get("isolated_std_diameter_nm")),
        )
    return out


def _summary_stats(path: Path) -> tuple[float, float]:
    values = {r["metric"]: r["value"] for r in _read_csv(path)}
    return float(values["mean_diameter_nm"]), float(values["std_diameter_nm"])


def _load_root(root: Path, wt_percent: int) -> RootStats:
    counts_rows = _read_csv(root / "particle_counts_by_map.csv")
    diam_mean, diam_std = _summary_stats(root / "particle_summary_stats.csv")
    method_stats = {job: _job_stats(counts_rows, job) for job in JOB_ORDER}
    return RootStats(
        label=f"{wt_percent} wt% SiNP",
        wt_percent=wt_percent,
        root=root,
        samples=sorted(method_stats[PRIMARY_JOB].sample_means),
        diameter_mean_nm=diam_mean,
        diameter_std_nm=diam_std,
        method_stats=method_stats,
        method_fits=_fit_map(root / "summary_outputs" / "fits" / "fit_summary.csv"),
        grain_stats=_grain_map(root / "grain_summary_by_job.csv"),
    )


def _figure(doc: Document, title: str, paths: list[Path], width: float = 5.9) -> None:
    existing = [p for p in paths if p.exists()]
    if not existing:
        doc.add_paragraph(f"[MISSING FIGURE] {title}")
        return
    for path in existing:
        doc.add_picture(str(path), width=Inches(width))
    doc.add_paragraph(title)
    for path in existing:
        doc.add_paragraph(f"Source: {path}")


def _combined_grid_paths(root: RootStats, prefix: str, job: str) -> list[Path]:
    base = root.root / "summary_outputs" / "combined"
    return [
        base / f"{prefix}_wt{root.wt_percent}_{job}.png",
    ]


def _table(doc: Document, title: str, headers: list[str], rows: list[list[str]]) -> None:
    p = doc.add_paragraph(title)
    if p.runs:
        p.runs[0].bold = True
    table = doc.add_table(rows=1, cols=len(headers))
    for i, header in enumerate(headers):
        table.rows[0].cells[i].text = header
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = value


def _modulus_paired_rows(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    rows = _read_csv(path)
    out: list[list[str]] = []
    labels = {
        "gwy_stats": "Baseline Gwyddion stats",
        "gwy_ops_py_stats": "Gwyddion preprocess + Python stats",
        "raw_minmax": "Raw export + min/max filter",
        "raw_chauvenet": "Raw export + Chauvenet",
        "raw_three_sigma": "Raw export + 3-sigma",
    }
    for row in rows:
        out.append(
            [
                labels.get(row.get("method", ""), row.get("method", "")),
                row.get("n_pairs", ""),
                f"{_f(row.get('median_ratio_avg')):.3f}",
                f"{_f(row.get('mean_ratio_avg')):.3f}",
                f"{_f(row.get('median_delta_avg')) / 1e6:.3f}",
                f"{_f(row.get('mean_delta_avg')) / 1e6:.3f}",
                f"{_f(row.get('mean_delta_n_valid')):.1f}",
            ]
        )
    return out


def _poisson_success(mu: float, target: int) -> float:
    if mu <= 0:
        return 0.0
    term = math.exp(-mu)
    cdf = term
    for k in range(1, target):
        term *= mu / k
        cdf += term
    return max(0.0, min(1.0, 1.0 - cdf))


def _required_scans(lam: float, p: float, target: int, conf: float, max_scans: int) -> int:
    eff = lam * p
    if eff <= 0:
        return max_scans
    for n in range(1, max_scans + 1):
        if _poisson_success(eff * n, target) >= conf:
            return n
    return max_scans


def _availability_crossover_p(lam: float, available_scans: int, target: int, conf: float) -> float | None:
    if lam <= 0 or available_scans <= 0:
        return None
    if _poisson_success(lam * available_scans, target) < conf:
        return None
    low = 0.0
    high = 1.0
    for _ in range(60):
        mid = (low + high) / 2.0
        success = _poisson_success(lam * available_scans * mid, target)
        if success >= conf:
            high = mid
        else:
            low = mid
    return high


def _overview_plot(wt10: RootStats, wt25: RootStats) -> Path:
    import matplotlib.pyplot as plt

    out = ASSET_DIR / "chapter6_stage1_overview.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    means_c = [wt10.method_stats[PRIMARY_JOB].mean_count, wt25.method_stats[PRIMARY_JOB].mean_count]
    stds_c = [wt10.method_stats[PRIMARY_JOB].std_count, wt25.method_stats[PRIMARY_JOB].std_count]
    means_i = [wt10.method_stats[PRIMARY_JOB].mean_isolated, wt25.method_stats[PRIMARY_JOB].mean_isolated]
    stds_i = [wt10.method_stats[PRIMARY_JOB].std_isolated, wt25.method_stats[PRIMARY_JOB].std_isolated]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    x = [0, 1]
    w = 0.34
    ax.bar([a - w / 2 for a in x], means_c, w, yerr=stds_c, capsize=4, label="Candidate count/scan")
    ax.bar([a + w / 2 for a in x], means_i, w, yerr=stds_i, capsize=4, label="Isolated count/scan")
    ax.set_xticks(x, [wt10.label, wt25.label])
    ax.set_ylabel("Particles per scan")
    ax.set_title("Stage 1 overview\nPrimary-route means with standard deviations")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def _crossover_plot(wt10: RootStats, wt25: RootStats) -> Path:
    import matplotlib.pyplot as plt

    out = ASSET_DIR / "chapter6_crossover_by_method.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    ps = [i / 100 for i in range(1, 101)]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), sharey=True)
    for ax, root in zip(axes, [wt10, wt25]):
        available_scans = root.method_stats[PRIMARY_JOB].maps
        max_scans = max(available_scans, 220)
        label_offsets = {PRIMARY_JOB: -18, COMPARISON_JOB: 18}
        for job in JOB_ORDER:
            lam = root.method_fits[job].mean_per_scan
            ys = [_required_scans(lam, p, TARGET_ISOLATED, CONFIDENCE, max_scans) for p in ps]
            style = JOB_STYLES.get(job, {})
            ax.plot(
                ps,
                ys,
                linewidth=style.get("linewidth", 1.4),
                linestyle=style.get("linestyle", "-"),
                marker=style.get("marker"),
                markevery=max(1, int(len(ps) / 10.0)),
                markersize=4,
                color=style.get("color"),
                label=_job_label(job),
            )
            if job in (PRIMARY_JOB, COMPARISON_JOB):
                p_cross = _availability_crossover_p(lam, available_scans, TARGET_ISOLATED, CONFIDENCE)
                if p_cross is not None and 0.0 < p_cross <= 1.0:
                    y_cross = _required_scans(lam, p_cross, TARGET_ISOLATED, CONFIDENCE, max_scans)
                    ax.scatter([p_cross], [y_cross], s=34, zorder=5, color=style.get("color"), marker=style.get("marker", "o"))
                    ax.annotate(
                        f"{_job_label(job)}\np* = {p_cross:.3f}",
                        xy=(p_cross, y_cross),
                        xytext=(8, label_offsets.get(job, 10)),
                        textcoords="offset points",
                        fontsize=7,
                        va="center",
                        ha="left",
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=style.get("color", "black"), alpha=0.9),
                    )
        ax.axhline(available_scans, color="black", linestyle="--", linewidth=1.1, label="Available scans")
        ax.text(0.985, available_scans - 4, f"Available scans\n= {available_scans}", ha="right", va="top", fontsize=8)
        ax.set_title(f"{root.label}\nRequired scans vs confirmation probability")
        ax.set_xlabel("Confirmation probability p")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Required scans for 95% confidence")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def _method_rows(root: RootStats) -> list[list[str]]:
    primary_mean = root.method_stats[PRIMARY_JOB].mean_isolated
    rows = []
    for job in JOB_ORDER:
        stats = root.method_stats[job]
        fit = root.method_fits[job]
        rows.append([
            root.label,
            _job_label(job),
            job,
            f"{stats.mean_isolated:.2f}",
            f"{stats.std_isolated:.2f}",
            _pct(stats.zero_isolated_rate),
            str(fit.n_required_095),
            f"{stats.mean_isolated / primary_mean:.2f}x",
            f"{stats.mean_isolated / root.wt_percent:.3f}",
        ])
    return rows


def _grain_rows(root: RootStats) -> list[list[str]]:
    rows = []
    for job in JOB_ORDER:
        grain = root.grain_stats[job]
        rows.append([
            root.label,
            _job_label(job),
            str(grain.grain_total),
            str(grain.grain_kept),
            str(grain.grain_isolated),
            _pm(grain.kept_mean_diameter_nm, grain.kept_std_diameter_nm, "nm"),
            _pm(grain.isolated_mean_diameter_nm, grain.isolated_std_diameter_nm, "nm"),
        ])
    return rows


def _sample_rows(root: RootStats) -> list[list[str]]:
    stats = root.method_stats[PRIMARY_JOB]
    rows = []
    for sample in root.samples:
        rows.append([
            root.label,
            sample.replace("_", " "),
            str(stats.sample_scan_counts[sample]),
            f"{stats.sample_means[sample]:.2f}",
            f"{stats.sample_stds[sample]:.2f}",
            f"{stats.sample_pct_nonzero[sample]:.1f}%",
        ])
    return rows


def _write(doc_path: Path, wt10: RootStats, wt25: RootStats) -> None:
    overview = _overview_plot(wt10, wt25)
    crossover = _crossover_plot(wt10, wt25)
    p10 = wt10.method_stats[PRIMARY_JOB]
    p25 = wt25.method_stats[PRIMARY_JOB]
    f10 = wt10.method_fits[PRIMARY_JOB]
    f25 = wt25.method_fits[PRIMARY_JOB]
    c10 = wt10.method_stats[COMPARISON_JOB]
    c25 = wt25.method_stats[COMPARISON_JOB]
    cf10 = wt10.method_fits[COMPARISON_JOB]
    cf25 = wt25.method_fits[COMPARISON_JOB]

    doc = Document()
    doc.add_heading("Chapter 6 Draft - Stage 1 Results and Feasibility Decision", level=0)
    doc.add_paragraph(f"Draft generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    doc.add_paragraph("Scope: measurement feasibility, scan efficiency, and decision thresholds only.")

    doc.add_heading("6.1 Processing Validation - Baseline PEGDA (No SiNP)", level=1)
    doc.add_paragraph("Baseline PEGDA validation in this chapter is carried primarily by the modulus method-comparison study. That study was used to evaluate forward/backward agreement, route consistency, and the practical effect of pixel loss before extending the Stage 1 logic to the particle-count workflow.")
    doc.add_paragraph("The modulus baseline artifact is limited in scope: it was performed on one PEGDA sample and one fracture-surface side, so it should be interpreted as method-validation evidence rather than a population-level PEGDA modulus study. Even with that scope limit, the paired forward/backward comparison and the route-consistency summaries provide the direct baseline-validation evidence requested in the thesis outline.")
    doc.add_paragraph("Unit provenance should be stated explicitly for this section. In this workflow, Gwyddion-derived outputs inherit the physical unit attached to the active data field when that unit is actually present in the imported field metadata. A direct one-file verification run on the current PEGDA modulus TIFFs showed that pygwy did not detect an embedded modulus z-unit for that file, so the current modulus source summaries carrying units = kPa should be treated as a workflow-level fallback/default assignment rather than fully verified source metadata truth. That same one-file verification run also produced a negative modulus export, so the absolute modulus value path should be treated as provisional pending targeted re-validation of the TIFF unit/processing chain. By contrast, the Stage 1 particle-count outputs are count-based summaries and therefore do not inherit a physical z-unit, while particle and grain diameter summaries are derived geometric metrics reported in nm.")
    _table(
        doc,
        "Table 6.1 - Paired forward/backward modulus baseline summary by method",
        ["Method", "Paired scans", "Median B/F ratio", "Mean B/F ratio", "Median delta avg (GPa-equiv.)", "Mean delta avg (GPa-equiv.)", "Mean delta n_valid"],
        _modulus_paired_rows(MODULUS_PAIRED_SUMMARY),
    )
    _figure(
        doc,
        "Figure 6.1 - Baseline PEGDA modulus validation figures. The paired-ratio box plot summarizes forward/backward agreement by method, while the absolute-modulus bars show method-level forward and backward modulus summaries with standard-error bars. These figures support route consistency and the forward-only selection used later in the Stage 1 topography workflow.",
        [
            MODULUS_ASSET_DIR / "paired_ratio_boxplot.png",
            MODULUS_ASSET_DIR / "forward_absolute_modulus_bar.png",
            MODULUS_ASSET_DIR / "backward_absolute_modulus_bar.png",
        ],
        width=5.5,
    )
    _figure(
        doc,
        "Figure 6.1b - Forward and backward baseline PEGDA modulus heatmaps plus one representative delta-versus-baseline comparison heatmap. These plots show the spatial baseline field for each scan direction and one example of how a comparison route shifts the baseline modulus pattern.",
        [
            MODULUS_FORWARD_COMPARE_DIR / "plots" / "heatmap_two_panel__baseline.png",
            MODULUS_BACKWARD_COMPARE_DIR / "plots" / "heatmap_two_panel__baseline.png",
            MODULUS_FORWARD_COMPARE_DIR / "plots" / "heatmap_two_panel__delta_vs_baseline__raw_chauvenet.png",
        ],
        width=5.5,
    )
    _figure(doc, "Figure 6.1c - Stage 1 overview for PEGDA, 1 wt% TPO, no coating, comparing 10 wt% and 25 wt% SiNP. Bars show mean candidate and isolated counts per scan with standard deviations.", [overview])

    doc.add_heading("6.2 Stage 1 - Particle Presence in PEGDA-SiNP", level=1)
    doc.add_heading("6.2.1 Scan Inventory", level=2)
    _table(doc, "Table 6.2 - Scan inventory used for the current Stage 1 analysis", ["System", "Sample sets", "Scans analyzed", "Scan size (um x um)", "Pixel grid", "Resolution (nm/pixel)", "Nominal map grid"], [[wt10.label, str(len(wt10.samples)), str(p10.maps), SCAN_SIZE_UM, PIXEL_GRID, RESOLUTION_NM_PER_PIXEL, NOMINAL_GRID], [wt25.label, str(len(wt25.samples)), str(p25.maps), SCAN_SIZE_UM, PIXEL_GRID, RESOLUTION_NM_PER_PIXEL, NOMINAL_GRID]])
    doc.add_paragraph(f"{wt10.label} contributed {p10.maps} scans across {len(wt10.samples)} sample sets. {wt25.label} contributed {p25.maps} scans across {len(wt25.samples)} sample sets. Each scan is a 5 um x 5 um AFM image on a nominal 21 x 21 survey grid with 512 x 512 pixels.")
    doc.add_paragraph("The nominal survey layout was 21 x 21 scans, but the analyzed inventories reflect only scans that were actually collected and retained in the grouped dataset. Some 25 wt% grouped sample sets were therefore incomplete relative to the nominal grid, even though the total analyzed inventory remained well above the later scan-sufficiency threshold.")

    doc.add_heading("6.2.2 Particle Count Per Scan", level=2)
    doc.add_paragraph(f"Under the primary route ({PRIMARY_JOB}), retained candidate counts averaged {_pm(p10.mean_count, p10.std_count)} particles per scan for {wt10.label} and {_pm(p25.mean_count, p25.std_count)} particles per scan for {wt25.label}. Zero-count scans were rare in both sets ({_pct(p10.zero_count_rate)} and {_pct(p25.zero_count_rate)}).")
    doc.add_paragraph(f"The {wt25.label} set showed a modest increase in candidate density relative to {wt10.label} ({p25.mean_count / p10.mean_count:.2f}x), but this stage still describes candidate features, not fully validated true particles.")
    doc.add_paragraph("Figures 6.2A and 6.2B show histograms of retained candidate-particle count per scan. In these plots, frequency is the number of scans falling at each retained-count value. For both loadings, the highest frequencies occur at low retained counts, indicating that most scans contain only a small number of retained candidate particles rather than large multi-particle populations.")
    doc.add_paragraph("Figures 6.3A and 6.3B are mean count maps across the grouped sample sets for each loading. They show that retained candidate particles are distributed across the surveyed grid rather than concentrated at a single localized region. These maps summarize mean count only; they do not show per-position standard deviation, which should be treated as a separate variability layer if spatial uncertainty is discussed in detail.")
    _table(doc, "Table 6.3 - Primary-method candidate count summary", ["System", "Mean count/scan", "Std", "Min", "Max", "Zero-count rate"], [[wt10.label, f"{p10.mean_count:.2f}", f"{p10.std_count:.2f}", str(p10.min_count), str(p10.max_count), _pct(p10.zero_count_rate)], [wt25.label, f"{p25.mean_count:.2f}", f"{p25.std_count:.2f}", str(p25.min_count), str(p25.max_count), _pct(p25.zero_count_rate)]])
    _figure(doc, "Figure 6.2 - Particle-count histograms for PEGDA, 1 wt% TPO, no coating, with 10 wt% and 25 wt% SiNP under the primary route.", [wt10.root / "fig_particle_count_hist.png", wt25.root / "fig_particle_count_hist.png"])
    _figure(doc, "Figure 6.3 - Particle-count grid heatmaps for the primary route, separated by SiNP loading.", [wt10.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_wt10_{PRIMARY_JOB}.png", wt25.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_wt25_{PRIMARY_JOB}.png"])
    _figure(
        doc,
        "Figure 6.3b - Empirical uncertainty companions for the mean kept-particle heatmaps under the primary route. Standard-deviation maps show between-sample spread, standard-error maps show uncertainty in the estimated mean, coefficient-of-variation maps normalize variability by the local mean, and n-maps show the number of contributing sample sets at each scan position.",
        [
            wt10.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_std_wt10_{PRIMARY_JOB}.png",
            wt10.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_se_wt10_{PRIMARY_JOB}.png",
            wt10.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_cv_wt10_{PRIMARY_JOB}.png",
            wt10.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_n_wt10_{PRIMARY_JOB}.png",
            wt25.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_std_wt25_{PRIMARY_JOB}.png",
            wt25.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_se_wt25_{PRIMARY_JOB}.png",
            wt25.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_cv_wt25_{PRIMARY_JOB}.png",
            wt25.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_n_wt25_{PRIMARY_JOB}.png",
        ],
        width=5.0,
    )

    doc.add_heading("6.2.3 Particle Diameter Distribution", level=2)
    doc.add_paragraph(f"After applying the configured {DIAMETER_FILTER_NM} nm filter, retained particle diameter averaged {_pm(wt10.diameter_mean_nm, wt10.diameter_std_nm, 'nm')} for {wt10.label} and {_pm(wt25.diameter_mean_nm, wt25.diameter_std_nm, 'nm')} for {wt25.label}. The retained means remain centered on the expected SiNP size band.")
    _table(doc, "Table 6.4 - Retained particle diameter summary", ["System", "Filter band (nm)", "Mean diameter (nm)", "Std diameter (nm)"], [[wt10.label, DIAMETER_FILTER_NM, f"{wt10.diameter_mean_nm:.2f}", f"{wt10.diameter_std_nm:.2f}"], [wt25.label, DIAMETER_FILTER_NM, f"{wt25.diameter_mean_nm:.2f}", f"{wt25.diameter_std_nm:.2f}"]])
    _figure(doc, "Figure 6.4 - Retained particle-diameter histograms for PEGDA, 1 wt% TPO, no coating, comparing 10 wt% and 25 wt% SiNP after filtering.", [wt10.root / "fig_particle_diameter_hist.png", wt25.root / "fig_particle_diameter_hist.png"])

    doc.add_heading("6.3 Isolation Analysis", level=1)
    doc.add_heading("6.3.1 Isolation Count Per Scan", level=2)
    doc.add_paragraph(f"Isolation is the controlling Stage 1 feasibility metric because only spatially separated targets are usable for Stage 2. In the current workflow, isolation is defined by a minimum center-to-center spacing of {ISOLATION_DISTANCE_NM} nm.")
    doc.add_paragraph(f"Primary-route isolated counts averaged {_pm(p10.mean_isolated, p10.std_isolated)} per scan for {wt10.label} and {_pm(p25.mean_isolated, p25.std_isolated)} per scan for {wt25.label}. Scans with at least one isolated particle accounted for {p10.pct_with_isolated:.1f}% and {p25.pct_with_isolated:.1f}% of the two datasets, respectively.")
    doc.add_paragraph(f"The key result is that the higher-loading dataset did not produce a proportionally larger isolated-particle yield. Mean isolated counts remained close ({p10.mean_isolated:.2f} versus {p25.mean_isolated:.2f} isolated particles per scan) even though candidate density increased.")
    doc.add_paragraph("As in the retained-count maps, the isolated-count heatmaps summarize mean isolated-particle count at each scan position across the grouped sample sets. They are therefore useful for showing spatial distribution, but not for showing the full between-sample spread at each position.")
    _table(doc, "Table 6.5 - Sample-level isolated-particle yield under the primary route", ["System", "Sample set", "Scans", "Mean isolated/scan", "Std", "% scans with >=1 isolated"], _sample_rows(wt10) + _sample_rows(wt25))
    _figure(doc, "Figure 6.5 - Histograms of isolated-particle counts per scan for the primary route, separated by 10 wt% and 25 wt% SiNP.", [wt10.root / "fig_isolated_count_hist.png", wt25.root / "fig_isolated_count_hist.png"])
    _figure(doc, "Figure 6.6 - Isolated-particle grid heatmaps for the primary route, separated by SiNP loading.", [wt10.root / "summary_outputs" / "combined" / f"fig_isolated_count_grid_wt10_{PRIMARY_JOB}.png", wt25.root / "summary_outputs" / "combined" / f"fig_isolated_count_grid_wt25_{PRIMARY_JOB}.png"])
    _figure(
        doc,
        "Figure 6.6b - Empirical uncertainty companions for the mean isolated-particle heatmaps under the primary route. These maps separate between-sample spread (std), uncertainty in the mean estimate (SE), normalized variability (CV), and spatial coverage (n contributing sample sets).",
        [
            wt10.root / "summary_outputs" / "combined" / f"fig_isolated_count_grid_std_wt10_{PRIMARY_JOB}.png",
            wt10.root / "summary_outputs" / "combined" / f"fig_isolated_count_grid_se_wt10_{PRIMARY_JOB}.png",
            wt10.root / "summary_outputs" / "combined" / f"fig_isolated_count_grid_cv_wt10_{PRIMARY_JOB}.png",
            wt10.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_n_wt10_{PRIMARY_JOB}.png",
            wt25.root / "summary_outputs" / "combined" / f"fig_isolated_count_grid_std_wt25_{PRIMARY_JOB}.png",
            wt25.root / "summary_outputs" / "combined" / f"fig_isolated_count_grid_se_wt25_{PRIMARY_JOB}.png",
            wt25.root / "summary_outputs" / "combined" / f"fig_isolated_count_grid_cv_wt25_{PRIMARY_JOB}.png",
            wt25.root / "summary_outputs" / "combined" / f"fig_particle_count_grid_n_wt25_{PRIMARY_JOB}.png",
        ],
        width=5.0,
    )

    doc.add_heading("6.3.2 Required Scans for 95% Confidence", level=2)
    doc.add_paragraph(f"Using the Poisson baseline fit, a target of {TARGET_ISOLATED} isolated particles, and {int(CONFIDENCE * 100)}% confidence, the primary route required {f10.n_required_095} scans for {wt10.label} and {f25.n_required_095} scans for {wt25.label}. Both analyzed inventories greatly exceed those requirements.")
    doc.add_paragraph("In Table 6.5, primary lambda is the mean isolated-particle count per scan under the primary route. The observed zero-isolated rate is the empirical fraction of scans with zero isolated particles. The required-scan value is the smallest number of scans for which the modeled probability of obtaining at least 30 isolated particles reaches 95%.")
    _table(doc, "Table 6.6 - Required scans for isolated-particle sufficiency under the primary route", ["System", "Primary lambda", "Observed zero-isolated rate", "Required scans (95%)", "Available scans"], [[wt10.label, f"{f10.mean_per_scan:.3f}", _pct(f10.zero_rate_obs), str(f10.n_required_095), str(p10.maps)], [wt25.label, f"{f25.mean_per_scan:.3f}", _pct(f25.zero_rate_obs), str(f25.n_required_095), str(p25.maps)]])

    doc.add_heading("6.4 Grain Metrics", level=1)
    doc.add_paragraph("Grain exports are now available for the full method matrix. These do not replace particle or isolation statistics, but they strengthen the segmentation-quality discussion and provide an additional diameter-based consistency check.")
    _table(doc, "Table 6.7 - Grain summary across the full method matrix", ["System", "Method", "Grain total", "Grain kept", "Grain isolated", "Kept diameter mean +/- std", "Isolated diameter mean +/- std"], _grain_rows(wt10) + _grain_rows(wt25))
    _figure(doc, "Figure 6.7 - Full-method grain diameter summaries for PEGDA, 1 wt% TPO, no coating, separated by 10 wt% and 25 wt% SiNP. Bar plots show method-wise mean +/- standard deviation; box plots show the corresponding diameter distributions.", [wt10.root / "summary_outputs" / "compare_by_wt" / "fig_grain_diameter_nm_kept_mean_by_job.png", wt10.root / "summary_outputs" / "compare_by_wt" / "fig_grain_diameter_nm_isolated_box_by_job.png", wt25.root / "summary_outputs" / "compare_by_wt" / "fig_grain_diameter_nm_kept_mean_by_job.png", wt25.root / "summary_outputs" / "compare_by_wt" / "fig_grain_diameter_nm_isolated_box_by_job.png"], width=5.5)

    doc.add_heading("6.5 Processing Route Sensitivity", level=1)
    doc.add_paragraph(f"The practical sensitivity question is not whether the processing routes produce visually different maps, but whether they materially change isolated-particle yield and therefore the number of scans needed for Stage 1 sufficiency. Relative to the primary route, the comparison route ({COMPARISON_JOB}) reduced mean isolated yield from {_pm(p10.mean_isolated, p10.std_isolated)} to {_pm(c10.mean_isolated, c10.std_isolated)} per scan in {wt10.label} and from {_pm(p25.mean_isolated, p25.std_isolated)} to {_pm(c25.mean_isolated, c25.std_isolated)} per scan in {wt25.label}. The corresponding 95% scan requirements increased from {f10.n_required_095} to {cf10.n_required_095} scans and from {f25.n_required_095} to {cf25.n_required_095} scans.")
    doc.add_paragraph("The full method table should be interpreted provisionally. A targeted post-generation verification identified a mask write-back issue in the thresholded particle-analysis path, so the full all-method matrix must be regenerated after that fix before any final claim is made about whether threshold variants truly collapse within a preprocessing family.")
    _table(doc, "Table 6.8 - All-method comparison with loading-normalized isolation yield", ["System", "Method", "Job/profile", "Mean isolated/scan", "Std", "Zero-isolated rate", "Req. scans (95%)", "Relative to primary", "Isolated/scan/wt%"], _method_rows(wt10) + _method_rows(wt25))
    _figure(doc, "Figure 6.8 - Full-method comparison of mean isolated-particle yield by job and SiNP loading for PEGDA, 1 wt% TPO, no coating. These plots summarize how preprocessing and threshold choices affect isolated-particle yield.", [wt10.root / "summary_outputs" / "compare_by_wt" / "fig_isolated_count_mean_by_job_10pct.png", wt25.root / "summary_outputs" / "compare_by_wt" / "fig_isolated_count_mean_by_job_25pct.png"])
    _figure(doc, "Figure 6.9 - Aggregate Poisson success-probability curves for all methods, separated by 10 wt% and 25 wt% SiNP. Horizontal dashed lines mark the 90%, 95%, and 99% success thresholds; vertical markers show the 95%-requirement scan count for each method.", [wt10.root / "summary_outputs" / "fits" / "risk_aggregate_wt_percent_10_poisson.png", wt25.root / "summary_outputs" / "fits" / "risk_aggregate_wt_percent_25_poisson.png"])

    doc.add_heading("6.6 Stage 2 Trigger / Crossover Decision", level=1)
    p_cross_10 = _availability_crossover_p(f10.mean_per_scan, p10.maps, TARGET_ISOLATED, CONFIDENCE)
    p_cross_25 = _availability_crossover_p(f25.mean_per_scan, p25.maps, TARGET_ISOLATED, CONFIDENCE)
    doc.add_paragraph("The Stage 2 trigger is expressed as a sensitivity study in confirmation probability p. The question is how far the confirmation rate could drop before the current Stage 1 scan pool would no longer meet the 30-particle, 95%-confidence target.")
    doc.add_paragraph("Figure 6.10 should be read as follows: the x-axis is the assumed fraction of Stage 1 isolated candidates that would later be confirmed as true particles in Stage 2, and the y-axis is the number of scans required to still achieve the Stage 2 target. The horizontal reference line is the number of scans already available. The crossover value p* is therefore the minimum confirmation fraction required for the currently available inventory to remain sufficient; it is not the probability that a crossover event occurs.")
    _table(doc, "Table 6.9 - Minimum confirmation fraction p* required for the current scan inventory to remain sufficient", ["System", "Primary lambda", "Available scans", "Minimum confirmation fraction p*"], [[wt10.label, f"{f10.mean_per_scan:.3f}", str(p10.maps), f"{p_cross_10:.3f}" if p_cross_10 is not None else "not reachable"], [wt25.label, f"{f25.mean_per_scan:.3f}", str(p25.maps), f"{p_cross_25:.3f}" if p_cross_25 is not None else "not reachable"]])
    _figure(doc, "Figure 6.10 - Required scan count versus confirmation probability p across the full method matrix, with the available-scan inventory shown as a horizontal reference and labeled crossover points for the primary and comparison routes. PEGDA, 1 wt% TPO, no coating, separated by 10 wt% and 25 wt% SiNP.", [crossover], width=6.6)

    doc.add_heading("6.7 Stage 1 Decision", level=1)
    doc.add_paragraph(f"For {wt10.label}, candidate particle presence was confirmed, the retained diameter distribution remained consistent with the configured {DIAMETER_FILTER_NM} nm size window, isolated particles occurred in {p10.pct_with_isolated:.1f}% of scans under the primary route, and the analyzed inventory of {p10.maps} scans greatly exceeded the {f10.n_required_095}-scan requirement.")
    doc.add_paragraph(f"For {wt25.label}, candidate particle presence was likewise confirmed, the retained diameter distribution remained acceptable, isolated particles occurred in {p25.pct_with_isolated:.1f}% of scans under the primary route, and the analyzed inventory of {p25.maps} scans greatly exceeded the corresponding {f25.n_required_095}-scan requirement.")
    doc.add_paragraph("Stage 2 high-resolution interrogation is therefore justified for both loadings under the current Stage 1 interpretation. The comparative result is that higher loading increased candidate density modestly, but did not materially improve isolated-particle availability enough to change the decision.")

    doc.add_heading("6.8 Discussion and Limits", level=1)
    doc.add_paragraph("Discussion is appropriate here so long as it remains tied to measurement feasibility. At present the chapter supports two firm claims and one provisional claim. The firm claims are that isolated particles are available in sufficient number under the primary route and that higher loading does not automatically produce a higher yield of usable isolated targets. The provisional claim is the detailed threshold-variant comparison, which must be regenerated after the threshold-mask fix is propagated through the full dataset.")
    doc.add_paragraph("The remaining uncertainty is not whether isolated candidates exist, but what fraction of those candidates will be confirmed as true particles once Stage 2 multi-channel validation is performed. That is why the crossover figure belongs in this chapter: it converts Stage 2 from a vague next step into a quantitative decision threshold while keeping Stage 2 itself as a neutral unknown to be investigated rather than assumed.")
    doc.add_paragraph("A second discussion point is model justification. The current datasets are large enough that both 10 wt% and 25 wt% inventories substantially exceed the scan requirement for the immediate Stage 1 feasibility claim, even though the two loadings do not contain equal numbers of scans. That does not by itself prove that Poisson is the only appropriate count model; rather, it shows that the present inventories are comfortably above the threshold needed to estimate the isolated-particle rate for this decision problem.")

    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(doc_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Populate the Chapter 6 thesis draft from current Stage 1 output roots.")
    parser.add_argument("--wt10-root", required=True)
    parser.add_argument("--wt25-root", required=True)
    parser.add_argument("--docx-path", default="docs/Thesis/Chapter6_Stage1_Results_Feasibility_DRAFT.docx")
    args = parser.parse_args()
    _write(Path(args.docx_path), _load_root(Path(args.wt10_root), 10), _load_root(Path(args.wt25_root), 25))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
