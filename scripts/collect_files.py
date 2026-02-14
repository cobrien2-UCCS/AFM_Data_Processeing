#!/usr/bin/env python3
"""
Config-driven file collection/copy utility with fuzzy keyword matching.

Use case: sift large mixed folders (channels, directions, samples) into a clean
subset for processing, even when filenames contain typos.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _load_config(path: str | Path) -> Dict[str, Any]:
    # Reuse the project loader but keep it optional for minimal coupling.
    try:
        repo_root = Path(__file__).resolve().parents[1]
        src_root = repo_root / "src"
        import sys

        if str(src_root) not in sys.path:
            sys.path.insert(0, str(src_root))
        from afm_pipeline.config import load_config  # type: ignore

        return load_config(path)
    except Exception:
        # Fall back to YAML/JSON directly.
        p = Path(path)
        if p.suffix.lower() in (".yaml", ".yml"):
            import yaml  # type: ignore

            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        import json

        return json.loads(p.read_text(encoding="utf-8"))


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _short_hash(text: str, n: int = 8) -> str:
    return hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()[:n]


def _shorten_name(name: str, max_len: int) -> str:
    if max_len <= 0 or len(name) <= max_len:
        return name
    h = _short_hash(name, 8)
    keep = max_len - (len(h) + 1)
    if keep < 1:
        return h
    return name[:keep] + "_" + h


def _norm_text(s: str) -> str:
    # Normalize for fuzzy matching: lowercase, keep only alnum.
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _tokenize_filename(name: str) -> List[str]:
    # Split on common separators and keep alnum-ish tokens.
    raw = re.split(r"[\s_\-\.]+", name)
    return [t for t in raw if t]


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _best_keyword_score(keyword: str, filename: str) -> Tuple[float, str]:
    """
    Return (best_score, reason) for a keyword vs filename.

    Strategy:
    - exact normalized substring -> 1.0
    - otherwise max of:
      - similarity(keyword, full filename)
      - similarity(keyword, tokens)
      - similarity(keyword, 2-3 token windows)
    """
    kw = _norm_text(keyword)
    fn = _norm_text(filename)
    if not kw or not fn:
        return 0.0, "empty"
    if kw in fn:
        return 1.0, "substring"

    tokens = _tokenize_filename(filename)
    tokens_n = [_norm_text(t) for t in tokens if _norm_text(t)]
    best = _similarity(kw, fn)
    reason = "full"
    for t in tokens_n:
        sc = _similarity(kw, t)
        if sc > best:
            best = sc
            reason = "token"
    # token windows (helps cases like "ModulusBackward" vs "Modulus Backward")
    for win in (2, 3):
        if len(tokens_n) < win:
            continue
        for i in range(0, len(tokens_n) - win + 1):
            joined = "".join(tokens_n[i : i + win])
            sc = _similarity(kw, joined)
            if sc > best:
                best = sc
                reason = f"token_window_{win}"
    return float(best), reason


def _extract_named(regex: str, text: str) -> Dict[str, str]:
    try:
        m = re.search(regex, text)
    except re.error:
        return {}
    if not m:
        return {}
    return {k: v for k, v in m.groupdict().items() if v is not None}


def _extract_meta(path: Path, extract_rules: List[Dict[str, Any]]) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    name = path.name
    for rule in extract_rules:
        regex = str(rule.get("regex") or "")
        if not regex:
            continue
        got = _extract_named(regex, name)
        if not got:
            continue
        # Optional map: {group: meta_key}
        mapping = rule.get("map") or {}
        if isinstance(mapping, dict) and mapping:
            for gk, gv in got.items():
                mk = mapping.get(gk) or gk
                meta[str(mk)] = str(gv)
        else:
            for gk, gv in got.items():
                meta[str(gk)] = str(gv)
    return meta


def _safe_template_substitute(template: str, ctx: Dict[str, Any]) -> str:
    # Minimal templating: {key} replacement.
    out = template
    for k, v in ctx.items():
        out = out.replace("{" + str(k) + "}", str(v))
    return out


@dataclass(frozen=True)
class MatchDecision:
    include: bool
    include_scores: Dict[str, float]
    exclude_scores: Dict[str, float]
    best_include_keyword: str
    best_include_score: float
    best_exclude_keyword: str
    best_exclude_score: float


def _decide_include(
    filename: str,
    include_keywords: List[str],
    exclude_keywords: List[str],
    include_mode: str,
    min_similarity: float,
) -> MatchDecision:
    include_scores: Dict[str, float] = {}
    exclude_scores: Dict[str, float] = {}

    best_in_kw = ""
    best_in_sc = 0.0
    for kw in include_keywords:
        sc, _ = _best_keyword_score(kw, filename)
        include_scores[kw] = sc
        if sc > best_in_sc:
            best_in_sc = sc
            best_in_kw = kw

    best_ex_kw = ""
    best_ex_sc = 0.0
    for kw in exclude_keywords:
        sc, _ = _best_keyword_score(kw, filename)
        exclude_scores[kw] = sc
        if sc > best_ex_sc:
            best_ex_sc = sc
            best_ex_kw = kw

    include_mode = (include_mode or "any").strip().lower()
    if include_keywords:
        if include_mode == "all":
            include_ok = all(include_scores.get(kw, 0.0) >= min_similarity for kw in include_keywords)
        else:
            include_ok = any(include_scores.get(kw, 0.0) >= min_similarity for kw in include_keywords)
    else:
        include_ok = True  # if no include keywords, include everything not excluded

    exclude_ok = False
    if exclude_keywords:
        exclude_ok = any(exclude_scores.get(kw, 0.0) >= min_similarity for kw in exclude_keywords)

    return MatchDecision(
        include=bool(include_ok and not exclude_ok),
        include_scores=include_scores,
        exclude_scores=exclude_scores,
        best_include_keyword=best_in_kw,
        best_include_score=float(best_in_sc),
        best_exclude_keyword=best_ex_kw,
        best_exclude_score=float(best_ex_sc),
    )


def _iter_files(input_root: Path, patterns: List[str], recursive: bool) -> Iterable[Path]:
    if not patterns:
        patterns = ["*"]
    patterns = [p.strip() for p in patterns if p and str(p).strip()]
    if recursive:
        for p in input_root.rglob("*"):
            if not p.is_file():
                continue
            for pat in patterns:
                if fnmatch.fnmatch(p.name, pat):
                    yield p
                    break
    else:
        for p in input_root.iterdir():
            if not p.is_file():
                continue
            for pat in patterns:
                if fnmatch.fnmatch(p.name, pat):
                    yield p
                    break


def _copy_one(src: Path, dst: Path, overwrite: bool) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if not overwrite:
            return "exists_skip"
        try:
            dst.unlink()
        except Exception:
            pass
    shutil.copy2(src, dst)
    return "copied"


def collect_job(cfg: Dict[str, Any], job_name: str, *, dry_run: bool = False) -> Path:
    jobs = cfg.get("file_collect_jobs") or cfg.get("collect_jobs") or {}
    if not isinstance(jobs, dict) or job_name not in jobs:
        raise ValueError(f"Unknown collect job '{job_name}'. Define it under file_collect_jobs.")
    job = jobs[job_name] or {}
    if not isinstance(job, dict):
        raise ValueError(f"Collect job '{job_name}' must be a dict.")

    input_root_raw = str(job.get("input_root") or "").strip()
    if not input_root_raw:
        raise ValueError(
            "input_root is required for file collection jobs. "
            "Set file_collect_jobs.<job>.input_root in config or pass --input-root."
        )
    input_root = Path(input_root_raw).expanduser()
    if not input_root.exists():
        raise FileNotFoundError(f"input_root not found: {input_root}")

    recursive = bool(job.get("recursive", True))
    patterns = job.get("patterns") or job.get("include_patterns") or ["*"]
    if isinstance(patterns, str):
        patterns = [p.strip() for p in patterns.split(";") if p.strip()]
    patterns = list(patterns)

    include_keywords = job.get("include_keywords") or job.get("keywords") or []
    exclude_keywords = job.get("exclude_keywords") or []
    if isinstance(include_keywords, str):
        include_keywords = [k.strip() for k in include_keywords.split(",") if k.strip()]
    if isinstance(exclude_keywords, str):
        exclude_keywords = [k.strip() for k in exclude_keywords.split(",") if k.strip()]
    include_keywords = list(include_keywords)
    exclude_keywords = list(exclude_keywords)

    include_mode = str(job.get("include_mode") or "any")
    min_similarity = float(job.get("min_similarity", 0.85))
    overwrite = bool(job.get("overwrite", False))
    preserve_tree = bool(job.get("preserve_tree", False))

    basename_max_len = int(job.get("basename_max_len", 140))
    path_max_len = int(job.get("path_max_len", 240))

    extract_rules = job.get("extract") or []
    if not isinstance(extract_rules, list):
        extract_rules = []

    out_cfg = job.get("output") or {}
    if not isinstance(out_cfg, dict):
        out_cfg = {}
    out_root_raw = str(out_cfg.get("out_root") or "").strip()
    if not out_root_raw:
        raise ValueError(
            "output.out_root is required for file collection jobs. "
            "Set file_collect_jobs.<job>.output.out_root in config or pass --out-root."
        )
    out_root = Path(out_root_raw).expanduser()
    run_name_tpl = str(out_cfg.get("run_name_template") or "collect_{timestamp}_{job}")
    timestamp = _now_stamp()
    run_name = _safe_template_substitute(run_name_tpl, {"timestamp": timestamp, "job": job_name})
    out_dir = out_root / run_name

    dest_subdir_tpl = str(out_cfg.get("dest_subdir_template") or "")
    rename_tpl = str(out_cfg.get("rename_template") or "{orig_name}")

    # Copy manifest
    copied_root = out_dir / "copied"
    manifest_path = out_dir / "copy_manifest.csv"
    meta_path = out_dir / "run_metadata.json"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    copied = 0
    considered = 0

    for src in _iter_files(input_root, patterns, recursive=recursive):
        considered += 1
        dec = _decide_include(
            src.name,
            include_keywords=include_keywords,
            exclude_keywords=exclude_keywords,
            include_mode=include_mode,
            min_similarity=min_similarity,
        )
        if not dec.include:
            continue

        meta = _extract_meta(src, extract_rules)
        rel_dir = ""
        try:
            rel_dir = str(src.parent.relative_to(input_root))
        except Exception:
            rel_dir = ""

        ctx: Dict[str, Any] = {
            "job": job_name,
            "timestamp": timestamp,
            "orig_name": src.name,
            "orig_stem": src.stem,
            "ext": src.suffix,
            "rel_dir": rel_dir,
            "short_hash": _short_hash(str(src)),
        }
        ctx.update(meta)

        if preserve_tree:
            dest_rel_dir = rel_dir
        else:
            dest_rel_dir = _safe_template_substitute(dest_subdir_tpl, ctx).strip().strip("/\\")

        new_name = _safe_template_substitute(rename_tpl, ctx)
        # Ensure extension if template omitted it.
        if Path(new_name).suffix == "" and src.suffix:
            new_name = new_name + src.suffix
        new_name = _shorten_name(new_name, basename_max_len)

        dst = out_dir / "copied" / dest_rel_dir / new_name

        # Try to stay under path_max_len by shortening filename further if needed.
        dst_str = str(dst)
        if path_max_len > 0 and len(dst_str) > path_max_len:
            # Recompute with tighter basename limit.
            overflow = len(dst_str) - path_max_len
            new_limit = max(16, basename_max_len - overflow)
            short_name = _shorten_name(new_name, new_limit)
            dst = out_dir / "copied" / dest_rel_dir / short_name

        action = "dry_run" if dry_run else _copy_one(src, dst, overwrite=overwrite)
        if action == "copied":
            copied += 1

        rows.append(
            {
                "job": job_name,
                "timestamp": timestamp,
                "src_path": str(src),
                "dst_path": str(dst),
                "action": action,
                "best_include_keyword": dec.best_include_keyword,
                "best_include_score": f"{dec.best_include_score:.4f}",
                "best_exclude_keyword": dec.best_exclude_keyword,
                "best_exclude_score": f"{dec.best_exclude_score:.4f}",
            }
        )

    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "job",
                "timestamp",
                "src_path",
                "dst_path",
                "action",
                "best_include_keyword",
                "best_include_score",
                "best_exclude_keyword",
                "best_exclude_score",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Write a small machine-readable record so other scripts can chain off this output.
    try:
        meta = {
            "job": job_name,
            "timestamp": timestamp,
            "input_root": str(input_root),
            "out_dir": str(out_dir),
            "copied_root": str(copied_root),
            "considered": int(considered),
            "matched": int(len(rows)),
            "copied": int(copied),
            "dry_run": bool(dry_run),
            "min_similarity": float(min_similarity),
            "include_mode": str(include_mode),
            "include_keywords": list(include_keywords),
            "exclude_keywords": list(exclude_keywords),
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    except Exception:
        pass

    print(f"Considered: {considered}")
    print(f"Matched: {len(rows)}")
    print(f"Copied: {copied} (dry_run={dry_run})")
    print(f"Out dir: {out_dir}")
    print(f"Copied root: {copied_root}")
    print(f"Manifest: {manifest_path}")
    print(f"Metadata: {meta_path}")
    return out_dir


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Collect/copy files using config-driven fuzzy keyword matching.")
    ap.add_argument("--config", required=True, help="Path to config YAML.")
    ap.add_argument("--job", required=True, help="Job name under file_collect_jobs.")
    ap.add_argument("--input-root", default="", help="Override job input_root.")
    ap.add_argument("--out-root", default="", help="Override output.out_root.")
    ap.add_argument("--run-name", default="", help="Override output run folder name (under out_root).")
    ap.add_argument("--dry-run", action="store_true", help="Do not copy; only write manifest.")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    cfg = _load_config(args.config)
    # Apply CLI overrides to the job config (without mutating the loaded config).
    jobs = cfg.get("file_collect_jobs") or cfg.get("collect_jobs") or {}
    if not isinstance(jobs, dict) or args.job not in jobs:
        raise ValueError(f"Unknown collect job '{args.job}'. Define it under file_collect_jobs.")
    job = dict(jobs.get(args.job) or {})
    if args.input_root:
        job["input_root"] = args.input_root
    out_cfg = dict(job.get("output") or {})
    if args.out_root:
        out_cfg["out_root"] = args.out_root
    if args.run_name:
        out_cfg["run_name_template"] = args.run_name
    if out_cfg:
        job["output"] = out_cfg
    # Replace just this job definition for the call.
    cfg2 = dict(cfg)
    jobs2 = dict(jobs)
    jobs2[args.job] = job
    cfg2["file_collect_jobs"] = jobs2
    collect_job(cfg2, args.job, dry_run=bool(args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
