# Hierarchical drift-diffusion analysis of the CDT — analysis plan

Status: draft, 2026-09-17. Data: 14 included participants (P13 excluded by the learning check;
P16 rebuilt from kinematics). Pipeline lives in `hddm/` (`prep.py` → `fit_hssm.py` → `report.py`).

## 1. Questions the model has to answer

| Hypothesis (slide) | DDM parameter | Prediction on medium trials | Contrast from the posterior |
|---|---|---|---|
| H1 Drift-rate modulation at 0° | drift rate *v* | high-control cue raises *v* at 0° more than at 90° | *v*: cue effect at 0° > 0; cue × angle < 0 |
| H2 Boundary/urgency at 90° | boundary *a* (urgency: collapse angle θ, stage 2) | high-control cue lowers *a* (or raises urgency) at 90° more than at 0° | *a*: cue effect at 90° < 0; cue × angle < 0 |
| Dissociation (overall RQ) | *v* vs *a* | cue acts on *v* at 0° and on *a* at 90° | both of the above; model comparison full vs drift-only vs boundary-only |
| H3 Asymmetric confidence | not a first-passage DDM parameter | — | tested with the P3 confidence contrast (already run; confounded by unequal objective control steps); a post-decision confidence model (2DSD / dynamic confidence) is a later extension |

## 2. Why a hierarchical Bayesian DDM, and which implementation

- Hierarchical estimation pools ~50 trials per participant × cell through group-level distributions; this is the standard remedy when per-cell trial counts are far below what single-subject fits need (≥ ~100–200 per cell; Lerche, Voss & Nagler 2017; Voss, Nagler & Lerche 2013). Precedents: Vandekerckhove, Tuerlinckx & Lee (2011); HDDM (Wiecki, Sofer & Frank 2013).
- Implementation: **HSSM** (Frank lab, successor of HDDM; PyMC/NUTS, analytic Wiener likelihood for the standard DDM, likelihood-approximation networks for collapsing-bound models — Fengler et al. 2021). Chosen over `brms::wiener` because (a) rstan cannot compile on this machine (StanHeaders/rstan version mismatch) and (b) HSSM's `angle` model gives a direct test of the *urgency* reading of H2, which the plain Wiener model cannot.
- Regression-on-parameters (drift, boundary, non-decision time as linear functions of cue, angle and their interaction with participant random slopes) follows the HDDMRegressor / brms-wiener convention used e.g. in the Desender lab's confidence work (Desender et al. 2019 eLife).

## 3. Data decisions (pre-specified)

1. **Trials.** Confirmatory model on *test-phase medium trials* only: the staircase equalises objective control and accuracy (≈ 71 %) across cues, so any cue effect on *v* or *a* is an expectation effect, not a stimulus effect. Sensitivity model on all test trials with difficulty (hard −1 / medium 0 / easy +1) as an additive drift covariate. Easy/hard trials are cue-congruent by design, so they cannot be used to separate cue from difficulty and are not in the confirmatory model.
2. **Timeouts** (no response within 5 s; 2.5–6.4 % per cell, higher under the low-control cue). These are right-censored observations. They are dropped from the likelihood and their rate is reported per cell; a cue-dependent timeout rate is itself informative and is listed with the results. (Neither HSSM nor brms-wiener handles censoring natively.)
3. **Fast guesses.** Minimum RT 0.59 s, nothing below 0.25 s → no lower cut-off is needed. A 2 % uniform outlier mixture (`p_outlier`) protects the likelihood against contaminants (Ratcliff & Tuerlinckx 2002).
4. **Response coding.** Accuracy coding (upper bound = correct). The cue predicts nothing about left/right, so a starting-point bias is meaningless; *z* is fixed at 0.5. Bias models are not fitted.
5. **RT definition.** RT from motion onset; in this task the 5-s motion window *is* the accumulation window, the response ends it. *t0* absorbs sensory-motor delay and the initial interval before the evidence becomes diagnostic. Known limitation: evidence in the CDT is not stationary within a trial (it grows as the participant moves); the DDM's constant-drift assumption is an approximation. Extension (stage 3): trial-level evidence (`mean_evidence_preRT`) as a drift covariate.
6. **Across-trial variability parameters** (sv, sz, st) are not estimated in the confirmatory model — they are poorly recoverable with few trials (Boehm et al. 2018).
7. **Exclusions** are those of the behavioural analysis (P13; P004). Adding a participant = adding their files to the data folder; `prep.py` handles a missing behavioural CSV by rebuilding from kinematics.

## 4. Model specification

Sum coding: cue high = +0.5 / low = −0.5; angle 90° = +0.5 / 0° = −0.5.

```
v ~ 1 + cue * angle + (1 + cue * angle | participant)
a ~ 1 + cue * angle + (1 + cue * angle | participant)
t ~ 1 + angle       + (1 + angle       | participant)      # rotation may change sensorimotor delay
z = 0.5
```

Priors (weakly informative, natural scale): *v* intercept N(1, 1), *a* intercept N(1.5, 0.5), *t* intercept N(0.6, 0.3); all fixed slopes N(0, 0.5) (v) / N(0, 0.3) (a) / N(0, 0.2) (t); random-effect SDs Half-Normal(0.5 / 0.3 / 0.2). Prior-predictive check before the fit.

Model set for comparison (secondary, LOO-CV; Vehtari, Gelman & Gabry 2017):
`null` (no cue/angle effects) · `drift` (cue × angle on *v* only) · `bound` (on *a* only) · `full` (both).
Primary inference is on the posterior contrasts of the `full` model — model selection is not required to answer H1/H2, and LOO differences with N = 14 will be small.

## 5. Sampling and checks

- NUTS (numpyro), 4 chains × 1000 warm-up + 1000 draws, target_accept 0.9.
- Convergence: R̂ < 1.01, bulk-ESS > 400, zero divergences. Otherwise: reparameterise / tighten priors / more warm-up, and say so.
- Posterior predictive checks: RT quantiles (0.1/0.3/0.5/0.7/0.9) and accuracy per participant × cell from 200 posterior draws vs. data (quantile-probability plots; Ratcliff & McKoon 2008).
- Parameter recovery: simulate one synthetic data set per posterior-mean parameter set with the real design (participants, trials per cell), refit, check that cue-effect contrasts recover. Required before the contrasts are reported as evidence (Wilson & Collins 2019).
- Report per contrast: posterior mean, 95 % HDI, P(direction). No p-values.

## 6. What the raw data already suggest (to calibrate expectations)

On medium trials the cue changed neither median RT (0°: 3.00 vs 3.05 s; 90°: 3.00 vs 2.92 s) nor accuracy appreciably (+0.02 / +0.03). A drift effect implies faster *and* more accurate responses; a lower boundary implies faster *and* less accurate ones. Neither pattern is visible at the group level, so the DDM will most likely return cue effects on *v* and *a* near zero with wide HDIs. That is a legitimate outcome: it would mean expectation moved the *ratings* (agency, confidence) without moving the *decision* variables — the dissociation the Zwischenbericht calls the core H1. Do not read "no drift effect" as a failed analysis.

## 7. Stages

1. **Now:** confirmatory `full` model on medium trials, N = 14; plus `null/drift/bound` for LOO. Report.
2. **Urgency:** HSSM `angle` model (linearly collapsing bounds), θ ~ cue × angle, medium trials. Tests the "increasing urgency" wording of H2 directly.
3. **Evidence-informed drift:** *v* ~ cue × angle + trial evidence, all test trials.
4. **Confidence:** two-stage / post-decision model if H3 is to be tested within the accumulation framework.

## 8. Re-running with new data

```
python prep.py <data_dir> hddm/out          # rebuilds the trial table; hash changes if data changed
python fit_hssm.py hddm/out hddm/fits --models full,null,drift,bound
python report.py hddm/fits                  # tables + figures for the newest hash
```
Fits are cached by data hash and model; unchanged data never refit. A hierarchical model has to be refitted when participants are added (no incremental updating; priors stay the pre-registered ones, they are not replaced by the previous posterior).

## References (verify page numbers before citing)

Boehm et al. (2018) *J Math Psych* — variability parameters. Desender, Boldt, Verguts & Donner (2019) *eLife* — confidence and SAT. Fengler, Govindarajan, Chen & Frank (2021) *eLife* — LANs. Lerche, Voss & Nagler (2017) *Behav Res Methods* — trial numbers. Ratcliff & McKoon (2008) *Neural Comput* — DDM review. Ratcliff & Tuerlinckx (2002) *Psychon Bull Rev* — contaminants. Vandekerckhove, Tuerlinckx & Lee (2011) *Psychol Methods* — hierarchical DDM. Vehtari, Gelman & Gabry (2017) *Stat Comput* — LOO. Voss, Nagler & Lerche (2013) *Exp Psychol* — practical intro. Wiecki, Sofer & Frank (2013) *Front Neuroinform* — HDDM. Wilson & Collins (2019) *eLife* — model-fitting good practice.
