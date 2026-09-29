"""Parameter recovery: simulate one data set from the fitted full model (real design: same
participants, trials per cell, per-participant parameters = posterior means), write it as a
prep dir, then refit with fit_hssm.py and compare the cue-effect contrasts.

    python recover.py <prep_out_dir> <fit_out_dir> <sim_prep_dir>          # step 1: simulate
    python fit_hssm.py <sim_prep_dir> <sim_fit_dir> --models full           # step 2: refit
    python recover.py <prep_out_dir> <fit_out_dir> <sim_prep_dir> --compare <sim_fit_dir>
"""
import sys, os, json, hashlib, argparse
import numpy as np, pandas as pd, arviz as az
def t_per_participant(post, pids, k=None):
    """per-participant non-decision time: unpooled t_participant_id if present, else hierarchical intercept + RE."""
    if "t_participant_id" in post:
        tp = post["t_participant_id"]; labs = [str(x) for x in tp.coords[tp.dims[-1]].values]
        arr = tp.values.reshape(-1, len(labs)); arr = arr[k] if k is not None else arr.mean(0)
        return arr[[labs.index(str(p_)) for p_ in pids]]
    return None

from ssms.basic_simulators.simulator import simulator

p = argparse.ArgumentParser(); p.add_argument("prep"); p.add_argument("fits"); p.add_argument("sim"); p.add_argument("--compare", default="")
p.add_argument("--trials", default="medium")
p.add_argument("--inject", default="", help="add hypothesised effects on top of the fitted ones, e.g. v0=0.15,a90=-0.15 (high-low cue effect on v at 0deg / on a at 90deg)")
a = p.parse_args()
INJ = {k: float(v) for k, v in (x.split("=") for x in a.inject.split(",") if x)}
sha = open(f"{a.prep}/ddm_trials.sha").read().strip()
d = pd.read_csv(f"{a.prep}/ddm_trials.csv", dtype={"participant_id": str})
if a.trials == "medium": d = d[d.difficulty == "medium"]
d = d.reset_index(drop=True)
post = az.from_netcdf(f"{a.fits}/{sha}/full_{a.trials}.nc").posterior
X = {"Intercept": np.ones(len(d)), "cue": d.cue.values, "angle": d.angle.values, "cue:angle": d.cue.values * d.angle.values}
da0 = post["v_1|participant_id"]; subs = [str(s) for s in da0.coords[da0.dims[-1]].values]; si = np.array([subs.index(s) for s in d.participant_id])

def trial_param(par):  # posterior-mean parameters per trial
    val = np.zeros(len(d))
    for term, x in X.items():
        fe = float(post[f"{par}_{term}"].mean()) if f"{par}_{term}" in post else 0.0
        ren = f"{par}_{'1' if term == 'Intercept' else term}|participant_id"
        re = post[ren].mean(("chain", "draw")).values[si] if ren in post else 0.0
        val += (fe + re) * x
    return val

if not a.compare:
    tt = t_per_participant(post, d.participant_id)
    tt = trial_param("t") if tt is None else tt + float(post["t_angle"].mean()) * d.angle.values
    vv, aa = trial_param("v"), trial_param("a")
    vv = vv + INJ.get("v0", 0) * d.cue.values * (d.angle.values < 0) + INJ.get("v90", 0) * d.cue.values * (d.angle.values > 0)
    aa = aa + INJ.get("a0", 0) * d.cue.values * (d.angle.values < 0) + INJ.get("a90", 0) * d.cue.values * (d.angle.values > 0)
    theta = np.column_stack([vv, aa, np.full(len(d), 0.5), np.clip(tt, 0.05, None)])
    o = simulator(model="ddm", theta=theta, n_samples=1, random_state=7)
    s = d.copy(); s["rt"] = o["rts"].ravel(); s["response"] = np.where(o["choices"].ravel() > 0, 1, -1)
    keep = (s.rt > 0.25) & (s.rt < 5.0)   # same deadline/censoring as the real data
    s = s[keep].reset_index(drop=True)
    os.makedirs(a.sim, exist_ok=True); s.to_csv(f"{a.sim}/ddm_trials.csv", index=False)
    open(f"{a.sim}/ddm_trials.sha", "w").write("sim_" + sha[:8] + ("_inj" if INJ else ""))
    truth = {}
    for par in ("v", "a"):
        c, i = float(post[f"{par}_cue"].mean()), float(post[f"{par}_cue:angle"].mean())
        e0, e90 = c - 0.5 * i + INJ.get(f"{par}0", 0), c + 0.5 * i + INJ.get(f"{par}90", 0)
        truth.update({f"{par} cue effect 0deg": e0, f"{par} cue effect 90deg": e90, f"{par} cue effect 90-0 (interaction)": e90 - e0})
    json.dump(dict(truth=truth, n_trials=int(len(s)), censored=int((~keep).sum())), open(f"{a.sim}/truth.json", "w"), indent=1)
    print(f"simulated {len(s)} trials ({(~keep).sum()} censored at 5 s) -> {a.sim}; generating contrasts:"); print(json.dumps(truth, indent=1))
else:
    truth = json.load(open(f"{a.sim}/truth.json"))["truth"]
    rp = az.from_netcdf(f"{a.compare}/{open(a.sim + '/ddm_trials.sha').read().strip()}/full_{a.trials}.nc").posterior
    rows = []
    for par in ("v", "a"):
        c, i = rp[f"{par}_cue"].values.ravel(), rp[f"{par}_cue:angle"].values.ravel()
        for lab, eff in (("0deg", c - 0.5 * i), ("90deg", c + 0.5 * i), ("90-0 (interaction)", i)):
            k = f"{par} cue effect {lab}"; lo, hi = az.hdi(eff, hdi_prob=0.95)
            rows.append(dict(contrast=k, generating=round(truth[k], 3), recovered_mean=round(float(eff.mean()), 3), hdi95=f"[{lo:+.3f}, {hi:+.3f}]", covered=bool(lo <= truth[k] <= hi)))
    t = pd.DataFrame(rows); print(t.to_markdown(index=False)); t.to_csv(f"{a.sim}/recovery.csv", index=False)
