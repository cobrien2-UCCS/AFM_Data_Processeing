> [!Important] Python Limits from Gwyddion
> >[!Quote] [Python Scripting DOC First Lines](https://gwyddion.net/documentation/user-guide-en/pygwy.html?utm_source=chatgpt.com)
> > > Pygwy only works with Python 2.7. Any Python 3 version that might exist in future will have to be created from scratch and will not be backward compatible. 
> > > 
> > > Python scripting allows you to automate data SPM processing tasks, both within Gwyddion and by using its functionality in standalone Python scripts run outside Gwyddion. The scripts can range from simple macro-like executions of several functions in sequence to complex programs combining data from multiple files and utilising third-party libraries or programs.

# **1. FrontMatter: Overview, Purpose, and Usage Context**

This document defines the architecture, data flow, configuration model, and operational conventions for the **AFM TIFF → Summary Statistics → Plotting Pipeline**.  
It is written to provide a clear mental model for both **human developers** and **automated code agents** designing or extending this system.

The pipeline transforms folders of AFM TIFF images into structured tabular summaries and configurable visualizations by applying reproducible, configuration-driven processing modes. All computational behavior is declarative: users modify **configuration files** rather than rewriting code.

---

## **1.1 Purpose of the Pipeline**

Modern AFM workflows often produce:

- scattered TIFF files
    
- inconsistent naming conventions
    
- ad-hoc processing steps
    
- manual, irreproducible statistics
    
- one-off plotting scripts
    

This system replaces that with a **structured, reproducible, mode-driven workflow**:

```text

TIFF file  
→ Gwyddion-based processing (mode)  
→ ModeResultRecord (key–value dictionary)  
→ CSV summary (csv_mode)  
→ Typed rows (result_schema)  
→ Visualization (plotting_mode)

```

The pipeline supports:

- Topography metrics
    
- Modulus maps
    
- Particle/grain statistics
    
- Custom scalar modes
    
- Grid-indexed heatmaps
    
- User-defined CSV layouts
    
- Plotting recipes that follow definable schemas
    

Every part of the pipeline is modular and replaceable. No step hard-codes assumptions about file structure, column ordering, or AFM channel names.

---

## **1.2 Audience and Expected Usage**

This system is designed for three user groups:

### **1. Engineers / Researchers**

They run:

- `summarize_folder_to_csv` to process scans under a chosen **processing_mode**
    
- `plot_summary_from_csv` using a **plotting_mode**
    

They modify YAML/JSON configuration to introduce:

- new processing modes
    
- new CSV layouts
    
- new plotting recipes
    

### **2. Developers Extending the Pipeline**

They add:

- new branches inside `APPLY_MODE_PIPELINE`
    
- new Gwyddion operations via pygwy modules
    
- custom result schemas and plotting modes
    

All while respecting the configuration-driven separation of concerns.

### **3. Automated Code Generators (LLM Agents, Codex, Manus)**

They must follow strict guardrails:

- **Do not hard-code CSV column counts or order**
    
- **Do not embed mode logic inside summarization or plotting layers**
    
- **Do not add new global state**
    
- **Express all behavioral variation in config, not code**

- Leave Comments in Code explaining everything in detail with inline or front matter comments

These constraints ensure reproducibility and prevent model drift from corrupting the architecture.

---

## **1.3 High-Level Architectural Principles**

This pipeline is built around four principles:

### **Principle 1: Declarative Configuration**

Modes, CSV layouts, result schemas, and plotting behaviors are all described in configuration files.  
Code remains generic; configuration determines behavior.

### **Principle 2: Clear Separation of Responsibilities**

|Component|Responsibility|
|---|---|
|**processing_mode**|Defines Gwyddion operations + metric_type|
|**csv_mode**|Defines CSV column structure and mapping rules|
|**result_schema**|Defines how CSV rows become typed objects|
|**plotting_mode**|Defines which schema a plot consumes and which recipe to call|

No component reaches into another’s domain.

### **Principle 3: Minimal, Predictable Core API**

All pipeline entrypoints follow simple, stable signatures:

```text

summarize_folder_to_csv(input_root, output_csv, processing_mode, csv_mode, cfg)

plot_summary_from_csv(csv_path, plotting_mode, cfg, output_dir)

process_tiff_with_gwyddion(path, mode, cfg) 

APPLY_MODE_PIPELINE(field, source_file, mode, cfg)

```

This makes the architecture testable, predictable, and safe for long-term maintenance.

### **Principle 4: Reproducible, Extensible Data Flow**

Every dataset processed with the same config and inputs yields identical outputs.  
Creating new modes or plots requires only:

- adding a new config block
    
- optionally adding a new branch in `APPLY_MODE_PIPELINE`
    
- adding a new `PLOT_*` recipe
    

The system never needs redesign for additional use cases.

---

## **1.4 Configuration-Driven Workflow**

A complete run is governed by **five configuration sections**:

```text

channel_defaults:  how AFM channels are identified
modes:             how TIFFs are processed
grid:              how grid indices are derived
csv_modes:         how ModeResultRecord → CSV rows
result_schemas:    how CSV rows → typed objects
plotting_modes:    which schema a plot requires

```

Optionally, users may define **profiles** representing specific scenarios:

```text

profiles:
  pla_modulus_grid:
    processing_mode: "modulus_basic"
    csv_mode:        "default_scalar"
    plotting_modes:  ["sample_bar_with_error", "heatmap_grid"]

```

This allows one-line commands such as:

```text

afm-summarize --profile pla_modulus_grid --input-root scans/ --out summary.csv
afm-plot      --profile pla_modulus_grid --csv summary.csv --out plots/

```

Configuration layering is allowed:

- a single file
    
- multiple categorical files
    
- scenario overrides
    
- environment-based profiles
    

What matters is the **final merged dictionary** (`cfg`) the pipeline receives.

---

## **1.5 Data Flow Overview**

### **1.5.1 ModeResultRecord**

Each TIFF produces a dict of values:

```text

core.source_file
core.mode
core.metric_type
core.avg_value
core.std_value
core.units
core.nx
core.ny
grid.row_idx
grid.col_idx
particle.*

```

Each mode defines _which keys it guarantees_, and CSV modes determine how they map into a table.

---

### **1.5.2 CSV Summary**

A csv_mode defines:

- column ordering
    
- key mappings
    
- default behavior for missing fields
    
- error/warning policy
    

This allows custom CSV layouts **without touching code**.

---

### **1.5.3 Result Schemas**

Schemas define how CSV columns become typed objects.  
Plotting modes then declare which schema they require.

This prevents plots from relying on raw CSV rows or guessing about file structure.

---

### **1.5.4 Plotting Pipeline**

Plotting proceeds as:

`CSV → result_schema → PLOT_* → matplotlib figure`

Plotting modes choose the recipe; recipes consume typed rows.

No statistical or processing logic resides in plotting.

---

## **1.6 Intended Extensions**

The architecture is explicitly designed to support:

- new AFM operations
    
- multi-step Gwyddion pipelines
    
- custom particle metrics
    
- multi-mode comparative dashboards
    
- domain-specific CSV layouts
    
- additional plotting templates
    
- integration into larger HDF5-based pipelines
    

None of these require architectural modification—only new config entries and optional additional branches in processing or plotting.

---

## **1.7 Out-of-Scope Features**

Intentionally excluded from the core architecture:

- file manifest utilities
    
- automatic file grouping
    
- implicit grid detection without config
    
- dynamic CSV schemas tied to per-run data
    
- automatic plot saving toggles
    
- interactive GUIs
    

These may be implemented externally but are not part of the pipeline’s stable API.

---

## **1.8 Core Guarantees**

- **Deterministic output** given (TIFFs, processing_mode, csv_mode, cfg).
    
- **No hidden assumptions** about file names or channel semantics.
    
- **No hard-coded column positions or metric types.**
    
- **Modular, replaceable components** for processing, summarization, and plotting.
    
- **Config-first architecture:** behavior is declarative, not embedded in code.
    
- **Testability:** each layer can be unit-tested independently using mocks.
    

---

## **1.9 What This Document Provides (and What Comes Next)**

This FrontMatter establishes:

- the philosophy
    
- high-level system behavior
    
- user expectations
    
- LLM guardrails
    
- the mental model needed to navigate the rest of the spec
    

Subsequent sections provide:

- detailed data models
    
- configuration schemas
    
- processing logic
    
- pseudocode for all core functions
    
- plotting specifications
    
- helper function definitions
    
- code generation / Codex implementation guide
    

Together, these form the complete definition of the AFM Summary Stats & Plotting Pipeline v2.

---
## 2. DATA MODELS
This pipeline is now explicitly **config- and CSV-mode driven**. The flow is:

1. Gwyddion processing produces a **mode result record** which corresponds to the mode chosen by the processing config to chose the data structure via an untyped dictionary of keys and values for that image.
    
2. A **CSV mode** definition describes:
    
    - which keys from the record to write as columns
        
    - how to name those columns
        
3. A **result schema** definition describes how to **rebuild typed objects from CSV rows** when needed (e.g., for plotting).
    

### 2.1 Core concepts

- **Processing mode**  
    A named recipe (`"modulus_basic"`, `"particle_count_basic"`, etc.) that tells Gwyddion what to do to a TIFF:  
    plane leveling, line correction, filters, particle detection, etc.
    
- **Mode result record**  
    A **per-image map** of key → value produced by the processing step.  
    This is the _only_ thing `process_tiff_with_gwyddion` guarantees.
    
- **CSV mode**  
    A configuration block that defines:
    
    - which keys from the mode result record are written to CSV
        
    - column names and ordering
        
    - default values and behavior when a key is missing
        
- **Result schema**  
    A configuration block that defines how to **interpret a CSV row** as a typed object usable by plotting or other analysis code.
    

### 2.2 Mode result record

Each TIFF processed by Gwyddion yields a **ModeResultRecord**:

```pseudocode

STRUCT ModeResultRecord:
    values: DICT<STRING, ANY>

```
The dictionary must at least include a minimal “core” set of keys, but this is **enforced by config, not by the function signature**.

Recommended core keys (convention, not hard-coded struct):

```text

core.source_file       // STRING: basename of TIFF
core.mode              // STRING: processing mode name
core.metric_type       // STRING: "modulus", "topography_height", "particle_count", etc.
core.avg_value         // FLOAT: scalar metric for this image
core.std_value         // FLOAT: scalar uncertainty or spread
core.units             // STRING: e.g. "GPa", "nm", "count"
core.nx                // INT: x-resolution (pixels)
core.ny                // INT: y-resolution (pixels)

```
Mode-specific or optional outputs attach more keys:
```text

particle.count_total           // INT
particle.count_density         // FLOAT
particle.mean_diameter_px      // FLOAT
particle.std_diameter_px       // FLOAT
particle.mean_circularity      // FLOAT
particle.std_circularity       // FLOAT

grid.row_idx                   // INT (zero-based)
grid.col_idx                   // INT (zero-based)

```
Each processing mode is responsible for **filling the keys it claims to support**. The CSV layer decides which of these keys become columns.

### 2.3 CSV modes
CSV modes define **how to serialize a ModeResultRecord into a row**.

Conceptual config structure (YAML-ish):

```yaml

csv_modes:
  default_scalar:
    columns:
      - { name: "source_file", from: "core.source_file" }
      - { name: "mode",        from: "core.mode" }
      - { name: "metric_type", from: "core.metric_type" }
      - { name: "avg_value",   from: "core.avg_value" }
      - { name: "std_value",   from: "core.std_value" }
      - { name: "units",       from: "core.units" }
      - { name: "nx",          from: "core.nx" }
      - { name: "ny",          from: "core.ny" }
      - { name: "row_idx",     from: "grid.row_idx", default: -1 }
      - { name: "col_idx",     from: "grid.col_idx", default: -1 }

    on_missing_field: "warn_null"   # or "error", "skip_row"

  particle_metrics:
    columns:
      - { name: "source_file",    from: "core.source_file" }
      - { name: "mode",           from: "core.mode" }
      - { name: "metric_type",    from: "core.metric_type" }
      - { name: "count_total",    from: "particle.count_total" }
      - { name: "count_density",  from: "particle.count_density" }
      - { name: "mean_diam_px",   from: "particle.mean_diameter_px" }
      - { name: "std_diam_px",    from: "particle.std_diameter_px" }
      - { name: "mean_circ",      from: "particle.mean_circularity" }
      - { name: "std_circ",       from: "particle.std_circularity" }
      - { name: "nx",             from: "core.nx" }
      - { name: "ny",             from: "core.ny" }
      - { name: "row_idx",        from: "grid.row_idx", default: -1 }
      - { name: "col_idx",        from: "grid.col_idx", default: -1 }

    on_missing_field: "warn_null"   # or "error", "skip_row"

```
The summarization code doesn’t know about “SummaryRow”. It only:

1. Reads a **ModeResultRecord**.
    
2. Looks up the csv_mode.
    
3. Pulls keys accordingly and writes a row.
    

The CSV header becomes:

```text

source_file,mode,metric_type,avg_value,std_value,units,nx,ny,row_idx,col_idx

```
for `default_scalar`, or the longer particle header for `particle_metrics`.

### 2.4 Result schemas (for reading CSV)

Plotting and later stages don’t want raw CSV dictionaries; they want typed rows.  
Result schemas specify how to go from CSV → object, symmetric with csv_modes.

Conceptual config  Example:
```yaml

result_schemas:
  default_scalar:
    from_csv_mode: "default_scalar"
    fields:
      - { field: "source_file", type: "string", column: "source_file" }
      - { field: "mode",        type: "string", column: "mode" }
      - { field: "metric_type", type: "string", column: "metric_type" }
      - { field: "avg_value",   type: "float",  column: "avg_value" }
      - { field: "std_value",   type: "float",  column: "std_value" }
      - { field: "units",       type: "string", column: "units" }
      - { field: "nx",          type: "int",    column: "nx" }
      - { field: "ny",          type: "int",    column: "ny" }
      - { field: "row_idx",     type: "int",    column: "row_idx" }
      - { field: "col_idx",     type: "int",    column: "col_idx" }

  particle_metrics:
    from_csv_mode: "particle_metrics"
    fields:
      - { field: "source_file",    type: "string", column: "source_file" }
      - { field: "mode",           type: "string", column: "mode" }
      - { field: "metric_type",    type: "string", column: "metric_type" }
      - { field: "count_total",    type: "int",    column: "count_total" }
      - { field: "count_density",  type: "float",  column: "count_density" }
      - { field: "mean_diam_px",   type: "float",  column: "mean_diam_px" }
      - { field: "std_diam_px",    type: "float",  column: "std_diam_px" }
      - { field: "mean_circ",      type: "float",  column: "mean_circ" }
      - { field: "std_circ",       type: "float",  column: "std_circ" }
      - { field: "nx",             type: "int",    column: "nx" }
      - { field: "ny",             type: "int",    column: "ny" }
      - { field: "row_idx",        type: "int",    column: "row_idx" }
      - { field: "col_idx",        type: "int",    column: "col_idx" }

```
Example Code for a Generic helper (Latter References in the Part 3 in the Core Function Helpers)
```pseudocode

FUNCTION build_result_object_from_csv_row(row: Dict<STRING, STRING>,
                                          schema_name: STRING,
                                          cfg: DICT) -> DICT<STRING, ANY>

    schema = cfg.result_schemas[schema_name]
    obj = EMPTY_DICT()

    FOR field_def IN schema.fields DO
        raw_val = row[field_def.column]
        obj[field_def.field] = CAST(raw_val, field_def.type)
    END FOR

    RETURN obj
END FUNCTION

```

Plotting code uses `build_result_object_from_csv_row` instead of assuming a fixed `SummaryRow` struct. This allows the design philosophy being centered around configs, modes to minimize hard coded values. 

---
## 3. CORE FUNCTIONS

This section describes the **top-level functions** that implement the TIFF → ModeResultRecord → CSV pipeline.

Key rules:

- Core functions work with **ModeResultRecord** objects (dicts), not hard-coded structs.
    
- CSV shape is controlled by **csv_modes** in config.
    
- Grid indices and other extras are added by **modes** via helper functions, not by the core.

### 3.1 `Summarize_folder_to_csv`

**Purpose:**  
Walk a folder of AFM TIFFs, process each image with a given **processing mode**, convert each mode result to a CSV row using a **csv_mode**, and write a summary CSV.

**Signature (conceptual):**
```pseudocode

FUNCTION summarize_folder_to_csv(input_root: STRING,
                                 output_csv_path: STRING,
                                 processing_mode: STRING,
                                 csv_mode: STRING,
                                 cfg: DICT) -> VOID

```
**Behavior:**

1. **Resolve CSV mode and schema**
```pseudocode

csv_def = cfg.csv_modes[csv_mode]
IF csv_def IS NULL THEN
    RAISE_ERROR("Unknown csv_mode: " + csv_mode)
END IF

```
2. **Find TIFF files**
	- Search only one directory level (no recursion) unless config says otherwise.
```pseudocode

tiff_files = FIND_FILES(input_root, pattern="*.tif")
IF tiff_files IS EMPTY THEN
    LOG_WARN("No TIFF files found in " + input_root)
END IF

```
3. **Open CSV and write Header**
```pseudocode

OPEN output_csv_path FOR WRITE AS csv_file

header_cols = [ col.name FOR col IN csv_def.columns ]
WRITE_LINE(csv_file, JOIN_WITH_COMMAS(header_cols))

```
4. **Process each TIFF**
```pseudocode

FOR path IN tiff_files DO
    TRY
        mode_result = process_tiff_with_gwyddion(path,
                                                 processing_mode,
                                                 cfg)

        row_values = BUILD_CSV_ROW(mode_result,
                                   csv_def,
                                   processing_mode,
                                   csv_mode)

        IF row_values IS NOT NULL THEN
            WRITE_LINE(csv_file, JOIN_WITH_COMMAS(row_values))
        ELSE
            // e.g., schema.on_incompatible_metrics == "skip_row"
            LOG_WARN("Skipping row for " + path + " under csv_mode=" + csv_mode)
        END IF

    CATCH e
        HANDLE_SUMMARIZE_ERROR(e,
                               path,
                               processing_mode,
                               csv_mode,
                               csv_def,
                               csv_file)
    END TRY
END FOR

CLOSE csv_file

```
5. **Error policy**
- Exact behavior for missing keys, incompatible modes, or processing failures is controlled by `csv_def.on_missing_field`, `csv_def.on_incompatible_metrics`, and `csv_def.on_error` (see Helper Functions).
    

`summary_folder_to_csv` itself **does not know** which columns exist; it only delegates to `BUILD_CSV_ROW` and the config.

### 3.2 `process_tiff_with_gwyddion`

**Purpose:**  
Given a single AFM TIFF and a **processing mode**, run the appropriate Gwyddion operations and return a **ModeResultRecord** (a dict of key → value).

**Signature (conceptual):**
```pseudocode

FUNCTION process_tiff_with_gwyddion(input_tiff_path: STRING,
                                    mode: STRING,
                                    cfg: DICT) -> ModeResultRecord

```
**Behavior:**

1. **Initialize / load TIFF into Gwyddion**
```pseudocode

GWY_INIT_IF_NEEDED()

container = GWY_FILE_LOAD(input_tiff_path)
IF container IS NULL THEN
    RAISE_ERROR("Failed to load TIFF into Gwyddion: " + input_tiff_path)
END IF

```
2. **Select data field (channel)**
- Determine `channel_family` from `cfg.modes[mode].channel_family` (e.g., `"modulus"` or `"topography"`).
    
- Resolve actual channel name via `cfg.channel_defaults[channel_family]`, with optional override in `cfg.modes[mode].channel_name`.
    
- If field not found, raise an error.
```pseudocode

field = SELECT_DATA_FIELD(container, mode, cfg)
IF field IS NULL THEN
    GWY_FILE_FREE(container)
    RAISE_ERROR("No suitable data field for mode=" + mode +
                " in file " + input_tiff_path)
END IF

```
3. **Apply processing mode pipeline**
- `APPLY_MODE_PIPELINE` handles all Gwyddion operations **and** decides what extra keys to attach (grid, particle, etc.).
```pseudocode

source_file = BASENAME(input_tiff_path)

field_processed, extra_values =
    APPLY_MODE_PIPELINE(field,
                        source_file,
                        mode,
                        cfg)

```
Where:
- `field_processed` is the final scalar field for metric computation (e.g., modulus map).
    
- `extra_values` is a dict of additional keys (particle._, grid._, etc.).

4. **Compute scalar metrics**
- Resolve `metric_type` from `cfg.modes[mode].metric_type` with a sensible default (e.g., `"modulus"`).
    
- For **scalar metrics** (modulus, topography, etc.) compute:
```pseudocode

data = EXTRACT_FIELD_DATA(field_processed)     // 2D array
valid = FILTER_VALID(data)                    // remove NaN/invalid
avg_val = MEAN(valid)
std_val = STD(valid)
z_units = GET_Z_UNITS(field_processed)

```
- For metrics such as `"particle_count"`, the mode pipeline is expected to put a scalar in `extra_values["core.avg_value"]` or similar. The core uses this if present.

Recommended patter:
```pseudocode

metric_type = cfg.modes[mode].metric_type OR "modulus"

result_values = EMPTY_DICT()

// minimal core keys
result_values["core.source_file"] = source_file
result_values["core.mode"]        = mode
result_values["core.metric_type"] = metric_type

IF extra_values.CONTAINS("core.avg_value") THEN
    // mode has explicitly defined avg/std/units
    result_values["core.avg_value"] = extra_values["core.avg_value"]
    result_values["core.std_value"] = extra_values["core.std_value"]
    result_values["core.units"]     = extra_values["core.units"]
ELSE
    // fallback: compute from processed field
    result_values["core.avg_value"] = avg_val
    result_values["core.std_value"] = std_val
    result_values["core.units"]     = z_units
END IF

(nx, ny) = GET_FIELD_DIMS(field_processed)
result_values["core.nx"] = nx
result_values["core.ny"] = ny

// merge remaining extras (particle.*, grid.*, etc.)
FOR (key, val) IN extra_values DO
    IF NOT result_values.CONTAINS(key) THEN
        result_values[key] = val
    END IF
END FOR

```
5. **Cleanup and return**
```pseudocode

GWY_FILE_FREE(container)

mode_result = NEW ModeResultRecord()
mode_result.values = result_values
RETURN mode_result

```
`process_tiff_with_gwyddion` has **no direct knowledge of CSV columns**. It only guarantees a `values` dict with consistent key naming (`core.*`, `particle.*`, `grid.*`, etc.).

### 3.3 `apply_mode_pipeline `

**Purpose:**  
Apply a mode-specific Gwyddion pipeline and return:

- a processed field for scalar metric computation, and
    
- a dict of **extra values** (e.g., grid indices, particle statistics, overrides for core.avg/std/units).
    
All mode behavior is declarative. Code reads flags and parameters from config so that new modes can be introduced without modifying the pipeline.

**Signature (conceptual):**
```pseudocode

FUNCTION APPLY_MODE_PIPELINE(field,
                             source_file: STRING,
                             mode: STRING,
                             cfg: DICT)
    -> (FIELD, DICT<STRING, ANY>)

```
**Behavior:**

Mode-dependent branching. Examples:

#### 3.3.1 Modulus modes
```pseudocode

IF mode == "modulus_basic" THEN
    f = field

    IF cfg.modes.modulus_basic.plane_level THEN
        f = GWY_PLANE_LEVEL(f)
    END IF

    IF cfg.modes.modulus_basic.row_flatten THEN
        f = GWY_ROW_FLATTEN(f)
    END IF

    IF cfg.modes.modulus_basic.median_filter.enable THEN
        f = GWY_MEDIAN_FILTER(f,
                              cfg.modes.modulus_basic.median_filter.size)
    END IF

    extras = EMPTY_DICT()

    IF cfg.modes.modulus_basic.needs_grid_indices THEN
        (r, c) = DERIVE_GRID_INDICES(source_file, cfg.grid)
        extras["grid.row_idx"] = r
        extras["grid.col_idx"] = c
    END IF

    RETURN f, extras
END IF

```
#### 3.3.2 Topography modes

```pseudocode

IF mode == "topography_flat" THEN
    f = field

    IF cfg.modes.topography_flat.plane_level THEN
        f = GWY_PLANE_LEVEL(f)
    END IF

    IF cfg.modes.topography_flat.line_correct THEN
        f = GWY_LINE_CORRECT(f,
                             cfg.modes.topography_flat.line_correct.method)
    END IF

    extras = EMPTY_DICT()

    IF cfg.modes.topography_flat.needs_grid_indices THEN
        (r, c) = DERIVE_GRID_INDICES(source_file, cfg.grid)
        extras["grid.row_idx"] = r
        extras["grid.col_idx"] = c
    END IF

    RETURN f, extras
END IF

```
#### 3.3.3 Particle metrics mode
For particle modes, the pipeline both preprocesses the field and computes particle-level stats, then exposes them as keys in `extras`:
```pseudocode

IF mode == "particle_count_basic" THEN
    f = field

    // 1. Preprocess
    IF cfg.modes.particle_count_basic.plane_level THEN
        f = GWY_PLANE_LEVEL(f)
    END IF

    // 2. Threshold and label
    binary = GWY_THRESHOLD(f, cfg.modes.particle_count_basic.threshold)
    binary = GWY_MORPH_OPEN(binary,
                            cfg.modes.particle_count_basic.morph_kernel_size)
    labels = GWY_GRAIN_LABEL(binary)

    // 3. Grain analysis
    stats = GWY_GRAIN_STATS(labels)

    count_total   = stats.num_grains
    count_density = stats.num_grains / (FIELD_AREA(f))

    mean_diam_px  = stats.mean_equivalent_diameter_px
    std_diam_px   = stats.std_equivalent_diameter_px
    mean_circ     = stats.mean_circularity
    std_circ      = stats.std_circularity

    extras = EMPTY_DICT()

    // expose particle.* keys
    extras["particle.count_total"]       = count_total
    extras["particle.count_density"]     = count_density
    extras["particle.mean_diameter_px"]  = mean_diam_px
    extras["particle.std_diameter_px"]   = std_diam_px
    extras["particle.mean_circularity"]  = mean_circ
    extras["particle.std_circularity"]   = std_circ

    // optionally override core metric for this mode
    extras["core.avg_value"] = TO_FLOAT(count_total)
    extras["core.std_value"] = 0.0
    extras["core.units"]     = "count"

    // optional grid indices
    IF cfg.modes.particle_count_basic.needs_grid_indices THEN
        (r, c) = DERIVE_GRID_INDICES(source_file, cfg.grid)
        extras["grid.row_idx"] = r
        extras["grid.col_idx"] = c
    END IF

    RETURN f, extras
END IF

```
#### 3.3.4 Raw pass-through mode
```pseudocode

IF mode == "raw_noop" THEN
    extras = EMPTY_DICT()

    IF cfg.modes.raw_noop.sanitize_invalid THEN
        f = REPLACE_INVALID_WITH_NAN(field)
    ELSE
        f = field
    END IF

    // optional grid
    IF cfg.modes.raw_noop.needs_grid_indices THEN
        (r, c) = DERIVE_GRID_INDICES(source_file, cfg.grid)
        extras["grid.row_idx"] = r
        extras["grid.col_idx"] = c
    END IF

    RETURN f, extras
END IF

```
#### 3.3.5 Fallback
```pseudocode

RAISE_ERROR("Unknown processing mode: " + mode)

```
---
## 4. HELPER FUNCTIONS

These helpers encapsulate repeated patterns so core functions don’t become a mess of string lookups and conditionals.

### 4.1 `build_csv_row`

**Purpose:**  
Convert a `ModeResultRecord` and a `csv_mode` definition into a list of CSV cell strings.

**Signature:**
```pseudocode

FUNCTION BUILD_CSV_ROW(mode_result: ModeResultRecord,
                       csv_def: CsvModeDefinition,
                       processing_mode: STRING,
                       csv_mode: STRING) -> LIST<STRING> | NULL

```
**Behavior:**
```pseudocode

values = []
record = mode_result.values

FOR col_def IN csv_def.columns DO
    key_path = col_def.from      // e.g., "core.avg_value" or "grid.row_idx"

    (ok, val) = RESOLVE_KEY_PATH(record, key_path)

    IF NOT ok THEN
        // handle missing field according to csv_def policy
        IF csv_def.on_missing_field == "skip_row" THEN
            LOG_WARN("Skipping row: missing field " + key_path +
                     " for file=" + record["core.source_file"])
            RETURN NULL

        ELSE IF csv_def.on_missing_field == "error" THEN
            RAISE_ERROR("Missing field " + key_path +
                        " under csv_mode=" + csv_mode +
                        " for mode=" + processing_mode)

        ELSE // "warn_null" or default
            LOG_WARN("Using default for missing field " + key_path +
                     " under csv_mode=" + csv_mode)
            val = col_def.default
        END IF
    END IF

    values.APPEND(FORMAT_FOR_CSV(val))
END FOR

RETURN values

```
`RESOLVE_KEY_PATH(record, "core.avg_value")` navigates dotted keys into the `values` dict.

### 4.2 `build_result_object_from_csv_row`

**Purpose:**  
Convert a raw CSV row templates based on mode (dict of column → string) into a typed object using a **result_schema** definition. Used by plotting and any downstream analysis.

**Signature:**
```pseudocode

FUNCTION build_result_object_from_csv_row(row: DICT<STRING, STRING>,
                                          schema_name: STRING,
                                          cfg: DICT) -> DICT<STRING, ANY>

```
Behavior:
```pseudocode

schema = cfg.result_schemas[schema_name]
IF schema IS NULL THEN
    RAISE_ERROR("Unknown result schema: " + schema_name)
END IF

obj = EMPTY_DICT()

FOR field_def IN schema.fields DO
    col_name = field_def.column
    type_tag = field_def.type

    IF NOT row.CONTAINS(col_name) THEN
        RAISE_ERROR("CSV missing expected column " + col_name +
                    " for schema=" + schema_name)
    END IF

    raw_val = row[col_name]
    obj[field_def.field] = CAST_FROM_STRING(raw_val, type_tag)
END FOR

RETURN obj

```
Plotters then consume `obj` instead of a fixed `SummaryRow` type.


### 4.3 `DERIVE_GRID_INDICES`

**Purpose:**  
Infer grid row/column indices from **filename** or **mapping CSV**, controlled by `cfg.grid`. Only called by modes that set `needs_grid_indices = true`.

Grid indices are optional metadata used exclusively by grid-based visualizations. They must be computed only when required by the processing mode to avoid unnecessary parsing overhead and to prevent grid pollution in non-grid datasets.

**Signature:**
```pseudocode

FUNCTION DERIVE_GRID_INDICES(source_file: STRING,
                             grid_cfg: DICT) -> (INT, INT)

```
**Behavior (conceptual):**
1. **Check enable flag**
```pseudocode

IF NOT grid_cfg.enable THEN
    RETURN (-1, -1)
END IF

```
2. **Try filename regex**
```pseudocode

IF grid_cfg.filename_regex IS NOT NULL THEN
    match = REGEX_MATCH(grid_cfg.filename_regex, source_file)

    IF match IS NOT NULL THEN
        row_raw = TO_INT(match.group("row"))
        col_raw = TO_INT(match.group("col"))

        IF grid_cfg.zero_based THEN
            row_idx = row_raw - 1
            col_idx = col_raw - 1
        ELSE
            row_idx = row_raw
            col_idx = col_raw
        END IF

        RETURN (row_idx, col_idx)
    END IF
END IF

```
3. **Fallback:mapping CSV**
```pseudocode

IF grid_cfg.mapping_csv_path IS NOT NULL THEN
    (found, row_idx, col_idx) = LOOKUP_GRID_FROM_CSV(source_file,
                                                     grid_cfg.mapping_csv_path,
                                                     grid_cfg.zero_based)
    IF found THEN
        RETURN (row_idx, col_idx)
    END IF
END IF

```
4. **Total failure**
```pseudocode

LOG_WARN("Could not derive grid indices for " + source_file)
RETURN (-1, -1)

```

### 4.4 Other Small Helpers

These are conceptual and can stay implicit in the spec:

- `SELECT_DATA_FIELD(container, mode, cfg)`
    
- `EXTRACT_FIELD_DATA(field_processed)`
    
- `FILTER_VALID(values)`
    
- `GET_Z_UNITS(field)`
    
- `GET_FIELD_DIMS(field)`
    
- `FORMAT_FOR_CSV(val)`
    
- `CAST_FROM_STRING(raw, type_tag)`
    
- `HANDLE_SUMMARIZE_ERROR(...)`
    
- `LOOKUP_GRID_FROM_CSV(source_file, mapping_csv_path, zero_based)`
    


---
## 5. CONFIGURATION & MODES (v2)  
    =============================
    

The pipeline is controlled entirely via configuration. Code only knows how to:

- run **processing modes** on TIFFs to produce `ModeResultRecord` dictionaries
    
- map those dictionaries to CSV using **csv_modes**
    
- map CSV rows back to typed objects using **result_schemas**
    
- map typed objects to plots using **plotting_modes**
    

This section describes the config structure conceptually (YAML-like).

### Top-level structure

A minimal combined config has:

```yaml

channel_defaults:  {...}
modes:             {...}    # processing modes
grid:              {...}
csv_modes:         {...}
result_schemas:    {...}
plotting_modes:    {...}
sample_bar_with_error: {...}   # plotting recipe configs
histogram_avg:        {...}
scatter_avg_vs_std:   {...}
mode_comparison_bar:  {...}
heatmap_grid:         {...}

```

These can split across multiple files if wanted. The spec just assumes `cfg` is a merged dict with these sections.

> [!Question] GPT Question?
> For the section above why is it that i could split it accror profiles?


---

### 5.1 Channel defaults

Processing modes reference **logical channel families** rather than hard-coding actual Gwyddion channel names.

```yaml

channel_defaults:
  modulus:
    channel_name: "Modulus"      # typical Park modulus channel name
  topography:
    channel_name: "Z Height"     # or "Height"

```
Processing modes then say:

```yaml

modes:
  modulus_basic:
    channel_family: "modulus"
  topography_flat:
    channel_family: "topography"

```
The helper `SELECT_DATA_FIELD` uses:

1. `modes[mode].channel_name` override if present
    
2. `channel_defaults[channel_family].channel_name`
    
3. fallback to “first data field” if nothing matches
    

---

### 5.2 Processing modes (`modes`)

Each processing mode defines:

- which channel to use
    
- which Gwyddion operations to run
    
- which **metric_type** to advertise
    
- whether grid indices are needed
    
- any mode-specific knobs

- ==any particular csv formats to follow based on the Gwydion operations which is related to the mode/program choses   (* GPT take a look to see if this makes sense)==

General structure:

```yaml

modes:
  <mode_name>:
    channel_family: "modulus" | "topography" | ...
    channel_name:   "optional override"
    metric_type:    "modulus" | "topography_height" | "particle_count" | "raw_scalar"
    needs_grid_indices: true | false

    # Gwyddion processing options, mode-specific
    plane_level: true | false
    row_flatten: true | false

    median_filter:
      enable: true | false
      size:   3

    line_correct:
      enable:  true | false
      method:  "median" | "polynomial"

    # Particle specific (example)
    threshold:          0.5
    morph_kernel_size:  3

```

### 5.2.1 Example: modulus modes

```yaml

modes:
  modulus_basic:
    channel_family: "modulus"
    metric_type:    "modulus"
    needs_grid_indices: true

    plane_level: true
    row_flatten: true

    median_filter:
      enable: true
      size:   3

  modulus_strict_qc:
    channel_family: "modulus"
    metric_type:    "modulus"
    needs_grid_indices: true

    plane_level:  true
    row_flatten:  true

    median_filter:
      enable: true
      size:   3

    outlier_clip:
      enable: true
      lower_percentile: 1
      upper_percentile: 99

```

### 5.2.2 Example: topography modes

```yaml

modes:
  topography_flat:
    channel_family: "topography"
    metric_type:    "topography_height"
    needs_grid_indices: true

    plane_level: true
    line_correct:
      enable: true
      method: "median"

  topography_smooth:
    channel_family: "topography"
    metric_type:    "topography_height"
    needs_grid_indices: true

    plane_level: true
    line_correct:
      enable: true
      method: "median"

    lowpass_filter:
      enable: true
      cutoff_freq: 0.2

    median_filter:
      enable: true
      size:   3

```

### 5.2.3 Example: particle metrics mode

```yaml

modes:
  particle_count_basic:
    channel_family: "modulus"  # or appropriate input field family
    metric_type:    "particle_count"
    needs_grid_indices: true

    plane_level: true

    threshold:          0.5
    morph_kernel_size:  3

```

### 5.2.4 Example: raw pass-through

```yaml

modes:
  raw_noop:
    channel_family: "topography"
    metric_type:    "raw_scalar"
    needs_grid_indices: false

    sanitize_invalid: true

```

The core never assumes which knobs exist; it just reads what the mode pipeline expects.

---

### 5.3 Grid configuration (`grid`)

Grid logic is filename-based and only used by modes that set `needs_grid_indices: true`.

```yaml

grid:
  enable: true

  filename_regex: "(?<row>\\d{2})_(?<col>\\d{2})"   # example
  zero_based: true         # subtract 1 from row/col when true

  mapping_csv_path: null   # or "grid_mapping.csv"

```

- `filename_regex` is applied to `source_file`. Named groups `row` and `col` are expected.
    
- If regex fails, `mapping_csv_path` can map `source_file` → `(row_idx, col_idx)`.
    
- If both fail, `(row_idx, col_idx) = (-1, -1)` and a warning is logged.
    

Only modes that explicitly want grid indices will call `DERIVE_GRID_INDICES`, so no unnecessary lookups happen.

---

### 5.4 CSV modes (`csv_modes`)

`csv_modes` define **how to serialize a ModeResultRecord into rows**.  
Each csv_mode defines:

- ordered list of `columns`
    
- mapping from `ModeResultRecord.values` keys (`from:`)
    
- what to do on missing fields
    

General structure:

```yaml

csv_modes:
  <csv_mode_name>:
    columns:
      - { name: "col_name", from: "key.path", default: <optional> }
      - ...

    on_missing_field: "warn_null" | "error" | "skip_row"
    on_incompatible_metrics: "error" | "skip_row" | "warn_null"   # optional

```

#### 5.4.1 Example: default scalar summary

```yaml

csv_modes:
  default_scalar:
    columns:
      - { name: "source_file", from: "core.source_file" }
      - { name: "mode",        from: "core.mode" }
      - { name: "metric_type", from: "core.metric_type" }
      - { name: "avg_value",   from: "core.avg_value" }
      - { name: "std_value",   from: "core.std_value" }
      - { name: "units",       from: "core.units" }
      - { name: "nx",          from: "core.nx" }
      - { name: "ny",          from: "core.ny" }
      - { name: "row_idx",     from: "grid.row_idx", default: -1 }
      - { name: "col_idx",     from: "grid.col_idx", default: -1 }

    on_missing_field: "warn_null"

```

#### 5.4.2 Example: particle metrics summary

```yaml

csv_modes:
  particle_metrics:
    columns:
      - { name: "source_file",    from: "core.source_file" }
      - { name: "mode",           from: "core.mode" }
      - { name: "metric_type",    from: "core.metric_type" }

      - { name: "count_total",    from: "particle.count_total" }
      - { name: "count_density",  from: "particle.count_density" }
      - { name: "mean_diam_px",   from: "particle.mean_diameter_px" }
      - { name: "std_diam_px",    from: "particle.std_diameter_px" }
      - { name: "mean_circ",      from: "particle.mean_circularity" }
      - { name: "std_circ",       from: "particle.std_circularity" }

      - { name: "nx",             from: "core.nx" }
      - { name: "ny",             from: "core.ny" }
      - { name: "row_idx",        from: "grid.row_idx", default: -1 }
      - { name: "col_idx",        from: "grid.col_idx", default: -1 }

    on_missing_field: "error"

```

If you try to use `particle_metrics` with a processing mode that never writes `particle.*` keys, `BUILD_CSV_ROW` will respect `on_missing_field` and either error, skip, or fill defaults.

---

### 5.5 Result schemas (`result_schemas`)

`result_schemas` define how to **interpret CSV rows as typed objects**. They are paired with csv_modes.

General structure:

```yaml

result_schemas:
  <schema_name>:
    from_csv_mode: "<csv_mode_name>"
    fields:
      - { field: "field_name", type: "string|float|int", column: "col_name" }
      - ...

```

#### 5.5.1 Example: scalar schema

```yaml

result_schemas:
  default_scalar:
    from_csv_mode: "default_scalar"
    fields:
      - { field: "source_file", type: "string", column: "source_file" }
      - { field: "mode",        type: "string", column: "mode" }
      - { field: "metric_type", type: "string", column: "metric_type" }
      - { field: "avg_value",   type: "float",  column: "avg_value" }
      - { field: "std_value",   type: "float",  column: "std_value" }
      - { field: "units",       type: "string", column: "units" }
      - { field: "nx",          type: "int",    column: "nx" }
      - { field: "ny",          type: "int",    column: "ny" }
      - { field: "row_idx",     type: "int",    column: "row_idx" }
      - { field: "col_idx",     type: "int",    column: "col_idx" }

```

#### 5.5.2 Example: particle schema

```yaml

result_schemas:
  particle_metrics:
    from_csv_mode: "particle_metrics"
    fields:
      - { field: "source_file",    type: "string", column: "source_file" }
      - { field: "mode",           type: "string", column: "mode" }
      - { field: "metric_type",    type: "string", column: "metric_type" }
      - { field: "count_total",    type: "int",    column: "count_total" }
      - { field: "count_density",  type: "float",  column: "count_density" }
      - { field: "mean_diam_px",   type: "float",  column: "mean_diam_px" }
      - { field: "std_diam_px",    type: "float",  column: "std_diam_px" }
      - { field: "mean_circ",      type: "float",  column: "mean_circ" }
      - { field: "std_circ",       type: "float",  column: "std_circ" }
      - { field: "nx",             type: "int",    column: "nx" }
      - { field: "ny",             type: "int",    column: "ny" }
      - { field: "row_idx",        type: "int",    column: "row_idx" }
      - { field: "col_idx",        type: "int",    column: "col_idx" }

```

---

### 5.6 Plotting modes (`plotting_modes`)

`plotting_modes` map **plotting_mode names** to required `result_schema` and any mode-level options.

General structure:

```yaml

plotting_modes:
  <plotting_mode>:
    result_schema: "default_scalar" | "particle_metrics" | ...

```

### 5.6.1 Example set

```yaml

plotting_modes:
  sample_bar_with_error:
    result_schema: "default_scalar"

  histogram_avg:
    result_schema: "default_scalar"

  scatter_avg_vs_std:
    result_schema: "default_scalar"

  mode_comparison_bar:
    result_schema: "default_scalar"

  heatmap_grid:
    result_schema: "default_scalar"

```

The plotting recipes themselves have their own config blocks for labels, colors, etc.:

```yaml

sample_bar_with_error:
  label_map: {}
  max_label_length: 40
  label_rotation: 45
  bar_width: 0.8

histogram_avg:
  bins: 20
  density: false

scatter_avg_vs_std:
  point_size: 30
  alpha: 0.7

mode_comparison_bar:
  sample_name_pattern: "^(?<sample>[^_]+)_.*"
  label_rotation: 45

heatmap_grid:
  cmap: "viridis"
  show_colorbar: true

```


### 5.7 Example File Names to check and use for `FileRegx`

### 5.7.2 File Name Examples

```text
PEGDA1TPO5SiNP-TestSample1-Side1-_250923_ChNameDirZ Height_Backward_ScanSize50.00x50.00_GrID007_LocationOfScanRC004004-CRO.tiff

PEGDA01TPO00SiNP_Sam01_S1_P__GrID006_LOC_RC001011-5.00x5.00-Z Height_Backward-251002-CRO.tiff

PEGDA01TPO025SiNP_Sam03_S1_P__GrID004_LOC_RC001006-5.00x5.00-Z Height_Backward-251015-CRO.tiff
```


### 5.7.1 Current and Legacy File Naming for Most Files

#### 5.7.1.1 Deprecated Legacy Pattern
``` text
SpecimenID_SurfaceID_P#_T#
```

#### 5.7.1.2 Current SmartScan Export Pattern

Example:

```
PEGDA01TPO025SiNP_Sam01_S2_P02_GrID000_LOC_RC001001-5.00x5.00-Z Height_Backward-251008-CRO
```
#### 5.7.1.3 Explicit Parsing Template

```
[SpecimenID]_[SampleTag]_[SurfaceID]_[ParticleTag]_[GridID]_LOC_RC[Row][Col]-[ScanSize]-[Channel]_[Direction]-[YYMMDD]-[Operator]
```
**Example**

**SpecimenID**  
  Example: `PEGDA01TPO025SiNP`  
  Encodes polymer, initiator fraction, filler.

- **SampleTag**  
  `Sam01` → sample index from that batch.

- **SurfaceID**  
  `S2` → fracture face index.

- **ParticleTag**  
  `P__` placeholder or actual particle number (`P02`).

- **GridID**  
  `GrID000` → AFM/SmartScan program grid index.

- **Grid Location**  
  `LOC_RC001001` → grid row/column.

- **Scan Size**  
  `5.00x5.00` (µm).

- **Channel**  
  e.g., `Z Height`, `Modulus`, `Phase`.

- **Scan Direction**  
  `Forward` or `Backward`.

- **Date Code**  
  `251008` → YYMMDD.

- **Operator**  
  `CRO`.
---
## 6. CODEGEN / “CODEX” IMPLEMENTATION GUIDE  
    =========================================
    

This section describes how to use an LLM code assistant (e.g. Codex-style tools, Manus, VS Code agents) to implement and extend this pipeline **without** letting it dismantle the design.

### Goals

- Keep **all behavior** aligned with this spec.
    
- Keep **modes, CSV layout, and plotting** driven from config, not hard-coded.
    
- Make it easy to add **new processing modes** and **new plotting modes** later with minimal human thinking.
    

### Recommended repo layout

Target a small Python package layout:

```text

afm_pipeline/
  __init__.py
  config.py           # load/validate YAML or JSON config
  processing.py       # process_tiff_with_gwyddion, APPLY_MODE_PIPELINE
  summarize.py        # summarize_folder_to_csv, BUILD_CSV_ROW, grid helpers
  plotting.py         # load_results_for_plotting, plot_summary_from_csv, PLOT_* recipes
  cli.py              # argparse-based CLI entrypoints
  modes/              # optional: mode-specific helpers if it grows
tests/
  test_processing.py
  test_summarize.py
  test_plotting.py
config/
  example_config.yaml
  example_modes.yaml
  example_plotting.yaml
documentation/
  user guid
  gwydion fuctions  # doc to describe indepth fucntions to use for modes
  python functions  # doc to describe indepth fucntions to use for ploting
  LLM and Agent Formates # use so that a user can querry an LLM to make more modes for a specfic application

```

You can keep config in one file or split it if that’s cleaner. The important part: **code reads from config; config encodes behavior.**

### Implementation phases for the LLM

Do not ask the model to “build everything.” You’ll get one giant, wrong file. Use this phased approach:

1. **Phase 1: Config loader + data classes**
    
    - Implement `config.py` to:
        
        - load YAML/JSON into a dict
            
        - optionally validate presence of top-level sections: `channel_defaults`, `modes`, `grid`, `csv_modes`, `result_schemas`, `plotting_modes`.
            
    - Implement small helpers / typed wrappers if you want (e.g. dataclasses for `CsvModeDefinition`, `ResultSchemaDefinition`).
        
2. **Phase 2: Summarization core**
    
    - Implement in `summarize.py`:
        
        - `summarize_folder_to_csv`
            
        - `BUILD_CSV_ROW`
            
        - `load_csv_table`
            
        - `build_result_object_from_csv_row`
            
    - No Gwyddion calls here. This layer only sees:
        
        - `ModeResultRecord.values` dict
            
        - `csv_modes` and `result_schemas`.
            
3. **Phase 3: Gwyddion integration**
    
    - Implement in `processing.py`:
        
        - `process_tiff_with_gwyddion`
            
        - `APPLY_MODE_PIPELINE` dispatch for a **minimal set** of modes:
            
            - `modulus_basic`
                
            - `topography_flat`
                
            - `particle_count_basic`
                
            - `raw_noop`
                
    - Wire in pygwy / Gwyddion calls using the reference functions in the appendix.
        
4. **Phase 4: Plotting**
    
    - Implement in `plotting.py`:
        
        - `plot_summary_from_csv`
            
        - `APPLY_PLOTTING_MODE` dispatcher
            
        - `PLOT_SAMPLE_BAR_WITH_ERROR`, `PLOT_HISTOGRAM_AVG`, `PLOT_SCATTER_AVG_VS_STD`, `PLOT_MODE_COMPARISON_BAR`, `PLOT_HEATMAP_GRID` using matplotlib.
            
5. **Phase 5: CLI + tests**
    
    - Implement:
        
        - `cli_summarize` → calls `summarize_folder_to_csv`
            
        - `cli_plot` → calls `plot_summary_from_csv`
            
    - Add tests that:
        
        - mock `process_tiff_with_gwyddion` to return fake `ModeResultRecord` dicts
            
        - verify CSV layout for `csv_modes`
            
        - verify plots run to completion and produce files.
            

**Agent: Stay on a tight leash!**

### Non-negotiable rules for the LLM

Enforce these constraints explicitly:

1. **Do not hard-code CSV column positions or counts.**
    
    - All CSV layout must come from `cfg["csv_modes"][csv_mode]`.
        
    - Reading CSV must use column names, not index positions.
        
2. **Do not hard-code “mode” logic into summarization or plotting.**
    
    - `summarize_folder_to_csv` cannot check `if mode == "particle_count_basic"`.
        
    - That belongs only in `APPLY_MODE_PIPELINE`.
        
3. **Do not compute grid indices outside `APPLY_MODE_PIPELINE` / `DERIVE_GRID_INDICES`.**
    
    - Only modes with `needs_grid_indices: true` should call the grid helper.
        
4. **Do not change the external function signatures** defined in this spec.
    
    - Implement them as described; if you need extra helpers, create new functions.
        
5. **Do not log or print from low-level helpers except via `logging`.**
    
    - Use the standard logging module so you can silence or redirect output later.
        


### Prompt templates: implementing core pieces

Use these as base prompts when calling your code assistant.

### A. Scaffold the project

> You are implementing a Python package called `afm_pipeline`.  
> You must follow this repo layout:
> 
> `afm_pipeline/   __init__.py   config.py   processing.py   summarize.py   plotting.py   cli.py tests/   ...`
> 
> Do not implement any functionality yet.  
> Just create empty module skeletons with:
> 
> - imports
>     
> - function stubs with the signatures described below
>     
> - doctrings that reference the spec.
>     
> 
> Here are the required functions and their signatures:  
```text

[paste function list from spec: summarize_folder_to_csv, process_tiff_with_gwyddion, APPLY_MODE_PIPELINE, BUILD_CSV_ROW, load_csv_table, build_result_object_from_csv_row, plot_summary_from_csv, APPLY_PLOTTING_MODE, and PLOT_* recipes]
```
> 
> Generate Python code for the above layout.

### B. Implement summarization logic

> Implement the functions in `summarize.py` according to this design:
> 
> - `summarize_folder_to_csv(input_root, output_csv_path, processing_mode, csv_mode, cfg)`
>     
>     - Walk `input_root` for `*.tif`.
>         
>     - For each file, call `process_tiff_with_gwyddion(path, processing_mode, cfg)`.
>         
>     - Do not touch Gwyddion here. Treat `process_tiff_with_gwyddion` as externally defined.
>         
>     - Use `cfg["csv_modes"][csv_mode]` to determine column names and mappings.
>         
>     - Use `BUILD_CSV_ROW` to convert a `ModeResultRecord` to a row.
>         
> - `BUILD_CSV_ROW(mode_result, csv_def, processing_mode, csv_mode)`
>     
>     - `mode_result` is a dict with keys like `"core.avg_value"`, `"grid.row_idx"`, `"particle.count_total"`.
>         
>     - Use the `columns` definition inside `csv_def` to map `from` paths to actual values.
>         
>     - Obey `csv_def["on_missing_field"]` for missing keys.
>         
> 
> Do not hard-code column names or counts. All layout comes from `csv_def`.

### C. Implement processing logic (Gwyddion integration)

> Implement `process_tiff_with_gwyddion` and `APPLY_MODE_PIPELINE` in `processing.py`.  
> The design:
> 
> - `process_tiff_with_gwyddion(path, mode, cfg)`:
>     
>     - Load a Gwyddion container from the TIFF.
>         
>     - Select a data field using a helper `select_data_field(container, mode, cfg)`.
>         
>     - Call `APPLY_MODE_PIPELINE(field, source_file, mode, cfg)` and get back:
>         
>         - `field_processed`
>             
>         - `extras` dict
>             
>     - If `extras` contains `core.avg_value`, `core.std_value`, `core.units`, use those.
>         
>     - Else, pull data from `field_processed` into NumPy and compute `avg_value`/`std_value` and `units`.
>         
>     - Fill a dict with:
>         
>         - `core.source_file`, `core.mode`, `core.metric_type`, `core.avg_value`, `core.std_value`, `core.units`, `core.nx`, `core.ny`
>             
>         - plus all key/value pairs from `extras` that don’t override these.
>             
>     - Return this dict as the `ModeResultRecord`.
>         
> - `APPLY_MODE_PIPELINE(field, source_file, mode, cfg)`:
>     
>     - Implement at least these modes:
>         
>         - `modulus_basic`
>             
>         - `topography_flat`
>             
>         - `particle_count_basic`
>             
>         - `raw_noop`
>             
>     - Each branch:
>         
>         - duplicates the field
>             
>         - applies Gwyddion operations according to `cfg["modes"][mode]`
>             
>         - populates an `extras` dict with any grid or particle values.
>             
> 
> Use pygwy / Gwyddion APIs as appropriate (plane leveling, median filters, thresholding, grain stats).  
> Do NOT hard-code CSV columns or call `BUILD_CSV_ROW` in this file.

### D. Implement plotting

> Implement plotting in `plotting.py`:
> 
> - `plot_summary_from_csv(csv_path, plotting_mode, cfg, output_dir)`
>     
>     - Look up `schema_name = cfg["plotting_modes"][plotting_mode]["result_schema"]`.
>         
>     - Call `load_results_for_plotting(csv_path, schema_name, cfg)`.
>         
>     - Dispatch to `APPLY_PLOTTING_MODE`.
>         
> - `APPLY_PLOTTING_MODE(data_rows, plotting_mode, cfg, output_dir)`
>     
>     - Call one of:
>         
>         - `plot_sample_bar_with_error`
>             
>         - `plot_histogram_avg`
>             
>         - `plot_scatter_avg_vs_std`
>             
>         - `plot_mode_comparison_bar`
>             
>         - `plot_heatmap_grid`
>             
> - Each `plot_*` implementation must use fields defined in the appropriate result schema (e.g. `default_scalar`).
>     
>     - Sample bar: `source_file`, `avg_value`, `std_value`.
>         
>     - Hist: `avg_value`.
>         
>     - Scatter: `avg_value`, `std_value`.
>         
>     - Mode comparison: `source_file`, `mode`, `avg_value`.
>         
>     - Heatmap: `row_idx`, `col_idx`, `avg_value`.
>         
> 
> Use `matplotlib.pyplot`. Do not hard-code any CSV column indices; use dict keys only.

### Prompt templates: adding new modes & plots

Once the system is in place, you can have the model help you add modes without rewriting everything.

### New processing mode

> I want to add a new processing mode `"modulus_smooth_qc"` to `modes` in the config.  
> It should:
> 
> - use channel_family `"modulus"`
>     
> - do plane leveling, row flattening, then a median filter of size 5
>     
> - apply an outlier clip between the 5th and 95th percentiles
>     
> - require grid indices
>     
> 
> Write:
> 
> 1. The YAML snippet to add under `modes` in the config.
>     
> 2. The new branch in `APPLY_MODE_PIPELINE` in `processing.py` that:
>     
>     - reads these config fields
>         
>     - applies the operations
>         
>     - returns `(processed_field, extras)`.
>         

### New CSV mode + schema

> I want a CSV mode `"scalar_plus_particle_count"` which:
> 
> - uses all columns from `default_scalar`
>     
> - plus a `count_total` column if `particle.count_total` exists
>     
> 
> Write:
> 
> 1. The new `csv_modes["scalar_plus_particle_count"]` config block.
>     
> 2. The matching `result_schemas["scalar_plus_particle_count"]` block.
>     
> 3. Any minimal changes needed in tests to validate this new mode.
>     

### New plotting mode

> I want a new plotting mode `"particle_count_heatmap"` which:
> 
> - uses `result_schema = "particle_metrics"`
>     
> - renders a heatmap of `count_total` over `row_idx`/`col_idx`
>     
> 
> Write:
> 
> 1. The `plotting_modes["particle_count_heatmap"]` config entry.
>     
> 2. The `particle_count_heatmap` plotting recipe in `plotting.py`, reusing the same `RENDER_HEATMAP` helper as `heatmap_grid`.
>     
> 3. A short example usage:
>     
>     - CLI call
>         
>     - config snippet to tie it together.
>         

> [!tip] How to keep the LLM from “helpfully” redesigning things
> 
> When you paste in parts of the spec, always include one small protective block like:
> 
> > Do not change any function signatures described here.  
> > Do not add new global variables.  
> > All new behavior must be expressed by:
> > 
> > - new config entries (`modes`, `csv_modes`, `result_schemas`, `plotting_modes`), and/or
> >     
> > - new mode branches inside `APPLY_MODE_PIPELINE`, and/or
> >     
> > - new plotting recipes called from `APPLY_PLOTTING_MODE`.
> >     
> > 
> > Do not modify existing branches or configs unless explicitly instructed.
> 
> That’s the guardrail that keeps “helpful” from turning into “unusable.”


---

This is the stuff you’ll actually touch when writing new modes / CLI tools around the spec.

## 1. Paths & files

**Module:** `pathlib`

```Python

from pathlib import Path

root = Path(input_root)
tiff_files = root.glob("*.tif")      # or "*.tiff"
for p in tiff_files:
    p.name      # "file.tif"
    p.stem      # "file"
    p.suffix    # ".tif"
    p.parent    # parent directory

```

Useful when implementing `summarize_folder_to_csv` and anything that walks a scan folder.

---

## 2. CSV I/O

**Module:** `csv`

```Python

import csv

# write
with open("summary.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["col1", "col2"])
    writer.writerow(["foo", 1.23])

# dict style write
with open("summary.csv", "w", newline="") as f:
    fieldnames = ["source_file", "avg_value"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerow({"source_file": "img1.tif", "avg_value": 3.14})

# read
with open("summary.csv", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        row["source_file"]
        float(row["avg_value"])

```

Use `DictReader` / `DictWriter` for the `csv_modes` + `result_schemas` world.

---

## 3. YAML / JSON config

### YAML (if you’re using PyYAML)

```Python

import yaml

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

# cfg["modes"]["modulus_basic"]["plane_level"]

```

### JSON (if you pick JSON instead)

```Python

import json

with open("config.json") as f:
    cfg = json.load(f)

```

---

## 4. Numeric helpers (NumPy)

**Module:** `numpy`

```Python

import numpy as np

data = np.asarray(field_data)       # 2D or 1D array

valid = data[np.isfinite(data)]     # drop NaN/inf
mean_val = float(np.mean(valid))
std_val  = float(np.std(valid))

```

These calls are your go-to for `avg_value` / `std_value` in scalar modes for user reference.

---

## 5. Matplotlib plotting

**Module:** `matplotlib.pyplot`

```Python

import matplotlib.pyplot as plt

# bar with error
fig, ax = plt.subplots()
ax.bar(x_positions, means, yerr=stds)
ax.set_xlabel("Sample")
ax.set_ylabel("Modulus (GPa)")
fig.tight_layout()
fig.savefig(output_path)
plt.close(fig)

```

Other patterns:

- Histogram:
    
```Python

fig, ax = plt.subplots()
ax.hist(values, bins=cfg["bins"], density=cfg["density"])

```
    
- Scatter:
    
```Python

fig, ax = plt.subplots()
ax.scatter(xs, ys, s=cfg["point_size"], alpha=cfg["alpha"])

```
    
- Heatmap:
    
```Python

fig, ax = plt.subplots()
im = ax.imshow(grid, origin="lower")
fig.colorbar(im, ax=ax)

```
  

That’s all your `PLOT_*` recipes in real code for user reference.

---

## 6. CLI wiring

**Module:** `argparse`

```Python

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--input-root", required=True)
parser.add_argument("--out-csv", required=True)
parser.add_argument("--mode", required=True)
parser.add_argument("--csv-mode", required=True)
args = parser.parse_args()

```
You’ll use this for `cli_summarize` / `cli_plot` entrypoints.

---

## 7. Logging

**Module:** `logging`

```Python

import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

log.info("Processing %s", path)
log.warning("Missing field %s in mode %s", key, mode)
log.error("Failed on %s", path, exc_info=True)

```

Use this instead of `print` so you can turn verbosity up/down.

---

# Gwyddion / PYGWY REFERENCE CHEATSHEET

Now the part that actually touches the AFM data.

High-level idea: pygwy exposes **Gwyddion’s C API** into Python as module `gwy`. You can run it: Please

- embedded in Gwyddion via `Data Process → Pygwy Console`, or
    
- as a standalone module if you install the on-disk pygwy build. [Gwyddion+1](https://gwyddion.net/documentation/user-guide-en/pygwy.html?utm_source=chatgpt.com)
    

You care mostly about:

- loading data (container, DataField)
    
- plane leveling / flattening
    
- simple filters
    
- masks & grains
    
- grain stats
    

Below is the subset you’ll actually want to remember.

---

## 1. Getting containers & data fields

From the running app (embedded pygwy):

`import gwy  container = gwy.gwy_app_data_browser_get_current(gwy.APP_CONTAINER) data_field = gwy.gwy_app_data_browser_get_current(gwy.APP_DATA_FIELD) field_id   = gwy.gwy_app_data_browser_get_current(gwy.APP_DATA_FIELD_ID)`

User guide + pygwy docs describe this pattern for accessing the “current” data. [Gwyddion+1](https://gwyddion.net/documentation/user-guide-en/pygwy.html?utm_source=chatgpt.com)

To enumerate fields in a container:

`import gwyutils data_dir = gwyutils.get_data_fields_dir(container)  # dict: key -> DataField`

Note: docs warn `get_data_fields` is a bit messy and suggest using the app data-browser helpers for specific types instead. [Gwyddion](https://gwyddion.net/documentation/head/pygwy/gwyutils-module.html?utm_source=chatgpt.com)

For standalone scripts, you’d use a loader like `gwy.gwy_file_load()` to load a `.gwy` or image file into a container (check pygwy docs for exact signature; it mirrors the C `gwy_file_load` call). [Gwyddion](https://gwyddion.net/documentation/?utm_source=chatgpt.com)

---

## 2. `gwy.DataField`: basic geometry & units

Class: `gwy.DataField` [Gwyddion+1](https://gwyddion.net/documentation/head/pygwy/gwy.DataField-class.html?utm_source=chatgpt.com)

Useful methods:

- Resolution & physical size:
    
    `xres = data_field.get_xres() yres = data_field.get_yres() xreal = data_field.get_xreal() yreal = data_field.get_yreal()`
    
- Data values: get a raw pointer or copy, but often you just use provided processing methods instead of pulling arrays directly.
    

---

## 3. Leveling & background removal

From `DataField` docs: plane fit & leveling. [Gwyddion+1](https://gwyddion.net/documentation/head/pygwy/gwy.DataField-class.html?utm_source=chatgpt.com)

- Fit plane:
    
    `pa, pbx, pby = data_field.fit_plane()`
    
- Apply leveling: either via high-level `plane_level` wrapper or manually subtracting the plane using the relation from docs:
    
    `# Conceptual: plane leveling using coefficients # data[i] := data[i] - (pa + pby*i + pbx*j)`
    

Gwyddion UI calls this _Data Process → Level → Plane Level_, and the same algorithm is exposed via pygwy. [Scribd+1](https://www.scribd.com/document/411617867/Gwyddion-User-Guide-En?utm_source=chatgpt.com)

You can also do polynomial fitting & other more advanced background removal via `fit_poly` and line-leveling functions, but for your pipeline the basic plane leveling is usually enough.

---

## 4. Statistical analysis of the field

From `DataField` statistical methods. [Gwyddion](https://gwyddion.net/documentation/head/pygwy/gwy.DataField-class.html?utm_source=chatgpt.com)

Common ones:

- Height distribution:
    
    `data_line = gwy.DataLine()  # or get an existing line data_field.dh(data_line, nstats)`
    
- Slope distribution, autocorrelation, PSDF, etc., exist as `da`, `acf`, `psdf`, `rpsdf`, etc., if you ever need them for roughness descriptors.
    

For your **summary stats** pipeline you’ll usually just pull the field into NumPy and do `mean/std` yourself, but these are your options for more exotic metrics.

---

## 5. Grain / particle operations

This is where your particle modes live.

From the Gwyddion grain tools & pygwy docs: [Scribd+2Gwyddion+2](https://www.scribd.com/document/411617867/Gwyddion-User-Guide-En?utm_source=chatgpt.com)

### 5.1 Masking & marking grains

Manual equivalents in UI:

- Data Process → Grains → Mark by Threshold
    
- Data Process → Grains → Mark by Otsu’s
    
- Data Process → Grains → Mark by Edge Detection
    
- Data Process → Grains → Remove Edge-Touching
    

Docs explain threshold-based, Otsu, and watershed marking for grains / particles. [Scribd](https://www.scribd.com/document/411617867/Gwyddion-User-Guide-En?utm_source=chatgpt.com)

In pygwy, these correspond to module calls that:

- create a **mask DataField** over the same grid as your main field,
    
- label grains in that mask.
    

You’ll typically:

1. Start with your height/modulus field (`data_field`).
    
2. Run a thresholder (e.g. Mark by Threshold) via pygwy module call to create a **mask field**.
    
3. Convert the mask to grain labels.
    

### 5.2 Numbering & sizing grains

From `gwy.DataField` grain methods: [Gwyddion+1](https://gwyddion.net/documentation/head/pygwy/gwy.DataField-class.html?utm_source=chatgpt.com)

Key functions:

`grains = mask_field.number_grains()        # label grains in mask sizes  = mask_field.get_grain_sizes(grains) bboxes = mask_field.get_grain_bounding_boxes(grains)`

- `number_grains()` creates a labeled grain index array.
    
- `get_grain_sizes(grains)` returns per-grain areas.
    
- There are also methods for bounding boxes, inscribed boxes, etc.
    

### 5.3 Grain statistics

Two main APIs:

- Per-grain values:
    
    `values = data_field.grains_get_values(grains, quantity)`
    
- Distribution of a grain quantity:
    
    `dist_line = gwy.DataLine() data_field.grains_get_distribution(mask_field, grains,                                    quantity, nstats)`
    

Where `quantity` is one of the `gwy.GrainQuantity` enums (e.g. area, equivalent diameter, circularity). [Gwyddion+1](https://gwyddion.net/documentation/head/pygwy/gwy.DataField-class.html?utm_source=chatgpt.com)

Your particle mode pseudo-pipeline:

1. Mark grains (mask).
    
2. `grains = mask_field.number_grains()`
    
3. `values = data_field.grains_get_values(grains, gwy.GrainQuantity.EQUIV_DIAMETER)`
    
4. Use NumPy to compute mean, std, count, density (`count / area`).
    

---

## 6. Misc pygwy utilities

From `gwyutils` and the general pygwy docs. [Gwyddion+1](https://gwyddion.net/documentation/pygwy.php?utm_source=chatgpt.com)

Useful bits:

- `gwyutils.get_data_fields_dir(container)` to inspect what’s in a `.gwy` file.
    
- `gwy.gwy_app_data_browser_get_data_ids(container)` & related “get IDs” helpers (preferred way to list images, masks, etc.).
    
- `DataField.duplicate()` to clone a field before destructive operations. [Gwyddion](https://gwyddion.net/documentation/head/pygwy/gwy.DataField-class.html?utm_source=chatgpt.com)
    

These keep your mode code from destroying the only copy of the raw data.

---

# MODE TEMPLATE (CONCEPTUAL)

Here’s a **minimal mode template** written in terms of real APIs:

`def run_mode_modulus_basic(data_field, source_file, cfg_mode, grid_cfg):     """     data_field: gwy.DataField for modulus channel     source_file: basename of the original file     cfg_mode: cfg["modes"]["modulus_basic"]     grid_cfg:  cfg["grid"]     Returns: (processed_field, extras_dict)     """     # 1. duplicate field so we don't mutate original     f = data_field.duplicate()      # 2. plane leveling     if cfg_mode.get("plane_level", True):         pa, pbx, pby = f.fit_plane()         # Apply plane subtraction here or use the higher-level plane_level call      # 3. row flatten, filters, etc., using other DataField methods     #    (line correction, median filter, etc. – via pygwy modules or DataField ops)      extras = {}      # 4. grid indices if enabled     if cfg_mode.get("needs_grid_indices", False):         r, c = derive_grid_indices(source_file, grid_cfg)         extras["grid.row_idx"] = r         extras["grid.col_idx"] = c      # 5. let the core compute avg/std/units from f     return f, extras

And a **particle mode** sketch:

`def run_mode_particle_basic(data_field, source_file, cfg_mode, grid_cfg):     """     Particle / grain analysis mode using threshold + grain stats.     """     f = data_field.duplicate()      # 1. plane level if requested     if cfg_mode.get("plane_level", True):         pa, pbx, pby = f.fit_plane()         # subtract plane from f      # 2. create mask via thresholding module     #    (call pygwy Grains → Mark by Threshold equivalent here)      mask_field = create_threshold_mask(f, cfg_mode)  # your wrapper      # 3. grain labeling & stats     grains = mask_field.number_grains()     diam_vals = f.grains_get_values(grains, gwy.GrainQuantity.EQUIV_DIAMETER)     circ_vals = f.grains_get_values(grains, gwy.GrainQuantity.CIRCULARITY)      diam_arr = np.asarray(diam_vals[1:], dtype=float)  # skip grain 0     circ_arr = np.asarray(circ_vals[1:], dtype=float)      count_total = int(diam_arr.size)     count_density = count_total / (f.get_xreal() * f.get_yreal())      extras = {         "particle.count_total":      count_total,         "particle.count_density":    count_density,         "particle.mean_diameter_px": float(np.mean(diam_arr)),         "particle.std_diameter_px":  float(np.std(diam_arr)),         "particle.mean_circularity": float(np.mean(circ_arr)),         "particle.std_circularity":  float(np.std(circ_arr)),         # override core metric to "count"         "core.avg_value": float(count_total),         "core.std_value": 0.0,         "core.units": "count",     }      if cfg_mode.get("needs_grid_indices", False):         r, c = derive_grid_indices(source_file, grid_cfg)         extras["grid.row_idx"] = r         extras["grid.col_idx"] = c      return f, extras`

Where `derive_grid_indices` is your filename/mapping-based helper.