# Drift robustness: old design vs two-track design

150 simulated participants per cell. Contrast = log w_d(0°) − log w_d(90°); true value −0.51 in the effect cells (ratio 0.6), 0 in the null cells. Bias = recovered − built-in, per participant, ± SE. Every cell uses the SAME participant pool and per-participant seeds, so the pool's own sampling error (about ± 1 SE) is shared by all cells: differences between scenarios or designs are more precise than any cell's absolute bias, and a bias that is the same in every cell is that shared error, not a design effect. p is the paired t-test of the recovered contrast against 0 (one test per cell, so in the null cells it should be unremarkable and in the effect cells small). floor = share of incorrect high-evidence trials rated 1. Threshold drift = change of the live staircase estimate, last vs first 10 trials (logit prop).

| truth | scenario | design | contrast fit | bias ± SE | d_z | p | r(w_d) | acc standard | acc strength (0° / 90°) | floor | threshold drift 0° / 90° |
|---|---|---|---|---|---|---|---|---|---|---|---|
| effect | no change | old | -0.49 | -0.01 ± 0.07 | -0.54 | 0.000 | 0.65 | 71 % | n/a | 24 % | -0.01 / +0.02 |
| effect | no change | two-track | -0.54 | -0.06 ± 0.06 | -0.68 | 0.000 | 0.70 | 71 % | 87 / 88 % | 12 % | -0.08 / +0.06 |
| effect | learning, both mappings | old | -0.51 | -0.02 ± 0.07 | -0.56 | 0.000 | 0.67 | 72 % | n/a | 25 % | -0.27 / -0.22 |
| effect | learning, both mappings | two-track | -0.49 | -0.01 ± 0.06 | -0.58 | 0.000 | 0.66 | 72 % | 87 / 88 % | 13 % | -0.35 / -0.20 |
| effect | drop once feedback stops | old | -0.51 | -0.01 ± 0.07 | -0.56 | 0.000 | 0.60 | 69 % | n/a | 22 % | +0.45 / +0.46 |
| effect | drop once feedback stops | two-track | -0.49 | +0.01 ± 0.06 | -0.61 | 0.000 | 0.67 | 69 % | 88 / 88 % | 13 % | +0.39 / +0.49 |
| effect | learning, 90 deg faster | old | -0.66 | -0.17 ± 0.07 | -0.73 | 0.000 | 0.68 | 72 % | n/a | 25 % | -0.13 / -0.35 |
| effect | learning, 90 deg faster | two-track | -0.50 | -0.02 ± 0.06 | -0.65 | 0.000 | 0.69 | 72 % | 87 / 89 % | 13 % | -0.20 / -0.32 |
| effect | slope rises, 90 deg only | old | -0.66 | -0.18 ± 0.07 | -0.76 | 0.000 | 0.71 | 70 % | n/a | 29 % | -0.01 / +0.06 |
| effect | slope rises, 90 deg only | two-track | -0.63 | -0.14 ± 0.06 | -0.82 | 0.000 | 0.72 | 71 % | 87 / 89 % | 14 % | -0.08 / +0.07 |
| effect | faster learning + slope, 90 | old | -0.87 | -0.39 ± 0.06 | -1.03 | 0.000 | 0.70 | 72 % | n/a | 31 % | -0.13 / -0.34 |
| effect | faster learning + slope, 90 | two-track | -0.54 | -0.06 ± 0.05 | -0.73 | 0.000 | 0.69 | 72 % | 87 / 90 % | 15 % | -0.20 / -0.31 |
| null | no change | old | +0.10 | +0.08 ± 0.07 | +0.12 | 0.146 | 0.65 | 71 % | n/a | 32 % | -0.01 / +0.02 |
| null | no change | two-track | +0.04 | +0.01 ± 0.05 | +0.05 | 0.524 | 0.67 | 71 % | 87 / 88 % | 18 % | -0.08 / +0.06 |
| null | learning, both mappings | old | +0.02 | -0.01 ± 0.07 | +0.02 | 0.790 | 0.64 | 72 % | n/a | 33 % | -0.27 / -0.22 |
| null | learning, both mappings | two-track | +0.06 | +0.03 ± 0.05 | +0.08 | 0.322 | 0.63 | 72 % | 87 / 88 % | 19 % | -0.35 / -0.20 |
| null | drop once feedback stops | old | +0.02 | -0.00 ± 0.07 | +0.02 | 0.837 | 0.56 | 69 % | n/a | 31 % | +0.45 / +0.46 |
| null | drop once feedback stops | two-track | +0.03 | +0.02 ± 0.06 | +0.04 | 0.629 | 0.64 | 69 % | 88 / 88 % | 19 % | +0.39 / +0.49 |
| null | learning, 90 deg faster | old | -0.10 | -0.12 ± 0.07 | -0.11 | 0.193 | 0.64 | 72 % | n/a | 33 % | -0.13 / -0.35 |
| null | learning, 90 deg faster | two-track | +0.05 | +0.02 ± 0.05 | +0.07 | 0.411 | 0.66 | 72 % | 87 / 89 % | 19 % | -0.20 / -0.32 |
| null | slope rises, 90 deg only | old | -0.07 | -0.10 ± 0.06 | -0.08 | 0.309 | 0.68 | 70 % | n/a | 37 % | -0.01 / +0.06 |
| null | slope rises, 90 deg only | two-track | -0.05 | -0.08 ± 0.05 | -0.08 | 0.345 | 0.67 | 71 % | 87 / 89 % | 20 % | -0.08 / +0.07 |
| null | faster learning + slope, 90 | old | -0.31 | -0.34 ± 0.06 | -0.37 | 0.000 | 0.61 | 72 % | n/a | 39 % | -0.13 / -0.34 |
| null | faster learning + slope, 90 | two-track | +0.01 | -0.02 ± 0.05 | +0.01 | 0.871 | 0.65 | 72 % | 87 / 90 % | 20 % | -0.20 / -0.31 |
