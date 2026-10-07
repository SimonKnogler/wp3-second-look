"""Model-based WP3 analysis: the Bayes-reference fit that the descriptive slopes in
analyze_wp3.py cannot replace (raw slopes are distorted by the bounded scale, see
design doc §10d / briefing §11).

Per participant x angle:
  1. Evidence strength e = logit(P(correct)) of a sample.
     Two-track design (trial_type column, design doc §10j): MEASURED. e_low = accuracy on the
     standard first looks, e_high = accuracy on the interleaved strength trials (choice-only trials
     whose first look is at the high strength; empirical-Bayes shrunk toward the group). The
     psychometric function, fitted on every decision trial including the strength-calibration
     block, only supplies the trial-to-trial variation around those levels ("anchored").
     Old files without strength trials: INFERRED from a psychometric function fitted on all
     decision trials (calibration + Task 1 + Task 2):  P(correct|prop) = .5 + .5*sigmoid(a*(logit(prop)-t)).
     The psychometric fit is always kept as a diagnostic.
  2. Baseline log-odds from Task 1 (level 0), separately for correct / incorrect trials:
     L0_c, L0_i = logit((mean rating - 1)/8).
  3. Task-2 ratings are fit by maximum likelihood (Gaussian on the 1-9 scale) under
       WEIGHT : L = L0_class + w_c*e (correct) | L0_class - w_d*e (incorrect)     params w_c, w_d, sd
       CHOICE : L = L0_class + b   + e         | L0_class + b   - e               params b, sd
       BOTH   : L = L0_class + b   + w_c*e     | L0_class + b   - w_d*e           params b, w_c, w_d, sd
     rating_hat = 1 + 8*sigmoid(L).  Model comparison by BIC.
  4. Group level (two-stage, as Rollwage): H1 log(w_d/w_c) < 0; H2 paired 0 vs 90;
     PDI correlations; BIC winner counts.  --truth ground_truth.csv adds parameter recovery.

Usage:
  python fit_wp3_model.py DATA_DIR [--pdi pdi.csv] [--truth ground_truth.csv] [--out results.csv]
"""
import argparse, pathlib, sys, warnings
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import ttest_1samp, ttest_rel, wilcoxon, pearsonr, spearmanr

sig = lambda x: 1.0 / (1.0 + np.exp(-x))
logit = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
ANGLES = (0, 90)
MIN_INCORRECT = 6


# ── loading (robust to the quirks the task actually produces) ───────────────────

def _bool(s):
    """is_timeout / prop_high_clipped arrive as bool, 'True'/'False' strings or NaN."""
    return s.map(lambda v: str(v).strip().lower() == "true" if pd.notna(v) else False)


def load_dir(path):
    frames = []
    for f in sorted(pathlib.Path(path).glob("*.csv")):
        if f.name in ("pdi.csv", "ground_truth.csv"):
            continue
        d = pd.read_csv(f, low_memory=False)
        if "phase" not in d.columns:
            continue
        d = d.loc[:, ~d.columns.str.contains(r"\.1$|^Unnamed")]      # duplicated expInfo columns
        d["__file"] = f.name
        frames.append(d)
    if not frames:
        sys.exit(f"no task CSVs under {path}")
    df = pd.concat(frames, ignore_index=True)
    df["phase"] = df["phase"].astype(str)
    for c in ("angle_bias", "prop_used", "prop_post", "accuracy", "wp3_confidence", "evidence_level", "wp3_task"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["is_timeout"] = _bool(df["is_timeout"]) if "is_timeout" in df.columns else False
    df["prop_high_clipped"] = _bool(df["prop_high_clipped"]) if "prop_high_clipped" in df.columns else False
    df["participant"] = df["participant"].astype(str)
    df["trial_type"] = df["trial_type"].fillna("standard") if "trial_type" in df.columns else "standard"
    return df


# ── 1. psychometric function ────────────────────────────────────────────────────

def fit_psychometric(prop, correct):
    x, y = logit(np.asarray(prop, float)), np.asarray(correct, float)
    if len(x) < 20 or len(np.unique(x)) < 3:
        return None
    def nll(th):
        a, t = np.exp(th[0]), th[1]
        p = np.clip(0.5 + 0.5 * sig(a * (x - t)), 1e-6, 1 - 1e-6)
        return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
    best = None
    for t0 in np.quantile(x, [0.3, 0.5, 0.7]):
        r = minimize(nll, [np.log(2.0), t0], method="Nelder-Mead")
        if best is None or r.fun < best.fun:
            best = r
    return dict(slope=float(np.exp(best.x[0])), thresh=float(best.x[1]))


def evidence_logit(prop, pf):
    p = 0.5 + 0.5 * sig(pf["slope"] * (logit(prop) - pf["thresh"]))
    return np.maximum(logit(p), 0.0)


# ── 3. updating models ──────────────────────────────────────────────────────────

def fit_models(e, correct, rating, L0c, L0i):
    """Returns dict of fitted params + BIC per model, or None."""
    e, c, r = np.asarray(e, float), np.asarray(correct, bool), np.asarray(rating, float)
    L0 = np.where(c, L0c, L0i)
    sgn = np.where(c, 1.0, -1.0)
    n = len(r)

    from scipy.stats import norm as _N

    def nll(pred, logsd):
        """Censored Gaussian (Tobit): a rating of 1 or 9 is an interval, not a point —
        otherwise saturated cells (everything at 9) make the weight unidentifiable and
        pull it toward zero."""
        sd = np.exp(logsd)
        z = (r - pred) / sd
        inner = (r > 1) & (r < 9)
        ll = np.sum(_N.logpdf(z[inner]) - logsd)
        ll += np.sum(_N.logsf((9 - 0.5 - pred[r >= 9]) / sd))     # P(rating >= 9)
        ll += np.sum(_N.logcdf((1 + 0.5 - pred[r <= 1]) / sd))    # P(rating <= 1)
        return -ll

    def M_weight(th):
        wc, wd = np.exp(th[0]), np.exp(th[1])
        return nll(1 + 8 * sig(L0 + np.where(c, wc, -wd) * e), th[2])

    def M_choice(th):
        b = th[0]
        return nll(1 + 8 * sig(L0 + b + sgn * e), th[1])

    def M_both(th):
        b, wc, wd = th[0], np.exp(th[1]), np.exp(th[2])
        return nll(1 + 8 * sig(L0 + b + np.where(c, wc, -wd) * e), th[3])

    def M_null(th):                      # ideal observer: w_c = w_d = 1, no bonus; only noise
        return nll(1 + 8 * sig(L0 + sgn * e), th[0])

    out = {}
    for name, fn, x0, k in (("null", M_null, [0], 1), ("weight", M_weight, [0, 0, 0], 3),
                            ("choice", M_choice, [0, 0], 2), ("both", M_both, [0, 0, 0, 0], 4)):
        best = None
        for jit in (0.0, 0.5, -0.5):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = minimize(fn, np.array(x0, float) + jit, method="Nelder-Mead",
                               options=dict(maxiter=4000, xatol=1e-5, fatol=1e-6))
            if best is None or res.fun < best.fun:
                best = res
        out[f"bic_{name}"] = 2 * best.fun + k * np.log(n)
        if name == "weight":
            out["w_c"], out["w_d"] = float(np.exp(best.x[0])), float(np.exp(best.x[1]))
        elif name == "choice":
            out["b_choice"] = float(best.x[0])
        elif name == "both":
            out["b_both"], out["w_c_both"], out["w_d_both"] = float(best.x[0]), float(np.exp(best.x[1])), float(np.exp(best.x[2]))
            out["sd_both"] = float(np.exp(best.x[3]))
        # "null" has only the noise parameter — nothing to extract
    out["best_model"] = min(("null", "weight", "choice", "both"), key=lambda m: out[f"bic_{m}"])
    # Weights are only identified within a range: a saturated cell can push a weight to
    # ~0 or to infinity at almost no likelihood cost. Bound them and flag it, and give the
    # group tests a winsorised log-ratio so one degenerate fit cannot dominate a t-test.
    W_LO, W_HI = 0.05, 3.0
    out["at_bound"] = bool(out["w_c"] <= W_LO * 1.05 or out["w_c"] >= W_HI / 1.05
                           or out["w_d"] <= W_LO * 1.05 or out["w_d"] >= W_HI / 1.05)
    out["w_c"], out["w_d"] = float(np.clip(out["w_c"], W_LO, W_HI)), float(np.clip(out["w_d"], W_LO, W_HI))
    return out


# ── measured evidence strength (two-track design) ───────────────────────────────

def strength_counts(df):
    """Correct / total strength trials per participant x angle: the interleaved ones in Task 1 + 2
    (no feedback, concurrent with the second looks they calibrate). The strength-calibration block
    only sets delta's start and feeds the psychometric fit."""
    if "trial_type" not in df.columns:
        return pd.DataFrame(columns=["participant", "angle_bias", "k", "n"])
    d = df[(df["trial_type"] == "strength") & df["accuracy"].notna() & ~df["is_timeout"] & df["wp3_task"].isin([1, 2])]
    return d.groupby(["participant", "angle_bias"])["accuracy"].agg(k="sum", n="count").reset_index()


def acc_priors(counts):
    """Beta prior per angle by method of moments from the people's strength accuracies.
    Between-person variance = observed variance of k/n minus the binomial noise expected anyway;
    if that is <= 0 the people are indistinguishable and we pool completely (pseudo-count 1000)."""
    out = {}
    for ang, g in counts.groupby("angle_bias"):
        p = g.k.sum() / g.n.sum()
        v = np.var(g.k / g.n, ddof=1) - np.mean(p * (1 - p) / g.n) if len(g) > 2 else 0.0
        m = np.clip(p * (1 - p) / v - 1, 1.0, 1000.0) if v > 0 else 1000.0
        out[int(ang)] = (p * m, (1 - p) * m)
    return out


# ── per participant x angle ─────────────────────────────────────────────────────

def fit_participant(dp, acc_prior=None, e_mode="anchored"):
    """acc_prior: {angle: (a0, b0)} Beta prior for the strength accuracy (see acc_priors);
    None = a flat Beta(.5, .5), i.e. the raw accuracy.
    e_mode (only with strength trials):
      "anchored" (default) = the LEVEL of e is the measured accuracy (drift-proof, not extrapolated);
                 trial-to-trial variation within a level comes from the psychometric function and only
                 scales deviations around that mean. Simulation (design doc §10j): as precise as the
                 old route, and removes ~80 % of the spurious contrast that mapping-specific drift causes.
      "measured" = one constant e per level. Unbiased under drift but discards real trial-level variation:
                 the contrast is 40-60 % noisier.
      "inferred" = the psychometric e alone: no protection against drift."""
    rows = []
    for ang in ANGLES:
        da = dp[dp["angle_bias"] == ang]
        if da.empty:
            continue
        dec = da[da["accuracy"].notna() & da["prop_used"].notna() & ~da["is_timeout"]]
        pf = fit_psychometric(dec["prop_used"], dec["accuracy"])         # always: it is the old route to e
        row = dict(participant=dp["participant"].iloc[0], angle=ang, n_psychometric=len(dec),
                   pf_slope=np.nan, pf_thresh_prop=np.nan)
        if pf is not None:
            row.update(pf_slope=pf["slope"], pf_thresh_prop=float(sig(pf["thresh"])))
        std = da[da["trial_type"] != "strength"] if "trial_type" in da.columns else da
        strn = (da[(da["trial_type"] == "strength") & da["accuracy"].notna() & ~da["is_timeout"] & da["wp3_task"].isin([1, 2])]
                if "trial_type" in da.columns else da.iloc[0:0])
        measured = len(strn) > 0
        if (not measured or e_mode != "measured") and pf is None:
            row["fail"] = "psychometric"; rows.append(row); continue
        t1 = std[(std["wp3_task"] == 1) & std["wp3_confidence"].notna() & ~std["is_timeout"]]
        t2 = std[(std["wp3_task"] == 2) & std["wp3_confidence"].notna() & ~std["is_timeout"]
                 & ~std["prop_high_clipped"] & std["prop_post"].notna()]
        n_inc = int((t2["accuracy"] == 0).sum())
        row.update(n_task1=len(t1), n_task2=len(t2), n_task2_incorrect=n_inc, n_strength=len(strn),
                   n_clipped=int(std["prop_high_clipped"].sum()))
        if len(t1) < 10 or n_inc < MIN_INCORRECT or (measured and len(strn) < 8):
            row["fail"] = "too_few_trials"; rows.append(row); continue
        L0c = float(logit((t1.loc[t1["accuracy"] == 1, "wp3_confidence"].mean() - 1) / 8))
        L0i = float(logit((t1.loc[t1["accuracy"] == 0, "wp3_confidence"].mean() - 1) / 8))
        if measured:
            a0, b0 = (acc_prior or {}).get(ang, (0.5, 0.5))
            first = std[std["accuracy"].notna() & ~std["is_timeout"] & std["wp3_task"].isin([1, 2])]
            acc_low = float(first["accuracy"].mean())
            acc_high = float((strn["accuracy"].sum() + a0) / (len(strn) + a0 + b0))
            e_low, e_high = max(float(logit(acc_low)), 0.0), max(float(logit(acc_high)), 0.0)
            e = np.where(t2["evidence_level"].values == 1, e_low, e_high)
            if e_mode != "measured":
                e_inf = evidence_logit(t2["prop_post"].values, pf)
                if e_mode == "anchored":
                    for lev, target in ((1, e_low), (2, e_high)):
                        m = t2["evidence_level"].values == lev
                        e = np.where(m, e_inf - e_inf[m].mean() + target, e)
                    e = np.maximum(e, 0.0)
                else:
                    e = e_inf
            row.update(acc_low=acc_low, acc_high=acc_high, acc_high_raw=float(strn["accuracy"].mean()))
        else:
            e = evidence_logit(t2["prop_post"].values, pf)
            e_low, e_high = float(np.mean(e[t2["evidence_level"] == 1])), float(np.mean(e[t2["evidence_level"] == 2]))
        row.update(L0_correct=L0c, L0_incorrect=L0i, e_low=e_low, e_high=e_high)
        row.update(fit_models(e, t2["accuracy"].values == 1, t2["wp3_confidence"].values, L0c, L0i))
        row["log_ratio"] = np.log(row["w_d"] / row["w_c"])
        row["fail"] = ""
        rows.append(row)
    return rows


# ── group level ─────────────────────────────────────────────────────────────────

def group_report(res, pdi=None, truth=None):
    ok = res[res["fail"] == ""].copy()
    ok["log_ratio"] = np.log(ok["w_d"] / ok["w_c"])            # on the bounded weights
    lo, hi = ok["log_ratio"].quantile([0.05, 0.95])
    ok["log_ratio_w"] = ok["log_ratio"].clip(lo, hi)            # winsorised for the t-tests
    print(f"\n=== MODEL-BASED RESULTS  (fits: {len(ok)} of {len(res)} participant x angle;"
          f" failures: {res['fail'].value_counts().drop('', errors='ignore').to_dict()};"
          f" at weight bound: {int(ok['at_bound'].sum())}) ===")
    for ang in ANGLES:
        a = ok[ok.angle == ang]
        print(f"  {ang:>2} deg  median w_c={a.w_c.median():.2f}  w_d={a.w_d.median():.2f}  "
              f"median log(w_d/w_c)={a.log_ratio.median():+.3f}  e_low={a.e_low.mean():.2f} e_high={a.e_high.mean():.2f}"
              f"  best model: {a.best_model.value_counts().to_dict()}")
    print("  (t-tests below use the 5–95 % winsorised log-ratio; medians above are raw)")
    per = ok.groupby("participant")["log_ratio_w"].mean()
    t, p = ttest_1samp(per, 0)
    print(f"\nH1 asymmetry  mean log(w_d/w_c) = {per.mean():+.3f}   t({len(per)-1})={t:.2f}  p={p:.2e}"
          f"   -> {'CONFIRMATION BIAS' if per.mean() < 0 and p < .05 else 'n.s. / other'}")
    w = ok.pivot_table(index="participant", columns="angle", values="log_ratio_w").dropna()
    if len(w) >= 3:
        t, p = ttest_rel(w[0], w[90])
        try: _, wp = wilcoxon(w[0], w[90])
        except ValueError: wp = np.nan
        print(f"H2 mode       log-ratio 0deg={w[0].mean():+.3f}  90deg={w[90].mean():+.3f}  "
              f"diff={(w[0]-w[90]).mean():+.3f}  t({len(w)-1})={t:.2f}  p={p:.2e}  wilcoxon p={wp:.2e}")
    # w_d alone is the well-identified quantity (incorrect trials start mid-scale; correct
    # trials start near the ceiling, so w_c is poorly identified per person). Report the
    # mode contrast on log(w_d) as the primary model-based test.
    wd = ok.pivot_table(index="participant", columns="angle", values="w_d").dropna()
    if len(wd) >= 3:
        t, p = ttest_rel(np.log(wd[0]), np.log(wd[90]))
        try: _, wp = wilcoxon(np.log(wd[0]), np.log(wd[90]))
        except ValueError: wp = np.nan
        print(f"H2 (w_d only) median w_d 0deg={wd[0].median():.2f}  90deg={wd[90].median():.2f}  "
              f"paired t on log w_d: t({len(wd)-1})={t:.2f}  p={p:.2e}  wilcoxon p={wp:.2e}   <- primary")
    if pdi is not None:
        pv = ok.pivot_table(index="participant", columns="angle", values="w_d").join(pdi.set_index("participant")["pdi"]).dropna()
        for ang in ANGLES:
            r, p = pearsonr(pv["pdi"], pv[ang]); rs, ps = spearmanr(pv["pdi"], pv[ang])
            print(f"H3 PDI x w_d({ang:>2}deg)  r={r:+.3f} p={p:.3f}   spearman={rs:+.3f} p={ps:.3f}  (n={len(pv)})")
    if truth is not None:
        print("\n=== PARAMETER RECOVERY (fitted vs generating) ===")
        m = ok.merge(truth, on="participant")
        for ang, wc, wd in ((0, "wc0", "wd0"), (90, "wc90", "wd90")):
            a = m[m.angle == ang]
            print(f"  {ang:>2} deg  w_c: r={pearsonr(a.w_c, a[wc])[0]:.2f}  bias={np.mean(a.w_c-a[wc]):+.2f}"
                  f"   w_d: r={pearsonr(a.w_d, a[wd])[0]:.2f}  bias={np.mean(a.w_d-a[wd]):+.2f}"
                  f"   log-ratio: r={pearsonr(a.log_ratio, np.log(a[wd]/a[wc]))[0]:.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path"); ap.add_argument("--pdi"); ap.add_argument("--truth"); ap.add_argument("--out")
    a = ap.parse_args()
    df = load_dir(a.path)
    print(f"loaded {df['participant'].nunique()} participants, {len(df)} rows, phases: {sorted(df.phase.unique())}")
    rows, prior = [], acc_priors(strength_counts(df))
    for _, dp in df.groupby("participant", sort=False):
        rows += fit_participant(dp, prior)
    res = pd.DataFrame(rows)
    out = pathlib.Path(a.out) if a.out else pathlib.Path(a.path) / "wp3_model_fits.csv"
    res.to_csv(out, index=False); print(f"[out] {out}")
    pdi = pd.read_csv(a.pdi, dtype={"participant": str}) if a.pdi else None
    truth = pd.read_csv(a.truth, dtype={"participant": str}) if a.truth else None
    group_report(res, pdi, truth)


if __name__ == "__main__":
    main()
