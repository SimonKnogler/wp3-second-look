"""One-page DDM figure for the hypotheses: group-level drift/boundary per condition + cue effects vs. predictions.

    python fig_hypotheses.py <fit.nc> <prep_out_dir> <out.png>
"""
import sys
import numpy as np, pandas as pd, arviz as az
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

nc, prep, out = sys.argv[1:4]
post = az.from_netcdf(nc).posterior
C = {0: "#2a78d6", 90: "#eb6834"}; INK2, GRID = "#52514e", "#e1e0d9"
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"], "font.size": 8,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#c3c2b7",
                     "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": .6, "axes.axisbelow": True,
                     "figure.facecolor": "white", "axes.titleweight": "bold", "axes.titlesize": 9, "axes.titlelocation": "left"})
f = lambda n: post[n].values.ravel() if n in post else 0.0

def cell(par, cue, ang):  # group-level parameter in one condition (sum coding +-0.5)
    return f(f"{par}_Intercept") + f(f"{par}_cue") * cue + f(f"{par}_angle") * ang + f(f"{par}_cue:angle") * cue * ang

fig = plt.figure(figsize=(7.2, 5.4))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05], hspace=.55, wspace=.35)
for k, (par, name, what) in enumerate((("v", "Drift rate", "how clearly control is perceived"),
                                       ("a", "Boundary", "how much evidence before answering (caution)"))):
    ax = fig.add_subplot(gs[0, k])
    for ang, xa in ((0, -.5), (90, .5)):
        xs = np.array([0, 1]) + (-.04 if ang == 0 else .04)
        m, lo, hi = [], [], []
        for cue in (-.5, .5):
            s = cell(par, cue, xa); h = az.hdi(s, hdi_prob=.95); m.append(s.mean()); lo.append(h[0]); hi.append(h[1])
        ax.errorbar(xs, m, yerr=[np.array(m) - lo, np.array(hi) - m], fmt="o-", color=C[ang], lw=2, ms=6, mec="white", mew=.8,
                    capsize=0, label=f"{ang}° rotation")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Low-control cue", "High-control cue"]); ax.set_xlim(-.4, 1.4)
    ax.set_title(f"{'AB'[k]}  {name}", pad=14); ax.set_ylabel(name, color=INK2)
    ax.text(0, 1.02, what, transform=ax.transAxes, fontsize=7, color=INK2, va="bottom")
    if k == 0: ax.legend(frameon=False, loc="upper left")

# C: cue effects against what each hypothesis predicted
ax = fig.add_subplot(gs[1, :]); ax.grid(axis="x", color=GRID); ax.grid(axis="y", visible=False)
rows = [("v", 0, "Drift at 0°", "H1: should be clearly > 0"), ("v", 90, "Drift at 90°", "no prediction"),
        ("a", 0, "Boundary at 0°", "no prediction"), ("a", 90, "Boundary at 90°", "H2: should be clearly < 0")]
for j, (par, ang, lab, pred) in enumerate(rows):
    y = len(rows) - 1 - j; xa = -.5 if ang == 0 else .5
    eff = cell(par, .5, xa) - cell(par, -.5, xa)
    lo, hi = az.hdi(eff, hdi_prob=.95); l5, h5 = az.hdi(eff, hdi_prob=.5)
    ax.plot([lo, hi], [y, y], color=C[ang], lw=1.2); ax.plot([l5, h5], [y, y], color=C[ang], lw=4, solid_capstyle="butt")
    ax.plot(eff.mean(), y, "o", color=C[ang], ms=6, mec="white", mew=.8)
    if pred.startswith("H1"): ax.annotate("", xy=(.3, y), xytext=(.17, y), arrowprops=dict(arrowstyle="-|>", color="#9a9a9a", lw=1.2))
    if pred.startswith("H2"): ax.annotate("", xy=(-.3, y), xytext=(-.17, y), arrowprops=dict(arrowstyle="-|>", color="#9a9a9a", lw=1.2))
    ax.text(.36, y, f"{pred}", va="center", fontsize=7, color=INK2, transform=ax.get_yaxis_transform() if False else ax.transData)
ax.axvline(0, color="#777", lw=.9, ls="--")
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[2] for r in rows][::-1]); ax.set_xlim(-.36, .62)
ax.set_xlabel("Effect of the high-control cue (high − low).  Dot = best estimate, thick = 50 %, thin = 95 % credible interval.\n"
              "Grey arrows = direction the hypothesis predicted.", color=INK2, fontsize=7)
ax.set_title("C  What the cue changed, compared with the predictions")
fig.suptitle("Hierarchical drift-diffusion model, medium trials, N = %d" % post["t_participant_id"].shape[-1] if "t_participant_id" in post else "", x=.07, y=1.0, ha="left", fontsize=10, fontweight="bold")
fig.savefig(out, dpi=300, bbox_inches="tight"); fig.savefig(out.replace(".png", ".pdf"), bbox_inches="tight")
print("saved", out)
