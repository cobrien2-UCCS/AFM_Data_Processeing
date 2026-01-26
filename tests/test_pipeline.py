import os
import sys
import csv
import unittest
import tempfile
from pathlib import Path
import json

# Ensure local package import without install
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for p in (REPO_ROOT, SRC_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

os.environ.setdefault("MPLBACKEND", "Agg")

from afm_pipeline import summarize_folder_to_csv, plot_summary_from_csv, load_config  # type: ignore # noqa: E402
from afm_pipeline.summarize import build_result_object_from_csv_row, build_csv_row  # type: ignore # noqa: E402
from scripts import run_pygwy_job  # type: ignore # noqa: E402


class PipelineTestCase(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "csv_modes": {
                "default_scalar": {
                    "columns": [
                        {"name": "source_file", "from": "core.source_file"},
                        {"name": "mode", "from": "core.mode"},
                        {"name": "metric_type", "from": "core.metric_type"},
                        {"name": "avg_value", "from": "core.avg_value"},
                        {"name": "std_value", "from": "core.std_value"},
                        {"name": "units", "from": "core.units"},
                        {"name": "nx", "from": "core.nx"},
                        {"name": "ny", "from": "core.ny"},
                    ],
                    "on_missing_field": "error",
                }
            },
            "result_schemas": {
                "default_scalar": {
                    "from_csv_mode": "default_scalar",
                    "fields": [
                        {"field": "source_file", "type": "string", "column": "source_file"},
                        {"field": "mode", "type": "string", "column": "mode"},
                        {"field": "metric_type", "type": "string", "column": "metric_type"},
                        {"field": "avg_value", "type": "float", "column": "avg_value"},
                        {"field": "std_value", "type": "float", "column": "std_value"},
                        {"field": "units", "type": "string", "column": "units"},
                        {"field": "nx", "type": "int", "column": "nx"},
                        {"field": "ny", "type": "int", "column": "ny"},
                    ],
                }
            },
            "plotting_modes": {
                "sample_bar_with_error": {
                    "result_schema": "default_scalar",
                    "recipe": "sample_bar_with_error",
                    "title": "Test Plot",
                }
            },
        }

    def test_build_csv_row_and_result_object(self):
        csv_def = self.cfg["csv_modes"]["default_scalar"]
        mode_result = {
            "core.source_file": "a.tif",
            "core.mode": "modulus_basic",
            "core.metric_type": "modulus",
            "core.avg_value": 1.23,
            "core.std_value": 0.1,
            "core.units": "GPa",
            "core.nx": 512,
            "core.ny": 512,
        }
        row = build_csv_row(mode_result, csv_def, "modulus_basic", "default_scalar")
        self.assertEqual(row[0], "a.tif")
        headers = [c["name"] for c in csv_def["columns"]]
        row_dict = dict(zip(headers, row))
        obj = build_result_object_from_csv_row(row_dict, "default_scalar", self.cfg)
        self.assertEqual(obj["mode"], "modulus_basic")
        self.assertAlmostEqual(obj["avg_value"], 1.23)
        self.assertEqual(obj["nx"], 512)

    def test_summarize_folder_to_csv_with_injected_processor(self):
        csv_def = self.cfg["csv_modes"]["default_scalar"]
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "f1.tif").write_bytes(b"")
            (root / "f2.tif").write_bytes(b"")

            def fake_processor(path, mode, cfg):
                return {
                    "core.source_file": path.name,
                    "core.mode": mode,
                    "core.metric_type": "modulus",
                    "core.avg_value": 2.0,
                    "core.std_value": 0.2,
                    "core.units": "GPa",
                    "core.nx": 256,
                    "core.ny": 256,
                }

            out_csv = root / "summary.csv"
            summarize_folder_to_csv(
                input_root=root,
                output_csv_path=out_csv,
                processing_mode="modulus_basic",
                csv_mode="default_scalar",
                cfg=self.cfg,
                processor=fake_processor,
            )

            with out_csv.open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["mode"], "modulus_basic")
            self.assertEqual(rows[0]["units"], "GPa")
            self.assertEqual(rows[0]["nx"], "256")

    def test_plot_summary_from_csv_generates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            csv_path = tmp / "summary.csv"
            with csv_path.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["source_file", "mode", "metric_type", "avg_value", "std_value", "units", "nx", "ny"])
                writer.writerow(["a.tif", "modulus_basic", "modulus", "1.5", "0.1", "GPa", "512", "512"])
            out_dir = tmp / "plots"
            plot_summary_from_csv(str(csv_path), "sample_bar_with_error", self.cfg, str(out_dir))
            plot_file = out_dir / "sample_bar_with_error.png"
            self.assertTrue(plot_file.exists(), "Plot file was not created")
            # Unit-aware ylabel should be set when not overridden; we read metadata from the PNG text fields if present.
            # Matplotlib does not store labels in PNG text by default, so we just assert file exists here.

    def test_plot_heatmap_grid_generates_file(self):
        cfg = dict(self.cfg)
        cfg["result_schemas"] = dict(cfg["result_schemas"])
        cfg["result_schemas"]["default_scalar"] = dict(cfg["result_schemas"]["default_scalar"])
        cfg["result_schemas"]["default_scalar"]["fields"] = list(cfg["result_schemas"]["default_scalar"]["fields"]) + [
            {"field": "row_idx", "type": "int", "column": "row_idx"},
            {"field": "col_idx", "type": "int", "column": "col_idx"},
        ]
        cfg["plotting_modes"] = dict(cfg["plotting_modes"])
        cfg["plotting_modes"]["heatmap_grid"] = {
            "result_schema": "default_scalar",
            "recipe": "heatmap_grid",
            "title": "Grid Heatmap",
            "colorbar_label": "avg_value",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            csv_path = tmp / "summary.csv"
            with csv_path.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["source_file", "mode", "metric_type", "avg_value", "std_value", "units", "nx", "ny", "row_idx", "col_idx"]
                )
                writer.writerow(["r0_c0.tif", "modulus_basic", "modulus", "1.0", "0.1", "GPa", "512", "512", "0", "0"])
                writer.writerow(["r0_c1.tif", "modulus_basic", "modulus", "2.0", "0.1", "GPa", "512", "512", "0", "1"])
                writer.writerow(["r1_c0.tif", "modulus_basic", "modulus", "3.0", "0.1", "GPa", "512", "512", "1", "0"])
                writer.writerow(["r1_c1.tif", "modulus_basic", "modulus", "4.0", "0.1", "GPa", "512", "512", "1", "1"])
            out_dir = tmp / "plots"
            plot_summary_from_csv(str(csv_path), "heatmap_grid", cfg, str(out_dir))
            plot_file = out_dir / "heatmap_grid.png"
            self.assertTrue(plot_file.exists(), "Heatmap plot file was not created")
            # As above, labels are not easily introspected from PNG without extra libraries; presence of file is our proxy.

    def test_build_csv_row_missing_field_error(self):
        csv_def = self.cfg["csv_modes"]["default_scalar"]
        # Remove a required key to trigger error
        mode_result = {
            "core.source_file": "a.tif",
            "core.mode": "modulus_basic",
            # "core.metric_type" missing
            "core.avg_value": 1.0,
            "core.std_value": 0.1,
            "core.units": "GPa",
            "core.nx": 128,
            "core.ny": 128,
        }
        with self.assertRaises(KeyError):
            build_csv_row(mode_result, csv_def, "modulus_basic", "default_scalar")

    def test_unit_conversion_and_mismatch_policy(self):
        manifest = {
            "mode_definition": {
                "metric_type": "modulus",
                "units": "GPa",
                "expected_units": "GPa",
                "on_unit_mismatch": "error",
            },
            "unit_conversions": {
                "modulus_basic": {
                    "MPa": {"target": "GPa", "factor": 0.001}
                }
            },
        }
        base = {
            "core.source_file": "a.tif",
            "core.mode": "modulus_basic",
            "core.metric_type": "modulus",
            "core.avg_value": 100.0,
            "core.std_value": 10.0,
            "core.units": "GPa",
            "core.nx": 1,
            "core.ny": 1,
        }
        # matching units
        applied = run_pygwy_job._apply_units(base.copy(), "modulus_basic", manifest["mode_definition"], manifest, "GPa")
        self.assertEqual(applied["core.units"], "GPa")
        # convertible units
        res_mpa = base.copy()
        res_mpa["core.avg_value"] = 200.0
        applied = run_pygwy_job._apply_units(res_mpa.copy(), "modulus_basic", manifest["mode_definition"], manifest, "MPa")
        self.assertAlmostEqual(applied["core.avg_value"], 0.2)
        self.assertEqual(applied["core.units"], "GPa")
        # mismatch skip_row
        mode_def_skip = manifest["mode_definition"].copy()
        mode_def_skip["on_unit_mismatch"] = "skip_row"
        skipped = run_pygwy_job._apply_units(base.copy(), "modulus_basic", mode_def_skip, manifest, "kPa")
        self.assertIsNone(skipped)

    def test_mask_outliers_builds_keep_mask(self):
        class FakeMaskField:
            def __init__(self, n):
                self._data = [0.0] * n

            def get_data(self):
                return self._data

        class FakeField:
            def __init__(self, data):
                self._data = list(data)

            def get_data(self):
                return self._data

            def create_full_mask(self):
                return FakeMaskField(len(self._data))

            def mask_outliers(self, mask_field, thresh):
                import math

                mean = sum(self._data) / float(len(self._data))
                sigma = math.sqrt(sum((v - mean) ** 2 for v in self._data) / float(len(self._data)))
                limit = float(thresh) * float(sigma)
                data = mask_field.get_data()
                for i, v in enumerate(self._data):
                    data[i] = 1.0 if abs(v - mean) > limit else 0.0

        field = FakeField([0.0, 0.0, 0.0, 0.0, 100.0])

        mask, kept, total = run_pygwy_job._build_single_mask(field, {"method": "outliers", "thresh": 1.5})
        self.assertEqual(total, 5)
        self.assertEqual(kept, 4)
        self.assertEqual(mask, [True, True, True, True, False])

        mask, kept, total = run_pygwy_job._build_single_mask(field, {"method": "outliers", "thresh": 1.5, "invert": True})
        self.assertEqual(total, 5)
        self.assertEqual(kept, 1)
        self.assertEqual(mask, [False, False, False, False, True])

    def test_mask_outliers2_builds_keep_mask(self):
        class FakeMaskField:
            def __init__(self, n):
                self._data = [0.0] * n

            def get_data(self):
                return self._data

        class FakeField:
            def __init__(self, data):
                self._data = list(data)

            def get_data(self):
                return self._data

            def create_full_mask(self):
                return FakeMaskField(len(self._data))

            def mask_outliers2(self, mask_field, thresh_low, thresh_high):
                import math

                mean = sum(self._data) / float(len(self._data))
                sigma = math.sqrt(sum((v - mean) ** 2 for v in self._data) / float(len(self._data)))
                lo = mean - float(thresh_low) * float(sigma)
                hi = mean + float(thresh_high) * float(sigma)
                data = mask_field.get_data()
                for i, v in enumerate(self._data):
                    data[i] = 1.0 if (v < lo or v > hi) else 0.0

        field = FakeField([0.0, 0.0, 0.0, 0.0, 100.0])
        mask, kept, total = run_pygwy_job._build_single_mask(field, {"method": "outliers2", "thresh_low": 1.5, "thresh_high": 1.5})
        self.assertEqual(total, 5)
        self.assertEqual(kept, 4)
        self.assertEqual(mask, [True, True, True, True, False])


if __name__ == "__main__":
    unittest.main()
