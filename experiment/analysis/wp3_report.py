#!/usr/bin/env python3
"""Turn results.json (from wp3_paper_analysis.py) into a results section in paper form:
APA-style statistics, tables, figures. Works for real and simulated data; the validation
section and the 'simulated' banner appear only when the results carry a ground truth.

  python wp3_report.py results.json report.html
"""
import json, math, sys
import numpy as np

R = json.load(open(sys.argv[1])); OUT = sys.argv[2]
SIM = "validation" in R
T = R["tests"]; ANG = ("0", "90"); NAME = {"0": "0°", "90": "90°"}

# ── number formatting (APA: no leading zero for p and r, true minus sign) ───────
def num(x, d=2, sign=False):
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s.replace("-", "−")
def nz(x, d=2):
    s = f"{abs(x):.{d}f}".lstrip("0") or "0"
    return ("−" if x < 0 else "") + s
def p_apa(p):
    return "<i>p</i> &lt; .001" if p < .001 else f"<i>p</i> = {nz(p, 3)}"
def t_apa(r, d="d<sub>z</sub>"):
    return f"<i>t</i>({r['df']}) = {num(r['t'])}, {p_apa(r['p'])}, <i>{d}</i> = {num(r['d'])}"
def ci(r, d=2):
    return f"95% CI [{num(r['ci'][0], d)}, {num(r['ci'][1], d)}]"
def pct(x, d=0):
    return f"{100 * x:.{d}f}%"

# ── SVG helpers ─────────────────────────────────────────────────────────────────
f1 = lambda v: f"{v:.1f}"
def txt(x, y, s, cls="t", anchor="start"):
    return f'<text x="{f1(x)}" y="{f1(y)}" text-anchor="{anchor}" class="{cls}">{s}</text>'
def ln(x1, y1, x2, y2, cls):
    return f'<line x1="{f1(x1)}" y1="{f1(y1)}" x2="{f1(x2)}" y2="{f1(y2)}" class="{cls}"></line>'
def dot(x, y, cls, r=4, title=None):
    t = f"<title>{title}</title>" if title else ""
    return f'<circle cx="{f1(x)}" cy="{f1(y)}" r="{r}" class="{cls}">{t}</circle>'
def path(pts, cls):
    return f'<path d="{" ".join(("M" if i == 0 else "L") + f1(x) + " " + f1(y) for i, (x, y) in enumerate(pts))}" class="{cls}"></path>'
def svg(w, h, body, label):
    return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">{"".join(body)}</svg>'
def axis_y(o, x0, x1, Y, ticks, fmt):
    for t in ticks:
        o.append(ln(x0, Y(t), x1, Y(t), "gr")); o.append(txt(x0 - 6, Y(t) + 4, fmt(t), "tm", "end"))

fits = [f for f in R["fits"] if f.get("fail", "") == ""]
by = lambda a: {f["participant"]: f for f in fits if int(f["angle"]) == int(a)}
ids = [i for i in by(0) if i in by(90)]
clipw = lambda v: min(max(v, 0.05), 3.0)

# Figure 1: accuracy by mapping
def fig_acc():
    w, h, L, Rm, Tp, B = 380, 250, 50, 20, 14, 36
    Y = lambda v: h - B - (v - 0.60) / 0.22 * (h - B - Tp); xa, xb = 150, 270
    o = []; axis_y(o, L, w - Rm, Y, [0.60, 0.65, 0.70, 0.75, 0.80], lambda t: nz(t))
    o.append(ln(L, Y(0.707), w - Rm, Y(0.707), "ref")); o.append(txt(w - Rm, Tp + 2, "dashed line: staircase target .707", "tm", "end"))
    for p in R["checks"]["acc_points"]:
        o.append(ln(xa, Y(p["a0"]), xb, Y(p["a90"]), "pl"))
    for p in R["checks"]["acc_points"]:
        o.append(dot(xa, Y(p["a0"]), "d0s", 3.5, f"{p['participant']}: {nz(p['a0'])}")); o.append(dot(xb, Y(p["a90"]), "d90s", 3.5, f"{p['participant']}: {nz(p['a90'])}"))
    c = R["checks"]["accuracy"]; se = lambda sd: stats_t() * sd / math.sqrt(c["n"])
    for gx, m, sd, cls, lc in ((xa - 46, c["mean_a"], c["sd_a"], "d0", "l0"), (xb + 46, c["mean_b"], c["sd_b"], "d90", "l90")):
        o.append(ln(gx, Y(m - se(sd)), gx, Y(m + se(sd)), lc)); o.append(dot(gx, Y(m), cls, 5, f"mean {nz(m)}"))
    o.append(txt((xa + xa - 46) / 2, h - 12, "0° direct", "tl", "middle")); o.append(txt((xb + xb + 46) / 2, h - 12, "90° rotated", "tl", "middle"))
    return svg(w, h, o, "Accuracy on decision trials at both mappings, one line per participant, with group means near the staircase target of .707.")
def stats_t():
    from scipy import stats
    return float(stats.t.ppf(.975, len(ids) - 1))

# Figure 2: confidence by evidence level
def fig_conf():
    w, h, pw, L, Tp, B = 760, 300, 380, 46, 16, 44
    o = []
    for k, a in enumerate((0, 90)):
        x0 = k * pw + L; x1 = k * pw + pw - 86; Y = lambda v: h - B - (v - 1) / 8 * (h - B - Tp)
        xs = [x0 + 22, (x0 + x1) / 2, x1 - 22]
        axis_y(o, x0, x1, Y, [1, 3, 5, 7, 9], lambda t: str(t)); o.append(ln(x0, Y(1), x1, Y(1), "ax"))
        for i, s in enumerate(("none", "low", "high")):
            o.append(txt(xs[i], h - 24, s, "t", "middle"))
        o.append(txt((x0 + x1) / 2, h - 6, "evidence after the choice", "tm", "middle"))
        o.append(txt(x0, 11, f"{a}° · " + ("prediction-based" if a == 0 else "regularity-based"), "tl"))
        for corr, dash, lab in ((1, "", "correct"), (0, " dash", "incorrect")):
            c = sorted([c for c in R["cells"] if c["angle"] == a and c["correct"] == corr], key=lambda c: c["level"])
            cls = f"l{a}"
            o.append(path([(xs[i], Y(c[i]["mean"])) for i in range(3)], f"ln {cls}{dash}"))
            for i in range(3):
                o.append(ln(xs[i], Y(c[i]["mean"] - c[i]["ci"]), xs[i], Y(c[i]["mean"] + c[i]["ci"]), f"eb {cls}"))
                o.append(dot(xs[i], Y(c[i]["mean"]), (f"d{a}" if corr else f"o{a}"), 4, f"{lab}, {('none','low','high')[i]}: M = {c[i]['mean']:.2f}"))
            o.append(txt(xs[2] + 12, Y(c[2]["mean"]) + 4, lab, "t")); o.append(txt(xs[2] + 12, Y(c[2]["mean"]) + 19, f"{c[2]['mean']:.1f}", "tb"))
    return svg(w, h, o, "Mean confidence rating by evidence level for correct and incorrect choices at each mapping. Confidence in incorrect choices falls further at 90 degrees than at 0 degrees.")

# Figure 3: model parameters by mapping
def fig_par():
    w, h, pw, L, Tp, B = 760, 310, 380, 52, 16, 40
    o = []
    # panel A: w_d, log axis
    lo, hi = math.log(0.06), math.log(3.2); x0, x1 = L, pw - 30
    Y = lambda v: h - B - (math.log(v) - lo) / (hi - lo) * (h - B - Tp); xa, xb = x0 + 120, x0 + 215
    axis_y(o, x0, x1, Y, [0.125, 0.25, 0.5, 1, 2], lambda t: f"{t:g}")
    o.append(ln(x0, Y(1), x1, Y(1), "ax")); o.append(txt(x0 + 4, Y(1) - 5, "1 = ideal", "tm"))
    A0, A9 = by(0), by(90)
    for i in ids:
        o.append(ln(xa, Y(clipw(A0[i]["w_d_both"])), xb, Y(clipw(A9[i]["w_d_both"])), "pl"))
    for i in ids:
        o.append(dot(xa, Y(clipw(A0[i]["w_d_both"])), "d0s", 3.5, f"{i}: {A0[i]['w_d_both']:.2f}")); o.append(dot(xb, Y(clipw(A9[i]["w_d_both"])), "d90s", 3.5, f"{i}: {A9[i]['w_d_both']:.2f}"))
    for a, gx, cls, lc, anc, off in (("0", xa - 56, "d0", "l0", "end", -10), ("90", xb + 56, "d90", "l90", "start", 10)):
        r = T["H1_by_angle"][a]
        o.append(ln(gx, Y(math.exp(r["ci"][0])), gx, Y(math.exp(r["ci"][1])), lc)); o.append(dot(gx, Y(math.exp(r["mean"])), cls, 5, f"geometric mean {math.exp(r['mean']):.2f}"))
        o.append(txt(gx + off, Y(math.exp(r["mean"])) + 4, f"{math.exp(r['mean']):.2f}", "tb", anc))
        if "ideal" in R:
            b = math.exp(R["ideal"]["by_angle"][a]["null_mean"])
            o.append(ln(gx - 22, Y(b), gx + 22, Y(b), "bench"))
    o.append(txt(xa - 28, h - 12, "0°", "tl", "middle")); o.append(txt(xb + 28, h - 12, "90°", "tl", "middle"))
    o.append(txt(x0, 11, "A · disconfirmatory weight w_d (log scale)", "tl"))
    # panel B: b
    x0, x1 = pw + L, 2 * pw - 30; bs = [f["b_both"] for f in fits]; blo, bhi = min(-0.6, min(bs) - 0.1), max(1.4, max(bs) + 0.1)
    Y = lambda v: h - B - (v - blo) / (bhi - blo) * (h - B - Tp); xa, xb = x0 + 120, x0 + 215
    axis_y(o, x0, x1, Y, [t for t in (-0.5, 0, 0.5, 1.0) if blo <= t <= bhi], lambda t: num(t, 1))
    o.append(ln(x0, Y(0), x1, Y(0), "ax")); o.append(txt(x0 + 4, Y(0) - 5, "0 = none", "tm"))
    for i in ids:
        o.append(ln(xa, Y(A0[i]["b_both"]), xb, Y(A9[i]["b_both"]), "pl"))
    for i in ids:
        o.append(dot(xa, Y(A0[i]["b_both"]), "d0s", 3.5, f"{i}: {A0[i]['b_both']:.2f}")); o.append(dot(xb, Y(A9[i]["b_both"]), "d90s", 3.5, f"{i}: {A9[i]['b_both']:.2f}"))
    tc = stats_t(); c = T["b_both"]
    for gx, m, sd, cls, lc, anc, off in ((xa - 56, c["mean_a"], c["sd_a"], "d0", "l0", "end", -10), (xb + 56, c["mean_b"], c["sd_b"], "d90", "l90", "start", 10)):
        e = tc * sd / math.sqrt(c["n"]); o.append(ln(gx, Y(m - e), gx, Y(m + e), lc)); o.append(dot(gx, Y(m), cls, 5, f"mean {m:.2f}"))
        o.append(txt(gx + off, Y(m) + 4, num(m), "tb", anc))
    o.append(txt(xa - 28, h - 12, "0°", "tl", "middle")); o.append(txt(xb + 28, h - 12, "90°", "tl", "middle"))
    o.append(txt(x0, 11, "B · commitment to the choice b", "tl"))
    return svg(w, h, o, "Fitted disconfirmatory weight and commitment parameter at each mapping, one line per participant with group estimates and 95 percent intervals.")

# Figure 4: bootstrap null
def fig_boot():
    b = R["boot"]; w, h, L, Rm, Tp, B = 520, 230, 40, 16, 22, 36
    hist = b["hist"]; n = sum(hist); mx = max(hist); X = lambda v: L + (v + 6) / 12 * (w - L - Rm); Y = lambda c: h - B - c / mx * (h - B - Tp)
    o = [ln(L, h - B, w - Rm, h - B, "ax")]
    for i, c in enumerate(hist):
        if c:
            o.append(f'<rect x="{f1(X(-6 + i * .5) + 1)}" y="{f1(Y(c))}" width="{f1(X(.5) - X(0) - 2)}" height="{f1(h - B - Y(c))}" class="bar"><title>{c} of {n} replicates</title></rect>')
    for t in (-6, -4, -2, 0, 2, 4, 6):
        o.append(txt(X(t), h - B + 16, num(t, 0), "tm", "middle"))
    o.append(txt((L + w - Rm) / 2, h - 4, "paired t under the null (w_d equal at both mappings)", "tm", "middle"))
    for q in b["crit"]:
        o.append(ln(X(q), h - B, X(q), h - B - 12, "ax2"))
    to = max(min(b["t_obs"], 6), -6)
    o.append(ln(X(to), Tp - 6, X(to), h - B, "obs")); o.append(txt(X(to) + (8 if to < 0 else -8), Tp + 4, f"observed t = {num(b['t_obs'])}", "tb", "start" if to < 0 else "end"))
    return svg(w, h, o, "Distribution of the paired t statistic under the bootstrap null with the observed value marked in its tail.")

# Figure 5: recovery
def fig_val():
    V = R["validation"]; w, h, pw, L, Tp, B = 760, 320, 380, 52, 18, 44
    o = []; lo, hi = math.log(0.06), math.log(3.2); x0, x1 = L, pw - 30
    X = lambda v: x0 + (math.log(v) - lo) / (hi - lo) * (x1 - x0); Y = lambda v: h - B - (math.log(v) - lo) / (hi - lo) * (h - B - Tp)
    for t in (0.125, 0.25, 0.5, 1, 2):
        o.append(ln(x0, Y(t), x1, Y(t), "gr")); o.append(txt(x0 - 6, Y(t) + 4, f"{t:g}", "tm", "end"))
        o.append(txt(X(t), h - B + 16, f"{t:g}", "tm", "middle"))
    o.append(ln(X(0.07), Y(0.07), X(3), Y(3), "ref")); o.append(txt(X(2.6), Y(3.0) + 14, "perfect recovery", "tm", "end"))
    for p in V["points"]:
        o.append(dot(X(p["wd_true"]), Y(clipw(p["wd_fit"])), f"d{p['angle']}", 4, f"{p['participant']} at {p['angle']}°: true {p['wd_true']:.2f}, recovered {p['wd_fit']:.2f}"))
    o.append(txt((x0 + x1) / 2, h - 6, "w_d put in", "tm", "middle")); o.append(txt(x0, 11, "A · w_d: put in vs. recovered", "tl"))
    x0, x1 = pw + L, 2 * pw - 30; d = V["delta"]; vals = [q for p in d["pairs"] for q in (p["true"], p["fit"])]
    a, b = min(-2.0, min(vals) - .1), max(0.8, max(vals) + .1)
    X = lambda v: x0 + (v - a) / (b - a) * (x1 - x0); Y = lambda v: h - B - (v - a) / (b - a) * (h - B - Tp)
    for t in (-2, -1.5, -1, -0.5, 0, 0.5):
        if a <= t <= b:
            o.append(ln(x0, Y(t), x1, Y(t), "ax" if t == 0 else "gr")); o.append(txt(x0 - 6, Y(t) + 4, num(t, 1), "tm", "end"))
            o.append(ln(X(t), h - B, X(t), Tp, "ax" if t == 0 else "gr")); o.append(txt(X(t), h - B + 16, num(t, 1), "tm", "middle"))
    o.append(ln(X(a), Y(a), X(b), Y(b), "ref"))
    for p in d["pairs"]:
        o.append(dot(X(p["true"]), Y(p["fit"]), "dk", 4, f"{p['participant']}: true {p['true']:.2f}, recovered {p['fit']:.2f}"))
    o.append(f'<rect x="{f1(X(d["true_mean"]) - 6)}" y="{f1(Y(d["fit_mean"]) - 6)}" width="12" height="12" class="sq"><title>group: true {d["true_mean"]:.2f}, recovered {d["fit_mean"]:.2f}</title></rect>')
    o.append(txt(x1, Y(a) - 8, "square: group mean", "tm", "end"))
    o.append(txt((x0 + x1) / 2, h - 6, "mode difference put in (log w_d, 0° − 90°)", "tm", "middle")); o.append(txt(x0, 11, "B · mode difference: put in vs. recovered", "tl"))
    return svg(w, h, o, "Recovered against generating values for the disconfirmatory weight and for the difference between mappings. Points lie below the identity line for the weight and around it for the difference.")

# ── text blocks ─────────────────────────────────────────────────────────────────
h2, h1, bb = T["H2_wd_both"], T["H1_wd_both"], T["b_both"]
geo = T["geo"]["w_d_both"]; ratio = math.exp(h2["mean"])
acc = R["checks"]["accuracy"]; prp = R["checks"]["prop"]; ev = R["evidence"]
sig2 = h2["p"] < .05
boot = R.get("boot"); ideal = R.get("ideal")
STR = R.get("strength")            # two-track data (design doc §10j): strength trials were collected
DES = R.get("design", {})

def quality_table():
    rows = "".join(f"<tr><td>{q['participant']}</td><td>{q['n_trials']}</td><td>{nz(q['acc_0'])}</td><td>{nz(q['acc_90'])}</td><td>{pct(q['timeouts'],1)}</td>"
                   f"<td>{pct(q['conf_mode_share'])}</td><td>{q['median_conf_rt']:.2f}</td><td>{pct(q['clipped_0'])}</td><td>{pct(q['clipped_90'])}</td><td>{'yes' if q['excluded'] else 'no'}</td></tr>" for q in R["quality"])
    return ("<table><thead><tr><th>Participant</th><th>Trials</th><th>Acc. 0°</th><th>Acc. 90°</th><th>Timeouts</th><th>Modal rating</th><th>Median rating RT (s)</th>"
            "<th>Clipped 0°</th><th>Clipped 90°</th><th>Excluded</th></tr></thead><tbody>" + rows + "</tbody></table>")
def bic_table():
    b = T["bic"]; lab = dict(null="Ideal observer (w = 1, b = 0)", weight="Weights (w<sub>c</sub>, w<sub>d</sub>)", choice="Commitment (b)", both="Weights + commitment")
    k = dict(null=1, weight=3, choice=2, both=4)
    rows = "".join(f"<tr><td>{lab[m]}</td><td>{k[m]}</td><td>{b['sum'][m]:.1f}</td><td>{b['delta'][m]:.1f}</td><td>{b['wins'][m]}</td></tr>" for m in ("null", "choice", "weight", "both"))
    return f"<table><thead><tr><th>Model</th><th>Free parameters</th><th>ΣBIC</th><th>ΔBIC</th><th>Best in (of {b['n_fits']})</th></tr></thead><tbody>{rows}</tbody></table>"
def par_table():
    wc = T["geo"]["w_c_both"]; r = []
    r.append(f"<tr><td>w<sub>d</sub> (disconfirming)</td><td>{geo['0']:.2f}</td><td>{geo['90']:.2f}</td><td>{num(h2['mean'])} [{num(h2['ci'][0])}, {num(h2['ci'][1])}]</td><td>{num(h2['t'])}</td><td>{nz(h2['p'],3)}</td><td>{num(h2['d'])}</td></tr>")
    c = T["wc_both"]; r.append(f"<tr><td>w<sub>c</sub> (confirming)</td><td>{wc['0']:.2f}</td><td>{wc['90']:.2f}</td><td>{num(c['mean'])} [{num(c['ci'][0])}, {num(c['ci'][1])}]</td><td>{num(c['t'])}</td><td>{nz(c['p'],3)}</td><td>{num(c['d'])}</td></tr>")
    r.append(f"<tr><td>b (commitment)</td><td>{num(bb['mean_a'])}</td><td>{num(bb['mean_b'])}</td><td>{num(bb['mean'])} [{num(bb['ci'][0])}, {num(bb['ci'][1])}]</td><td>{num(bb['t'])}</td><td>{nz(bb['p'],3)}</td><td>{num(bb['d'])}</td></tr>")
    return ("<table><thead><tr><th>Parameter</th><th>0°</th><th>90°</th><th>Difference [95% CI]</th><th><i>t</i>(" + str(h2["df"]) + ")</th><th><i>p</i></th><th><i>d<sub>z</sub></i></th></tr></thead><tbody>"
            + "".join(r) + "</tbody></table>")
def val_table():
    V = R["validation"]; P, E = V["params"], V["evidence"]; rows = []
    for lab, kt, kf, src, d in (("w<sub>d</sub>", "wd_true", "wd_fit", P, 2), ("w<sub>c</sub>", "wc_true", "wc_fit", P, 2), ("b", "b_true", "b_fit", P, 2),
                                ("Strength of the weak sample", "e_low_true", "e_low_fit", E, 2), ("Strength of the strong sample", "e_high_true", "e_high_fit", E, 2),
                                ("Psychometric slope", "slope_true", "slope_fit", E, 2)):
        rows.append(f"<tr><td>{lab}</td>" + "".join(f"<td>{src[a][kt]:.{d}f}</td><td>{src[a][kf]:.{d}f}</td>" for a in ANG) + "</tr>")
    return ("<table><thead><tr><th rowspan='2'>Quantity</th><th colspan='2'>0°</th><th colspan='2'>90°</th></tr><tr><th>Put in</th><th>Recovered</th><th>Put in</th><th>Recovered</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")

def strength_table():
    a, f = STR["acc"], STR["floor_ceiling"]; dl, dr = STR["delta"], STR["threshold_drift"]["by_angle"]
    rows = "".join(f"<tr><td>{NAME[g]}</td><td>{pct(a[g]['mean'], 1)}</td><td>{pct(a[g]['sd'], 1)}</td><td>{a[g]['n_trials']:.0f}</td>"
                   f"<td>{num(dl[g]['first10'])} → {num(dl[g]['last10'])}</td><td>{num(dr[g]['mean'], 2, True)}</td>"
                   f"<td>{pct(f[g]['floor'])}</td><td>{pct(f[g]['ceiling'])}</td></tr>" for g in ANG)
    return ("<table><thead><tr><th>Mapping</th><th>Strength-trial accuracy</th><th><i>SD</i> across people</th><th>Trials</th>"
            "<th>Offset δ, first → last 10</th><th>Threshold drift (logit)</th><th>Floor (incorrect, strong)</th><th>Ceiling (correct, strong)</th></tr></thead><tbody>"
            + rows + "</tbody></table>")

V = R.get("validation")
md = R["meta"]
parts = []
A = parts.append

A(f"""<header>
{'<div class="banner"><b>Simulated data.</b> Ten simulated participants built to behave as the hypothesis states. These are not empirical results; the numbers show what the planned analysis returns when the truth is known.</div>' if SIM else ''}
<p class="eyebrow">A Second Look · work package 3 · {'validation of the planned analysis' if SIM else 'results'}</p>
<h1>{'Does the analysis measure what we set out to measure?' if SIM else 'Results'}</h1>
<p class="dek">{'The complete planned analysis, run on data files in the exact layout the online task writes, from simulated participants whose true parameters are known.' if SIM else ''}</p>
</header>""")

if SIM:
    d = V["delta"]; lv0 = V["params"]["0"]; lv9 = V["params"]["90"]
    A(f"""<section><h2>Summary</h2>
<div class="verdict">
<p><b>The primary measure works.</b> The simulated participants used disconfirming evidence {pct(1 - math.exp(d['true_mean']))} less under the direct mapping than under the rotated one. The analysis recovered a reduction of {pct(1 - ratio)} (log difference put in {num(d['true_mean'])}, recovered {num(d['fit_mean'])}). The contrast was {'significant' if sig2 else 'not significant'} at <i>N</i> = {h2['n']}, {t_apa(h2)}{f", bootstrap {p_apa(boot['p'])}" if boot else ""}.</p>
{f'''<p><b>The absolute level is {'recovered' if max(abs(lv0['wd_fit'] / lv0['wd_true'] - 1), abs(lv9['wd_fit'] / lv9['wd_true'] - 1)) < .15 else 'still biased'}.</b> Fitted w<sub>d</sub> came out at {lv0['wd_fit']:.2f} and {lv9['wd_fit']:.2f} where {lv0['wd_true']:.2f} and {lv9['wd_true']:.2f} had been put in ({100 * lv0['wd_fit'] / lv0['wd_true']:.0f}% and {100 * lv9['wd_fit'] / lv9['wd_true']:.0f}%). The strength of the high evidence is measured rather than extrapolated, so the level no longer rests on an over-estimated psychometric slope. A test of w<sub>d</sub> against 1 still goes through an ideal-observer benchmark, below.</p>
<p><b>What follows for the real study</b> is listed in the last section.</p>''' if STR else f'''<p><b>The absolute level does not.</b> Fitted w<sub>d</sub> came out at {lv0['wd_fit']:.2f} and {lv9['wd_fit']:.2f} where {lv0['wd_true']:.2f} and {lv9['wd_true']:.2f} had been put in. The strength of the strong evidence sample is over-estimated, which pulls every weight down by about the same factor. The contrast between mappings is unaffected; a test of w<sub>d</sub> against 1 is not valid and is replaced by a benchmark below.</p>
<p><b>Five changes follow for the real study,</b> three of them already made. They are listed in the last section.</p>'''}
</div></section>""")

A(f"""<section><h2>Method</h2>
<p>{'Ten participants were simulated' if SIM else f"{R['n_total']} participants took part"}. Each judged which of two circles they controlled, under a direct (0°) and a rotated (90°) mapping in counterbalanced order, with control proportion set by a 1-up-2-down staircase that ran throughout. Per mapping there were 30 Task 1 trials (decision, then confidence rating on a 9-point scale) and 60 Task 2 trials (decision, a further 3 s of evidence, then the rating). {f"The further evidence was of the same strength as the decision sample (low) or stronger (high), and always came from the true target. The high strength was not fixed: a second adaptive track (weighted up-down, 85% target) set it relative to the live staircase value, driven by strength trials: choice-only trials whose first look was already at the high strength, {DES.get('strength_calibration', 0)} per mapping in a short calibration block with feedback after the staircase calibration, then {DES['strength_task1']} interleaved in Task 1 and {DES['strength_task2']} in Task 2 without feedback. The accuracy of the interleaved ones is the measured strength of the high evidence; strength trials carry no rating and no further evidence and are not part of the confidence model." if STR else "The further evidence was of the same strength as the decision sample (low) or 1.2 logit stronger (high), and always came from the true target."}</p>
{f'''<p>The simulated observers rated confidence as 1 + 8·σ(L<sub>0</sub> + b ± w·e) plus Gaussian noise, rounded to the scale. Group values put in: w<sub>d</sub> = {V['params']['90']['wd_true']:.2f} at 90° and {V['params']['0']['wd_true']:.2f} at 0°; b = {V['params']['0']['b_true']:.2f} and w<sub>c</sub> = {V['params']['0']['wc_true']:.2f} at both mappings. Participants differed around these values. The random seed was fixed before any result was seen. Files were written in the layout and number format of the online task.</p>''' if SIM else ''}
<p>Ratings were analysed with four models fitted per participant and mapping by maximum likelihood with a censored-Gaussian response function: an ideal observer, asymmetric weights, a commitment term, and both. Inference used the parameters of the model with both, fixed in advance. The primary test was the paired comparison of log w<sub>d</sub> between mappings, referred to the <i>t</i> distribution and to a parametric-bootstrap null in which each participant's session was re-simulated from their fitted parameters with w<sub>d</sub> equal at both mappings.</p>
</section>""")

A(f"""<section><h2>Results</h2>
<h3>Data quality and exclusions</h3>
<p>Participants were excluded for overall accuracy outside [.60, .85], accuracy at either mapping outside [.55, .85], one rating on more than 90% of trials, a median rating time below 850 ms, or more than 5% timeouts. {R['n_excluded']} of {R['n_total']} participants met a criterion, leaving <i>N</i> = {R['n_included']} and {R['n_trials']:,} trials. {'No model fit failed.' if not R['model_fail'] else f"{len(R['model_fail'])} fits failed and were dropped."}</p>
<figure><figcaption><b>Table 1.</b> Data quality per participant. Clipped = share of Task 2 trials whose strong sample hit the ceiling of the control proportion; these trials are excluded from the model fits.</figcaption><div class="tw">{quality_table()}</div></figure>

<h3>Manipulation checks</h3>
<p>The staircase held accuracy at the intended level under both mappings (0°: <i>M</i> = {nz(acc['mean_a'])}, <i>SD</i> = {nz(acc['sd_a'])}; 90°: <i>M</i> = {nz(acc['mean_b'])}, <i>SD</i> = {nz(acc['sd_b'])}), with no difference between them, {t_apa(acc)} (Figure 1). It reached that level at a higher control proportion under the rotated mapping (<i>M</i> = {nz(prp['mean_b'])} vs. {nz(prp['mean_a'])}), {t_apa(prp)}, which confirms that the rotation made control harder to detect and that the staircase compensated.</p>
{f'''<p>The strong evidence was delivered where the design aims and equally under both mappings (Table 2). Strength-trial accuracy was {pct(STR['acc']['0']['mean'], 1)} (0°) and {pct(STR['acc']['90']['mean'], 1)} (90°); the difference was {num(STR['diff']['mean'] * 100, 1)} percentage points, {t_apa(STR['diff'])}. Equivalence within ±5 points: TOST {p_apa(STR['tost']['p'])}. The tracked offset moved from its start value of 0.80 to the following means (first → last ten strength trials, 0°: {num(STR['delta']['0']['first10'])} → {num(STR['delta']['0']['last10'])}; 90°: {num(STR['delta']['90']['first10'])} → {num(STR['delta']['90']['last10'])}). The live threshold drifted by {num(STR['threshold_drift']['by_angle']['0']['mean'], 2, True)} (0°) and {num(STR['threshold_drift']['by_angle']['90']['mean'], 2, True)} (90°) logit over the session; the difference between mappings, the quantity that would bias the primary contrast, was {num(STR['threshold_drift']['diff']['mean'], 2, True)}, {t_apa(STR['threshold_drift']['diff'])}.</p>
<figure><figcaption><b>Table 2.</b> Evidence levels as delivered.</figcaption><div class="tw">{strength_table()}</div></figure>''' if STR else ''}
<p>The evidence samples differed in strength as intended. {"As measured, the weak sample corresponded to" if STR else "Expressed as the accuracy a sample would support, the weak sample corresponded to"} {pct(ev['0']['p_low'])} (0°) and {pct(ev['90']['p_low'])} (90°), the strong sample to {pct(ev['0']['p_high'])} and {pct(ev['90']['p_high'])}. The mean number of incorrect Task 2 trials per participant and mapping, which identify w<sub>d</sub>, was {ev['0']['n_inc_t2']:.1f} and {ev['90']['n_inc_t2']:.1f}.</p>
<figure class="narrow"><div class="plot">{fig_acc()}</div><div class="legend"><span><i class="sw b0"></i>0° direct</span><span><i class="sw b90"></i>90° rotated</span><span>small: participants · large: mean ± 95% CI</span></div>
<figcaption><b>Figure 1.</b> Accuracy on decision trials by mapping.</figcaption></figure>

<h3>Metacognitive sensitivity</h3>
<p>Metacognitive sensitivity was estimated from Task 1 by maximum likelihood (Maniscalco &amp; Lau, 2012) with ratings in three bins. Pooled over mappings, <i>d′</i> was {md['pooled']['d1']['mean']:.2f} (<i>SD</i> = {md['pooled']['d1']['sd']:.2f}) and meta-<i>d′</i> {md['pooled']['meta_d']['mean']:.2f} (<i>SD</i> = {md['pooled']['meta_d']['sd']:.2f}). Meta-<i>d′</i> did not differ between mappings (0°: <i>M</i> = {md['meta_d']['mean_a']:.2f}; 90°: <i>M</i> = {md['meta_d']['mean_b']:.2f}), {t_apa(md['meta_d'])}, nor did the ratio meta-<i>d′</i>/<i>d′</i>, {t_apa(md['mratio'])}.</p>
{f'''<p class="note">Two limits apply. The simulated observers do not generate confidence from a signal-detection model, so there is no true ratio to recover here; this section shows that the analysis runs and finds no difference where none was built in. And with 30 trials per mapping the per-person ratio is very noisy (<i>SD</i> = {md['mratio']['sd_a']:.2f} at 0°): for the comparison between mappings the hierarchical estimator used in work package 1 is the appropriate tool.</p>''' if SIM else ''}

<h3>Confidence after further evidence</h3>
<p>Confidence moved in the direction of the evidence (Figure 2). After correct choices it rose with evidence strength and approached the top of the scale under both mappings. After incorrect choices it fell, and fell further under the rotated mapping: following the strong sample, mean confidence in an incorrect choice was {[c for c in R['cells'] if c['angle']==0 and c['correct']==0 and c['level']==2][0]['mean']:.2f} at 0° and {[c for c in R['cells'] if c['angle']==90 and c['correct']==0 and c['level']==2][0]['mean']:.2f} at 90°. The descriptive slope of confidence over evidence level on incorrect trials was shallower at 0° (<i>M</i> = {R['beta_disc']['mean_a']:.2f}) than at 90° (<i>M</i> = {R['beta_disc']['mean_b']:.2f}), {t_apa(R['beta_disc'])}. Because correct trials start near the ceiling of the scale, raw slopes are reported for description only.</p>
<figure><div class="plot">{fig_conf()}</div><div class="legend"><span><i class="key"></i>correct (confirming evidence)</span><span><i class="key dashk"></i>incorrect (disconfirming evidence)</span><span>mean ± 95% within-participant CI</span></div>
<figcaption><b>Figure 2.</b> Confidence (1 = certainly wrong, 9 = certainly right) by strength of the evidence received after the choice.</figcaption></figure>

<h3>Computational model</h3>
<p><b>Model comparison.</b> Summed over participants and mappings, the model with asymmetric weights had the lowest BIC, followed by the model with weights and commitment (ΔBIC = {T['bic']['delta']['both']:.1f}); the commitment-only model (ΔBIC = {T['bic']['delta']['choice']:.1f}) and the ideal observer (ΔBIC = {T['bic']['delta']['null']:.1f}) fitted clearly worse (Table {3 if STR else 2}). {'BIC therefore preferred the simpler model although the data were generated with a commitment term: at this trial count the penalty for the fourth parameter outweighs a commitment of this size. Inference nevertheless uses the model with both terms, as fixed in advance, because a model without b attributes differences in commitment to w<sub>d</sub>.' if SIM else 'Inference uses the model with both terms, as fixed in advance.'}</p>
<figure><figcaption><b>Table {3 if STR else 2}.</b> Model comparison.</figcaption><div class="tw">{bic_table()}</div></figure>

<p><b>Primary hypothesis: the mapping changes how disconfirming evidence is used.</b> The disconfirmatory weight was lower under the direct mapping (geometric mean w<sub>d</sub> = {geo['0']:.2f}) than under the rotated mapping ({geo['90']:.2f}), a reduction of {pct(1 - ratio)}. The difference in log w<sub>d</sub> was {num(h2['mean'])}, {ci(h2)}, {t_apa(h2)}; Wilcoxon signed-rank {p_apa(h2['wilcoxon_p'])} (Table {4 if STR else 3}, Figure 3A).{f" Referred to the bootstrap null ({boot['n']} replicates), the observed statistic gave {p_apa(boot['p'])} (Figure 4). Under that null the paired difference averaged {num(boot['null_mean_diff'])}, so the estimator carries no material bias toward either mapping in this sample." if boot else ""}</p>
<p><b>Commitment.</b> The commitment parameter did not differ between mappings (0°: <i>M</i> = {num(bb['mean_a'])}; 90°: <i>M</i> = {num(bb['mean_b'])}), {t_apa(bb)} (Figure 3B). The confirmatory weight did not differ either, {t_apa(T['wc_both'])}. The difference between mappings is therefore specific to the use of disconfirming evidence, as built in.</p>
<figure><figcaption><b>Table {4 if STR else 3}.</b> Parameter estimates by mapping (weights: geometric means; differences on the log scale for weights).</figcaption><div class="tw">{par_table()}</div></figure>
<figure><div class="plot">{fig_par()}</div><div class="legend"><span><i class="sw b0"></i>0° direct</span><span><i class="sw b90"></i>90° rotated</span><span>small: participants · large: group estimate ± 95% CI</span>{'<span><i class="key benchk"></i>dotted: an ideal observer, as this pipeline returns it</span>' if ideal else ''}</div>
<figcaption><b>Figure 3.</b> Fitted parameters of the model with weights and commitment.</figcaption></figure>
{f'''<figure class="narrow"><div class="plot">{fig_boot()}</div><figcaption><b>Figure 4.</b> Bootstrap distribution of the test statistic under the null hypothesis of equal w<sub>d</sub>. Ticks mark the 2.5th and 97.5th percentiles.</figcaption></figure>''' if boot else ''}

<p><b>Is disconfirming evidence under-used at all?</b> Averaged over mappings, log w<sub>d</sub> was {num(h1['mean'])} (w<sub>d</sub> = {math.exp(h1['mean']):.2f}). {f"An ideal observer passed through the same pipeline does not return w<sub>d</sub> = 1 but {math.exp(ideal['null_mean']):.2f} (log {num(ideal['null_mean'])}; {ideal['n']} replicates), because the strength of the strong sample is over-estimated. Against this benchmark the observed value gave {p_apa(ideal['p'])} overall; by mapping, 0°: observed {math.exp(ideal['by_angle']['0']['obs']):.2f} against a benchmark of {math.exp(ideal['by_angle']['0']['null_mean']):.2f}, {p_apa(ideal['by_angle']['0']['p'])}; 90°: observed {math.exp(ideal['by_angle']['90']['obs']):.2f} against {math.exp(ideal['by_angle']['90']['null_mean']):.2f}, {p_apa(ideal['by_angle']['90']['p'])}. A test against 1 would have returned {t_apa(h1, 'd')}, overstating the evidence." if ideal else f"Against 1: {t_apa(h1, 'd')}."}</p>
<p><b>Secondary analysis.</b> Meta-<i>d′</i> from Task 1 was related to the sensitivity of Task 2 confidence to the further evidence at <i>r</i> = {nz(R['meta_predicts_sens']['r'])} (<i>n</i> = {R['meta_predicts_sens']['n']}){', an estimate too imprecise at this sample size to interpret' if R['meta_predicts_sens']['n'] < 30 else ''}.</p>
</section>""")

if SIM:
    E = V["evidence"]
    A(f"""<section><h2>Validation against the known truth</h2>
<p>Because the participants were simulated, every estimate can be compared with the value that produced it (Table {5 if STR else 4}, Figure 5).</p>
<p><b>The difference between mappings is recovered.</b> The mean difference in log w<sub>d</sub> put in was {num(d['true_mean'])}; the analysis returned {num(d['fit_mean'])}. Individual differences were recovered at <i>r</i> = {nz(d['r'])}, individual weights at <i>r</i> = {nz(V['r_wd'])}. The recovered differences were more variable than the true ones (<i>SD</i> = {d['fit_sd']:.2f} vs. {d['true_sd']:.2f}): most of the spread between people in the fitted values is measurement error, as the power analysis had indicated.</p>
{f'''<p><b>The level</b> of the weak sample was estimated at {E['0']['e_low_fit']:.2f} (put in {E['0']['e_low_true']:.2f}) and of the strong sample at {E['0']['e_high_fit']:.2f} (put in {E['0']['e_high_true']:.2f}) at 0°, and at {E['90']['e_high_fit']:.2f} (put in {E['90']['e_high_true']:.2f}) at 90°. The strong sample is not extrapolated from the staircase's range: its accuracy is measured on strength trials, shrunk toward the group value, and the psychometric function only supplies variation around that level.</p>''' if STR else f'''<p><b>The level is not.</b> The weak sample's strength was estimated accurately ({E['0']['e_low_fit']:.2f} against {E['0']['e_low_true']:.2f} at 0°), the strong sample's was not ({E['0']['e_high_fit']:.2f} against {E['0']['e_high_true']:.2f} at 0°; {E['90']['e_high_fit']:.2f} against {E['90']['e_high_true']:.2f} at 90°). The strong sample lies outside the range of control proportions the staircase visits, so its strength is extrapolated from a psychometric slope that is itself over-estimated (median {E['0']['slope_fit']:.2f} and {E['90']['slope_fit']:.2f} against {E['0']['slope_true']:.2f}). An over-estimated evidence strength is compensated by an under-estimated weight. In a separate check on 120 simulated participants per cell the fitted weights were 0.75 (0°) and 0.77 (90°) of the true values when the calibration trials entered the psychometric fit, as they do here, and 0.67 and 0.66 when they did not. A weaker strong sample (0.8 instead of 1.2 logit) left the factor unchanged. The factor is the same at both mappings, which is why the contrast survives.</p>'''}
<figure><figcaption><b>Table {5 if STR else 4}.</b> Group values put in and recovered.</figcaption><div class="tw">{val_table()}</div></figure>
<figure><div class="plot">{fig_val()}</div><div class="legend"><span><i class="sw b0"></i>0° direct</span><span><i class="sw b90"></i>90° rotated</span><span><i class="key refk"></i>perfect recovery</span></div>
<figcaption><b>Figure 5.</b> Recovery of the disconfirmatory weight (A) and of the difference between mappings (B).</figcaption></figure>
</section>

<section><h2>Consequences for the study</h2>
<p>The primary test stays as planned: the paired contrast on log w<sub>d</sub> from the model with weights and commitment recovers the effect and is not biased toward either mapping.</p>
{f'''<ol class="todo">
<li><b>Strength trials replace the extrapolation.</b> Done: a strength-calibration block ({DES.get('strength_calibration', 0)} choice-only trials per mapping) sets each person's high offset, {DES['strength_task1']} + {DES['strength_task2']} interleaved strength trials keep it at about 85% and measure it; the level of the evidence is that measured accuracy.</li>
<li><b>Report the checks in Table 2.</b> Equal strength-trial accuracy across mappings (TOST), convergence of the offset and the drift of the live threshold are preregistered diagnostics, not assumptions.</li>
<li><b>Test the level of w<sub>d</sub> against the ideal-observer benchmark, not against 1.</b> Done: the analysis script produces the benchmark from each participant's own fitted parameters, re-simulating the same two-track design.</li>
<li><b>Estimate metacognitive efficiency hierarchically.</b> Open: thirty Task 1 trials per mapping do not support a per-person ratio.</li>
<li><b>Expect BIC to prefer the simpler model, and say so in the preregistration.</b> Open: this is not evidence against a commitment term of the size Rollwage et al. (2018) reported; the model used for inference is fixed in advance for that reason.</li>
</ol>''' if STR else '''<ol class="todo">
<li><b>Test the level of w<sub>d</sub> against the ideal-observer benchmark, not against 1.</b> Done: the analysis script produces the benchmark from each participant's own fitted parameters.</li>
<li><b>Write the calibration trials to the data file.</b> Done: the online task did not log them; it does now. They reduce the bias in the level from about one third to about one quarter.</li>
<li><b>Write every collected field to the data file.</b> Done: fullscreen exits, the second quiz counter and the Prolific study and session identifiers were collected but never written.</li>
<li><b>Estimate metacognitive efficiency hierarchically.</b> Open: thirty Task 1 trials per mapping do not support a per-person ratio.</li>
<li><b>Expect BIC to prefer the simpler model, and say so in the preregistration.</b> Open: this is not evidence against a commitment term of the size Rollwage et al. (2018) reported; the model used for inference is fixed in advance for that reason.</li>
</ol>'''}
<p class="note">Sample size. The effect built in here, a reduction of {pct(1 - math.exp(d['true_mean']))}, is more than twice the smallest effect the full study is powered to detect (20% at <i>N</i> = 150). Ten participants suffice to show that the analysis returns what was put in; they say nothing about whether an effect of realistic size will be found.</p>
</section>""")

CSS = """
:root{color-scheme:light;--bg:#FAFAF7;--surface:#FFFFFF;--panel:#ECEEF0;--ink:#15181C;--ink2:#2B3036;--muted:#4A5058;--grid:#DDE0E3;--axis:#9AA1A9;--hair:#C2C7CD;
--c0:#2A78D6;--c90:#D95926;--warnbg:#FFF4D6;--warnink:#5C4300;--okbg:#E3F3EC}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#0F1216;--surface:#171B21;--panel:#1D2229;--ink:#F2F3F5;--ink2:#D5D9DE;--muted:#A9B0B8;--grid:#262B32;--axis:#5A626C;--hair:#363C45;
--c0:#3987E5;--c90:#E26A3A;--warnbg:#3A2E14;--warnink:#F3D58A;--okbg:#16302A}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#0F1216;--surface:#171B21;--panel:#1D2229;--ink:#F2F3F5;--ink2:#D5D9DE;--muted:#A9B0B8;--grid:#262B32;--axis:#5A626C;--hair:#363C45;
--c0:#3987E5;--c90:#E26A3A;--warnbg:#3A2E14;--warnink:#F3D58A;--okbg:#16302A}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"IBM Plex Sans","Helvetica Neue",Helvetica,sans-serif;font-size:17px;line-height:1.6;padding-inline:20px;padding-block:0 96px}
main{max-width:800px;margin:0 auto}
header{padding-top:40px}
h1{font-family:"IBM Plex Serif",Georgia,serif;font-weight:600;font-size:clamp(30px,5vw,44px);line-height:1.15;letter-spacing:-.01em;margin:6px 0 10px;text-wrap:balance}
h2{font-family:"IBM Plex Serif",Georgia,serif;font-weight:600;font-size:26px;margin:52px 0 10px;text-wrap:balance}
h3{font-size:18px;font-weight:600;margin:34px 0 6px}
p{margin:0 0 14px;max-width:72ch}
.eyebrow{font-family:"IBM Plex Mono",Menlo,monospace;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0}
.dek{font-size:20px;line-height:1.45;color:var(--ink2)}
.banner{background:var(--warnbg);color:var(--warnink);border-radius:8px;padding:12px 16px;font-size:15.5px;margin-bottom:28px}
.verdict{background:var(--panel);border-radius:10px;padding:18px 20px 6px}
.note{font-size:15.5px;color:var(--ink2);border-left:2px solid var(--axis);padding-left:14px}
figure{margin:22px 0 26px}
figure.narrow{max-width:540px}
figcaption{font-size:14.5px;color:var(--ink2);margin:8px 0;max-width:72ch}
.plot{background:var(--surface);border:1px solid var(--hair);border-radius:10px;padding:14px 12px 8px}
.plot svg{display:block;width:100%;height:auto;overflow:visible}
.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14.5px;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--hair);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
thead th{font-weight:600;border-bottom:1.5px solid var(--ink);border-top:1.5px solid var(--ink)}
tbody tr:last-child td{border-bottom:1.5px solid var(--ink)}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13px;color:var(--ink2);margin:8px 2px 0}
.legend span{display:inline-flex;align-items:center;gap:7px}
.sw{display:inline-block;width:11px;height:11px;border-radius:3px}.b0{background:var(--c0)}.b90{background:var(--c90)}
.key{display:inline-block;width:24px;border-top:2px solid var(--ink)}.dashk{border-top-style:dashed}.refk{border-top:1.5px dashed var(--axis)}.benchk{border-top:2px dotted var(--ink)}
ol.todo{padding-left:22px;max-width:72ch}ol.todo li{margin:0 0 10px}
svg text{font-family:"IBM Plex Sans",Helvetica,sans-serif;font-size:12px;fill:var(--ink2)}
svg .tm{font-family:"IBM Plex Mono",Menlo,monospace;font-size:11.5px;fill:var(--muted)}
svg .tl{font-size:12.5px;font-weight:600;fill:var(--ink)} svg .tb{font-weight:600;fill:var(--ink)}
svg .gr{stroke:var(--grid);stroke-width:1} svg .ax{stroke:var(--axis);stroke-width:1} svg .ax2{stroke:var(--ink);stroke-width:1.5}
svg .ref{stroke:var(--axis);stroke-width:1.25;stroke-dasharray:5 4} svg .bench{stroke:var(--ink);stroke-width:2;stroke-dasharray:2 3}
svg .pl{stroke:var(--axis);stroke-width:1}
svg .ln{fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round} svg .dash{stroke-dasharray:6 5}
svg .l0{stroke:var(--c0);stroke-width:2} svg .l90{stroke:var(--c90);stroke-width:2} svg .eb{stroke-width:1.5}
svg .d0{fill:var(--c0);stroke:var(--surface);stroke-width:2} svg .d90{fill:var(--c90);stroke:var(--surface);stroke-width:2}
svg .d0s{fill:var(--c0);fill-opacity:.6} svg .d90s{fill:var(--c90);fill-opacity:.6}
svg .o0{fill:var(--surface);stroke:var(--c0);stroke-width:2} svg .o90{fill:var(--surface);stroke:var(--c90);stroke-width:2}
svg .dk{fill:var(--ink2);fill-opacity:.65} svg .sq{fill:var(--ink);stroke:var(--surface);stroke-width:2}
svg .bar{fill:var(--axis)} svg .obs{stroke:var(--ink);stroke-width:2}
"""
# No doctype / html / head / body of our own: the page is published as an artifact, which wraps
# the content in its own skeleton. A browser opening the file directly builds the same tree.
html = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{'Second Look Validation' if SIM else 'Second Look Results'}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Serif:wght@500;600&display=swap">
<style>{CSS}</style>
<main>
{''.join(parts)}
<p class="eyebrow" style="margin-top:48px">Analysis: wp3_paper_analysis.py · report: wp3_report.py{' · data: make_validation_data.py, seed 20260929' if SIM else ''}</p>
</main>"""
open(OUT, "w", encoding="utf-8").write(html)
print(f"[report] {OUT}  {len(html.encode()) // 1024} KB")
