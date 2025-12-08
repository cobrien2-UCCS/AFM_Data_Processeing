import os
import sys
import csv
import unittest
import tempfile
from pathlib import Path

# Ensure local package import without install
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("MPLBACKEND", "Agg")

from afm_pipeline import summarize_folder_to_csv, plot_summary_from_csv, load_config  # noqa: E402
from afm_pipeline.summarize import build_result_object_from_csv_row, build_csv_row  # noqa: E402


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

            rows = list(csv.DictReader(out_csv.open()))
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


if __name__ == "__main__":
    unittest.main()
