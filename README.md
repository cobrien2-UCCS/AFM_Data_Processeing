# AFM-Data-Processeing
This Repo is for all things related to the data management of the my Thesis. It will include a MATLAB Data Storeage Class, which imports .tiff and .hdf5 files and creates a class for that data for analysis, and exports an .hdf5 for future Lab Calculations and better data management practices.

## Environment check
Use the helper utility to confirm the expected Python packages and Gwyddion are present:

```bash
python scripts/check_env.py
```

- Returns non-zero if required components are missing.
- Use `--json` for machine-readable output.
- Install Python dependencies via `python -m pip install -r requirements.txt`.

### Gwyddion / pygwy notes (Windows)
- Gwyddion/pygwy on Windows is 32-bit and ships with Python 2.7; install the 32-bit Gwyddion build plus its pygtk runtime.
- The checker will flag a 64-bit host Python as incompatible for pygwy; use the interpreter bundled with Gwyddion when running pygwy modes.
- If you only need to read `.gwy` files outside pygwy, consider the optional `gwyfile` package (`python -m pip install gwyfile`).

#### Install resources
- Official install guide (pygwy, Windows): https://gwyddion.net/documentation/user-guide-en/installation-ms-windows.html#installation-ms-windows-pygwy
- 32-bit PyGTK runtime and matching 32-bit Python 2.7 (required by pygwy on Windows): https://sourceforge.net/projects/gwyddion/files/pygtk-win32/
- Python-only `.gwy` reader (no pygwy): https://pypi.org/project/gwyfile/
- Community pygwy examples (reference only, unvetted): https://github.com/Drilack7/Python-Scripts-for-Gwyddion

#### pygwy prerequisites (Windows)
- Python 2.7 (e.g., python-2.7.16.msi; 32-bit) is required for pygwy.
- PyGTK2 stack: install PyGTK, PyCairo, and PyGObject for Python 2.7 (32-bit). The Gwyddion SourceForge mirrors include:
  - pygobject-2.28.3.win32-py2.7.msi
  - pycairo-1.8.10.win32-py2.7.msi
  - pygtk-2.24.0.win32-py2.7.msi
- An all-in-one installer (pygtk-all-in-one-2.24.2.win32-py2.7.msi) exists but installs GTK+ twice; use with caution. The separate installers are recommended.
// TODO: add direct download links for the installers above once confirmed.

### Recommended dual-environment workflow
- Keep pygwy-dependent processing in a small Python 2.7 (32-bit) module/script that only uses pygwy/Gwyddion and writes neutral outputs (CSV/JSON/NumPy arrays) to disk.
- Run summarization/plotting/CLI in Python 3.x, consuming those neutral outputs. This avoids Py3-only imports in the Py2 layer and keeps Py2 surface minimal.
- If you need shared helpers, restrict them to pure I/O or other Py2-safe code, or maintain separate Py2/Py3 stubs.

### Processing philosophy
- Use Gwyddion/pygwy as the primary execution path for all leveling, filtering, and grain/particle operations.
- Allow Python-side math only for supplementary steps (e.g., clipping, unit conversions, aggregations) that are not available or are impractical in Gwyddion.
- When adding new modes, prefer Gwyddion modules first; use Python helpers as an explicit secondary step.

### Manifest bridge (YAML in Py3 → JSON for Py2 pygwy)
- Author/edit the config in YAML (Python 3.x) and generate a JSON manifest for the Py2 runner:
  ```bash
  python scripts/make_job_manifest.py --config config.yaml --input-root scans/ --output-dir out/ --processing-mode modulus_basic --csv-mode default_scalar --out job_manifest.json
  # or use --profile to pull defaults from config.profiles
  ```
- The manifest contains: processing_mode, csv_mode, grid/channel defaults, mode/csv definitions, and the file list.
- Run pygwy processing with the Py2.7 interpreter (32-bit) that ships with Gwyddion:
  ```bash
  python2 scripts/run_pygwy_job.py --manifest job_manifest.json
  ```
- Summarization/plotting stay in Python 3.x and consume the outputs written by the Py2 run.
- The Py2 runner writes `summary.csv` (or `--output-csv`) using the `csv_mode_definition` embedded in the manifest. pygwy is required; no fallback is executed to avoid producing invalid data. Implement real pygwy logic in `scripts/run_pygwy_job.py` where indicated.
- Units: the pygwy runner reads field units, applies optional conversions from `unit_conversions`, and enforces per-mode `expected_units` with `on_unit_mismatch` (`error|warn|skip_row`).

### Py3 CLI helpers
- Summarize TIFFs to CSV (uses config.modes/csv_modes):
  ```bash
  python scripts/cli_summarize.py --config config.yaml --input-root scans/ --out-csv summary.csv --processing-mode modulus_basic --csv-mode default_scalar
  # or use --profile to pull defaults
  ```
- Plot from CSV (uses config.plotting_modes/result_schemas):
  ```bash
  python scripts/cli_plot.py --config config.yaml --csv summary.csv --plotting-mode sample_bar_with_error --out plots/
  # or use --profile to pick plotting_modes
  ```

### Example config
See `config.example.yaml` for a starter config matching the spec structure:
- `channel_defaults`, `modes`, `grid`, `csv_modes`, `result_schemas`, `plotting_modes`, `profiles`.

### Tests
Run Py3 unit tests (covers summarize/plot helpers):
```bash
python -m unittest discover -s tests -p "test_*.py"
```
