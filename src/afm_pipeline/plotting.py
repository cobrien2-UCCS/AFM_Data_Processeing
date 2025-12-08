"""
Plotting functions per spec.

Dispatches plotting_mode -> recipe using cfg["plotting_modes"].
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt

from .summarize import load_csv_table, build_result_object_from_csv_row

log = logging.getLogger(__name__)


def plot_summary_from_csv(csv_path: str, plotting_mode: str, cfg: Dict[str, Any], output_dir: str):
    """Entry: load CSV, cast rows via result_schema, dispatch plotting recipe."""
    plotting_def = cfg.get("plotting_modes", {}).get(plotting_mode)
    if not plotting_def:
        raise ValueError(f"Unknown plotting_mode: {plotting_mode}")
    schema_name = plotting_def.get("result_schema")
    if not schema_name:
        raise ValueError(f"plotting_mode {plotting_mode} missing result_schema")

    rows = load_csv_table(csv_path)
    typed_rows = [build_result_object_from_csv_row(r, schema_name, cfg) for r in rows]
    APPLY_PLOTTING_MODE(typed_rows, plotting_mode, cfg, output_dir)


def APPLY_PLOTTING_MODE(data_rows: List[Dict[str, Any]], plotting_mode: str, cfg: Dict[str, Any], output_dir: str):
    """Dispatcher for plotting modes."""
    plotting_def = cfg.get("plotting_modes", {}).get(plotting_mode, {})
    recipe = plotting_def.get("recipe") or plotting_def.get("type") or plotting_mode
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if recipe == "sample_bar_with_error":
        plot_sample_bar_with_error(data_rows, plotting_def, out_dir, plotting_mode)
    elif recipe == "histogram_avg":
        plot_histogram_avg(data_rows, plotting_def, out_dir, plotting_mode)
    elif recipe == "scatter_avg_vs_std":
        plot_scatter_avg_vs_std(data_rows, plotting_def, out_dir, plotting_mode)
    elif recipe == "mode_comparison_bar":
        plot_mode_comparison_bar(data_rows, plotting_def, out_dir, plotting_mode)
    elif recipe == "heatmap_grid":
        plot_heatmap_grid(data_rows, plotting_def, out_dir, plotting_mode)
    else:
        raise ValueError(f"Unknown plotting recipe '{recipe}' for plotting_mode '{plotting_mode}'")


def plot_sample_bar_with_error(rows: List[Dict[str, Any]], plotting_def: Dict[str, Any], out_dir: Path, name: str):
    labels = [r.get("source_file", "") for r in rows]
    means = [r.get("avg_value", 0.0) for r in rows]
    stds = [r.get("std_value", 0.0) for r in rows]

    fig, ax = plt.subplots()
    ax.bar(range(len(labels)), means, yerr=stds, capsize=4)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel(plotting_def.get("ylabel", "avg_value"))
    ax.set_title(plotting_def.get("title", name))
    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.png", dpi=300)
    plt.close(fig)


def plot_histogram_avg(rows: List[Dict[str, Any]], plotting_def: Dict[str, Any], out_dir: Path, name: str):
    values = [r.get("avg_value", 0.0) for r in rows if r.get("avg_value") is not None]
    bins = plotting_def.get("bins", 20)

    fig, ax = plt.subplots()
    ax.hist(values, bins=bins, density=plotting_def.get("density", False))
    ax.set_xlabel(plotting_def.get("xlabel", "avg_value"))
    ax.set_ylabel(plotting_def.get("ylabel", "count"))
    ax.set_title(plotting_def.get("title", name))
    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.png", dpi=300)
    plt.close(fig)


def plot_scatter_avg_vs_std(rows: List[Dict[str, Any]], plotting_def: Dict[str, Any], out_dir: Path, name: str):
    xs = [r.get("avg_value", 0.0) for r in rows]
    ys = [r.get("std_value", 0.0) for r in rows]

    fig, ax = plt.subplots()
    ax.scatter(xs, ys, s=plotting_def.get("point_size", 30), alpha=plotting_def.get("alpha", 0.7))
    ax.set_xlabel(plotting_def.get("xlabel", "avg_value"))
    ax.set_ylabel(plotting_def.get("ylabel", "std_value"))
    ax.set_title(plotting_def.get("title", name))
    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.png", dpi=300)
    plt.close(fig)


def plot_mode_comparison_bar(rows: List[Dict[str, Any]], plotting_def: Dict[str, Any], out_dir: Path, name: str):
    labels = [r.get("source_file", "") for r in rows]
    modes = [r.get("mode", "") for r in rows]
    means = [r.get("avg_value", 0.0) for r in rows]
    annotated = [f"{m}:{l}" if m else l for m, l in zip(modes, labels)]

    fig, ax = plt.subplots()
    ax.bar(range(len(annotated)), means)
    ax.set_xticks(range(len(annotated)))
    ax.set_xticklabels(annotated, rotation=45, ha="right")
    ax.set_ylabel(plotting_def.get("ylabel", "avg_value"))
    ax.set_title(plotting_def.get("title", name))
    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.png", dpi=300)
    plt.close(fig)


def plot_heatmap_grid(rows: List[Dict[str, Any]], plotting_def: Dict[str, Any], out_dir: Path, name: str):
    if not rows:
        log.warning("No data rows for heatmap: %s", name)
        return

    max_row = max(int(r.get("row_idx", 0)) for r in rows)
    max_col = max(int(r.get("col_idx", 0)) for r in rows)
    grid = [[float("nan")] * (max_col + 1) for _ in range(max_row + 1)]

    for r in rows:
        ri = int(r.get("row_idx", 0))
        ci = int(r.get("col_idx", 0))
        grid[ri][ci] = r.get("avg_value", float("nan"))

    fig, ax = plt.subplots()
    im = ax.imshow(grid, origin="lower")
    fig.colorbar(im, ax=ax, label=plotting_def.get("colorbar_label", "avg_value"))
    ax.set_xlabel("col_idx")
    ax.set_ylabel("row_idx")
    ax.set_title(plotting_def.get("title", name))
    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.png", dpi=300)
    plt.close(fig)
