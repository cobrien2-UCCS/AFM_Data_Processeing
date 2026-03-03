import csv
import json
import math
import statistics as stats
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_BASE = Path(r"C:\Users\Conor O'Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT")

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


def to_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def to_int(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default


def sample_from_summary_path(csv_path):
    # .../PEGDA_SiNP/<sample>/particle_forward/summary.csv
    try:
        return csv_path.parent.parent.name
    except Exception:
        return "unknown"


def system_from_summary_path(csv_path):
    try:
        # .../<system>/<sample>/particle_forward/summary.csv
        return csv_path.parent.parent.parent.name
    except Exception:
        return "unknown"


def sample_from_particle_path(csv_path):
    try:
        # .../PEGDA_SiNP/<sample>/particle_forward/*_particles.csv
        return csv_path.parent.parent.name
    except Exception:
        return "unknown"


def system_from_particle_path(csv_path):
    try:
        return csv_path.parent.parent.parent.name
    except Exception:
        return "unknown"


def short_label(label, max_len=18):
    if len(label) <= max_len:
        return label
    return label[: max_len - 3] + "..."


def main():
    inv = read_inventory()

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
        if "particle_forward" not in str(p):
            continue
        for row in read_particle_summary(p):
            row["source_csv"] = str(p)
            row["sample"] = sample_from_summary_path(p)
            row["system"] = system_from_summary_path(p)
            summary_rows.append(row)

    count_rows = []
    counts = []
    isolated_counts = []
    counts_by_sample = {}
    isolated_by_sample = {}
    sample_system = {}
    rows_by_sample = {}
    for row in summary_rows:
        count_total = to_int(row.get("count_total"))
        count_iso = to_int(row.get("count_isolated"))
        sample = row.get("sample", "unknown")
        system = row.get("system", "unknown")
        counts.append(count_total)
        isolated_counts.append(count_iso)
        counts_by_sample.setdefault(sample, []).append(count_total)
        isolated_by_sample.setdefault(sample, []).append(count_iso)
        rows_by_sample.setdefault(sample, []).append(row)
        if sample not in sample_system:
            sample_system[sample] = system
        count_rows.append({
            "source_file": row.get("source_file", ""),
            "count_total": count_total,
            "count_isolated": count_iso,
            "diam_min_nm": row.get("diam_min_nm", ""),
            "diam_max_nm": row.get("diam_max_nm", ""),
            "iso_min_dist_nm": row.get("iso_min_dist_nm", ""),
            "sample": sample,
            "system": system,
        })

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

    if counts:
        plt.figure(figsize=(6,4))
        plt.hist(counts, bins=20, color="#4C78A8", edgecolor="black")
        plt.title("Particle Count per Map (PEGDA-SiNP)")
        plt.xlabel("Particles per map")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_particle_count_hist.png", dpi=300)
        plt.close()

    if diameters:
        plt.figure(figsize=(6,4))
        plt.hist(diameters, bins=30, color="#F58518", edgecolor="black")
        plt.title("Particle Diameter Distribution (filtered)")
        plt.xlabel("Diameter (nm)")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_particle_diameter_hist.png", dpi=300)
        plt.close()

    if isolated_counts:
        plt.figure(figsize=(6,4))
        plt.hist(isolated_counts, bins=20, color="#54A24B", edgecolor="black")
        plt.title("Isolated Particle Count per Map (PEGDA-SiNP)")
        plt.xlabel("Isolated particles per map")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_isolated_count_hist.png", dpi=300)
        plt.close()

    if counts:
        plt.figure(figsize=(7,4))
        plt.scatter(range(1, len(counts) + 1), counts, s=12, color="#4C78A8", alpha=0.8)
        plt.title("Particle Count per Map (index order)")
        plt.xlabel("Map index")
        plt.ylabel("Particles per map")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_particle_count_scatter.png", dpi=300)
        plt.close()

    if isolated_counts:
        plt.figure(figsize=(7,4))
        plt.scatter(range(1, len(isolated_counts) + 1), isolated_counts, s=12, color="#54A24B", alpha=0.8)
        plt.title("Isolated Particle Count per Map (index order)")
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
        plt.title("Particle Count per Map by Sample")
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
        plt.title("Isolated Particle Count per Map by Sample")
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
        plt.title("Mean Particle Count per Map by Sample")
        plt.xlabel("Sample")
        plt.ylabel("Particles per map (mean ± std)")
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
        plt.title("Mean Isolated Particle Count per Map by Sample")
        plt.xlabel("Sample")
        plt.ylabel("Isolated particles per map (mean ± std)")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(OUT_BASE / "fig_isolated_count_mean_by_sample.png", dpi=300)
        plt.close()

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
