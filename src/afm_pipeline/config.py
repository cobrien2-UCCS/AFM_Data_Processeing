"""
Config loader for the AFM pipeline (YAML authoring; JSON fallback).

- Prefer YAML for authoring (Py3), per spec.
- Falls back to JSON if YAML is not available or the file extension is .json.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # YAML optional; JSON fallback

log = logging.getLogger(__name__)

REQUIRED_SECTIONS = [
    "channel_defaults",
    "modes",
    "grid",
    "csv_modes",
    "result_schemas",
    "plotting_modes",
]


def load_config(path: str | Path) -> Dict[str, Any]:
    """Load config from YAML (preferred) or JSON."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")

    suffix = p.suffix.lower()
    if suffix in [".yaml", ".yml"]:
        if yaml is None:
            raise RuntimeError("PyYAML not installed; cannot load YAML config.")
        with p.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    else:
        with p.open("r", encoding="utf-8") as f:
            cfg = json.load(f)

    _check_sections(cfg, p)
    return cfg


def _check_sections(cfg: Dict[str, Any], path: Path) -> None:
    """Warn if recommended top-level sections are missing (per spec)."""
    missing = [sec for sec in REQUIRED_SECTIONS if sec not in cfg]
    if missing:
        log.warning("Config %s missing sections: %s", path, ", ".join(missing))
