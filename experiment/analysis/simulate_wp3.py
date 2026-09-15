"""Simulate WP3 sessions in the EXACT file format the task writes, so the analysis
pipeline can be built and validated before any human data exist.

Generative observer model (per participant x angle):
  * psychometric function  P(correct | prop) = 0.5 + 0.5 * sigmoid(a * (logit(prop) - t))
    with threshold t (prop at ~70.7%) and slope a; a 1-up-2-down staircase runs on it
    (calibration, then — as in the task — through Task 1 and Task 2 from decisions only).
  * evidence strength of a sample at prop p:  e = logit(P(correct | p))   (log-LR of a
    sample that always points to the truth), so level 2 = level 1 + ~1.2 logit.
  * confidence in log-odds:  L0 = pre + m * (+1 correct / -1 incorrect)   [m: meta-sensitivity]
        Task 1:  L = L0
        Task 2:  L = L0 + b + w_c * e   (correct)      L = L0 + b - w_d * e   (incorrect)
    b = choice-bias bonus (0 unless --choice-bias). Rating = round(1 + 8 * sigmoid(L) + noise).
  * confirmation bias = w_d < w_c. Default truth: w_d(0deg) << w_d(90deg); PDI (conviction)
    correlates negatively with w_d(0deg).

Writes one CSV per participant (PsychoPy layout, incl. calibration rows and the
wp3_summary row) or the web layout (--format web), plus:
  pdi.csv                participant,pdi           (external questionnaire stand-in)
  ground_truth.csv       the generating parameters  (for parameter recovery)

Usage:
  python simulate_wp3.py OUTDIR [--n 150] [--seed 1] [--format psychopy|web]
                                [--choice-bias 0.0] [--wd0 0.45 --wd90 0.85]
                                [--noise 1.2] [--timeout 0.02] [--track 1]
"""
import argparse, pathlib
import numpy as np
import pandas as pd

BOOST = 1.2
PROP_MIN, PROP_MAX = 0.02, 0.90
T1_N, T2_N = 30, 60
CAL_MIN, CAL_MAX, CAL_REV = 40, 80, 12

sig = lambda x: 1.0 / (1.0 + np.exp(-x))
logit = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
clamp = lambda p: float(np.clip(p, PROP_MIN, PROP_MAX))


class Staircase:
    """1-up-2-down, mirrors staircase.py: big steps until 3 reversals, then small."""
    def __init__(self, start=0.85, big=0.10, small=0.05):
        self.p, self.big, self.small = start, big, small
        self.ncorr, self.lastdir, self.rev = 0, 0, []

    @property
    def step(self):
        return self.small if len(self.rev) >= 3 else self.big

    def next(self):
        return self.p

    def update(self, correct):
        d = 0
        if correct:
            self.ncorr += 1
            if self.ncorr >= 2:
                self.p = max(self.p - self.step, PROP_MIN); d = -1; self.ncorr = 0
        else:
            self.p = min(self.p + self.step, PROP_MAX); d = +1; self.ncorr = 0
        if d and self.lastdir and d != self.lastdir:
            self.rev.append(self.p)
        if d:
            self.lastdir = d

    def threshold(self):
        return self.p if not self.rev else float(np.mean(self.rev[-8:]))


def draw_participants(n, rng, wd0, wd90, choice_bias):
    """Participant-level parameters. PDI conviction is generated jointly with w_d(0deg)."""
    z_pdi = rng.normal(size=n)
    pdi = np.clip(12 + 8.5 * z_pdi, 0, 40)
    r_pdi = -0.35                                          # true PDI -> w_d(0deg) correlation
    z_wd0 = r_pdi * z_pdi + np.sqrt(1 - r_pdi ** 2) * rng.normal(size=n)
    P = pd.DataFrame(dict(
        participant=[f"{1000 + i}" for i in range(n)],
        pdi=np.round(pdi).astype(int),
        # psychometric: threshold prop at 70.7% and slope, per angle (90 is harder)
        t0=logit(np.clip(rng.normal(0.45, 0.10, n), 0.15, 0.80)),
        t90=logit(np.clip(rng.normal(0.58, 0.12, n), 0.20, 0.85)),
        slope=np.clip(rng.normal(2.2, 0.5, n), 1.0, 4.0),
        # confidence baseline (log-odds) and meta-sensitivity
        pre0=rng.normal(1.45, 0.40, n), pre90=rng.normal(0.95, 0.40, n),
        meta=np.clip(rng.normal(0.55, 0.25, n), 0.0, 1.5),
        # updating weights
        wc0=np.clip(rng.normal(0.95, 0.20, n), 0.1, 2.0),
        wc90=np.clip(rng.normal(0.92, 0.20, n), 0.1, 2.0),
        wd0=np.clip(wd0 + 0.25 * z_wd0, 0.02, 2.0),
        wd90=np.clip(rng.normal(wd90, 0.25, n), 0.02, 2.0),
        b0=choice_bias, b90=choice_bias,
        noise=np.clip(rng.normal(1.2, 0.25, n), 0.6, 2.0),
        order=[[0, 90] if i % 2 == 0 else [90, 0] for i in range(n)],
    ))
    return P


def p_correct(prop, t, slope):
    return 0.5 + 0.5 * sig(slope * (logit(prop) - t))


def rating_from_logodds(L, noise, rng):
    r = 1 + 8 * sig(L) + rng.normal(0, noise)
    return int(np.clip(np.round(r), 1, 9))


def simulate_participant(p, rng, fmt, timeout_rate, track):
    rows, trial_no, scores = [], 0, []
    base = dict(participant=p.participant, session=1, age="", gender="", handedness="",
                learning_order=str(p.order), counterbalance_index=int(p.participant) % 8)
    for block_i, ang in enumerate(p.order, 1):
        t, sl = (p.t0, p.slope) if ang == 0 else (p.t90, p.slope)
        pre, wc, wd, b = (p.pre0, p.wc0, p.wd0, p.b0) if ang == 0 else (p.pre90, p.wc90, p.wd90, p.b90)
        sc = Staircase()

        # ── calibration (with feedback; logged like the task does) ──────────────
        n = 0
        while n < CAL_MAX and not (len(sc.rev) >= CAL_REV and n >= CAL_MIN):
            prop = clamp(sc.next()); n += 1
            correct = rng.random() < p_correct(prop, t, sl)
            true = rng.choice(["square", "dot"]); resp = true if correct else ("dot" if true == "square" else "square")
            sc.update(correct)
            rows.append(dict(base, phase="calibration_interleaved", trial_num=n, angle_bias=float(ang),
                             prop_used=prop, staircase_prop=prop, staircase_reversals=len(sc.rev),
                             trial_index_within_staircase=n, accuracy=float(correct), is_timeout=False,
                             rt_choice=float(rng.uniform(0.8, 2.5)), true_shape=true, resp_shape=resp))
        med0 = clamp(sc.threshold())

        def decision_trial(task, lev):
            nonlocal trial_no
            trial_no += 1
            prop = clamp(sc.next()) if track else med0
            p_high = clamp(sig(logit(prop) + BOOST))
            clipped = p_high >= 0.899
            timeout = rng.random() < timeout_rate
            true = rng.choice(["square", "dot"])
            if timeout:
                rows.append(dict(base, phase=f"wp3_task{task}", trial_num=trial_no, wp3_task=task,
                                 evidence_level=lev, angle_bias=float(ang), prop_used=prop, prop_post=np.nan,
                                 med_live=clamp(sc.threshold()), prop_high_clipped=clipped, accuracy=np.nan,
                                 is_timeout=True, rt_choice=np.nan, true_shape=true, resp_shape="timeout",
                                 wp3_confidence=np.nan, wp3_prob=np.nan, wp3_conf_rt=np.nan, wp3_score=0.0))
                scores.append(0.0); return
            correct = rng.random() < p_correct(prop, t, sl)
            resp = true if correct else ("dot" if true == "square" else "square")
            if track:
                sc.update(correct)
            L0 = pre + p.meta * (1 if correct else -1)
            post = np.nan
            if lev == 0:
                L = L0
            else:
                post = prop if lev == 1 else p_high
                e = logit(p_correct(post, t, sl))          # log-LR of a truth-pointing sample
                L = L0 + b + (wc * e if correct else -wd * e)
            conf = rating_from_logodds(L, p.noise, rng)
            pc = (conf - 1) / 8
            score = 1 - (1 - pc) ** 2 if correct else 1 - pc ** 2
            scores.append(score)
            rows.append(dict(base, phase=f"wp3_task{task}", trial_num=trial_no, wp3_task=task,
                             evidence_level=lev, angle_bias=float(ang), prop_used=prop, prop_post=post,
                             med_live=clamp(sc.threshold()), prop_high_clipped=clipped, accuracy=float(correct),
                             is_timeout=False, rt_choice=float(rng.lognormal(0.2, 0.35)), true_shape=true,
                             resp_shape=resp, wp3_confidence=float(conf), wp3_prob=pc * 100,
                             wp3_conf_rt=float(rng.lognormal(0.5, 0.4)), wp3_score=score))

        for _ in range(T1_N):
            decision_trial(1, 0)
        levels = [1] * (T2_N // 2) + [2] * (T2_N - T2_N // 2); rng.shuffle(levels)
        for lev in levels:
            decision_trial(2, lev)

    mean_score = float(np.mean(scores))
    rows.append(dict(base, phase="wp3_summary", wp3_mean_score=round(mean_score, 4),
                     wp3_bonus=round(mean_score, 2), bonus_quiz_attempts=int(rng.integers(1, 3)),
                     bonus_motivation_1to5=int(rng.integers(2, 6))))
    df = pd.DataFrame(rows)
    if fmt == "web":
        # the web port logs Task 1/2 only, with its own column set — no calibration rows
        cols = ["participant", "session", "phase", "wp3_task", "evidence_level", "angle_bias",
                "prop_used", "prop_post", "accuracy", "true_shape", "resp_shape", "rt_choice",
                "is_timeout", "wp3_confidence", "wp3_prob", "wp3_conf_rt", "wp3_score",
                "prop_high_clipped", "med_live", "bonus_quiz_attempts", "bonus_motivation_1to5",
                "wp3_mean_score", "wp3_bonus"]
        w = df[df.phase.str.startswith("wp3_task")].copy()
        for c in ("bonus_quiz_attempts", "bonus_motivation_1to5", "wp3_mean_score", "wp3_bonus"):
            w[c] = df[c].dropna().iloc[-1]
        return w.reindex(columns=cols)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--format", choices=["psychopy", "web"], default="psychopy")
    ap.add_argument("--choice-bias", type=float, default=0.0, help="fixed log-odds bonus for the chosen option")
    ap.add_argument("--wd0", type=float, default=0.45, help="mean disconfirmatory weight, 0 deg")
    ap.add_argument("--wd90", type=float, default=0.85, help="mean disconfirmatory weight, 90 deg")
    ap.add_argument("--timeout", type=float, default=0.02)
    ap.add_argument("--track", type=int, default=1, help="1 = staircase runs through both tasks")
    ap.add_argument("--boost", type=float, default=BOOST, help="logit(prop) boost for high evidence (task default 1.2)")
    a = ap.parse_args()
    globals()["BOOST"] = a.boost
    rng = np.random.default_rng(a.seed)
    out = pathlib.Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    P = draw_participants(a.n, rng, a.wd0, a.wd90, a.choice_bias)
    for _, p in P.iterrows():
        df = simulate_participant(p, rng, a.format, a.timeout, a.track)
        name = (f"CDT_v2_blockwise_fast_response_{p.participant}.csv" if a.format == "psychopy"
                else f"CDT_wp3_{p.participant}.csv")
        df.to_csv(out / name, index=False)
    P[["participant", "pdi"]].to_csv(out / "pdi.csv", index=False)
    P.drop(columns=["order"]).to_csv(out / "ground_truth.csv", index=False)
    print(f"[sim] {a.n} participants -> {out}  (format={a.format}, wd0={a.wd0}, wd90={a.wd90}, "
          f"choice_bias={a.choice_bias}, track={a.track})")


if __name__ == "__main__":
    main()
