#!/usr/bin/env python3
"""Does the mapping contrast survive learning?  Old design vs two-track design (design doc §10j).

The primary test compares w_d between the 0 deg and 90 deg mappings. w_d is a shift per unit of
evidence e, so any error in e that differs between the mappings becomes a spurious contrast.
Here the observer's threshold and slope CHANGE during the session (learning, a drop once feedback
stops, one mapping learning faster than the other) and we ask what each design recovers.

  old        fixed high offset (+1.2 logit); e inferred from a psychometric function fitted once
  two-track  high offset set per person by a strength-calibration block and tracked to ~85 % by interleaved
             choice-only strength trials; the level of e is their measured accuracy (empirical-Bayes shrunk
             toward the group), trial-level variation from the psychometric fit

Each scenario is run with a built-in effect (true w_d ratio 0.6) and with none (ratio 1.0), so the
table shows recovery bias, power and the false-positive rate.

  python drift_robustness_wp3.py [--n 100] [--procs 8] [--scen "no change;learning, 90 deg faster"] [--out drift_robustness_report.md]
"""
import argparse, pathlib, sys, warnings
from multiprocessing import Pool
import numpy as np
import pandas as pd
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import simulate_wp3 as S      # noqa: E402
import fit_wp3_model as F     # noqa: E402
import power_wp3 as PW        # noqa: E402

# threshold step after calibration / threshold drift over the session (logit prop) / relative slope drift: (0 deg, 90 deg)
SCEN = {
    "no change":                     dict(step=(0.0, 0.0), drift=(0.0, 0.0),   slope=(0.0, 0.0)),
    "learning, both mappings":       dict(step=(0.0, 0.0), drift=(-0.4, -0.4), slope=(0.0, 0.0)),
    "drop once feedback stops":      dict(step=(0.5, 0.5), drift=(0.0, 0.0),   slope=(0.0, 0.0)),
    "learning, 90 deg faster":       dict(step=(0.0, 0.0), drift=(-0.2, -0.6), slope=(0.0, 0.0)),
    "slope rises, 90 deg only":      dict(step=(0.0, 0.0), drift=(0.0, 0.0),   slope=(0.0, 0.6)),
    "faster learning + slope, 90":   dict(step=(0.0, 0.0), drift=(-0.2, -0.6), slope=(0.0, 0.6)),
}
DESIGNS = {"old": (0, 0, 0), "two-track": (20, 10, 25)}      # strength trials per mapping: calibration block, Task 1, Task 2
TRUTH = {"effect": float(np.log(0.6)), "null": 0.0}


def _simulate(a):
    key, pdict, seed = a
    truth, scen, design = key
    sc = SCEN[scen]
    S.T1_N, S.T2_N, S.BOOST = 30, 60, 1.2
    S.D0_N, S.D1_N, S.D2_N = DESIGNS[design]
    S.STEP, S.DRIFT = dict(zip((0, 90), sc["step"])), dict(zip((0, 90), sc["drift"]))
    S.SLOPE_DRIFT = dict(zip((0, 90), sc["slope"]))
    df = S.simulate_participant(pd.Series(pdict), np.random.default_rng(seed), "web", 0.005, 1)
    df["phase"] = df["phase"].astype(str); df["participant"] = df["participant"].astype(str)
    df["is_timeout"] = F._bool(df["is_timeout"]); df["prop_high_clipped"] = F._bool(df["prop_high_clipped"])
    diag = {}
    for ang in (0, 90):
        d = df[(df.angle_bias == ang) & df.phase.str.startswith("wp3_task") & ~df.is_timeout]
        std, stn = d[d.trial_type == "standard"], d[d.trial_type == "strength"]
        hi_i = std[(std.evidence_level == 2) & (std.accuracy == 0)].wp3_confidence
        diag[ang] = dict(acc_std=std.accuracy.mean(), acc_str=stn.accuracy.mean() if len(stn) else np.nan,
                         floor=(hi_i == 1).mean() if len(hi_i) else np.nan,
                         threshold_drift=float(F.logit(std.med_live.values[-10:]).mean() - F.logit(std.med_live.values[:10]).mean()))
    return key, pdict, df, diag


def _fit(a):
    key, pdict, df, diag, prior = a
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rows = F.fit_participant(df, prior)
    out = []
    for r in rows:
        if r.get("fail", "x") != "":
            continue
        ang = int(r["angle"])
        out.append(dict(truth=key[0], scen=key[1], design=key[2], pid=pdict["participant"], angle=ang,
                        wd_fit=float(np.clip(r["w_d_both"], 0.05, 3.0)), wd_true=pdict[f"wd{ang}"],
                        e_high_fit=r["e_high"], **diag[ang]))
    return out


def run(n, procs, scens):
    jobs = []
    for truth, mu in TRUTH.items():
        P = PW.draw_pool(dict(pool=n, mu_delta=mu, sd_delta=0.30, b_mean=0.40, b_sd=0.30, b_shift0=0.0,
                              noise=1.2, t1=30, t2=60, boost=1.2), 4242)
        for scen in scens:
            for design in DESIGNS:
                jobs += [((truth, scen, design), P.iloc[i].to_dict(), 700000 + i) for i in range(n)]
    with Pool(procs) as pool:
        sims = pool.map(_simulate, jobs, chunksize=4)
        # empirical-Bayes prior per cell: needs everyone's strength accuracy, so a second pass
        cells = {}
        for key, _, df, _ in sims:
            cells.setdefault(key, []).append(df)
        prior = {k: F.acc_priors(F.strength_counts(pd.concat(v))) for k, v in cells.items()}
        res = pool.map(_fit, [(k, p, df, dg, prior[k]) for k, p, df, dg in sims], chunksize=4)
    return pd.DataFrame([r for rr in res for r in rr])


def summarise(d):
    rows = []
    for (truth, scen, design), s in d.groupby(["truth", "scen", "design"], sort=False):
        w = s.pivot_table(index="pid", columns="angle", values="wd_fit").dropna()
        t = s.pivot_table(index="pid", columns="angle", values="wd_true").dropna()
        fit = np.log(w[0]) - np.log(w[90]); true = np.log(t[0]) - np.log(t[90])
        bias = fit - true
        a = s.groupby("angle")
        rows.append(dict(truth=truth, scenario=scen, design=design, n=len(w),
                         contrast_true=true.mean(), contrast_fit=fit.mean(), bias=bias.mean(),
                         bias_se=bias.std(ddof=1) / np.sqrt(len(bias)), dz=fit.mean() / fit.std(ddof=1),
                         r_wd=float(np.corrcoef(np.log(s.wd_true), np.log(s.wd_fit))[0, 1]),
                         p=stats.ttest_1samp(fit, 0).pvalue,
                         acc_std=s.acc_std.mean(), acc_str=s.acc_str.mean(),
                         acc_str_0=a.acc_str.mean().get(0, np.nan), acc_str_90=a.acc_str.mean().get(90, np.nan),
                         floor=s.floor.mean(), thr_drift_0=a.threshold_drift.mean().get(0, np.nan),
                         thr_drift_90=a.threshold_drift.mean().get(90, np.nan)))
    return pd.DataFrame(rows)


def report(R, n):
    f = lambda x, k=2: f"{x:+.{k}f}"
    L = [f"# Drift robustness: old design vs two-track design\n",
         f"{n} simulated participants per cell. Contrast = log w_d(0°) − log w_d(90°); true value −0.51 in the "
         "effect cells (ratio 0.6), 0 in the null cells. Bias = recovered − built-in, per participant, ± SE. "
         "Every cell uses the SAME participant pool and per-participant seeds, so the pool's own sampling error "
         "(about ± 1 SE) is shared by all cells: differences between scenarios or designs are more precise than "
         "any cell's absolute bias, and a bias that is the same in every cell is that shared error, not a design effect. "
         "p is the paired t-test of the recovered contrast against 0 (one test per cell, so in the null cells it "
         "should be unremarkable and in the effect cells small). floor = share of incorrect high-evidence trials "
         "rated 1. Threshold drift = change of the live staircase estimate, last vs first 10 trials (logit prop).\n",
         "| truth | scenario | design | contrast fit | bias ± SE | d_z | p | r(w_d) | acc standard | acc strength (0° / 90°) | floor | threshold drift 0° / 90° |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in R.itertuples():
        L.append(f"| {r.truth} | {r.scenario} | {r.design} | {f(r.contrast_fit)} | {f(r.bias)} ± {r.bias_se:.2f} | "
                 f"{f(r.dz)} | {r.p:.3f} | {r.r_wd:.2f} | {100 * r.acc_std:.0f} % | "
                 + (f"{100 * r.acc_str_0:.0f} / {100 * r.acc_str_90:.0f} %" if r.design == "two-track" else "n/a")
                 + f" | {100 * r.floor:.0f} % | {f(r.thr_drift_0)} / {f(r.thr_drift_90)} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--scen", default="", help=";-separated subset of scenarios (default: all)")
    ap.add_argument("--out", default=str(HERE / "drift_robustness_report.md"))
    a = ap.parse_args()
    raw = run(a.n, a.procs, [x.strip() for x in a.scen.split(";")] if a.scen else list(SCEN))
    R = summarise(raw)
    out = pathlib.Path(a.out)
    raw.to_csv(out.with_name(out.stem + "_raw.csv"), index=False)
    out.write_text(report(R, a.n))
    R.to_csv(out.with_suffix(".csv"), index=False)
    pd.set_option("display.width", 250, "display.max_columns", 30)
    print(R.round(2).to_string(index=False)); print(f"\n[out] {out}")
