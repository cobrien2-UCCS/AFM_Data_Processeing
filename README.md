# AFM-Data-Management Pipeline
Config-driven AFM TIFF processing (pygwy/Gwyddion), CSV summarization, and plotting. Support material for Conor O'Brien's thesis project.

## Quick start (Windows / PowerShell)
Run the full pipeline (Py3 -> Py2/pygwy -> Py3) from the repo root:

```powershell
.\scripts\run_pipeline.ps1 -InputRoot "C:\path\to\your\tiffs" -Profile modulus_grid -Plot
```

- Set `PYTHON2_EXE` if your Python 2.7 path is not `C:\Python27\python.exe`.
- Set `GWY_BIN` if your Gwyddion `bin` folder is not `C:\Program Files (x86)\Gwyddion\bin`.

## Environment check
Use the helper utility to confirm the expected Python packages and Gwyddion are present:

```bash
python scripts/check_env.py
```

- In the pygwy (Python 2.7, 32-bit) environment (PowerShell example):
  ```powershell
  cd "<repo root>"
  & "C:\Python27\python.exe" scripts\check_env.py --require-pygwy
  ```

- Returns non-zero if required components are missing.
- Use `--json` for machine-readable output.
- Install Python dependencies via `python -m pip install -r requirements.txt`.
- Optional (recommended): install the Py3 package for `python -m afm_pipeline.cli` and console scripts:
  `python -m pip install -e .`

### Gwyddion / pygwy notes (Windows)
- Gwyddion/pygwy on Windows is 32-bit and ships with Python 2.7; install the 32-bit Gwyddion build plus its pygtk runtime.
- The checker will flag a 64-bit host Python as incompatible for pygwy; use the interpreter bundled with Gwyddion when running pygwy modes.
- If you only need to read `.gwy` files outside pygwy, consider the optional `gwyfile` package (`python -m pip install gwyfile`).

#### Install resources (Windows)
- Official install guide (pygwy): https://gwyddion.net/documentation/user-guide-en/installation-ms-windows.html#installation-ms-windows-pygwy
- 32-bit PyGTK runtime and matching 32-bit Python 2.7: https://sourceforge.net/projects/gwyddion/files/pygtk-win32/
- Python-only `.gwy` reader (no pygwy): https://pypi.org/project/gwyfile/
- Community pygwy examples (reference only, unvetted): https://github.com/Drilack7/Python-Scripts-for-Gwyddion
- Required installers (mirrors):
  - Python 2.7.16 (32-bit MSI): https://sourceforge.net/projects/gwyddion/files/pygtk-win32/python-2.7.16.msi/download
  - pygobject-2.28.3.win32-py2.7.msi: https://sourceforge.net/projects/gwyddion/files/pygtk-win32/pygobject-2.28.3.win32-py2.7.msi/download
  - pycairo-1.8.10.win32-py2.7.msi: https://sourceforge.net/projects/gwyddion/files/pygtk-win32/pycairo-1.8.10.win32-py2.7.msi/download
  - pygtk-2.24.0.win32-py2.7.msi: https://sourceforge.net/projects/gwyddion/files/pygtk-win32/pygtk-2.24.0.win32-py2.7.msi/download
  - All-in-one (not recommended): https://sourceforge.net/projects/gwyddion/files/pygtk-win32/pygtk-all-in-one-2.24.2.win32-py2.7.msi/download

### Recommended dual-environment workflow
- Keep pygwy-dependent processing in a small Python 2.7 (32-bit) module/script that only uses pygwy/Gwyddion and writes neutral outputs (CSV/JSON/NumPy arrays) to disk.
- Run summarization/plotting/CLI in Python 3.x, consuming those neutral outputs. This avoids Py3-only imports in the Py2 layer and keeps Py2 surface minimal.
- If you need shared helpers, restrict them to pure I/O or other Py2-safe code, or maintain separate Py2/Py3 stubs.

#### Typical usage in an IDE (e.g., VS Code)
- Set your workspace interpreter to Python 3.x and install `requirements.txt`.
- From that env:
  - Run `python scripts/check_env.py`.
  - Generate manifests and plot.
- From the 32-bit Python 2.7 + pygwy env:
  - Run `C:\Python27\python.exe scripts\check_env.py --require-pygwy` (or your Python 2.7 path).
  - Run `C:\Python27\python.exe scripts\run_pygwy_job.py --manifest job_manifest.json` to process TIFFs.

### Processing philosophy
- Use Gwyddion/pygwy as the primary execution path for all leveling, filtering, and grain/particle operations.
- Allow Python-side math only for supplementary steps (e.g., clipping, unit conversions, aggregations) that are not available or are impractical in Gwyddion.
- When adding new modes, prefer Gwyddion modules first; use Python helpers as an explicit secondary step.

### Manifest bridge (YAML in Py3 -> JSON for Py2 pygwy)
- Author/edit the config in YAML (Python 3.x) and generate a JSON manifest for the Py2 runner:
  ```bash
  python scripts/make_job_manifest.py --config config.yaml --input-root scans/ --output-dir out/ --processing-mode modulus_basic --csv-mode default_scalar --out job_manifest.json
  # or use --profile to pull defaults from config.profiles
  ```
- The manifest contains: processing_mode, csv_mode, grid/channel defaults, mode/csv definitions, and the file list.
- Patterns: defaults to `*.tif;*.tiff`. Use `**/*.tif` (or similar) to recurse.
- Input filtering (optional): set `input_filters` in `config.yaml` (include/exclude regex) to drop Forward/Backward duplicates or other unwanted files during manifest generation.
- Typical workflow:
  - Py3: generate manifest.
  - Py2: run pygwy processing to produce summary CSV.
  - Py3: plot from the CSV.
- Run pygwy processing with the Py2.7 interpreter (32-bit) that ships with Gwyddion:
  ```powershell
  # PowerShell example (Windows):
  & "C:\Python27\python.exe" scripts\run_pygwy_job.py --manifest job_manifest.json
  ```
- Summarization/plotting stay in Python 3.x and consume the outputs written by the Py2 run.
- The Py2 runner writes `summary.csv` (or `--output-csv`) using the `csv_mode_definition` embedded in the manifest. pygwy is required; no fallback is executed to avoid producing invalid data. Implement real pygwy logic in `scripts/run_pygwy_job.py` where indicated.
- Units: the pygwy runner reads field units, applies optional conversions from `unit_conversions`, and enforces per-mode `expected_units` with `on_unit_mismatch` (`error|warn|skip_row`).
- Grid indices: if `grid.filename_regex` changes, regenerate the manifest (otherwise `row_idx/col_idx` will remain `-1`).

### Py3 helpers
- Plot from CSV (uses config.plotting_modes/result_schemas):
  ```bash
  python scripts/cli_plot.py --config config.yaml --csv summary.csv --plotting-mode sample_bar_with_error --out plots/
  # or use --profile to pick plotting_modes
  ```
- TIFF processing itself is performed by the Py2/pygwy runner (`scripts/run_pygwy_job.py`).

### Example config
See `config.example.yaml` for a starter config matching the spec structure:
- `channel_defaults`, `modes`, `grid`, `csv_modes`, `result_schemas`, `plotting_modes`, `profiles`.
- `summarize.recursive` controls recursive TIFF search for summarize.

### Tests
Run Py3 unit tests (covers summarize/plot helpers):
```bash
python -m unittest discover -s tests -p "test_*.py"
```

### User guide
See `docs/USER_GUIDE.md` for how to create configs, add modes/plots/CSV rules, unit handling, and expected outputs.
