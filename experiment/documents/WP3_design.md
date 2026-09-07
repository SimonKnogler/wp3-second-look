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
