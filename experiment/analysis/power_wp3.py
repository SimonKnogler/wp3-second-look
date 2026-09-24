#!/usr/bin/env python3
"""power_wp3.py — is WP3's primary test feasible at a fixed N?

Monte Carlo over the COMPLETE pipeline, nothing approximated:
  * generative observer  = simulate_wp3.py  (staircase, psychometric function, choice bias,
                           bounded 9-point ratings), recalibrated to Rollwage et al. 2018
  * analysis             = fit_wp3_model.fit_participant, verbatim  (psychometric fit, Task-1
                           anchors, censored-Gaussian model fits, exclusion gates, weight bounds)

Primary test: paired t on log w_d, 0 deg vs 90 deg  (fit_wp3_model's "H2 (w_d only)"), for
  * the WEIGHT model  (w_c, w_d; the current primary)
  * the BOTH model    (b, w_c, w_d; adds the choice-bias intercept that Rollwage 2018 found
                       carries the individual differences — the recommended primary)

Generative truth (Rollwage 2018, Fig. 4B, moderates):
  * log w_d(90) ~ N(log 1.0, 0.30)     group updates ~optimally on disconfirmation
  * choice bias b ~ N(0.40, 0.30)      the mechanism that won Rollwage's model comparison
  * mode effect: log w_d(0) = log w_d(90) + D_i,  D_i ~ N(mu_delta, sd_delta^2)
        mu_delta = -0.20  <=>  w_d is 18 % lower under the predictive mapping
        sd_delta          =    TRUE between-person heterogeneity of that effect
  * baseline confidence and meta-sensitivity set so Task-1 group confidence ~ 70 % (his Fig. 4B)

Each participant is fitted independently of N, so a pool of P participants per condition is
fitted ONCE; power at any N follows from the pool analytically (noncentral t on the observable
paired effect size) and is checked by resampling subsets.

Usage:
  python power_wp3.py                  full run  (~20 min on 8 cores)
  python power_wp3.py --smoke          plumbing check, 2 tiny conditions
  python power_wp3.py --pool 400       faster, noisier
Outputs: analysis_output/power/{report.md, summary.csv, fits_<condition>.csv}
"""
import argparse, pathlib, sys, time, warnings
import numpy as np
import pandas as pd
from multiprocessing import Pool, cpu_count
from scipy.stats import nct, t as tdist
from scipy.optimize import brentq

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import simulate_wp3 as S          # noqa: E402
import fit_wp3_model as F         # noqa: E402

OUT = HERE.parent.parent / "analysis_output" / "power"

# Rollwage 2018 Fig. 4B, moderates: mean confidence (%) at evidence level 0 / 1 / 2.
# Read from the figure, treat as +-3.  The shape is what matters: shallow green, steep red.
ROLLWAGE = {"correct": (72, 75, 78), "incorrect": (67, 52, 40)}

PRE, META = 0.78, 0.22            # baseline log-odds confidence, meta-sensitivity -> Task-1 ~70 %, gap ~9 pts
ATTRITION = 0.13                  # careless / incomplete sessions, on top of the analysis gates
N_RECRUIT = (100, 130, 150, 200)  # 150 is the hard cap; 200 shown for reference only


# ── conditions ──────────────────────────────────────────────────────────────────

def conditions(pool_main, pool_extra):
    base = dict(sd_delta=0.30, b_mean=0.40, b_sd=0.30, b_shift0=0.0, noise=1.2, t1=30, t2=60, boost=1.2)
    C = []
    for mu in (0.0, -0.10, -0.20, -0.30, -0.40):
        C.append(dict(base, name=f"A_mu{mu:+.2f}", mu_delta=mu, pool=pool_main,
                      group="A  effect size  (sd_delta=0.30, b~N(.4,.3), split 30/60, noise 1.2)"))
    for sd in (0.15, 0.45):
        C.append(dict(base, name=f"B_sd{sd:.2f}", mu_delta=-0.20, sd_delta=sd, pool=pool_extra,
                      group="B  heterogeneity of the mode effect  (mu_delta=-0.20)"))
    C.append(dict(base, name="C_bshift", mu_delta=0.0, b_shift0=0.30, pool=pool_extra,
                  group="C  confound: mode effect on CHOICE BIAS only, w_d equal  (false-positive check)"))
    for t1, t2 in ((20, 70), (45, 45)):
        C.append(dict(base, name=f"D_split{t1}_{t2}", mu_delta=-0.20, t1=t1, t2=t2, pool=pool_extra,
                      group="D  Task-1 / Task-2 split, 90 trials per angle  (mu_delta=-0.20)"))
    for nz in (0.8, 1.6):
        C.append(dict(base, name=f"E_noise{nz:.1f}", mu_delta=-0.20, noise=nz, pool=pool_extra,
                      group="E  rating noise SD on the 9-point scale  (mu_delta=-0.20)"))
    # The task's +1.2-logit boost implies ~95 % accuracy for the high sample under a WP1-like
    # psychometric slope; Rollwage's high sample gave 80 %. Weaker boosts approach his spacing.
    for bo in (0.5, 0.8, 1.0):
        C.append(dict(base, name=f"F_boost{bo:.1f}", mu_delta=-0.20, boost=bo, pool=pool_extra,
                      group="F  evidence boost, logit(prop) for the high sample  (mu_delta=-0.20; task default 1.2)"))
    return C


def draw_pool(c, seed):
    rng = np.random.default_rng(seed)
    n = c["pool"]
    P = S.draw_participants(n, rng, 0.85, 0.85, 0.0)      # psychometric params, order; rest overwritten
    lw90 = rng.normal(0.0, 0.30, n)
    delta = rng.normal(c["mu_delta"], c["sd_delta"], n)
    P["wd90"] = np.exp(lw90)
    P["wd0"] = np.exp(lw90 + delta)
    wc = np.exp(rng.normal(np.log(0.9), 0.20, n))
    P["wc0"] = wc; P["wc90"] = wc
    b = rng.normal(c["b_mean"], c["b_sd"], n)
    P["b90"] = b; P["b0"] = b + c["b_shift0"]
    pre = rng.normal(PRE, 0.35, n)                          # no built-in baseline difference by angle
    P["pre0"] = pre; P["pre90"] = pre
    P["meta"] = np.clip(rng.normal(META, 0.12, n), 0.05, 1.0)
    P["noise"] = np.clip(rng.normal(c["noise"], 0.20, n), 0.4, 2.5)
    P["delta_true"] = delta
    return P


# ── one participant: simulate -> analyse (worker) ───────────────────────────────

def _work(args):
    pdict, seed, t1, t2, boost = args
    S.T1_N, S.T2_N, S.BOOST = t1, t2, boost                 # simulate_participant reads module globals
    rng = np.random.default_rng(seed)
    df = S.simulate_participant(pd.Series(pdict), rng, "psychopy", 0.02, 1)
    # mirror fit_wp3_model.load_dir's coercions exactly
    df["phase"] = df["phase"].astype(str)
    df["is_timeout"] = F._bool(df["is_timeout"])
    df["prop_high_clipped"] = F._bool(df["prop_high_clipped"])
    df["participant"] = df["participant"].astype(str)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rows = F.fit_participant(df)
    tk = df[df.phase.str.startswith("wp3_task") & df.wp3_confidence.notna()]
    cal = tk.groupby(["evidence_level", "accuracy"])["wp3_prob"].mean().to_dict()
    # accuracy the HIGH post-decision sample would yield if it were responded to (Rollwage: 80 %)
    hi = tk[tk.evidence_level == 2]
    t_of = {0.0: pdict["t0"], 90.0: pdict["t90"]}
    cal["acc_high"] = float(np.mean([S.p_correct(pp, t_of[a], pdict["slope"]) for pp, a in zip(hi.prop_post, hi.angle_bias)])) if len(hi) else np.nan
    cal["acc_low"] = float(np.mean([S.p_correct(pp, t_of[a], pdict["slope"]) for pp, a in zip(tk[tk.evidence_level == 1].prop_post, tk[tk.evidence_level == 1].angle_bias)])) if len(tk) else np.nan
    for r in rows:
        t1rows = tk[(tk.angle_bias == r["angle"]) & (tk.wp3_task == 1)]
        r.update(wd0_true=pdict["wd0"], wd90_true=pdict["wd90"], delta_true=pdict["delta_true"],
                 n_task1_incorrect=int((t1rows.accuracy == 0).sum()))
    return rows, cal


def run_condition(c, seed, procs):
    P = draw_pool(c, seed)
    tasks = [(P.iloc[i].to_dict(), seed * 100_000 + i, c["t1"], c["t2"], c["boost"]) for i in range(len(P))]
    t0 = time.time()
    with Pool(procs) as pool:
        out = pool.map(_work, tasks, chunksize=4)
    fits = pd.DataFrame([r for rr, _ in out for r in rr])
    return fits, [cl for _, cl in out], time.time() - t0


# ── power arithmetic ────────────────────────────────────────────────────────────

def power_paired(dz, n, alpha=0.05):
    """Two-sided paired t at effect size dz (mean/SD of the paired differences)."""
    if not np.isfinite(dz) or n < 3:
        return np.nan
    df = n - 1
    tc = tdist.ppf(1 - alpha / 2, df)
    ncp = dz * np.sqrt(n)
    return float(nct.sf(tc, df, ncp) + nct.cdf(-tc, df, ncp))


def dz_required(n, power=0.80):
    return brentq(lambda d: power_paired(d, n) - power, 1e-4, 5.0)


def n_eff(n_recruit, pass_rate):
    return int(round(n_recruit * (1 - ATTRITION) * pass_rate))


def summarise(c, fits, n_resample=2000, seed=0):
    ok = fits[fits["fail"] == ""].copy()
    ok["w_d_both"] = ok["w_d_both"].clip(0.05, 3.0)         # the bounds the fitter applies to w_d
    piv = lambda col: ok.pivot_table(index="participant", columns="angle", values=col).dropna()
    pass_rate = len(piv("w_d")) / c["pool"]                 # both angles survived the gates
    res = dict(name=c["name"], group=c["group"], pool=c["pool"], mu_delta=c["mu_delta"],
               sd_delta=c["sd_delta"], b_shift0=c["b_shift0"], noise=c["noise"], t1=c["t1"], t2=c["t2"],
               boost=c["boost"], pass_rate=pass_rate,
               pct_reduction_true=100 * (1 - np.exp(c["mu_delta"])),
               n_inc_task1=ok["n_task1_incorrect"].mean(), n_inc_task2=ok["n_task2_incorrect"].mean(),
               fail_counts=str(fits["fail"].value_counts().to_dict()),
               best_model=str(ok["best_model"].value_counts(normalize=True).round(2).to_dict()))
    dt = ok.drop_duplicates("participant")["delta_true"]
    res["dz_true"] = dt.mean() / dt.std(ddof=1) if dt.std(ddof=1) > 0 else np.inf
    for N in N_RECRUIT:
        res[f"neff_N{N}"] = n_eff(N, pass_rate)
    rng = np.random.default_rng(seed)
    for model, col in (("weight", "w_d"), ("both", "w_d_both")):
        for ang, tcol in ((0, "wd0_true"), (90, "wd90_true")):
            a = ok[ok.angle == ang]
            err = np.log(a[col]) - np.log(a[tcol])
            res[f"sdmeas_{model}_{ang}"] = float(err.std(ddof=1))
            res[f"recov_{model}_{ang}"] = float(np.corrcoef(np.log(a[col]), np.log(a[tcol]))[0, 1])
        w = piv(col)
        d = (np.log(w[0]) - np.log(w[90])).values
        sd = d.std(ddof=1)
        dz = d.mean() / sd if sd > 0 else np.nan
        res[f"mean_d_{model}"], res[f"sd_d_{model}"], res[f"dz_obs_{model}"] = float(d.mean()), float(sd), float(dz)
        for N in N_RECRUIT:
            res[f"power_{model}_N{N}"] = power_paired(dz, n_eff(N, pass_rate))
        ne = n_eff(150, pass_rate)
        hits = 0
        for _ in range(n_resample):
            s = rng.choice(d, ne, replace=ne > len(d))       # bootstrap only if the pool is too small (--smoke)
            tstat = s.mean() / (s.std(ddof=1) / np.sqrt(ne))
            hits += 2 * tdist.sf(abs(tstat), ne - 1) < 0.05
        res[f"power_emp_{model}_N150"] = hits / n_resample
        res[f"mde_logwd_{model}_N150"] = dz_required(ne) * sd         # smallest detectable |mu_delta|
        res[f"mde_pct_{model}_N150"] = 100 * (1 - np.exp(-res[f"mde_logwd_{model}_N150"]))
    return res


# ── reporting ───────────────────────────────────────────────────────────────────

def calibration_table(cals, boost):
    agg = pd.DataFrame(cals).mean()
    lines = ["| evidence level | correct: sim | Rollwage | incorrect: sim | Rollwage |", "|---|---|---|---|---|"]
    for lev in (0, 1, 2):
        c_ = agg.get((lev, 1.0), np.nan); i_ = agg.get((lev, 0.0), np.nan)
        lines.append(f"| {lev} | {c_:5.1f} % | {ROLLWAGE['correct'][lev]} % | {i_:5.1f} % | {ROLLWAGE['incorrect'][lev]} % |")
    lines += ["", f"Accuracy the post-decision samples would yield if responded to (boost = {boost} logit): "
              f"low **{100*agg['acc_low']:.0f} %** (Rollwage: ~71 %), high **{100*agg['acc_high']:.0f} %** (Rollwage: 80 %)."]
    return "\n".join(lines)


def fmt_power(p):
    return "  n/a " if not np.isfinite(p) else f"{p:5.2f}"


def report(rows, cal_md, elapsed, args):
    df = pd.DataFrame(rows)
    L = ["# WP3 power / feasibility — primary test: paired t on log w_d, 0° vs 90°", "",
         f"pool per condition: A = {args.pool}, B–E = {args.pool_extra} · attrition {ATTRITION:.0%} on top of the "
         f"analysis gates · α = .05 two-sided · runtime {elapsed/60:.1f} min on {args.procs} cores", "",
         "## 0. Does the simulator look like Rollwage 2018 (Fig. 4B)?", "",
         "Group-mean confidence at μ_Δ = 0. What must match is the *shape*: shallow rise on correct trials "
         "(ceiling), steep fall on incorrect trials.", "", cal_md, ""]
    for grp, g in df.groupby("group", sort=True):
        L += [f"## {grp}", ""]
        L += ["| condition | μ_Δ | true % ↓ w_d(0°) | σ_Δ | true d_z | pass | n_eff @150 | "
              "σ_meas w_d (weight / both) | obs d_z (weight / both) | power N=100 | N=130 | **N=150** | N=200 | emp. N=150 | MDE @150 (both) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in g.iterrows():
            sm = f"{r.sdmeas_weight_0:.2f} / {r.sdmeas_both_0:.2f}"
            dz = f"{r.dz_obs_weight:+.2f} / {r.dz_obs_both:+.2f}"
            pw = " | ".join(f"{fmt_power(r[f'power_weight_N{N}'])} / {fmt_power(r[f'power_both_N{N}'])}" for N in N_RECRUIT)
            L.append(f"| {r['name']} | {r.mu_delta:+.2f} | {r.pct_reduction_true:4.0f} % | {r.sd_delta:.2f} | "
                     f"{r.dz_true:+.2f} | {r.pass_rate:.2f} | {r.neff_N150} | {sm} | {dz} | {pw} | "
                     f"{r.power_emp_weight_N150:.2f} / {r.power_emp_both_N150:.2f} | "
                     f"{r.mde_logwd_both_N150:.2f} log = {r.mde_pct_both_N150:.0f} % |")
        L.append("")
        L.append("power cells are weight-model / both-model. At μ_Δ = 0 the 'power' column is the false-positive rate.")
        L.append("")
    a0 = df[df["name"] == "A_mu+0.00"].iloc[0]
    L += ["## Key quantities", "",
          f"- incorrect Task-2 trials per participant per angle (what identifies w_d): **{a0.n_inc_task2:.1f}**; "
          f"incorrect Task-1 trials (what anchors L0_incorrect): **{a0.n_inc_task1:.1f}**",
          f"- per-angle measurement SD of log w_d, weight model: {a0.sdmeas_weight_0:.2f} (0°) / {a0.sdmeas_weight_90:.2f} (90°); "
          f"both model: {a0.sdmeas_both_0:.2f} / {a0.sdmeas_both_90:.2f}",
          f"- recovery r(log fitted, log true) w_d, both model: {a0.recov_both_0:.2f} (0°) / {a0.recov_both_90:.2f} (90°)",
          f"- participants surviving both angles' gates: {a0.pass_rate:.0%}  →  150 recruited ≈ **{a0.neff_N150} paired**",
          f"- best model by BIC under Rollwage-like truth: {a0.best_model}",
          f"- exclusion reasons: {a0.fail_counts}", ""]
    return "\n".join(L), df


# ── main ────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", type=int, default=600, help="participants per condition, group A")
    ap.add_argument("--pool-extra", type=int, default=400, help="participants per condition, groups B–F")
    ap.add_argument("--procs", type=int, default=cpu_count())
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--only", nargs="*", help="condition names to run (default: all)")
    ap.add_argument("--smoke", action="store_true", help="2 tiny conditions, checks the plumbing")
    ap.add_argument("--out", help="output directory (default analysis_output/power)")
    args = ap.parse_args()
    global OUT
    if args.out:
        OUT = pathlib.Path(args.out)
    if args.smoke:
        args.pool = args.pool_extra = 24
    C = conditions(args.pool, args.pool_extra)
    if args.smoke:
        C = [c for c in C if c["name"] in ("A_mu+0.00", "A_mu-0.30")]
    if args.only:
        C = [c for c in C if c["name"] in set(args.only)]
    OUT.mkdir(parents=True, exist_ok=True)
    est = sum(c["pool"] for c in C) * 1.3 / args.procs / 60
    print(f"[power] {len(C)} conditions, {sum(c['pool'] for c in C)} participants, ~{est:.0f} min on {args.procs} cores\n")
    rows, cal_md, t_all = [], "", time.time()
    for i, c in enumerate(C, 1):
        fits, cals, dt = run_condition(c, args.seed + i, args.procs)
        fits.to_csv(OUT / f"fits_{c['name']}.csv", index=False)
        r = summarise(c, fits, n_resample=200 if args.smoke else 2000, seed=args.seed)
        rows.append(r)
        if c["name"] == "A_mu+0.00":
            cal_md = calibration_table(cals, c["boost"])
        if c["name"].startswith("F_boost"):
            cal_md += f"\n\nWith boost = {c['boost']}: " + calibration_table(cals, c["boost"]).split("\n")[-1]
        print(f"[{i:>2}/{len(C)}] {c['name']:<16} {dt/60:4.1f} min  pass={r['pass_rate']:.2f}  n_eff@150={r['neff_N150']:>3}  "
              f"σ_meas(both,0°)={r['sdmeas_both_0']:.2f}  obs d_z weight/both={r['dz_obs_weight']:+.2f}/{r['dz_obs_both']:+.2f}  "
              f"power@150 weight/both={fmt_power(r['power_weight_N150'])}/{fmt_power(r['power_both_N150'])}  "
              f"MDE@150(both)={r['mde_pct_both_N150']:.0f}%", flush=True)
    md, df = report(rows, cal_md or "_(A_mu+0.00 not run)_", time.time() - t_all, args)
    (OUT / "report.md").write_text(md)
    df.to_csv(OUT / "summary.csv", index=False)
    print("\n" + md)
    print(f"[out] {OUT}/report.md  summary.csv  fits_*.csv")


if __name__ == "__main__":
    main()
