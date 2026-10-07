#!/usr/bin/env python3
"""The planned WP3 analysis, start to finish, as it will be reported.

Runs unchanged on real or simulated data (lab or web layout):

  1. Data quality and exclusions   Rollwage's participant criteria + a per-mapping accuracy window
  2. Manipulation checks           accuracy equal across mappings; strength of the evidence samples
  3. Metacognitive sensitivity     meta-d', M-ratio from Task 1, by mapping
  4. Descriptives                  confidence by evidence level x correctness x mapping
  5. Computational model           null / weight / choice / both by BIC; parameters of the BOTH model
       H1  disconfirming evidence is under-used          log w_d vs an IDEAL-OBSERVER BENCHMARK
           (not vs 0: the strength of the strong sample is extrapolated and over-estimated, which
           pulls every fitted w_d down by about a third; an ideal observer run through this
           pipeline does not come out at 1)
       H2  ...more so under the direct mapping (PRIMARY)  log w_d, 0 vs 90 deg, paired
           tested against the t distribution AND a parametric-bootstrap null
       secondary: commitment b, 0 vs 90 deg (the competing account)
  6. Validation                    only if ground_truth.csv is present: recovered vs generating values

Two-track data (trial_type column, design doc §10j): strength trials are analysed separately. They give
the MEASURED strength of the high evidence (and are checked for equality across mappings, convergence
and drift); everything else, including the exclusion criteria, uses the standard trials only.

  python wp3_paper_analysis.py DATA_DIR [--truth ground_truth.csv] [--boot 300] [--out results.json]
"""
import argparse, json, pathlib, sys, warnings
import numpy as np
import pandas as pd
from multiprocessing import Pool, cpu_count
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fit_wp3_model as F     # noqa: E402
import analyze_wp3 as A       # noqa: E402
import simulate_wp3 as S      # noqa: E402

ANGLES = (0, 90)
BLOCK_ACC = (0.55, 0.85)      # per-mapping accuracy window (design doc, staircase section)
W_LO, W_HI = 0.05, 3.0        # bounds the fitter applies to the weights
logit = F.logit


# ── small statistics helpers ────────────────────────────────────────────────────

def one_sample(x, mu=0.0):
    x = np.asarray(x, float); x = x[np.isfinite(x)]; n = len(x)
    if n < 3:
        return None
    t, p = stats.ttest_1samp(x, mu); sd = x.std(ddof=1); se = sd / np.sqrt(n); tc = stats.t.ppf(.975, n - 1)
    return dict(n=n, df=n - 1, mean=float(x.mean()), sd=float(sd), t=float(t), p=float(p),
                ci=[float(x.mean() - tc * se), float(x.mean() + tc * se)], d=float((x.mean() - mu) / sd))


def paired(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float); ok = np.isfinite(a) & np.isfinite(b); a, b = a[ok], b[ok]
    r = one_sample(a - b)
    if r is None:
        return None
    try:
        r["wilcoxon_p"] = float(stats.wilcoxon(a, b).pvalue)
    except ValueError:
        r["wilcoxon_p"] = float("nan")
    r.update(mean_a=float(a.mean()), mean_b=float(b.mean()), sd_a=float(a.std(ddof=1)), sd_b=float(b.std(ddof=1)))
    return r


def within_ci(wide):
    """Cousineau-Morey 95 % CI half-widths for a participants x cells table."""
    w = wide.dropna(); n, k = w.shape
    norm = w.sub(w.mean(axis=1), axis=0) + w.values.mean()
    return (stats.t.ppf(.975, n - 1) * norm.std(ddof=1) / np.sqrt(n) * np.sqrt(k / (k - 1))).to_dict(), n


# ── 1-4: quality, checks, metacognition, descriptives ───────────────────────────

def load(path):
    df = F.load_dir(path)
    for c in ("wp3_conf_rt", "rt_choice"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[df.phase.str.startswith("wp3_task") | df.phase.str.startswith("calibration")].copy()


def quality(df):
    rows = []
    for pid, dp in df.groupby("participant", sort=False):
        fl = A.exclusion_flags(dp); valid = dp[~dp.is_timeout]
        acc = {a: float(valid[valid.angle_bias == a].accuracy.mean()) for a in ANGLES}
        t2 = dp[dp.wp3_task == 2]
        rows.append(dict(participant=pid, n_trials=len(dp), accuracy=float(valid.accuracy.mean()),
                         acc_0=acc[0], acc_90=acc[90], timeouts=float(dp.is_timeout.mean()),
                         conf_mode_share=float(valid.wp3_confidence.value_counts(normalize=True).max()),
                         median_conf_rt=float(valid.wp3_conf_rt.median()),
                         clipped_0=float(t2[t2.angle_bias == 0].prop_high_clipped.mean()),
                         clipped_90=float(t2[t2.angle_bias == 90].prop_high_clipped.mean()),
                         block_acc_out=bool(any(not (BLOCK_ACC[0] <= v <= BLOCK_ACC[1]) for v in acc.values())),
                         **{k: bool(v) for k, v in fl.items() if k != "exclude"}))
    q = pd.DataFrame(rows)
    q["excluded"] = q[["acc_out_of_range", "conf_degenerate", "conf_rt_too_fast", "too_many_timeouts", "block_acc_out"]].any(axis=1)
    return q


def metacognition(df):
    rows = []
    for pid, dp in df.groupby("participant", sort=False):
        t1 = dp[(dp.wp3_task == 1) & ~dp.is_timeout]
        for a in ANGLES:
            m = A.meta_d_from_task1(t1[t1.angle_bias == a], 3)
            rows.append(dict(participant=pid, angle=a, d1=m["d1"], meta_d=m["meta_d"], mratio=m["mratio"]))
        m = A.meta_d_from_task1(t1, 3)
        rows.append(dict(participant=pid, angle=-1, d1=m["d1"], meta_d=m["meta_d"], mratio=m["mratio"]))
    return pd.DataFrame(rows)


def descriptives(df):
    v = df[~df.is_timeout & df.wp3_confidence.notna()]
    cell = v.groupby(["participant", "angle_bias", "evidence_level", "accuracy"]).wp3_confidence.mean().unstack(["angle_bias", "evidence_level", "accuracy"])
    ci, n = within_ci(cell)
    out = []
    for (a, lev, acc), col in cell.items():
        out.append(dict(angle=int(a), level=int(lev), correct=int(acc), mean=float(col.mean()), ci=float(ci[(a, lev, acc)]), n=n))
    betas = []
    for pid, dp in v.groupby("participant", sort=False):
        for a in ANGLES:
            b = A.evidence_betas(dp[dp.angle_bias == a])
            betas.append(dict(participant=pid, angle=a, beta_conf=b["beta_confirmatory"], beta_disc=b["beta_disconfirmatory"],
                              sens=A.task2_sensitivity(dp[dp.angle_bias == a])))
    return out, pd.DataFrame(betas)


def strength_checks(dstr, dstd):
    """Did the high strength land where the design aims, equally at both mappings, and stay there?"""
    if dstr.empty:
        return None
    v = dstr[~dstr.is_timeout & dstr.accuracy.notna()]
    g = v.groupby(["participant", "angle_bias"]).accuracy.mean().unstack().dropna()
    n = v.groupby(["participant", "angle_bias"]).accuracy.count().unstack().mean()
    diff = g[0] - g[90]; m, se, k = diff.mean(), diff.std(ddof=1) / np.sqrt(len(diff)), len(diff) - 1
    margin = 0.05                                   # equivalence margin: 5 percentage points
    out = dict(acc={str(a): dict(mean=float(g[a].mean()), sd=float(g[a].std(ddof=1)), n_trials=float(n[a])) for a in ANGLES},
               diff=paired(g[0], g[90]),
               tost=dict(margin=margin, p=float(max(1 - stats.t.cdf((m + margin) / se, k), stats.t.cdf((m - margin) / se, k)))))
    dl = v.groupby(["participant", "angle_bias"]).delta_live
    out["delta"] = {str(a): dict(first10=float(dl.apply(lambda x: x.iloc[:10].mean()).unstack()[a].mean()),
                                 last10=float(dl.apply(lambda x: x.iloc[-10:].mean()).unstack()[a].mean())) for a in ANGLES}
    s = dstd[~dstd.is_timeout]
    mm = s.groupby(["participant", "angle_bias"]).med_live.apply(
        lambda x: float(logit(x.iloc[-10:]).mean() - logit(x.iloc[:10]).mean())).unstack().dropna()
    out["threshold_drift"] = dict(by_angle={str(a): dict(mean=float(mm[a].mean()), sd=float(mm[a].std(ddof=1))) for a in ANGLES},
                                  diff=paired(mm[0], mm[90]))
    t2 = s[(s.wp3_task == 2) & (s.evidence_level == 2) & s.wp3_confidence.notna()]
    out["floor_ceiling"] = {str(a): dict(floor=float((t2[(t2.angle_bias == a) & (t2.accuracy == 0)].wp3_confidence == 1).mean()),
                                         ceiling=float((t2[(t2.angle_bias == a) & (t2.accuracy == 1)].wp3_confidence == 9).mean()))
                            for a in ANGLES}
    return out


def half_stability(fits, df):
    """w_d from the first vs second half of Task 2 (same e, same baseline): is the weight stable over the session?"""
    rows = []
    for pid, dp in df.groupby("participant", sort=False):
        for a in ANGLES:
            f = fits[(fits.participant == pid) & (fits.angle == a) & (fits.fail == "")]
            if f.empty:
                continue
            f = f.iloc[0]
            t2 = dp[(dp.angle_bias == a) & (dp.wp3_task == 2) & (dp.trial_type != "strength") & dp.wp3_confidence.notna()
                    & ~dp.is_timeout & ~dp.prop_high_clipped & dp.prop_post.notna()]
            h = len(t2) // 2
            for k, part in enumerate((t2.iloc[:h], t2.iloc[h:]), 1):
                if (part.accuracy == 0).sum() < 3:
                    continue
                e = np.where(part.evidence_level.values == 1, f.e_low, f.e_high)
                m = F.fit_models(e, part.accuracy.values == 1, part.wp3_confidence.values, f.L0_correct, f.L0_incorrect)
                rows.append(dict(participant=pid, half=k, angle=a, lwd=float(np.log(np.clip(m["w_d_both"], W_LO, W_HI)))))
    r = pd.DataFrame(rows)
    w = r.groupby(["participant", "half"]).lwd.mean().unstack().dropna()
    return dict(half1=float(w[1].mean()), half2=float(w[2].mean()), test=paired(w[1], w[2]))


# ── 5: the model ────────────────────────────────────────────────────────────────

def fit_all(df):
    rows, prior = [], F.acc_priors(F.strength_counts(df))
    for _, dp in df.groupby("participant", sort=False):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            rows += F.fit_participant(dp, prior)
    r = pd.DataFrame(rows)
    r["participant"] = r["participant"].astype(str)
    for c in ("w_d_both", "w_c_both"):
        r[c] = r[c].clip(W_LO, W_HI)
    return r


def wide(fits, col):
    return fits[fits.fail == ""].pivot_table(index="participant", columns="angle", values=col).dropna()


def model_tests(fits):
    ok = fits[fits.fail == ""]
    T = {}
    wd = wide(fits, "w_d_both"); T["n_pairs"] = int(len(wd))
    T["H2_wd_both"] = paired(np.log(wd[0]), np.log(wd[90]))
    T["H1_wd_both"] = one_sample(np.log(wd).mean(axis=1))
    T["H1_by_angle"] = {str(a): one_sample(np.log(wd[a])) for a in ANGLES}
    b = wide(fits, "b_both"); T["b_both"] = paired(b[0], b[90])
    wc = wide(fits, "w_c_both"); T["wc_both"] = paired(np.log(wc[0]), np.log(wc[90]))
    ww = wide(fits, "w_d"); T["wd_weight"] = paired(np.log(ww[0]), np.log(ww[90]))
    T["geo"] = {c: {str(a): float(np.exp(np.log(wide(fits, c)[a]).mean())) for a in ANGLES} for c in ("w_d_both", "w_c_both", "w_d")}
    models = ("null", "weight", "choice", "both")
    sums = {m: float(ok[f"bic_{m}"].sum()) for m in models}; best = min(sums.values())
    T["bic"] = dict(sum=sums, delta={m: sums[m] - best for m in models},
                    wins={m: int((ok.best_model == m).sum()) for m in models}, n_fits=int(len(ok)))
    return T


# ── parametric bootstrap under H0 (w_d equal across mappings) ───────────────────

def _boot_one(args):
    pdict, seed, design, prior = args
    S.D0_N, S.D1_N, S.D2_N = design                # strength trials per mapping (calibration block, Task 1, Task 2), as in the real data
    rng = np.random.default_rng(seed)
    df = S.simulate_participant(pd.Series(pdict), rng, "web", 0.005, 1)
    df["phase"] = df["phase"].astype(str); df["participant"] = df["participant"].astype(str)
    df["is_timeout"] = F._bool(df["is_timeout"]); df["prop_high_clipped"] = F._bool(df["prop_high_clipped"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rows = F.fit_participant(df, prior)
    out = {}
    for r in rows:
        if r.get("fail", "x") == "":
            out[int(r["angle"])] = float(np.clip(r["w_d_both"], W_LO, W_HI))
    return out


def bootstrap(fits, n_boot, seed, procs, wd="equal", design=(0, 0, 0), prior=None):
    """Re-simulate every participant's whole session from their FITTED parameters and refit,
    so the reference distribution carries whatever bias the design and estimator have.
      wd="equal"  w_d equalised across mappings (each person's own geometric mean): null for H2
      wd="ideal"  w_d = 1 at both mappings: what an ideal observer looks like THROUGH this pipeline"""
    ok = fits[fits.fail == ""]; ids = list(wide(fits, "w_d_both").index)
    people = []
    for k, pid in enumerate(ids):
        f = {int(r.angle): r for r in ok[ok.participant == pid].itertuples()}
        wd0 = 1.0 if wd == "ideal" else float(np.exp(np.mean([np.log(f[0].w_d_both), np.log(f[90].w_d_both)])))
        p = dict(participant=str(9000 + k), order=[0, 90] if k % 2 == 0 else [90, 0], slope=1.0, meta=0.0, noise=1.0,
                 wd0=wd0, wd90=wd0)
        for a in ANGLES:
            r = f[a]
            p.update({f"t{a}": float(logit(r.pf_thresh_prop)), f"slope{a}": float(r.pf_slope),
                      f"pre{a}": float((r.L0_correct + r.L0_incorrect) / 2), f"meta{a}": float((r.L0_correct - r.L0_incorrect) / 2),
                      f"wc{a}": float(r.w_c_both), f"b{a}": float(r.b_both), f"noise{a}": float(r.sd_both)})
        people.append(p)
    tasks = [(p, seed * 1_000_003 + b * 1009 + i, design, prior) for b in range(n_boot) for i, p in enumerate(people)]
    with Pool(procs) as pool:
        res = pool.map(_boot_one, tasks, chunksize=4)
    n = len(people); ts, ds, ms, m0, m90 = [], [], [], [], []
    for b in range(n_boot):
        rr = [r for r in res[b * n:(b + 1) * n] if 0 in r and 90 in r]
        d = np.array([np.log(r[0]) - np.log(r[90]) for r in rr])
        if len(d) >= 3 and d.std(ddof=1) > 0:
            ts.append(d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))); ds.append(d.mean())
            ms.append(np.mean([(np.log(r[0]) + np.log(r[90])) / 2 for r in rr]))
            m0.append(np.mean([np.log(r[0]) for r in rr])); m90.append(np.mean([np.log(r[90]) for r in rr]))
    return dict(t=np.array(ts), d=np.array(ds), m=np.array(ms), m0=np.array(m0), m90=np.array(m90))


# ── 6: validation against the generating values ─────────────────────────────────

def validation(fits, truth, df):
    ok = fits[fits.fail == ""].merge(truth, on="participant")
    V = dict(points=[], params={}, evidence={})
    t2 = df[(df.wp3_task == 2) & ~df.is_timeout & ~df.prop_high_clipped & df.prop_post.notna()].merge(truth, on="participant")
    for a in ANGLES:
        d = t2[t2.angle_bias == a]; tt = d["t0"] if a == 0 else d["t90"]
        d = d.assign(e_true=logit(S.p_correct(d.prop_post.values, tt.values, d.slope.values)))
        f = ok[ok.angle == a]
        V["evidence"][str(a)] = dict(e_low_true=float(d[d.evidence_level == 1].e_true.mean()), e_high_true=float(d[d.evidence_level == 2].e_true.mean()),
                                     e_low_fit=float(f.e_low.mean()), e_high_fit=float(f.e_high.mean()),
                                     slope_true=float(f.slope.mean()), slope_fit=float(f.pf_slope.median()))
    for a, wd, wc, b in ((0, "wd0", "wc0", "b0"), (90, "wd90", "wc90", "b90")):
        s = ok[ok.angle == a]
        for r in s.itertuples():
            V["points"].append(dict(participant=r.participant, angle=a, wd_true=float(getattr(r, wd)), wd_fit=float(r.w_d_both),
                                    b_true=float(getattr(r, b)), b_fit=float(r.b_both)))
        V["params"][str(a)] = dict(
            wd_true=float(np.exp(np.log(s[wd]).mean())), wd_fit=float(np.exp(np.log(s.w_d_both).mean())),
            wc_true=float(np.exp(np.log(s[wc]).mean())), wc_fit=float(np.exp(np.log(s.w_c_both).mean())),
            b_true=float(s[b].mean()), b_fit=float(s.b_both.mean()))
    al = ok.copy(); al["wd_true"] = np.where(al.angle == 0, al.wd0, al.wd90)
    V["r_wd"] = float(np.corrcoef(np.log(al.wd_true), np.log(al.w_d_both))[0, 1])
    w = wide(fits, "w_d_both"); t = truth.set_index("participant").loc[w.index]
    dfit = np.log(w[0]) - np.log(w[90])
    V["delta"] = dict(true_mean=float(t.delta_true.mean()), fit_mean=float(dfit.mean()),
                      true_sd=float(t.delta_true.std(ddof=1)), fit_sd=float(dfit.std(ddof=1)),
                      r=float(np.corrcoef(t.delta_true, dfit)[0, 1]),
                      pairs=[dict(participant=i, true=float(t.delta_true[i]), fit=float(dfit[i])) for i in w.index])
    return V


# ── run ─────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path"); ap.add_argument("--truth"); ap.add_argument("--out")
    ap.add_argument("--boot", type=int, default=300, help="replicates, null for H2 (0 = skip both bootstraps)")
    ap.add_argument("--boot-ideal", type=int, default=200, help="replicates, ideal-observer benchmark for H1")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--no-stability", dest="stability", action="store_false", help="skip the half-split refit of w_d")
    ap.add_argument("--procs", type=int, default=cpu_count())
    a = ap.parse_args()
    allrows = load(a.path)                                   # calibration + all rated trials
    df = allrows[allrows.phase.str.startswith("wp3_task")]
    dstd = df[df.trial_type != "strength"]                   # standard trials: exclusions, checks, descriptives
    q = quality(dstd); keep = set(q[~q.excluded].participant)
    dfk = dstd[dstd.participant.isin(keep)]
    dstr = df[(df.trial_type == "strength") & df.participant.isin(keep)]
    R = dict(n_total=int(len(q)), n_excluded=int(q.excluded.sum()), n_included=len(keep),
             n_trials=int(len(dfk)), quality=q.to_dict("records"))

    valid = dfk[~dfk.is_timeout]
    acc = valid.groupby(["participant", "angle_bias"]).accuracy.mean().unstack()
    prop = valid.groupby(["participant", "angle_bias"]).prop_used.mean().unstack()
    R["checks"] = dict(accuracy=paired(acc[0], acc[90]), prop=paired(prop[0], prop[90]),
                       acc_points=[dict(participant=i, a0=float(acc.loc[i, 0]), a90=float(acc.loc[i, 90])) for i in acc.index])

    md = metacognition(dfk); R["meta"] = dict(rows=md.to_dict("records"))
    for col in ("d1", "meta_d", "mratio"):
        w = md[md.angle >= 0].pivot_table(index="participant", columns="angle", values=col).dropna()
        R["meta"][col] = paired(w[0], w[90])
    pooled = md[md.angle == -1]
    R["meta"]["pooled"] = {c: dict(mean=float(pooled[c].mean()), sd=float(pooled[c].std(ddof=1))) for c in ("d1", "meta_d", "mratio")}

    R["cells"], betas = descriptives(dfk)
    bw = betas.pivot_table(index="participant", columns="angle", values="beta_disc").dropna()
    R["beta_disc"] = paired(bw[0], bw[90])

    kept = allrows[allrows.participant.isin(keep)]
    fits = fit_all(kept); R["fits"] = json.loads(fits.to_json(orient="records"))
    R["strength"] = strength_checks(dstr, dfk)
    prior = F.acc_priors(F.strength_counts(kept))
    cnt = dstr.groupby(["participant", "angle_bias", "wp3_task"]).size().groupby("wp3_task").median()
    blk = allrows[(allrows.phase == "calibration_strength") & allrows.participant.isin(keep)]
    d0 = int(blk.groupby(["participant", "angle_bias"]).size().median()) if len(blk) else 0
    design = (d0, int(cnt.get(1, 0)), int(cnt.get(2, 0)))    # strength trials per mapping: calibration block, Task 1, Task 2
    R["design"] = dict(strength_calibration=design[0], strength_task1=design[1], strength_task2=design[2])
    if a.stability:
        R["half"] = half_stability(fits, dfk)
    R["n_calibration_rows"] = int((allrows.phase.str.startswith("calibration")).sum())
    R["model_fail"] = fits[fits.fail != ""][["participant", "angle", "fail"]].to_dict("records")
    ok = fits[fits.fail == ""]
    R["evidence"] = {str(g): dict(e_low=float(s.e_low.mean()), e_high=float(s.e_high.mean()),
                                  p_low=float(F.sig(s.e_low).mean()), p_high=float(F.sig(s.e_high).mean()),
                                  n_inc_t2=float(s.n_task2_incorrect.mean())) for g, s in ok.groupby("angle")}
    R["tests"] = model_tests(fits)
    sens = betas.groupby("participant").sens.mean(); mr = pooled.set_index("participant").meta_d
    j = pd.concat([sens, mr], axis=1).dropna()
    R["meta_predicts_sens"] = dict(r=float(j.corr().iloc[0, 1]), n=int(len(j)))

    if a.boot > 0:
        B = bootstrap(fits, a.boot, a.seed, a.procs, "equal", design, prior); ts, ds = B["t"], B["d"]
        I = bootstrap(fits, a.boot_ideal, a.seed + 7, a.procs, "ideal", design, prior)
        obs = R["tests"]["H1_wd_both"]["mean"]; wdw = wide(fits, "w_d_both")
        R["ideal"] = dict(n=int(len(I["m"])), obs=obs, null_mean=float(I["m"].mean()), null_sd=float(I["m"].std(ddof=1)),
                          p=float((np.sum(np.abs(I["m"] - I["m"].mean()) >= abs(obs - I["m"].mean())) + 1) / (len(I["m"]) + 1)),
                          by_angle={str(g): dict(obs=float(np.log(wdw[g]).mean()), null_mean=float(I[k].mean()), null_sd=float(I[k].std(ddof=1)),
                                                 p=float((np.sum(np.abs(I[k] - I[k].mean()) >= abs(np.log(wdw[g]).mean() - I[k].mean())) + 1) / (len(I[k]) + 1)))
                                    for g, k in ((0, "m0"), (90, "m90"))},
                          null_diff=float(I["d"].mean()))
        t_obs = R["tests"]["H2_wd_both"]["t"]
        R["boot"] = dict(n=int(len(ts)), t_obs=t_obs, p=float((np.sum(np.abs(ts) >= abs(t_obs)) + 1) / (len(ts) + 1)),
                         null_mean_diff=float(ds.mean()), null_t_mean=float(ts.mean()), null_t_sd=float(ts.std(ddof=1)),
                         crit=[float(np.quantile(ts, .025)), float(np.quantile(ts, .975))],
                         hist=np.histogram(ts, bins=np.arange(-6, 6.01, 0.5))[0].tolist())

    tp = pathlib.Path(a.truth) if a.truth else pathlib.Path(a.path).parent / "ground_truth.csv"
    if tp.exists():
        R["validation"] = validation(fits, pd.read_csv(tp, dtype={"participant": str}), dfk)
    out = pathlib.Path(a.out) if a.out else pathlib.Path(a.path).parent / "results.json"
    out.write_text(json.dumps(R, indent=1, default=float))
    h2, h1 = R["tests"]["H2_wd_both"], R["tests"]["H1_wd_both"]
    print(f"included {R['n_included']} of {R['n_total']}; paired fits {R['tests']['n_pairs']}")
    print(f"H1  log w_d vs 0: M={h1['mean']:+.3f}  t({h1['df']})={h1['t']:.2f}  p={h1['p']:.4f}   (biased benchmark, see ideal)")
    if "ideal" in R:
        i = R["ideal"]; print(f"    vs ideal-observer benchmark ({i['n']} replicates): ideal comes out at {i['null_mean']:+.3f} (w_d = {np.exp(i['null_mean']):.2f}), observed {i['obs']:+.3f}, p={i['p']:.4f}")
    print(f"H2  log w_d 0 vs 90: diff={h2['mean']:+.3f} CI[{h2['ci'][0]:+.3f},{h2['ci'][1]:+.3f}]  t({h2['df']})={h2['t']:.2f}  p={h2['p']:.4f}  dz={h2['d']:.2f}")
    if "boot" in R:
        print(f"    bootstrap null ({R['boot']['n']} replicates): p={R['boot']['p']:.4f}  null mean diff={R['boot']['null_mean_diff']:+.3f}")
    if "validation" in R:
        d = R["validation"]["delta"]; print(f"validation: true diff {d['true_mean']:+.3f} -> recovered {d['fit_mean']:+.3f};  r(log w_d true, fit)={R['validation']['r_wd']:.2f}")
    print(f"[out] {out}")


if __name__ == "__main__":
    main()
