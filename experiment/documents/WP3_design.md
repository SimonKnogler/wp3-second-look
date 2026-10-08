# WP3 — Belief Updating in Control Detection

**Status:** design fixed, desktop + web tasks built & bot/Node-verified, analysis
built & self-tested. First human check runs done (2026-09-03): replay
side/rotation bug fixed (§10b), replay marker added (§10c), control rating
tried & removed (§3), literature pass (§10d). Last updated 2026-09-03.

Adapts **Rollwage, Dolan & Fleming (2018, *Current Biology*), "Metacognitive
Failure as a Feature of Those Holding Radical Beliefs"** (PDF in this folder) to
the Control-Detection Task (CDT). WP3 is the **online** work package of the
dissertation (proposal: N ≈ 150).

---

## 1. Research questions

**Big question:** When people receive new evidence *after* a decision, do they
revise their belief rationally — or hold on and under-weight what contradicts
them (confirmation bias)?

1. **Is there an asymmetry?** Do people weight confirming evidence more than
   disconfirming? (confirmatory vs disconfirmatory integration)
2. **Does it depend on the processing mode? (core hypothesis)** Is the bias
   stronger in the prediction-based mode (0°, fixed internal model) than in the
   regularity-based mode (90°, flexible)?
3. **Clinical bridge:** Does delusional ideation (PDI) predict resistance to
   disconfirmatory evidence, especially at 0°?

Secondary (Rollwage): does task-1 **meta-d′** predict sensitivity to
post-decision evidence?

**Dropped from the proposal (deliberate):** the expectation **cues** and the
easy/hard difficulty levels. None of Q1–Q3 need them; they are WP1 machinery.
Following Rollwage, WP3 uses a **single medium difficulty** — at ~71% correct you
get both correct (~confirmatory) and incorrect (~disconfirmatory) trials
naturally, so no difficulty range is required.

---

## 2. The paradigm

**Base — CDT:** two shapes (square, dot); the participant moves the mouse and one
shape follows (blended with a pre-recorded trajectory), the other is an
independent decoy. After ~3–5 s: *"which shape did you control?"* Difficulty =
control proportion `prop`; a 1-up-2-down staircase fixes it at **70.7% correct**
(the point of maximum uncertainty, where evidence has room to shift the judgment).

**Two processing modes, blocked by angle** (order counterbalanced):
- **0° (prediction):** shape follows the mouse directly — a fixed internal model.
- **90° (regularity):** movement rotated 90° — the model fails, one must detect
  the pattern flexibly.

**Two phases** (the Rollwage twist; the only difference is *when* confidence is asked):
- **Task 1** — decision → **confidence**. (baseline, "evidence level 0"; gives meta-d′)
- **Task 2** — decision → **post-decision evidence sample** → **confidence**.

**Post-decision evidence sample (the key mechanic):** a second short motion
sample (no response) that always re-shows the **TRUE target** more clearly —
independent of what the participant chose.
- Chose correctly → sample **confirms** → confidence should rise.
- Chose incorrectly → sample points to the OTHER shape → **disconfirms** →
  confidence should fall.
- ⚠️ The proposal's wording "for the object they have chosen" is imprecise; taken
  literally it makes every sample confirmatory and breaks the design. Correct
  (Rollwage): the evidence points to the **correct** answer.

**Three evidence levels** (the analysis x-axis):
| level | source | strength |
|---|---|---|
| 0 | Task 1 | none |
| 1 (low) | Task 2 | same as decision (medium prop, ~0.26) — a fresh 2nd sample |
| 2 (high)| Task 2 | boosted (+1.2 logit, ~0.26 → ~0.54) |

"Low" is *not* "no info": it is a second independent sample at the same clarity.

---

## 3. Confidence scale (exactly Rollwage)

9-point scale = **subjective probability the decision was correct**:
`1 = 0%` (sure it was the OTHER shape) · `5 = 50%` (pure guess) · `9 = 100%` (sure
my choice). Below the midpoint expresses a **change of mind** — so a reversal is
captured continuously, **without a second decision**. (An earlier "guessing →
certain" scale was wrong: its floor at 50% could not express "I was wrong" and
would compress the disconfirmatory measure.)

Logged as `wp3_confidence` (1–9) and `wp3_prob` (0–100).

**Incentive (added 2026-09-03, as Rollwage):** confidence is paid by the
**quadratic scoring rule**, p = (rating−1)/8, score = 1−(1−p)² if correct,
1−p² if incorrect; timeouts score 0. Proper: honest reporting maximises
expected pay; 'sure and right' and 'sure I was wrong and was wrong' both pay
the maximum — which removes the only *motivational* reason to defend a refuted
choice without touching the belief-side mechanisms (prior precision, choice
bias, gain modulation) H2 is about. Rollwage found his effect *with* this rule.
Rules that follow from the design: (a) **both tasks, identically** — the
slopes run from Task 1 to Task 2, an asymmetric incentive would be a slope
artefact, and meta-d′ comes from Task 1; (b) **never shown per trial** — the
score reveals correctness exactly, the task is feedback-free; one total at the
end; (c) principle explained, formula not, with a **two-item comprehension
quiz** that loops until passed (`bonus_quiz_attempts` logged) — answered **on
the 1–9 scale itself** (accept ≤2 / ≥8); a first version offered 1/2/3 answer
keys labelled "8–9 / 5 / 1–2", so the key to press was nearly the opposite of
its meaning, and the first human check run stopped there. The explanation
leads with what is rewarded — *knowing when you are right, not performance*:
being wrong costs nothing if you notice it, and both "right + rated 9" and
"wrong + rated 1" pay in full; (d) a
**manipulation check** ("how much did the rule affect how carefully you
rated", 1–5, `bonus_motivation_1to5`) asked *before* the reveal. Logged per
trial as `wp3_score` (participant never sees it); `wp3_mean_score`,
`wp3_bonus` at participant level. Env `CDT_WP3_BONUS` (max, 0 = lab mode with
points) / web `?bonus=`. Power side-effect: lower rating noise raises β
reliability (.79 → up to .86), worth ~30–60 participants on Q3.

**Control rating — tried and removed (2026-09-02 → 2026-09-03).** A 7-point
"how much control over the shape you chose" probe after each confidence rating
was implemented and run once (participant 97). Removed: it broke the trial
rhythm, and as a second rating immediately after the first it would mostly
track confidence (anchoring) rather than dissociate experience from judgment.
The dissociation question is real but needs its own design (e.g. rating order
counterbalanced between subjects, or the control rating on a subset of trials
*instead of* confidence) — parked, see §12 follow-ups.

---

## 4. Trial structure & numbers (defaults, per participant)

| phase | per angle | × 2 angles | purpose |
|---|---|---|---|
| Calibration (1u2d) | ~50 (min 40 / max 80) | ~100 | find medium (70.7%) |
| Task 1 | 30 | 60 | baseline, level 0 |
| Task 2 (½ low / ½ high) | 60 | 120 | levels 1 & 2 |
| **Total** | ~140 | **~280** | ≈ 55–60 min (incl. control rating) |

- ~90 decision trials / angle → at 71% ≈ **26 incorrect** / angle (the precious
  disconfirmatory trials). Bottleneck for single-subject betas; raise `T2` if
  per-angle precision matters, else rely on N. Rollwage had 120 Task-2 trials in
  a single context.
- Trajectory budget: pool = 1280 usable (1200 shipped to web); WP3 uses ~800
  trajectory-draws/session → comfortable, recycles gracefully if exhausted.

---

## 5. Measures & what "rational" means

Per participant × angle:
- **confirmatory β** = slope of confidence over evidence level (0→1→2) on
  **correct** trials (should be positive).
- **disconfirmatory β** = slope on **incorrect** trials, sign-flipped (higher =
  more revision after contradiction).
- **meta-d′** (MLE, Maniscalco & Lau) from Task 1 only.
- **Task-2 sensitivity** = accuracy × evidence interaction (does the update scale
  with evidence strength?).

**No trial pairing across phases.** Task 1 is the level-0 anchor; each trial is
classified correct/incorrect by its *own* decision and enters a pooled regression
as a data point at its evidence level. A trial being correct in phase 1 and
incorrect in phase 2 is irrelevant — they are never compared as a pair. The
"update" is the *slope/gap* vs the no-evidence (level-0) baseline, aggregated
within each correctness class — not a within-trial difference.

**Operationalising "rational" — three levels:**
1. **Sign:** up for confirming, down for disconfirming. (The correct direction is
   known because evidence always points to the truth.)
2. **Symmetry (our primary index):** confirmatory β ≈ disconfirmatory β.
   Confirmation bias = disconfirmatory β < confirmatory β. Descriptive, robust,
   computed now.
3. **Bayes-optimal (the strict normative yardstick):** an SDT ideal observer
   combines the pre- and post-decision evidence (both of known strength) into an
   optimal posterior; deviation from it = irrationality, its direction = the bias.
   Predicts (a) bigger updates for high than low evidence [captured by the
   interaction term] and (b) a specific optimal magnitude. **The full Bayes model
   + Rollwage's model comparison (choice-bias vs optimal) is NOT yet built** — the
   symmetry index is the primary analysis; the Bayes model is the next step.

---

## 6. Analysis pipeline

`experiment/analysis/analyze_wp3.py` (self-tested: recovers meta-d′; separates
rational vs confirmation-biased synthetic agents). Faithful to Rollwage:
- Exclusions: accuracy ∉ [0.60, 0.85], one confidence >90% of trials, median
  confidence RT < 850 ms, >5% timeouts.
- meta-d′ (MLE) from Task 1; confirmatory/disconfirmatory β; Task-2 interaction.
- Group (two-stage): Q1 asymmetry, Q2 0° vs 90° paired, meta-d′→sensitivity,
  Q3 PDI correlations (`--pdi participant,pdi`).
- Figure: confidence × evidence, correct vs incorrect, per angle (Rollwage Fig 4B).
- Reads columns: `phase, wp3_task, evidence_level, angle_bias, accuracy,
  wp3_confidence, wp3_conf_rt, is_timeout, participant` — **identical for desktop
  and web**, so it runs on either unchanged.
- **Not built:** Bayes-optimal reference + computational model comparison;
  hierarchical mixed models (two-stage is Rollwage's primary approach).

---

## 7. Implementation

**Desktop (PsychoPy):** `experiment/task/CDT_windows_blockwise_fast_response.py`,
flag `CDT_WP3=1`. Per-block 1u2d calibration → Task 1 → Task 2 with the evidence
sample. `run_trial` gained `accept_response` (evidence sample = motion-only) and
honors `motion_dur`. Env: `CDT_WP3_T1/T2/BOOST/EVDUR`. Launch (fullscreen, from
Simon's own session via `!`):
```
CDT_CHECK_MODE=0 CDT_WP3=1 CDT_PARTICIPANT=<n> python -u CDT_windows_blockwise_fast_response.py
```

**Web (for online / Pavlovia):** `experiment/web/` — the online path (WP3 is the
online WP). *Not* PsychoJS (hand-coded, no Builder); a genuine JS port.
- `engine.js` — motion loop ported line-for-line; Node-verified (prop 0 → chance,
  monotone rise, ceiling at 0.5 — matches Python).
- `index.html` — full flow (staircase → Task 1 → Task 2), canvas +
  requestAnimationFrame, 9-point confidence, CSV export (same columns as above).
- `motion_pool.bin`/`.json` — real trajectories (1200 × 298 × 2, 2.9 MB), from
  `export_pool_for_web.py`.
- Local test needs a server: `python3 -m http.server 8000` → `localhost:8000`
  (mouse, not trackpad). Short run: `?t1=6&t2=12`.
- URL config: `t1, t2, calmin, calmax, boost, evdur, pid, seed`.

---

## 8. Hosting plan (online study)

- **Recruitment: Prolific** (`?pid={{%PROLIFIC_PID%}}`).
- **Hosting: Pavlovia** (static git repo — push the 4 web files). Check for an LMU
  Pavlovia site licence (then free). Alternatives: Cognition.run (free, piloting),
  Netlify.
- **Data: OSF DataPipe** (set `DATAPIPE_ID` in index.html — host-agnostic) or the
  built-in CSV download. Native PsychoJS saving deliberately not used.
- `analyze_wp3.py` runs on the resulting CSV unchanged.

---

## 9. Open items / honest caveats

- **No human run yet** — bot/Node verify plumbing & math, not the *feel* (browser
  test; is the 3-s evidence sample long enough to feel the difference? `EVDUR`).
- **PDI questionnaire** collected externally, not in the task.
- **Bayes-optimal model + model comparison** not built (§5 level 3).
- **Web:** browser feel-test pending; consent/instructions/demographics screens
  not added; trajectory pairing simplified to random pairs (engine
  speed-equalisation is the main anti-cue protection); motor-task-online caveats
  (mouse vs trackpad, DPI, frame rate → enforce mouse + fullscreen, log frame
  rate, apply the Rollwage exclusions already in the analysis).
- **Single-subject precision** limited by ~26 incorrect trials/angle; the effects
  are group-level (N ≈ 150).
- **Boost ceiling (found 2026-09-03):** `clamp_prop` caps prop at 0.90. If a
  participant's medium converges above ~0.72, `medium + 1.2 logit` is clipped
  and *high ≈ low* — the evidence manipulation silently collapses for that
  block. Logged as `prop_high_clipped` (per row) with a console warning; treat
  clipped blocks as excluded (Rollwage's accuracy band does not catch this,
  it is a prop-level problem). Expect it mainly at 90° in weaker detectors.

---

## 10. Related direction (staffing / BA thesis)

WP3's core *is* a cognitive bias (confirmation bias / belief perseverance) — the
engine behind many logical fallacies (cherry-picking, motivated reasoning). A
prospective intern interested in the **cognitive-bias ↔ logical-fallacy** mapping
could contribute the conceptual layer (which fallacies reduce to a belief-updating
failure?) grounded by WP3's empirical measure — a viable BA angle.

---

## 10b. Bug found & fixed in first human check run (2026-09-03)

**Symptom:** participant 97, all 14 WP3 trials correct, yet confidence collapsed
from 8/8/8 in Task 1 to 1–3 in Task 2 — confirming evidence read as
disconfirmation. Confidence RTs of 10–16 s on some Task-2 trials (confusion).

**Cause:** both objects are *identical black circles* (`square`/`dot` is
internal bookkeeping only); the participant identifies them purely by side and
answers with spatial keys (a/s). `run_trial` re-rolled `left_shape` on every
call — including the evidence sample — so in ~50 % of Task-2 trials the true
target swapped sides between decision and replay. The correct object was
replayed, on the wrong side.

**Second instance of the same class:** at 90° the rotation *sign* (±90°) was
also re-drawn per `run_trial` call, so the replay could run with the mapping
mirrored relative to the decision ("up → left" became "up → right") — the
learned regularity, not just the side, could flip.

**Fix (both):** `run_trial(..., left_shape=None, applied_angle_override=None)`;
the evidence sample passes `left_shape=res['left_shape']` and
`applied_angle_override=res['applied_angle_bias']`, inheriting the decision
trial's layout and rotation. `left_shape` is now logged per kinematics frame so
both invariants are verifiable (bot-checked). **Web port fixed in the same
commit** — `motionTrial(..., {forceLeft, forceApplied})` in
`experiment/web/index.html`, evidence call passes `r.left`, `r.applied`.

**Verified 2026-09-03** on bot run 9703 (`data/simulated/bot_runs/`): all
Task-2 trials identical in side, ±90° sign and target between decision and
replay (`analysis/check_wp3_replay_invariant.py` → OK 7/7; a timed-out trial
correctly has no replay). The checker treats "no matched trials" as a failure —
the first attempt silently passed on a logging gap.

**General rule this establishes:** *the evidence sample must be a replay of the
decision trial in every respect except control strength.* Any future
per-trial randomisation added to `run_trial`/`motionTrial` must be threaded
through to the evidence call.

**Lesson:** this would have silently inverted the core measure in a full run,
and no plumbing test (bot/Node) could catch it — only a human noticing that
confirmation "felt wrong". Keep the pre-pilot human check run in the protocol.

## 10c. The evidence sample must be marked — and named correctly (2026-09-03)

Human check run: the evidence sample was not experienced as belonging to the
trial just answered. Cause: Rollwage's post-decision evidence appeared
*passively* (350 ms of dots, "bonus information" by instruction only); ours
re-uses the full active trial — fixation, wait-for-movement, 3 s of motion — so
unmarked it reads as a new trial. Fix: the fixation cross is replaced by an
"EXTRA EVIDENCE — same two circles, a second look" cue, a persistent top label
runs during the movement, and the Part-B instruction spells out the two-part
trial (both platforms). No change to timing or evidence strength.

**Do not call it a "replay".** `find_matched_trajectory_pair()` / `pickPair()`
run on every `run_trial` call and consume *unused* snippets, so the evidence
sample draws **fresh trajectories**, and the participant moves the mouse anew:
it is a second **independent** sample, which is exactly why it carries new
information (a literal repeat would carry none — cf. Rollwage's "a new sample
of flickering dots"). Constant across decision and evidence are only: the two
circles, their sides, the ±90° sign, and which one is truly controlled. The
same holds across Task 1 and Task 2 — no trajectory is ever reused in a
session (~800 draws of 1280 available). A first version of the marker said
"REPLAY — same trial, watch again", which would have told participants to
expect a repeat and to discount the sample when it looked different; renamed
throughout (`evidence_cue`, `evidence_label`, `is_evidence`, `EVIDENCE_ON`).

## 10d. Literature pass (2026-09-03) — what it changes

- **Rollwage et al. 2020, Nat Commun.** Two confidence ratings per trial (before
  and after 350 ms post-decision dots); high *initial* confidence abolished
  disconfirmatory processing (MEG). This is the mechanism H2 rests on. **Open
  design fork:** a pre-evidence confidence rating would give a within-trial
  update and a trial-level test of confidence gating — at the cost of breaking
  Task-1/Task-2 comparability (Rollwage 2018 deliberately did *not* rate before
  the evidence in Task 2) and possibly increasing commitment via reporting.
  Not implemented; decide before preregistration.
- **Talluri et al. 2018, Curr Biol.** Choice vs no-choice between two motion
  intervals: choice-consistent evidence is *actively overweighted* (gain
  modulation), not merely ignored. Establishes the "evidence-then-decide"
  control as a proven manipulation (our option C) and predicts the same
  gain-modulation signature here.
- **Changes-of-mind without post-decision evidence (Fleming lab).** Reversals
  occur with no new evidence and are tied to *slow* initial RTs. Consequences:
  (i) level 0 is not "no revision", it is "revision from internal uncertainty
  only"; (ii) `rt_choice` enters the models as a covariate; (iii) a below-midpoint
  rating in Task 1 is a legitimate change of mind, not noise.
- **Rollwage 2018 details worth copying:** confidence incentivised with a
  quadratic scoring rule; ~10 % excluded for median confidence RT < 850 ms;
  high evidence = log-strength × 1.3 → 81 % correct (ours: +1.2 logit; check
  the induced accuracy in the pilot the same way).

## 10e. Continuous staircase through both tasks (2026-09-03)

**Why.** WP3's three evidence levels are **time-ordered**: level 0 is all of
Task 1, levels 1–2 are all of Task 2. So *anything* that changes over time
enters the confidence slope as if it were an evidence effect. Simon reports
strong learning effects in earlier runs of this paradigm; WP1 hit the opposite
in pilot p99 — the same prop yielded 69% in calibration (with feedback) but 57%
in test (without), collapsing medium toward chance. Either direction
contaminates the phase comparison, and the second also starves the scarce
incorrect trials.

**What changed.** The per-block 1u2d no longer freezes after calibration: the
same staircase keeps running through Task 1 and Task 2 (`CDT_WP3_TRACK=1`
default, `=0` restores Rollwage's fixed prop; web `?track=`). This mirrors
WP1's test-phase tracking (`CDT_TRACK_TEST`), so the two work packages stay
1:1. Per decision trial: prop = live `next_stimulus()`, and **high = that
trial's own prop + 1.2 logit**, so the two evidence levels stay exactly one
boost apart whatever the difficulty. Updates come from the **decision only** —
the evidence sample never feeds the staircase. Logged per trial: `prop_used`,
`prop_post`, `med_live` (live threshold estimate, a drift trace) and
`prop_high_clipped` (now per trial, since the ceiling can be hit transiently).

**Costs, accepted.** (a) The step itself is weak implicit feedback in a
feedback-free task — mitigated by the small step size after the calibration's
reversals; WP1 has run this way since July. (b) Evidence strength is no longer
constant across trials — not a problem for the analysis, which needs the actual
per-trial props anyway (and the Bayes reference model *requires* them).
(c) Incorrect trials cluster after step-downs — inherent to any staircase;
carry prop and trial index as covariates. Trial index stays a covariate
regardless, since tracking equates accuracy, not learning.

## 10f. PsychoPy gotcha: poll loops must flip (found 2026-09-04)

Three human check runs in a row stopped before the first calibration, with only
a header row saved. Cause: the bonus quiz and the motivation check polled
`event.getKeys()` in a `while` loop that drew and flipped **once before** the
loop. On the pyglet backend `win.flip()` is what dispatches window events, so
without a flip inside the loop the keyboard queue is never pumped and *no key
is ever seen* — including ESC. The screen simply sits there. Every other rating
screen in the script (e.g. `wp3_confidence`) draws + flips inside its loop,
which is why only the two newly added screens were affected. Fixed; a scan of
every `while` loop containing `event.getKeys` now reports none without a flip.
**Rule for any new response screen: draw and flip on every iteration.**

## 10f. Analysis dry-run on simulated data (2026-09-15) — what it changed

`analysis/simulate_wp3.py` writes sessions in the task's exact CSV layout (calibration
rows, `wp3_task1/2`, `wp3_summary`; `--format web` for the online layout) from a
generative observer with known w_c / w_d per angle, a running 1u2d, timeouts, clipping and
a PDI correlated with w_d(0°). `analysis/fit_wp3_model.py` is the model-based analysis
(psychometric → per-trial evidence logit → censored-Gaussian ML fit of w_c, w_d; null /
weight / choice-bias / both models by BIC; two-stage group tests; parameter recovery
against `ground_truth.csv`). Both pipelines were run on N = 150 simulated participants
under four truths: mode effect (w_d 0.45 vs 0.85), null (0.95/0.95), pure choice bias
(b = 0.8, weights equal), and a milder boost. Findings, in order of consequence:

1. **The descriptive β index is inverted by the scale, as predicted (§10d).** On data with
   a strong built-in bias at 0°, `analyze_wp3.py` reports β_conf = 0.44 < β_disc = 1.29 —
   "more disconfirmatory than confirmatory integration". It is a faithful Rollwage
   replication and it gives the wrong sign for H1. Keep it as the descriptive layer; it is
   not the primary test.
2. **H1 as a w_d/w_c ratio is biased toward finding confirmation bias.** Under the null,
   the ratio test still came out p = 5e-4, because w_c is inflated at the ceiling (median
   1.15 vs truth 0.95). **w_c is not identified per person in this paradigm**: correct
   trials start near 9, so almost any w_c ≥ 0.5 fits. Recovery r ≈ 0.1–0.3 regardless of
   likelihood or boost. → Report w_c at group level only; do not build H1 on the ratio.
3. **w_d is well identified and the mode contrast on w_d is the primary model-based test.**
   Recovery r = 0.55–0.72, bias ≈ 0. Paired test on log w_d (0° vs 90°): true effect
   p = 4e-20; null p = 0.86; pure choice bias p = 0.71 (correctly null — commitment does
   not create a mode difference). Medians recover the truth (0.30 vs 0.71 for 0.43/0.87).
4. **A pure choice bias masquerades as confirmation bias in the weight model** (fitted
   w_d = 0.5 with true w_d = 0.95) — the intercept/slope confusion from §10d — and the BIC
   comparison catches it once an explicit **ideal-observer null model** (w = 1, b = 0) is
   in the set: under pure choice bias "choice" wins 70–84 of 150 per angle and the null
   model 9–24; under the true null the null model wins 71–85 and "choice" only 27–31.
   Without the null model, "choice" also won under the null simply by having fewer
   parameters. The w_d mode test is correctly null in both cases (p = .86 / .71).
5. **Saturation is a design issue, not just an analysis one.** With +1.2 logit, 60 % of
   correct high-evidence ratings are 9. A milder boost (0.6) barely helps because the
   *baseline* on correct trials is already ~7.8. The +1.2 boost should be validated in the
   pilot against the accuracy it induces (Rollwage: 81 %); if it induces > 90 % the high
   level is near-decisive and adds little beyond the low level.
6. **Unbounded fits explode.** A few participants' w_c went to 10⁹. Weights are now bounded
   to [0.05, 3], flagged (`at_bound`), and group t-tests use a 5–95 % winsorised log-ratio;
   medians are reported raw. A full hierarchical (Stan) fit would do this properly.
7. **Data-structure quirks found in the real CSVs:** (a) keys logged both via `addData`
   and `extraInfo` come out twice (`participant.1`, `wp3_mean_score.1`, …, `Unnamed: 71`)
   — fixed in the task for the WP3 additions, and both loaders strip `.1`/`Unnamed`
   columns; (b) the calibration phase is `calibration_interleaved`; (c) `is_timeout` /
   `prop_high_clipped` arrive as bool, string or NaN depending on the row — loaders coerce
   explicitly (`astype(bool)` on the string `"False"` is `True`); (d) the **web CSV has no
   calibration rows** — the psychometric function is still estimable from Task 1+2 because
   the staircase keeps prop varying (`CDT_WP3_TRACK=1`); with a frozen prop it would not be.
   Keep tracking on, or log calibration in the web port; (e) in the **kinematics** file the
   calibration `trial_num` counter restarts for the second block, so the same `trial_num`
   appears under both angles — group on `(phase, angle_bias, trial_num)`, never on
   `trial_num` alone, or two calibration trials silently merge into one. Task-1/2 and
   evidence rows are unaffected (continuous counter).
8. **The PDI test is the weakest link,** as the power analysis said: with true r = −0.35
   on w_d(0°) it is detected at N = 150 (r ≈ −0.22, Spearman −0.30, p < .01) but one
   unlucky seed (latent r = −0.11) shows nothing. Preregister Spearman on w_d(0°).

Dry-run outputs live in `analysis_output/` (gitignored); regenerate with the two scripts.

## 10g. Fixed decision window (2026-09-24)

The choice used to be taken *during* motion: the trial ended on the keypress
(`while clk.getTime() < total_motion_duration and resp_shape is None`). That is WP1's
regime, and the `*_preRT` columns exist to serve it — evidence accumulated up to the
response, for drift-diffusion analysis.

It is wrong for WP3. Viewing time *is* evidence quantity here, so self-termination made
evidence-per-trial vary (a) uncontrolled, (b) **with confidence** — people bail early on
trials that feel easy, so high-confidence trials carried less evidence — and potentially
(c) **with angle**, which is the primary contrast. A mode difference in sampling policy
would have been indistinguishable from a mode difference in evidence weighting, and the
psychometric-to-LLR step in `fit_wp3_model.py` assumes comparable evidence given `prop`.
The staircase inherited the same problem: a threshold averaged over variable exposures.

Now: the motion window is fixed and the choice is taken after it, from a frozen display.
Window set to **3 s** (`CDT_WP3_MOTIONDUR` / `?motiondur=`), matching the 3 s evidence
sample, so both stages of a Task-2 trial deliver the same exposure. A late answer no
longer discards the trial (`CDT_WP3_RESPGRACE`, default 20 s, then a real timeout).
`rt_choice` is now deliberation time from the prompt, not sampling time; `*_preRT`
columns are NaN for WP3 decision trials by construction.

WP1 is untouched: the behaviour is opt-in per call
(`run_trial(respond_after_motion=True)`, default `False`), and WP3's calibration passes
the same window as the task it calibrates.

Verified on a bot session (p901, both angles): 14/14 decision trials answered, **no
timeouts**, `rt_choice` 1.9–3.7 s measured from the prompt, and the replay-invariant
check passes on all 8 evidence samples. Frames per trial are now equal across
calibration, Task 1, Task 2 and the evidence sample (867–1102, ~5 % frame-rate jitter) —
the decision trials match the evidence sample, which was fixed-duration by construction,
i.e. evidence per trial is now constant where it used to be whatever the participant
chose to take.

## 10h. Power / feasibility at the hard cap N = 150 (2026-09-24)

`experiment/analysis/power_wp3.py` — Monte Carlo over the **complete** pipeline: the
`simulate_wp3.py` observer recalibrated to Rollwage 2018 (group `w_d(90°)` ≈ 1, choice bias
`b ~ N(.4, .3)` — the mechanism that won his model comparison), analysed with
`fit_wp3_model.fit_participant` verbatim (gates, anchors, bounds). 18 conditions, 9,800
simulated participants. Tables: `power_wp3_report.md`, `power_wp3_summary*.csv`.

1. **The weight model cannot be the primary test.** With the true mode difference placed in
   choice bias only (`w_d` equal across angles) it reports a `w_d` mode effect of −0.22 log and
   rejects H0 in **79 %** of N = 150 samples; with a real `w_d` effect it inflates it by 25–50 %
   (true −0.20 → −0.31). The **both** model (`b`, `w_c`, `w_d`) is unbiased to within
   0.02–0.05 log in every condition and reads +0.03 under the confound.
2. **Feasible for a medium-or-larger effect.** Both model, 150 recruited → ~127 paired (13 %
   attrition + gates): **MDE = 0.22 log = 20 % reduction in `w_d` at 80 % power**, stable at
   19–20.5 % across all 18 conditions. Power: 10 % → 0.20; 18 % → ~0.80 (0.71–0.89 across
   independent pools); 26 % → 0.97. Rollwage's extreme-group (top-decile radicals) difference
   is ≈ 30 %. Not feasible for a ≤ 10 % effect at any affordable N.
3. **Measurement noise, not N, is the constraint.** Per-angle SD of log `w_d` ≈ 0.57 → 0.81 of
   the 0.87 paired SD; true heterogeneity (0.30) is minor. Recovery r ≈ 0.65 at 0° but ≈ 0.50 at
   90°: the harder angle clips the boosted sample against the 0.90 ceiling more often. N = 200
   would move 18 % power only to ~0.83. Rating noise 1.6 → 0.8 moves it 0.52 → 0.78 — the scoring
   rule stays.
4. **Boost.** 0.8 / 1.0 / 1.2 logit are power-equivalent within Monte Carlo error (0.84 / 0.78 /
   0.87 at 18 %, pools of 800); 0.5 is worse (0.68). Implied accuracy of the high sample: 1.2 →
   93 %, 0.8 → 87 %, 0.5 → 82 % (Rollwage: 80 %). Keep 1.2 for power, or drop to 0.8 for Rollwage
   comparability and less ceiling clipping at 90°; both defensible.
5. **Split** 30/60 vs 20/70 vs 45/45 (90 trials per angle): within noise; no change.
6. **Small null bias of the both model:** its paired difference averages ≈ −0.045 log when the
   truth is 0 (two independent pools, 600 and 800) → Type I ≈ 0.07–0.09 at nominal .05. Source
   is the design asymmetry in (3). Preregister a **parametric-bootstrap null** (simulate from the
   fitted parameters with `w_d` equalised across angles) or a simulation-calibrated α.
7. Incorrect Task-2 trials per angle: **16.9** (the earlier reliability estimate assumed ~26);
   incorrect Task-1 trials anchoring `L0_incorrect`: 8.7.

**Decision:** run at N = 150. Preregister the both model as primary, the 20 % MDE, and the
bootstrap null. PDI dropped from the confirmatory set (Rollwage's r ≈ .10–.17 needs N ≈ 400+).

## 10i. Validation run: does the analysis measure what we set out to measure? (2026-09-29)

Ten participants were simulated to behave as the hypothesis states (w_d at 0° = 0.6 × w_d at
90°; commitment and confirmatory weight equal), written in the online task's exact file layout
(`make_validation_data.py`, seed fixed beforehand), and put through the complete planned
analysis (`wp3_paper_analysis.py`). Report: `WP3_validation_results.html`; poster on the canvas.

1. **The primary measure works.** Difference in log w_d put in −0.67, recovered −0.77, 95 % CI
   [−1.17, −0.37], t(9) = −4.35, p = .002, d_z = −1.38; bootstrap null p = .003. Commitment did
   not differ between mappings, as built in. Individual weights recovered at r = .83.
2. **The level of w_d is biased low; never test it against 1.** The strong evidence sample lies
   outside the range the staircase visits, so its strength is extrapolated from a psychometric
   slope that is itself over-estimated (strong sample: true 3.0, fitted 3.5–4.7). An over-estimated
   evidence strength is compensated by an under-estimated weight: fitted/true = 0.75 with
   calibration trials in the fit, 0.66 without (120 simulated participants per cell). The factor is
   the same at both mappings, which is why the contrast survives. A weaker boost (0.8) does not
   change it. (§10j: the new design measures the strength of the strong sample instead.)
3. **The fix: an ideal-observer benchmark.** Each participant's session is re-simulated from
   their fitted parameters with w_d = 1 and refitted. Through this pipeline an ideal observer
   returns w_d = 0.83, not 1. Against that benchmark the run gave the correct answer at both
   mappings: 0° under-used (0.39, p = .005; true 0.47), 90° not (0.85, p = .88; true 0.92).
4. **The online task was losing data.** Calibration trials were never written to the file, and
   neither were `fullscreen_exits`, `bonus_quiz_attempts_evidence` and the Prolific study and
   session identifiers (collected into META but missing from `toCSV()`'s column list). Both
   fixed; calibration rows are pushed outside the scoring path so the bonus is untouched.
   With calibration rows in the fit, recovery of individual weights rose from r = .61 to .83.
5. **BIC prefers the simpler model** (weights only, ΔBIC ≈ 17 to the model with commitment)
   although the data were generated with a commitment term. The model for inference stays fixed
   in advance; say so in the preregistration.
6. **Per-person M-ratio from 30 Task-1 trials per mapping is too noisy** (SD > 1). Use the
   hierarchical estimator for the comparison between mappings, as in work package 1.

The effect built in here (about 50 % reduction) is more than twice the smallest effect the full
study can detect. Ten participants show that the analysis returns what was put in, not that an
effect of realistic size will be found.

## 10j. Learning drift, and the two-track evidence design (2026-10-02)

**Problem.** The primary test compares w_d between the 0° and 90° mappings, and w_d is a shift per
unit of evidence e. e was inferred from a psychometric function fitted once per person and mapping
and treated as constant over the session. If the observer's threshold or slope *changes* during the
session (learning, a drop once feedback stops) and does so differently at the two mappings, e is
wrong by a different amount at each and the error appears as a mode contrast. 90° is harder and has
more room to learn, so this is plausible. Simulated (`drift_robustness_wp3.py`, 150 observers per
cell, true w_d ratio 1.0): the old design returns a spurious contrast of **−0.12** when 90°
learns faster (threshold drift −0.2 vs −0.6 logit) and **−0.34** when that is combined with a rising
slope at 90°; against a smallest relevant effect of −0.22. Keeping the staircase running or freezing
it makes no difference (−0.25 vs −0.21 in an earlier 60-per-cell run): both feed the same static function.

Why it concerns e_high and not e_low: with the 1-up-2-down running throughout, first looks and low
second looks sit at ≈ 70.7 % by construction at any time, so e_low is drift-proof. e_high lies outside
the range the staircase visits and rests on the fitted slope, which is over-estimated on adaptive
data, flattened when pooled over a moving threshold, and itself able to change with learning.

**Design: stop inferring the high level, pin it and measure it.** Per mapping, two adaptive tracks run
through Task 1 and Task 2:

| | first look / low second look | high second look |
|---|---|---|
| controlled by | prop p (1-up-2-down, 70.7 %, unchanged) | offset δ (logit): p_high = σ(logit p + δ) |
| rule | unchanged | weighted up-down (Kaernbach 1991), up/down = .85/.15: +0.453 after an error, −0.08 after a correct, δ ∈ [0.3, 1.8], start 0.8 |
| updated by | standard trials only | strength trials only |

*Strength trials* are Task-1-style trials whose first look is already at p_high: move, choose, rate —
no second look (`trial_type = "strength"`, all others `"standard"`; `evidence_level = 0`). Three places:
- **strength calibration**, 20 per mapping right after the 1-up-2-down calibration, choice only and
  **without feedback** (`phase = calibration_strength`): δ's start for this person;
- **interleaved**, 10 among Task 1 and 25 among Task 2: keep δ tracking through the session and
  *measure* what the high strength supports under the conditions of the second looks.
They never move the staircase; standard trials never move δ. New columns: `trial_type`, `delta_live`
(the offset in force on that trial). `?d0=0&d1=0&d2=0` restores the old design. In Task 1 a strength
trial is indistinguishable from any other; in Task 2 participants are told that some trials have no
extra evidence and are rated right after the choice. Budget: 370–450 decision trials plus 120 second
looks, about 57 minutes (was ≈ 50); 980–1140 trajectory draws against a pool of 1200, so no recycling.

Two choices here were made against the first build and are worth keeping in mind:
- *Rated and scored, not choice-only.* A choice-only strength trial has no consequence for the
  participant. Anyone who notices "very clear trial → ends after the choice → does not count" can answer
  carelessly on clear-feeling trials, which lowers the measured strength and inflates w_d — at both
  mappings, so mostly in the level, but in the contrast if the clarity cue differs between mappings.
  With a rating the trial counts toward the bonus, there is nothing to recognise and nothing to skimp
  on. The ratings themselves are not used (a high-strength Task-1 cell, analysable later). Cost ≈ 2 s per trial.
- *No feedback in the strength calibration.* The track needs the outcomes, not the participant.
  Twenty mostly-"Right" messages immediately before Part A would lift the baseline confidence L0
  measured there; the feedback-free stretch now starts with this block instead of with Part A.

Why interleaved rather than a block alone: a block measures the strength once, before Task 2, while
the second looks it calibrates come 85 trials later. The 1-up-2-down carries a threshold shift into
p_high on its own (δ is a distance to the live value); a later change in the slope it does not, and
only trials during Task 2 can. Why not a second absolute staircase: it would have to rediscover the
threshold shift the 1-up-2-down already knows from many more trials; tracking the *distance* leaves
it only the slow part. The first build of this design gave the interleaved trials a second look and a
rating so that every Task-2 trial looked alike; dropped, since neither is used and they cost ≈ 100
trajectories and 5 minutes.

Step sizes were chosen by simulation (100 observers, starts of δ = 0.4, 0.8, 1.4): 0.08 / 0.453 reaches
86–87 % delivered accuracy from every start within the 35 strength trials; 0.05 / 0.28 jitters less but
converges more slowly from a poor start. The delivered accuracy is 86–87 % rather than 85 % because of the floor on δ and its
jitter (SD ≈ 0.3 logit): `test_two_track.py`.

**Analysis (`fit_wp3_model.fit_participant`, default `e_mode="anchored"`).** The model and the primary
test are unchanged; only the source of e changes, and strength trials stay out of the confidence model
and out of the exclusion criteria.
- The **level** of e comes from measured accuracy: e_low = logit(accuracy on standard first looks),
  e_high = logit(accuracy on the *interleaved* strength trials; the calibration block has feedback and
  precedes Task 1, so it only sets δ and widens the psychometric fit), the latter shrunk toward the group value per mapping
  (beta-binomial, method of moments, `acc_priors`): with ~35 trials the person-level binomial SE
  (≈ 6 points) exceeds the plausible spread, so this is close to complete pooling.
- **Trial-to-trial variation within a level** comes from the psychometric function (fitted on all
  decision trials, strength trials included, so the high range is observed, not extrapolated) and
  enters only as deviations around the measured level.
- Considered and rejected, same data (100 per cell, four scenarios): *one constant e per level* is
  unbiased under drift but throws away real trial-level variation (SD of the contrast 1.0–1.17 against
  0.65–0.83; r(w_d) .35–.49 against .58–.70): about half the power. *The psychometric e alone* (strength
  trials just widen its range) gains nothing against drift (combined scenario: −0.32).

**Result** (150 simulated observers per cell; bias = recovered − built-in contrast in log w_d, SE ≈ 0.06;
null = true contrast 0, effect = −0.49). Every cell uses the same participant pool and seeds, so a pool's
own sampling error (± 1 SE) is shared by all cells: differences between scenarios are more precise than
the absolute numbers, and a bias that is the same in every cell is that shared error, not a design effect
(a 200-observer pool drawn afresh gave +0.06 ± 0.05 for the two-track design and +0.01 ± 0.06 for the old
one with no drift at all).

| scenario | old, null | old, effect | two-track, null | two-track, effect |
|---|---|---|---|---|
| no change | +0.08 | −0.01 | +0.01 | −0.06 |
| learning, both mappings | −0.01 | −0.02 | +0.03 | −0.01 |
| drop once feedback stops | 0.00 | −0.01 | +0.02 | +0.01 |
| learning, 90° faster | **−0.12** | **−0.17** | +0.02 | −0.02 |
| slope rises, 90° only | −0.10 | **−0.18** | −0.08 | **−0.14** |
| 90° faster learning + slope | **−0.34** | **−0.39** | −0.02 | −0.06 |

Mapping-specific threshold drift is removed (−0.12 → +0.02; −0.34 → −0.02; −0.39 → −0.06). Power is
unchanged or better where the old design is unbiased (d_z −0.58 to −0.82 against −0.54 to −0.76 old; in
the three drift cells the old d_z of −0.73 to −1.03 is inflated by the bias; r(w_d) .63–.72 against .56–.71).
Delivered strength-trial accuracy 87–90 % at both mappings in every cell; the floor on incorrect
high-evidence trials 12–20 % against 22–39 %. With the first build (second look and rating on the
interleaved trials, δ starting at 0.8 for everyone) the picture was the same within sampling error.

**Validation run in the new design** (10 simulated observers, same seed and generating values as §10i;
`analysis/validation_two_track/`, report `WP3_validation_two_track.html`). Contrast put in −0.67, recovered
−0.58, 95 % CI [−1.11, −0.05], t(9) = −2.47, p = .035, d_z = −0.78; bootstrap null p = .023. The level
is recovered: w_d 0.43 / 0.77 against 0.47 / 0.92 put in, and the ideal-observer benchmark comes out at
w_d = 1.02 (was 0.83); against it 0° is under-used (p = .005), 90° not reliably (p = .13), as built in.
Strength-trial accuracy 86.8 % / 87.0 % (TOST within ±5 points p = .008). Individual weights r = .59.
Three builds of this design were run on these same ten observers (the random stream differs between
builds); they returned contrasts of −0.88, −0.77 and −0.58 and r(w_d) of .74, .86 and .59 around a truth
of −0.67. That spread is what ten observers give (SE of the contrast ≈ 0.3), not a difference between
builds; the 150-observer grid is the evidence on bias and precision. Two of the preregistered checks
fired here by chance with nothing built in (live-threshold drift 0° vs 90° p = .03, w_d first vs second
half of Task 2 p = .02): they are group-level diagnostics for N ≈ 127, not per-pilot pass/fail tests.
Keep testing the *level* against the benchmark rather than against 1.

**Not solved.**
- A *slope* change that differs between the mappings is only halved (−0.08 / −0.09, about 1.5 SE;
  a third of the smallest relevant effect, in the hypothesised direction).
- The floor on incorrect high-evidence trials fell from 22–39 % to 13–21 %, not to the ≈ 10 % hoped for.
- The simulation cannot test implicit feedback from either staircase (trials get easier after errors);
  the pilot's rating distributions are the check. Nor does it say whether a strong sample triggers
  categorical "obviously wrong" ratings instead of graded updating; the pilot must show that the
  rating distribution on incorrect high-evidence trials is graded, not a spike at 1.
- δ jitters by about ±0.3 logit; the average accuracy is what enters, so this costs a little precision, not bias.
- Drift *in w_d itself* over the session is a different question and not addressed.

**Preregistration statements.** The high evidence is held at ≈ 85 % by a weighted up-down track; the
primary measure is the paired contrast of log w_d from the model with weights and commitment, with e
anchored to measured strength-trial accuracy; checks reported (and now in the results report as
"Evidence levels as delivered"): strength-trial accuracy 0° vs 90° with a TOST equivalence margin of ±5
points, convergence of δ (first vs last ten strength trials), drift of the live threshold per mapping and
its difference between mappings, floor and ceiling rates, and w_d in the first vs second half of Task 2.

**Files.** `web/index.html` (`DeltaTrack`, `CFG.D0_N/D1_N/D2_N`, `trial_type`, `delta_live`), `simulate_wp3.py`
(`D0_N, D1_N, D2_N, DELTA_*`, `STEP, DRIFT, SLOPE_DRIFT`), `fit_wp3_model.py` (`strength_counts`, `acc_priors`,
`e_mode`), `wp3_paper_analysis.py` (`strength_checks`, `half_stability`, design-aware bootstrap),
`wp3_report.py`, `drift_robustness_wp3.py` (+ `drift_robustness_report.md/.csv`), `test_two_track.py`,
`make_validation_data.py --d0 20 --d1 10 --d2 25` (`analysis/validation_two_track/`). Old files (no `trial_type`)
still load and fit exactly as before. Not yet mirrored in the PsychoPy lab task.

## 10k. Web port parity with the lab and with WP1 online (2026-10-05)

Simon's own pilot of the online version: the cursor flashed up large when the mouse was shaken
(macOS "shake to locate"), could stray to a second monitor, and as the staircase made trials harder
the circles seemed to run along the edges of their boxes. Comparison with the WP1 online port
(`metasoa/CDT_online`) showed three things the WP3 port lacked and WP1 had built in deliberately:

1. **Pointer Lock** — relative mouse deltas, system cursor hidden by the OS, no screen edge, no
   second monitor, no shake-to-locate. Deltas are the OS-accelerated ones (as PsychoPy read them).
2. **Fixed-rate physics at the lab's rate.** The lab loop takes one physics step per `win.flip()`,
   so its rate is the display's. The WP3 port did the same in the browser, which made the stimulus
   depend on the participant's monitor. Now a `SimClock` turns wall time into fixed steps and spreads
   a frame's mouse movement over them. **The rate is 120 steps/s**, because that is what the WP1 lab
   actually ran: the WP1 kinematics files (three real participants, ~510 trials each) show 118.8–119.6
   frames per second, a 297-frame snippet playing in 2.5 s, median hand speed 10–17 px per step
   (1200–2000 px/s, 36–49 % of steps above the 20 px cap), median trial 2.3–2.9 s (response-terminated)
   — and the circles on a box wall **28–33 % of the time**. My first fix used 60 steps/s on the
   assumption the lab ran at 60 Hz (the WP1 online README says so; it is wrong): at 60 steps/s the
   same constants give slow motion — directions persist twice as long, the cap bites at 1200 instead
   of 2400 px/s — and the circles crawl along the walls; that is what Simon saw and the lab never had.
3. **The lab's trajectory handling.** The pool is exported with the lab's preprocessing (validity
   filter, speed normalisation to 7.5 px/step, universal set of 1240 + 40 ranked by quality) and
   trials use matched pairs with consistent smoothing (`find_matched_trajectory_pair`,
   `apply_consistent_smoothing`), not random raw snippets.

The box confinement itself is identical in lab, WP1 online and WP3 (hard clamp, ±200 × ±250 px),
and the lab data show wall contact a third of the time; it is part of the design. Pool and physics
of the WP3 port were checked against WP1's `cdt-core.js` on identical inputs (pool: max difference
3·10⁻⁶ over all 1280 snippets; positions: 10⁻¹³ over 180 steps). The WP1 **online** port is a
different matter: it steps once per rendered frame with a floor of one step, so on a 60 Hz screen it
runs at 60 steps/s (half the lab's speed, twice the wall contact) and on 120 Hz at 120; its
`display_fps` column tells which. It has never been used for data collection.

Also from the pilot: a device check at the start (`input_device`; trackpad users are asked to
return the study), one screen only, the bonus quoted in money with a worked example on the first
screens (`?bonus=` must be set for Prolific), timeout kept as a safety net (response is after the
motion with 20 s grace), 3 s motion window kept. New columns: `display_fps`, `low_move_ratio`
(per trial), `input_device`, `pointer_lock`, `pointer_lock_exits`. Checks: `test_engine.js`
(control signal; 360 steps per 3 s at 30/60/120/144 Hz; matched pairs more alike than random;
recycling), a browser run of the unpatched motion loop (360 steps in 3.00 s wall time,
`display_fps` ≈ display rate), and the refused-lock fallback. The PsychoPy task needs nothing: it
is the reference, provided it runs on a 120 Hz display as in the WP1 lab (on a 60 Hz monitor it
would give the slow-motion stimulus; check `frame`/`timestamp` in its kinematics file).

## 10l. Web build: what the data file must carry before Prolific (2026-10-07)

A review of the online build before the first Prolific pilot found that the trial CSV could not
support checks the project relies on, and that a few failure modes would cost whole sessions.
No change to the task, the schedule or the stimulus.

- **Replay invariant on web data.** `check_wp3_replay_invariant.py` (§10b) is the first check on
  new data, but the web build wrote no kinematics file and logged neither the side layout nor the
  applied ±90° sign, so the check could not run. Each trial now logs `left_shape`,
  `applied_angle_bias` and `evidence_sum` (summed momentary evidence of the 3 s look); Task-2 rows add
  the same for the second look (`post_*`). The script reads either file.
- **Reproducibility and context:** `seed`, `build`, `started_at`, `duration_min`, screen/window
  size, `dpr`, `user_agent`, `block_idx`, `trial_idx`. `user_agent` contains commas, so the CSV
  writer now quotes fields.
- **Saving:** an interim upload after each block (`*.csv.partial`), the local download only as a
  fallback, and on Prolific a retry screen instead of a redirect when the final upload fails.
  A Prolific URL without a DataPipe id or without `bonus` refuses to start.
- **Pause bug:** an Esc during the response prompt did not stop the 20 s grace clock (the trial
  could time out right after resuming, and `rt_choice` included the pause), and keys pressed on the
  pause screen counted as answers. The response clock now pauses with the motion clock, and choice
  and rating keys are ignored while paused.

## 10m. Consent, debrief, instruction checks and online exclusions (2026-10-07)

Research on Prolific's rules and online best practice:
`/mnt/project-files/wp3-setup/online-standards-consent-exclusions.md` (project files). Prolific allows a
rejection only after two failed attention checks of an allowed type (instructional manipulation checks or
nonsensical items), never for performance and never for failed comprehension checks. Hence two levels:
few Prolific-compliant checks decide payment; stricter preregistered criteria decide the analysis only.

- **Attention checks cost no trials** (Simon, 2026-10-07: trials are too scarce for catch trials). Three
  instruction screens (Part A and Part B of block 1, start of block 2) ask for K instead of SPACE.
  Logged `imc_1..3`, `imc_failed`.
- **Consent** first (Y/N, decline ends the session without saving), **closing self-report** (mouse whole
  time, focus 1–5, interruptions, technical problems, optional comment; stated not to affect payment) and a
  **debrief** at the end; on Prolific the participant leaves with a keypress instead of a 4 s redirect.
  The consent text is Simon's WP1 LMU consent form ("Who's in control?"), retitled for WP3 and adapted for
  online use: keypress instead of name and signature, the participant information shown on screen, questions
  by e-mail or Prolific message, the two YES/NO items asked separately and re-contact via Prolific.
- **No CAPTCHA:** without a server to verify the token it is bypassable, it adds a third party to the
  consent, and the task itself filters bots (chance accuracy fails the 0.60–0.85 band).
- **Analysis:** `exclusion_flags` adds, where the columns exist, failed instruction check, self-reported
  non-mouse use, no pointer lock, median `display_fps` < 50 and median `low_move_ratio` > 0.30. The last two
  thresholds are provisional, to be fixed on pilot data and preregistered. Still to preregister: trial-level
  exclusions (hand still, dropped frames) and a check that their rate does not differ between 0° and 90°.

## 10n. One movement modality: mouse only (2026-10-08)

Simon (2026-10-08): the sense-of-agency literature argues for analysing a single movement modality,
because hand movements and their kinematics may differ with the device moved (mouse vs. trackpad).
This supersedes the idea of allowing trackpads and modelling device as a covariate.

- **Default: mouse.** It is the device the lab task and the WP1 data used, the one most agency studies
  with cursor control use, and the one Prolific participants most often have on a desktop. Trackpad data
  are not analysed (not even as a sensitivity analysis: a trackpad subsample would be small and self-selected).
- **Recording.** Device question at the start (trackpad users are asked to plug in a mouse or return the
  study; `input_device_initial` keeps the first answer, `input_device` the device used), closing self-report
  `selfreport_device` (mouse the whole time?) stated not to affect payment. Prolific screening: desktop only.
- **No device detection from the data.** Browsers report a trackpad as a mouse (`pointerType = "mouse"`),
  and kinematic signatures (`low_move_ratio`, delta granularity) are not validated for this. `low_move_ratio`
  stays an analysis criterion for too little movement, not a device test. Checked descriptively in the pilot.
- **Analysis.** `exclusion_flags` → `not_mouse_only`: excluded when the start answer (final `input_device`)
  or the self-report is not mouse.

**Preregistration statement.** Only data from participants who used a computer mouse throughout are
analysed. Participants are excluded if they report at the start or at the end of the session (with the
assurance that the answer does not affect payment) that they used a trackpad or another device for any part
of the task. Movement modality is held constant rather than modelled, because control detection relies on the
kinematics of the moving hand, which differ between devices.

## 11. Considered and rejected (2026-09-02): instructed control expectations

To reconnect WP3 with the proposal's "expectations of control" moderator, we
considered block-wise *instructed* expectations ("in this block your control is
stronger/weaker" while prop stays medium), à la Blackburne, Frith & Yon (2025).
Rejected: a one-shot instruction against ~90 trials of contradicting experience
is a weak prior with an extinction problem, and a null would be uninterpretable
(no way to tell "expectation has no effect" from "expectation never took hold")
without adding manipulation checks and trial-position modelling. The proposal's
expectation hypothesis remains untested in WP3 by design; revisit only with a
properly learned (cued) expectation, i.e. WP1 machinery.

## 12. Follow-up study (sketched 2026-09-02): active vs. passive post-decision evidence

WP3 manipulates the **prior side** of updating (how the belief was formed:
model-based 0° vs. evidence-based 90°). The natural sequel manipulates the
**likelihood side**: how the *evidence* is generated. In the current design the
post-decision sample is **actively produced** — the participant moves the mouse
again during the replay. (Note this is already a difference from Rollwage, whose
post-decision evidence was passively viewed dots; we don't currently exploit it.)

**Design:** within-subject, evidence sample either *active* (as now) or
*passive* — a playback of the participant's own recorded cursor trajectory from
that trial, so the visual stimulus is matched and only agency over the evidence
differs. Requires cursor recording + a playback path in `run_trial`.

**Why it matters:** it localises the resistance WP3 measures. In the predictive
mode, self-generated input is subject to **sensory attenuation** (comparator
model). Two decidable outcomes:
- Resistance sits in the **evidence channel**: disconfirmation arriving during
  one's own movement is attenuated as self-generated → the *passive* version of
  the same disconfirmation should penetrate better (larger confidence drop).
- Resistance sits on the **belief side** (commitment / choice bias): active vs.
  passive makes no difference.

**Status:** deliberately NOT merged into WP3 — it shifts the research question
from belief revision to evidence weighting, and a 2×2×2 would halve the scarce
incorrect-trial cells. Run after WP3 establishes the base effect; the active
condition then already exists as baseline.

---

## References
- Rollwage, Dolan & Fleming (2018). *Metacognitive Failure as a Feature of Those
  Holding Radical Beliefs.* Current Biology 28, 4014–4021. (PDF in this folder.)
- Wen, Charles & Haggard (2023). *Metacognition and sense of agency.* Cognition.
- Maniscalco & Lau (2012); Fleming (2017) — meta-d′.
- Dissertation proposal: `Antrag Studienstiftung - 30.12.2024.pdf` (WP1–WP3, §WP3 p.16).
