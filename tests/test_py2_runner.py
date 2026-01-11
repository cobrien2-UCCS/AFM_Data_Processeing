import sys
import unittest
from pathlib import Path

py2 = sys.version_info[0] == 2

# Ensure local package import without install
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for p in (REPO_ROOT, SRC_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def _can_import_gwy():
    try:
        import gwy  # noqa: F401
        return True
    except Exception:
        return False


@unittest.skipUnless(py2, "Py2/pygwy-specific tests; skipped on Py3.")
class Py2RunnerTests(unittest.TestCase):
    def test_try_import_pygwy_flag(self):
        from scripts import run_pygwy_job

        can = run_pygwy_job.try_import_pygwy()
        imported = _can_import_gwy()
        self.assertEqual(can, imported)

    def test_process_manifest_dry_run(self):
        if not _can_import_gwy():
            self.skipTest("pygwy not importable in this environment")
        from scripts import run_pygwy_job

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
