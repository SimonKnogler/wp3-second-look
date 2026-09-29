"""Hierarchical DDM (HSSM) for the CDT expectation x rotation design.

    python fit_hssm.py <prep_out_dir> <fit_out_dir> [--models full,null,drift,bound,dissoc]
                       [--trials medium|all] [--draws 1000] [--tune 1000] [--chains 4] [--subset N]

Fits are cached under <fit_out_dir>/<data-hash>/<model>_<trials>.nc : adding participants
changes the hash -> everything refits; unchanged data -> nothing refits.
Accuracy coding (upper bound = correct), z fixed at 0.5, sum-coded cue/angle (+-0.5), so
  v cue effect at 0deg  = b_cue - 0.5*b_cue:angle      (H1: > 0)
  a cue effect at 90deg = b_cue + 0.5*b_cue:angle      (H2: < 0 = lower boundary)
"""
import sys, os, json, argparse, time
os.environ.setdefault("XLA_FLAGS", "--xla_force_host_platform_device_count=4")  # parallel chains on CPU
import numpy as np, pandas as pd, arviz as az
import hssm

p = argparse.ArgumentParser()
p.add_argument("prep"); p.add_argument("out")
p.add_argument("--models", default="full"); p.add_argument("--trials", default="medium")
p.add_argument("--draws", type=int, default=1000); p.add_argument("--tune", type=int, default=1000)
p.add_argument("--chains", type=int, default=4); p.add_argument("--subset", type=int, default=0)
p.add_argument("--sampler", default="numpyro")
p.add_argument("--re", default="intercept", help="intercept: (1|pid) on v and a, cue/angle effects group-level (HDDM default, group_only_regressors); slopes: (1+cue*angle|pid)")
a = p.parse_args()

sha = open(f"{a.prep}/ddm_trials.sha").read().strip()
out = f"{a.out}/{sha}"; os.makedirs(out, exist_ok=True)
d = pd.read_csv(f"{a.prep}/ddm_trials.csv", dtype={"participant_id": str})
if a.trials == "medium":
    d = d[d.difficulty == "medium"]
else:
    d["diff_c"] = d.difficulty.map({"hard": -1.0, "medium": 0.0, "easy": 1.0})
if a.subset:
    d = d[d.participant_id.isin(sorted(d.participant_id.unique(), key=int)[: a.subset])]
d = d.reset_index(drop=True)
print(f"hash {sha}  trials {len(d)}  participants {d.participant_id.nunique()}  models {a.models}")

RE = "(1 + cue * angle | participant_id)" if a.re == "slopes" else "(1 | participant_id)"
# t is NOT pooled: one independent non-decision time per participant (+ a common angle shift). Runs 1-2 with a
# hierarchical t never converged (R-hat up to 2.9): each participant's t is hard-bounded by their own fastest RT
# (0.68-1.39 s), and a group distribution over t has to satisfy all bounds at once. Hierarchy stays on v and a.
T_FORMULA = "t ~ 0 + participant_id + angle"
def spec(v, av, t=T_FORMULA):
    return [dict(name="v", formula=v, prior=PRI_V), dict(name="a", formula=av, prior=PRI_A), dict(name="t", formula=t, prior=PRI_T)]

# weakly informative priors on the natural scale (v: drift toward the correct bound; a: boundary; t: non-decision s)
sd = lambda s: dict(name="HalfNormal", sigma=s)
PRI_V = {"Intercept": dict(name="Normal", mu=1.0, sigma=1.0), "cue": dict(name="Normal", mu=0, sigma=0.5),
         "angle": dict(name="Normal", mu=0, sigma=0.5), "cue:angle": dict(name="Normal", mu=0, sigma=0.5),
         "1|participant_id": dict(name="Normal", mu=0, sigma=sd(0.5)), "cue|participant_id": dict(name="Normal", mu=0, sigma=sd(0.3)),
         "angle|participant_id": dict(name="Normal", mu=0, sigma=sd(0.3)), "cue:angle|participant_id": dict(name="Normal", mu=0, sigma=sd(0.3))}
PRI_A = {"Intercept": dict(name="Normal", mu=1.5, sigma=0.5), "cue": dict(name="Normal", mu=0, sigma=0.3),
         "angle": dict(name="Normal", mu=0, sigma=0.3), "cue:angle": dict(name="Normal", mu=0, sigma=0.3),
         "1|participant_id": dict(name="Normal", mu=0, sigma=sd(0.3)), "cue|participant_id": dict(name="Normal", mu=0, sigma=sd(0.2)),
         "angle|participant_id": dict(name="Normal", mu=0, sigma=sd(0.2)), "cue:angle|participant_id": dict(name="Normal", mu=0, sigma=sd(0.2))}
# run 1 (t RE sd 0.2): 307 divergences, ESS 7 on t — participants' minimum RTs span 0.68-1.39 s, so per-participant t
# needs room; the likelihood is hard-bounded at rt > t.
PRI_T = {"participant_id": dict(name="Normal", mu=0.8, sigma=0.4), "angle": dict(name="Normal", mu=0, sigma=0.2)}

MODELS = {
    "null":   spec("v ~ 1 + (1 | participant_id)", "a ~ 1 + (1 | participant_id)"),
    "drift":  spec(f"v ~ 1 + cue * angle + {RE}", "a ~ 1 + (1 | participant_id)"),
    "bound":  spec("v ~ 1 + (1 | participant_id)", f"a ~ 1 + cue * angle + {RE}"),
    "full":   spec(f"v ~ 1 + cue * angle + {RE}", f"a ~ 1 + cue * angle + {RE}"),
}
if a.trials == "all":  # difficulty enters drift additively (easy/hard are cue-congruent by design)
    for k in MODELS:
        MODELS[k][0]["formula"] = MODELS[k][0]["formula"].replace("v ~ 1 +", "v ~ 1 + diff_c +")
        MODELS[k][0]["prior"] = {**PRI_V, "diff_c": dict(name="Normal", mu=0.5, sigma=0.5)}

def prune(inc, cols):  # drop prior entries for terms not in a formula (HSSM errors otherwise)
    for s in inc:
        s["prior"] = {k: v for k, v in s["prior"].items() if (k == "Intercept" and "~ 0 +" not in s["formula"]) or (k != "Intercept" and k.split("|")[0] in s["formula"])}
    return inc

results = {}
for name in a.models.split(","):
    tag = f"{name}_{a.trials}" + ("" if a.re == "intercept" else "_slopes") + (f"_sub{a.subset}" if a.subset else "")
    nc = f"{out}/{tag}.nc"
    if os.path.exists(nc):
        print(f"[{tag}] cached"); idata = az.from_netcdf(nc)
    else:
        t0 = time.time()
        m = hssm.HSSM(data=d, model="ddm", loglik_kind="analytical", include=prune(MODELS[name], d.columns), z=0.5,
                      p_outlier=0.02, lapse=hssm.Prior("Uniform", lower=0.25, upper=5.0))
        idata = m.sample(sampler=a.sampler, chains=a.chains, draws=a.draws, tune=a.tune, target_accept=0.95,
                         idata_kwargs=dict(log_likelihood=True))
        az.to_netcdf(idata, nc); print(f"[{tag}] fitted in {(time.time()-t0)/60:.1f} min")
    s = az.summary(idata, kind="all")
    fixed = s.loc[[i for i in s.index if "|" not in i and "_sigma" not in i and "_offset" not in i]]
    fixed.to_csv(f"{out}/{tag}_fixed.csv"); s.to_csv(f"{out}/{tag}_summary_all.csv")
    diag = dict(max_rhat=float(s["r_hat"].max()), min_ess_bulk=float(s["ess_bulk"].min()),
                divergences=int(idata.sample_stats["diverging"].values.sum()))
    # hypothesis contrasts from the posterior
    post = idata.posterior; con = {}
    for par, hyp in (("v", "H1 drift: cue effect at 0deg > 0"), ("a", "H2 boundary: cue effect at 90deg < 0")):
        pre = f"{par}_"  # HSSM 0.3 prefixes every parameter, v included
        cue_n, int_n = f"{pre}cue", f"{pre}cue:angle"
        if cue_n not in post: continue
        c, i = post[cue_n].values.ravel(), post[int_n].values.ravel()
        for lab, eff in (("0deg", c - 0.5 * i), ("90deg", c + 0.5 * i), ("90-0 (interaction)", i)):
            con[f"{par} cue effect {lab}"] = dict(mean=float(eff.mean()), hdi95=[float(x) for x in az.hdi(eff, hdi_prob=0.95)],
                                                 p_gt0=float((eff > 0).mean()))
    try:
        loo = az.loo(idata); diag.update(elpd_loo=float(loo.elpd_loo), loo_se=float(loo.se), p_loo=float(loo.p_loo))
    except Exception as e:
        diag["loo_error"] = str(e)[:200]
    results[tag] = dict(diag=diag, contrasts=con, n_trials=len(d), n_participants=int(d.participant_id.nunique()))
    print(json.dumps(results[tag], indent=1))
    json.dump(results[tag], open(f"{out}/{tag}_results.json", "w"), indent=1)
print("FIT DONE")
