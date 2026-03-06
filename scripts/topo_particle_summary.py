import argparse
import csv
import json
import math
import re
import statistics as stats
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_BASE = Path(r"C:\Users\Conor O'Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT")
DATA_GROUPED = Path("docs/File Locations for Data Grouped.txt")

SCAN_SIZE_UM = (5.0, 5.0)
GRID = (512, 512)
RES_NM = 5000.0 / 512.0
TARGET_ISOLATED = 30


def read_inventory():
    inv_path = OUT_BASE / "scan_inventory.json"
    if not inv_path.exists():
        return []
    return json.loads(inv_path.read_text(encoding="utf-8"))


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def find_summary_csvs():
    return list(OUT_BASE.rglob("summary.csv"))


def read_particle_summary(csv_path):
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def find_particle_csvs():
    return list(OUT_BASE.rglob("*_particles.csv"))


def read_particle_rows(csv_path):
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def find_grain_csvs():
    return list(OUT_BASE.rglob("*_grains.csv"))


def read_grain_rows(csv_path):
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def to_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def to_float_or_none(v):
    try:
        return float(v)
    except Exception:
        return None


def to_int(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default


def sample_from_summary_path(csv_path):
    # .../<system>/<sample>/<job>/summary.csv
    try:
        return csv_path.parent.parent.name
    except Exception:
        return "unknown"


def system_from_summary_path(csv_path):
    try:
        # .../<system>/<sample>/<job>/summary.csv
        return csv_path.parent.parent.parent.name
    except Exception:
        return "unknown"

def job_from_summary_path(csv_path):
    try:
        return csv_path.parent.name
    except Exception:
        return "unknown"


def sample_from_particle_path(csv_path):
    try:
        # .../<system>/<sample>/<job>/particles/*_particles.csv
        return csv_path.parent.parent.name
    except Exception:
        return "unknown"


def system_from_particle_path(csv_path):
    try:
        return csv_path.parent.parent.parent.name
    except Exception:
        return "unknown"

def job_from_particle_path(csv_path):
    try:
        return csv_path.parent.parent.name
    except Exception:
        return "unknown"


def sample_from_grain_path(csv_path):
    try:
        # .../<system>/<sample>/<job>/grains/*_grains.csv
        return csv_path.parent.parent.name
    except Exception:
        return "unknown"


def system_from_grain_path(csv_path):
    try:
        return csv_path.parent.parent.parent.name
    except Exception:
        return "unknown"


def job_from_grain_path(csv_path):
    try:
        return csv_path.parent.parent.name
    except Exception:
        return "unknown"


def grain_numeric_fields(rows):
    if not rows:
        return []
    exclude = set([
        "source_file",
        "grain_id",
        "center_x_px",
        "center_y_px",
        "center_x_nm",
        "center_y_nm",
        "kept",
        "isolated",
        "edge_excluded",
    ])
    fields = set()
    for row in rows:
        for key, val in row.items():
            if key in exclude:
                continue
            if not (key in ("area_px", "diameter_px", "diameter_nm") or key.startswith("grain_")):
                continue
            if to_float_or_none(val) is not None:
                fields.add(key)
    return sorted(fields)


def summarize_numeric(values):
    if not values:
        return {"mean": 0.0, "std": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "count": 0}
    return {
        "mean": stats.mean(values),
        "std": stats.pstdev(values) if len(values) > 1 else 0.0,
        "median": stats.median(values),
        "min": min(values),
        "max": max(values),
        "count": len(values),
    }


def _plot_hist(values, title, xlabel, out_path, bins=30, color="#4C78A8"):
    if not values:
        return
    plt.figure(figsize=(6, 4))
    plt.hist(values, bins=bins, color=color, edgecolor="black")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()


def short_label(label, max_len=18):
    if len(label) <= max_len:
        return label
    return label[: max_len - 3] + "..."


def wrap_label(label, max_len=16, max_lines=2):
    if len(label) <= max_len:
        return label
    parts = label.split("_")
    if len(parts) == 1:
        return short_label(label, max_len)
    lines = []
    current = ""
    for part in parts:
        if not current:
            candidate = part
        else:
            candidate = current + "_" + part
        if len(candidate) <= max_len:
            current = candidate
            continue
        lines.append(current if current else part)
        current = part if current else ""
        if len(lines) >= max_lines - 1:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    return "\n".join(lines)


def _wt_percent_from_sample(sample):
    if not sample:
        return None
    m = re.search(r"tpo(10|25)sinp", sample, re.I)
    if not m:
        return None
    return int(m.group(1))


def parse_data_grouped(path):
    groups = []
    current_system = None
    current_label = None
    if not path.exists():
        return groups
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# PEGDA Only"):
            current_system = "pegda"
            current_label = None
            continue
        if line.startswith("# PEGDA SiNP"):
            current_system = "pegda_sinp"
            current_label = None
            continue
        if line.startswith("## "):
            current_label = line[3:].strip()
            groups.append({"system": current_system, "label": current_label, "roots": []})
            continue
        if line.startswith("#"):
            continue
        if line.startswith("C:\\") and groups:
            groups[-1]["roots"].append(line)
    return groups


def _norm_key(value):
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def build_sample_group_map(groups):
    """
    Build a mapping from sample folder name -> grouped metadata.

    We keep:
    - exact map: sample -> group
    - normalized map: norm(sample) -> group
    - root norms: norm(full_root_path) -> group (for substring matches)
    """
    mapping = {}
    norm_map = {}
    root_norms = []
    for g in groups:
        for root in g["roots"]:
            sample = Path(root).name
            mapping[sample] = g
            n = _norm_key(sample)
            if n:
                norm_map[n] = g
            root_norms.append((_norm_key(root), g))
    return mapping, norm_map, root_norms


def classify_sample(sample, mapping, norm_map, root_norms):
    if sample in mapping:
        return mapping[sample]
    norm = _norm_key(sample)
    if norm in norm_map:
        return norm_map[norm]
    # Prefer root path substring match: root_norm in norm(sample) or norm(sample) in root_norm
    for root_norm, g in root_norms or []:
        if not root_norm or not norm:
            continue
        if root_norm in norm or norm in root_norm:
            return g
    # Last resort: fuzzy contains
    best = None
    best_len = 0
    for k, g in norm_map.items():
        if not k or not norm:
            continue
        if k in norm or norm in k:
            if len(k) > best_len:
                best_len = len(k)
                best = g
    return best or {}


def scraped_status_from_label(label):
    if not label:
        return ""
    if re.search(r"\bnon[- ]scraped\b", label, re.I):
        return "Non Scraped"
    if re.search(r"\bscraped\b", label, re.I):
        return "Scraped"
    return ""


def wt_percent_from_label(label):
    if not label:
        return ""
    m = re.search(r"(10|25)%", label)
    return f"{m.group(1)}%" if m else ""


def _parse_row_col(source_file):
    if not source_file:
        return None, None
    m = re.search(r"LOC_RC(?P<row>\d{3})(?P<col>\d{3})", source_file)
    if not m:
        return None, None
    return int(m.group("row")), int(m.group("col"))


def parse_args():
    ap = argparse.ArgumentParser(description="Aggregate topo particle outputs.")
    ap.add_argument("--out-base", default="", help="Override output base directory.")
    ap.add_argument("--config", default="", help="Optional YAML config file with summary_plot overrides.")
    ap.add_argument("--grid-cmap", default="viridis", help="Colormap for grid plots.")
    ap.add_argument("--grid-zero-outline-color", default="red", help="Outline color for zero-count scans.")
    ap.add_argument("--grid-fixed-max", type=float, default=15.0, help="Fixed max particles/scan for filtered grids.")
    ap.add_argument("--grid-fixed-max-raw", type=float, default=60.0, help="Fixed max particles/scan for raw grids.")
    ap.add_argument("--grid-raw-job-pattern", default="raw|unfiltered|nomask", help="Regex to treat job as raw.")
    ap.add_argument("--fast", action="store_true", help="Skip slow plotting (for quick iteration).")
    ap.add_argument("--skip-grid-plots", action="store_true", help="Skip grid heatmap plots.")
    ap.add_argument("--skip-grain-hist-plots", action="store_true", help="Skip per-job grain histogram plots.")
    ap.add_argument("--skip-grain-trend-plots", action="store_true", help="Skip grain trend plots by job.")
    return ap.parse_args()


def _grid_expected_positions(rows, cols, index_base):
    return {(r, c) for r in range(index_base, index_base + rows) for c in range(index_base, index_base + cols)}


def _format_positions(positions, limit=20):
    items = sorted(positions)[:limit]
    return "; ".join("R%03dC%03d" % (r, c) for r, c in items)


def apply_grid_policy(count_rows, sample_to_group, cfg):
    summary_cfg = cfg.get("summary", {}) if cfg else {}
    policy = summary_cfg.get("grid_policy", "keep_all")
    grid_rows = int(summary_cfg.get("grid_rows", 21))
    grid_cols = int(summary_cfg.get("grid_cols", 21))
    index_base = int(summary_cfg.get("grid_index_base", 1))
    exclude_samples = set(s for s in summary_cfg.get("exclude_samples", []) if s)
    exclude_source_files = [s.lower() for s in summary_cfg.get("exclude_source_files", []) if s]

    filtered = []
    for row in count_rows:
        sample = row.get("sample", "")
        source_file = (row.get("source_file") or "").lower()
        if sample in exclude_samples:
            continue
        if exclude_source_files and any(token in source_file for token in exclude_source_files):
            continue
        filtered.append(row)

    expected = _grid_expected_positions(grid_rows, grid_cols, index_base)
    sample_positions = {}
    sample_pos_files = {}
    for row in filtered:
        sample = row.get("sample", "")
        row_idx = to_int(row.get("row_idx", -1), -1)
        col_idx = to_int(row.get("col_idx", -1), -1)
        if row_idx <= 0 or col_idx <= 0:
            continue
        sample_positions.setdefault(sample, set()).add((row_idx, col_idx))
        key = (sample, row_idx, col_idx)
        sample_pos_files.setdefault(key, set()).add(row.get("source_file", ""))

    issues = []
    for sample, positions in sample_positions.items():
        group = sample_to_group.get(sample, {})
        label = group.get("label", "")
        wt = wt_percent_from_label(label) or (f"{_wt_percent_from_sample(sample)}%" if _wt_percent_from_sample(sample) else "")
        scraped = scraped_status_from_label(label)
        missing = expected - positions
        duplicate_positions = []
        duplicate_files = []
        for (s, r, c), files in sample_pos_files.items():
            if s != sample:
                continue
            if len(files) > 1:
                duplicate_positions.append((r, c))
                duplicate_files.extend(list(files)[:3])
        issues.append({
            "sample": sample,
            "system": row.get("system", ""),
            "group_label": label,
            "wt_percent": wt,
            "scraped": scraped,
            "expected_positions": len(expected),
            "present_positions": len(positions),
            "missing_count": len(missing),
            "missing_positions": _format_positions(missing),
            "duplicate_positions": _format_positions(set(duplicate_positions)),
            "duplicate_files": "; ".join(sorted(set(duplicate_files))[:5]),
        })

    issues_path = OUT_BASE / "grid_issues_by_sample.csv"
    if issues:
        write_csv(issues_path, issues, list(issues[0].keys()))

    if policy == "manual_review":
        problem_samples = [r for r in issues if r.get("missing_count", 0) or r.get("duplicate_positions")]
        if problem_samples:
            review_csv = OUT_BASE / "grid_manual_review.csv"
            write_csv(review_csv, problem_samples, list(problem_samples[0].keys()))
            blacklist = OUT_BASE / "grid_manual_review_blacklist.txt"
            blacklist.write_text("\n".join(sorted({r["sample"] for r in problem_samples})), encoding="utf-8")
            print("Manual review required. See:")
            print(str(review_csv))
            print(str(blacklist))
            return None, {"policy": policy, "issues": len(problem_samples)}

    if policy == "require_full_grid":
        full_samples = {r["sample"] for r in issues if r.get("missing_count", 0) == 0}
        filtered = [r for r in filtered if r.get("sample") in full_samples]
        return filtered, {"policy": policy, "kept_samples": len(full_samples), "expected_positions": len(expected)}

    if policy == "intersect_grid":
        group_positions = {}
        for r in issues:
            sample = r["sample"]
            group = sample_to_group.get(sample, {})
            key = group.get("label") or r.get("system") or "unknown"
            group_positions.setdefault(key, []).append(sample_positions.get(sample, set()))
        intersection = {}
        for key, sets in group_positions.items():
            if not sets:
                continue
            inter = set.intersection(*sets) if len(sets) > 1 else sets[0]
            intersection[key] = inter
        filtered = [
            r for r in filtered
            if (r.get("row_idx"), r.get("col_idx")) in intersection.get(
                (sample_to_group.get(r.get("sample", ""), {}).get("label") or r.get("system") or "unknown"),
                set()
            )
        ]
        return filtered, {"policy": policy, "groups": len(intersection)}

    return filtered, {"policy": policy}


def main():
    args = parse_args()
    global OUT_BASE
    if args.out_base:
        OUT_BASE = Path(args.out_base)
    cfg = {}
    # Some attributes are only populated when a config file is loaded; default them for direct CLI use.
    if not hasattr(args, "job_order"):
        args.job_order = []
    # "fast" implies skipping the slowest plots unless explicitly requested.
    if getattr(args, "fast", False):
        args.skip_grid_plots = True
        args.skip_grain_hist_plots = True
    if args.config:
        try:
            import yaml
            cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {}
            plot_cfg = cfg.get("summary_plot") or {}
            args.grid_cmap = plot_cfg.get("grid_cmap", args.grid_cmap)
            args.grid_zero_outline_color = plot_cfg.get("grid_zero_outline_color", args.grid_zero_outline_color)
            args.grid_fixed_max = float(plot_cfg.get("grid_fixed_max", args.grid_fixed_max))
            args.grid_fixed_max_raw = float(plot_cfg.get("grid_fixed_max_raw", args.grid_fixed_max_raw))
            args.grid_raw_job_pattern = plot_cfg.get("grid_raw_job_pattern", args.grid_raw_job_pattern)
            args.job_order = plot_cfg.get("job_order", [])
            # Optional toggles (defaults preserve existing behavior).
            if "enable_grid_plots" in plot_cfg:
                args.skip_grid_plots = not bool(plot_cfg.get("enable_grid_plots"))
            if "enable_grain_hist_plots" in plot_cfg:
                args.skip_grain_hist_plots = not bool(plot_cfg.get("enable_grain_hist_plots"))
            if "enable_grain_trend_plots" in plot_cfg:
                args.skip_grain_trend_plots = not bool(plot_cfg.get("enable_grain_trend_plots"))
        except Exception:
            pass

    inv = read_inventory()
    groups = parse_data_grouped(DATA_GROUPED)
    sample_to_group, norm_group_map, root_norms = build_sample_group_map(groups)

    systems = {"pegda": [], "pegda_sinp": []}
    for r in inv:
        sys_name = r.get("system", "unknown")
        if sys_name in systems:
            systems[sys_name].append(r)

    inventory_table = []
    for sys_name, rows in systems.items():
        total_maps = sum(int(r.get("map_count", 0)) for r in rows)
        if total_maps == 0:
            continue
        inventory_table.append({
            "system": "PEGDA" if sys_name == "pegda" else "PEGDA-SiNP",
            "total_maps": total_maps,
            "scan_um_x": SCAN_SIZE_UM[0],
            "scan_um_y": SCAN_SIZE_UM[1],
            "grid_x": GRID[0],
            "grid_y": GRID[1],
            "resolution_nm_per_px": RES_NM,
        })

    write_csv(OUT_BASE / "scan_inventory.csv", inventory_table, list(inventory_table[0].keys()) if inventory_table else [
        "system","total_maps","scan_um_x","scan_um_y","grid_x","grid_y","resolution_nm_per_px"
    ])

    summary_rows = []
    for p in find_summary_csvs():
        # Accept any particle job summary: .../<system>/<sample>/<job>/summary.csv
        if p.parent.name.lower().startswith("particle_") is False:
            continue
        for row in read_particle_summary(p):
            row["source_csv"] = str(p)
            row["sample"] = sample_from_summary_path(p)
            row["system"] = system_from_summary_path(p)
            row["job"] = job_from_summary_path(p)
            summary_rows.append(row)

    count_rows = []
    for row in summary_rows:
        count_total = to_int(row.get("count_total"))
        raw_val = row.get("count_total_raw")
        raw_present = raw_val not in (None, "")
        count_total_raw = to_int(raw_val)
        count_total_filtered = to_int(row.get("count_total_filtered"))
        count_iso = to_int(row.get("count_isolated"))
        sample = row.get("sample", "unknown")
        system = row.get("system", "unknown")
        job = row.get("job", "unknown")
        group = classify_sample(sample, sample_to_group, norm_group_map, root_norms)
        group_label = group.get("label", "")
        wt_label = wt_percent_from_label(group_label) or (f"{_wt_percent_from_sample(sample)}%" if _wt_percent_from_sample(sample) else "")
        scraped = scraped_status_from_label(group_label)
        row_idx = to_int(row.get("row_idx", -1), -1)
        col_idx = to_int(row.get("col_idx", -1), -1)
        if row_idx <= 0 or col_idx <= 0:
            pr, pc = _parse_row_col(row.get("source_file", ""))
            if pr and pc:
                row_idx = pr
                col_idx = pc
        count_rows.append({
            "source_file": row.get("source_file", ""),
            "count_total": count_total,
            "count_total_raw": count_total_raw if raw_present else "",
            "count_total_filtered": count_total_filtered if count_total_filtered else "",
            "count_isolated": count_iso,
            "threshold": row.get("threshold", ""),
            "threshold_source": row.get("threshold_source", ""),
            "diam_min_nm": row.get("diam_min_nm", ""),
            "diam_max_nm": row.get("diam_max_nm", ""),
            "iso_min_dist_nm": row.get("iso_min_dist_nm", ""),
            "sample": sample,
            "system": system,
            "job": job,
            "group_label": group_label,
            "wt_percent": wt_label,
            "scraped": scraped,
            "row_idx": row_idx,
            "col_idx": col_idx,
        })

    count_rows, policy_info = apply_grid_policy(count_rows, sample_to_group, cfg)
    if count_rows is None:
        print("Summary halted for manual review.")
        return

    counts = []
    isolated_counts = []
    counts_by_sample = {}
    isolated_by_sample = {}
    sample_system = {}
    rows_by_sample = {}
    counts_by_job = {}
    isolated_by_job = {}
    counts_by_job_wt = {}
    isolated_by_job_wt = {}
    counts_raw_by_job = {}
    counts_filtered_by_job = {}
    grid_counts = {}
    grid_isolated = {}
    grid_raw_counts = {}
    grid_zero = {}
    grid_iso_zero = {}
    wt_grid_counts = {}
    wt_grid_isolated = {}
    wt_grid_raw_counts = {}
    wt_grid_n = {}
    wt_grid_counts_sq = {}
    wt_grid_isolated_sq = {}
    wt_grid_raw_counts_sq = {}
    for row in count_rows:
        count_total = to_int(row.get("count_total"))
        raw_val = row.get("count_total_raw")
        raw_present = raw_val not in (None, "")
        count_total_raw = to_int(raw_val)
        count_total_filtered = to_int(row.get("count_total_filtered"))
        count_iso = to_int(row.get("count_isolated"))
        sample = row.get("sample", "unknown")
        system = row.get("system", "unknown")
        job = row.get("job", "unknown")
        wt_label = row.get("wt_percent", "")
        counts.append(count_total)
        isolated_counts.append(count_iso)
        counts_by_sample.setdefault(sample, []).append(count_total)
        isolated_by_sample.setdefault(sample, []).append(count_iso)
        rows_by_sample.setdefault(sample, []).append(row)
        if sample not in sample_system:
            sample_system[sample] = system
        counts_by_job.setdefault(job, []).append(count_total)
        isolated_by_job.setdefault(job, []).append(count_iso)
        if wt_label:
            counts_by_job_wt.setdefault((job, wt_label), []).append(count_total)
            isolated_by_job_wt.setdefault((job, wt_label), []).append(count_iso)
        if raw_present:
            counts_raw_by_job.setdefault(job, []).append(count_total_raw)
        if count_total_filtered:
            counts_filtered_by_job.setdefault(job, []).append(count_total_filtered)

        row_idx = to_int(row.get("row_idx", -1), -1)
        col_idx = to_int(row.get("col_idx", -1), -1)
        if row_idx > 0 and col_idx > 0:
            key = (system, sample, job)
            grid_counts.setdefault(key, {})[(row_idx, col_idx)] = count_total
            grid_isolated.setdefault(key, {})[(row_idx, col_idx)] = count_iso
            if raw_present:
                grid_raw_counts.setdefault(key, {})[(row_idx, col_idx)] = count_total_raw
            if count_total == 0:
                grid_zero.setdefault(key, set()).add((row_idx, col_idx))
            if count_iso == 0:
                grid_iso_zero.setdefault(key, set()).add((row_idx, col_idx))

            wt = _wt_percent_from_sample(sample)
            if wt:
                wt_key = (wt, job)
                wt_grid_counts.setdefault(wt_key, {})
                wt_grid_isolated.setdefault(wt_key, {})
                wt_grid_raw_counts.setdefault(wt_key, {})
                wt_grid_n.setdefault(wt_key, {})
                wt_grid_counts_sq.setdefault(wt_key, {})
                wt_grid_isolated_sq.setdefault(wt_key, {})
                wt_grid_raw_counts_sq.setdefault(wt_key, {})
                wt_grid_counts[wt_key].setdefault((row_idx, col_idx), 0.0)
                wt_grid_isolated[wt_key].setdefault((row_idx, col_idx), 0.0)
                wt_grid_raw_counts[wt_key].setdefault((row_idx, col_idx), 0.0)
                wt_grid_n[wt_key].setdefault((row_idx, col_idx), 0)
                wt_grid_counts_sq[wt_key].setdefault((row_idx, col_idx), 0.0)
                wt_grid_isolated_sq[wt_key].setdefault((row_idx, col_idx), 0.0)
                wt_grid_raw_counts_sq[wt_key].setdefault((row_idx, col_idx), 0.0)
                wt_grid_counts[wt_key][(row_idx, col_idx)] += float(count_total)
                wt_grid_isolated[wt_key][(row_idx, col_idx)] += float(count_iso)
                if raw_present:
                    wt_grid_raw_counts[wt_key][(row_idx, col_idx)] += float(count_total_raw)
                    wt_grid_raw_counts_sq[wt_key][(row_idx, col_idx)] += float(count_total_raw) * float(count_total_raw)
                wt_grid_counts_sq[wt_key][(row_idx, col_idx)] += float(count_total) * float(count_total)
                wt_grid_isolated_sq[wt_key][(row_idx, col_idx)] += float(count_iso) * float(count_iso)
                wt_grid_n[wt_key][(row_idx, col_idx)] += 1

    if count_rows:
        write_csv(OUT_BASE / "particle_counts_by_map.csv", count_rows, list(count_rows[0].keys()))

    count_stats = {}
    if counts:
        count_stats = {
            "total_particles": sum(counts),
            "maps": len(counts),
            "mean_per_map": stats.mean(counts),
            "std_per_map": stats.pstdev(counts) if len(counts) > 1 else 0.0,
            "min_per_map": min(counts),
            "max_per_map": max(counts),
        }

    iso_stats = {}
    if isolated_counts:
        iso_stats = {
            "mean_isolated_per_map": stats.mean(isolated_counts),
            "std_isolated_per_map": stats.pstdev(isolated_counts) if len(isolated_counts) > 1 else 0.0,
            "maps_with_isolated": sum(1 for v in isolated_counts if v > 0),
            "percent_maps_with_isolated": 100.0 * sum(1 for v in isolated_counts if v > 0) / float(len(isolated_counts)),
        }

    diameters = []
    diameters_by_sample = {}
    diameters_by_job = {}
    diameters_by_job_wt = {}
    for p in find_particle_csvs():
        for row in read_particle_rows(p):
            kept = to_int(row.get("kept", 0))
            if kept != 1:
                continue
            d = to_float(row.get("diameter_nm"))
            if d > 0:
                diameters.append(d)
                sample = sample_from_particle_path(p)
                diameters_by_sample.setdefault(sample, []).append(d)
                job = job_from_particle_path(p)
                diameters_by_job.setdefault(job, []).append(d)
                wt = _wt_percent_from_sample(sample)
                if wt:
                    diameters_by_job_wt.setdefault((job, wt), []).append(d)

    diam_stats = {}
    if diameters:
        diam_stats = {
            "count_particles": len(diameters),
            "mean_diameter_nm": stats.mean(diameters),
            "std_diameter_nm": stats.pstdev(diameters) if len(diameters) > 1 else 0.0,
        }

    stats_rows = []
    if count_stats:
        stats_rows.append({"metric": "total_particles", "value": count_stats.get("total_particles")})
        stats_rows.append({"metric": "maps", "value": count_stats.get("maps")})
        stats_rows.append({"metric": "mean_per_map", "value": count_stats.get("mean_per_map")})
        stats_rows.append({"metric": "std_per_map", "value": count_stats.get("std_per_map")})
        stats_rows.append({"metric": "min_per_map", "value": count_stats.get("min_per_map")})
        stats_rows.append({"metric": "max_per_map", "value": count_stats.get("max_per_map")})
    if iso_stats:
        stats_rows.append({"metric": "mean_isolated_per_map", "value": iso_stats.get("mean_isolated_per_map")})
        stats_rows.append({"metric": "std_isolated_per_map", "value": iso_stats.get("std_isolated_per_map")})
        stats_rows.append({"metric": "percent_maps_with_isolated", "value": iso_stats.get("percent_maps_with_isolated")})
    if diam_stats:
        stats_rows.append({"metric": "mean_diameter_nm", "value": diam_stats.get("mean_diameter_nm")})
        stats_rows.append({"metric": "std_diameter_nm", "value": diam_stats.get("std_diameter_nm")})

    if stats_rows:
        write_csv(OUT_BASE / "particle_summary_stats.csv", stats_rows, ["metric", "value"])

    # Diameter stats by job + wt%
    if diameters_by_job_wt:
        rows = []
        for (job, wt), vals in sorted(diameters_by_job_wt.items()):
            if not vals:
                continue
            rows.append({
                "job": job,
                "wt_percent": f"{wt}%",
                "count": len(vals),
                "mean_diameter_nm": stats.mean(vals),
                "std_diameter_nm": stats.pstdev(vals) if len(vals) > 1 else 0.0,
            })
        if rows:
            write_csv(OUT_BASE / "particle_diameter_stats_by_job_wt.csv", rows, list(rows[0].keys()))

    # Diameter histograms by job + wt%
    if diameters_by_job_wt:
        diam_dir = OUT_BASE / "summary_outputs" / "diameter_by_job_wt"
        diam_dir.mkdir(parents=True, exist_ok=True)
        for (job, wt), vals in diameters_by_job_wt.items():
            if not vals:
                continue
            _plot_hist(
                vals,
                "Particle Diameter\n%s (wt%d%%)" % (job, wt),
                "Diameter (nm)",
                diam_dir / ("hist_diameter_%s_wt%d.png" % (job, wt)),
            )

    if counts:
        plt.figure(figsize=(6,4))
        plt.hist(counts, bins=20, color="#4C78A8", edgecolor="black")
        plt.title("Kept Particle Count per Scan\n(all jobs, pre-isolation)")
        plt.xlabel("Particles per map")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_particle_count_hist.png", dpi=300)
        plt.close()

    if diameters:
        plt.figure(figsize=(6,4))
        plt.hist(diameters, bins=30, color="#F58518", edgecolor="black")
        plt.title("Particle Diameter Distribution\n(filtered)")
        plt.xlabel("Diameter (nm)")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_particle_diameter_hist.png", dpi=300)
        plt.close()

    if isolated_counts:
        plt.figure(figsize=(6,4))
        plt.hist(isolated_counts, bins=20, color="#54A24B", edgecolor="black")
        plt.title("Isolated Particle Count per Scan\n(all jobs)")
        plt.xlabel("Isolated particles per map")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_isolated_count_hist.png", dpi=300)
        plt.close()

    if counts:
        plt.figure(figsize=(7,4))
        plt.scatter(range(1, len(counts) + 1), counts, s=12, color="#4C78A8", alpha=0.8)
        plt.title("Kept Particle Count per Scan\n(index order)")
        plt.xlabel("Map index")
        plt.ylabel("Particles per map")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_particle_count_scatter.png", dpi=300)
        plt.close()

    if isolated_counts:
        plt.figure(figsize=(7,4))
        plt.scatter(range(1, len(isolated_counts) + 1), isolated_counts, s=12, color="#54A24B", alpha=0.8)
        plt.title("Isolated Particle Count per Map\n(index order)")
        plt.xlabel("Map index")
        plt.ylabel("Isolated particles per map")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_isolated_count_scatter.png", dpi=300)
        plt.close()

    if counts_by_sample:
        labels = [short_label(s) for s in counts_by_sample.keys()]
        data = [counts_by_sample[s] for s in counts_by_sample.keys()]
        plt.figure(figsize=(8,4))
        plt.boxplot(data, labels=labels, showfliers=True)
        plt.title("Kept Particle Count per Scan\nby Sample")
        plt.xlabel("Sample")
        plt.ylabel("Particles per map")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_particle_count_box_by_sample.png", dpi=300)
        plt.close()

    if isolated_by_sample:
        labels = [short_label(s) for s in isolated_by_sample.keys()]
        data = [isolated_by_sample[s] for s in isolated_by_sample.keys()]
        plt.figure(figsize=(8,4))
        plt.boxplot(data, labels=labels, showfliers=True)
        plt.title("Isolated Particle Count per Map\nby Sample")
        plt.xlabel("Sample")
        plt.ylabel("Isolated particles per map")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_isolated_count_box_by_sample.png", dpi=300)
        plt.close()

    if counts_by_sample:
        labels = [short_label(s) for s in counts_by_sample.keys()]
        means = [stats.mean(v) if v else 0.0 for v in counts_by_sample.values()]
        stds = [stats.pstdev(v) if len(v) > 1 else 0.0 for v in counts_by_sample.values()]
        plt.figure(figsize=(8,4))
        plt.bar(labels, means, yerr=stds, color="#4C78A8", capsize=4)
        plt.title("Mean Kept Particle Count per Scan\nby Sample")
        plt.xlabel("Sample")
        plt.ylabel("Particles per map (mean +/- std)")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_particle_count_mean_by_sample.png", dpi=300)
        plt.close()

    if isolated_by_sample:
        labels = [short_label(s) for s in isolated_by_sample.keys()]
        means = [stats.mean(v) if v else 0.0 for v in isolated_by_sample.values()]
        stds = [stats.pstdev(v) if len(v) > 1 else 0.0 for v in isolated_by_sample.values()]
        plt.figure(figsize=(8,4))
        plt.bar(labels, means, yerr=stds, color="#54A24B", capsize=4)
        plt.title("Mean Isolated Particle Count per Scan\nby Sample")
        plt.xlabel("Sample")
        plt.ylabel("Isolated particles per map (mean +/- std)")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_isolated_count_mean_by_sample.png", dpi=300)
        plt.close()

    if counts_by_job:
        job_order = (args.job_order or []) or list(counts_by_job.keys())
        job_labels = [wrap_label(j, 18, 2) for j in job_order]
        means = [stats.mean(counts_by_job.get(j, [])) if counts_by_job.get(j) else 0.0 for j in job_order]
        stds = [stats.pstdev(counts_by_job.get(j, [])) if len(counts_by_job.get(j, [])) > 1 else 0.0 for j in job_order]
        plt.figure(figsize=(9,4))
        plt.bar(job_labels, means, yerr=stds, color="#72B7B2", capsize=4)
        plt.title("Mean Kept Particle Count per Scan\nby Job")
        plt.xlabel("Job")
        plt.ylabel("Particles per map (mean +/- std)")
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_particle_count_mean_by_job.png", dpi=300)
        plt.close()

    if isolated_by_job:
        job_order = (args.job_order or []) or list(isolated_by_job.keys())
        job_labels = [wrap_label(j, 18, 2) for j in job_order]
        means = [stats.mean(isolated_by_job.get(j, [])) if isolated_by_job.get(j) else 0.0 for j in job_order]
        stds = [stats.pstdev(isolated_by_job.get(j, [])) if len(isolated_by_job.get(j, [])) > 1 else 0.0 for j in job_order]
        plt.figure(figsize=(9,4))
        plt.bar(job_labels, means, yerr=stds, color="#59A14F", capsize=4)
        plt.title("Mean Isolated Particle Count per Scan\nby Job")
        plt.xlabel("Job")
        plt.ylabel("Isolated particles per map (mean +/- std)")
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_isolated_count_mean_by_job.png", dpi=300)
        plt.close()

    # Per-wt bar plots by job
    if counts_by_job_wt:
        out_dir = OUT_BASE / "summary_outputs" / "compare_by_wt"
        out_dir.mkdir(parents=True, exist_ok=True)
        wt_groups = sorted({wt for (_, wt) in counts_by_job_wt.keys()})
        for wt in wt_groups:
            jobs = args.job_order or sorted({job for (job, w) in counts_by_job_wt.keys() if w == wt})
            if not jobs:
                continue
            means = [stats.mean(counts_by_job_wt.get((job, wt), [])) if counts_by_job_wt.get((job, wt)) else 0.0 for job in jobs]
            stds = [stats.pstdev(counts_by_job_wt.get((job, wt), [])) if len(counts_by_job_wt.get((job, wt), [])) > 1 else 0.0 for job in jobs]
            labels = [wrap_label(j, 18, 2) for j in jobs]
            plt.figure(figsize=(9,4))
            plt.bar(labels, means, yerr=stds, color="#4C78A8", capsize=4)
            plt.title("Mean Kept Particle Count per Scan\nby Job (%s)" % wt)
            plt.xlabel("Job")
            plt.ylabel("Particles per scan (mean +/- std)")
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            plt.savefig(out_dir / ("fig_particle_count_mean_by_job_%s.png" % wt.replace("%","pct")), dpi=300)
            plt.close()

            iso_means = [stats.mean(isolated_by_job_wt.get((job, wt), [])) if isolated_by_job_wt.get((job, wt)) else 0.0 for job in jobs]
            iso_stds = [stats.pstdev(isolated_by_job_wt.get((job, wt), [])) if len(isolated_by_job_wt.get((job, wt), [])) > 1 else 0.0 for job in jobs]
            plt.figure(figsize=(9,4))
            plt.bar(labels, iso_means, yerr=iso_stds, color="#54A24B", capsize=4)
            plt.title("Mean Isolated Particle Count per Scan\nby Job (%s)" % wt)
            plt.xlabel("Job")
            plt.ylabel("Isolated particles per scan (mean +/- std)")
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            plt.savefig(out_dir / ("fig_isolated_count_mean_by_job_%s.png" % wt.replace("%","pct")), dpi=300)
            plt.close()

    # Per-job histograms (kept / raw / isolated)
    if counts_by_job or isolated_by_job:
        job_hist_dir = OUT_BASE / "summary_outputs" / "job_hists"
        job_hist_dir.mkdir(parents=True, exist_ok=True)
        for job, vals in counts_by_job.items():
            job_dir = job_hist_dir / job
            job_dir.mkdir(parents=True, exist_ok=True)
            _plot_hist(
                vals,
                "Kept Particle Count (pre-isolation) - %s" % job,
                "Particles per scan",
                job_dir / "hist_kept_counts.png",
                bins=20,
            )
            raw_vals = counts_raw_by_job.get(job, [])
            if raw_vals:
                _plot_hist(
                    raw_vals,
                    "Raw Particle Count (pre-filter) - %s" % job,
                    "Particles per scan",
                    job_dir / "hist_raw_counts.png",
                    bins=20,
                    color="#E45756",
                )
            iso_vals = isolated_by_job.get(job, [])
            if iso_vals:
                _plot_hist(
                    iso_vals,
                    "Isolated Particle Count - %s" % job,
                    "Isolated particles per scan",
                    job_dir / "hist_isolated_counts.png",
                    bins=20,
                    color="#54A24B",
                )

    # Grid count maps (per sample/job)
    if grid_counts and not getattr(args, "skip_grid_plots", False):
        import numpy as np
        import matplotlib.patches as patches

        area_um2 = float(SCAN_SIZE_UM[0] * SCAN_SIZE_UM[1])
        fixed_max_per_scan = float(args.grid_fixed_max)
        fixed_raw_max_per_scan = float(args.grid_fixed_max_raw)
        raw_job_re = re.compile(args.grid_raw_job_pattern, re.I)
        cmap = plt.cm.get_cmap(args.grid_cmap).copy()
        cmap.set_bad(color="lightgray")

        def _plot_grid(grid_raw, grid_density, zero_cells, title, out_path, vmax):
            masked = np.ma.masked_invalid(grid_density)
            plt.figure(figsize=(6, 5))
            ax = plt.gca()
            ax.imshow(masked, origin="lower", aspect="auto", cmap=cmap, vmin=0.0, vmax=vmax)
            ax.set_title(title)
            ax.set_xlabel("Col index")
            ax.set_ylabel("Row index")
            cbar = plt.colorbar(ax.images[0], ax=ax)
            cbar.set_label("Particles per um^2")

            # Annotate counts
            nrows, ncols = grid_raw.shape
            ax.set_xticks(list(range(ncols)))
            ax.set_yticks(list(range(nrows)))
            ax.set_xticklabels([str(i + 1) for i in range(ncols)], fontsize=6)
            ax.set_yticklabels([str(i + 1) for i in range(nrows)], fontsize=6)
            for r in range(nrows):
                for c in range(ncols):
                    val = grid_raw[r, c]
                    if np.isnan(val):
                        continue
                    ax.text(
                        c,
                        r,
                        str(int(val)),
                        ha="center",
                        va="center",
                        fontsize=6,
                        color="white",
                        bbox=dict(facecolor="black", alpha=0.6, edgecolor="none", boxstyle="round,pad=0.1"),
                    )

            # Outline zero-count cells (scans present but filtered to zero)
            for (rr, cc) in zero_cells:
                rect = patches.Rectangle(
                    (cc - 1 - 0.5, rr - 1 - 0.5),
                    1,
                    1,
                    linewidth=1.2,
                    edgecolor=args.grid_zero_outline_color,
                    facecolor="none",
                )
                ax.add_patch(rect)

            plt.tight_layout()
            plt.savefig(out_path, dpi=300)
            plt.close()

        def _plot_grid_metric(grid_metric, title, out_path, cbar_label, vmax=None, annotate=False, annotate_fmt="{:.2f}"):
            masked = np.ma.masked_invalid(grid_metric)
            plt.figure(figsize=(6, 5))
            ax = plt.gca()
            ax.imshow(masked, origin="lower", aspect="auto", cmap=cmap, vmin=0.0, vmax=vmax)
            ax.set_title(title)
            ax.set_xlabel("Col index")
            ax.set_ylabel("Row index")
            cbar = plt.colorbar(ax.images[0], ax=ax)
            cbar.set_label(cbar_label)
            nrows, ncols = grid_metric.shape
            ax.set_xticks(list(range(ncols)))
            ax.set_yticks(list(range(nrows)))
            ax.set_xticklabels([str(i + 1) for i in range(ncols)], fontsize=6)
            ax.set_yticklabels([str(i + 1) for i in range(nrows)], fontsize=6)
            if annotate:
                for r in range(nrows):
                    for c in range(ncols):
                        val = grid_metric[r, c]
                        if np.isnan(val):
                            continue
                        text = annotate_fmt.format(val)
                        ax.text(
                            c,
                            r,
                            text,
                            ha="center",
                            va="center",
                            fontsize=6,
                            color="white",
                            bbox=dict(facecolor="black", alpha=0.6, edgecolor="none", boxstyle="round,pad=0.1"),
                        )
            plt.tight_layout()
            plt.savefig(out_path, dpi=300)
            plt.close()

        for (system, sample, job), cells in grid_counts.items():
            if not cells:
                continue
            max_per_scan = fixed_raw_max_per_scan if raw_job_re.search(job) else fixed_max_per_scan
            vmax = max_per_scan / area_um2 if area_um2 else None
            max_r = max(r for r, _ in cells.keys())
            max_c = max(c for _, c in cells.keys())
            grid_raw = np.full((max_r, max_c), np.nan, dtype=float)
            grid_raw_iso = np.full((max_r, max_c), np.nan, dtype=float)
            grid_raw_unfiltered = None
            if (system, sample, job) in grid_raw_counts:
                grid_raw_unfiltered = np.full((max_r, max_c), np.nan, dtype=float)
            for (r, c), val in cells.items():
                grid_raw[r - 1, c - 1] = val
            for (r, c), val in grid_isolated.get((system, sample, job), {}).items():
                grid_raw_iso[r - 1, c - 1] = val
            if grid_raw_unfiltered is not None:
                for (r, c), val in grid_raw_counts.get((system, sample, job), {}).items():
                    grid_raw_unfiltered[r - 1, c - 1] = val
            grid_density = grid_raw / area_um2 if area_um2 else grid_raw
            grid_iso_density = grid_raw_iso / area_um2 if area_um2 else grid_raw_iso
            zero_cells = grid_zero.get((system, sample, job), set())
            iso_zero_cells = grid_iso_zero.get((system, sample, job), set())

            out_dir = OUT_BASE / system / sample / "summary_outputs"
            out_dir.mkdir(parents=True, exist_ok=True)

            _plot_grid(
                grid_raw,
                grid_density,
                zero_cells,
                "Kept Particle Density Grid\n(%s)" % job,
                out_dir / ("fig_particle_count_grid_%s.png" % job),
                vmax,
            )
            _plot_grid(
                grid_raw_iso,
                grid_iso_density,
                iso_zero_cells,
                "Isolated Particle Density Grid\n(%s)" % job,
                out_dir / ("fig_isolated_count_grid_%s.png" % job),
                vmax,
            )
            if grid_raw_unfiltered is not None:
                raw_vmax = fixed_raw_max_per_scan / area_um2 if area_um2 else None
                grid_raw_unfiltered_density = (
                    grid_raw_unfiltered / area_um2 if area_um2 else grid_raw_unfiltered
                )
                _plot_grid(
                    grid_raw_unfiltered,
                    grid_raw_unfiltered_density,
                    set(),
                    "Raw Particle Density Grid\n(%s)" % job,
                    out_dir / ("fig_particle_count_raw_grid_%s.png" % job),
                    raw_vmax,
                )

        # Combined grids per wt%
        if wt_grid_counts:
            combined_dir = OUT_BASE / "summary_outputs" / "combined"
            combined_dir.mkdir(parents=True, exist_ok=True)
            for (wt, job), cells in wt_grid_counts.items():
                if not cells:
                    continue
                max_per_scan = fixed_raw_max_per_scan if raw_job_re.search(job) else fixed_max_per_scan
                vmax = max_per_scan / area_um2 if area_um2 else None
                max_r = max(r for r, _ in cells.keys())
                max_c = max(c for _, c in cells.keys())
                grid_raw = np.full((max_r, max_c), np.nan, dtype=float)
                grid_raw_iso = np.full((max_r, max_c), np.nan, dtype=float)
                grid_std = np.full((max_r, max_c), np.nan, dtype=float)
                grid_std_iso = np.full((max_r, max_c), np.nan, dtype=float)
                grid_cv = np.full((max_r, max_c), np.nan, dtype=float)
                grid_cv_iso = np.full((max_r, max_c), np.nan, dtype=float)
                grid_se = np.full((max_r, max_c), np.nan, dtype=float)
                grid_se_iso = np.full((max_r, max_c), np.nan, dtype=float)
                grid_n = np.full((max_r, max_c), np.nan, dtype=float)
                grid_raw_unfiltered = None
                grid_raw_unfiltered_std = None
                grid_raw_unfiltered_cv = None
                grid_raw_unfiltered_se = None
                if wt_grid_raw_counts.get((wt, job)):
                    grid_raw_unfiltered = np.full((max_r, max_c), np.nan, dtype=float)
                    grid_raw_unfiltered_std = np.full((max_r, max_c), np.nan, dtype=float)
                    grid_raw_unfiltered_cv = np.full((max_r, max_c), np.nan, dtype=float)
                    grid_raw_unfiltered_se = np.full((max_r, max_c), np.nan, dtype=float)
                for (r, c), total in cells.items():
                    n = wt_grid_n.get((wt, job), {}).get((r, c), 1)
                    mean_val = total / float(n) if n else np.nan
                    sum_sq = wt_grid_counts_sq.get((wt, job), {}).get((r, c), 0.0)
                    var = max(0.0, (sum_sq / float(n)) - (mean_val * mean_val)) if n else np.nan
                    std_val = math.sqrt(var) if n else np.nan
                    cv_val = (std_val / mean_val) if n and mean_val > 0 else np.nan
                    se_val = (std_val / math.sqrt(float(n))) if n and n > 0 else np.nan
                    grid_raw[r - 1, c - 1] = mean_val
                    grid_std[r - 1, c - 1] = std_val
                    grid_cv[r - 1, c - 1] = cv_val
                    grid_se[r - 1, c - 1] = se_val
                    grid_n[r - 1, c - 1] = n
                for (r, c), total in wt_grid_isolated.get((wt, job), {}).items():
                    n = wt_grid_n.get((wt, job), {}).get((r, c), 1)
                    mean_val = total / float(n) if n else np.nan
                    sum_sq = wt_grid_isolated_sq.get((wt, job), {}).get((r, c), 0.0)
                    var = max(0.0, (sum_sq / float(n)) - (mean_val * mean_val)) if n else np.nan
                    std_val = math.sqrt(var) if n else np.nan
                    cv_val = (std_val / mean_val) if n and mean_val > 0 else np.nan
                    se_val = (std_val / math.sqrt(float(n))) if n and n > 0 else np.nan
                    grid_raw_iso[r - 1, c - 1] = mean_val
                    grid_std_iso[r - 1, c - 1] = std_val
                    grid_cv_iso[r - 1, c - 1] = cv_val
                    grid_se_iso[r - 1, c - 1] = se_val
                if grid_raw_unfiltered is not None:
                    for (r, c), total in wt_grid_raw_counts.get((wt, job), {}).items():
                        n = wt_grid_n.get((wt, job), {}).get((r, c), 1)
                        mean_val = total / float(n) if n else np.nan
                        sum_sq = wt_grid_raw_counts_sq.get((wt, job), {}).get((r, c), 0.0)
                        var = max(0.0, (sum_sq / float(n)) - (mean_val * mean_val)) if n else np.nan
                        std_val = math.sqrt(var) if n else np.nan
                        cv_val = (std_val / mean_val) if n and mean_val > 0 else np.nan
                        se_val = (std_val / math.sqrt(float(n))) if n and n > 0 else np.nan
                        grid_raw_unfiltered[r - 1, c - 1] = mean_val
                        grid_raw_unfiltered_std[r - 1, c - 1] = std_val
                        grid_raw_unfiltered_cv[r - 1, c - 1] = cv_val
                        grid_raw_unfiltered_se[r - 1, c - 1] = se_val
                grid_density = grid_raw / area_um2 if area_um2 else grid_raw
                grid_iso_density = grid_raw_iso / area_um2 if area_um2 else grid_raw_iso
                grid_std_density = grid_std / area_um2 if area_um2 else grid_std
                grid_iso_std_density = grid_std_iso / area_um2 if area_um2 else grid_std_iso
                grid_se_density = grid_se / area_um2 if area_um2 else grid_se
                grid_iso_se_density = grid_se_iso / area_um2 if area_um2 else grid_se_iso
                zero_cells = set()
                iso_zero_cells = set()

                _plot_grid(
                    grid_raw,
                    grid_density,
                    zero_cells,
                    "Mean Kept Particle Density Grid\n(wt%d%%, %s)" % (wt, job),
                    combined_dir / ("fig_particle_count_grid_wt%d_%s.png" % (wt, job)),
                    vmax,
                )
                _plot_grid(
                    grid_raw_iso,
                    grid_iso_density,
                    iso_zero_cells,
                    "Mean Isolated Density Grid\n(wt%d%%, %s)" % (wt, job),
                    combined_dir / ("fig_isolated_count_grid_wt%d_%s.png" % (wt, job)),
                    vmax,
                )
                std_vmax = float(np.nanmax(grid_std_density)) if np.any(~np.isnan(grid_std_density)) else None
                iso_std_vmax = float(np.nanmax(grid_iso_std_density)) if np.any(~np.isnan(grid_iso_std_density)) else None
                cv_vmax = float(np.nanmax(grid_cv)) if np.any(~np.isnan(grid_cv)) else None
                iso_cv_vmax = float(np.nanmax(grid_cv_iso)) if np.any(~np.isnan(grid_cv_iso)) else None
                se_vmax = float(np.nanmax(grid_se_density)) if np.any(~np.isnan(grid_se_density)) else None
                iso_se_vmax = float(np.nanmax(grid_iso_se_density)) if np.any(~np.isnan(grid_iso_se_density)) else None
                n_vmax = float(np.nanmax(grid_n)) if np.any(~np.isnan(grid_n)) else None

                _plot_grid_metric(
                    grid_std_density,
                    "Std Kept Particle Density Grid\n(wt%d%%, %s)" % (wt, job),
                    combined_dir / ("fig_particle_count_grid_std_wt%d_%s.png" % (wt, job)),
                    "Std particles per um^2",
                    vmax=std_vmax,
                )
                _plot_grid_metric(
                    grid_iso_std_density,
                    "Std Isolated Particle Density Grid\n(wt%d%%, %s)" % (wt, job),
                    combined_dir / ("fig_isolated_count_grid_std_wt%d_%s.png" % (wt, job)),
                    "Std isolated particles per um^2",
                    vmax=iso_std_vmax,
                )
                _plot_grid_metric(
                    grid_cv,
                    "CV Kept Particle Count Grid\n(wt%d%%, %s)" % (wt, job),
                    combined_dir / ("fig_particle_count_grid_cv_wt%d_%s.png" % (wt, job)),
                    "Coefficient of variation",
                    vmax=cv_vmax,
                )
                _plot_grid_metric(
                    grid_cv_iso,
                    "CV Isolated Particle Count Grid\n(wt%d%%, %s)" % (wt, job),
                    combined_dir / ("fig_isolated_count_grid_cv_wt%d_%s.png" % (wt, job)),
                    "Coefficient of variation",
                    vmax=iso_cv_vmax,
                )
                _plot_grid_metric(
                    grid_n,
                    "Contributing Sample Count Grid\n(wt%d%%, %s)" % (wt, job),
                    combined_dir / ("fig_particle_count_grid_n_wt%d_%s.png" % (wt, job)),
                    "Number of contributing samples",
                    vmax=n_vmax,
                    annotate=True,
                    annotate_fmt="{:.0f}",
                )
                _plot_grid_metric(
                    grid_se_density,
                    "SE Kept Particle Density Grid\n(wt%d%%, %s)" % (wt, job),
                    combined_dir / ("fig_particle_count_grid_se_wt%d_%s.png" % (wt, job)),
                    "SE particles per um^2",
                    vmax=se_vmax,
                )
                _plot_grid_metric(
                    grid_iso_se_density,
                    "SE Isolated Particle Density Grid\n(wt%d%%, %s)" % (wt, job),
                    combined_dir / ("fig_isolated_count_grid_se_wt%d_%s.png" % (wt, job)),
                    "SE isolated particles per um^2",
                    vmax=iso_se_vmax,
                )
                if grid_raw_unfiltered is not None:
                    raw_vmax = fixed_raw_max_per_scan / area_um2 if area_um2 else None
                    grid_raw_unfiltered_density = (
                        grid_raw_unfiltered / area_um2 if area_um2 else grid_raw_unfiltered
                    )
                    _plot_grid(
                        grid_raw_unfiltered,
                        grid_raw_unfiltered_density,
                        set(),
                        "Mean Raw Particle Density Grid\n(wt%d%%, %s)" % (wt, job),
                        combined_dir / ("fig_particle_count_raw_grid_wt%d_%s.png" % (wt, job)),
                        raw_vmax,
                    )
                    raw_std_density = (
                        grid_raw_unfiltered_std / area_um2 if area_um2 else grid_raw_unfiltered_std
                    )
                    raw_se_density = (
                        grid_raw_unfiltered_se / area_um2 if area_um2 else grid_raw_unfiltered_se
                    )
                    raw_std_vmax = float(np.nanmax(raw_std_density)) if np.any(~np.isnan(raw_std_density)) else None
                    raw_cv_vmax = float(np.nanmax(grid_raw_unfiltered_cv)) if np.any(~np.isnan(grid_raw_unfiltered_cv)) else None
                    raw_se_vmax = float(np.nanmax(raw_se_density)) if np.any(~np.isnan(raw_se_density)) else None
                    _plot_grid_metric(
                        raw_std_density,
                        "Std Raw Particle Density Grid\n(wt%d%%, %s)" % (wt, job),
                        combined_dir / ("fig_particle_count_raw_grid_std_wt%d_%s.png" % (wt, job)),
                        "Std particles per um^2",
                        vmax=raw_std_vmax,
                    )
                    _plot_grid_metric(
                        grid_raw_unfiltered_cv,
                        "CV Raw Particle Count Grid\n(wt%d%%, %s)" % (wt, job),
                        combined_dir / ("fig_particle_count_raw_grid_cv_wt%d_%s.png" % (wt, job)),
                        "Coefficient of variation",
                        vmax=raw_cv_vmax,
                    )
                    _plot_grid_metric(
                        raw_se_density,
                        "SE Raw Particle Density Grid\n(wt%d%%, %s)" % (wt, job),
                        combined_dir / ("fig_particle_count_raw_grid_se_wt%d_%s.png" % (wt, job)),
                        "SE particles per um^2",
                        vmax=raw_se_vmax,
                    )

    per_sample_rows = []
    for sample, sample_counts in counts_by_sample.items():
        sample_isolated = isolated_by_sample.get(sample, [])
        sample_diam = diameters_by_sample.get(sample, [])
        system = sample_system.get(sample, "unknown")
        out_dir = OUT_BASE / system / sample / "summary_outputs"
        out_dir.mkdir(parents=True, exist_ok=True)

        row = {
            "sample": sample,
            "system": system,
            "maps": len(sample_counts),
            "total_particles": sum(sample_counts),
            "mean_per_map": stats.mean(sample_counts) if sample_counts else 0.0,
            "std_per_map": stats.pstdev(sample_counts) if len(sample_counts) > 1 else 0.0,
            "min_per_map": min(sample_counts) if sample_counts else 0,
            "max_per_map": max(sample_counts) if sample_counts else 0,
            "mean_isolated_per_map": stats.mean(sample_isolated) if sample_isolated else 0.0,
            "std_isolated_per_map": stats.pstdev(sample_isolated) if len(sample_isolated) > 1 else 0.0,
            "percent_maps_with_isolated": (
                100.0 * sum(1 for v in sample_isolated if v > 0) / float(len(sample_isolated))
                if sample_isolated else 0.0
            ),
            "mean_diameter_nm": stats.mean(sample_diam) if sample_diam else 0.0,
            "std_diameter_nm": stats.pstdev(sample_diam) if len(sample_diam) > 1 else 0.0,
        }
        per_sample_rows.append(row)

        if sample_counts:
            plt.figure(figsize=(6,4))
            plt.hist(sample_counts, bins=20, color="#4C78A8", edgecolor="black")
            plt.title("Particle Count per Map")
            plt.xlabel("Particles per map")
            plt.ylabel("Frequency")
            plt.tight_layout()
            plt.savefig(out_dir / "fig_particle_count_hist.png", dpi=300)
            plt.close()

            plt.figure(figsize=(7,4))
            plt.scatter(range(1, len(sample_counts) + 1), sample_counts, s=12, color="#4C78A8", alpha=0.8)
            plt.title("Particle Count per Map (index order)")
            plt.xlabel("Map index")
            plt.ylabel("Particles per map")
            plt.tight_layout()
            plt.savefig(out_dir / "fig_particle_count_scatter.png", dpi=300)
            plt.close()

        if sample_isolated:
            plt.figure(figsize=(6,4))
            plt.hist(sample_isolated, bins=20, color="#54A24B", edgecolor="black")
            plt.title("Isolated Particle Count per Map")
            plt.xlabel("Isolated particles per map")
            plt.ylabel("Frequency")
            plt.tight_layout()
            plt.savefig(out_dir / "fig_isolated_count_hist.png", dpi=300)
            plt.close()

            plt.figure(figsize=(7,4))
            plt.scatter(range(1, len(sample_isolated) + 1), sample_isolated, s=12, color="#54A24B", alpha=0.8)
            plt.title("Isolated Particle Count per Map (index order)")
            plt.xlabel("Map index")
            plt.ylabel("Isolated particles per map")
            plt.tight_layout()
            plt.savefig(out_dir / "fig_isolated_count_scatter.png", dpi=300)
            plt.close()

        if sample_diam:
            plt.figure(figsize=(6,4))
            plt.hist(sample_diam, bins=30, color="#F58518", edgecolor="black")
            plt.title("Particle Diameter Distribution (filtered)")
            plt.xlabel("Diameter (nm)")
            plt.ylabel("Frequency")
            plt.tight_layout()
            plt.savefig(out_dir / "fig_particle_diameter_hist.png", dpi=300)
            plt.close()

    if per_sample_rows:
        write_csv(OUT_BASE / "particle_summary_stats_by_sample.csv", per_sample_rows, list(per_sample_rows[0].keys()))

    # Per-job summary table
    per_job_rows = []
    for job, job_counts in counts_by_job.items():
        job_isolated = isolated_by_job.get(job, [])
        job_diam = diameters_by_job.get(job, [])
        job_raw = counts_raw_by_job.get(job, [])
        job_filtered = counts_filtered_by_job.get(job, [])
        per_job_rows.append({
            "job": job,
            "maps": len(job_counts),
            "total_particles": sum(job_counts),
            "mean_per_map": stats.mean(job_counts) if job_counts else 0.0,
            "std_per_map": stats.pstdev(job_counts) if len(job_counts) > 1 else 0.0,
            "raw_mean_per_map": stats.mean(job_raw) if job_raw else 0.0,
            "raw_std_per_map": stats.pstdev(job_raw) if len(job_raw) > 1 else 0.0,
            "filtered_mean_per_map": stats.mean(job_filtered) if job_filtered else 0.0,
            "filtered_std_per_map": stats.pstdev(job_filtered) if len(job_filtered) > 1 else 0.0,
            "mean_isolated_per_map": stats.mean(job_isolated) if job_isolated else 0.0,
            "std_isolated_per_map": stats.pstdev(job_isolated) if len(job_isolated) > 1 else 0.0,
            "percent_maps_with_isolated": (
                100.0 * sum(1 for v in job_isolated if v > 0) / float(len(job_isolated))
                if job_isolated else 0.0
            ),
            "mean_diameter_nm": stats.mean(job_diam) if job_diam else 0.0,
            "std_diameter_nm": stats.pstdev(job_diam) if len(job_diam) > 1 else 0.0,
        })
    if per_job_rows:
        write_csv(OUT_BASE / "particle_summary_stats_by_job.csv", per_job_rows, list(per_job_rows[0].keys()))

    # ---- Grain summary (from *_grains.csv) ----
    grain_rows = []
    for p in find_grain_csvs():
        for row in read_grain_rows(p):
            row["source_csv"] = str(p)
            row["sample"] = sample_from_grain_path(p)
            row["system"] = system_from_grain_path(p)
            row["job"] = job_from_grain_path(p)
            grain_rows.append(row)

    if grain_rows:
        numeric_fields = grain_numeric_fields(grain_rows)
        if numeric_fields:
            # Group by job
            rows_by_job = {}
            rows_by_sample_job = {}
            for row in grain_rows:
                job = row.get("job", "unknown")
                sample = row.get("sample", "unknown")
                rows_by_job.setdefault(job, []).append(row)
                rows_by_sample_job.setdefault((sample, job), []).append(row)

            def build_grain_summary(rows, include_keys):
                kept_vals = {f: [] for f in numeric_fields}
                iso_vals = {f: [] for f in numeric_fields}
                all_vals = {f: [] for f in numeric_fields}
                kept_count = 0
                iso_count = 0
                edge_excluded = 0
                for r in rows:
                    kept = to_int(r.get("kept", 0)) == 1
                    iso = to_int(r.get("isolated", 0)) == 1
                    edge = to_int(r.get("edge_excluded", 0)) == 1
                    if edge:
                        edge_excluded += 1
                    for f in numeric_fields:
                        v = to_float_or_none(r.get(f))
                        if v is None:
                            continue
                        all_vals[f].append(v)
                        if kept:
                            kept_vals[f].append(v)
                        if iso:
                            iso_vals[f].append(v)
                    if kept:
                        kept_count += 1
                    if iso:
                        iso_count += 1
                out = dict(include_keys)
                out["grain_total"] = len(rows)
                out["grain_kept"] = kept_count
                out["grain_isolated"] = iso_count
                out["grain_edge_excluded"] = edge_excluded
                for f in numeric_fields:
                    s_all = summarize_numeric(all_vals[f])
                    s_kept = summarize_numeric(kept_vals[f])
                    s_iso = summarize_numeric(iso_vals[f])
                    out["all_mean_%s" % f] = s_all["mean"]
                    out["all_median_%s" % f] = s_all["median"]
                    out["all_std_%s" % f] = s_all["std"]
                    out["kept_mean_%s" % f] = s_kept["mean"]
                    out["kept_median_%s" % f] = s_kept["median"]
                    out["kept_std_%s" % f] = s_kept["std"]
                    out["isolated_mean_%s" % f] = s_iso["mean"]
                    out["isolated_median_%s" % f] = s_iso["median"]
                    out["isolated_std_%s" % f] = s_iso["std"]
                return out

            job_rows = []
            for job, rows in rows_by_job.items():
                job_rows.append(build_grain_summary(rows, {"job": job}))
            if job_rows:
                write_csv(OUT_BASE / "grain_summary_by_job.csv", job_rows, list(job_rows[0].keys()))

            sample_job_rows = []
            for (sample, job), rows in rows_by_sample_job.items():
                sample_job_rows.append(build_grain_summary(rows, {"sample": sample, "job": job}))
            if sample_job_rows:
                write_csv(OUT_BASE / "grain_summary_by_sample_job.csv", sample_job_rows, list(sample_job_rows[0].keys()))

            # Per-grain plots (by job) for key fields if available.
            if not getattr(args, "skip_grain_hist_plots", False):
                plots_dir = OUT_BASE / "grain_plots"
                plots_dir.mkdir(parents=True, exist_ok=True)
                key_fields = []
                for f in ("diameter_nm", "area_px", "grain_projected_area", "grain_surface_area"):
                    if f in numeric_fields:
                        key_fields.append(f)
                if not key_fields:
                    key_fields = numeric_fields[:2]

                for job, rows in rows_by_job.items():
                    job_dir = plots_dir / job
                    job_dir.mkdir(parents=True, exist_ok=True)
                    for field_name in key_fields:
                        vals_all = []
                        vals_kept = []
                        vals_iso = []
                        for r in rows:
                            v = to_float_or_none(r.get(field_name))
                            if v is None:
                                continue
                            vals_all.append(v)
                            if to_int(r.get("kept", 0)) == 1:
                                vals_kept.append(v)
                            if to_int(r.get("isolated", 0)) == 1:
                                vals_iso.append(v)
                        _plot_hist(
                            vals_all,
                            "Grain %s (all) - %s" % (field_name, job),
                            field_name,
                            job_dir / ("grain_%s_all.png" % field_name),
                        )
                        _plot_hist(
                            vals_kept,
                            "Grain %s (kept) - %s" % (field_name, job),
                            field_name,
                            job_dir / ("grain_%s_kept.png" % field_name),
                            color="#F58518",
                        )
                        _plot_hist(
                            vals_iso,
                            "Grain %s (isolated) - %s" % (field_name, job),
                            field_name,
                            job_dir / ("grain_%s_isolated.png" % field_name),
                            color="#54A24B",
                        )

            # Cross-method grain trends (diameter) across jobs (and by wt% if available).
            if "diameter_nm" in numeric_fields and not getattr(args, "skip_grain_trend_plots", False):
                trend_dir = OUT_BASE / "summary_outputs" / "grain_compare"
                trend_dir.mkdir(parents=True, exist_ok=True)

                def _job_vals(rows, which):
                    vals = []
                    for r in rows:
                        if which == "kept" and to_int(r.get("kept", 0)) != 1:
                            continue
                        if which == "isolated" and to_int(r.get("isolated", 0)) != 1:
                            continue
                        v = to_float_or_none(r.get("diameter_nm"))
                        if v is None:
                            continue
                        vals.append(v)
                    return vals

                def _bar_with_error(values_by_job, out_path, title, ylabel):
                    jobs = list(values_by_job.keys())
                    labels = [wrap_label(j, 18, 2) for j in jobs]
                    means = [stats.mean(values_by_job[j]) if values_by_job[j] else 0.0 for j in jobs]
                    stds = [stats.pstdev(values_by_job[j]) if len(values_by_job[j]) > 1 else 0.0 for j in jobs]
                    plt.figure(figsize=(10, 4))
                    plt.bar(labels, means, yerr=stds, color="#4C78A8", capsize=4)
                    plt.title(title)
                    plt.xlabel("Job")
                    plt.ylabel(ylabel)
                    plt.xticks(rotation=30, ha="right")
                    plt.tight_layout()
                    plt.savefig(out_path, dpi=300)
                    plt.close()

                def _boxplot(values_by_job, out_path, title, ylabel):
                    jobs = list(values_by_job.keys())
                    labels = [wrap_label(j, 18, 2) for j in jobs]
                    data = [values_by_job[j] for j in jobs]
                    plt.figure(figsize=(10, 4))
                    plt.boxplot(data, labels=labels, showfliers=True)
                    plt.title(title)
                    plt.xlabel("Job")
                    plt.ylabel(ylabel)
                    plt.xticks(rotation=30, ha="right")
                    plt.tight_layout()
                    plt.savefig(out_path, dpi=300)
                    plt.close()

                job_order = args.job_order or sorted(rows_by_job.keys())
                kept_by_job = {j: _job_vals(rows_by_job.get(j, []), "kept") for j in job_order}
                iso_by_job = {j: _job_vals(rows_by_job.get(j, []), "isolated") for j in job_order}
                kept_by_job = {j: v for j, v in kept_by_job.items() if v}
                iso_by_job = {j: v for j, v in iso_by_job.items() if v}

                if kept_by_job:
                    _bar_with_error(
                        kept_by_job,
                        trend_dir / "fig_grain_diameter_nm_kept_mean_by_job.png",
                        "Mean Grain Diameter (kept)\nby Job",
                        "Diameter (nm, mean +/- std)",
                    )
                    _boxplot(
                        kept_by_job,
                        trend_dir / "fig_grain_diameter_nm_kept_box_by_job.png",
                        "Grain Diameter Distribution (kept)\nby Job",
                        "Diameter (nm)",
                    )
                if iso_by_job:
                    _bar_with_error(
                        iso_by_job,
                        trend_dir / "fig_grain_diameter_nm_isolated_mean_by_job.png",
                        "Mean Grain Diameter (isolated)\nby Job",
                        "Diameter (nm, mean +/- std)",
                    )
                    _boxplot(
                        iso_by_job,
                        trend_dir / "fig_grain_diameter_nm_isolated_box_by_job.png",
                        "Grain Diameter Distribution (isolated)\nby Job",
                        "Diameter (nm)",
                    )

    feas = ""
    if iso_stats and iso_stats.get("mean_isolated_per_map"):
        mean_iso = iso_stats.get("mean_isolated_per_map")
        maps_needed = math.ceil(TARGET_ISOLATED / float(mean_iso)) if mean_iso > 0 else None
        if maps_needed:
            feas = (
                "Based on the current Stage 1 dataset, approximately %d maps are required "
                "to obtain ~%d isolated particles (rule-of-thumb target for stable statistics), "
                "using the observed mean isolated count per map." % (maps_needed, TARGET_ISOLATED)
            )
    if feas:
        (OUT_BASE / "feasibility_statement.txt").write_text(feas, encoding="utf-8")

    print("Summary written to", OUT_BASE)


if __name__ == "__main__":
    main()
