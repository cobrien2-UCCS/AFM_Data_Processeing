#!/usr/bin/env python3
"""
Environment and dependency checker for the AFM pipeline.

This utility verifies:
- Python version
- Required Python packages (import and minimum version)
- Presence of Gwyddion CLI and pygwy (`gwy` module) in the current interpreter
"""

import argparse
import importlib
import json
import re
import shutil
import subprocess
import sys
import platform

if sys.version_info[0] < 3:
    # This utility is designed for the Python 3 environment only.
    # Use it to validate the Py3 summarize/plot setup. For the Py2.7/pygwy
    # environment, simply verify that `import gwy` succeeds in that interpreter.
    sys.stderr.write(
        "check_env.py is intended for Python 3.x only. "
        "Run it under your Py3 environment to validate numpy/matplotlib/PyYAML.\n"
    )
    sys.exit(1)
try:
    import importlib.metadata as importlib_metadata  # type: ignore
except ImportError:
    try:
        import importlib_metadata  # type: ignore
    except ImportError:
        importlib_metadata = None

REQUIRED_PYTHON_MIN = (3, 8)

# Minimum versions are recommendations; adjust as the pipeline grows.
REQUIRED_PACKAGES = {
    "numpy": "1.22.0",
    "matplotlib": "3.6.0",
    "PyYAML": "6.0.0",
}

# Optional-but-useful packages.
OPTIONAL_PACKAGES = {
    "gwyfile": None,  # for reading .gwy files without pygwy
}


def _run_with_output(cmd):
    """Execute a command and return (returncode, stdout, stderr) as text."""
    try:
        proc = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except AttributeError:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        code = proc.returncode

    if not isinstance(stdout, str):
        stdout = stdout.decode("utf-8", "ignore")
    if not isinstance(stderr, str):
        stderr = stderr.decode("utf-8", "ignore")
    return code, stdout, stderr


def _normalize_version(version_str):
    """Convert a version string into a tuple of integers for rough comparison."""
    parts = []
    for token in re.split(r"[.+-]", version_str):
        token_digits = "".join(ch for ch in token if ch.isdigit())
        if token_digits:
            try:
                parts.append(int(token_digits))
            except ValueError:
                continue
    return tuple(parts)


def _version_ok(installed, minimum):
    """Best-effort version comparison without extra dependencies."""
    if not installed:
        return False
    if not minimum:
        return True
    return _normalize_version(installed) >= _normalize_version(minimum)


def check_python_version():
    current = sys.version_info
    ok = (current.major, current.minor) >= REQUIRED_PYTHON_MIN
    detail = "%s.%s.%s (min %s.%s)" % (
        current.major,
        current.minor,
        current.micro,
        REQUIRED_PYTHON_MIN[0],
        REQUIRED_PYTHON_MIN[1],
    )
    return {
        "component": "python",
        "required": True,
        "ok": ok,
        "detail": detail,
    }


def check_python_packages():
    results = []
    for package, min_version in REQUIRED_PACKAGES.items():
        entry = {
            "component": "python-package:%s" % package,
            "required": True,
            "ok": False,
            "detail": "",
        }
        try:
            importlib.import_module(package)
        except ImportError:
            entry["detail"] = "not installed"
            results.append(entry)
            continue

        installed_version = ""
        if importlib_metadata is not None:
            try:
                installed_version = importlib_metadata.version(package)
            except Exception:
                installed_version = ""

        if min_version and installed_version:
            entry["ok"] = _version_ok(installed_version, min_version)
            if entry["ok"]:
                entry["detail"] = "%s (>= %s)" % (installed_version, min_version)
            else:
                entry["detail"] = "%s (< %s)" % (installed_version, min_version)
        else:
            entry["ok"] = True
            detail_version = installed_version or "unknown version"
            entry["detail"] = "%s (no min specified)" % detail_version

        results.append(entry)
    return results


def check_optional_packages():
    results = []
    for package, min_version in OPTIONAL_PACKAGES.items():
        entry = {
            "component": "optional-package:%s" % package,
            "required": False,
            "ok": False,
            "detail": "",
        }
        try:
            importlib.import_module(package)
            entry["ok"] = True
            entry["detail"] = "installed"
        except ImportError:
            entry["ok"] = False
            entry["detail"] = "not installed (optional)"
        results.append(entry)
    return results


def check_gwyddion(required):
    results = []

    cli_path = shutil.which("gwyddion")
    if cli_path:
        try:
            code, stdout, stderr = _run_with_output(["gwyddion", "--version"])
            version_output = (stdout or stderr or "").strip()
            results.append(
                {
                    "component": "gwyddion-cli",
                    "required": required,
                    "ok": code == 0,
                    "detail": version_output if version_output else "exit code %s" % code,
                }
            )
        except Exception as exc:  # pragma: no cover - defensive
            results.append(
                {
                    "component": "gwyddion-cli",
                    "required": required,
                    "ok": False,
                    "detail": "failed to execute: %s" % exc,
                }
            )
    else:
        results.append(
            {
                "component": "gwyddion-cli",
                "required": required,
                "ok": False,
                "detail": "gwyddion not found on PATH",
            }
        )

    try:
        importlib.import_module("gwy")
        results.append(
            {
                "component": "pygwy-module",
                "required": required,
                "ok": True,
                "detail": "imported `gwy` in current interpreter",
            }
        )
    except ImportError:
        results.append(
            {
                "component": "pygwy-module",
                "required": required,
                "ok": False,
                "detail": (
                    "could not import `gwy`; ensure Gwyddion is installed and "
                    "use the interpreter that ships with pygwy (often Python 2.7)."
                ),
            }
        )

    return results


def check_architecture_for_pygwy():
    """Warn on Windows 64-bit because pygwy/Gwyddion typically ship 32-bit Python 2.7."""
    arch, _ = platform.architecture()
    is_windows = platform.system().lower().startswith("win")
    if is_windows and arch == "64bit":
        return {
            "component": "pygwy-arch-compat",
            "required": False,
            "ok": False,
            "detail": "Host Python is 64-bit; pygwy on Windows expects 32-bit Python 2.7 (install 32-bit Gwyddion).",
        }
    return {
        "component": "pygwy-arch-compat",
        "required": False,
        "ok": True,
        "detail": "%s Python; ensure pygwy-compatible interpreter when processing." % arch,
    }


def format_human(results):
    lines = []
    for entry in results:
        status = "OK" if entry.get("ok") else "MISSING"
        component = entry.get("component", "unknown")
        detail = entry.get("detail", "")
        lines.append("[%s] %-22s %s" % (status.ljust(7), component, detail))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Check Python and Gwyddion dependencies for the AFM pipeline."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit results as JSON instead of human-readable text.",
    )
    parser.add_argument(
        "--require-pygwy",
        action="store_true",
        help="Treat Gwyddion/pygwy components as required (use in pygwy/Py2 environment).",
    )
    args = parser.parse_args()

    results = []
    results.append(check_python_version())
    results.extend(check_python_packages())
    results.extend(check_optional_packages())
    results.extend(check_gwyddion(required=args.require_pygwy))
    results.append(check_architecture_for_pygwy())

    all_required_ok = all(
        entry.get("ok", False) or not entry.get("required", True) for entry in results
    )

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_human(results))

    return 0 if all_required_ok else 1


if __name__ == "__main__":
    sys.exit(main())
