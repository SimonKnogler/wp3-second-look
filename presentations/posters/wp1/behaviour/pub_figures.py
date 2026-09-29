"""Publication figures for CDT WP1 (included sample).

    python pub_figures.py <data_dir> <out_dir> [metad.json]

Writes fig2..fig6 + figS1 as PDF (vector, fonts embedded) and 300-dpi PNG, plus
stats.md with every number the figures show. Encoding is identical in every
figure: colour = rotation (0° blue, 90° orange), x = cue or difficulty. Error
bars are 95 % within-subject CIs (Cousineau-Morey) unless stated otherwise.
"""
import sys, glob, json, os
import numpy as np, pandas as pd
from scipy import stats
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.transforms as mtrans
from matplotlib.lines import Line2D

DATA, OUT = sys.argv[1], sys.argv[2]
METAD = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(OUT, exist_ok=True)

C = {0: "#2a78d6", 90: "#eb6834"}          # validated: CVD dE 24.7 on white
INK, INK2, MUTED, GRID, BASE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
V2 = {"14"}                                 # ran design v2 (cue runs); all others v1

mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 8, "axes.titlesize": 9, "axes.titleweight": "bold", "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5,
    "axes.edgecolor": BASE, "axes.labelcolor": INK2, "axes.linewidth": 0.8,
    "xtick.color": BASE, "ytick.color": BASE, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "legend.frameon": False, "axes.titlecolor": INK,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "pdf.fonttype": 42, "svg.fonttype": "none", "savefig.bbox": "tight",
})

# ---------------------------------------------------------------- data
files = sorted(f for f in glob.glob(f"{DATA}/CDT_*.csv") if "kinematics" not in f)
df = pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True)
df = df[df.phase.notna()].copy()
df["subj"] = df.participant.astype(str)
df["ph"] = (df.phase.astype(str).str.replace(r"_-?\d+$", "", regex=True)
            .str.replace("_interleaved", "", regex=False))
df["to"] = df.is_timeout.astype(str).eq("True")
ok = df[~df.to]
test, learn, cal = ok[ok.ph.eq("test")], ok[ok.ph.eq("learning")], ok[ok.ph.eq("calibration")]
med = test[test.actual_difficulty_level.eq("medium")]
SUBJ = sorted(df.subj.unique(), key=int)
N = len(SUBJ)
ANG, CUES, DIFF = [0, 90], ["low", "high"], ["hard", "medium", "easy"]
S = [f"# Figure statistics (N = {N}; v2: {', '.join('P' + s for s in sorted(V2 & set(SUBJ)))})\n"]


def save(fig, name):
    fig.savefig(f"{OUT}/{name}.pdf")
    fig.savefig(f"{OUT}/{name}.png", dpi=300)
    plt.close(fig)


def wide(d, dv, factor, levels):
    w = d.groupby(["subj", "angle_bias", factor])[dv].mean().unstack(["angle_bias", factor])
    return w[[(a, l) for a in ANG for l in levels]]


def morey(w):
    """Cousineau-Morey 95 % within-subject CI for each column of a subj x cell frame."""
    w = w.dropna()
    n, k = w.shape
    norm = w.sub(w.mean(axis=1), axis=0) + w.values.mean()
    half = norm.std(ddof=1) / np.sqrt(n) * np.sqrt(k / (k - 1)) * stats.t.ppf(.975, n - 1)
    return w.mean(), half


def letter(ax, s):
    ax.text(-0.2, 1.04, s, transform=ax.transAxes, fontsize=11, fontweight="bold",
            color=INK, va="bottom", ha="left")


def refline(ax, y, label, *_):
    """Reference line with its label in the right margin, so it never covers data."""
    ax.axhline(y, color=MUTED, lw=0.8, zorder=0)
    tr = mtrans.blended_transform_factory(ax.transAxes, ax.transData)
    ax.text(1.01, y, label, transform=tr, color=INK2, fontsize=6.5, ha="left", va="center", clip_on=False)


def two_by(ax, w, levels, ticklabels, ylabel, title, legend=False):
    """Levels on x, one line per rotation; faint lines = individual participants."""
    m, h = morey(w)
    x = np.arange(len(levels))
    off = {0: -0.07, 90: 0.07}
    for a in ANG:
        cols = [(a, l) for l in levels]
        for _, row in w[cols].iterrows():
            ax.plot(x + off[a], row.values, color=C[a], alpha=0.22, lw=0.7, zorder=1)
        ax.errorbar(x + off[a], m[cols].values, yerr=h[cols].values, color=C[a], lw=1.6,
                    marker="o", ms=5.5, mec="white", mew=1.0, elinewidth=1.6, capsize=0,
                    zorder=3, label=f"{a}° rotation")
    ax.set_xticks(x)
    ax.set_xticklabels(ticklabels)
    ax.set_xlim(-0.4, len(levels) - 0.6)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left")
    if legend:
        ax.legend(handles=[Line2D([], [], color=C[a], lw=1.6, marker="o", ms=5.5, mew=0,
                                  label=f"{a}° rotation") for a in ANG],
                  loc="upper left", handlelength=1.6)
    return m, h


def log_cells(title, m, h, fmt="{:.3f}"):
    S.append(f"\n## {title}\n")
    for (a, l), v in m.items():
        S.append(f"- {a}° / {l}: {fmt.format(v)} ± {fmt.format(h[(a, l)])} (95 % within-CI)")


# ================================================================ Fig 2
fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.5))
m, h = two_by(ax[0], wide(med, "accuracy", "cue_difficulty_prediction", CUES), CUES,
              ["Low-control cue", "High-control cue"], "Proportion correct",
              "Calibration held", legend=True)
refline(ax[0], 0.707, "target\n70.7 %")
ax[0].set_ylim(0.5, 0.9)
log_cells("Fig 2A — medium-trial accuracy", m, h)

m, h = two_by(ax[1], wide(learn, "accuracy", "cue_difficulty_prediction", CUES), CUES,
              ["Low-control cue", "High-control cue"], "Proportion correct",
              "Cue learning")
refline(ax[1], 0.5, "chance", 1.35)
ax[1].set_ylim(0.2, 1.02)
log_cells("Fig 2B — learning-phase accuracy", m, h)

m, h = two_by(ax[2], wide(test, "accuracy", "actual_difficulty_level", DIFF), DIFF,
              ["Hard", "Medium", "Easy"], "Proportion correct", "Difficulty levels (test)")
refline(ax[2], 0.5, "chance", 2.35)
ax[2].set_ylim(0.3, 1.02)
log_cells("Fig 2C — test accuracy by difficulty", m, h)
for a_, l in zip(ax, "ABC"):
    letter(a_, l)
fig.tight_layout(w_pad=2.2)
save(fig, "fig2_manipulation_checks")

# ================================================================ Fig 3
fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.6))
specs = [("agency_rating", "Agency rating (1–7)", "Sense of agency"),
         ("confidence_rating", "Confidence (1–4)", "Confidence"),
         ("accuracy", "Proportion correct", "Accuracy")]
for i, (dv, yl, tt) in enumerate(specs):
    m, h = two_by(ax[i], wide(med, dv, "cue_difficulty_prediction", CUES), CUES,
                  ["Low-control cue", "High-control cue"], yl, tt, legend=(i == 0))
    log_cells(f"Fig 3{'ABC'[i]} — medium trials, {dv}", m, h)
    letter(ax[i], "ABC"[i])
ax[2].set_ylim(0.5, 0.9)
fig.tight_layout(w_pad=2.2)
save(fig, "fig3_expectation_by_rotation")

# ================================================================ Fig 4
fig, ax = plt.subplots(1, 2, figsize=(5.0, 2.7))
S.append("\n## Fig 4 — cue effect (high − low) per participant, medium trials\n")
for i, (dv, lab) in enumerate([("agency_rating", "Agency"), ("confidence_rating", "Confidence")]):
    w = wide(med, dv, "cue_difficulty_prediction", CUES)
    d = pd.DataFrame({a: w[(a, "high")] - w[(a, "low")] for a in ANG})
    a_ = ax[i]
    for s, row in d.iterrows():
        a_.plot([0, 1], row.values, color=BASE, lw=0.8, zorder=1)
        for j, a in enumerate(ANG):
            hollow = s in V2
            a_.plot(j, row[a], "o", ms=5, zorder=2, mec=C[a] if hollow else "white",
                    mfc="white" if hollow else C[a], mew=1.2 if hollow else 0.8)
    for j, a in enumerate(ANG):
        mu, se = d[a].mean(), d[a].sem()
        half = se * stats.t.ppf(.975, len(d) - 1)
        a_.errorbar(j + 0.22, mu, yerr=half, color=C[a], marker="o", ms=6.5, mec="white",
                    mew=1.0, elinewidth=1.8, capsize=0, zorder=3)
        tt = stats.ttest_1samp(d[a], 0)
        S.append(f"- {lab} {a}°: M = {mu:+.3f}, 95 % CI [{mu - half:+.3f}, {mu + half:+.3f}], "
                 f"t({len(d) - 1}) = {tt.statistic:.2f}, p = {tt.pvalue:.4f}, dz = {mu / d[a].std(ddof=1):.2f}")
    diff = d[90] - d[0]
    tt = stats.ttest_1samp(diff, 0)
    S.append(f"- {lab} 90° − 0° (interaction): M = {diff.mean():+.3f}, t({len(diff) - 1}) = "
             f"{tt.statistic:.2f}, p = {tt.pvalue:.4f}, dz = {diff.mean() / diff.std(ddof=1):.2f}, "
             f"{int((diff > 0).sum())}/{len(diff)} participants larger at 90°")
    a_.axhline(0, color=MUTED, lw=0.8, zorder=0)
    a_.set_xticks([0, 1]); a_.set_xticklabels(["0°", "90°"])
    a_.set_xlim(-0.35, 1.5)
    a_.set_xlabel("Rotation")
    a_.set_ylabel(f"{lab}: high − low cue")
    a_.set_title(lab, loc="left")
    a_.text(0.98, 0.03, f"90° > 0° in {int((diff > 0).sum())}/{len(diff)}", transform=a_.transAxes,
            ha="right", va="bottom", fontsize=6.5, color=INK2)
    letter(a_, "AB"[i])
ax[1].legend(handles=[Line2D([], [], marker="o", ls="", mfc=MUTED, mec="white", ms=5, label="Design v1"),
                      Line2D([], [], marker="o", ls="", mfc="white", mec=MUTED, mew=1.2, ms=5, label="Design v2")],
             loc="upper left", handletextpad=0.3)
fig.tight_layout(w_pad=2.4)
save(fig, "fig4_cue_effect_per_participant")

from statsmodels.stats.anova import AnovaRM
S.append("\n## 2x2 repeated-measures ANOVA (analysis plan of the proposal), medium trials\n")
mm = med.copy(); mm["angle"] = mm.angle_bias.astype(int).astype(str)
for dv in ("agency_rating", "confidence_rating", "accuracy"):
    agg = mm.groupby(["subj", "cue_difficulty_prediction", "angle"], as_index=False)[dv].mean()
    tab = AnovaRM(agg, dv, "subj", within=["cue_difficulty_prediction", "angle"]).fit().anova_table
    for eff, row in tab.iterrows():
        eta = row["F Value"] / (row["F Value"] + row["Den DF"])
        S.append(f"- {dv} · {eff.replace('cue_difficulty_prediction', 'cue')}: F({row['Num DF']:.0f},{row['Den DF']:.0f}) = "
                 f"{row['F Value']:.2f}, p = {row['Pr > F']:.4f}, partial eta2 = {eta:.2f}")

# ================================================================ Fig 5
# P3 as operationalised in behavioral_analysis.py, next to two benchmarks that
# carry no expectation: the same slopes in accuracy, and the objective control step.
def slopes(dv):
    g = test.groupby(["subj", "angle_bias", "cue_difficulty_prediction", "actual_difficulty_level"])[dv].mean()
    out = []
    for s in SUBJ:
        for a in ANG:
            try:
                hv = g[(s, a, "high", "easy")] - g[(s, a, "high", "medium")]
                lv = g[(s, a, "low", "medium")] - g[(s, a, "low", "hard")]
            except KeyError:
                continue
            out.append(dict(subj=s, angle_bias=a, high=hv, low=lv))
    return pd.DataFrame(out)

fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.6))
S.append("\n## Fig 5 — violation slopes (P3) and stimulus benchmarks\n")
for i, (dv, yl, tt) in enumerate([("agency_rating", "Δ agency rating", "Agency (P3 contrast)"),
                                  ("accuracy", "Δ proportion correct", "Accuracy (stimulus benchmark)"),
                                  ("prop_used", "Δ proportion of self-motion", "Objective control step")]):
    sl = slopes(dv)
    w = sl.pivot(index="subj", columns="angle_bias", values=["high", "low"])
    w = w.swaplevel(axis=1)[[(a, l) for a in ANG for l in ("high", "low")]]
    m, h = two_by(ax[i], w, ["high", "low"], ["High cue:\neasy − medium", "Low cue:\nmedium − hard"],
                  yl, tt, legend=(i == 0))
    ax[i].axhline(0, color=MUTED, lw=0.8, zorder=0)
    asym = {a: (w[(a, "high")] - w[(a, "low")]) for a in ANG}
    for a in ANG:
        t_ = stats.ttest_1samp(asym[a], 0)
        S.append(f"- {tt} {a}°: high-cue step {m[(a, 'high')]:.3f}, low-cue step {m[(a, 'low')]:.3f}, "
                 f"asymmetry {asym[a].mean():+.3f}, t = {t_.statistic:.2f}, p = {t_.pvalue:.4f}")
    letter(ax[i], "ABC"[i])
fig.tight_layout(w_pad=2.2)
save(fig, "fig5_violation_asymmetry")

# ================================================================ Fig 6
if METAD and os.path.exists(METAD):
    R = json.load(open(METAD))
    ind = pd.DataFrame(R["indiv"])
    ind["M"] = np.exp(ind.logM_shrunk)
    s_ = R["summary"]
    fig, ax = plt.subplots(1, 2, figsize=(5.4, 2.6), gridspec_kw=dict(width_ratios=[1, 1.25]))
    pv = ind.pivot(index="subject", columns="cond", values="M")
    for _, row in pv.iterrows():
        ax[0].plot([0, 1], [row[0], row[90]], color=BASE, lw=0.8, zorder=1)
    for j, a in enumerate(ANG):
        ax[0].plot(np.full(len(pv), j), pv[a], "o", ms=4.5, color=C[a], mec="white", mew=0.8, zorder=2)
        q = s_["mu0"] if a == 0 else s_["mu90"]
        e = np.exp(q)
        ax[0].errorbar(j + 0.22, e[1], yerr=[[e[1] - e[0]], [e[2] - e[1]]], color=C[a], marker="o",
                       ms=6.5, mec="white", mew=1.0, elinewidth=1.8, capsize=0, zorder=3)
    refline(ax[0], 1.0, "ideal")
    ax[0].set_ylim(0.5, 1.06)
    ax[0].set_xticks([0, 1]); ax[0].set_xticklabels(["0°", "90°"]); ax[0].set_xlim(-0.35, 1.5)
    ax[0].set_xlabel("Rotation"); ax[0].set_ylabel("M-ratio (meta-d′ / d′)")
    ax[0].set_title("Metacognitive efficiency", loc="left")
    p = R["paired"]
    dg, pdens = np.array(p["dgrid"]), np.array(p["pdiff"])
    pdens = pdens / np.trapz(pdens, dg)
    lo, md, hi = p["diff"]
    ax[1].fill_between(dg, pdens, color=INK2, alpha=0.12, lw=0)
    inside = (dg >= lo) & (dg <= hi)
    ax[1].fill_between(dg[inside], pdens[inside], color=INK2, alpha=0.22, lw=0)
    ax[1].plot(dg, pdens, color=INK2, lw=1.4)
    ax[1].axvline(0, color=MUTED, lw=0.8)
    ax[1].set_xlim(-1.2, 1.2); ax[1].set_ylim(bottom=0)
    ax[1].grid(False)
    ax[1].set_xlabel("Δ log M-ratio (90° − 0°)"); ax[1].set_ylabel("Posterior density")
    ax[1].set_title("Within-participant difference", loc="left")
    ax[1].text(0.98, 0.95, f"median {md:+.2f}\n95 % CrI [{lo:+.2f}, {hi:+.2f}]\nP(Δ > 0) = {p['p_gt0']:.2f}",
               transform=ax[1].transAxes, ha="right", va="top", fontsize=6.5, color=INK2)
    letter(ax[0], "A"); letter(ax[1], "B")
    fig.tight_layout(w_pad=2.4)
    save(fig, "fig6_metacognition")
    S.append("\n## Fig 6 — hierarchical meta-d′\n")
    S.append(f"- M-ratio 0°: {np.exp(s_['mu0'][1]):.3f} [{np.exp(s_['mu0'][0]):.3f}, {np.exp(s_['mu0'][2]):.3f}]")
    S.append(f"- M-ratio 90°: {np.exp(s_['mu90'][1]):.3f} [{np.exp(s_['mu90'][0]):.3f}, {np.exp(s_['mu90'][2]):.3f}]")
    S.append(f"- unpaired Δ log M: {s_['diff'][1]:+.3f} [{s_['diff'][0]:+.3f}, {s_['diff'][2]:+.3f}], P(>0) = {s_['p_gt0']:.3f}")
    S.append(f"- paired Δ log M: {md:+.3f} [{lo:+.3f}, {hi:+.3f}], P(>0) = {p['p_gt0']:.3f}")
else:
    S.append("\n## Fig 6 — skipped (no meta-d′ results file)\n")

# ================================================================ Fig S1
fig, ax = plt.subplots(1, 2, figsize=(5.0, 2.6))
m, h = two_by(ax[0], wide(med, "rt_choice", "cue_difficulty_prediction", CUES), CUES,
              ["Low-control cue", "High-control cue"], "Response time (s)", "RT, medium trials", legend=True)
log_cells("Fig S1A — medium-trial RT", m, h)
letter(ax[0], "A")
c = cal.dropna(subset=["staircase_threshold"])
thr = c.groupby(["subj", "angle_bias"]).staircase_threshold.last().unstack()
for _, row in thr.iterrows():
    ax[1].plot([0, 1], [row[0], row[90]], color=BASE, lw=0.8, zorder=1)
for j, a in enumerate(ANG):
    ax[1].plot(np.full(len(thr), j), thr[a], "o", ms=4.5, color=C[a], mec="white", mew=0.8, zorder=2)
    mu, half = thr[a].mean(), thr[a].sem() * stats.t.ppf(.975, len(thr) - 1)
    ax[1].errorbar(j + 0.22, mu, yerr=half, color=C[a], marker="o", ms=6.5, mec="white", mew=1,
                   elinewidth=1.8, capsize=0, zorder=3)
    S.append(f"- Threshold {a}°: M = {mu:.3f} ± {half:.3f}")
ax[1].set_xticks([0, 1]); ax[1].set_xticklabels(["0°", "90°"]); ax[1].set_xlim(-0.35, 1.5)
ax[1].set_xlabel("Rotation"); ax[1].set_ylabel("Proportion of self-motion")
ax[1].set_title("Calibrated threshold", loc="left")
letter(ax[1], "B")
fig.tight_layout(w_pad=2.4)
save(fig, "figS1_rt_and_thresholds")

open(f"{OUT}/stats.md", "w").write("\n".join(S) + "\n")
print("\n".join(S))
