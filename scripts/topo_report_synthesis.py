from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, stdev


PRIMARY_JOB = "particle_forward_medianbg_mean"
COMPARISON_JOB = "particle_forward_flatten_mean"
TARGET_ISOLATED = 30
CONFIDENCE = 0.95
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
        std_count=stdev(counts) if len(counts) > 1 else 0.0,
        min_count=min(counts),
        max_count=max(counts),
        zero_count_rate=sum(1 for x in counts if x == 0) / len(counts),
        mean_isolated=mean(isolated),
        std_isolated=stdev(isolated) if len(isolated) > 1 else 0.0,
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


def load_root(root: Path, wt_percent: int) -> RootStats:
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


def method_rows(root: RootStats) -> list[dict[str, str]]:
    primary_mean = root.method_stats[PRIMARY_JOB].mean_isolated
    rows = []
    for job in JOB_ORDER:
        stats = root.method_stats[job]
        fit = root.method_fits[job]
        rows.append(
            {
                "system": root.label,
                "method": JOB_LABELS.get(job, job),
                "job": job,
                "mean_isolated_per_scan": f"{stats.mean_isolated:.2f}",
                "std_isolated_per_scan": f"{stats.std_isolated:.2f}",
                "zero_isolated_rate": f"{stats.zero_isolated_rate:.4f}",
                "required_scans_095": str(fit.n_required_095),
                "relative_to_primary": f"{(stats.mean_isolated / primary_mean):.2f}x" if primary_mean > 0 else "n/a",
                "isolated_per_scan_per_wt": f"{(stats.mean_isolated / root.wt_percent):.3f}",
            }
        )
    return rows


def grain_rows(root: RootStats) -> list[dict[str, str]]:
    rows = []
    for job in JOB_ORDER:
        grain = root.grain_stats[job]
        rows.append(
            {
                "system": root.label,
                "method": JOB_LABELS.get(job, job),
                "job": job,
                "grain_total": str(grain.grain_total),
                "grain_kept": str(grain.grain_kept),
                "grain_isolated": str(grain.grain_isolated),
                "kept_mean_diameter_nm": f"{grain.kept_mean_diameter_nm:.2f}",
                "kept_std_diameter_nm": f"{grain.kept_std_diameter_nm:.2f}",
                "isolated_mean_diameter_nm": f"{grain.isolated_mean_diameter_nm:.2f}",
                "isolated_std_diameter_nm": f"{grain.isolated_std_diameter_nm:.2f}",
            }
        )
    return rows


def sample_rows(root: RootStats) -> list[dict[str, str]]:
    stats = root.method_stats[PRIMARY_JOB]
    rows = []
    for sample in root.samples:
        rows.append(
            {
                "system": root.label,
                "sample_set": sample,
                "scans": str(stats.sample_scan_counts[sample]),
                "mean_isolated_per_scan": f"{stats.sample_means[sample]:.2f}",
                "std_isolated_per_scan": f"{stats.sample_stds[sample]:.2f}",
                "pct_scans_with_isolated": f"{stats.sample_pct_nonzero[sample]:.1f}",
            }
        )
    return rows


def _poisson_success(mu: float, target: int) -> float:
    if mu <= 0:
        return 0.0
    term = math.exp(-mu)
    cdf = term
    for k in range(1, target):
        term *= mu / k
        cdf += term
    return max(0.0, min(1.0, 1.0 - cdf))


def availability_crossover_p(lam: float, available_scans: int, target: int = TARGET_ISOLATED, conf: float = CONFIDENCE) -> float | None:
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


def required_scan_rows(roots: list[RootStats]) -> list[dict[str, str]]:
    rows = []
    for root in roots:
        stats = root.method_stats[PRIMARY_JOB]
        fit = root.method_fits[PRIMARY_JOB]
        rows.append(
            {
                "system": root.label,
                "primary_lambda": f"{fit.mean_per_scan:.3f}",
                "observed_zero_isolated_rate": f"{fit.zero_rate_obs:.4f}",
                "required_scans_095": str(fit.n_required_095),
                "available_scans": str(stats.maps),
            }
        )
    return rows


def crossover_rows(roots: list[RootStats]) -> list[dict[str, str]]:
    rows = []
    for root in roots:
        stats = root.method_stats[PRIMARY_JOB]
        fit = root.method_fits[PRIMARY_JOB]
        p_cross = availability_crossover_p(fit.mean_per_scan, stats.maps)
        rows.append(
            {
                "system": root.label,
                "primary_lambda": f"{fit.mean_per_scan:.3f}",
                "available_scans": str(stats.maps),
                "minimum_confirmation_fraction_pstar": f"{p_cross:.3f}" if p_cross is not None else "not reachable",
            }
        )
    return rows


def build_bundle(wt10_root: Path, wt25_root: Path) -> dict:
    wt10 = load_root(wt10_root, 10)
    wt25 = load_root(wt25_root, 25)
    roots = [wt10, wt25]
    return {
        "wt10_root": str(wt10_root),
        "wt25_root": str(wt25_root),
        "primary_job": PRIMARY_JOB,
        "comparison_job": COMPARISON_JOB,
        "target_isolated": TARGET_ISOLATED,
        "confidence": CONFIDENCE,
        "systems": [
            {
                "label": root.label,
                "wt_percent": root.wt_percent,
                "sample_sets": len(root.samples),
                "scans_analyzed": root.method_stats[PRIMARY_JOB].maps,
                "diameter_mean_nm": round(root.diameter_mean_nm, 4),
                "diameter_std_nm": round(root.diameter_std_nm, 4),
            }
            for root in roots
        ],
        "sample_rows": [row for root in roots for row in sample_rows(root)],
        "required_scan_rows": required_scan_rows(roots),
        "grain_rows": [row for root in roots for row in grain_rows(root)],
        "method_rows": [row for root in roots for row in method_rows(root)],
        "crossover_rows": crossover_rows(roots),
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def write_bundle(bundle: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "topo_report_synthesis.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    _write_csv(out_dir / "topo_report_table_6_5_sample_isolated.csv", bundle.get("sample_rows", []))
    _write_csv(out_dir / "topo_report_table_6_6_required_scans.csv", bundle.get("required_scan_rows", []))
    _write_csv(out_dir / "topo_report_table_6_7_grain_summary.csv", bundle.get("grain_rows", []))
    _write_csv(out_dir / "topo_report_table_6_8_method_comparison.csv", bundle.get("method_rows", []))
    _write_csv(out_dir / "topo_report_table_6_9_crossover.csv", bundle.get("crossover_rows", []))
