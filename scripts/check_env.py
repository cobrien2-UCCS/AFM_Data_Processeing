#!/usr/bin/env python
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
import os
import re
import shutil
import subprocess
import sys
import platform

try:
    import importlib.metadata as importlib_metadata  # type: ignore
except ImportError:
    try:
        import importlib_metadata  # type: ignore
    except ImportError:
        importlib_metadata = None

REQUIRED_PYTHON_MIN_PY3 = (3, 8)
REQUIRED_PYTHON_MIN_PY2 = (2, 7)

# NOTE: Distribution/package names are not always the same as import names.
# We store both to avoid false "missing" reports (e.g. PyYAML -> import yaml).
REQUIRED_PACKAGES_PY3 = [
    {"dist": "numpy", "import": "numpy", "min_version": "1.22.0"},
    {"dist": "matplotlib", "import": "matplotlib", "min_version": "3.6.0"},
    {"dist": "PyYAML", "import": "yaml", "min_version": "6.0.0"},
]

# pygwy/Gwyddion on Windows expects Python 2.7 + PyGTK2 (and 32-bit builds).
# These imports are a quick signal that the required runtime pieces are present.
REQUIRED_MODULES_PY2 = [
    {"dist": "pygtk", "import": "gtk", "min_version": None},
    {"dist": "pygobject", "import": "gobject", "min_version": None},
    {"dist": "pycairo", "import": "cairo", "min_version": None},
]

OPTIONAL_PACKAGES_PY3 = [
    {"dist": "gwyfile", "import": "gwyfile", "min_version": None},
]


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
    if current[0] >= 3:
        ok = (current[0], current[1]) >= REQUIRED_PYTHON_MIN_PY3
        detail = "%s.%s.%s (min %s.%s)" % (
            current[0],
            current[1],
            current[2],
            REQUIRED_PYTHON_MIN_PY3[0],
            REQUIRED_PYTHON_MIN_PY3[1],
        )
    else:
        ok = (current[0], current[1]) >= REQUIRED_PYTHON_MIN_PY2
        detail = "%s.%s.%s (min %s.%s)" % (
            current[0],
            current[1],
            current[2],
            REQUIRED_PYTHON_MIN_PY2[0],
            REQUIRED_PYTHON_MIN_PY2[1],
        )
    return {
        "component": "python",
        "required": True,
        "ok": ok,
        "detail": detail,
    }


def _dist_version(dist_name):
    if importlib_metadata is None:
        return ""
    try:
        return importlib_metadata.version(dist_name)
    except Exception:
        return ""


def check_python_packages():
    results = []
    if sys.version_info[0] >= 3:
        reqs = REQUIRED_PACKAGES_PY3
    else:
        # For Py2/pygwy environments, the required PyGTK modules are often
        # reachable only when the Gwyddion bin directory is on PATH (DLLs) and
        # sys.path. Bootstrap best-effort before checking imports.
        bin_dir = _find_gwyddion_bin()
        if bin_dir and os.path.isdir(bin_dir):
            if bin_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            if bin_dir not in sys.path:
                sys.path.insert(0, bin_dir)
            pygwy_dir = os.path.join(os.path.dirname(bin_dir), "share", "gwyddion", "pygwy")
            if os.path.isdir(pygwy_dir) and pygwy_dir not in sys.path:
                sys.path.insert(0, pygwy_dir)
        reqs = REQUIRED_MODULES_PY2

    for req in reqs:
        dist_name = req.get("dist")
        import_name = req.get("import") or dist_name
        min_version = req.get("min_version")
        entry = {
            "component": "python-package:%s" % dist_name,
            "required": True,
            "ok": False,
            "detail": "",
        }
        try:
            importlib.import_module(import_name)
        except ImportError:
            entry["detail"] = "not installed"
            results.append(entry)
            continue

        installed_version = _dist_version(dist_name)

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
    if sys.version_info[0] < 3:
        return results
    for req in OPTIONAL_PACKAGES_PY3:
        dist_name = req.get("dist")
        import_name = req.get("import") or dist_name
        min_version = req.get("min_version")
        entry = {
            "component": "optional-package:%s" % dist_name,
            "required": False,
            "ok": False,
            "detail": "",
        }
        try:
            importlib.import_module(import_name)
            entry["ok"] = True
            entry["detail"] = "installed" if not min_version else "installed (version not checked)"
        except ImportError:
            entry["ok"] = False
            entry["detail"] = "not installed (optional)"
        results.append(entry)
    return results


def _which(executable):
    try:
        return shutil.which(executable)  # Py3.3+
    except Exception:
        pass

    path = os.environ.get("PATH") or ""
    if not path:
        return None
    is_windows = platform.system().lower().startswith("win")
    exts = [""]
    if is_windows:
        pathext = os.environ.get("PATHEXT") or ".EXE;.BAT;.CMD;.COM"
        exts = [e.lower() for e in pathext.split(os.pathsep) if e]

    for p in path.split(os.pathsep):
        p = p.strip('"')
        if not p:
            continue
        for ext in exts:
            cand = os.path.join(p, executable)
            if is_windows and ext and not cand.lower().endswith(ext):
                cand = cand + ext
            if os.path.isfile(cand):
                return cand
    return None


def _find_gwyddion_bin():
    candidates = []
    env_bin = os.environ.get("GWY_BIN") or os.environ.get("GWYDDION_BIN")
    if env_bin:
        candidates.append(env_bin)

    exe_on_path = _which("gwyddion") or _which("gwyddion.exe")
    if exe_on_path:
        candidates.append(os.path.dirname(exe_on_path))

    candidates.extend(
        [
            r"C:\Program Files (x86)\Gwyddion\bin",
            r"C:\Program Files\Gwyddion\bin",
        ]
    )

    for bin_dir in candidates:
        if not bin_dir or not os.path.isdir(bin_dir):
            continue
        exe = os.path.join(bin_dir, "gwyddion.exe")
        if os.path.isfile(exe):
            return bin_dir
    return None


def _try_import_pygwy_with_bootstrap(bin_dir):
    try:
        importlib.import_module("gwy")
        return True, "imported `gwy` in current interpreter"
    except Exception:
        pass

    if not bin_dir or not os.path.isdir(bin_dir):
        return False, "gwyddion bin directory not found"

    try:
        if bin_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        if bin_dir not in sys.path:
            sys.path.insert(0, bin_dir)

        pygwy_dir = os.path.join(os.path.dirname(bin_dir), "share", "gwyddion", "pygwy")
        if os.path.isdir(pygwy_dir) and pygwy_dir not in sys.path:
            sys.path.insert(0, pygwy_dir)

        importlib.import_module("gwy")
        return True, "imported `gwy` after bootstrapping PATH/sys.path"
    except Exception as exc:
        return False, "could not import `gwy`: %s" % exc


def check_gwyddion(required):
    results = []

    bin_dir = _find_gwyddion_bin()
    if bin_dir:
        exe_path = os.path.join(bin_dir, "gwyddion.exe")
        try:
            code, stdout, stderr = _run_with_output([exe_path, "--version"])
            version_output = (stdout or stderr or "").strip()
            results.append(
                {
                    "component": "gwyddion-cli",
                    "required": required,
                    "ok": code == 0,
                    "detail": (
                        (version_output if version_output else "exit code %s" % code)
                        + " (%s)" % exe_path
                    ),
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
                "detail": "gwyddion not found (set GWY_BIN or add to PATH)",
            }
        )

    if sys.version_info[0] >= 3:
        results.append(
            {
                "component": "pygwy-module",
                "required": required,
                "ok": False,
                "detail": "pygwy is Python 2.7-only on Windows; run this check under 32-bit Python 2.7.",
            }
        )
    else:
        ok, detail = _try_import_pygwy_with_bootstrap(bin_dir)
        results.append(
            {
                "component": "pygwy-module",
                "required": required,
                "ok": ok,
                "detail": detail,
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
        if entry.get("ok"):
            status = "OK"
        else:
            status = "MISSING" if entry.get("required", True) else "WARN"
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
