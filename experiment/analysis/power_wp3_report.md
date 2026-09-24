# WP3 power / feasibility — primary test: paired t on log w_d, 0° vs 90°

pool per condition: A = 600, B–E = 400 · attrition 13% on top of the analysis gates · α = .05 two-sided · runtime 32.0 min on 8 cores

## 0. Does the simulator look like Rollwage 2018 (Fig. 4B)?

Group-mean confidence at μ_Δ = 0. What must match is the *shape*: shallow rise on correct trials (ceiling), steep fall on incorrect trials.

| evidence level | correct: sim | Rollwage | incorrect: sim | Rollwage |
|---|---|---|---|---|
| 0 |  72.0 % | 72 % |  62.5 % | 67 % |
| 1 |  87.2 % | 75 % |  52.2 % | 52 % |
| 2 |  92.9 % | 78 % |  20.9 % | 40 % |

Accuracy the post-decision samples would yield if responded to (boost = 1.2 logit): low **71 %** (Rollwage: ~71 %), high **93 %** (Rollwage: 80 %).

With boost = 0.5: Accuracy the post-decision samples would yield if responded to (boost = 0.5 logit): low **71 %** (Rollwage: ~71 %), high **82 %** (Rollwage: 80 %).

With boost = 0.8: Accuracy the post-decision samples would yield if responded to (boost = 0.8 logit): low **70 %** (Rollwage: ~71 %), high **87 %** (Rollwage: 80 %).

## A  effect size  (sd_delta=0.30, b~N(.4,.3), split 30/60, noise 1.2)

| condition | μ_Δ | true % ↓ w_d(0°) | σ_Δ | true d_z | pass | n_eff @150 | σ_meas w_d (weight / both) | obs d_z (weight / both) | power N=100 | N=130 | **N=150** | N=200 | emp. N=150 | MDE @150 (both) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_mu+0.00 | +0.00 |    0 % | 0.30 | +0.07 | 0.98 | 127 | 0.60 / 0.58 | +0.01 / -0.06 |  0.05 /  0.08 |  0.05 /  0.09 |  0.05 /  0.10 |  0.05 /  0.11 | 0.03 / 0.07 | 0.22 log = 20 % |
| A_mu-0.10 | -0.10 |   10 % | 0.30 | -0.30 | 0.97 | 127 | 0.59 / 0.56 | -0.18 / -0.10 |  0.39 /  0.15 |  0.48 /  0.18 |  0.54 /  0.20 |  0.66 /  0.25 | 0.55 / 0.16 | 0.22 log = 20 % |
| A_mu-0.20 | -0.20 |   18 % | 0.30 | -0.66 | 0.97 | 127 | 0.65 / 0.57 | -0.36 / -0.23 |  0.90 /  0.53 |  0.96 /  0.65 |  0.98 /  0.71 |  1.00 /  0.83 | 0.99 / 0.74 | 0.23 log = 20 % |
| A_mu-0.30 | -0.30 |   26 % | 0.30 | -0.92 | 0.96 | 125 | 0.62 / 0.56 | -0.44 / -0.35 |  0.98 /  0.88 |  1.00 /  0.95 |  1.00 /  0.97 |  1.00 /  0.99 | 1.00 / 0.98 | 0.22 log = 20 % |
| A_mu-0.40 | -0.40 |   33 % | 0.30 | -1.42 | 0.97 | 127 | 0.64 / 0.55 | -0.64 / -0.50 |  1.00 /  1.00 |  1.00 /  1.00 |  1.00 /  1.00 |  1.00 /  1.00 | 1.00 / 1.00 | 0.21 log = 19 % |

power cells are weight-model / both-model. At μ_Δ = 0 the 'power' column is the false-positive rate.

## B  heterogeneity of the mode effect  (mu_delta=-0.20)

| condition | μ_Δ | true % ↓ w_d(0°) | σ_Δ | true d_z | pass | n_eff @150 | σ_meas w_d (weight / both) | obs d_z (weight / both) | power N=100 | N=130 | **N=150** | N=200 | emp. N=150 | MDE @150 (both) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B_sd0.15 | -0.20 |   18 % | 0.15 | -1.26 | 0.97 | 127 | 0.59 / 0.57 | -0.40 / -0.37 |  0.95 /  0.91 |  0.99 /  0.97 |  0.99 /  0.98 |  1.00 /  1.00 | 1.00 / 0.99 | 0.20 log = 19 % |
| B_sd0.45 | -0.20 |   18 % | 0.45 | -0.33 | 0.97 | 127 | 0.60 / 0.55 | -0.24 / -0.22 |  0.58 /  0.50 |  0.69 /  0.61 |  0.76 /  0.67 |  0.87 /  0.80 | 0.79 / 0.70 | 0.23 log = 20 % |

power cells are weight-model / both-model. At μ_Δ = 0 the 'power' column is the false-positive rate.

## C  confound: mode effect on CHOICE BIAS only, w_d equal  (false-positive check)

| condition | μ_Δ | true % ↓ w_d(0°) | σ_Δ | true d_z | pass | n_eff @150 | σ_meas w_d (weight / both) | obs d_z (weight / both) | power N=100 | N=130 | **N=150** | N=200 | emp. N=150 | MDE @150 (both) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C_bshift | +0.00 |    0 % | 0.30 | +0.12 | 0.98 | 128 | 0.65 / 0.49 | -0.25 / +0.04 |  0.61 /  0.06 |  0.73 /  0.07 |  0.79 /  0.07 |  0.89 /  0.07 | 0.83 / 0.03 | 0.21 log = 19 % |

power cells are weight-model / both-model. At μ_Δ = 0 the 'power' column is the false-positive rate.

## D  Task-1 / Task-2 split, 90 trials per angle  (mu_delta=-0.20)

| condition | μ_Δ | true % ↓ w_d(0°) | σ_Δ | true d_z | pass | n_eff @150 | σ_meas w_d (weight / both) | obs d_z (weight / both) | power N=100 | N=130 | **N=150** | N=200 | emp. N=150 | MDE @150 (both) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D_split20_70 | -0.20 |   18 % | 0.30 | -0.59 | 0.98 | 128 | 0.71 / 0.60 | -0.34 / -0.19 |  0.87 /  0.42 |  0.94 /  0.52 |  0.97 /  0.58 |  0.99 /  0.71 | 0.99 / 0.61 | 0.22 log = 20 % |
| D_split45_45 | -0.20 |   18 % | 0.30 | -0.63 | 0.96 | 125 | 0.67 / 0.68 | -0.33 / -0.26 |  0.85 /  0.65 |  0.93 /  0.76 |  0.96 /  0.82 |  0.99 /  0.92 | 0.98 / 0.86 | 0.25 log = 22 % |

power cells are weight-model / both-model. At μ_Δ = 0 the 'power' column is the false-positive rate.

## E  rating noise SD on the 9-point scale  (mu_delta=-0.20)

| condition | μ_Δ | true % ↓ w_d(0°) | σ_Δ | true d_z | pass | n_eff @150 | σ_meas w_d (weight / both) | obs d_z (weight / both) | power N=100 | N=130 | **N=150** | N=200 | emp. N=150 | MDE @150 (both) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E_noise0.8 | -0.20 |   18 % | 0.30 | -0.68 | 0.99 | 129 | 0.60 / 0.51 | -0.34 / -0.24 |  0.87 /  0.61 |  0.94 /  0.72 |  0.97 /  0.78 |  0.99 /  0.89 | 0.98 / 0.83 | 0.19 log = 17 % |
| E_noise1.6 | -0.20 |   18 % | 0.30 | -0.70 | 0.95 | 125 | 0.70 / 0.68 | -0.21 / -0.18 |  0.48 /  0.37 |  0.59 /  0.47 |  0.66 /  0.52 |  0.78 /  0.65 | 0.69 / 0.52 | 0.25 log = 22 % |

power cells are weight-model / both-model. At μ_Δ = 0 the 'power' column is the false-positive rate.

## F  evidence boost, logit(prop) for the high sample  (mu_delta=-0.20; task default 1.2)

| condition | μ_Δ | true % ↓ w_d(0°) | σ_Δ | true d_z | pass | n_eff @150 | σ_meas w_d (weight / both) | obs d_z (weight / both) | power N=100 | N=130 | **N=150** | N=200 | emp. N=150 | MDE @150 (both) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F_boost0.5 | -0.20 |   18 % | 0.30 | -0.70 | 1.00 | 130 | 0.89 / 0.75 | -0.28 / -0.22 |  0.74 /  0.51 |  0.85 /  0.62 |  0.89 /  0.68 |  0.96 /  0.81 | 0.94 / 0.70 | 0.24 log = 22 % |
| F_boost0.8 | -0.20 |   18 % | 0.30 | -0.67 | 0.98 | 129 | 0.76 / 0.64 | -0.32 / -0.28 |  0.84 /  0.74 |  0.92 /  0.84 |  0.95 /  0.89 |  0.99 /  0.96 | 0.98 / 0.93 | 0.22 log = 20 % |

power cells are weight-model / both-model. At μ_Δ = 0 the 'power' column is the false-positive rate.

## Key quantities

- incorrect Task-2 trials per participant per angle (what identifies w_d): **16.9**; incorrect Task-1 trials (what anchors L0_incorrect): **8.7**
- per-angle measurement SD of log w_d, weight model: 0.60 (0°) / 0.58 (90°); both model: 0.58 / 0.57
- recovery r(log fitted, log true) w_d, both model: 0.65 (0°) / 0.52 (90°)
- participants surviving both angles' gates: 98%  →  150 recruited ≈ **127 paired**
- best model by BIC under Rollwage-like truth: {'null': 0.32, 'choice': 0.29, 'weight': 0.28, 'both': 0.11}
- exclusion reasons: {'': 1186, 'too_few_trials': 14}
