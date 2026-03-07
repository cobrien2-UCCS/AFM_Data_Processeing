from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median

from docx import Document
from docx.shared import Inches
import matplotlib.pyplot as plt


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _f(value: str | None) -> float:
    if value in (None, "", "nan", "NaN"):
        return float("nan")
    return float(value)


def _i(value: str | None) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))


def _add_table(doc: Document, title: str, headers: list[str], rows: list[list[str]]) -> None:
    p = doc.add_paragraph(title)
    if p.runs:
        p.runs[0].bold = True
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = value


def _add_figure(doc: Document, title: str, path: Path, width: float = 6.0) -> None:
    if path.exists():
        doc.add_picture(str(path), width=Inches(width))
        doc.add_paragraph(title)
        doc.add_paragraph(f"Source: {path}")
    else:
        doc.add_paragraph(f"[MISSING FIGURE] {title}")
        doc.add_paragraph(f"Expected source: {path}")


def _add_heading_paragraph(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True


def _plot_boxplot(out_path: Path, title: str, labels: list[str], series: list[list[float]], ylabel: str) -> None:
    if not series or not any(s for s in series):
        return
    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    ax.boxplot(series, tick_labels=labels, showfliers=False)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def _aggregate_compare_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        method = row["method"]
        avg = _f(row.get("avg_value"))
        avg_baseline = _f(row.get("avg_baseline"))
        std = _f(row.get("std_value"))
        std_baseline = _f(row.get("std_baseline"))
        n_valid = _f(row.get("n_valid"))
        n_valid_baseline = _f(row.get("n_valid_baseline"))
        delta_avg = _f(row.get("delta_avg"))
        delta_std = _f(row.get("delta_std"))
        delta_n = _f(row.get("delta_n_valid"))
        if avg_baseline == avg_baseline and avg_baseline != 0.0 and avg == avg:
            grouped[method]["ratio_avg"].append(avg / avg_baseline)
        if std_baseline == std_baseline and std_baseline != 0.0 and std == std:
            grouped[method]["ratio_std"].append(std / std_baseline)
        if n_valid_baseline == n_valid_baseline and n_valid_baseline != 0.0 and n_valid == n_valid:
            grouped[method]["ratio_n"].append(n_valid / n_valid_baseline)
        if delta_avg == delta_avg:
            grouped[method]["delta_avg"].append(delta_avg)
        if delta_std == delta_std:
            grouped[method]["delta_std"].append(delta_std)
        if delta_n == delta_n:
            grouped[method]["delta_n"].append(delta_n)

    out: dict[str, dict[str, float]] = {}
    for method, metrics in grouped.items():
        out[method] = {
            "n_scans": len(metrics["delta_avg"]),
            "mean_ratio_avg": mean(metrics["ratio_avg"]) if metrics["ratio_avg"] else float("nan"),
            "median_ratio_avg": median(metrics["ratio_avg"]) if metrics["ratio_avg"] else float("nan"),
            "mean_delta_avg": mean(metrics["delta_avg"]) if metrics["delta_avg"] else float("nan"),
            "mean_ratio_std": mean(metrics["ratio_std"]) if metrics["ratio_std"] else float("nan"),
            "mean_delta_std": mean(metrics["delta_std"]) if metrics["delta_std"] else float("nan"),
            "mean_delta_n": mean(metrics["delta_n"]) if metrics["delta_n"] else float("nan"),
            "min_delta_n": min(metrics["delta_n"]) if metrics["delta_n"] else float("nan"),
            "max_delta_n": max(metrics["delta_n"]) if metrics["delta_n"] else float("nan"),
        }
    return out


def _load_baseline_inventory(path: Path) -> tuple[int, str]:
    rows = _read_csv(path)
    units = rows[0].get("units", "") if rows else ""
    return len(rows), units


def _fmt_ratio(value: float) -> str:
    return "" if value != value else f"{value:.3f}"


def _fmt_num(value: float) -> str:
    return "" if value != value else f"{value:.3e}"


def build_report(
    forward_compare_dir: Path,
    backward_compare_dir: Path,
    paired_dir: Path,
    forward_baseline_summary: Path,
    backward_baseline_summary: Path,
    output_docx: Path,
) -> None:
    forward_long = _read_csv(forward_compare_dir / "comparison_long.csv")
    backward_long = _read_csv(backward_compare_dir / "comparison_long.csv")
    paired_rows = _read_csv(paired_dir / "fwd_bwd_summary.csv")
    paired_long = _read_csv(paired_dir / "fwd_bwd_long.csv")
    forward_baseline_rows = _read_csv(forward_baseline_summary)
    backward_baseline_rows = _read_csv(backward_baseline_summary)

    forward_agg = _aggregate_compare_rows(forward_long)
    backward_agg = _aggregate_compare_rows(backward_long)
    n_forward, units_forward = _load_baseline_inventory(forward_baseline_summary)
    n_backward, units_backward = _load_baseline_inventory(backward_baseline_summary)
    output_dir = output_docx.parent
    asset_dir = output_dir / "modulus_baseline_assets"
    asset_dir.mkdir(parents=True, exist_ok=True)

    doc = Document()
    doc.add_heading("Modulus Baseline Validation Report", level=0)
    doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    doc.add_paragraph(
        "This report summarizes the baseline PEGDA modulus method-comparison results used to support Chapter 6, "
        "Section 6.1 (Baseline PEGDA Validation). Its purpose is to document forward/backward agreement, route "
        "consistency, and the practical basis for restricting the Stage 1 topography workflow to forward scans."
    )

    _add_heading_paragraph(doc, "Workflow and method definitions")
    doc.add_paragraph(
        "The modulus baseline workflow compares several processing/statistics routes applied to the same PEGDA modulus "
        "scan set. The baseline route is the Gwyddion-statistics path (`modulus_gwy_stats` / `gwy_stats`), which uses "
        "Gwyddion preprocessing and Gwyddion-derived summary statistics. Alternative routes keep the same overall scan set "
        "but change how the post-preprocessing statistics or raw-value filtering are performed."
    )
    _add_table(
        doc,
        "Table M0 - Method definitions used in the modulus baseline validation",
        ["Method", "Definition", "Purpose in this report"],
        [
            ["modulus_gwy_stats (baseline)", "Gwyddion preprocessing with Gwyddion-derived statistics.", "Reference route for all modulus comparisons."],
            ["gwy_ops_py_stats", "Gwyddion preprocessing with Python-derived statistics on the processed field.", "Checks whether the stats engine changes the modulus summary materially."],
            ["raw_minmax", "Raw-value export with Python min/max validity filtering.", "Checks a simple deterministic raw-data filtering route."],
            ["raw_chauvenet", "Raw-value export with Chauvenet outlier filtering.", "Checks sensitivity to probabilistic outlier rejection."],
            ["raw_three_sigma", "Raw-value export with 3-sigma outlier filtering.", "Checks sensitivity to sigma-based outlier rejection."],
            ["Forward/backward paired summary", "Row/column-matched comparison between forward and backward scans.", "Checks directional consistency and supports forward-only selection in the topo Stage 1 workflow."],
        ],
    )
    _add_heading_paragraph(doc, "Calculation definitions used in the modulus comparison study")
    doc.add_paragraph(
        "For each scan, the comparison script reads the reported modulus summary from each method and compares it to the "
        "baseline Gwyddion-statistics route. The per-scan quantities used in this report are:"
    )
    doc.add_paragraph("avg_value: mean modulus reported by the comparison method for a scan.")
    doc.add_paragraph("std_value: standard deviation of modulus reported by the comparison method for a scan.")
    doc.add_paragraph("n_valid: number of valid pixels retained for that scan.")
    doc.add_paragraph("avg_baseline: mean modulus from the baseline route for the same scan.")
    doc.add_paragraph("std_baseline: standard deviation from the baseline route for the same scan.")
    doc.add_paragraph("n_valid_baseline: valid-pixel count from the baseline route for the same scan.")
    doc.add_paragraph("delta_avg = avg_value - avg_baseline")
    doc.add_paragraph("delta_std = std_value - std_baseline")
    doc.add_paragraph("delta_n_valid = n_valid - n_valid_baseline")
    doc.add_paragraph(
        "For the paired forward/backward comparison, scans are matched by grid row/column index and the paired quantities are:"
    )
    doc.add_paragraph("delta_avg(F/B) = avg_backward - avg_forward")
    doc.add_paragraph("ratio_avg(F/B) = avg_backward / avg_forward")
    doc.add_paragraph(
        "A ratio near 1.0 indicates close directional agreement. A delta near 0 indicates close agreement with the "
        "baseline route or, in the paired case, close agreement between scan directions."
    )
    doc.add_paragraph(
        "In the grouped bar plots, each bar summarizes a method-level modulus comparison against the baseline route. In the "
        "heatmaps, the baseline heatmap shows the spatial distribution of the baseline modulus summaries, while the "
        "delta-versus-baseline heatmaps show how a comparison route shifts the spatial pattern relative to that same baseline."
    )
    doc.add_paragraph(
        "A visually quiet or nearly blank delta heatmap does not necessarily indicate missing data. In several cases, "
        "particularly for the raw min/max route, the comparison values remain very close to the baseline or to the "
        "Gwyddion-preprocess/Python-stats route, so the spatial delta field compresses toward zero."
    )

    _add_table(
        doc,
        "Table M1 - Baseline dataset context",
        ["Dataset", "Baseline method", "Scans", "Units", "Compare directory"],
        [
            ["Forward modulus baseline", "modulus_gwy_stats", str(n_forward), units_forward, str(forward_compare_dir)],
            ["Backward modulus baseline", "modulus_gwy_stats", str(n_backward), units_backward, str(backward_compare_dir)],
            ["Paired forward/backward summary", "paired row/col matches", str(len(paired_rows)), "", str(paired_dir)],
        ],
    )
    _add_table(
        doc,
        "Table M1a - Baseline file/source inventory",
        ["Direction", "Scan count", "Example source file", "Baseline summary path"],
        [
            [
                "Forward",
                str(n_forward),
                (forward_baseline_rows[0]["source_file"] if forward_baseline_rows else ""),
                str(forward_baseline_summary),
            ],
            [
                "Backward",
                str(n_backward),
                (backward_baseline_rows[0]["source_file"] if backward_baseline_rows else ""),
                str(backward_baseline_summary),
            ],
        ],
    )

    method_order = ["gwy_ops_py_stats", "raw_minmax", "raw_chauvenet", "raw_three_sigma"]
    method_labels = {
        "gwy_ops_py_stats": "Gwyddion preprocess + Python stats",
        "raw_minmax": "Raw export + min/max filter",
        "raw_chauvenet": "Raw export + Chauvenet",
        "raw_three_sigma": "Raw export + 3-sigma",
        "gwy_stats": "Forward/backward paired baseline",
    }

    _add_table(
        doc,
        "Table M2 - Forward method comparison summary",
        ["Method", "Scans", "Mean ratio vs baseline", "Median ratio vs baseline", "Mean delta avg", "Mean delta n_valid"],
        [
            [
                method_labels.get(m, m),
                str(int(forward_agg[m]["n_scans"])),
                _fmt_ratio(forward_agg[m]["mean_ratio_avg"]),
                _fmt_ratio(forward_agg[m]["median_ratio_avg"]),
                _fmt_num(forward_agg[m]["mean_delta_avg"]),
                _fmt_num(forward_agg[m]["mean_delta_n"]),
            ]
            for m in method_order
            if m in forward_agg
        ],
    )

    _add_table(
        doc,
        "Table M3 - Backward method comparison summary",
        ["Method", "Scans", "Mean ratio vs baseline", "Median ratio vs baseline", "Mean delta avg", "Mean delta n_valid"],
        [
            [
                method_labels.get(m, m),
                str(int(backward_agg[m]["n_scans"])),
                _fmt_ratio(backward_agg[m]["mean_ratio_avg"]),
                _fmt_ratio(backward_agg[m]["median_ratio_avg"]),
                _fmt_num(backward_agg[m]["mean_delta_avg"]),
                _fmt_num(backward_agg[m]["mean_delta_n"]),
            ]
            for m in method_order
            if m in backward_agg
        ],
    )

    _add_table(
        doc,
        "Table M4 - Paired forward/backward method agreement summary",
        ["Method", "Pairs", "Mean ratio (F/B)", "Median ratio (F/B)", "Mean delta avg (F-B)", "Mean delta n_valid (F-B)"],
        [
            [
                method_labels.get(r["method"], r["method"]),
                str(_i(r.get("n_pairs"))),
                _fmt_ratio(_f(r.get("mean_ratio_avg"))),
                _fmt_ratio(_f(r.get("median_ratio_avg"))),
                _fmt_num(_f(r.get("mean_delta_avg"))),
                _fmt_num(_f(r.get("mean_delta_n_valid"))),
            ]
            for r in paired_rows
        ],
    )
    _add_table(
        doc,
        "Table M5 - Default processing parameters shared across modulus comparison methods",
        ["Parameter", "Default value", "Meaning"],
        [
            ["Metric", "Modulus", "Per-scan modulus summary from AFM modulus TIFFs."],
            ["Units", "kPa", "Normalized modulus unit used for comparison outputs."],
            ["Scan size", "5 um x 5 um", "Per-scan image size."],
            ["Pixel grid", "512 x 512", "Nominal pixel resolution of each scan."],
            ["Baseline route", "modulus_gwy_stats / gwy_stats", "Gwyddion preprocessing + Gwyddion statistics."],
            ["Row/col metadata", "Parsed from filename", "Grid-position matching for paired and heatmap comparisons."],
        ],
    )
    _add_table(
        doc,
        "Table M6 - Method variation table",
        ["Method", "What changes relative to baseline", "n_valid effect", "Interpretation role"],
        [
            ["gwy_ops_py_stats", "Statistics engine changes from Gwyddion to Python after Gwyddion preprocessing.", "Usually no n_valid change.", "Separates preprocessing effects from stats-engine effects."],
            ["raw_minmax", "Uses raw export plus deterministic min/max validity window.", "Usually no or minimal n_valid change.", "Checks whether a simple raw-data validity rule reproduces baseline behavior."],
            ["raw_chauvenet", "Uses raw export plus Chauvenet outlier filtering.", "Moderate n_valid reduction where outliers exist.", "Tests sensitivity to probabilistic outlier rejection."],
            ["raw_three_sigma", "Uses raw export plus 3-sigma outlier filtering.", "Larger n_valid reduction where outliers exist.", "Tests sensitivity to sigma-based outlier rejection."],
            ["Forward/backward paired summary", "Compares matched scans by direction.", "Not a filtering route.", "Checks directional consistency for method selection."],
        ],
    )

    doc.add_paragraph(
        "Interpretive note: the paired forward/backward table is the most direct basis for the forward-only selection used "
        "in the Stage 1 topography workflow. Values with median ratio near 1.0 indicate close directional agreement when "
        "matching scans by grid position."
    )

    labels = [method_labels[m] for m in method_order]
    forward_delta_series = [[_f(r["delta_avg"]) for r in forward_long if r["method"] == m and _f(r["delta_avg"]) == _f(r["delta_avg"])] for m in method_order]
    backward_delta_series = [[_f(r["delta_avg"]) for r in backward_long if r["method"] == m and _f(r["delta_avg"]) == _f(r["delta_avg"])] for m in method_order]
    paired_ratio_series = [
        [_f(r["ratio_avg"]) for r in paired_long if r["method"] == m and _f(r["ratio_avg"]) == _f(r["ratio_avg"])]
        for m in method_order
        if any(pr["method"] == m for pr in paired_long)
    ]
    paired_ratio_labels = [method_labels[m] for m in method_order if any(pr["method"] == m for pr in paired_long)]

    forward_box = asset_dir / "forward_delta_avg_boxplot.png"
    backward_box = asset_dir / "backward_delta_avg_boxplot.png"
    paired_box = asset_dir / "paired_ratio_boxplot.png"
    _plot_boxplot(forward_box, "Forward modulus comparison: delta avg vs baseline", labels, forward_delta_series, "Delta avg (kPa)")
    _plot_boxplot(backward_box, "Backward modulus comparison: delta avg vs baseline", labels, backward_delta_series, "Delta avg (kPa)")
    _plot_boxplot(paired_box, "Paired forward/backward ratio by method", paired_ratio_labels, paired_ratio_series, "Mean ratio (F/B)")

    _add_figure(
        doc,
        "Figure M1 - Paired forward/backward modulus summary.",
        paired_dir / "plots" / "fwd_bwd_summary.png",
    )
    _add_figure(
        doc,
        "Figure M2 - Forward modulus method comparison (grouped bar plot).",
        forward_compare_dir / "plots" / "avg_grouped_bar.png",
    )
    _add_figure(
        doc,
        "Figure M3 - Backward modulus method comparison (grouped bar plot).",
        backward_compare_dir / "plots" / "avg_grouped_bar.png",
    )
    _add_figure(
        doc,
        "Figure M3a - Forward modulus box plot of delta avg vs baseline by method.",
        forward_box,
    )
    _add_figure(
        doc,
        "Figure M3b - Backward modulus box plot of delta avg vs baseline by method.",
        backward_box,
    )
    _add_figure(
        doc,
        "Figure M3c - Paired forward/backward ratio box plot by method.",
        paired_box,
    )
    _add_figure(
        doc,
        "Figure M4 - Forward baseline modulus heatmap.",
        forward_compare_dir / "plots" / "heatmap_two_panel__baseline.png",
    )
    _add_figure(
        doc,
        "Figure M5 - Backward baseline modulus heatmap.",
        backward_compare_dir / "plots" / "heatmap_two_panel__baseline.png",
    )

    _add_heading_paragraph(doc, "Forward delta-versus-baseline heatmaps")
    for method in ["gwy_ops_py_stats", "raw_minmax", "raw_chauvenet", "raw_three_sigma"]:
        _add_figure(
            doc,
            f"Forward delta heatmap - {method_labels.get(method, method)}.",
            forward_compare_dir / "plots" / f"heatmap_two_panel__delta_vs_baseline__{method}.png",
        )

    _add_heading_paragraph(doc, "Backward delta-versus-baseline heatmaps")
    for method in ["gwy_ops_py_stats", "raw_minmax", "raw_chauvenet", "raw_three_sigma"]:
        _add_figure(
            doc,
            f"Backward delta heatmap - {method_labels.get(method, method)}.",
            backward_compare_dir / "plots" / f"heatmap_two_panel__delta_vs_baseline__{method}.png",
        )

    doc.add_paragraph(
        "Use in Chapter 6: this report supports the baseline PEGDA validation section by showing that the modulus workflow "
        "was internally consistent across route variants and that forward/backward directional differences were small enough "
        "to justify restricting the present Stage 1 topography workflow to forward scans."
    )
    _add_heading_paragraph(doc, "Scope and next-step note")
    doc.add_paragraph(
        "This modulus baseline comparison was performed on a single PEGDA sample and one fracture-surface side. It is "
        "therefore a method-validation artifact rather than a full population-level modulus study. A more complete "
        "directional and route-consistency study should be repeated across additional grouped samples, separated by side, "
        "before broad generalization. The same comparison framework should later be extended to composite PEGDA-SiNP "
        "systems and Li-containing systems so that method consistency can be evaluated under the full set of material "
        "conditions used in the thesis."
    )

    output_docx.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_docx)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a compact modulus baseline validation report.")
    ap.add_argument(
        "--forward-compare-dir",
        default="out/method_compare/compare_20260223_173256",
    )
    ap.add_argument(
        "--backward-compare-dir",
        default="out/method_compare/compare_20260223_173335",
    )
    ap.add_argument(
        "--paired-dir",
        default="out/method_compare/fwd_bwd_20260223_173826",
    )
    ap.add_argument(
        "--forward-baseline-summary",
        default="out/method_compare/compare_inputs_20260223_173037/forward/gwy_stats/summary.csv",
    )
    ap.add_argument(
        "--backward-baseline-summary",
        default="out/method_compare/compare_inputs_20260223_173037/backward/gwy_stats/summary.csv",
    )
    ap.add_argument(
        "--output-docx",
        default=r"C:\Users\Conor O'Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT\Modulus_Baseline_Validation_Report_20260306.docx",
    )
    args = ap.parse_args()
    build_report(
        forward_compare_dir=Path(args.forward_compare_dir),
        backward_compare_dir=Path(args.backward_compare_dir),
        paired_dir=Path(args.paired_dir),
        forward_baseline_summary=Path(args.forward_baseline_summary),
        backward_baseline_summary=Path(args.backward_baseline_summary),
        output_docx=Path(args.output_docx),
    )


if __name__ == "__main__":
    main()
