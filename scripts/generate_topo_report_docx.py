import csv
import math
import re
import statistics as stats
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Inches

OUT_BASE = Path(r"C:\Users\Conor O'Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT")
REPORT_PATH = OUT_BASE / "topo_particle_report_draft.docx"
DATA_GROUPED = Path("docs/File Locations for Data Grouped.txt")

BASELINE_JOB = "particle_forward_medianbg_mean"
SYSTEM_SINP = "PEGDA_SiNP"
TARGET_ISOLATED = 30
ISOLATION_DIST_NM = 900.0
DIAMETER_FILTER_NM = "400-500 nm (current comparison runs)"


def read_csv_dicts(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    for idx, header in enumerate(headers):
        hdr_cells[idx].text = header
    for row in rows:
        cells = table.add_row().cells
        for idx, val in enumerate(row):
            cells[idx].text = str(val)
    return table


def add_picture_if_exists(doc, path, width_in=5.5):
    if path.exists():
        doc.add_picture(str(path), width=Inches(width_in))
        return True
    doc.add_paragraph(f"(Missing figure: {path.name})")
    return False


def parse_data_grouped(path):
    groups = []
    current_system = None
    current_label = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# PEGDA Only"):
            current_system = "PEGDA"
            current_label = None
            continue
        if line.startswith("# PEGDA SiNP"):
            current_system = "PEGDA_SiNP"
            current_label = None
            continue
        if line.startswith("#"):
            continue
        if line.startswith("## "):
            current_label = line[3:].strip()
            groups.append({"system": current_system, "label": current_label, "roots": []})
            continue
        if line.startswith("C:\\") and groups:
            groups[-1]["roots"].append(line)
    return groups


def _norm_key(value):
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def build_sample_group_map(groups):
    mapping = {}
    norm_map = {}
    order = []
    for g in groups:
        label = g["label"]
        order.append(label)
        for root in g["roots"]:
            sample = Path(root).name
            mapping[sample] = g
            norm = _norm_key(sample)
            if norm:
                norm_map[norm] = g
            stripped = sample.rstrip("-_ ")
            if stripped and stripped not in mapping:
                mapping[stripped] = g
                norm_map[_norm_key(stripped)] = g
    return mapping, norm_map, order


def classify_sample(sample, mapping, norm_map):
    if sample in mapping:
        return mapping[sample], "exact"
    norm = _norm_key(sample)
    if norm in norm_map:
        return norm_map[norm], "normalized"
    best = None
    best_len = 0
    for norm_key, grp in norm_map.items():
        if not norm_key:
            continue
        if norm_key in norm or norm in norm_key:
            if len(norm_key) > best_len:
                best_len = len(norm_key)
                best = grp
    return best, "fuzzy" if best else (None, None)


def parse_scan_id(source_file):
    m = re.search(r"LOC_RC(?P<row>\d{3})(?P<col>\d{3})", source_file)
    if not m:
        return Path(source_file).stem
    return "R{}-C{}".format(m.group("row"), m.group("col"))


def wt_percent_from_label(label):
    if not label:
        return ""
    m = re.search(r"(10|25)%", label)
    return f"{m.group(1)}%" if m else ""


def wt_percent_from_sample(sample):
    if not sample:
        return ""
    m = re.search(r"tpo(10|25)sinp", sample, re.I)
    return f"{m.group(1)}%" if m else ""


def scraped_status_from_label(label):
    if not label:
        return ""
    if re.search(r"\bnon[- ]scraped\b", label, re.I):
        return "Non Scraped"
    if re.search(r"\bscraped\b", label, re.I):
        return "Scraped"
    return ""


def _find_plot_paths(input_bases, system, sample, job):
    bases = input_bases or [OUT_BASE]
    for base in bases:
        plot_dir = base / system / sample / "summary_outputs"
        count_plot = plot_dir / f"fig_particle_count_grid_{job}.png"
        iso_plot = plot_dir / f"fig_isolated_count_grid_{job}.png"
        if count_plot.exists() or iso_plot.exists():
            return count_plot, iso_plot
    return None, None


def parse_args():
    import argparse
    ap = argparse.ArgumentParser(description="Generate topo particle Word report.")
    ap.add_argument("--out-base", default="", help="Override output base directory.")
    ap.add_argument("--out-base-list", default="", help="Semicolon-separated input roots for a combined report.")
    ap.add_argument("--report-path", default="", help="Override report output path.")
    return ap.parse_args()


def main():
    args = parse_args()
    global OUT_BASE, REPORT_PATH
    input_bases = []
    if args.out_base_list:
        input_bases = [Path(p.strip()) for p in args.out_base_list.split(";") if p.strip()]
    if args.out_base:
        OUT_BASE = Path(args.out_base)
    elif input_bases:
        OUT_BASE = input_bases[0]
    if args.report_path:
        REPORT_PATH = Path(args.report_path)
    else:
        REPORT_PATH = OUT_BASE / "topo_particle_report_draft.docx"

    doc = Document()

    doc.add_heading("Topo Particle Summary Report (Draft)", level=0)
    doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if input_bases:
        doc.add_paragraph("Output roots:")
        for base in input_bases:
            doc.add_paragraph(str(base), style="List Bullet")
    else:
        doc.add_paragraph(f"Output root: {OUT_BASE}")
    doc.add_paragraph(f"Baseline job: {BASELINE_JOB}")
    doc.add_paragraph("Map/grid area: 50 um x 50 um (21 x 21 grid, 5% overlap per scan)")
    if DATA_GROUPED.exists():
        doc.add_paragraph(f"Grouping source: {DATA_GROUPED}")

    doc.add_heading("Definitions and Processing Types", level=1)
    doc.add_paragraph(
        "Map = the full 50 um x 50 um grid footprint for a sample (21 x 21 scan positions). "
        "Scan = a single 5 um x 5 um AFM image at one grid index (Row/Col)."
    )
    doc.add_paragraph(
        "Baseline processing (per scan): alignment/row correction, background leveling (median), "
        "particle detection with mean-threshold mask, edge exclusion, diameter filter, and "
        "isolation filter based on center-to-center distance."
    )
    doc.add_paragraph(
        "Grid plots: missing scans are shown in gray; scans that exist but were filtered to zero "
        "particles are outlined in yellow; numbers overlay the raw particle count per scan."
    )

    doc.add_heading("1. Scan Inventory", level=1)
    inv_rows = read_csv_dicts(OUT_BASE / "scan_inventory.csv")
    groups = parse_data_grouped(DATA_GROUPED) if DATA_GROUPED.exists() else []
    sample_to_group, norm_group_map, group_order = build_sample_group_map(groups) if groups else ({}, {}, [])
    inv_by_root = {}
    inv_by_root_norm = {}
    inv_jsons = []
    if input_bases:
        inv_jsons = [b / "scan_inventory.json" for b in input_bases]
    else:
        inv_jsons = [OUT_BASE / "scan_inventory.json"]
    for inv_json in inv_jsons:
        if not inv_json.exists():
            continue
        try:
            import json
            for r in json.loads(inv_json.read_text(encoding="utf-8")):
                root = r.get("input_root")
                if root:
                    inv_by_root[root] = r
                    inv_by_root_norm[_norm_key(root)] = r
        except Exception:
            pass

    if inv_rows:
        headers = [
            "System",
            "SiNP wt%",
            "Scraped?",
            "Group",
            "Total scans",
            "Scan size (um x um)",
            "Pixel grid",
            "Resolution (nm/px)",
        ]
        rows = []
        if groups and inv_by_root:
            for g in groups:
                sys_name = g.get("system") or ""
                label = g.get("label") or ""
                wt = wt_percent_from_label(label)
                scraped = scraped_status_from_label(label)
                total = 0
                for root in g.get("roots") or []:
                    rec = inv_by_root.get(root) or inv_by_root_norm.get(_norm_key(root))
                    if rec:
                        total += int(rec.get("map_count", 0))
                total_display = total if total > 0 else "0 (not processed)"
                rows.append([
                    "PEGDA" if sys_name == "PEGDA" else "PEGDA-SiNP",
                    wt,
                    scraped,
                    label,
                    total_display,
                    "5 x 5",
                    "512 x 512",
                    "9.7656",
                ])
        else:
            for row in inv_rows:
                rows.append([
                    row.get("system", ""),
                    "",
                    "",
                    "All",
                    row.get("total_maps", ""),
                    f"{row.get('scan_um_x','')} x {row.get('scan_um_y','')}",
                    f"{row.get('grid_x','')} x {row.get('grid_y','')}",
                    row.get("resolution_nm_per_px", ""),
                ])
        add_table(doc, headers, rows)
    else:
        doc.add_paragraph("scan_inventory.csv not found.")

    doc.add_heading("2. Particle Count Data (PEGDA-SiNP)", level=1)
    count_rows = []
    if input_bases:
        for base in input_bases:
            count_rows.extend(read_csv_dicts(base / "particle_counts_by_map.csv"))
    else:
        count_rows = read_csv_dicts(OUT_BASE / "particle_counts_by_map.csv")
    base_rows = [
        r for r in count_rows
        if r.get("job") == BASELINE_JOB and r.get("system") == SYSTEM_SINP
    ]
    if base_rows:
        counts = [int(float(r.get("count_total", 0) or 0)) for r in base_rows]
        isolated = [int(float(r.get("count_isolated", 0) or 0)) for r in base_rows]
        total_particles = sum(counts)
        mean_counts = stats.mean(counts)
        std_counts = stats.pstdev(counts) if len(counts) > 1 else 0.0
        min_counts = min(counts)
        max_counts = max(counts)
        mean_iso = stats.mean(isolated)
        std_iso = stats.pstdev(isolated) if len(isolated) > 1 else 0.0
        pct_iso = 100.0 * sum(1 for v in isolated if v > 0) / float(len(isolated))

        doc.add_paragraph("Aggregate (baseline job)")
        add_table(
            doc,
            ["Metric", "Value"],
            [
                ["Total particles detected", total_particles],
                ["Mean particles per scan", f"{mean_counts:.3f}"],
                ["Std. dev. particles per scan", f"{std_counts:.3f}"],
                ["Min particles per scan", min_counts],
                ["Max particles per scan", max_counts],
                ["Mean isolated particles per scan", f"{mean_iso:.3f}"],
                ["Std. dev. isolated particles per scan", f"{std_iso:.3f}"],
                ["% scans with >= 1 isolated particle", f"{pct_iso:.3f}"],
            ],
        )

        doc.add_paragraph("Per-scan particle counts (baseline job), grouped by SiNP wt% and scraped status.")
        sinp_group_order = [g["label"] for g in groups if g.get("system") == SYSTEM_SINP] if groups else []
        rows_by_group = {label: [] for label in sinp_group_order} if sinp_group_order else {}
        unclassified = set()
        for r in base_rows:
            sample = r.get("sample", "")
            group, _match_mode = classify_sample(sample, sample_to_group, norm_group_map)
            label = group.get("label", "Unclassified") if group else "Unclassified"
            wt = wt_percent_from_label(label) or wt_percent_from_sample(sample) or "Unknown"
            scan_id = parse_scan_id(r.get("source_file", ""))
            if label == "Unclassified":
                unclassified.add(sample)
            rows_by_group.setdefault(label, []).append([
                wt,
                label,
                sample,
                scan_id,
                r.get("count_total", ""),
                r.get("count_isolated", ""),
            ])

        order = sinp_group_order or sorted(rows_by_group.keys())
        for label in order:
            group_rows = rows_by_group.get(label) or []
            if not group_rows:
                continue
            doc.add_heading(label, level=3)
            add_table(
                doc,
                ["SiNP wt%", "Group", "Sample", "Scan ID", "Particles (Total)", "Particles (Isolated)"],
                group_rows,
            )
            # Embed grid plots if available (per sample)
            samples = sorted({r[2] for r in group_rows})
            for sample in samples:
                count_plot, iso_plot = _find_plot_paths(input_bases, SYSTEM_SINP, sample, BASELINE_JOB)
                if (count_plot and count_plot.exists()) or (iso_plot and iso_plot.exists()):
                    doc.add_paragraph(
                        f"Grid density maps for {sample} ({BASELINE_JOB}); "
                        "counts are normalized per scan area (particles/um^2) with fixed color range "
                        "equivalent to 0-12 particles per scan."
                    )
                    if count_plot:
                        add_picture_if_exists(doc, count_plot)
                    if iso_plot:
                        add_picture_if_exists(doc, iso_plot)
        if unclassified:
            doc.add_paragraph("Unclassified samples (did not match grouped file list):")
            for sample in sorted(unclassified):
                doc.add_paragraph(sample, style="List Bullet")
    else:
        doc.add_paragraph("No baseline rows found in particle_counts_by_map.csv.")

    doc.add_heading("3. Particle Size Distribution", level=1)
    stats_rows = []
    if input_bases:
        for base in input_bases:
            stats_rows.extend(read_csv_dicts(base / "particle_summary_stats.csv"))
    else:
        stats_rows = read_csv_dicts(OUT_BASE / "particle_summary_stats.csv")
    mean_d = next((r["value"] for r in stats_rows if r.get("metric") == "mean_diameter_nm"), None)
    std_d = next((r["value"] for r in stats_rows if r.get("metric") == "std_diameter_nm"), None)
    add_table(
        doc,
        ["Metric", "Value"],
        [
            ["Mean particle diameter (nm)", mean_d or "n/a"],
            ["Std. dev. particle diameter (nm)", std_d or "n/a"],
            ["Diameter filter", DIAMETER_FILTER_NM],
        ],
    )
    doc.add_paragraph(
        "Note: diameter stats are based on available per-particle exports; the baseline job may not export per-particle CSVs."
    )
    add_picture_if_exists(doc, OUT_BASE / "fig_particle_diameter_hist.png")

    doc.add_heading("4. Isolation Criteria", level=1)
    add_table(
        doc,
        ["Metric", "Value"],
        [
            ["Isolation definition (center-to-center)", f">= {ISOLATION_DIST_NM} nm"],
        ],
    )
    add_picture_if_exists(doc, OUT_BASE / "fig_isolated_count_hist.png")

    doc.add_heading("5. Method Comparison", level=1)
    by_job = []
    if input_bases:
        for base in input_bases:
            by_job.extend(read_csv_dicts(base / "particle_summary_stats_by_job.csv"))
    else:
        by_job = read_csv_dicts(OUT_BASE / "particle_summary_stats_by_job.csv")
    job_order = [
        "particle_forward_medianbg_mean",
        "particle_forward_medianbg_fixed0",
        "particle_forward_medianbg_p95",
        "particle_forward_medianbg_max_fixed0_p95",
        "particle_forward_flatten_mean",
        "particle_forward_flatten_fixed0",
        "particle_forward_flatten_p95",
        "particle_forward_flatten_max_fixed0_p95",
    ]
    job_rows = []
    by_job_map = {r.get("job"): r for r in by_job}
    for job in job_order:
        r = by_job_map.get(job)
        if not r:
            continue
        job_rows.append([
            job,
            r.get("mean_per_map", ""),
            r.get("std_per_map", ""),
            r.get("mean_isolated_per_map", ""),
            r.get("std_isolated_per_map", ""),
            r.get("percent_maps_with_isolated", ""),
        ])
    add_table(
        doc,
        ["Job", "Mean/Scan", "Std/Scan", "Mean Isolated/Scan", "Std Isolated/Scan", "% Scans w/ Iso"],
        job_rows,
    )
    add_picture_if_exists(doc, OUT_BASE / "fig_particle_count_mean_by_job.png")
    add_picture_if_exists(doc, OUT_BASE / "fig_isolated_count_mean_by_job.png")

    doc.add_heading("6. Grain Summary (Selected Fields)", level=1)
    grain_rows = []
    if input_bases:
        for base in input_bases:
            grain_rows.extend(read_csv_dicts(base / "grain_summary_by_job.csv"))
    else:
        grain_rows = read_csv_dicts(OUT_BASE / "grain_summary_by_job.csv")
    grain_map = {r.get("job"): r for r in grain_rows}
    grain_table_rows = []
    for job in job_order:
        r = grain_map.get(job)
        if not r:
            continue
        grain_table_rows.append([
            job,
            r.get("grain_total", ""),
            r.get("grain_kept", ""),
            r.get("grain_isolated", ""),
            r.get("kept_mean_diameter_nm", ""),
            r.get("kept_std_diameter_nm", ""),
            r.get("isolated_mean_diameter_nm", ""),
            r.get("isolated_std_diameter_nm", ""),
        ])
    add_table(
        doc,
        [
            "Job",
            "Grain Total",
            "Grain Kept",
            "Grain Isolated",
            "Kept Mean Diam (nm)",
            "Kept Std Diam (nm)",
            "Isolated Mean Diam (nm)",
            "Isolated Std Diam (nm)",
        ],
        grain_table_rows,
    )

    doc.add_heading("7. Statistical Feasibility Statement", level=1)
    if base_rows:
        by_group = {}
        for r in base_rows:
            sample = r.get("sample", "")
            group, _match_mode = classify_sample(sample, sample_to_group, norm_group_map)
            label = group.get("label", "Unclassified") if group else "Unclassified"
            wt = wt_percent_from_label(label) or wt_percent_from_sample(sample) or "Unknown"
            by_group.setdefault(wt, []).append(int(float(r.get("count_isolated", 0) or 0)))
        feas_rows = []
        for wt, vals in sorted(by_group.items()):
            mean_iso = stats.mean(vals) if vals else 0.0
            std_iso = stats.pstdev(vals) if len(vals) > 1 else 0.0
            scans_needed = math.ceil(TARGET_ISOLATED / mean_iso) if mean_iso > 0 else None
            if scans_needed:
                expected_total = mean_iso * scans_needed
                std_total = std_iso * math.sqrt(scans_needed)
                scans_needed_disp = str(scans_needed)
                expected_disp = f"{expected_total:.1f}"
                std_disp = f"{std_total:.1f}"
            else:
                scans_needed_disp = "n/a"
                expected_disp = "n/a"
                std_disp = "n/a"
            feas_rows.append([wt, f"{mean_iso:.3f}", f"{std_iso:.3f}", scans_needed_disp, expected_disp, std_disp])
        add_table(
            doc,
            [
                "SiNP wt%",
                "Mean isolated/scan",
                "Std isolated/scan",
                "Scans needed for ~30 isolated",
                "Expected isolated (at N)",
                "Std isolated (at N)",
            ],
            feas_rows,
        )
        doc.add_paragraph(
            "Scans needed are computed per SiNP wt% group (not pooled across all SiNP samples). "
            "Std for total isolated assumes independent scans (std_total = sqrt(N) * std_per_scan)."
        )
    else:
        doc.add_paragraph("Feasibility statement could not be computed (no isolated count data).")

    doc.add_heading("8. Equations (Summary)", level=1)
    doc.add_paragraph("Mean per scan: x_bar = (1/N) * sum(x_i)")
    doc.add_paragraph("Population std: sigma = sqrt((1/N) * sum((x_i - x_bar)^2))")
    doc.add_paragraph("Percent scans with isolated: 100 * sum(1[x_i > 0]) / N")
    doc.add_paragraph("Scans needed: N_needed = ceil(T / mean_isolated_per_scan), with T = 30")
    doc.add_paragraph("Expected isolated for N scans: E_total = N * mean_isolated_per_scan")
    doc.add_paragraph("Std of isolated total for N scans: sigma_total = sqrt(N) * std_isolated_per_scan")
    doc.add_paragraph("Resolution: 5000 nm / 512 = 9.7656 nm/px")

    doc.add_heading("9. LiTFSI Comparison", level=1)
    doc.add_paragraph("Not applicable (no PEGDA-LiTFSI-SiNP samples in this dataset).")

    try:
        doc.save(str(REPORT_PATH))
        print(f"Wrote report to {REPORT_PATH}")
    except PermissionError:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        alt_path = OUT_BASE / f"topo_particle_report_draft_{ts}.docx"
        doc.save(str(alt_path))
        print(f"Report file was locked; wrote report to {alt_path}")


if __name__ == "__main__":
    main()
