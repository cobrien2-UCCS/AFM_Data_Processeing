import os
import sys
import unittest

py2 = sys.version_info[0] == 2

# Ensure local package import without install
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC_ROOT = os.path.join(REPO_ROOT, "src")
SCRIPTS_ROOT = os.path.join(REPO_ROOT, "scripts")
for p in (REPO_ROOT, SRC_ROOT, SCRIPTS_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)


def _can_import_gwy():
    try:
        import gwy  # noqa: F401
        return True
    except Exception:
        return False


@unittest.skipUnless(py2, "Py2/pygwy-specific tests; skipped on Py3.")
class Py2RunnerTests(unittest.TestCase):
    def test_try_import_pygwy_flag(self):
        import run_pygwy_job

        can = run_pygwy_job.try_import_pygwy()
        imported = _can_import_gwy()
        self.assertEqual(can, imported)

    def test_process_manifest_dry_run(self):
        import run_pygwy_job

        manifest = {
            "files": [],
            "output_dir": ".",
            "output_csv": "summary.csv",
            "csv_mode_definition": {},
            "processing_mode": "raw_noop",
            "csv_mode": "default",
        }
        # Should not raise when dry_run is True even with empty files list.
        run_pygwy_job.process_manifest(manifest, dry_run=True)


if __name__ == "__main__":
    unittest.main()
