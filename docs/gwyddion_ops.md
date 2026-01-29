# Gwyddion/pygwy Processing Methods (Pipeline Reference)

This repo uses **Gwyddion's Python API ("pygwy")** from the Py2 runner to preprocess AFM TIFFs and compute summary statistics.

- **Runner:** `scripts/run_pygwy_job.py` (Python 2.7 + 32-bit Gwyddion/pygwy on Windows)
- **Config entrypoint:** `modes.<mode>.gwyddion_ops` (ordered list of operations)

The goal of this doc is to list what the pipeline supports today, what args it accepts, how to use it in practice, and (when possible) the closest equivalent in the Gwyddion GUI.

## Quick context: how pygwy operations work

The runner uses two styles of operations:

1) **`DataField` methods** (operate directly on a `gwy.DataField` object)
- Examples: plane leveling via `fit_plane()`/`plane_level()`, median filter via `filter_median()`.

2) **GUI/process functions** via `gwy.gwy_process_func_run()`
- Used when an operation is implemented as a GUI module (not just a `DataField` method).
- These often read parameters from **app settings** (`gwy.gwy_app_settings_get()`), just like the GUI.
- In this repo, **Align Rows** is run this way because it uses the `linematch` module.

Gwyddion reference docs (official):
- Python scripting overview: https://gwyddion.net/documentation/user-guide-en/pygwy.html
- pygwy API reference: https://gwyddion.net/documentation/head/pygwy/

## Config schema for `gwyddion_ops`

Each list item is a dict with:
- `op` (or `name`): operation name (case-insensitive; `-` and spaces become `_`)
- `params`: optional dict of args

Example (from `configs/TEST configs/Example configs/config.modulus_suite.yaml`):

```yaml
modes:
  modulus_complex:
    gwyddion_ops:
      - { op: "plane_level" }
      - { op: "align_rows", params: { direction: "horizontal", method: "median" } }
      - { op: "median", params: { size: 3 } }
      - { op: "clip_percentiles", params: { low: 0.5, high: 99.5 } }
```

In practice:
1) Put `gwyddion_ops` under your chosen mode in a config yaml.
2) Generate a manifest (Py3): `python scripts/make_job_manifest.py --config config.yaml --input-root <tiffs> --output-dir out --processing-mode <mode> --csv-mode <csv_mode> --out out/job_manifest.json`
3) Run processing (Py2): `& "C:\\Python27\\python.exe" scripts\\run_pygwy_job.py --manifest out\\job_manifest.json`

For end-to-end usage (`manifest → pygwy → plots`), see `docs/USER_GUIDE.md`.

## Operation reference (supported today)

### 1) `plane_level`

**What it does:** Fits and subtracts a best-fit plane.

**Pipeline implementation:** `DataField.fit_plane()` then `DataField.plane_level(pa, pbx, pby)`.

**Config:**
```yaml
- { op: plane_level }
```

**Args:** none (any `params` are currently ignored).

**GUI equivalent:** `Data Process → Level → Plane Level`  
Docs: https://gwyddion.net/documentation/user-guide-en/leveling-and-background.html#plane-level

---

### 2) `align_rows` (scan-line correction / linematch)

**What it does:** Corrects scan-line artefacts by aligning rows/columns using one of Gwyddion's linematch methods.

**Pipeline implementation:**
- Selects the active field in the data browser
- Writes app settings:
  - `/module/linematch/direction` (horizontal/vertical)
  - `/module/linematch/method` (integer method id)
  - `/module/linematch/do_extract` (false)
  - `/module/linematch/do_plot` (false)
- Runs: `gwy.gwy_process_func_run("align_rows", container, gwy.RUN_IMMEDIATE)`

**Config:**
```yaml
- op: align_rows
  params:
    direction: horizontal   # strongly recommended (avoid stale GUI settings)
    method: median          # optional; defaults to median
```

**Args (`params`):**
- `enable` (bool, default `true`)
- `direction` (`horizontal`|`vertical`)  
  - If omitted, Gwyddion may use the last GUI setting; set it explicitly.
- `method` (string) or `method_id` (int)
  - If both are set, `method_id` wins.
  - Supported method names (mapped to ids in the runner):
    - `median` (0)
    - `modus` (1)
    - `polynomial` (2)
    - `median_difference` (3)
    - `matching` (4)
    - `facet_level_tilt` (5)
    - `trimmed_mean` (6)
    - `trimmed_mean_difference` (7)

**GUI equivalent:** `Data Process → Correct Data → Align Rows`  
Docs: https://gwyddion.net/documentation/user-guide-en/scan-line-defects.html#line-correction

**Practical note (row + column correction):**
Running Align Rows in both directions is a common workflow for scan artefacts:
```yaml
gwyddion_ops:
  - { op: align_rows, params: { direction: horizontal, method: median } }
  - { op: align_rows, params: { direction: vertical, method: median } }
```

#### Alternative config: `modes.<mode>.line_correct`

The runner also supports a single “Align Rows” step as `line_correct`, applied before `gwyddion_ops`:

```yaml
modes:
  modulus_basic:
    line_correct:
      enable: true
      direction: horizontal
      method: median        # or method_id: 0..7
```

Prefer `gwyddion_ops` when you need explicit ordering, repetition, or to keep everything in one list. Avoid configuring both `line_correct` and an `align_rows` op unless you intend to run Align Rows twice.

---

### 3) `median`

**What it does:** Median filter denoising on the data field.

**Pipeline implementation:** `DataField.filter_median(size)`.

**Config:**
```yaml
- op: median
  params: { size: 3 }
```

**Args (`params`):**
- `size` (int, default `3`)  
  - Use odd values (3, 5, 7…) to match typical neighbourhood definitions.

**GUI equivalent:** Filters tool → “Median value” (Basic Filters Tool)  
Docs: https://gwyddion.net/documentation/user-guide-en/filters.html#basic-filters

---

### 4) `clip_percentiles` (Python-side helper)

**What it does:** Clamps field values to the `[low, high]` percentiles (computed from the current field values).

**Pipeline implementation:** Python-side percentile computation and in-place clipping (`_field_clip_percentiles()`).

**Config:**
```yaml
- op: clip_percentiles
  params: { low: 0.5, high: 99.5 }
```

**Args (`params`):**
- `low` (float, default `0.0`)  — percentile in [0, 100]
- `high` (float, default `100.0`) — percentile in [0, 100]

**GUI equivalent:** none 1:1 (conceptually similar to histogram-based clipping).

## Line correction legacy flags (avoid for new configs)

Older configs may use:
- `line_level_x: true`
- `line_level_y: true`

In the runner these are treated as “Align Rows median” (horizontal then vertical). Prefer `gwyddion_ops` for explicit ordering and repeatability.

## Masking / ROI methods (affect stats, not the image)

Config: `modes.<mode>.mask`

Masking builds a boolean mask and summary stats (avg/std/min/max/n_valid) are computed **only over included pixels**.

Supported methods:

### `threshold`
```yaml
mask:
  enable: true
  method: threshold
  threshold: 0.0
  direction: above      # above|below
  include_equal: true
  invert: false
```

### `range`
```yaml
mask:
  enable: true
  method: range
  min_value: 200.0      # optional
  max_value: 100000.0   # optional
  inclusive: true
  invert: false
```

### `percentile`
```yaml
mask:
  enable: true
  method: percentile
  percentiles: [5, 95]
  inclusive: true
  invert: false
```

### `outliers` / `outliers2` (Gwyddion-native outlier marking)

These use `DataField.mask_outliers()` / `DataField.mask_outliers2()` (computed after preprocessing).
They mark pixels more than `thresh * σ` away from the mean (σ = RMS deviation).
The pipeline inverts the Gwyddion mask so the default behavior is **keep non-outliers**; set `invert: true` to keep only outliers.

```yaml
mask:
  enable: true
  method: outliers
  thresh: 3.0
```

```yaml
mask:
  enable: true
  method: outliers2
  thresh_low: 3.0
  thresh_high: 3.0
```

**GUI equivalent:** `Data Process → Correct Data → Mask of Outliers`  
Docs: https://gwyddion.net/documentation/user-guide-en/editing-correction.html#mask-of-outliers

### Multi-step masks (`combine: and|or`)

```yaml
mask:
  combine: and
  steps:
    - { method: threshold, threshold: 0.0, direction: above }
    - { method: percentile, percentiles: [5, 95] }
  on_empty: error     # error|warn|blank|skip_row
```

## Grain / particle counting (mode: `particle_count_basic`)

The runner supports a basic particle mode that:
- thresholds the field into a binary mask
- labels grains (`number_grains()`)
- extracts grain sizes and derived diameters
- optionally reads circularity (`GrainQuantity.CIRCULARITY`)

Closest GUI equivalents live under Grain Analysis (threshold marking + grain statistics):
- Grain analysis overview: https://gwyddion.net/documentation/user-guide-en/grain-analysis.html

## Units (what the runner reads)

- Z units: `field.get_si_unit_z().get_unit_string()`
- Area (real units): `field.get_xreal() * field.get_yreal()`

If a TIFF has missing Z-units, the runner behavior is controlled by:
- `on_missing_units: error|warn|skip_row`
- `assume_units: "kPa"` (explicit opt-in to assign a unit when the file has none)

## Debugging: verifying parity vs GUI

For side-by-side validation against Gwyddion GUI workflows, enable debug traces:

```yaml
debug:
  enable: true
  trace_dir: out/debug/traces
  stats_provenance: true
```

The runner writes per-file `*.trace.json` step records (including before/after stats snapshots when enabled), and optional debug artifact TIFFs (`mask`, `aligned`, `leveled`, `filtered`) when requested via `debug.artifacts`.

## Next Gwyddion ops to consider (not implemented yet)

These exist in the GUI and are referenced in the Gwyddion docs, but are not wired into `gwyddion_ops` yet:
- `Flatten Base` (`Data Process → Level → Flatten Base`)  
  Docs: https://gwyddion.net/documentation/user-guide-en/leveling-and-background.html#flatten-base
- `Polynomial Background` (`Data Process → Level → Polynomial Background`)  
  Docs: https://gwyddion.net/documentation/user-guide-en/leveling-and-background.html#polynomial-level

When adding new ops, prefer:
1) Prototype in the GUI
2) Identify the process function name (often matches module id, e.g. `flatten_base`)
3) Determine any required app settings keys (`/module/<name>/...`)
4) Add a new handler in `_apply_ops_sequence()` and document it here
