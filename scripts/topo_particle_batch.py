import argparse
import os
import re
import sys
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

DEFAULT_CONFIG = Path("configs/TEST configs/Example configs/config.topo_particle_2jobs_masking.yaml")
DEFAULT_DATA_LIST = Path("docs/File Locations for Data Grouped.txt")
DEFAULT_OUT_BASE = Path(r"C:\Users\Conor O'Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT")
PATTERN = "*Z Height*Forward*.tif;*Z Height*Forward*.tiff"

JOBS = [
    "particle_forward_medianbg_mean",
    "particle_forward_medianbg_fixed0",
    "particle_forward_medianbg_p95",
    "particle_forward_medianbg_max_fixed0_p95",
    "particle_forward_flatten_mean",
    "particle_forward_flatten_fixed0",
    "particle_forward_flatten_p95",
    "particle_forward_flatten_max_fixed0_p95",
]

SCAN_SIZE_UM = (5.0, 5.0)
GRID = (512, 512)
RES_NM = 5000.0 / 512.0

SYSTEM_RULES = [
    ("pegda", re.compile(r"tpo00sinp", re.I)),
    ("pegda_sinp", re.compile(r"tpo(10|25)sinp", re.I)),
]


def classify_system(path):
    p = str(path)
    for name, rx in SYSTEM_RULES:
        if rx.search(p):
            return name
    return "unknown"


def list_input_paths(data_list):
    paths = []
    for line in data_list.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("C:\\"):
            paths.append(line)
    return paths


def find_files(root):
    root = Path(root)
    files = []
    for pat in [p.strip() for p in PATTERN.split(";") if p.strip()]:
        if pat.startswith("**/"):
            glob_pat = pat[3:]
        else:
            glob_pat = pat
        files.extend(root.rglob(glob_pat))
    return sorted({str(p.resolve()) for p in files if p.is_file()})


def run_particle_job(input_root, output_root, job_name, config_path):
    cmd = [
        sys.executable,
        "scripts/run_job.py",
        "--config", str(config_path),
        "--job", job_name,
        "--input-root", str(input_root),
        "--output-root", str(output_root),
    ]
    print("RUN:", " ".join(cmd))
    res = subprocess.run(cmd, check=False)
    if res.returncode != 0:
        raise RuntimeError("run_job failed for %s" % input_root)


def parse_args():
    ap = argparse.ArgumentParser(description="Batch run topo particle jobs for SiNP systems.")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="Config YAML path.")
    ap.add_argument("--data-list", default=str(DEFAULT_DATA_LIST), help="Text file with input roots.")
    ap.add_argument("--out-base", default=str(DEFAULT_OUT_BASE), help="Output base directory.")
    ap.add_argument("--jobs", default="", help="Comma-separated job names (override default job list).")
    ap.add_argument("--only-wt", default="", help="Filter SiNP roots by wt%% (e.g., 10 or 25).")
    return ap.parse_args()


def main():
    args = parse_args()
    config_path = Path(args.config)
    data_list = Path(args.data_list)
    out_base = Path(args.out_base)
    jobs = JOBS
    if args.jobs:
        jobs = [j.strip() for j in args.jobs.split(",") if j.strip()]
    wt_filter = str(args.only_wt).strip()
    wt_rx = None
    if wt_filter:
        if wt_filter == "10":
            wt_rx = re.compile(r"tpo10sinp", re.I)
        elif wt_filter == "25":
            wt_rx = re.compile(r"tpo25sinp", re.I)

    out_base.mkdir(parents=True, exist_ok=True)
    inventory_rows = []
    sinp_roots = []
    root_counts = {}
    timing = {
        "started": datetime.now().isoformat(timespec="seconds"),
        "config": str(config_path),
        "jobs": jobs,
        "entries": [],
    }
    t0_all = time.time()

    for path in list_input_paths(data_list):
        if not os.path.isdir(path):
            print("SKIP (missing):", path)
            continue
        system = classify_system(path)
        files = find_files(path)
        inventory_rows.append({
            "system": system,
            "input_root": path,
            "map_count": len(files),
            "scan_um_x": SCAN_SIZE_UM[0],
            "scan_um_y": SCAN_SIZE_UM[1],
            "grid_x": GRID[0],
            "grid_y": GRID[1],
            "resolution_nm_per_px": RES_NM,
        })
        root_counts[path] = len(files)
        if system == "pegda_sinp":
            sinp_roots.append(path)

    # Save inventory
    inv_path = out_base / "scan_inventory.json"
    inv_path.write_text(json.dumps(inventory_rows, indent=2), encoding="utf-8")
    print("Wrote", inv_path)

    # Run particle counting for SiNP systems
    for root in sinp_roots:
        if wt_rx and not wt_rx.search(str(root)):
            continue
        base = Path(root).name
        out_root = out_base / "PEGDA_SiNP" / base
        out_root.mkdir(parents=True, exist_ok=True)
        for job_name in jobs:
            t0 = time.time()
            run_particle_job(root, out_root, job_name, config_path)
            timing["entries"].append({
                "input_root": root,
                "job": job_name,
                "scan_count": root_counts.get(root, 0),
                "seconds": round(time.time() - t0, 3),
            })

    total_seconds = round(time.time() - t0_all, 3)
    timing["total_seconds"] = total_seconds
    timing["finished"] = datetime.now().isoformat(timespec="seconds")
    timing["total_scans"] = sum(root_counts.get(r, 0) for r in sinp_roots)
    timing["total_jobs"] = len(jobs)
    timing["roots_processed"] = len(sinp_roots)
    timing_path = out_base / "run_timing.json"
    timing_path.write_text(json.dumps(timing, indent=2), encoding="utf-8")
    print("Wrote", timing_path)

    print("Done.")


if __name__ == "__main__":
    main()
