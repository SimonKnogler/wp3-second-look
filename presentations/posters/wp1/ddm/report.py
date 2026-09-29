"""Tables + figures for the newest fit hash.

    python report.py <prep_out_dir> <fit_out_dir> <report_dir> [--trials medium] [--suffix _sub2]
"""
import sys, os, glob, json, argparse
import numpy as np, pandas as pd, arviz as az
def t_per_participant(post, pids, k=None):
    """per-participant non-decision time: unpooled t_participant_id if present, else hierarchical intercept + RE."""
    if "t_participant_id" in post:
        tp = post["t_participant_id"]; labs = [str(x) for x in tp.coords[tp.dims[-1]].values]
        arr = tp.values.reshape(-1, len(labs)); arr = arr[k] if k is not None else arr.mean(0)
        return arr[[labs.index(str(p_)) for p_ in pids]]
    return None

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

p = argparse.ArgumentParser(); p.add_argument("prep"); p.add_argument("fits"); p.add_argument("out")
p.add_argument("--trials", default="medium"); p.add_argument("--suffix", default="")
a = p.parse_args()
sha = open(f"{a.prep}/ddm_trials.sha").read().strip(); F = f"{a.fits}/{sha}"; os.makedirs(a.out, exist_ok=True)
d = pd.read_csv(f"{a.prep}/ddm_trials.csv", dtype={"participant_id": str})
if a.trials == "medium": d = d[d.difficulty == "medium"]
C = {0: "#2a78d6", 90: "#eb6834"}
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "white"})
lines = [f"# Hierarchical DDM (HSSM) — data hash {sha}, N = {d.participant_id.nunique()}, {len(d)} {a.trials} trials\n"]

# ---- model comparison + convergence
rows = []
for f in sorted(glob.glob(f"{F}/*_{a.trials}{a.suffix}_results.json")):
    r = json.load(open(f)); m = os.path.basename(f).split("_")[0]
    rows.append(dict(model=m, **{k: r["diag"].get(k) for k in ("elpd_loo", "loo_se", "p_loo", "max_rhat", "min_ess_bulk", "divergences")}))
cmp = pd.DataFrame(rows)
if len(cmp) and "elpd_loo" in cmp:
    cmp["d_elpd_vs_best"] = cmp.elpd_loo - cmp.elpd_loo.max(); cmp = cmp.sort_values("elpd_loo", ascending=False)
lines += ["## Model comparison (LOO-CV) and convergence\n", cmp.round(2).to_markdown(index=False), ""]

# ---- full model contrasts
full = f"{F}/full_{a.trials}{a.suffix}"
if os.path.exists(full + "_results.json"):
    idata = az.from_netcdf(full + ".nc"); post = idata.posterior
    con = {}
    for par in ("v", "a"):
        c, i = post[f"{par}_cue"].values.ravel(), post[f"{par}_cue:angle"].values.ravel()
        for lab, eff in (("0deg", c - 0.5 * i), ("90deg", c + 0.5 * i), ("90-0 (interaction)", i)):
            lo, hi = az.hdi(eff, hdi_prob=0.95)
            con[f"{par} cue effect {lab}"] = dict(mean=eff.mean(), sd=eff.std(), hdi95=f"[{lo:+.3f}, {hi:+.3f}]", p_gt0=(eff > 0).mean())
    ct = pd.DataFrame(con).T
    lines += ["## Full model: cue (high − low) effects from the posterior\n",
              "H1 predicts v cue effect 0deg > 0 (and > 90deg); H2 predicts a cue effect 90deg < 0 (and < 0deg).\n",
              ct.round(3).to_markdown(), ""]
    fx = pd.read_csv(full + "_fixed.csv", index_col=0)
    lines += ["## Full model: population-level parameters\n", fx.round(3).to_markdown(), ""]
    # forest of the simple effects
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.4))
    for k, (par, ttl, ylab) in enumerate((("v", "Drift rate", "cue effect on v"), ("a", "Boundary", "cue effect on a"))):
        pre = f"{par}_"
        c, i = post[f"{pre}cue"].values.ravel(), post[f"{pre}cue:angle"].values.ravel()
        for j, (ang, eff) in enumerate(((0, c - 0.5 * i), (90, c + 0.5 * i))):
            lo, hi = az.hdi(eff, hdi_prob=0.95); l50, h50 = az.hdi(eff, hdi_prob=0.5)
            ax[k].plot([lo, hi], [j, j], color=C[ang], lw=1); ax[k].plot([l50, h50], [j, j], color=C[ang], lw=3)
            ax[k].plot(eff.mean(), j, "o", color=C[ang], ms=5)
        ax[k].axvline(0, color="#999", lw=0.8, ls="--"); ax[k].set_yticks([0, 1]); ax[k].set_yticklabels(["0°", "90°"])
        ax[k].set_title(ttl, loc="left", fontweight="bold"); ax[k].set_xlabel(f"{ylab} (high − low), 95 % / 50 % HDI")
    fig.tight_layout(); fig.savefig(f"{a.out}/ddm_cue_effects.png", dpi=300); fig.savefig(f"{a.out}/ddm_cue_effects.pdf"); plt.close(fig)

    # per-participant condition means (v and a) from random effects
    def cond_param(par):
        pre = f"{par}_"
        da = post[f"{pre}1|participant_id"]; subs = list(da.coords[da.dims[-1]].values)
        out = {}
        for s_i, s in enumerate(subs):
            get = lambda n: (post[f"{pre}{n}"].values.ravel() if n == "Intercept" else 0) + (post[f"{pre}{n if n!='Intercept' else '1'}|participant_id"].values[..., s_i].ravel() if f"{pre}{n if n!='Intercept' else '1'}|participant_id" in post else 0) + (post[f"{pre}{n}"].values.ravel() if n != "Intercept" and f"{pre}{n}" in post else 0)
            b0, bc, ba, bi = get("Intercept"), get("cue"), get("angle"), get("cue:angle")
            for ang, xa in ((0, -0.5), (90, 0.5)):
                for cue, xc in (("low", -0.5), ("high", 0.5)):
                    out[(s, ang, cue)] = float((b0 + bc * xc + ba * xa + bi * xc * xa).mean())
        return pd.Series(out).unstack([1, 2])
    try:
        pv, pa = cond_param("v"), cond_param("a")
        fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.6))
        for k, (tab, ttl) in enumerate(((pv, "Drift rate v"), (pa, "Boundary a"))):
            for ang in (0, 90):
                x = np.array([0, 1]) + (0.03 if ang else -0.03)
                for s in tab.index: ax[k].plot(x, [tab.loc[s, (ang, "low")], tab.loc[s, (ang, "high")]], color=C[ang], alpha=0.25, lw=0.8)
                ax[k].plot(x, [tab[(ang, "low")].mean(), tab[(ang, "high")].mean()], "o-", color=C[ang], lw=2, label=f"{ang}° rotation")
            ax[k].set_xticks([0, 1]); ax[k].set_xticklabels(["Low-control cue", "High-control cue"]); ax[k].set_title(ttl, loc="left", fontweight="bold")
        ax[0].legend(frameon=False); fig.tight_layout(); fig.savefig(f"{a.out}/ddm_participant_params.png", dpi=300); plt.close(fig)
        pd.concat({"v": pv, "a": pa}, axis=1).round(3).to_csv(f"{a.out}/ddm_participant_condition_params.csv")
    except Exception as e:
        lines.append(f"(participant-level parameter plot skipped: {e})")

    # ---- posterior predictive check: simulate each trial from 100 posterior draws (ssms simulator), compare RT quantiles + accuracy per cell
    try:
        from ssms.basic_simulators.simulator import simulator
        rng = np.random.default_rng(1); nd = post.sizes["chain"] * post.sizes["draw"]; pick = rng.choice(nd, 100, replace=False)
        da0 = post["v_1|participant_id"]; fitted = [str(s) for s in da0.coords[da0.dims[-1]].values]
        dd = d[d.participant_id.astype(str).isin(fitted)].reset_index(drop=True); X = {"Intercept": np.ones(len(dd)), "cue": dd.cue.values, "angle": dd.angle.values, "cue:angle": dd.cue.values * dd.angle.values}
        def trial_param(par, k):
            da0 = post[f"{par}_1|participant_id"]; subs = [str(s) for s in da0.coords[da0.dims[-1]].values]; si = np.array([subs.index(str(s)) for s in dd.participant_id])
            val = np.zeros(len(dd))
            for term, x in X.items():
                fe = post[f"{par}_{term}"].values.ravel()[k] if f"{par}_{term}" in post else 0.0
                ren = f"{par}_{'1' if term == 'Intercept' else term}|participant_id"
                re = post[ren].values.reshape(nd, -1)[k][si] if ren in post else 0.0
                val += (fe + re) * x
            return val
        sims = []
        for k in pick:
            tt = t_per_participant(post, dd.participant_id, k)
            tt = trial_param("t", k) if tt is None else tt + post["t_angle"].values.ravel()[k] * dd.angle.values
            theta = np.column_stack([trial_param("v", k), trial_param("a", k), np.full(len(dd), 0.5), np.clip(tt, 0.05, None)])
            o = simulator(model="ddm", theta=theta, n_samples=1, random_state=int(k))
            sims.append(np.column_stack([o["rts"].ravel(), o["choices"].ravel()]))
        arr = np.stack(sims)  # draws x trials x (rt, choice in {-1,1})
        qs = [.1, .3, .5, .7, .9]; fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.8), sharey=True); ppc_rows = []
        for k, ang in enumerate((0, 90)):
            for cue, mk in (("low", "s"), ("high", "o")):
                idx = np.where((dd.angle_label.values == ang) & (dd.cue_label.values == cue))[0]
                obs_acc = (dd.response.values[idx] == 1).mean(); oq = np.quantile(dd.rt.values[idx], qs)
                sim_acc = (arr[:, idx, 1] > 0).mean(axis=1); sq = np.quantile(arr[:, idx, 0], qs, axis=1)
                ax[k].plot([obs_acc] * 5, oq, mk, color=C[ang], ms=5, mfc="white", label=f"{cue} cue: data")
                ax[k].errorbar(np.full(5, sim_acc.mean()), sq.mean(axis=1), yerr=[sq.mean(axis=1) - np.quantile(sq, .025, axis=1), np.quantile(sq, .975, axis=1) - sq.mean(axis=1)],
                               xerr=np.full(5, sim_acc.std() * 1.96), fmt=mk, color=C[ang], ms=3, alpha=.6, label=f"{cue} cue: model")
                ppc_rows.append(dict(angle=ang, cue=cue, acc_data=round(obs_acc, 3), acc_model=round(sim_acc.mean(), 3), **{f"q{int(q*100)}_data": round(o_, 2) for q, o_ in zip(qs, oq)}, **{f"q{int(q*100)}_model": round(s_, 2) for q, s_ in zip(qs, sq.mean(axis=1))}))
            ax[k].set_title(f"{ang}° rotation", loc="left", fontweight="bold"); ax[k].set_xlabel("proportion correct"); ax[k].set_ylim(0, 5.2)
        ax[0].set_ylabel("RT quantiles .1/.3/.5/.7/.9 (s)"); ax[0].legend(frameon=False, fontsize=6); fig.tight_layout(); fig.savefig(f"{a.out}/ddm_ppc.png", dpi=300); plt.close(fig)
        lines += ["## Posterior predictive check (group level, 100 draws)\n", pd.DataFrame(ppc_rows).to_markdown(index=False), "", "Figure: ddm_ppc.png (open = data, filled = model with 95 % interval). Note the 5-s deadline truncates the data but not the simulation.\n"]
    except Exception as e:
        import traceback; lines.append(f"(PPC skipped: {traceback.format_exc()[-400:]})")

open(f"{a.out}/ddm_report.md", "w").write("\n".join(lines)); print("\n".join(lines))
