#!/usr/bin/env python3
"""
Compare multiple processing methods by merging their summary.csv outputs.

Outputs:
- comparison_wide.csv: one row per source_file with baseline + method columns
- comparison_long.csv: one row per (source_file, method)
- plots/*.png: quick visuals (bars, scatter, heatmaps if grid indices exist)

This script is intentionally lightweight (stdlib + numpy + matplotlib) so it can
run in the repo environment without extra dependencies.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt


def _isfinite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        v = float(s)
    except Exception:
        return None
    if not math.isfinite(v):
        return None
    return v


def _to_int(x: Any) -> Optional[int]:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def _truncate(text: str, max_len: int) -> str:
    if max_len <= 0 or len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    head = (max_len - 3) // 2
    tail = max_len - 3 - head
    return text[:head] + "..." + text[-tail:]


@dataclass(frozen=True)
class SummaryRow:
    source_file: str
    row_idx: Optional[int]
    col_idx: Optional[int]
    avg_value: Optional[float]
    std_value: Optional[float]
    n_valid: Optional[int]
    units: str
    mode: str
    metric_type: str
    nx: Optional[int]
    ny: Optional[int]


def load_summary_csv(path: Path) -> List[SummaryRow]:
    rows: List[SummaryRow] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            source_file = (r.get("source_file") or "").strip()
            if not source_file:
                continue
            rows.append(
                SummaryRow(
                    source_file=source_file,
                    row_idx=_to_int(r.get("row_idx")),
                    col_idx=_to_int(r.get("col_idx")),
                    avg_value=_to_float(r.get("avg_value")),
                    std_value=_to_float(r.get("std_value")),
                    n_valid=_to_int(r.get("n_valid")),
                    units=str(r.get("units") or "").strip(),
                    mode=str(r.get("mode") or "").strip(),
                    metric_type=str(r.get("metric_type") or "").strip(),
                    nx=_to_int(r.get("nx")),
                    ny=_to_int(r.get("ny")),
                )
            )
    return rows


def discover_method_summaries(methods_root: Path) -> Dict[str, Path]:
    """
    Find summary.csv files under methods_root.

    Expected layout (current pipeline):
      <methods_root>/<method_name>/config.<config_stem>/summary.csv
    """
    found: Dict[str, Path] = {}
    for summary in methods_root.rglob("summary.csv"):
        try:
            method_name = summary.parents[1].name  # <method>/config.<...>/summary.csv
        except Exception:
            continue
        if method_name not in found:
            found[method_name] = summary
    return found


def write_csv(path: Path, fieldnames: List[str], rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def build_grid(rows: List[SummaryRow], value_field: str) -> Tuple[np.ndarray, int, int]:
    valid = [r for r in rows if r.row_idx is not None and r.col_idx is not None]
    if not valid:
        return np.zeros((0, 0), dtype=float), 0, 0
    max_r = max(int(r.row_idx) for r in valid)
    max_c = max(int(r.col_idx) for r in valid)
    grid = np.full((max_r + 1, max_c + 1), np.nan, dtype=float)

    # If duplicates exist, average them.
    acc: Dict[Tuple[int, int], List[float]] = {}
    for r in valid:
        v = getattr(r, value_field)
        if v is None:
            continue
        key = (int(r.row_idx), int(r.col_idx))
        acc.setdefault(key, []).append(float(v))
    for (ri, ci), vals in acc.items():
        grid[ri, ci] = float(np.mean(vals)) if vals else np.nan
    return grid, max_r + 1, max_c + 1


def plot_grouped_bar(
    out_path: Path,
    title: str,
    xlabels: List[str],
    series: List[Tuple[str, List[Optional[float]]]],
    yerr: Optional[List[Tuple[str, List[Optional[float]]]]] = None,
    ylabel: str = "",
    max_label_len: int = 40,
):
    labels = [_truncate(x, max_label_len) for x in xlabels]
    n = len(labels)
    m = len(series)
    if n == 0 or m == 0:
        return

    x = np.arange(n, dtype=float)
    width = 0.8 / float(max(m, 1))

    fig_w = max(10.0, 1.4 * n)
    fig, ax = plt.subplots(figsize=(fig_w, 5.0))

    for i, (name, vals) in enumerate(series):
        ys = np.array([v if v is not None else np.nan for v in vals], dtype=float)
        xs = x - 0.4 + width / 2.0 + i * width
        if yerr is not None:
            err_map = {nm: e for nm, e in yerr}
            es = np.array([err_map.get(name, [None] * n)[j] for j in range(n)], dtype=float)
            es = np.where(np.isfinite(es), es, 0.0)
            ax.bar(xs, ys, width, label=name, yerr=es, capsize=3)
        else:
            ax.bar(xs, ys, width, label=name)

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_scatter_vs_baseline(
    out_path: Path,
    title: str,
    baseline_vals: List[Optional[float]],
    method_vals: List[Optional[float]],
    xlabel: str,
    ylabel: str,
):
    xs = np.array([v if v is not None else np.nan for v in baseline_vals], dtype=float)
    ys = np.array([v if v is not None else np.nan for v in method_vals], dtype=float)
    mask = np.isfinite(xs) & np.isfinite(ys)
    if not mask.any():
        return

    fig, ax = plt.subplots(figsize=(5.5, 5.0))
    ax.scatter(xs[mask], ys[mask], s=30, alpha=0.75)

    lo = float(np.nanmin(np.concatenate([xs[mask], ys[mask]])))
    hi = float(np.nanmax(np.concatenate([xs[mask], ys[mask]])))
    if math.isfinite(lo) and math.isfinite(hi) and lo != hi:
        ax.plot([lo, hi], [lo, hi], linestyle="--", linewidth=1.0, color="black", alpha=0.6)

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_two_panel_heatmap(
    out_path: Path,
    title: str,
    left: np.ndarray,
    right: np.ndarray,
    left_label: str,
    right_label: str,
    cmap_left: str = "viridis",
    cmap_right: str = "magma",
):
    if left.size == 0 or right.size == 0:
        return
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.5), constrained_layout=True)

    im0 = axes[0].imshow(left, origin="lower", aspect="auto", cmap=cmap_left)
    axes[0].set_title(left_label)
    plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(right, origin="lower", aspect="auto", cmap=cmap_right)
    axes[1].set_title(right_label)
    plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    fig.suptitle(title)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare method summary.csv outputs against a baseline.")
    ap.add_argument("--baseline-summary", required=True, help="Path to baseline summary.csv.")
    ap.add_argument("--methods-root", required=True, help="Root folder containing method subfolders with summary.csv.")
    ap.add_argument("--out-root", default="out/method_compare", help="Where to write comparison outputs.")
    ap.add_argument("--label-max-len", type=int, default=40, help="Max label length for bar plots.")
    args = ap.parse_args()

    baseline_path = Path(args.baseline_summary)
    methods_root = Path(args.methods_root)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_root) / f"compare_{stamp}"
    plots_dir = out_dir / "plots"

    baseline_rows = load_summary_csv(baseline_path)
    methods = discover_method_summaries(methods_root)
    if not methods:
        raise SystemExit(f"No summary.csv files found under {methods_root}")

    # Keep deterministic ordering: baseline first, then other methods alphabetically.
    method_names = sorted(methods.keys())

    method_rows: Dict[str, List[SummaryRow]] = {name: load_summary_csv(methods[name]) for name in method_names}

    # Merge keys.
    keys: List[str] = sorted({r.source_file for r in baseline_rows} | {r.source_file for ms in method_rows.values() for r in ms})

    baseline_by_key = {r.source_file: r for r in baseline_rows}
    method_by_key: Dict[str, Dict[str, SummaryRow]] = {mn: {r.source_file: r for r in rs} for mn, rs in method_rows.items()}

    # Wide rows for Excel.
    wide_rows: List[Dict[str, Any]] = []
    long_rows: List[Dict[str, Any]] = []

    for k in keys:
        b = baseline_by_key.get(k)
        row_idx = b.row_idx if b else None
        col_idx = b.col_idx if b else None
        units_b = b.units if b else ""
        avg_b = b.avg_value if b else None
        std_b = b.std_value if b else None
        n_b = b.n_valid if b else None

        out: Dict[str, Any] = {
            "source_file": k,
            "row_idx": row_idx if row_idx is not None else "",
            "col_idx": col_idx if col_idx is not None else "",
            "baseline_method": "gwyddion_only",
            "avg__baseline": avg_b if avg_b is not None else "",
            "std__baseline": std_b if std_b is not None else "",
            "n_valid__baseline": n_b if n_b is not None else "",
            "units__baseline": units_b,
        }

        for mn in method_names:
            mr = method_by_key[mn].get(k)
            avg_m = mr.avg_value if mr else None
            std_m = mr.std_value if mr else None
            n_m = mr.n_valid if mr else None
            units_m = mr.units if mr else ""

            out[f"avg__{mn}"] = avg_m if avg_m is not None else ""
            out[f"std__{mn}"] = std_m if std_m is not None else ""
            out[f"n_valid__{mn}"] = n_m if n_m is not None else ""
            out[f"units__{mn}"] = units_m

            # Deltas vs baseline when available.
            if avg_b is not None and avg_m is not None:
                out[f"delta_avg__{mn}"] = avg_m - avg_b
                out[f"ratio_avg__{mn}"] = (avg_m / avg_b) if avg_b != 0 else ""
            else:
                out[f"delta_avg__{mn}"] = ""
                out[f"ratio_avg__{mn}"] = ""

            if std_b is not None and std_m is not None:
                out[f"delta_std__{mn}"] = std_m - std_b
                out[f"ratio_std__{mn}"] = (std_m / std_b) if std_b != 0 else ""
            else:
                out[f"delta_std__{mn}"] = ""
                out[f"ratio_std__{mn}"] = ""

            if n_b is not None and n_m is not None:
                out[f"delta_n_valid__{mn}"] = int(n_m) - int(n_b)
                out[f"ratio_n_valid__{mn}"] = (float(n_m) / float(n_b)) if n_b != 0 else ""
            else:
                out[f"delta_n_valid__{mn}"] = ""
                out[f"ratio_n_valid__{mn}"] = ""

            long_rows.append(
                {
                    "source_file": k,
                    "method": mn,
                    "avg_value": avg_m if avg_m is not None else "",
                    "std_value": std_m if std_m is not None else "",
                    "n_valid": n_m if n_m is not None else "",
                    "units": units_m,
                    "avg_baseline": avg_b if avg_b is not None else "",
                    "std_baseline": std_b if std_b is not None else "",
                    "n_valid_baseline": n_b if n_b is not None else "",
                    "delta_avg": (avg_m - avg_b) if (avg_b is not None and avg_m is not None) else "",
                    "delta_std": (std_m - std_b) if (std_b is not None and std_m is not None) else "",
                    "delta_n_valid": (int(n_m) - int(n_b)) if (n_b is not None and n_m is not None) else "",
                }
            )

        wide_rows.append(out)

    # Decide field order (baseline columns then per-method blocks).
    fields = [
        "source_file",
        "row_idx",
        "col_idx",
        "baseline_method",
        "avg__baseline",
        "std__baseline",
        "n_valid__baseline",
        "units__baseline",
    ]
    for mn in method_names:
        fields.extend(
            [
                f"avg__{mn}",
                f"std__{mn}",
                f"n_valid__{mn}",
                f"units__{mn}",
                f"delta_avg__{mn}",
                f"ratio_avg__{mn}",
                f"delta_std__{mn}",
                f"ratio_std__{mn}",
                f"delta_n_valid__{mn}",
                f"ratio_n_valid__{mn}",
            ]
        )

    write_csv(out_dir / "comparison_wide.csv", fields, wide_rows)
    write_csv(
        out_dir / "comparison_long.csv",
        [
            "source_file",
            "method",
            "avg_value",
            "std_value",
            "n_valid",
            "units",
            "avg_baseline",
            "std_baseline",
            "n_valid_baseline",
            "delta_avg",
            "delta_std",
            "delta_n_valid",
        ],
        long_rows,
    )

    # Plots: grouped mean+std bars.
    xlabels = keys
    baseline_avg = [baseline_by_key.get(k).avg_value if baseline_by_key.get(k) else None for k in keys]
    baseline_std = [baseline_by_key.get(k).std_value if baseline_by_key.get(k) else None for k in keys]
    series_avg: List[Tuple[str, List[Optional[float]]]] = [("baseline", baseline_avg)]
    series_std: List[Tuple[str, List[Optional[float]]]] = [("baseline", baseline_std)]
    for mn in method_names:
        series_avg.append((mn, [method_by_key[mn].get(k).avg_value if method_by_key[mn].get(k) else None for k in keys]))
        series_std.append((mn, [method_by_key[mn].get(k).std_value if method_by_key[mn].get(k) else None for k in keys]))

    plot_grouped_bar(
        plots_dir / "avg_grouped_bar.png",
        title="avg_value by method (error bars = std_value)",
        xlabels=xlabels,
        series=series_avg,
        yerr=series_std,
        ylabel="avg_value",
        max_label_len=int(args.label_max_len),
    )

    # n_valid bars
    series_n: List[Tuple[str, List[Optional[float]]]] = [
        ("baseline", [float(baseline_by_key.get(k).n_valid) if (baseline_by_key.get(k) and baseline_by_key.get(k).n_valid is not None) else None for k in keys])
    ]
    for mn in method_names:
        series_n.append((mn, [float(method_by_key[mn].get(k).n_valid) if (method_by_key[mn].get(k) and method_by_key[mn].get(k).n_valid is not None) else None for k in keys]))
    plot_grouped_bar(
        plots_dir / "n_valid_grouped_bar.png",
        title="n_valid by method",
        xlabels=xlabels,
        series=series_n,
        yerr=None,
        ylabel="n_valid",
        max_label_len=int(args.label_max_len),
    )

    # Scatter vs baseline for each method.
    for mn in method_names:
        method_avg = [method_by_key[mn].get(k).avg_value if method_by_key[mn].get(k) else None for k in keys]
        plot_scatter_vs_baseline(
            plots_dir / f"scatter_avg_vs_baseline__{mn}.png",
            title=f"avg_value: {mn} vs baseline",
            baseline_vals=baseline_avg,
            method_vals=method_avg,
            xlabel="baseline avg_value",
            ylabel=f"{mn} avg_value",
        )

    # Heatmaps if indices exist.
    if any(r.row_idx is not None and r.col_idx is not None for r in baseline_rows):
        b_avg_grid, _, _ = build_grid(baseline_rows, "avg_value")
        b_std_grid, _, _ = build_grid(baseline_rows, "std_value")
        plot_two_panel_heatmap(
            plots_dir / "heatmap_two_panel__baseline.png",
            title="baseline (gwyddion_only)",
            left=b_avg_grid,
            right=b_std_grid,
            left_label="avg_value",
            right_label="std_value",
        )
        for mn in method_names:
            rs = method_rows[mn]
            m_avg_grid, _, _ = build_grid(rs, "avg_value")
            m_std_grid, _, _ = build_grid(rs, "std_value")
            plot_two_panel_heatmap(
                plots_dir / f"heatmap_two_panel__{mn}.png",
                title=mn,
                left=m_avg_grid,
                right=m_std_grid,
                left_label="avg_value",
                right_label="std_value",
            )
            # Delta vs baseline.
            if m_avg_grid.shape == b_avg_grid.shape:
                d_avg = m_avg_grid - b_avg_grid
                d_std = m_std_grid - b_std_grid
                plot_two_panel_heatmap(
                    plots_dir / f"heatmap_two_panel__delta_vs_baseline__{mn}.png",
                    title=f"delta vs baseline: {mn} - baseline",
                    left=d_avg,
                    right=d_std,
                    left_label="delta avg_value",
                    right_label="delta std_value",
                    cmap_left="coolwarm",
                    cmap_right="coolwarm",
                )

    print(f"Wrote comparison CSVs to {out_dir}")
    print(f"Wrote plots to {plots_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

