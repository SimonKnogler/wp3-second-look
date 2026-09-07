# Second Look — WP3: Belief Updating in Control Judgements

**A second look at one's own agency: post-decision evidence and confidence in control judgements.**

Work Package 3 of the doctoral project *When Expectations Take the Wheel: Investigating
Metacognitive Processes in Action Control* 

> **Status:** task built for lab (PsychoPy) and online (JavaScript), both bot-verified.
> **No human data collected yet.** Design is fixed pending preregistration.

---

## What the experiment asks

People judge which of two identical circles they are moving with the mouse. The judgement
is calibrated to be genuinely uncertain (~70.7 % correct), and then — on half the trials —
**more evidence arrives after the decision has already been made**. That evidence always
points to the truth, so it confirms participants who were right and refutes participants
who were wrong.

The question is how confidence in the original judgement responds:

1. **Is revision asymmetric?** Does confirming evidence move confidence more than
   disconfirming evidence of the same strength?
2. **Does the processing mode matter?** The same task is run with the movement mapped
   directly (0°, a valid internal forward model applies) and rotated by 90° (the model
   fails; control must be inferred from correlation over time). Difficulty is equated by
   staircase, so the two differ only in *how* the judgement is computed.
3. **Does it relate to delusional ideation?** PDI (Peters et al.), collected separately.

The dependent variable throughout is **confidence in a judgement about one's own control**.
Adapted from Rollwage, Dolan & Fleming (2018, *Current Biology*), using Wen Wen's Control
Detection Task.

Full rationale, design decisions and predicted data patterns:
**[`experiment/documents/WP3_briefing.pdf`](experiment/documents/WP3_briefing.pdf)** (14 pages).

---

## Repository map

```
experiment/
  task/        PsychoPy implementation (lab)
  web/         hand-coded JS port (online, Pavlovia/Prolific)
  analysis/    analysis pipeline + regression checks
  data/        participant data — see data/README.md (mostly gitignored)
  documents/   design doc, briefing PDF, slide decks, figures
Motion_Library/  pre-recorded mouse trajectories the task samples from
presentations/   slide decks for talks — add yours here
analysis_output/ generated results (gitignored)
```

---

## Running the task

### Lab version (PsychoPy)

Requires PsychoPy ≥ 2024 with numpy, pandas. On this machine:
`/opt/anaconda3/bin/python3` already has it.

```bash
cd experiment/task
CDT_WP3=1 CDT_CHECK_MODE=0 CDT_PARTICIPANT=1 python3 -u CDT_windows_blockwise_fast_response.py
```

A short functional run (a few minutes instead of ~55):

```bash
CDT_WP3=1 CDT_CHECK_MODE=1 CDT_PARTICIPANT=99 python3 -u CDT_windows_blockwise_fast_response.py
```

**Keys:** `SPACE` advance · `a`/`s` left/right circle · `1`–`9` confidence · `ESC` quit (saves).

**Environment flags**

| Flag | Default | Meaning |
|---|---|---|
| `CDT_WP3` | `0` | **must be `1`** — enables WP3 mode |
| `CDT_CHECK_MODE` | `1` | `1` = short functional run, `0` = full session |
| `CDT_PARTICIPANT` | — | participant id; also skips the GUI dialogs |
| `CDT_WP3_T1` / `CDT_WP3_T2` | `30` / `60` | trials per angle in Task 1 / Task 2 |
| `CDT_WP3_BOOST` | `1.2` | logit boost for high post-decision evidence |
| `CDT_WP3_EVDUR` | `3.0` | duration of the evidence sample (s) |
| `CDT_WP3_TRACK` | `1` | keep the staircase running through both tasks (`0` = freeze after calibration) |
| `CDT_WP3_BONUS` | `0` | max confidence bonus (quadratic scoring rule); `0` = points only |
| `CDT_BOT` | `0` | automated run, for regression testing |
| `CDT_WINDOWED` | `0` | windowed instead of exclusive fullscreen (needed when launched from a background process on macOS) |

### Online version (JavaScript)

Needs a web server — `file://` will not work.

```bash
cd experiment/web && python3 -m http.server 8000
# then open http://localhost:8000
```

URL parameters mirror the env flags: `?t1=6&t2=12&calmin=10&calmax=15&bonus=1.00&pid=99`.

Engine self-test (verifies the motion loop against the Python reference):

```bash
cd experiment/web && node test_engine.js
```

---

## Analysis

```bash
python3 experiment/analysis/analyze_wp3.py
```

Pools trials from both phases as evidence levels 0/1/2 and fits separate regressions
`confidence ~ evidence_level` for correct trials (confirmatory β) and incorrect trials
(disconfirmatory β), plus meta-d′ from Task 1 only. Rollwage's exclusion criteria are
applied.

**Regression check** — verifies that the evidence sample kept the decision trial's side
and rotation. Run it on any new data; a violation silently inverts the core measure:

```bash
python3 experiment/analysis/check_wp3_replay_invariant.py <kinematics.csv> [...]
```

---

## Known constraints (read before changing anything)

- **The evidence sample must inherit the decision trial's side and ±90° sign.** Both
  objects are identical circles, so participants identify them only by position. A pilot
  where the side was re-randomised produced 14/14 correct trials with confidence
  collapsing from 8 to 1–3: confirmation was experienced as refutation.
- **It is not a "replay".** The sample draws *fresh* trajectories — that is why it carries
  information. Only side, rotation and the true target are held constant.
- **The confidence score is never shown per trial.** It would reveal accuracy and destroy
  the feedback-free design. One total at the end only.
- **`prop` is capped at 0.90.** If a participant's medium converges above ~0.72 the boost
  clips and high ≈ low; those blocks are flagged (`prop_high_clipped`) and excluded.
- **The Bayes-optimal reference model is not built yet.** It decides the *sign* of the
  primary result, not just its precision — see §11 of the briefing. Build it before data
  collection so predictions can be preregistered.

---

## Open work

- [ ] Bayes-optimal reference model + choice-bias vs weighting model comparison
- [ ] Human feel-test of scale, evidence marker and scoring-rule instructions
- [ ] Pilot: what accuracy does the +1.2-logit boost actually induce? (Rollwage: 81 %)
- [ ] Consent / instruction / demographics screens for the online version
- [ ] Hosting: Pavlovia + Prolific + OSF DataPipe (`DATAPIPE_ID` in `web/index.html`)
- [ ] Preregistration

---

## Relationship to WP1

The task code is shared with WP1 (`../metasoa`): WP3 lives inside the same script behind
the `CDT_WP3` env flag. The two were byte-identical until 2026-09; WP3-specific fixes have
since diverged, so **changes to shared trial code must be reconciled manually**.

`Motion_Library/` contains only the five files the task actually loads.

---

## References

Full list in the briefing PDF. The primary sources:

- Rollwage, Dolan & Fleming (2018). Metacognitive failure as a feature of those holding
  radical beliefs. *Current Biology* 28(24), 4014–4021.
- Wen, Charles & Haggard (2023). Metacognition and sense of agency. *Cognition* 241.
- Peters, Joseph & Garety (1999). Measurement of delusional ideation in the normal
  population: introducing the PDI. *Schizophrenia Bulletin* 25(3), 553–576.

Papers are not stored in this repository.
