"""Hierarchisches meta-d' (HMeta-d nach Fleming 2017), abhängigkeitsfrei.

    python hmetad.py <data_dir>

Warum hierarchisch: Einzelfits von meta-d' sind bei ~100 Trials pro Zelle so
verrauscht, dass die Schätzung fast nichts wert ist (SD ~0.4 bei einem Wert von
~0.6). Das hierarchische Modell schätzt Gruppen- und Einzelebene gemeinsam und
zieht instabile Einzelwerte zum Gruppenmittel — die Gruppenschätzung wird
dadurch erheblich präziser als der Mittelwert der Einzelfits.

Modell, wie in HMeta-d:

    log M_ic ~ Normal(mu_c, sigma)          M = meta-d' / d', c = Winkel
    meta-d'_ic = M_ic * d'_ic               d' und Kriterium aus Typ-1 fixiert
    Typ-2-Kriterien: pro Zelle frei

Interessierende Größe: mu_90 - mu_0 auf der log-M-Skala.

Umsetzung ohne MCMC: Für jede Zelle wird die Profil-Likelihood von log M auf
einem Gitter berechnet (Typ-2-Kriterien an jedem Gitterpunkt wegoptimiert).
Damit lassen sich die Einzelwerte exakt ausintegrieren, und die Posterior über
(mu_0, mu_90, sigma) ist nur noch dreidimensional — direkt auf einem Gitter
auswertbar. Kein Sampler, keine Konvergenzdiagnostik, reproduzierbar.

Priors: mu_c ~ Normal(0, 1) auf log-Skala (M = 1 ist ideal, also a priori
zentriert auf Effizienz 1), sigma ~ HalfNormal(0.5). Beide schwach informativ.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).parent))
from metad import _logL, trials2counts  # noqa: E402


def _type1(nR_S1, nR_S2, s=1.0):
    n_ratings = len(nR_S1) // 2
    tot1, tot2 = nR_S1.sum(), nR_S2.sum()
    i = n_ratings - 1
    HR = nR_S2[i + 1:].sum() / tot2
    FAR = nR_S1[i + 1:].sum() / tot1
    d1 = (1 / s) * norm.ppf(HR) - norm.ppf(FAR)
    c1 = (-1 / (1 + s)) * (norm.ppf(HR) + norm.ppf(FAR))
    return float(d1), float(c1)


def profile_loglik(nR_S1, nR_S2, meta_grid, s=1.0):
    """Profil-Log-Likelihood von meta-d' über ein Gitter; Kriterien wegoptimiert."""
    nR_S1 = np.asarray(nR_S1, float).copy()
    nR_S2 = np.asarray(nR_S2, float).copy()
    n_ratings = len(nR_S1) // 2
    if (nR_S1 == 0).any() or (nR_S2 == 0).any():
        nR_S1 = nR_S1 + 1.0 / (2 * n_ratings)
        nR_S2 = nR_S2 + 1.0 / (2 * n_ratings)
    d1, c1 = _type1(nR_S1, nR_S2, s)
    if not np.isfinite(d1) or abs(d1) < 1e-6:
        return None, np.nan, np.nan

    cons = []
    for k in range(1, n_ratings - 1):
        cons.append({"type": "ineq", "fun": (lambda p, k=k: p[k] - p[k - 1])})
    cons.append({"type": "ineq", "fun": (lambda p: -p[n_ratings - 2] - 1e-4)})
    cons.append({"type": "ineq", "fun": (lambda p: p[n_ratings - 1] - 1e-4)})
    for k in range(1, n_ratings - 1):
        cons.append({"type": "ineq",
                     "fun": (lambda p, k=k: p[n_ratings - 1 + k] - p[n_ratings - 2 + k])})
    bnds = [(-10.0, 10.0)] * (2 * (n_ratings - 1))
    x0 = np.concatenate([np.linspace(-1.4, -0.3, n_ratings - 1),
                         np.linspace(0.3, 1.4, n_ratings - 1)])

    out = np.empty(len(meta_grid))
    warm = x0.copy()
    for j, m in enumerate(meta_grid):
        r = minimize(lambda t: _logL(np.concatenate(([m], t)), nR_S1, nR_S2,
                                     n_ratings, d1, c1, s),
                     warm, method="SLSQP", bounds=bnds, constraints=cons,
                     options={"maxiter": 400, "ftol": 1e-9})
        out[j] = -r.fun
        if r.success:
            warm = r.x                       # warm start: Gitter ist glatt
    return out, d1, c1


# ---------------------------------------------------------------------------
def fit_hierarchical(cells, n_grid_m=55, n_grid_mu=61, n_grid_sig=25):
    """cells: Liste von dicts mit subject, cond, nR_S1, nR_S2.

    Gibt die Posterior über (mu_0, mu_90, sigma) und die geshrinkten
    Einzelschätzungen zurück.
    """
    logM = np.linspace(np.log(0.03), np.log(2.6), n_grid_m)
    per = []
    for c in cells:
        d1, c1 = _type1(np.asarray(c["nR_S1"], float) + 1e-9,
                        np.asarray(c["nR_S2"], float) + 1e-9)
        meta_grid = np.exp(logM) * d1
        ll, d1, c1 = profile_loglik(c["nR_S1"], c["nR_S2"], meta_grid)
        per.append(dict(**c, ll=ll, d1=d1, meta_grid=meta_grid))
        print(f"   Profil fertig: {c['subject']} · {c['cond']}°  d'={d1:.3f}")

    conds = sorted({c["cond"] for c in cells})
    mu_grid = np.linspace(np.log(0.05), np.log(1.8), n_grid_mu)
    sig_grid = np.linspace(0.05, 1.6, n_grid_sig)

    # Likelihood pro Zelle, marginalisiert über log M — als Funktion von (mu, sigma)
    # cellL[i][a, b] = sum_m exp(ll_m) * N(logM_m; mu_a, sig_b)
    cellL = []
    for p in per:
        if p["ll"] is None:
            cellL.append(None)
            continue
        w = np.exp(p["ll"] - np.nanmax(p["ll"]))
        w[~np.isfinite(w)] = 0.0
        M = np.zeros((len(mu_grid), len(sig_grid)))
        for a, mu in enumerate(mu_grid):
            for b, sg in enumerate(sig_grid):
                M[a, b] = np.sum(w * norm.pdf(logM, mu, sg))
        cellL.append(np.log(np.clip(M, 1e-300, None)))

    # Posterior über (mu_0, mu_90, sigma)
    logpost = np.zeros((len(mu_grid), len(mu_grid), len(sig_grid)))
    for p, L in zip(per, cellL):
        if L is None:
            continue
        if p["cond"] == conds[0]:
            logpost += L[:, None, :]
        else:
            logpost += L[None, :, :]
    logpost += norm.logpdf(mu_grid, 0, 1)[:, None, None]
    logpost += norm.logpdf(mu_grid, 0, 1)[None, :, None]
    logpost += norm.logpdf(sig_grid, 0, 0.5)[None, None, :]
    post = np.exp(logpost - logpost.max())
    post /= post.sum()

    return dict(mu_grid=mu_grid, sig_grid=sig_grid, post=post, per=per,
                conds=conds, logM=logM)


def summarise(fit):
    mu, sig, post = fit["mu_grid"], fit["sig_grid"], fit["post"]
    p0 = post.sum(axis=(1, 2))
    p90 = post.sum(axis=(0, 2))
    ps = post.sum(axis=(0, 1))

    def qs(grid, p, q=(.025, .5, .975)):
        c = np.cumsum(p / p.sum())
        return [float(np.interp(x, c, grid)) for x in q]

    # Posterior der Differenz
    pd_ = np.zeros(len(mu) * 2 - 1)
    dgrid = np.linspace(mu[0] - mu[-1], mu[-1] - mu[0], len(pd_))
    P2 = post.sum(axis=2)
    for a in range(len(mu)):
        for b in range(len(mu)):
            k = np.argmin(np.abs(dgrid - (mu[b] - mu[a])))
            pd_[k] += P2[a, b]
    pd_ /= pd_.sum()
    return dict(mu0=qs(mu, p0), mu90=qs(mu, p90), sigma=qs(sig, ps),
                diff=qs(dgrid, pd_), dgrid=dgrid, pdiff=pd_,
                p_gt0=float(pd_[dgrid > 0].sum()))


# ---------------------------------------------------------------------------
def load_cells(data_dir, min_trials=20):
    import glob
    import pandas as pd
    files = sorted(f for f in glob.glob(f"{data_dir}/CDT_*.csv") if "kinematics" not in f)
    df = pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True)
    df["s"] = df.participant.astype(str).str.zfill(3)
    t = df[(df.phase.astype(str).str.startswith("test")) & (df.is_timeout != True)]
    med = t[t.actual_difficulty_level.eq("medium")].dropna(subset=["confidence_rating"])
    cells = []
    for s in sorted(med.s.unique()):
        for a in (0, 90):
            g = med[(med.s.eq(s)) & (med.angle_bias.eq(a))]
            if len(g) < min_trials:
                continue
            stim = (g.true_side == "right").astype(int).values
            resp = (g.resp_side == "right").astype(int).values
            conf = g.confidence_rating.astype(int).values
            n1, n2 = trials2counts(stim, resp, conf, 4)
            cells.append(dict(subject=s, cond=a, nR_S1=n1, nR_S2=n2, n=len(g)))
    return cells


def main(data_dir):
    cells = load_cells(data_dir)
    print(f"Zellen: {len(cells)}  ({len({c['subject'] for c in cells})} Probanden)")
    fit = fit_hierarchical(cells)
    s = summarise(fit)
    e = np.exp
    print("\n=== Gruppenebene (log M-Ratio) ===")
    print(f"  mu(0°)    {s['mu0'][1]:+.3f}   95%-KI [{s['mu0'][0]:+.3f}, {s['mu0'][2]:+.3f}]"
          f"   -> M-Ratio {e(s['mu0'][1]):.3f} [{e(s['mu0'][0]):.3f}, {e(s['mu0'][2]):.3f}]")
    print(f"  mu(90°)   {s['mu90'][1]:+.3f}   95%-KI [{s['mu90'][0]:+.3f}, {s['mu90'][2]:+.3f}]"
          f"   -> M-Ratio {e(s['mu90'][1]):.3f} [{e(s['mu90'][0]):.3f}, {e(s['mu90'][2]):.3f}]")
    print(f"  sigma     {s['sigma'][1]:.3f}   95%-KI [{s['sigma'][0]:.3f}, {s['sigma'][2]:.3f}]")
    print("\n=== H2: mu(90°) - mu(0°) ===")
    print(f"  {s['diff'][1]:+.3f}   95%-KI [{s['diff'][0]:+.3f}, {s['diff'][2]:+.3f}]")
    print(f"  P(Differenz > 0) = {s['p_gt0']:.3f}")
    print("\n  (H2 sagt eine POSITIVE Differenz voraus: Metakognition besser bei 90°)")
    return fit, s


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print(__doc__)


# ---------------------------------------------------------------------------
#  Gepaarte Variante
# ---------------------------------------------------------------------------
def fit_paired(cells, n_grid=61):
    """Within-subject-Modell:

        log M_i,0  = a_i - delta/2
        log M_i,90 = a_i + delta/2
        a_i ~ Normal(mu, tau)

    Der Personenanteil a_i steht in beiden Bedingungen derselben Person und
    kuerzt sich aus der Differenz heraus. Das ungepaarte Modell (fit_hierarchical)
    schaetzt delta als Differenz zweier unabhaengig geschaetzter Gruppenmittel und
    traegt die gesamte Zwischen-Personen-Varianz mit — bei einem Design, in dem
    jede Person beide Bedingungen durchlaeuft, ist das verschenkte Praezision.
    """
    logM = np.linspace(np.log(0.03), np.log(2.6), 55)
    subj = sorted({c["subject"] for c in cells})
    curves = {}
    for c in cells:
        d1, _ = _type1(np.asarray(c["nR_S1"], float) + 1e-9,
                       np.asarray(c["nR_S2"], float) + 1e-9)
        ll, d1, _ = profile_loglik(c["nR_S1"], c["nR_S2"], np.exp(logM) * d1)
        if ll is None:
            continue
        w = np.exp(ll - np.nanmax(ll))
        w[~np.isfinite(w)] = 0.0
        curves[(c["subject"], c["cond"])] = w
        print(f"   Profil fertig: {c['subject']} · {c['cond']}°  d'={d1:.3f}")

    mu_g = np.linspace(np.log(0.08), np.log(1.6), n_grid)
    tau_g = np.linspace(0.05, 1.2, 21)
    dl_g = np.linspace(-1.6, 1.6, n_grid)
    a_g = logM                                   # Integrationsgitter fuer a_i

    logpost = np.zeros((len(mu_g), len(tau_g), len(dl_g)))
    for s in subj:
        if (s, 0) not in curves or (s, 90) not in curves:
            continue
        w0, w90 = curves[(s, 0)], curves[(s, 90)]
        # L(a, delta) = L0(a - d/2) * L90(a + d/2), interpoliert auf a_g
        L = np.empty((len(a_g), len(dl_g)))
        for k, d in enumerate(dl_g):
            L[:, k] = (np.interp(a_g - d / 2, logM, w0, left=0, right=0)
                       * np.interp(a_g + d / 2, logM, w90, left=0, right=0))
        for i, mu in enumerate(mu_g):
            for j, tau in enumerate(tau_g):
                pa = norm.pdf(a_g, mu, tau)
                logpost[i, j, :] += np.log(np.clip(L.T @ pa, 1e-300, None))
    logpost += norm.logpdf(mu_g, 0, 1)[:, None, None]
    logpost += norm.logpdf(tau_g, 0, 0.5)[None, :, None]
    logpost += norm.logpdf(dl_g, 0, 1)[None, None, :]
    post = np.exp(logpost - logpost.max())
    post /= post.sum()

    pd_ = post.sum(axis=(0, 1))
    c = np.cumsum(pd_ / pd_.sum())
    q = [float(np.interp(x, c, dl_g)) for x in (.025, .5, .975)]
    pmu = post.sum(axis=(1, 2)); cm = np.cumsum(pmu / pmu.sum())
    return dict(dgrid=dl_g, pdiff=pd_ / pd_.sum(), diff=q,
                p_gt0=float(pd_[dl_g > 0].sum() / pd_.sum()),
                mu=[float(np.interp(x, cm, mu_g)) for x in (.025, .5, .975)])
