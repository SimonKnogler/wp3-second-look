# Data

**Raw participant data is not versioned in git.** It goes to OSF; this folder keeps the
structure so the paths in the scripts work out of the box. Only `.gitkeep` files and this
README are committed.

```
data/
  pilot/            pilot sessions (feel-tests, boost calibration)
  real/raw/         main data collection, one file per session
  real/processed/   cleaned / merged files produced by the analysis
  simulated/        bot runs — regenerate, never commit
```

## File naming

The PsychoPy task writes two files per session:

```
CDT_v2_blockwise_fast_response_<participant>.csv             one row per trial
CDT_v2_blockwise_fast_response_<participant>_kinematics.csv  one row per frame
```

A repeated participant id gets a `_1`, `_2` … suffix rather than overwriting. The online
version writes `CDT_wp3_<participant>.csv` (trial level only).

## Trial-level columns that matter

| Column | Meaning |
|---|---|
| `phase` | `calibration`, `wp3_task1`, `wp3_task2`, `wp3_evidence`, `wp3_summary` |
| `evidence_level` | `0` none (Task 1) · `1` low · `2` high (+1.2 logit) |
| `angle_bias` | `0` prediction mode · `90` regularity mode |
| `prop_used` | control strength of the decision trial |
| `prop_post` | control strength of the evidence sample |
| `med_live` | running staircase threshold — drift trace |
| `prop_high_clipped` | `True` = boost hit the 0.90 ceiling, high ≈ low → **exclude block** |
| `accuracy` | 1 correct, 0 incorrect |
| `rt_choice` | decision RT (s) |
| `wp3_confidence` | 1–9, subjective P(correct); **< 5 is a change of mind** |
| `wp3_prob` | the same on a 0–100 scale |
| `wp3_conf_rt` | confidence RT (s) — used for exclusions |
| `wp3_score` | quadratic scoring rule score for that trial (never shown to the participant) |
| `is_timeout` | no response during the movement window |

The `wp3_summary` row carries participant-level fields: `wp3_mean_score`, `wp3_bonus`,
`bonus_quiz_attempts`, `bonus_motivation_1to5`.

## Exclusions (following Rollwage)

Applied in `analysis/analyze_wp3.py`:

- accuracy outside 0.60–0.85 (staircase failed to converge)
- one confidence rating used on > 90 % of trials
- median confidence RT < 850 ms
- blocks with `prop_high_clipped = True`

## Before analysing new data

Run the invariant check — a violation silently inverts the core measure:

```bash
python3 ../analysis/check_wp3_replay_invariant.py real/raw/*_kinematics.csv
```
