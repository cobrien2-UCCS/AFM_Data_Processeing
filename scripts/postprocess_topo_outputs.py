from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _run(cmd: list[str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        f.write("CMD: " + " ".join(cmd) + "\n\n")
        f.flush()
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)
        return p.wait()


def main() -> int:
    ap = argparse.ArgumentParser(description="Postprocess topo particle run outputs into summary + fits + final Word report.")
    ap.add_argument("--out-base-list", required=True, help="Semicolon-separated output roots (e.g., wt10;wt25).")
    ap.add_argument("--summary-config", default="configs/TEST configs/Example configs/config.topo_particle_summary.yaml")
    ap.add_argument("--fits-config", default="configs/TEST configs/Example configs/config.topo_particle_fits.yaml")
    ap.add_argument("--report-path", default="", help="If empty, write next to the first out-base.")
    ap.add_argument("--skip-fits", action="store_true", help="Skip distribution fitting step.")
    ap.add_argument("--fast-summary", action="store_true", help="Use topo_particle_summary.py --fast.")
    args = ap.parse_args()

    bases = [Path(p.strip()) for p in args.out_base_list.split(";") if p.strip()]
    if not bases:
        raise SystemExit("No out bases provided.")
    for b in bases:
        if not b.exists():
            raise SystemExit(f"Missing out base: {b}")

    report_path = Path(args.report_path) if args.report_path else (bases[0] / f"topo_particle_report_FINAL_{_ts()}.docx")
    run_dir = bases[0] / "postprocess_logs" / f"postprocess_{_ts()}"

    py = [sys.executable]

    # 1) Summary per root
    for b in bases:
        cmd = py + ["scripts/topo_particle_summary.py", "--out-base", str(b), "--config", args.summary_config]
        if args.fast_summary:
            cmd.append("--fast")
        rc = _run(cmd, run_dir / f"summary_{b.name}.log")
        if rc != 0:
            print(f"Summary failed for {b} (rc={rc}). See {run_dir}.", file=sys.stderr)
            return rc

    # 2) Fits per root (optional)
    if not args.skip_fits:
        for b in bases:
            cmd = py + ["scripts/fit_particle_distributions.py", "--config", args.fits_config, "--input-root", str(b)]
            rc = _run(cmd, run_dir / f"fits_{b.name}.log")
            if rc != 0:
                print(f"Fits failed for {b} (rc={rc}). See {run_dir}.", file=sys.stderr)
                return rc

    # 3) Final report combining roots
    cmd = py + [
        "scripts/generate_topo_report_docx.py",
        "--out-base-list",
        ";".join(str(b) for b in bases),
        "--report-path",
        str(report_path),
    ]
    rc = _run(cmd, run_dir / "report.log")
    if rc != 0:
        print(f"Report generation failed (rc={rc}). See {run_dir}.", file=sys.stderr)
        return rc

    print(f"Wrote: {report_path}")
    print(f"Logs: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

