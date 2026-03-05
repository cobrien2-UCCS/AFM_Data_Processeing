import argparse
import csv
import math
import re
import random
import statistics as stats
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


DEFAULT_OUT_BASE = Path(r"C:\Users\Conor O'Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT")


def load_config(path):
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    if yaml is None:
        raise RuntimeError("PyYAML is required to load config files.")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows and (not fieldnames or len(fieldnames) == 0):
        fieldnames = sorted({k for row in rows for k in row.keys()})
    if rows and fieldnames:
        all_keys = set()
        for row in rows:
            all_keys.update(row.keys())
        for key in sorted(all_keys):
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_counts_csv(root):
    root = Path(root)
    direct = root / "particle_counts_by_map.csv"
    if direct.exists():
        return direct
    matches = list(root.rglob("particle_counts_by_map.csv"))
    return matches[0] if matches else None


def read_rows(csv_path):
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def to_int(v, default=None):
    try:
        return int(float(v))
    except Exception:
        return default


def slugify(text):
    if text is None:
        return "unknown"
    s = re.sub(r"\s+", "_", str(text))
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s)
    return s.strip("_") or "unknown"


def poisson_cdf(k, lam):
    if k < 0:
        return 0.0
    p = math.exp(-lam)
    cdf = p
    for i in range(1, k + 1):
        p = p * lam / float(i)
        cdf += p
    return min(max(cdf, 0.0), 1.0)


def poisson_pmf(k, lam):
    if k < 0:
        return 0.0
    try:
        return math.exp(-lam) * (lam ** k) / math.factorial(k)
    except Exception:
        return 0.0


def nb_params_from_mean_var(mean_val, var_val):
    if mean_val <= 0:
        return {"r": 0.0, "p": 1.0, "underdispersed": True}
    if var_val <= mean_val:
        # Under-dispersed; approximate Poisson with large r.
        r = 1e9
        p = r / (r + mean_val)
        return {"r": r, "p": p, "underdispersed": True}
    r = (mean_val * mean_val) / (var_val - mean_val)
    p = r / (r + mean_val)
    return {"r": r, "p": p, "underdispersed": False}


def nb_pmf(k, r, p):
    if k < 0:
        return 0.0
    if r <= 0:
        return 0.0
    try:
        logp = math.lgamma(k + r) - math.lgamma(r) - math.lgamma(k + 1)
        logp += r * math.log(p) + k * math.log(1.0 - p)
        return math.exp(logp)
    except Exception:
        return 0.0


def nb_cdf(k, r, p):
    if k < 0:
        return 0.0
    if r <= 0:
        return 0.0
    p0 = p ** r
    cdf = p0
    prob = p0
    for i in range(0, k):
        prob = prob * (i + r) / float(i + 1) * (1.0 - p)
        cdf += prob
    return min(max(cdf, 0.0), 1.0)


def zinb_params(values, nb_params):
    mean_val = stats.mean(values) if values else 0.0
    p0_obs = sum(1 for v in values if v == 0) / float(len(values)) if values else 0.0
    r = nb_params["r"]
    p = nb_params["p"]
    p0_nb = p ** r if r > 0 else 1.0
    if p0_nb >= 1.0:
        pi = 0.0
    else:
        pi = (p0_obs - p0_nb) / (1.0 - p0_nb)
        pi = max(0.0, min(0.95, pi))
    return {"pi": pi, "mean": mean_val, "p0_obs": p0_obs, "p0_nb": p0_nb}


def zinb_pmf(k, r, p, pi):
    if k == 0:
        return pi + (1.0 - pi) * (p ** r)
    return (1.0 - pi) * nb_pmf(k, r, p)


def poisson_sample(lam, rng):
    if lam <= 0:
        return 0
    l = math.exp(-lam)
    k = 0
    p = 1.0
    while p > l:
        k += 1
        p *= rng.random()
    return k - 1


def nb_sample(r, p, rng):
    if r <= 0:
        return 0
    # Gamma-Poisson mixture
    scale = (1.0 - p) / p
    lam = rng.gammavariate(r, scale)
    return poisson_sample(lam, rng)


def zinb_sample(r, p, pi, rng):
    if rng.random() < pi:
        return 0
    return nb_sample(r, p, rng)


def compute_poisson_fit(values):
    if not values:
        return None
    mean_val = stats.mean(values)
    return {"lambda": mean_val, "mean": mean_val}


def compute_checks(values, mean_val, thresholds):
    if not values:
        return {}
    variance = stats.pvariance(values) if len(values) > 1 else 0.0
    var_mean_ratio = variance / mean_val if mean_val > 0 else (float("inf") if variance > 0 else 0.0)
    zeros = sum(1 for v in values if v == 0)
    zero_rate = zeros / float(len(values))
    poisson_zero = math.exp(-mean_val) if mean_val >= 0 else 0.0
    zero_ratio = zero_rate / poisson_zero if poisson_zero > 0 else float("inf")

    var_warn = thresholds.get("var_mean_ratio_warn", 1.2)
    zero_warn = thresholds.get("zero_ratio_warn", 1.5)
    min_mean = thresholds.get("min_mean", 0.0)

    passes_poisson = True
    if mean_val < min_mean:
        passes_poisson = False
    if var_mean_ratio > var_warn:
        passes_poisson = False
    if zero_ratio > zero_warn:
        passes_poisson = False

    return {
        "variance": variance,
        "var_mean_ratio": var_mean_ratio,
        "zero_rate": zero_rate,
        "poisson_zero_rate": poisson_zero,
        "zero_ratio": zero_ratio,
        "passes_poisson": passes_poisson,
    }


def compute_risk_curve(mean_val, target_total, max_scans):
    curve = []
    if mean_val <= 0:
        for n in range(1, max_scans + 1):
            curve.append({"n_scans": n, "success_prob": 0.0})
        return curve
    for n in range(1, max_scans + 1):
        lam = n * mean_val
        success = 1.0 - poisson_cdf(target_total - 1, lam)
        curve.append({"n_scans": n, "success_prob": success})
    return curve


def compute_nb_risk_curve(mean_val, var_val, target_total, max_scans):
    params = nb_params_from_mean_var(mean_val, var_val)
    r = params["r"]
    p = params["p"]
    curve = []
    for n in range(1, max_scans + 1):
        r_sum = n * r
        success = 1.0 - nb_cdf(target_total - 1, r_sum, p)
        curve.append({"n_scans": n, "success_prob": success})
    return curve, params


def compute_zinb_risk_curve(values, nb_params, zinb_params, target_total, max_scans, mc_samples, seed):
    r = nb_params["r"]
    p = nb_params["p"]
    pi = zinb_params["pi"]
    rng = random.Random(seed)
    success_counts = [0] * max_scans
    for _ in range(mc_samples):
        total = 0
        for n in range(1, max_scans + 1):
            total += zinb_sample(r, p, pi, rng)
            if total >= target_total:
                success_counts[n - 1] += 1
    curve = []
    for n in range(1, max_scans + 1):
        curve.append({"n_scans": n, "success_prob": success_counts[n - 1] / float(mc_samples)})
    return curve


def find_required_scans(curve, levels):
    out = {}
    for level in levels:
        req = None
        for row in curve:
            if row["success_prob"] >= level:
                req = row["n_scans"]
                break
        out[level] = req
    return out


def plot_histogram(values, pmf_func, out_path, title, max_bin=None):
    if not values:
        return
    max_val = max(values)
    max_bin = max_bin if max_bin is not None else max_val
    bins = list(range(0, max_bin + 2))
    plt.figure(figsize=(8, 4.5))
    plt.hist(values, bins=bins, color="#4C78A8", alpha=0.8, rwidth=0.85)
    xs = list(range(0, max_bin + 1))
    ys = [pmf_func(k) * len(values) for k in xs]
    plt.plot(xs, ys, color="#F58518", marker="o", linestyle="-", linewidth=1.5, label="Model fit")
    plt.title(title)
    plt.xlabel("Count per scan")
    plt.ylabel("Frequency")
    plt.legend()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_risk_curve(curve, levels, out_path, title):
    if not curve:
        return
    xs = [row["n_scans"] for row in curve]
    ys = [row["success_prob"] for row in curve]
    plt.figure(figsize=(8, 4.5))
    plt.plot(xs, ys, color="#54A24B", linewidth=2)
    for level in levels:
        plt.axhline(level, color="#999999", linestyle="--", linewidth=1)
    plt.title(title)
    plt.xlabel("Number of scans")
    plt.ylabel("P(total isolated >= target)")
    plt.ylim(0.0, 1.0)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_risk_band(curve, band, levels, out_path, title, color="#54A24B"):
    xs = [row["n_scans"] for row in curve]
    ys = [row["success_prob"] for row in curve]
    plt.figure(figsize=(8, 4.5))
    plt.plot(xs, ys, color=color, linewidth=2)
    if band:
        lower = [b["p_low"] for b in band]
        upper = [b["p_high"] for b in band]
        plt.fill_between(xs, lower, upper, color=color, alpha=0.2)
    for level in levels:
        plt.axhline(level, color="#999999", linestyle="--", linewidth=1)
    plt.title(title)
    plt.xlabel("Number of scans")
    plt.ylabel("P(total isolated >= target)")
    plt.ylim(0.0, 1.0)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def bootstrap_risk(values, model, target_total, max_scans, bootstrap_n, seed):
    rng = random.Random(seed)
    curves = []
    for _ in range(bootstrap_n):
        sample = [rng.choice(values) for _ in range(len(values))]
        mean_val = stats.mean(sample)
        var_val = stats.pvariance(sample) if len(sample) > 1 else 0.0
        if model == "poisson":
            curve = compute_risk_curve(mean_val, target_total, max_scans)
        elif model == "nb":
            curve, _ = compute_nb_risk_curve(mean_val, var_val, target_total, max_scans)
        else:
            continue
        curves.append(curve)
    return curves


def risk_band_from_curves(curves, percentiles):
    if not curves:
        return []
    low, high = percentiles
    band = []
    for idx in range(len(curves[0])):
        vals = [c[idx]["success_prob"] for c in curves]
        vals.sort()
        if not vals:
            band.append({"p_low": 0.0, "p_high": 0.0})
            continue
        lo = vals[int((low / 100.0) * (len(vals) - 1))]
        hi = vals[int((high / 100.0) * (len(vals) - 1))]
        band.append({"p_low": lo, "p_high": hi})
    return band


def histogram_probs(values, max_bin):
    if not values:
        return [0.0] * (max_bin + 1)
    counts = [0] * (max_bin + 1)
    for v in values:
        idx = v if v <= max_bin else max_bin
        if idx < 0:
            continue
        counts[idx] += 1
    total = float(sum(counts)) or 1.0
    return [c / total for c in counts]


def js_divergence(p, q):
    m = [(a + b) / 2.0 for a, b in zip(p, q)]
    return 0.5 * (kl_divergence(p, m) + kl_divergence(q, m))


def kl_divergence(p, q):
    s = 0.0
    for a, b in zip(p, q):
        if a <= 0.0:
            continue
        if b <= 0.0:
            continue
        s += a * math.log(a / b, 2)
    return s


def l1_distance(p, q):
    return sum(abs(a - b) for a, b in zip(p, q))


def wasserstein1(p, q):
    cdf_p = 0.0
    cdf_q = 0.0
    dist = 0.0
    for a, b in zip(p, q):
        cdf_p += a
        cdf_q += b
        dist += abs(cdf_p - cdf_q)
    return dist

def resolve_out_dir(root, out_dir):
    if out_dir is None:
        return Path(root) / "summary_outputs" / "fits"
    out_dir = Path(out_dir)
    if out_dir.is_absolute():
        return out_dir
    return Path(root) / out_dir


def main():
    ap = argparse.ArgumentParser(description="Fit particle count distributions and compute scan risk curves.")
    ap.add_argument("--config", default="configs/TEST configs/Example configs/config.topo_particle_fits.yaml")
    ap.add_argument("--input-root", action="append", dest="input_roots", help="Output root(s) to analyze.")
    ap.add_argument("--out-dir", default=None, help="Override output directory (absolute or relative).")
    ap.add_argument("--fast", action="store_true", help="Use reduced sampling for quick previews.")
    args = ap.parse_args()

    cfg = load_config(args.config)
    fit_cfg = cfg.get("fit", {})
    if fit_cfg.get("enable") is False:
        print("Fit disabled by config.")
        return

    input_roots = args.input_roots or fit_cfg.get("input_roots") or []
    if not input_roots:
        input_roots = [str(DEFAULT_OUT_BASE)]

    count_field = fit_cfg.get("count_field", "count_isolated")
    stratify_by = fit_cfg.get("stratify_by", ["wt_percent", "scraped", "job"])
    count_models = fit_cfg.get("count_models")
    if not count_models:
        count_model = fit_cfg.get("count_model", "poisson")
        count_models = [count_model]
    count_models = [m.lower() for m in count_models]
    min_samples = int(fit_cfg.get("min_samples", 5))
    target_total = int(fit_cfg.get("target_total", 30))
    reliability_levels = fit_cfg.get("reliability_levels", [0.9, 0.95, 0.99])
    max_scans = int(fit_cfg.get("max_scans", 200))
    seed = int(fit_cfg.get("random_seed", 13))
    mc_samples = int(fit_cfg.get("mc_samples", 2000))
    plot_cfg = fit_cfg.get("plot", {})
    plot_enable = plot_cfg.get("enable", True)
    plot_hist = plot_cfg.get("histogram", True)
    plot_risk = plot_cfg.get("risk_curve", True)
    hist_max_bin = plot_cfg.get("hist_max_bin", None)
    combine_models = plot_cfg.get("combine_models", True)
    combine_uncertainty = plot_cfg.get("combine_uncertainty", False)
    unc_cfg = fit_cfg.get("uncertainty", {})
    unc_enable = unc_cfg.get("enable", True)
    unc_bootstrap = int(unc_cfg.get("bootstrap", 200))
    unc_percentiles = unc_cfg.get("band_percentiles", [5, 95])
    unc_models = [m.lower() for m in unc_cfg.get("include_models", ["poisson", "nb"])]
    checks_cfg = fit_cfg.get("checks", {})
    method_cfg = fit_cfg.get("method_compare", {})
    method_enable = method_cfg.get("enable", True)
    method_stratify = method_cfg.get("stratify_by", [])
    method_hist_max = method_cfg.get("hist_max_bin", hist_max_bin)
    method_count_field = method_cfg.get("count_field", count_field)

    if args.fast:
        mc_samples = min(mc_samples, 500)
        unc_bootstrap = min(unc_bootstrap, 50)
        max_scans = min(max_scans, 100)
        print("Fast mode: mc_samples=%d bootstrap=%d max_scans=%d" % (mc_samples, unc_bootstrap, max_scans))

    for root in input_roots:
        root_path = Path(root)
        counts_csv = read_counts_csv(root_path)
        if counts_csv is None:
            print("No particle_counts_by_map.csv found under", root_path)
            continue
        rows = read_rows(counts_csv)
        out_dir = resolve_out_dir(root_path, args.out_dir or fit_cfg.get("output_dir"))
        out_dir.mkdir(parents=True, exist_ok=True)

        groups = {}
        for row in rows:
            val = to_int(row.get(count_field))
            if val is None or val < 0:
                continue
            key_parts = []
            key_dict = {}
            for field in stratify_by:
                key_val = row.get(field, "")
                key_parts.append("%s=%s" % (field, key_val))
                key_dict[field] = key_val
            key = tuple(key_parts)
            groups.setdefault(key, {"meta": key_dict, "values": []})["values"].append(val)

        summary_rows = []
        curve_rows = []
        model_curves = {}
        model_bands = {}
        for key, payload in groups.items():
            values = payload["values"]
            meta = payload["meta"]
            if len(values) < min_samples:
                continue
            label = "__".join(key)
            safe_label = slugify(label)
            mean_val = stats.mean(values)
            var_val = stats.pvariance(values) if len(values) > 1 else 0.0

            zero_rate_obs = sum(1 for v in values if v == 0) / float(len(values)) if values else 0.0
            for model in count_models:
                curve = None
                checks = {}
                params = {}
                if model == "poisson":
                    fit = compute_poisson_fit(values)
                    if not fit:
                        continue
                    checks = compute_checks(values, fit["mean"], checks_cfg)
                    curve = compute_risk_curve(fit["mean"], target_total, max_scans)
                    params = {"lambda": fit["lambda"]}
                    params["p0_model"] = math.exp(-fit["lambda"]) if fit["lambda"] >= 0 else 0.0
                    pmf_func = lambda k, lam=fit["lambda"]: poisson_pmf(k, lam)
                elif model == "nb":
                    nb_params = nb_params_from_mean_var(mean_val, var_val)
                    curve, nb_params_used = compute_nb_risk_curve(mean_val, var_val, target_total, max_scans)
                    params = {"nb_r": nb_params_used["r"], "nb_p": nb_params_used["p"], "nb_underdisp": nb_params_used["underdispersed"]}
                    params["p0_model"] = (nb_params_used["p"] ** nb_params_used["r"]) if nb_params_used["r"] > 0 else 1.0
                    pmf_func = lambda k, r=nb_params_used["r"], p=nb_params_used["p"]: nb_pmf(k, r, p)
                elif model == "zinb":
                    nb_params = nb_params_from_mean_var(mean_val, var_val)
                    zinb = zinb_params(values, nb_params)
                    curve = compute_zinb_risk_curve(values, nb_params, zinb, target_total, max_scans, mc_samples, seed)
                    params = {
                        "nb_r": nb_params["r"],
                        "nb_p": nb_params["p"],
                        "zinb_pi": zinb["pi"],
                        "zinb_p0_obs": zinb["p0_obs"],
                        "zinb_p0_nb": zinb["p0_nb"],
                    }
                    params["p0_model"] = zinb["pi"] + (1.0 - zinb["pi"]) * (nb_params["p"] ** nb_params["r"]) if nb_params["r"] > 0 else 1.0
                    pmf_func = lambda k, r=nb_params["r"], p=nb_params["p"], pi=zinb["pi"]: zinb_pmf(k, r, p, pi)
                else:
                    continue

                required = find_required_scans(curve, reliability_levels)

                if plot_enable and plot_hist:
                    plot_histogram(
                        values,
                        pmf_func,
                        out_dir / ("hist_%s_%s.png" % (safe_label, model)),
                        "Counts per scan (%s | %s)" % (label, model),
                        max_bin=hist_max_bin,
                    )
                if plot_enable and plot_risk:
                    plot_risk_curve(
                        curve,
                        reliability_levels,
                        out_dir / ("risk_%s_%s.png" % (safe_label, model)),
                        "P(total >= %d) vs scans (%s | %s)" % (target_total, label, model),
                    )

                if unc_enable and model in unc_models and unc_bootstrap > 0:
                    boot_curves = bootstrap_risk(values, model, target_total, max_scans, unc_bootstrap, seed + 7)
                    band = risk_band_from_curves(boot_curves, unc_percentiles)
                    model_bands[(label, model)] = band
                    if plot_enable:
                        plot_risk_band(
                            curve,
                            band,
                            reliability_levels,
                            out_dir / ("risk_band_%s_%s.png" % (safe_label, model)),
                            "P(total >= %d) w/ uncertainty (%s | %s)" % (target_total, label, model),
                        )

                model_curves[(label, model)] = curve

                row_out = {
                    "count_field": count_field,
                    "count_model": model,
                    "n_scans": len(values),
                    "mean_per_scan": mean_val,
                    "variance_per_scan": var_val,
                    "zero_rate_obs": zero_rate_obs,
                    "min_per_scan": min(values),
                    "max_per_scan": max(values),
                    "target_total": target_total,
                }
                row_out.update(meta)
                row_out.update(checks)
                row_out.update(params)
                for level, req in required.items():
                    row_out["n_required_%s" % str(level).replace(".", "")] = req if req is not None else ""
                summary_rows.append(row_out)

                for row_curve in curve:
                    curve_rows.append({
                        "count_field": count_field,
                        "count_model": model,
                        "target_total": target_total,
                        "n_scans": row_curve["n_scans"],
                        "success_prob": row_curve["success_prob"],
                        "group_label": label,
                        **meta,
                    })

            if plot_enable and combine_models and model_curves:
                plt.figure(figsize=(8, 4.5))
                for model in count_models:
                    curve = model_curves.get((label, model))
                    if not curve:
                        continue
                    xs = [row["n_scans"] for row in curve]
                    ys = [row["success_prob"] for row in curve]
                    plt.plot(xs, ys, linewidth=2, label=model)
                for level in reliability_levels:
                    plt.axhline(level, color="#999999", linestyle="--", linewidth=1)
                plt.title("P(total >= %d) vs scans (%s | compare)" % (target_total, label))
                plt.xlabel("Number of scans")
                plt.ylabel("P(total isolated >= target)")
                plt.ylim(0.0, 1.0)
                plt.legend()
                plt.tight_layout()
                plt.savefig(out_dir / ("risk_compare_%s.png" % safe_label), dpi=160)
                plt.close()

            if plot_enable and combine_uncertainty and model_bands:
                plt.figure(figsize=(8, 4.5))
                for model in count_models:
                    curve = model_curves.get((label, model))
                    band = model_bands.get((label, model))
                    if not curve:
                        continue
                    xs = [row["n_scans"] for row in curve]
                    ys = [row["success_prob"] for row in curve]
                    plt.plot(xs, ys, linewidth=1.5, label=model)
                    if band:
                        lower = [b["p_low"] for b in band]
                        upper = [b["p_high"] for b in band]
                        plt.fill_between(xs, lower, upper, alpha=0.15)
                for level in reliability_levels:
                    plt.axhline(level, color="#999999", linestyle="--", linewidth=1)
                plt.title("P(total >= %d) with uncertainty (%s)" % (target_total, label))
                plt.xlabel("Number of scans")
                plt.ylabel("P(total isolated >= target)")
                plt.ylim(0.0, 1.0)
                plt.legend()
                plt.tight_layout()
                plt.savefig(out_dir / ("risk_compare_uncertainty_%s.png" % safe_label), dpi=160)
                plt.close()

        if summary_rows:
            write_csv(out_dir / "fit_summary.csv", summary_rows, list(summary_rows[0].keys()))
        if curve_rows:
            write_csv(out_dir / "fit_risk_curves.csv", curve_rows, list(curve_rows[0].keys()))

        if method_enable:
            method_groups = {}
            for row in rows:
                val = to_int(row.get(method_count_field))
                if val is None or val < 0:
                    continue
                job = row.get("job", "unknown")
                meta = {}
                key_parts = []
                for field in method_stratify:
                    key_val = row.get(field, "")
                    meta[field] = key_val
                    key_parts.append("%s=%s" % (field, key_val))
                key = tuple(key_parts) if key_parts else ("all",)
                payload = method_groups.setdefault(key, {"meta": meta, "jobs": {}})
                payload["jobs"].setdefault(job, []).append(val)

            hist_rows = []
            dist_rows = []
            metric_rows = []
            variance_rows = []
            for key, payload in method_groups.items():
                meta = payload["meta"]
                jobs = payload["jobs"]
                if not jobs:
                    continue
                max_val = 0
                if method_hist_max is not None:
                    max_val = int(method_hist_max)
                else:
                    for vals in jobs.values():
                        if vals:
                            max_val = max(max_val, max(vals))
                hist_by_job = {}
                for job, vals in jobs.items():
                    probs = histogram_probs(vals, max_val)
                    hist_by_job[job] = probs
                    metric_rows.append({
                        **meta,
                        "job": job,
                        "n_scans": len(vals),
                        "mean_per_scan": stats.mean(vals) if vals else 0.0,
                        "variance_per_scan": stats.pvariance(vals) if len(vals) > 1 else 0.0,
                        "zero_rate": sum(1 for v in vals if v == 0) / float(len(vals)) if vals else 0.0,
                    })
                    for idx, pval in enumerate(probs):
                        hist_rows.append({**meta, "job": job, "bin": idx, "prob": pval})

                jobs_list = sorted(hist_by_job.keys())
                for i in range(len(jobs_list)):
                    for j in range(i + 1, len(jobs_list)):
                        a = jobs_list[i]
                        b = jobs_list[j]
                        pa = hist_by_job[a]
                        pb = hist_by_job[b]
                        dist_rows.append({
                            **meta,
                            "job_a": a,
                            "job_b": b,
                            "js_divergence": js_divergence(pa, pb),
                            "l1_distance": l1_distance(pa, pb),
                            "wasserstein1": wasserstein1(pa, pb),
                        })

                means = [r["mean_per_scan"] for r in metric_rows if r["job"] in jobs_list]
                vars_ = [r["variance_per_scan"] for r in metric_rows if r["job"] in jobs_list]
                zeros = [r["zero_rate"] for r in metric_rows if r["job"] in jobs_list]
                if means:
                    variance_rows.append({
                        **meta,
                        "metric": "mean_per_scan",
                        "job_count": len(means),
                        "mean": stats.mean(means),
                        "variance": stats.pvariance(means) if len(means) > 1 else 0.0,
                        "std": stats.pstdev(means) if len(means) > 1 else 0.0,
                        "min": min(means),
                        "max": max(means),
                    })
                if vars_:
                    variance_rows.append({
                        **meta,
                        "metric": "variance_per_scan",
                        "job_count": len(vars_),
                        "mean": stats.mean(vars_),
                        "variance": stats.pvariance(vars_) if len(vars_) > 1 else 0.0,
                        "std": stats.pstdev(vars_) if len(vars_) > 1 else 0.0,
                        "min": min(vars_),
                        "max": max(vars_),
                    })
                if zeros:
                    variance_rows.append({
                        **meta,
                        "metric": "zero_rate",
                        "job_count": len(zeros),
                        "mean": stats.mean(zeros),
                        "variance": stats.pvariance(zeros) if len(zeros) > 1 else 0.0,
                        "std": stats.pstdev(zeros) if len(zeros) > 1 else 0.0,
                        "min": min(zeros),
                        "max": max(zeros),
                    })

            if hist_rows:
                write_csv(out_dir / "method_histograms.csv", hist_rows, list(hist_rows[0].keys()))
            if dist_rows:
                write_csv(out_dir / "method_histogram_distances.csv", dist_rows, list(dist_rows[0].keys()))
            if metric_rows:
                write_csv(out_dir / "method_compare_metrics.csv", metric_rows, list(metric_rows[0].keys()))
            if variance_rows:
                write_csv(out_dir / "method_variance_summary.csv", variance_rows, list(variance_rows[0].keys()))

        print("Fit outputs written to", out_dir)


if __name__ == "__main__":
    main()
