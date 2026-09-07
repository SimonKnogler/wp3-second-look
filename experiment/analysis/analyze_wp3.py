"""WP3 analysis — faithful adaptation of Rollwage, Dolan & Fleming (2018, Curr Biol)
to the CDT post-decision evidence paradigm (CDT_WP3=1 runs of
CDT_windows_blockwise_fast_response.py).

Pipeline (mirrors Rollwage's STAR Methods, extended per-angle 0/90):
  1. Exclusion flags per participant (their criteria): overall accuracy outside
     [0.60, 0.85] (staircase failed), one confidence rating >90% of trials,
     median confidence RT < 850 ms, >5% timeouts.
  2. meta-d' (MLE, Maniscalco & Lau 2012 — the non-hierarchical variant Rollwage
     used) from TASK 1 ONLY, per angle, to keep it independent of the
     post-decision analysis. Ratings 1-9 are collapsed into N_BINS bins.
  3. Evidence integration (their core measure): per participant x angle,
     trial-by-trial OLS with evidence strength 0 (task 1) / 1 (low) / 2 (high)
     predicting confidence — SEPARATELY for correct trials (beta = confirmatory
     integration) and incorrect trials (sign-flipped beta = disconfirmatory
     integration; higher = more revision after contradictory evidence).
  4. Task-2-only sensitivity index: confidence ~ accuracy(+1/-1) + evidence(1/2)
     + accuracy x evidence; the interaction beta summarises sensitivity to
     post-decision evidence independently of the task-1 data used for meta-d'.
  5. Group stats (two-stage summary statistics, as Rollwage): asymmetry
     (confirmatory vs disconfirmatory), 0 vs 90 paired tests (WP3's core
     hypothesis: disconfirmatory integration lower at 0), meta-d' -> sensitivity
     regression, and optional PDI correlations (--pdi csv: participant,pdi).
  6. Figure: mean confidence by evidence level, correct vs incorrect, per angle
     (analog of Rollwage Fig 4B).

Usage:
  python analyze_wp3.py <csv-or-directory> [--pdi pdi.csv] [--bins 3]
  python analyze_wp3.py --selftest

Not implemented (later step): Rollwage's computational model comparison
(temporal-weighting / choice-bias / choice-weighting) and hierarchical mixed
models — the two-stage approach here is their primary analysis.
"""
import argparse, pathlib, sys
import numpy as np
import pandas as pd
from scipy.stats import norm, ttest_rel, ttest_1samp, wilcoxon, pearsonr, spearmanr
from scipy.optimize import minimize

ANGLES = (0, 90)
N_BINS_DEFAULT = 3          # collapse 1-9 confidence for meta-d' cell counts
MIN_TRIALS_BETA = 6         # per accuracy class; below -> NaN beta
# Rollwage exclusion thresholds
ACC_LO, ACC_HI = 0.60, 0.85
CONF_MODE_MAX = 0.90
CONF_RT_MIN = 0.850
TIMEOUT_MAX = 0.05


# ── meta-d' (MLE, Maniscalco & Lau 2012) ────────────────────────────────────────

def trials2counts(stim, resp, rating, n_bins):
    """stim/resp: 0=S1, 1=S2. rating: 1..n_bins. Returns nR_S1, nR_S2 (len 2B):
    [resp=S1 rating B..1, resp=S2 rating 1..B]."""
    nR_S1 = np.zeros(2 * n_bins)
    nR_S2 = np.zeros(2 * n_bins)
    for s, r, c in zip(stim, resp, rating):
        if r == 0:
            idx = n_bins - int(c)          # resp S1: rating B..1 -> 0..B-1
        else:
            idx = n_bins + int(c) - 1      # resp S2: rating 1..B -> B..2B-1
        (nR_S1 if s == 0 else nR_S2)[idx] += 1
    return nR_S1, nR_S2


def fit_meta_d(nR_S1, nR_S2, n_bins):
    """Equal-variance SDT, response-conditional ML. Returns dict(d1, c1, meta_d, mratio)."""
    B = n_bins
    pad = 1.0 / (2 * B)
    n1 = np.asarray(nR_S1, float) + pad
    n2 = np.asarray(nR_S2, float) + pad
    # type 1 (collapsed over ratings)
    far = n1[B:].sum() / n1.sum()          # P(resp S2 | S1)
    hr = n2[B:].sum() / n2.sum()           # P(resp S2 | S2)
    d1 = norm.ppf(hr) - norm.ppf(far)
    c1 = -0.5 * (norm.ppf(hr) + norm.ppf(far))
    if abs(d1) < 1e-6:
        return dict(d1=d1, c1=c1, meta_d=np.nan, mratio=np.nan)
    c_rel = c1 / d1                        # criterion held constant in relative units

    def segprobs(mu, meta_c, crits_desc, crits_asc):
        """P(resp,rating|stim mu). Returns (pS1_resp[B], pS2_resp[B]) rating 1..B."""
        # S1 responses: boundaries meta_c > a1 > ... > a_{B-1} > -inf
        bounds = [meta_c] + list(crits_desc) + [-np.inf]
        pS1 = [norm.cdf(bounds[j] - mu) - norm.cdf(bounds[j + 1] - mu) for j in range(B)]
        # S2 responses: meta_c < b1 < ... < b_{B-1} < inf
        bounds = [meta_c] + list(crits_asc) + [np.inf]
        pS2 = [norm.cdf(bounds[j + 1] - mu) - norm.cdf(bounds[j] - mu) for j in range(B)]
        return np.array(pS1), np.array(pS2)

    def negll(x):
        meta_d = x[0]
        meta_c = c_rel * meta_d
        s1sp = np.exp(x[1:B])              # B-1 spacings each side
        s2sp = np.exp(x[B:2 * B - 1])
        crits_desc = meta_c - np.cumsum(s1sp)
        crits_asc = meta_c + np.cumsum(s2sp)
        ll = 0.0
        for stim_counts, mu in ((n1, -meta_d / 2), (n2, meta_d / 2)):
            pS1, pS2 = segprobs(mu, meta_c, crits_desc, crits_asc)
            pRespS1, pRespS2 = max(pS1.sum(), 1e-10), max(pS2.sum(), 1e-10)
            # response-conditional rating probabilities
            condS1 = np.clip(pS1 / pRespS1, 1e-10, 1)   # rating 1..B
            condS2 = np.clip(pS2 / pRespS2, 1e-10, 1)
            # counts: [resp S1 rating B..1, resp S2 rating 1..B]
            ll += float(np.dot(stim_counts[:B][::-1], np.log(condS1)))
            ll += float(np.dot(stim_counts[B:], np.log(condS2)))
        return -ll

    x0 = np.concatenate([[d1], np.full(2 * (B - 1), np.log(0.5))])
    res = minimize(negll, x0, method='Nelder-Mead',
                   options=dict(maxiter=4000, xatol=1e-4, fatol=1e-4))
    meta_d = float(res.x[0])
    return dict(d1=float(d1), c1=float(c1), meta_d=meta_d,
                mratio=meta_d / d1 if abs(d1) > 1e-6 else np.nan)


def meta_d_from_task1(df_t1, n_bins):
    """meta-d' from task-1 trials (stim=true_shape, resp=resp_shape, binned conf)."""
    d = df_t1.dropna(subset=['wp3_confidence'])
    if len(d) < 15:
        return dict(d1=np.nan, c1=np.nan, meta_d=np.nan, mratio=np.nan)
    stim = (d['true_shape'] == 'dot').astype(int).values
    resp = (d['resp_shape'] == 'dot').astype(int).values
    conf = d['wp3_confidence'].astype(float).values
    binned = np.clip(np.ceil(conf / (9.0 / n_bins)), 1, n_bins).astype(int)
    nR_S1, nR_S2 = trials2counts(stim, resp, binned, n_bins)
    return fit_meta_d(nR_S1, nR_S2, n_bins)


# ── evidence integration (Rollwage's core betas) ────────────────────────────────

def _slope(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < MIN_TRIALS_BETA or len(np.unique(x)) < 2:
        return np.nan
    return float(np.polyfit(x, y, 1)[0])


def evidence_betas(df_angle):
    """Confirmatory / disconfirmatory integration: confidence ~ evidence level
    (0/1/2), pooled task 1 + task 2, split by initial-decision accuracy."""
    d = df_angle.dropna(subset=['wp3_confidence', 'accuracy'])
    cor = d[d['accuracy'] == 1]
    inc = d[d['accuracy'] == 0]
    beta_conf = _slope(cor['evidence_level'], cor['wp3_confidence'])
    beta_disc_raw = _slope(inc['evidence_level'], inc['wp3_confidence'])
    return dict(beta_confirmatory=beta_conf,
                beta_disconfirmatory=(-beta_disc_raw if not np.isnan(beta_disc_raw) else np.nan),
                n_correct=len(cor), n_incorrect=len(inc))


def task2_sensitivity(df_angle):
    """Task-2-only: confidence ~ acc(+1/-1) + evidence(1/2) + acc x evidence.
    Interaction beta = overall sensitivity to post-decision evidence."""
    d = df_angle[(df_angle['wp3_task'] == 2)].dropna(subset=['wp3_confidence', 'accuracy'])
    if len(d) < 2 * MIN_TRIALS_BETA:
        return np.nan
    acc = np.where(d['accuracy'].values == 1, 1.0, -1.0)
    ev = d['evidence_level'].astype(float).values
    if len(np.unique(ev)) < 2 or len(np.unique(acc)) < 2:
        return np.nan
    X = np.column_stack([np.ones(len(d)), acc, ev, acc * ev])
    beta, *_ = np.linalg.lstsq(X, d['wp3_confidence'].astype(float).values, rcond=None)
    return float(beta[3])


# ── exclusions (Rollwage criteria) ──────────────────────────────────────────────

def exclusion_flags(df_p):
    valid = df_p[~df_p['is_timeout'].astype(bool)]
    acc = valid['accuracy'].mean()
    conf = valid['wp3_confidence'].dropna()
    mode_share = conf.value_counts(normalize=True).max() if len(conf) else np.nan
    med_rt = valid['wp3_conf_rt'].dropna().median()
    to_rate = df_p['is_timeout'].astype(bool).mean()
    flags = dict(acc_out_of_range=not (ACC_LO <= acc <= ACC_HI),
                 conf_degenerate=bool(mode_share > CONF_MODE_MAX) if not np.isnan(mode_share) else True,
                 conf_rt_too_fast=bool(med_rt < CONF_RT_MIN) if not np.isnan(med_rt) else False,
                 too_many_timeouts=bool(to_rate > TIMEOUT_MAX))
    flags['exclude'] = any(flags.values())
    return flags


# ── per-participant + group pipeline ────────────────────────────────────────────

def load_wp3(path):
    p = pathlib.Path(path)
    files = sorted(p.glob("*.csv")) if p.is_dir() else [p]
    frames = []
    for f in files:
        try:
            d = pd.read_csv(f)
        except Exception:
            continue
        if 'phase' in d.columns and d['phase'].astype(str).str.startswith('wp3').any():
            w = d[d['phase'].astype(str).str.startswith('wp3_task')].copy()
            w['__file'] = f.name
            frames.append(w)
    if not frames:
        sys.exit(f"No wp3_task rows found under {path}")
    df = pd.concat(frames, ignore_index=True)
    for col in ('evidence_level', 'accuracy', 'wp3_confidence', 'wp3_conf_rt', 'angle_bias', 'wp3_task'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def analyse(df, n_bins):
    rows = []
    for pid, dp in df.groupby('participant'):
        flags = exclusion_flags(dp)
        valid = dp[~dp['is_timeout'].astype(bool)]
        for ang in ANGLES:
            da = valid[valid['angle_bias'] == ang]
            if da.empty:
                continue
            md = meta_d_from_task1(da[da['wp3_task'] == 1], n_bins)
            eb = evidence_betas(da)
            rows.append(dict(participant=pid, angle=ang,
                             n_task1=int((da['wp3_task'] == 1).sum()),
                             n_task2=int((da['wp3_task'] == 2).sum()),
                             accuracy=float(da['accuracy'].mean()),
                             mean_conf=float(da['wp3_confidence'].mean()),
                             d_prime=md['d1'], meta_d=md['meta_d'], mratio=md['mratio'],
                             beta_confirmatory=eb['beta_confirmatory'],
                             beta_disconfirmatory=eb['beta_disconfirmatory'],
                             n_correct=eb['n_correct'], n_incorrect=eb['n_incorrect'],
                             beta_interaction_task2=task2_sensitivity(da),
                             **{f'excl_{k}': v for k, v in flags.items()}))
    return pd.DataFrame(rows)


def _paired(res, col):
    """Paired 0 vs 90 test on participants having both angles."""
    w = res.pivot_table(index='participant', columns='angle', values=col).dropna()
    if len(w) < 3 or 0 not in w.columns or 90 not in w.columns:
        return None
    a, b = w[0].values, w[90].values
    t, p = ttest_rel(a, b)
    try:
        wstat, wp = wilcoxon(a, b)
    except ValueError:
        wstat, wp = np.nan, np.nan
    return dict(n=len(w), mean0=a.mean(), mean90=b.mean(), t=t, p=p, wilcoxon_p=wp)


def group_stats(res, pdi=None):
    inc = res[~res['excl_exclude'].astype(bool)]
    print(f"\n=== GROUP (n included = {inc['participant'].nunique()}"
          f" of {res['participant'].nunique()}) ===")
    # Q1 asymmetry: confirmatory vs disconfirmatory (pooled over angles, per ppt mean)
    per = inc.groupby('participant')[['beta_confirmatory', 'beta_disconfirmatory']].mean().dropna()
    if len(per) >= 3:
        t, p = ttest_rel(per['beta_confirmatory'], per['beta_disconfirmatory'])
        print(f"Q1 asymmetry  conf={per['beta_confirmatory'].mean():+.3f} vs "
              f"disc={per['beta_disconfirmatory'].mean():+.3f}   t={t:.2f} p={p:.4f}")
        for col in ('beta_confirmatory', 'beta_disconfirmatory'):
            t1, p1 = ttest_1samp(per[col], 0)
            print(f"   {col} vs 0: t={t1:.2f} p={p1:.4f}")
    # Q2 mode: 0 vs 90
    for col in ('beta_disconfirmatory', 'beta_confirmatory', 'beta_interaction_task2', 'meta_d'):
        r = _paired(inc, col)
        if r:
            print(f"Q2 {col:26s} 0deg={r['mean0']:+.3f}  90deg={r['mean90']:+.3f}  "
                  f"t={r['t']:.2f} p={r['p']:.4f} (wilcoxon p={r['wilcoxon_p']:.4f}, n={r['n']})")
    # meta-d' -> post-decision sensitivity (Rollwage: task-1 meta-d' predicts task-2 sensitivity)
    m = inc.dropna(subset=['meta_d', 'beta_interaction_task2'])
    if len(m) >= 4:
        r, p = pearsonr(m['meta_d'], m['beta_interaction_task2'])
        print(f"meta-d' -> task-2 sensitivity: pearson r={r:.3f} p={p:.4f} (n={len(m)})")
    # Q3 PDI
    if pdi is not None:
        pv = inc.pivot_table(index='participant', columns='angle',
                             values='beta_disconfirmatory').join(pdi.set_index('participant'))
        pv = pv.dropna()
        for ang in ANGLES:
            if ang in pv.columns and len(pv) >= 4:
                r, p = pearsonr(pv['pdi'], pv[ang])
                rs, ps = spearmanr(pv['pdi'], pv[ang])
                print(f"Q3 PDI vs disconfirmatory({ang}deg): r={r:.3f} p={p:.4f} "
                      f"(spearman {rs:.3f}/{ps:.4f}, n={len(pv)})")


def make_figure(df, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    valid = df[~df['is_timeout'].astype(bool)].dropna(subset=['wp3_confidence', 'accuracy'])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    for ax, ang in zip(axes, ANGLES):
        da = valid[valid['angle_bias'] == ang]
        for acc, col, lab in ((1, "#2563eb", "correct"), (0, "#d97706", "incorrect")):
            g = da[da['accuracy'] == acc].groupby('evidence_level')['wp3_confidence']
            if g.count().sum() == 0:
                continue
            m, se = g.mean(), g.sem()
            ax.errorbar(m.index, m.values, yerr=se.values, color=col, marker='o',
                        capsize=3, label=lab)
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["task 1\n(none)", "low", "high"])
        ax.set_xlabel("post-decision evidence")
        ax.set_title(f"{ang} deg")
    axes[0].set_ylabel("confidence (1-9)")
    axes[0].legend(frameon=False)
    fig.suptitle("Confidence by post-decision evidence (Rollwage Fig 4B analog)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    print(f"[fig] wrote {out_png}")


# ── self-test ───────────────────────────────────────────────────────────────────

def selftest():
    rng = np.random.default_rng(7)
    # (1) meta-d' recovery: ideal observer -> meta-d' ~= d'
    d_true, n = 1.5, 4000
    stim = rng.integers(0, 2, n)
    x = rng.normal(np.where(stim == 1, d_true / 2, -d_true / 2), 1.0)
    resp = (x > 0).astype(int)
    dist = np.abs(x)
    rating = np.digitize(dist, [0.5, 1.0]) + 1          # 1..3
    nR_S1, nR_S2 = trials2counts(stim, resp, rating, 3)
    fit = fit_meta_d(nR_S1, nR_S2, 3)
    print(f"[selftest] d'={fit['d1']:.3f} meta-d'={fit['meta_d']:.3f} (ideal observer)")
    assert abs(fit['meta_d'] - fit['d1']) < 0.25, "meta-d' recovery failed"

    # (2) beta recovery: rational vs confirmation-biased agent
    def agent(w_disc, pid):
        rows = []
        for ang in ANGLES:
            for task, levels in ((1, [0] * 60), (2, [1] * 30 + [2] * 30)):
                for ev in levels:
                    correct = rng.random() < 0.71
                    conf = 5 + (1.0 * ev if correct else -w_disc * ev) + rng.normal(0, 1)
                    rows.append(dict(participant=pid, angle_bias=ang, wp3_task=task,
                                     evidence_level=ev, accuracy=int(correct),
                                     wp3_confidence=float(np.clip(conf, 1, 9)),
                                     wp3_conf_rt=1.5, is_timeout=False,
                                     true_shape='dot' if rng.random() < .5 else 'square',
                                     resp_shape='dot'))
        return rows
    sim = pd.DataFrame(agent(1.0, 'rational') + agent(0.05, 'biased'))
    sim.loc[sim.index, 'resp_shape'] = np.where(
        sim['accuracy'] == 1, sim['true_shape'],
        np.where(sim['true_shape'] == 'dot', 'square', 'dot'))
    res = analyse(sim, 3)
    r = res.groupby('participant')[['beta_confirmatory', 'beta_disconfirmatory']].mean()
    print(r.round(3).to_string())
    assert r.loc['rational', 'beta_disconfirmatory'] > 0.5, "rational disc beta too low"
    assert r.loc['biased', 'beta_disconfirmatory'] < 0.4, "biased disc beta too high"
    assert (r['beta_confirmatory'] > 0.5).all(), "confirmatory betas too low"
    print("[selftest] PASS: meta-d' recovers; rational vs biased agents separate")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path', nargs='?', help="wp3 CSV or directory of CSVs")
    ap.add_argument('--pdi', help="CSV with columns participant,pdi")
    ap.add_argument('--bins', type=int, default=N_BINS_DEFAULT)
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        selftest(); return
    if not args.path:
        ap.error("path required (or --selftest)")
    df = load_wp3(args.path)
    print(f"Loaded {len(df)} wp3 trials, {df['participant'].nunique()} participant(s)")
    res = analyse(df, args.bins)
    out_dir = (pathlib.Path(args.path) if pathlib.Path(args.path).is_dir()
               else pathlib.Path(args.path).parent) / "wp3_analysis"
    out_dir.mkdir(exist_ok=True)
    res_path = out_dir / "wp3_results.csv"
    res.to_csv(res_path, index=False)
    print(f"[out] {res_path}")
    cols = ['participant', 'angle', 'accuracy', 'd_prime', 'meta_d',
            'beta_confirmatory', 'beta_disconfirmatory', 'beta_interaction_task2',
            'n_incorrect', 'excl_exclude']
    print(res[cols].round(3).to_string(index=False))
    pdi = pd.read_csv(args.pdi) if args.pdi else None
    if res['participant'].nunique() > 1:
        group_stats(res, pdi)
    make_figure(df, out_dir / "wp3_confidence_by_evidence.png")


if __name__ == "__main__":
    main()
