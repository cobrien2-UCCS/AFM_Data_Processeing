# Method Comparison Tables (2026-02-23 run)
These tables summarize the forward/backward comparisons for the full modulus dataset (PEGDA1TPO00SiNP_Sam01_S1).
Outputs:
- Forward: `out/method_compare/compare_20260223_173256/`
- Backward: `out/method_compare/compare_20260223_173335/`
Baseline: `config.modulus_gwy_stats` (Gwyddion stats after preprocessing).

## Forward Baseline Summary (Gwyddion stats)
| Metric | Mean | Median | Min | Max | n |
|---|---:|---:|---:|---:|---:|
| avg_value (kPa) | 1.512e+09 | 1.029e+08 | 2.954e+07 | 1.040e+11 | 105 |
| std_value (kPa) | 1.553e+08 | 5.162e+07 | 5.861e+06 | 4.124e+09 | 105 |
| n_valid | 2.215e+05 | 2.529e+05 | 0.000 | 2.621e+05 | 107 |

## Forward Method vs Baseline Summary
| Method | Mean ratio avg | Median ratio avg | Mean ratio std | Mean delta avg | Median delta avg | Mean delta std | Mean delta n_valid | delta n_valid min | delta n_valid max | Nonzero delta n (count) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gwy_ops_py_stats | 0.910 | 0.996 | 0.797 | -1.284e+09 | -4.406e+05 | -9.042e+07 | 0.000 | 0.000 | 0.000 | 0 |
| raw_minmax | 0.910 | 0.996 | 0.797 | -1.284e+09 | -4.406e+05 | -9.042e+07 | 0.000 | 0.000 | 0.000 | 0 |
| raw_chauvenet | 0.944 | 0.984 | 0.645 | -1.155e+08 | -1.191e+06 | -5.792e+07 | -490.065 | -2447.000 | 0.000 | 71 |
| raw_three_sigma | 0.950 | 0.975 | 0.577 | -6.602e+07 | -1.787e+06 | -6.255e+07 | -1189.467 | -5060.000 | 0.000 | 81 |

## Forward Largest |delta avg| per Method
| Method | delta avg (kPa) | Row | Col | Source file |
|---|---:|---:|---:|---|
| gwy_ops_py_stats | -1.036e+11 | 9 | 11 | PEGDA01TPO000SiNP_Sam01_S1_P__GrID045_LOC_RC010012-5.00x5.00-Modulus_Forward-251030-CRO_9bae1474.tiff |
| raw_minmax | -1.036e+11 | 9 | 11 | PEGDA01TPO000SiNP_Sam01_S1_P__GrID045_LOC_RC010012-5.00x5.00-Modulus_Forward-251030-CRO_9bae1474.tiff |
| raw_chauvenet | -4.186e+09 | 20 | 10 | PEGDA01TPO000SiNP_Sam01_S1_P__GrID100_LOC_RC021011-5.00x5.00-Modulus_Forward-251103-CRO_fd17ffd5.tiff |
| raw_three_sigma | -2.678e+09 | 19 | 9 | PEGDA01TPO000SiNP_Sam01_S1_P__GrID090_LOC_RC020010-5.00x5.00-Modulus_Forward-251103-CRO_c9aeafeb.tiff |

## Backward Baseline Summary (Gwyddion stats)
| Metric | Mean | Median | Min | Max | n |
|---|---:|---:|---:|---:|---:|
| avg_value (kPa) | 7.613e+08 | 1.150e+08 | 2.943e+07 | 2.278e+10 | 103 |
| std_value (kPa) | 1.242e+08 | 5.162e+07 | 5.831e+06 | 1.266e+09 | 103 |
| n_valid | 2.151e+05 | 2.527e+05 | 0.000 | 2.621e+05 | 107 |

## Backward Method vs Baseline Summary
| Method | Mean ratio avg | Median ratio avg | Mean ratio std | Mean delta avg | Median delta avg | Mean delta std | Mean delta n_valid | delta n_valid min | delta n_valid max | Nonzero delta n (count) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gwy_ops_py_stats | 0.913 | 0.997 | 0.824 | -5.277e+08 | -5.226e+05 | -5.366e+07 | 0.000 | 0.000 | 0.000 | 0 |
| raw_minmax | 0.913 | 0.997 | 0.824 | -5.277e+08 | -5.226e+05 | -5.366e+07 | 0.000 | 0.000 | 0.000 | 0 |
| raw_chauvenet | 0.936 | 0.984 | 0.669 | -1.543e+08 | -1.135e+06 | -4.957e+07 | -466.869 | -2466.000 | 0.000 | 64 |
| raw_three_sigma | 0.938 | 0.976 | 0.618 | -1.208e+08 | -1.713e+06 | -4.904e+07 | -1141.757 | -4992.000 | 0.000 | 71 |

## Backward Largest |delta avg| per Method
| Method | delta avg (kPa) | Row | Col | Source file |
|---|---:|---:|---:|---|
| gwy_ops_py_stats | -2.223e+10 | 9 | 11 | PEGDA01TPO000SiNP_Sam01_S1_P__GrID045_LOC_RC010012-5.00x5.00-Modulus_Backward-251030-CRO_4f9d30ad.tiff |
| raw_minmax | -2.223e+10 | 9 | 11 | PEGDA01TPO000SiNP_Sam01_S1_P__GrID045_LOC_RC010012-5.00x5.00-Modulus_Backward-251030-CRO_4f9d30ad.tiff |
| raw_chauvenet | -6.541e+09 | 6 | 20 | PEGDA01TPO000SiNP_Sam01_S1_P__GrID036_LOC_RC007021-5.00x5.00-Modulus_Backward-251029-CRO_6f7fed9d.tiff |
| raw_three_sigma | -6.541e+09 | 6 | 20 | PEGDA01TPO000SiNP_Sam01_S1_P__GrID036_LOC_RC007021-5.00x5.00-Modulus_Backward-251029-CRO_6f7fed9d.tiff |

## Forward vs Backward Summary (paired by row/col)
Source: `out/method_compare/fwd_bwd_20260223_173826/fwd_bwd_summary.csv`.
| Method | n_pairs | mean ratio avg | median ratio avg | mean delta avg | median delta avg | delta avg min | delta avg max | mean delta n_valid | delta n min | delta n max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gwy_stats | 99 | 2.181 | 1.000 | -8.004e+08 | -4975.327 | -8.124e+10 | 9.018e+09 | -4318.657 | -2.544e+05 | 2.569e+05 |
| gwy_ops_py_stats | 99 | 1.418 | 1.001 | 4.562e+06 | 3.730e+04 | -7.670e+08 | 6.820e+08 | -4318.657 | -2.544e+05 | 2.569e+05 |
| raw_minmax | 99 | 1.418 | 1.001 | 4.562e+06 | 3.730e+04 | -7.670e+08 | 6.820e+08 | -4318.657 | -2.544e+05 | 2.569e+05 |
| raw_chauvenet | 91 | 1.419 | 1.000 | -4.069e+06 | -5677.791 | -8.588e+08 | 7.058e+08 | -8176.473 | -2.446e+05 | 2.569e+05 |
| raw_three_sigma | 88 | 1.424 | 1.001 | 2.604e+06 | 1.786e+04 | -7.672e+08 | 6.838e+08 | -1.126e+04 | -2.443e+05 | 2.569e+05 |

---

## Prior Run (2026-02-13)
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
