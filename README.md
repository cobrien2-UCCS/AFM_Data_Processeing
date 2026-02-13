# AFM-Data-Management Pipeline
Config-driven AFM TIFF processing (pygwy/Gwyddion), CSV summarization, and plotting. Support material for Conor O'Brien's thesis project. Defaults normalize modulus to kPa.

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
- Units: the pygwy runner reads field units, applies per-mode conversions from `unit_conversions`, and enforces `expected_units` with `on_unit_mismatch` (`error|warn|skip_row`). Modulus configs normalize everything to kPa (conversions for MPa/GPa/Pa included).
- Route clarity: set `modes.<mode>.stats_source` to `gwyddion` (masked stats via Gwyddion) or `python` (masked stats via Python). Mixed Gwyddion+Python routes are rejected unless `allow_mixed_processing: true` is set in the mode.
- Optional Python-side filtering/export: set `modes.<mode>.python_data_filtering` to export per-image CSVs (row,col,value,kept) after pygwy preprocessing and run `three_sigma`, `chauvenet`, and/or `min_max` filters before stats are computed.
- Grid indices: if `grid.filename_regex` changes, regenerate the manifest (otherwise `row_idx/col_idx` will remain `-1`).
- Plotting recipes: bar/hist/scatter, plus multiple heatmap variants (mean/std/CV/range), overlays (sigma-colored text, alpha/hatch), bubble overlay, and two-panel mean+std. Select via `plotting_modes`/profiles without changing code.

### Py3 helpers
- Plot from CSV (uses config.plotting_modes/result_schemas):
  ```bash
  python scripts/cli_plot.py --config config.yaml --csv summary.csv --plotting-mode sample_bar_with_error --out plots/
  # or use --profile to pick plotting_modes
  ```
- TIFF processing itself is performed by the Py2/pygwy runner (`scripts/run_pygwy_job.py`).

### Method comparison (Gwyddion-only baseline vs Python variants)
To compare multiple run outputs against a baseline summary CSV, use:
```powershell
py -3 scripts/compare_methods.py `
  --baseline-summary "out/verify_raw_trunc_gwyddion_only/config.modulus_gwyddion_only/summary.csv" `
  --methods-root "out/verify_raw_trunc_less_tuned" `
  --out-root "out/method_compare"
```
This writes `comparison_wide.csv` (Excel-friendly), `comparison_long.csv` (tidy), and plots under `out/method_compare/compare_<timestamp>/plots/`.

### Example config
See `config.example.yaml` for a starter config matching the spec structure:
- `channel_defaults`, `modes`, `grid`, `csv_modes`, `result_schemas`, `plotting_modes`, `profiles`.
- `summarize.recursive` controls recursive TIFF search for summarize.

Repo examples live in `configs/TEST configs/Example configs/`:
- `configs/TEST configs/Example configs/config.modulus_export_python_filters.yaml`
- `configs/TEST configs/Example configs/config.modulus_gwyddion_only.yaml`
Older/staging examples are kept under `configs/TEST configs/Depriciated configs/`.

### Tests
Run Py3 unit tests (covers summarize/plot helpers):
```bash
python -m unittest discover -s tests -p "test_*.py"
```

### Spec alignment / gaps
See `docs/SPEC_GAP_LIST.md` for a working checklist of spec alignment, gaps to shore up, and upcoming topography testing notes.

### User guide
See `docs/USER_GUIDE.md` for how to create configs, add modes/plots/CSV rules, unit handling, debug artifacts/logging, and expected outputs.

### Batch-run configs (optional helper)
Use `scripts/run_config_suite.py` to iterate over multiple configs, writing each to its own output folder:
```powershell
py -3 scripts/run_config_suite.py --configs configs\*.yaml --input-root scans\ --output-root out\suite --py2-exe "C:\Python27\python.exe" --profile modulus_grid
```
Each config gets its own `out\suite\<config-stem>\` with manifest, summary.csv, and plots.

### Debug (optional)
- Enable via `debug.enable: true` in your config (can be stored anywhere; pass `--config <path>`).
- Choose artifacts: `mask|leveled|aligned|filtered`, set `sample_limit`, and `out_dir` (defaults to `out/debug`); a Pillow/NumPy fallback writes TIFFs if pygwy export isn't available.
- Debug logs include units (detected or mode fallback), mask/stats counts, and grid indices when enabled.
