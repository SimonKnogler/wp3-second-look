"""meta-d' after Maniscalco & Lau (2012), maximum-likelihood fit.

Port of `fit_meta_d_MLE.m` (Maniscalco & Lau 2012, Consciousness & Cognition 21;
see also Fleming & Lau 2014). Fills the gap the Antrag names for WP1-H2: the
pipeline's section C reports type-2 AUROC, which does not control for type-1
performance, whereas meta-d' does.

The idea: meta-d' is the type-1 sensitivity that a *metacognitively ideal*
observer would need in order to produce the confidence data actually observed.
Comparing it to the real d' separates metacognitive efficiency from perceptual
sensitivity:

    M-ratio = meta-d' / d'      1.0 = ideal, < 1 = information lost after the
                                decision, > 1 = more information used for
                                confidence than for the decision itself
    M-diff  = meta-d' - d'      same thing on an absolute scale

Usage
-----
    from metad import fit_meta_d, trials2counts

    nR_S1, nR_S2 = trials2counts(stimulus, response, confidence, n_ratings=4)
    fit = fit_meta_d(nR_S1, nR_S2)
    fit["meta_da"], fit["da"], fit["M_ratio"]

CLI: `python metad.py <data_dir>` fits every subject x angle on medium trials.

Caveats that matter at this sample size: the fit needs a reasonable number of
trials per response x confidence cell. With ~50 trials per cell and a 4-point
scale, several cells will be sparse; the standard 1/(2*nRatings) padding is
applied and `cells_padded` is reported so you can see when it fired.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm


def trials2counts(stimulus, response, confidence, n_ratings, pad=False):
    """Response counts per stimulus class, ordered as fit_meta_d expects.

    stimulus, response : 0/1 arrays (0 = S1, 1 = S2)
    confidence         : integers 1..n_ratings
    Returns (nR_S1, nR_S2), each of length 2*n_ratings, ordered
        [resp S1 conf n .. resp S1 conf 1, resp S2 conf 1 .. resp S2 conf n]
    """
    stimulus = np.asarray(stimulus, int)
    response = np.asarray(response, int)
    confidence = np.asarray(confidence, int)
    m = np.isfinite(confidence) & (confidence >= 1) & (confidence <= n_ratings)
    stimulus, response, confidence = stimulus[m], response[m], confidence[m]

    nR_S1, nR_S2 = [], []
    for r in range(n_ratings, 0, -1):          # resp S1, confidence high -> low
        nR_S1.append(np.sum((stimulus == 0) & (response == 0) & (confidence == r)))
        nR_S2.append(np.sum((stimulus == 1) & (response == 0) & (confidence == r)))
    for r in range(1, n_ratings + 1):          # resp S2, confidence low -> high
        nR_S1.append(np.sum((stimulus == 0) & (response == 1) & (confidence == r)))
        nR_S2.append(np.sum((stimulus == 1) & (response == 1) & (confidence == r)))
    nR_S1 = np.array(nR_S1, float)
    nR_S2 = np.array(nR_S2, float)
    if pad:
        nR_S1 += 1.0 / (2 * n_ratings)
        nR_S2 += 1.0 / (2 * n_ratings)
    return nR_S1, nR_S2


def _logL(params, nR_S1, nR_S2, n_ratings, d1, t1c1, s):
    meta_d1 = params[0]
    t2c1 = params[1:]

    S1mu, S1sd = -meta_d1 / 2.0, 1.0
    S2mu, S2sd = meta_d1 / 2.0, 1.0 / s
    # Shift so the type-1 criterion sits at zero. The criterion is carried over
    # from type 1, rescaled by meta_d'/d' so its *relative* placement is kept —
    # this is what makes meta-d' comparable to d' rather than a free refit.
    shift = meta_d1 * (t1c1 / d1)
    S1mu -= shift
    S2mu -= shift
    t1c = 0.0

    C_area_rS1 = norm.cdf(t1c, S1mu, S1sd)
    I_area_rS1 = norm.cdf(t1c, S2mu, S2sd)
    C_area_rS2 = 1 - norm.cdf(t1c, S2mu, S2sd)
    I_area_rS2 = 1 - norm.cdf(t1c, S1mu, S1sd)
    if min(C_area_rS1, I_area_rS1, C_area_rS2, I_area_rS2) < 1e-12:
        return 1e10

    bounds = np.concatenate(([-np.inf], t2c1[:n_ratings - 1], [t1c],
                             t2c1[n_ratings - 1:], [np.inf]))

    prC_rS1 = np.diff(norm.cdf(bounds[:n_ratings + 1], S1mu, S1sd)) / C_area_rS1
    prI_rS1 = np.diff(norm.cdf(bounds[:n_ratings + 1], S2mu, S2sd)) / I_area_rS1
    prC_rS2 = np.diff(norm.cdf(bounds[n_ratings:], S2mu, S2sd)) / C_area_rS2
    prI_rS2 = np.diff(norm.cdf(bounds[n_ratings:], S1mu, S1sd)) / I_area_rS2

    nC_rS1 = nR_S1[:n_ratings]
    nI_rS1 = nR_S2[:n_ratings]
    nC_rS2 = nR_S2[n_ratings:]
    nI_rS2 = nR_S1[n_ratings:]

    eps = 1e-12
    logL = (np.sum(nC_rS1 * np.log(np.clip(prC_rS1, eps, None)))
            + np.sum(nI_rS1 * np.log(np.clip(prI_rS1, eps, None)))
            + np.sum(nC_rS2 * np.log(np.clip(prC_rS2, eps, None)))
            + np.sum(nI_rS2 * np.log(np.clip(prI_rS2, eps, None))))
    return -logL if np.isfinite(logL) else 1e10


def fit_meta_d(nR_S1, nR_S2, s=1.0):
    """Fit meta-d'. Returns dict with da, meta_da, M_ratio, M_diff, ca, logL."""
    nR_S1 = np.asarray(nR_S1, float).copy()
    nR_S2 = np.asarray(nR_S2, float).copy()
    n_ratings = len(nR_S1) // 2
    padded = bool((nR_S1 == 0).any() or (nR_S2 == 0).any())
    if padded:
        nR_S1 = nR_S1 + 1.0 / (2 * n_ratings)
        nR_S2 = nR_S2 + 1.0 / (2 * n_ratings)

    # --- type 1 ---
    tot_S1, tot_S2 = nR_S1.sum(), nR_S2.sum()
    HR, FAR = [], []
    for c in range(1, 2 * n_ratings):
        HR.append(nR_S2[c:].sum() / tot_S2)
        FAR.append(nR_S1[c:].sum() / tot_S1)
    i = n_ratings - 1
    d1 = (1 / s) * norm.ppf(HR[i]) - norm.ppf(FAR[i])
    c1 = (-1 / (1 + s)) * (norm.ppf(HR[i]) + norm.ppf(FAR[i]))
    if not np.isfinite(d1) or abs(d1) < 1e-6:
        return dict(da=np.nan, meta_da=np.nan, M_ratio=np.nan, M_diff=np.nan,
                    ca=np.nan, logL=np.nan, cells_padded=padded, n=int(tot_S1 + tot_S2))

    # --- start values: type-2 criteria spread around the type-1 criterion ---
    t2c_S1 = c1 - np.linspace(0.3, 1.2, n_ratings - 1)[::-1]
    t2c_S2 = c1 + np.linspace(0.3, 1.2, n_ratings - 1)
    x0 = np.concatenate(([d1], t2c_S1, t2c_S2))

    # The FULL criterion vector [t2c_S1 ..., 0, t2c_S2 ...] must be increasing.
    # Constraining monotonicity only inside each group lets the two groups cross
    # the type-1 criterion, at which point the likelihood degenerates and the
    # optimiser runs meta-d' off to +-1e7. This is the constraint set fmincon
    # gets in the original MATLAB via its linear inequality matrix.
    cons = []
    for k in range(1, n_ratings - 1):                       # within S1 block
        cons.append({"type": "ineq", "fun": (lambda p, k=k: p[k + 1] - p[k])})
    cons.append({"type": "ineq",                            # last S1 crit < 0
                 "fun": (lambda p: -p[n_ratings - 1] - 1e-4)})
    cons.append({"type": "ineq",                            # first S2 crit > 0
                 "fun": (lambda p: p[n_ratings] - 1e-4)})
    for k in range(1, n_ratings - 1):                       # within S2 block
        cons.append({"type": "ineq",
                     "fun": (lambda p, k=k: p[n_ratings + k] - p[n_ratings + k - 1])})
    bnds = [(-5.0, 5.0)] + [(-10.0, 10.0)] * (len(x0) - 1)

    best = None
    for jitter in (0.0, 0.5, -0.5):                         # a few restarts
        xs = x0.copy()
        xs[0] = np.clip(d1 + jitter, -5, 5)
        r = minimize(_logL, xs, args=(nR_S1, nR_S2, n_ratings, d1, c1, s),
                     method="SLSQP", bounds=bnds, constraints=cons,
                     options={"maxiter": 3000, "ftol": 1e-11})
        if np.isfinite(r.fun) and (best is None or r.fun < best.fun):
            best = r
    res = best
    meta_d1 = float(res.x[0])
    return dict(da=float(d1), meta_da=meta_d1, M_ratio=meta_d1 / d1,
                M_diff=meta_d1 - d1, ca=float(c1), logL=float(-res.fun),
                cells_padded=padded, n=int(tot_S1 + tot_S2), converged=bool(res.success))


# ---------------------------------------------------------------------------
def simulate(d1, c1, meta_d1, t2c_S1, t2c_S2, n_per_stim, rng):
    """Sample response x confidence counts from the meta-d' model itself.

    Type-1 responses follow d1 and c1. Within each response x correctness cell
    the confidence distribution is the one a d'=meta_d1 observer would produce.
    This is the generative side of `_logL`, so fitting it back is a genuine
    round trip rather than a test of some other noise model.
    """
    n_ratings = len(t2c_S1) + 1
    HR = 1 - norm.cdf(c1 - d1 / 2)
    FAR = 1 - norm.cdf(c1 + d1 / 2)

    S1mu, S2mu = -meta_d1 / 2, meta_d1 / 2
    shift = meta_d1 * (c1 / d1)
    S1mu -= shift
    S2mu -= shift
    bounds = np.concatenate(([-np.inf], t2c_S1, [0.0], t2c_S2, [np.inf]))
    C_rS1 = norm.cdf(0, S1mu, 1)
    I_rS1 = norm.cdf(0, S2mu, 1)
    C_rS2 = 1 - norm.cdf(0, S2mu, 1)
    I_rS2 = 1 - norm.cdf(0, S1mu, 1)
    prC_rS1 = np.diff(norm.cdf(bounds[:n_ratings + 1], S1mu, 1)) / C_rS1
    prI_rS1 = np.diff(norm.cdf(bounds[:n_ratings + 1], S2mu, 1)) / I_rS1
    prC_rS2 = np.diff(norm.cdf(bounds[n_ratings:], S2mu, 1)) / C_rS2
    prI_rS2 = np.diff(norm.cdf(bounds[n_ratings:], S1mu, 1)) / I_rS2

    nR_S1 = np.concatenate([rng.multinomial(round(n_per_stim * (1 - FAR)), prC_rS1),
                            rng.multinomial(round(n_per_stim * FAR), prI_rS2)]).astype(float)
    nR_S2 = np.concatenate([rng.multinomial(round(n_per_stim * (1 - HR)), prI_rS1),
                            rng.multinomial(round(n_per_stim * HR), prC_rS2)]).astype(float)
    return nR_S1, nR_S2


def _selfcheck():
    """Round-trip recovery from the model's own generative process.

    Run: python metad.py --check
    """
    rng = np.random.default_rng(7)
    d1, c1 = 1.40, 0.05
    t2c_S1 = np.array([-1.2, -0.7, -0.3])
    t2c_S2 = np.array([0.3, 0.7, 1.2])
    print("Round-trip: aus dem Modell simuliert, dann zurueckgefittet")
    print(f"{'wahr':>8}{'N/Stim':>8}{'geschaetzt':>12}{'d1 gefittet':>13}{'M-ratio':>9}")
    for meta_true in (1.40, 1.10, 0.80, 0.50):
        for n in (5000, 50):
            est = [fit_meta_d(*simulate(d1, c1, meta_true, t2c_S1, t2c_S2, n, rng))
                   for _ in (range(1) if n > 1000 else range(200))]
            mm = np.nanmean([e["meta_da"] for e in est])
            dd = np.nanmean([e["da"] for e in est])
            print(f"{meta_true:8.2f}{n:8d}{mm:12.3f}{dd:13.3f}{mm/dd:9.3f}")


def _cli(data_dir):
    import glob
    import pandas as pd
    files = sorted(f for f in glob.glob(f"{data_dir}/CDT_*.csv") if "kinematics" not in f)
    df = pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True)
    df["s"] = df.participant.astype(str).str.zfill(3)
    t = df[(df.phase.astype(str).str.startswith("test")) & (df.is_timeout != True)]
    med = t[t.actual_difficulty_level.eq("medium")].dropna(subset=["confidence_rating"])
    print(f"{'Proband':<9}{'Winkel':>7}{'n':>5}{'d1':>8}{'meta-d1':>9}{'M-ratio':>9}"
          f"{'M-diff':>8}   {'pad':>3}")
    out = []
    for s in sorted(med.s.unique()):
        for a in (0, 90):
            g = med[(med.s.eq(s)) & (med.angle_bias.eq(a))]
            if len(g) < 20:
                continue
            stim = (g.true_side == "right").astype(int).values
            resp = (g.resp_side == "right").astype(int).values
            conf = g.confidence_rating.astype(int).values
            f = fit_meta_d(*trials2counts(stim, resp, conf, 4))
            out.append(dict(s=s, angle=a, **f))
            print(f"{s:<9}{a:>7}{f['n']:>5}{f['da']:>8.3f}{f['meta_da']:>9.3f}"
                  f"{f['M_ratio']:>9.3f}{f['M_diff']:>8.3f}   {'ja' if f['cells_padded'] else '-':>3}")
    d = pd.DataFrame(out)
    if len(d):
        w = d.pivot(index="s", columns="angle", values="M_ratio")
        print("\nM-ratio 90 - 0 pro Proband:")
        print((w[90] - w[0]).round(3).to_string())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        _selfcheck()
    elif len(sys.argv) > 1:
        _cli(sys.argv[1])
    else:
        print(__doc__)
