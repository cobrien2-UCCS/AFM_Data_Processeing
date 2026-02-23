# Method Comparison Tables (2026-02-13 run)
These tables summarize the comparison in `out/method_compare/compare_20260213_150349/` based on `comparison_wide.csv`.
Use the short method names in the tables below to keep the results section concise (see the Method Key).
## Baseline Summary (Gwyddion-only)
| Metric | Mean | Median | Min | Max | n |
|---|---:|---:|---:|---:|---:|
| avg_value (kPa) | 3.38e+08 | 2.44e+08 | 3.87e+07 | 7.99e+08 | 7 |
| std_value (kPa) | 1.11e+08 | 8.14e+07 | 2.37e+07 | 3.17e+08 | 7 |
| n_valid | 2.561e+05 | 2.592e+05 | 2.483e+05 | 2.601e+05 | 7 |

## Method vs Baseline Summary
Columns are computed across all tiles vs the baseline. Ratio values are method/baseline.
| Method | Mean ratio avg | Median ratio avg | Mean ratio std | Mean delta avg | Median delta avg | Mean delta std | Mean delta n_valid | delta n_valid min | delta n_valid max | Nonzero delta n (count) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| modulus_export_chauvenet | 0.981 | 0.983 | 0.551 | -5.18e+06 | -2.28e+06 | -6.43e+07 | -297.9 | -2040 | 0 | 2 |
| modulus_export_combo | 0.973 | 0.974 | 0.42 | -5.98e+06 | -3.17e+06 | -7.31e+07 | -1852 | -6136 | 0 | 6 |
| modulus_export_minmax | 0.986 | 0.995 | 0.594 | -4.97e+06 | -2.28e+06 | -6.33e+07 | 0 | 0 | 0 | 0 |
| modulus_export_raw_only | 0.986 | 0.995 | 0.594 | -4.97e+06 | -2.28e+06 | -6.33e+07 | 0 | 0 | 0 | 0 |
| modulus_export_three_sigma | 0.976 | 0.981 | 0.505 | -5.51e+06 | -2.42e+06 | -6.68e+07 | -918.1 | -4918 | 0 | 4 |

## Largest |delta avg| per Method
| Method | delta avg (kPa) | Row | Col | Source file |
|---|---:|---:|---:|---|
| modulus_export_chauvenet | -2.22e+07 | 0 | 0 | PEGDA01TPO000SiNP_Sam01_S1_P__GrID000_LOC_RC001001-5.00x5.00-Modulus_Backward-251021-CRO.tiff |
| modulus_export_combo | -2.22e+07 | 0 | 0 | PEGDA01TPO000SiNP_Sam01_S1_P__GrID000_LOC_RC001001-5.00x5.00-Modulus_Backward-251021-CRO.tiff |
| modulus_export_minmax | -2.22e+07 | 0 | 0 | PEGDA01TPO000SiNP_Sam01_S1_P__GrID000_LOC_RC001001-5.00x5.00-Modulus_Backward-251021-CRO.tiff |
| modulus_export_raw_only | -2.22e+07 | 0 | 0 | PEGDA01TPO000SiNP_Sam01_S1_P__GrID000_LOC_RC001001-5.00x5.00-Modulus_Backward-251021-CRO.tiff |
| modulus_export_three_sigma | -2.22e+07 | 0 | 0 | PEGDA01TPO000SiNP_Sam01_S1_P__GrID000_LOC_RC001001-5.00x5.00-Modulus_Backward-251021-CRO.tiff |

## Method Key (Short Descriptions)
This is a shorthand reference for the comparison table above. Update if configs change.
| Method | Route | Stats source | Filters |
|---|---|---|---|
| gwyddion_only (baseline) | Gwyddion preprocess + Gwyddion stats | gwyddion | mask 1..1e9 kPa, no Python filters |
| modulus_export_raw_only | Gwyddion preprocess + Python stats | python | no Python filters (raw export only) |
| modulus_export_minmax | Gwyddion preprocess + Python stats | python | min/max value window |
| modulus_export_three_sigma | Gwyddion preprocess + Python stats | python | 3-sigma |
| modulus_export_chauvenet | Gwyddion preprocess + Python stats | python | Chauvenet |
| modulus_export_combo | Gwyddion preprocess + Python stats | python | min/max + 3-sigma + Chauvenet |

## Other Tables To Consider (for future runs)
These are optional tables that often strengthen a methods/results section.
- Per-scan summary table (mean, std, n_valid) grouped by `file.direction` (Forward/Backward).
- Forward vs Backward delta table (avg/std/n_valid per scan).
- Per-method outlier impact table (count of scans where n_valid drops > X%).
- Per-method spatial consistency table (e.g., mean of row/col gradients).
