"""
Plotting functions per spec.

Dispatches plotting_mode -> recipe using cfg["plotting_modes"].
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import EngFormatter, FuncFormatter, FormatStrFormatter, MaxNLocator

from .summarize import load_csv_table, build_result_object_from_csv_row

log = logging.getLogger(__name__)


def _infer_unit(rows: List[Dict[str, Any]]) -> str:
    """Best-effort unit inference from data rows."""
    for r in rows:
        if "units" in r and r["units"]:
            return str(r["units"])
        if "core.units" in r and r["core.units"]:
            return str(r["core.units"])
    return ""


def _infer_metric_label(rows: List[Dict[str, Any]]) -> str:
    """Best-effort metric label inference from data rows."""
    for r in rows:
        if "metric_type" in r and r["metric_type"]:
            return str(r["metric_type"])
        if "core.metric_type" in r and r["core.metric_type"]:
            return str(r["core.metric_type"])
    return ""


def _format_text_with_units(text: Any, unit: str, metric_label: str) -> str:
    if text is None:
        return ""
    text = str(text)
    unit = unit or ""
    metric_label = metric_label or ""
    return text.replace("{units}", unit).replace("{unit}", unit).replace("{metric}", metric_label)


def _get_formatter(fmt: Any, places: Any):
    fmt = str(fmt or "").strip().lower()
    if not fmt:
        return None
    try:
        places = int(places) if places is not None else None
    except Exception:
        places = None
    if fmt in ("engineering", "eng"):
        return EngFormatter(places=places)
    if fmt in ("scientific", "sci"):
        if places is None:
            return FuncFormatter(lambda x, pos: f"{x:.3e}")
        return FuncFormatter(lambda x, pos: f"{x:.{places}e}")
    if fmt in ("plain", "fixed"):
        if places is None:
            return None
        return FormatStrFormatter(f"%.{places}f")
    return None


def _apply_axis_formatting(ax, plotting_def: Dict[str, Any], axis: str):
    fmt = plotting_def.get(f"{axis}axis_format") or plotting_def.get("axis_format")
    places = plotting_def.get(f"{axis}axis_places") or plotting_def.get("axis_places")
    formatter = _get_formatter(fmt, places)
    if formatter is None:
        return
    if axis == "x":
        ax.xaxis.set_major_formatter(formatter)
    else:
        ax.yaxis.set_major_formatter(formatter)


def _apply_integer_ticks(ax, plotting_def: Dict[str, Any]):
    x_int = plotting_def.get("xaxis_integer")
    y_int = plotting_def.get("yaxis_integer")
    if x_int is None:
        x_int = plotting_def.get("axis_integer")
    if y_int is None:
        y_int = plotting_def.get("axis_integer")
    if x_int:
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    if y_int:
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))


def _apply_colorbar_formatting(cbar, plotting_def: Dict[str, Any], prefix: str = ""):
    fmt = plotting_def.get(f"{prefix}colorbar_format") or plotting_def.get("colorbar_format")
    places = plotting_def.get(f"{prefix}colorbar_places") or plotting_def.get("colorbar_places")
    formatter = _get_formatter(fmt, places)
    if formatter is None:
        return
    cbar.formatter = formatter
    cbar.update_ticks()


def _resolve_center_value(spec: Any, values: List[float]):
    if spec is None:
        return None
    try:
        if isinstance(spec, (int, float)):
            return float(spec)
    except Exception:
        pass
    s = str(spec).strip().lower()
    if s in ("mean", "avg", "average"):
        return float(np.nanmean(values)) if values else None
    if s in ("median",):
        return float(np.nanmedian(values)) if values else None
    if s in ("zero", "0"):
        return 0.0
    try:
        return float(s)
    except Exception:
        return None


def _collect_range_values(csv_glob: Any, field: str, base_path: Path) -> List[float]:
    if not csv_glob:
        return []
    base_path = Path(base_path)
    values: List[float] = []
    try:
        paths = list(base_path.glob(str(csv_glob)))
    except Exception:
        paths = []
    for p in paths:
        try:
            rows = load_csv_table(str(p))
        except Exception:
            continue
        for r in rows:
            v = r.get(field)
            if v is None:
                continue
            try:
                f = float(v)
            except Exception:
                continue
            if f == f:
                values.append(f)
    return values


def _resolve_norm(norm_name: Any, grid: List[List[float]] | None, vmin: float | None, vmax: float | None,
                  linthresh: Any = None, linscale: Any = None, vcenter: float | None = None, label: str = ""):
    if not norm_name:
        return None, vmin, vmax
    norm_name = str(norm_name).strip().lower()
    vals = []
    if grid:
        for row in grid:
            for v in row:
                if v == v:
                    vals.append(v)
    if vmin is None and vals:
        vmin = min(vals)
    if vmax is None and vals:
        vmax = max(vals)
    if norm_name == "log":
        if vmin is None or vmax is None:
            return None, vmin, vmax
        if vmin <= 0:
            pos_vals = [v for v in vals if v > 0]
            if not pos_vals:
                log.warning("No positive values for log norm %s; skipping log.", label)
                return None, vmin, vmax
            vmin = min(pos_vals)
        return mcolors.LogNorm(vmin=vmin, vmax=vmax), vmin, vmax
    if norm_name == "symlog":
        if vmin is None or vmax is None:
            return None, vmin, vmax
        lt = float(linthresh) if linthresh is not None else 1.0
        ls = float(linscale) if linscale is not None else 1.0
        return mcolors.SymLogNorm(linthresh=lt, linscale=ls, vmin=vmin, vmax=vmax), vmin, vmax
    if norm_name == "centered":
        if vmin is None or vmax is None:
            return None, vmin, vmax
        if vcenter is None:
            vcenter = 0.0
        return mcolors.TwoSlopeNorm(vcenter=vcenter, vmin=vmin, vmax=vmax), vmin, vmax
    return None, vmin, vmax


def _truncate_text(text: str, max_len: int) -> str:
    if max_len is None:
        return text
    try:
        max_len = int(max_len)
    except Exception:
        return text
    if max_len <= 0 or len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    head = (max_len - 3) // 2
    tail = max_len - 3 - head
    if tail <= 0:
        return text[: max_len - 3] + "..."
    return text[:head] + "..." + text[-tail:]


def _format_label(label: Any, plotting_def: Dict[str, Any]) -> str:
    text = "" if label is None else str(label)
    if plotting_def.get("label_basename"):
        text = Path(text).name
        if plotting_def.get("label_strip_ext", True):
            text = Path(text).stem
    return _truncate_text(text, plotting_def.get("label_max_len"))


def _build_label(row: Dict[str, Any], plotting_def: Dict[str, Any]) -> str:
    mode = str(plotting_def.get("label_mode") or "").strip().lower()
    if mode in ("grid_rowcol", "gridrowcol"):
        gid = row.get("grid_id")
        ri = row.get("row_idx")
        ci = row.get("col_idx")
        parts = []
        if gid not in (None, ""):
            parts.append(str(gid))
        if ri not in (None, -1) and ci not in (None, -1):
            parts.append(f"r{ri}, c{ci}")
        label = " ".join(parts) if parts else row.get("source_file", "")
        return _truncate_text(str(label), plotting_def.get("label_max_len"))
    if mode in ("grid_id", "gridid"):
        gid = row.get("grid_id")
        if gid not in (None, ""):
            return _truncate_text(str(gid), plotting_def.get("label_max_len"))
    return _format_label(row.get("source_file", ""), plotting_def)


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
    APPLY_PLOTTING_MODE(typed_rows, plotting_mode, cfg, output_dir, csv_path=csv_path)


def APPLY_PLOTTING_MODE(data_rows: List[Dict[str, Any]], plotting_mode: str, cfg: Dict[str, Any], output_dir: str, csv_path: Optional[str] = None): # CAPS are generaly styled as contatns or gloabl varibles not funcitons. Overal the Dispacher is a good way to do this. 
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
        plot_heatmap_grid(data_rows, plotting_def, out_dir, plotting_mode, csv_path=csv_path)
    elif recipe in ("heatmap_grid_bubbles", "heatmap_grid_bubble_overlay"):
        plot_heatmap_grid_bubbles(data_rows, plotting_def, out_dir, plotting_mode)
    elif recipe in ("heatmap_two_panel", "heatmap_grid_two_panel"):
        plot_heatmap_two_panel(data_rows, plotting_def, out_dir, plotting_mode, csv_path=csv_path)
    else:
        raise ValueError(f"Unknown plotting recipe '{recipe}' for plotting_mode '{plotting_mode}'")


def _sigma_color(z: float, sigma_bins: List[float], colors: List[str]) -> str:
    if z is None or z != z:
        return colors[-1] if colors else "black"
    for idx, thr in enumerate(sigma_bins):
        if z <= thr:
            if idx < len(colors):
                return colors[idx]
            return colors[-1] if colors else "black"
    return colors[-1] if colors else "black"


def _sigma_legend_handles(sigma_bins: List[float], colors: List[str], marker: str = "o") -> List[Line2D]:
    handles: List[Line2D] = []
    if not sigma_bins or not colors:
        return handles
    for idx, thr in enumerate(sigma_bins):
        c = colors[idx] if idx < len(colors) else (colors[-1] if colors else "black")
        handles.append(Line2D([0], [0], marker=marker, linestyle="None", color=c, label=f"= {thr:g}s"))
    if len(colors) >= len(sigma_bins) + 1:
        handles.append(Line2D([0], [0], marker=marker, linestyle="None", color=colors[len(sigma_bins)], label=f"> {sigma_bins[-1]:g}s"))
    return handles


def _save_separate_legend(out_dir: Path, name: str, handles: List[Line2D], title: str, loc: str = "upper left"):
    """Save a standalone legend figure to <out_dir>/<name>_legend.png."""
    try:
        fig, ax = plt.subplots(figsize=(2.5, 2.5))
        ax.axis("off")
        ax.legend(handles=handles, title=title, loc=loc, fontsize=7, title_fontsize=8, framealpha=0.8)
        fig.savefig(out_dir / f"{name}_legend.png", dpi=300, bbox_inches="tight")
        plt.close(fig)
    except Exception:
        pass


def _extract_value(row: Dict[str, Any], field: str) -> float:
    """Pull a value from row, supporting a few derived fields."""
    try:
        if field == "cv_value":
            s = float(row.get("std_value", float("nan")))
            m = float(row.get("avg_value", float("nan")))
            if m == 0 or m != m:
                return float("nan")
            return s / m
        if field == "range_value":
            lo = row.get("core.min_value")
            hi = row.get("core.max_value")
            if lo is None or hi is None:
                return float("nan")
            return float(hi) - float(lo)
        return float(row.get(field, float("nan")))
    except Exception:
        return float("nan")


def plot_sample_bar_with_error(rows: List[Dict[str, Any]], plotting_def: Dict[str, Any], out_dir: Path, name: str):
    labels = [_build_label(r, plotting_def) for r in rows]
    means = [r.get("avg_value", 0.0) for r in rows]
    stds = [r.get("std_value", 0.0) for r in rows]
    unit = _infer_unit(rows)
    metric_label = _infer_metric_label(rows)
    label_mode = str(plotting_def.get("label_units_mode") or "auto").strip().lower()

    fig, ax = plt.subplots()
    ax.bar(range(len(labels)), means, yerr=stds, capsize=4)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ylabel = plotting_def.get("ylabel")
    if label_mode == "auto":
        ylabel = _format_text_with_units(ylabel, unit, metric_label) if ylabel else (f"avg_value ({unit})" if unit else "avg_value")
    else:
        ylabel = ylabel or (f"avg_value ({unit})" if unit else "avg_value")
    ax.set_ylabel(ylabel)
    xlabel = plotting_def.get("xlabel")
    if xlabel:
        ax.set_xlabel(_format_text_with_units(xlabel, unit, metric_label) if label_mode == "auto" else xlabel)
    title = plotting_def.get("title", name)
    if label_mode == "auto":
        title = _format_text_with_units(title, unit, metric_label) if title else name
    ax.set_title(title)
    _apply_axis_formatting(ax, plotting_def, "y")
    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.png", dpi=300)
    plt.close(fig)


def plot_histogram_avg(rows: List[Dict[str, Any]], plotting_def: Dict[str, Any], out_dir: Path, name: str):
    values = [r.get("avg_value", 0.0) for r in rows if r.get("avg_value") is not None]
    bins = plotting_def.get("bins", 20)
    unit = _infer_unit(rows)
    metric_label = _infer_metric_label(rows)
    label_mode = str(plotting_def.get("label_units_mode") or "auto").strip().lower()

    fig, ax = plt.subplots()
    ax.hist(values, bins=bins, density=plotting_def.get("density", False))
    xlabel = plotting_def.get("xlabel")
    if label_mode == "auto":
        xlabel = _format_text_with_units(xlabel, unit, metric_label) if xlabel else (f"avg_value ({unit})" if unit else "avg_value")
    else:
        xlabel = xlabel or (f"avg_value ({unit})" if unit else "avg_value")
    ax.set_xlabel(xlabel)
    ylabel = plotting_def.get("ylabel", "count")
    if label_mode == "auto":
        ylabel = _format_text_with_units(ylabel, unit, metric_label)
    ax.set_ylabel(ylabel)
    title = plotting_def.get("title", name)
    if label_mode == "auto":
        title = _format_text_with_units(title, unit, metric_label) if title else name
    ax.set_title(title)
    _apply_axis_formatting(ax, plotting_def, "x")
    _apply_axis_formatting(ax, plotting_def, "y")
    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.png", dpi=300)
    plt.close(fig)


def plot_scatter_avg_vs_std(rows: List[Dict[str, Any]], plotting_def: Dict[str, Any], out_dir: Path, name: str):
    xs = [r.get("avg_value", 0.0) for r in rows]
    ys = [r.get("std_value", 0.0) for r in rows]
    unit = _infer_unit(rows)
    metric_label = _infer_metric_label(rows)
    label_mode = str(plotting_def.get("label_units_mode") or "auto").strip().lower()

    fig, ax = plt.subplots()
    ax.scatter(xs, ys, s=plotting_def.get("point_size", 30), alpha=plotting_def.get("alpha", 0.7))
    xlabel = plotting_def.get("xlabel")
    ylabel = plotting_def.get("ylabel")
    if label_mode == "auto":
        xlabel = _format_text_with_units(xlabel, unit, metric_label) if xlabel else (f"avg_value ({unit})" if unit else "avg_value")
        ylabel = _format_text_with_units(ylabel, unit, metric_label) if ylabel else (f"std_value ({unit})" if unit else "std_value")
    else:
        xlabel = xlabel or (f"avg_value ({unit})" if unit else "avg_value")
        ylabel = ylabel or (f"std_value ({unit})" if unit else "std_value")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    title = plotting_def.get("title", name)
    if label_mode == "auto":
        title = _format_text_with_units(title, unit, metric_label) if title else name
    ax.set_title(title)
    _apply_axis_formatting(ax, plotting_def, "x")
    _apply_axis_formatting(ax, plotting_def, "y")
    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.png", dpi=300)
    plt.close(fig)


def plot_mode_comparison_bar(rows: List[Dict[str, Any]], plotting_def: Dict[str, Any], out_dir: Path, name: str):
    labels = [_build_label(r, plotting_def) for r in rows]
    modes = [r.get("mode", "") for r in rows]
    means = [r.get("avg_value", 0.0) for r in rows]
    annotated = [f"{m}:{l}" if m else l for m, l in zip(modes, labels)]
    annotated = [_truncate_text(a, plotting_def.get("label_max_len")) for a in annotated]
    unit = _infer_unit(rows)
    metric_label = _infer_metric_label(rows)
    label_mode = str(plotting_def.get("label_units_mode") or "auto").strip().lower()

    fig, ax = plt.subplots()
    ax.bar(range(len(annotated)), means)
    ax.set_xticks(range(len(annotated)))
    ax.set_xticklabels(annotated, rotation=45, ha="right")
    ylabel = plotting_def.get("ylabel")
    if label_mode == "auto":
        ylabel = _format_text_with_units(ylabel, unit, metric_label) if ylabel else (f"avg_value ({unit})" if unit else "avg_value")
    else:
        ylabel = ylabel or (f"avg_value ({unit})" if unit else "avg_value")
    ax.set_ylabel(ylabel)
    xlabel = plotting_def.get("xlabel")
    if xlabel:
        ax.set_xlabel(_format_text_with_units(xlabel, unit, metric_label) if label_mode == "auto" else xlabel)
    title = plotting_def.get("title", name)
    if label_mode == "auto":
        title = _format_text_with_units(title, unit, metric_label) if title else name
    ax.set_title(title)
    _apply_axis_formatting(ax, plotting_def, "y")
    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.png", dpi=300)
    plt.close(fig)


def plot_heatmap_grid(rows: List[Dict[str, Any]], plotting_def: Dict[str, Any], out_dir: Path, name: str, csv_path: Optional[str] = None):
    if not rows:
        log.warning("No data rows for heatmap: %s", name)
        return

    # Filter out missing grid indices (default -1) so they don't wrap (Python -1 index).
    valid_rows = []
    skipped = 0
    for r in rows:
        try:
            ri = int(r.get("row_idx", -1))
            ci = int(r.get("col_idx", -1))
        except Exception:
            skipped += 1
            continue
        if ri < 0 or ci < 0:
            skipped += 1
            continue
        valid_rows.append(r)

    if skipped:
        log.warning("Skipping %d rows without valid grid indices for heatmap '%s'.", skipped, name)

    if not valid_rows:
        log.warning("No valid grid-indexed rows for heatmap: %s", name)
        return

    max_row = max(int(r.get("row_idx", 0)) for r in valid_rows)
    max_col = max(int(r.get("col_idx", 0)) for r in valid_rows)
    grid = [[float("nan")] * (max_col + 1) for _ in range(max_row + 1)]

    duplicate_policy = plotting_def.get("duplicate_policy", "warn_mean")
    value_field = plotting_def.get("value_field", "avg_value")

    # Track grid_id consistency: same grid_id mapped to multiple row/col locations.
    grid_id_positions: Dict[str, set] = {}
    cell_values: Dict[tuple[int, int], List[float]] = {}
    for r in valid_rows:
        ri = int(r.get("row_idx", 0))
        ci = int(r.get("col_idx", 0))
        v = _extract_value(r, value_field)
        cell_values.setdefault((ri, ci), []).append(v)
        gid = str(r.get("grid_id")) if r.get("grid_id") not in (None, "") else None
        if gid:
            grid_id_positions.setdefault(gid, set()).add((ri, ci))

    gid_conflicts = {gid: pos for gid, pos in grid_id_positions.items() if len(pos) > 1}
    if gid_conflicts:
        log.warning("Grid_id mapped to multiple row/col locations: %s", gid_conflicts)

    duplicates = {k: v for k, v in cell_values.items() if len(v) > 1}
    if duplicates:
        msg = "Found %d duplicate grid cells for heatmap '%s'." % (len(duplicates), name)
        if duplicate_policy == "error":
            raise ValueError(msg + " Set plotting_modes.<mode>.duplicate_policy to control behavior.")
        log.warning("%s Using policy=%s.", msg, duplicate_policy)

    for (ri, ci), vals in cell_values.items():
        clean = [x for x in vals if x == x]  # drop NaNs
        if not clean:
            grid[ri][ci] = float("nan")
            continue
        if len(clean) == 1 or duplicate_policy in ("warn_last", "last"):
            grid[ri][ci] = clean[-1]
        elif duplicate_policy in ("warn_first", "first"):
            grid[ri][ci] = clean[0]
        else:
            # warn_mean (default): average duplicates
            grid[ri][ci] = sum(clean) / float(len(clean))

    unit = _infer_unit(valid_rows)
    metric_label = _infer_metric_label(valid_rows)
    label_mode = str(plotting_def.get("label_units_mode") or "auto").strip().lower()

    # Build colormap (optional custom colors or named cmap)
    cmap = None
    cmap_colors = plotting_def.get("cmap_colors")
    if cmap_colors:
        try:
            cmap = mcolors.LinearSegmentedColormap.from_list("custom", cmap_colors)
        except Exception:
            cmap = None
    if cmap is None:
        cmap = plotting_def.get("cmap", "viridis")
    # Optional explicit limits + range locking
    vmin_cfg = plotting_def.get("vmin")
    vmax_cfg = plotting_def.get("vmax")
    discrete_bins = plotting_def.get("discrete_bins")
    norm = None
    vmin = None
    vmax = None
    finite_vals = [grid[r][c] for r in range(len(grid)) for c in range(len(grid[0])) if grid[r][c] == grid[r][c]]
    base_path = Path(csv_path).parent if csv_path else out_dir
    range_vals = _collect_range_values(plotting_def.get("range_csv_glob"), value_field, base_path)
    vals_for_range = range_vals if range_vals else finite_vals
    if vals_for_range:
        vmin = min(vals_for_range) if vmin_cfg is None else float(vmin_cfg)
        vmax = max(vals_for_range) if vmax_cfg is None else float(vmax_cfg)
        if vmin == vmax:
            eps = abs(vmin) * 1e-6 if vmin != 0 else 1e-3
            vmin -= eps
            vmax += eps

    norm_name = plotting_def.get("norm")
    center_spec = plotting_def.get("center") or plotting_def.get("center_mode") or plotting_def.get("center_value")
    center_val = _resolve_center_value(center_spec, vals_for_range)
    if norm_name:
        norm, vmin, vmax = _resolve_norm(
            norm_name,
            grid,
            vmin=vmin,
            vmax=vmax,
            linthresh=plotting_def.get("linthresh"),
            linscale=plotting_def.get("linscale"),
            vcenter=center_val,
            label=name,
        )
    elif discrete_bins and isinstance(discrete_bins, int) and discrete_bins > 0 and vmin is not None and vmax is not None:
        boundaries = list(np.linspace(vmin, vmax, discrete_bins + 1))
        norm = mcolors.BoundaryNorm(boundaries, discrete_bins)

    fig, ax = plt.subplots()
    if norm is not None:
        im = ax.imshow(grid, origin="lower", cmap=cmap, norm=norm)
    else:
        im = ax.imshow(grid, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax)
    cbar_label = plotting_def.get("colorbar_label")
    if label_mode == "auto":
        cbar_label = _format_text_with_units(cbar_label, unit, metric_label) if cbar_label else (f"{value_field} ({unit})" if unit else value_field)
    else:
        cbar_label = cbar_label or (f"{value_field} ({unit})" if unit else value_field)
    cbar = fig.colorbar(im, ax=ax, label=cbar_label)
    if norm and isinstance(norm, mcolors.BoundaryNorm):
        cbar.set_ticks(norm.boundaries)
        cbar.ax.set_yticklabels([f"{b:.2g}" for b in norm.boundaries])
    _apply_colorbar_formatting(cbar, plotting_def)

    # Optional overlay: color-coded text for another metric (e.g., std_value sigma bins)
    overlay_cfg = plotting_def.get("overlay_std") or {}
    if overlay_cfg.get("enable"):
        ov_field = overlay_cfg.get("value_field", "std_value")
        text_fmt = overlay_cfg.get("text_fmt", "{val:.1f}")
        sigma_bins = overlay_cfg.get("sigma_bins", [1.0, 2.0, 3.0, 5.0])
        colors = overlay_cfg.get("colors", ["#006400", "#ffa500", "#ff4500", "#8b0000", "#000000"])
        # Collect overlay values per cell
        ov_cells: Dict[tuple[int, int], float] = {}
        ov_vals = []
        for r in valid_rows:
            ri = int(r.get("row_idx", 0))
            ci = int(r.get("col_idx", 0))
            v = _extract_value(r, ov_field)
            if v == v:
                ov_cells[(ri, ci)] = v
                ov_vals.append(v)
        if ov_vals:
            mean_v = float(np.nanmean(ov_vals))
            sigma_v = float(np.nanstd(ov_vals))
            if sigma_v <= 0.0:
                sigma_v = None
            for (ri, ci), v in ov_cells.items():
                if v != v:
                    ax.text(ci, ri, "NA", ha="center", va="center", color="#ff0000", fontsize=8, fontweight="bold")
                    continue
                z = 0.0
                if sigma_v:
                    z = abs(v - mean_v) / sigma_v
                color = _sigma_color(z, sigma_bins, colors)
                ax.text(ci, ri, text_fmt.format(val=v, z=z), ha="center", va="center", color=color, fontsize=8)
            if overlay_cfg.get("legend", True):
                handles = _sigma_legend_handles(list(sigma_bins), list(colors), marker="s")
                if handles:
                    loc = overlay_cfg.get("legend_loc", "upper right")
                    bbox = overlay_cfg.get("legend_bbox")  # e.g., [1.05, 1] to place outside
                    if overlay_cfg.get("legend_separate"):
                        _save_separate_legend(out_dir, f"{name}_sigma", handles, f"{ov_field} s-bins", loc="upper left")
                    elif overlay_cfg.get("legend_panel"):
                        box = ax.get_position()
                        pad = float(overlay_cfg.get("legend_panel_pad", 0.02))
                        width = float(overlay_cfg.get("legend_panel_width", 0.08))
                        leg_ax = ax.figure.add_axes([box.x1 + pad, box.y0, width, box.height])
                        leg_ax.axis("off")
                        leg_ax.legend(handles=handles, title=f"{ov_field} s-bins", loc="upper left", fontsize=7, title_fontsize=8, framealpha=0.8)
                    elif bbox:
                        ax.legend(handles=handles, title=f"{ov_field} s-bins", loc=loc, bbox_to_anchor=tuple(bbox), fontsize=7, title_fontsize=8, framealpha=0.8)
                    else:
                        ax.legend(handles=handles, title=f"{ov_field} s-bins", loc=loc, fontsize=7, title_fontsize=8, framealpha=0.8)

    # Optional alpha overlay driven by another field (e.g., std_value)
    alpha_cfg = plotting_def.get("overlay_alpha") or {}
    if alpha_cfg.get("enable"):
        alpha_field = alpha_cfg.get("value_field", "std_value")
        alpha_min = float(alpha_cfg.get("alpha_min", 0.3))
        alpha_max = float(alpha_cfg.get("alpha_max", 1.0))
        vmin_a = alpha_cfg.get("vmin")
        vmax_a = alpha_cfg.get("vmax")
        alpha_grid = [[1.0] * (max_col + 1) for _ in range(max_row + 1)]
        vals = []
        for r in valid_rows:
            ri = int(r.get("row_idx", 0))
            ci = int(r.get("col_idx", 0))
            v = _extract_value(r, alpha_field)
            if v == v:
                vals.append(v)
                alpha_grid[ri][ci] = v
        if vals:
            lo = float(vmin_a) if vmin_a is not None else min(vals)
            hi = float(vmax_a) if vmax_a is not None else max(vals)
            if hi == lo:
                hi = lo + 1e-6
            for ri in range(max_row + 1):
                for ci in range(max_col + 1):
                    v = alpha_grid[ri][ci]
                    if v == v:
                        frac = (v - lo) / (hi - lo)
                        frac = max(0.0, min(1.0, frac))
                        alpha_grid[ri][ci] = alpha_min + (alpha_max - alpha_min) * frac
                    else:
                        alpha_grid[ri][ci] = alpha_min
            im.set_alpha(np.array(alpha_grid))

    # Optional hatch overlay to flag cells exceeding thresholds
    hatch_cfg = plotting_def.get("overlay_hatch") or {}
    if hatch_cfg.get("enable"):
        h_field = hatch_cfg.get("value_field", "std_value")
        thresh = float(hatch_cfg.get("threshold", 0.0))
        direction = str(hatch_cfg.get("direction", "gt")).lower()
        hatch_pat = str(hatch_cfg.get("hatch", "///"))
        edgecolor = hatch_cfg.get("edgecolor", "#000000")
        facecolor = hatch_cfg.get("facecolor", "none")
        alpha = float(hatch_cfg.get("alpha", 0.3))
        for r in valid_rows:
            ri = int(r.get("row_idx", 0))
            ci = int(r.get("col_idx", 0))
            v = _extract_value(r, h_field)
            if v != v:
                continue
            cond = v > thresh if direction in ("gt", "above") else v < thresh
            if cond:
                ax.add_patch(
                    Rectangle((ci - 0.5, ri - 0.5), 1.0, 1.0, hatch=hatch_pat, fill=True, edgecolor=edgecolor, facecolor=facecolor, lw=0.5, alpha=alpha)
                )

    ax.set_xlabel("col_idx")
    ax.set_ylabel("row_idx")
    _apply_axis_formatting(ax, plotting_def, "x")
    _apply_axis_formatting(ax, plotting_def, "y")
    _apply_integer_ticks(ax, plotting_def)
    title = plotting_def.get("title", name)
    if label_mode == "auto":
        title = _format_text_with_units(title, unit, metric_label) if title else name
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.png", dpi=300)
    plt.close(fig)


def plot_heatmap_two_panel(rows: List[Dict[str, Any]], plotting_def: Dict[str, Any], out_dir: Path, name: str, csv_path: Optional[str] = None):
    """
    Two-panel plot: left = avg heatmap, right = std (or other secondary field).
    """
    left_field = plotting_def.get("left_field", "avg_value")
    right_field = plotting_def.get("right_field", "std_value")
    duplicate_policy = plotting_def.get("duplicate_policy", "warn_mean")
    label_mode = str(plotting_def.get("label_units_mode") or "auto").strip().lower()

    def build_grid(field: str):
        valid_rows = []
        for r in rows:
            try:
                ri = int(r.get("row_idx", -1))
                ci = int(r.get("col_idx", -1))
            except Exception:
                continue
            if ri < 0 or ci < 0:
                continue
            valid_rows.append(r)
        if not valid_rows:
            return None, 0, 0
        max_row = max(int(r.get("row_idx", 0)) for r in valid_rows)
        max_col = max(int(r.get("col_idx", 0)) for r in valid_rows)
        grid = [[float("nan")] * (max_col + 1) for _ in range(max_row + 1)]
        cell_values: Dict[tuple[int, int], List[float]] = {}
        for r in valid_rows:
            ri = int(r.get("row_idx", 0))
            ci = int(r.get("col_idx", 0))
            v = _extract_value(r, field)
            cell_values.setdefault((ri, ci), []).append(v)
        for (ri, ci), vals in cell_values.items():
            clean = [x for x in vals if x == x]
            if not clean:
                grid[ri][ci] = float("nan")
            elif len(clean) == 1 or duplicate_policy in ("warn_last", "last"):
                grid[ri][ci] = clean[-1]
            elif duplicate_policy in ("warn_first", "first"):
                grid[ri][ci] = clean[0]
            else:
                grid[ri][ci] = sum(clean) / float(len(clean))
        return grid, max_row, max_col

    left_grid, lr, lc = build_grid(left_field)
    right_grid, rr, rc = build_grid(right_field)
    if left_grid is None or right_grid is None:
        log.warning("No valid rows for two-panel heatmap: %s", name)
        return

    unit = _infer_unit(rows)
    metric_label = _infer_metric_label(rows)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharex=True, sharey=True)
    cmap_left = plotting_def.get("left_cmap", "viridis")
    cmap_right = plotting_def.get("right_cmap", "magma")

    base_path = Path(csv_path).parent if csv_path else out_dir
    left_vals = _collect_range_values(plotting_def.get("left_range_csv_glob"), left_field, base_path)
    right_vals = _collect_range_values(plotting_def.get("right_range_csv_glob"), right_field, base_path)
    if not left_vals:
        left_vals = [v for row in left_grid for v in row if v == v]
    if not right_vals:
        right_vals = [v for row in right_grid for v in row if v == v]

    left_vmin = plotting_def.get("left_vmin")
    left_vmax = plotting_def.get("left_vmax")
    right_vmin = plotting_def.get("right_vmin")
    right_vmax = plotting_def.get("right_vmax")
    if left_vmin is None and left_vals:
        left_vmin = min(left_vals)
    if left_vmax is None and left_vals:
        left_vmax = max(left_vals)
    if right_vmin is None and right_vals:
        right_vmin = min(right_vals)
    if right_vmax is None and right_vals:
        right_vmax = max(right_vals)

    left_center_spec = plotting_def.get("left_center") or plotting_def.get("center") or plotting_def.get("center_mode") or plotting_def.get("center_value")
    right_center_spec = plotting_def.get("right_center") or plotting_def.get("center") or plotting_def.get("center_mode") or plotting_def.get("center_value")
    left_center_val = _resolve_center_value(left_center_spec, left_vals)
    right_center_val = _resolve_center_value(right_center_spec, right_vals)

    left_norm, left_vmin, left_vmax = _resolve_norm(
        plotting_def.get("left_norm"),
        left_grid,
        vmin=left_vmin,
        vmax=left_vmax,
        linthresh=plotting_def.get("left_linthresh"),
        linscale=plotting_def.get("left_linscale"),
        vcenter=left_center_val,
        label=f"{name}.left",
    )
    right_norm, right_vmin, right_vmax = _resolve_norm(
        plotting_def.get("right_norm"),
        right_grid,
        vmin=right_vmin,
        vmax=right_vmax,
        linthresh=plotting_def.get("right_linthresh"),
        linscale=plotting_def.get("right_linscale"),
        vcenter=right_center_val,
        label=f"{name}.right",
    )

    if left_norm is not None:
        im1 = axes[0].imshow(left_grid, origin="lower", cmap=cmap_left, norm=left_norm)
    else:
        im1 = axes[0].imshow(left_grid, origin="lower", cmap=cmap_left, vmin=left_vmin, vmax=left_vmax)
    left_title = plotting_def.get("left_title")
    if label_mode == "auto":
        left_title = _format_text_with_units(left_title, unit, metric_label) if left_title else f"{left_field}"
    else:
        left_title = left_title or f"{left_field}"
    axes[0].set_title(left_title)
    axes[0].set_xlabel("col_idx")
    axes[0].set_ylabel("row_idx")
    _apply_axis_formatting(axes[0], plotting_def, "x")
    _apply_axis_formatting(axes[0], plotting_def, "y")
    _apply_integer_ticks(axes[0], plotting_def)
    cbar1_label = plotting_def.get("left_colorbar_label")
    if label_mode == "auto":
        cbar1_label = _format_text_with_units(cbar1_label, unit, metric_label) if cbar1_label else (f"{left_field} ({unit})" if unit else left_field)
    else:
        cbar1_label = cbar1_label or (f"{left_field} ({unit})" if unit else left_field)
    cbar1 = fig.colorbar(im1, ax=axes[0], label=cbar1_label)
    _apply_colorbar_formatting(cbar1, plotting_def, prefix="left_")

    if right_norm is not None:
        im2 = axes[1].imshow(right_grid, origin="lower", cmap=cmap_right, norm=right_norm)
    else:
        im2 = axes[1].imshow(right_grid, origin="lower", cmap=cmap_right, vmin=right_vmin, vmax=right_vmax)
    right_title = plotting_def.get("right_title")
    if label_mode == "auto":
        right_title = _format_text_with_units(right_title, unit, metric_label) if right_title else f"{right_field}"
    else:
        right_title = right_title or f"{right_field}"
    axes[1].set_title(right_title)
    axes[1].set_xlabel("col_idx")
    _apply_axis_formatting(axes[1], plotting_def, "x")
    _apply_axis_formatting(axes[1], plotting_def, "y")
    _apply_integer_ticks(axes[1], plotting_def)
    cbar2_label = plotting_def.get("right_colorbar_label")
    if label_mode == "auto":
        cbar2_label = _format_text_with_units(cbar2_label, unit, metric_label) if cbar2_label else (f"{right_field} ({unit})" if unit else right_field)
    else:
        cbar2_label = cbar2_label or (f"{right_field} ({unit})" if unit else right_field)
    cbar2 = fig.colorbar(im2, ax=axes[1], label=cbar2_label)
    _apply_colorbar_formatting(cbar2, plotting_def, prefix="right_")

    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.png", dpi=300)
    plt.close(fig)


def plot_heatmap_grid_bubbles(rows: List[Dict[str, Any]], plotting_def: Dict[str, Any], out_dir: Path, name: str):
    """
    Heatmap for one field with a bubble overlay for another field (typically std).

    Config:
      value_field (background): default avg_value
      overlay_bubbles:
        enable: true
        value_field: std_value
        sigma_bins: [1,2,3,5]
        colors: [...]
        max_sigma: 5
        size_min: 30
        size_max: 300
        alpha: 0.9
        edgecolor: "#000000"
        legend: true
    """
    overlay_cfg = plotting_def.get("overlay_bubbles") or {}
    if not overlay_cfg.get("enable"):
        raise ValueError("heatmap_grid_bubbles requires plotting_modes.<mode>.overlay_bubbles.enable: true")

    # Reuse the base heatmap renderer, then add bubbles on top.
    value_field = plotting_def.get("value_field", "avg_value")
    # Copy plotting_def but disable any text overlay to keep this recipe focused.
    base_def = dict(plotting_def)
    base_def.pop("overlay_std", None)

    # Build base heatmap data (mostly copied from plot_heatmap_grid to keep behavior consistent).
    if not rows:
        log.warning("No data rows for heatmap: %s", name)
        return

    valid_rows = []
    skipped = 0
    for r in rows:
        try:
            ri = int(r.get("row_idx", -1))
            ci = int(r.get("col_idx", -1))
        except Exception:
            skipped += 1
            continue
        if ri < 0 or ci < 0:
            skipped += 1
            continue
        valid_rows.append(r)

    if skipped:
        log.warning("Skipping %d rows without valid grid indices for heatmap '%s'.", skipped, name)
    if not valid_rows:
        log.warning("No valid grid-indexed rows for heatmap: %s", name)
        return

    max_row = max(int(r.get("row_idx", 0)) for r in valid_rows)
    max_col = max(int(r.get("col_idx", 0)) for r in valid_rows)
    grid = [[float("nan")] * (max_col + 1) for _ in range(max_row + 1)]

    duplicate_policy = plotting_def.get("duplicate_policy", "warn_mean")

    def _reduce(vals: List[float]) -> float:
        clean = [x for x in vals if x == x]
        if not clean:
            return float("nan")
        if len(clean) == 1 or duplicate_policy in ("warn_last", "last"):
            return clean[-1]
        if duplicate_policy in ("warn_first", "first"):
            return clean[0]
        return sum(clean) / float(len(clean))

    bg_cell_values: Dict[tuple[int, int], List[float]] = {}
    ov_field = overlay_cfg.get("value_field", "std_value")
    ov_cell_values: Dict[tuple[int, int], List[float]] = {}
    for r in valid_rows:
        ri = int(r.get("row_idx", 0))
        ci = int(r.get("col_idx", 0))
        bg_v = _extract_value(r, value_field)
        bg_cell_values.setdefault((ri, ci), []).append(bg_v)
        ov_v = _extract_value(r, ov_field)
        ov_cell_values.setdefault((ri, ci), []).append(ov_v)

    duplicates = {k: v for k, v in bg_cell_values.items() if len(v) > 1}
    if duplicates:
        msg = "Found %d duplicate grid cells for heatmap '%s'." % (len(duplicates), name)
        if duplicate_policy == "error":
            raise ValueError(msg + " Set plotting_modes.<mode>.duplicate_policy to control behavior.")
        log.warning("%s Using policy=%s.", msg, duplicate_policy)

    for (ri, ci), vals in bg_cell_values.items():
        grid[ri][ci] = _reduce(vals)

    cmap = plotting_def.get("cmap", "viridis")
    cmap_colors = plotting_def.get("cmap_colors")
    if cmap_colors:
        try:
            cmap = mcolors.LinearSegmentedColormap.from_list("custom", cmap_colors)
        except Exception:
            pass

    # Optional explicit limits for background
    vmin = plotting_def.get("vmin")
    vmax = plotting_def.get("vmax")
    if vmin is not None:
        vmin = float(vmin)
    if vmax is not None:
        vmax = float(vmax)

    unit = _infer_unit(valid_rows)
    fig, ax = plt.subplots()
    im = ax.imshow(grid, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax)
    cbar_label = plotting_def.get("colorbar_label") or ("%s (%s)" % (value_field, unit) if unit else value_field)
    fig.colorbar(im, ax=ax, label=cbar_label)

    # Bubble overlay
    sigma_bins = overlay_cfg.get("sigma_bins", [1.0, 2.0, 3.0, 5.0])
    colors = overlay_cfg.get("colors", ["#006400", "#ffa500", "#ff4500", "#8b0000", "#000000"])
    max_sigma = float(overlay_cfg.get("max_sigma", 5.0))
    size_min = float(overlay_cfg.get("size_min", 30.0))
    size_max = float(overlay_cfg.get("size_max", 300.0))
    alpha = float(overlay_cfg.get("alpha", 0.9))
    edgecolor = overlay_cfg.get("edgecolor", "#000000")

    ov_vals = []
    ov_cell_reduced: Dict[tuple[int, int], float] = {}
    for k, vals in ov_cell_values.items():
        v = _reduce(vals)
        ov_cell_reduced[k] = v
        if v == v:
            ov_vals.append(v)

    mean_v = float(np.nanmean(ov_vals)) if ov_vals else 0.0
    sigma_v = float(np.nanstd(ov_vals)) if ov_vals else 0.0
    if sigma_v <= 0.0:
        sigma_v = None

    xs = []
    ys = []
    ss = []
    cs = []
    for (ri, ci), v in ov_cell_reduced.items():
        if v != v:
            continue
        z = 0.0
        if sigma_v:
            z = abs(v - mean_v) / sigma_v
        zc = min(z, max_sigma) if max_sigma > 0 else z
        frac = (zc / max_sigma) if max_sigma > 0 else 0.0
        size = size_min + (size_max - size_min) * frac
        xs.append(ci)
        ys.append(ri)
        ss.append(size)
        cs.append(_sigma_color(z, list(sigma_bins), list(colors)))

    ax.scatter(xs, ys, s=ss, c=cs, alpha=alpha, edgecolors=edgecolor, linewidths=0.8)
    if overlay_cfg.get("legend", True):
        handles = _sigma_legend_handles(list(sigma_bins), list(colors), marker="o")
        if handles:
            loc = overlay_cfg.get("legend_loc", "upper right")
            bbox = overlay_cfg.get("legend_bbox")
            if overlay_cfg.get("legend_separate"):
                _save_separate_legend(out_dir, f"{name}_sigma", handles, f"{ov_field} s-bins", loc="upper left")
            elif overlay_cfg.get("legend_panel"):
                box = ax.get_position()
                pad = float(overlay_cfg.get("legend_panel_pad", 0.02))
                width = float(overlay_cfg.get("legend_panel_width", 0.08))
                leg_ax = ax.figure.add_axes([box.x1 + pad, box.y0, width, box.height])
                leg_ax.axis("off")
                leg_ax.legend(handles=handles, title=f"{ov_field} s-bins", loc="upper left", fontsize=7, title_fontsize=8, framealpha=0.8)
            elif bbox:
                ax.legend(handles=handles, title=f"{ov_field} s-bins", loc=loc, bbox_to_anchor=tuple(bbox), fontsize=7, title_fontsize=8, framealpha=0.8)
            else:
                ax.legend(handles=handles, title=f"{ov_field} s-bins", loc=loc, fontsize=7, title_fontsize=8, framealpha=0.8)

    ax.set_xlabel("col_idx")
    ax.set_ylabel("row_idx")
    ax.set_title(plotting_def.get("title", name))
    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.png", dpi=300)
    plt.close(fig)
