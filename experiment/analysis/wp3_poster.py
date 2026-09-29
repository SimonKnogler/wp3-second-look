#!/usr/bin/env python3
"""Results poster (one A4 artboard for the design canvas) from results.json, in the style of
the 'A Second Look' and 'Expecting Control' posters. Works for simulated and real results;
the validation row and the 'simulated' marking appear only when a ground truth is present.

  python wp3_poster.py results.json OUT.dc.html
"""
import json, math, sys

R = json.load(open(sys.argv[1])); OUT = sys.argv[2]
SIM = "validation" in R; T = R["tests"]
BLUE, ORANGE, INK, SEC, MUT, GRID, AXIS, PAPER = "#2A78D6", "#D95926", "#15181C", "#2B3036", "#4A5058", "#DDE0E3", "#9AA1A9", "#FAFAF7"
COL = {0: BLUE, 90: ORANGE}
MONO = "'IBM Plex Mono', Menlo, monospace"; SANS = "'IBM Plex Sans', Helvetica, sans-serif"
TC = {9: 2.262, 8: 2.306, 7: 2.365}

f1 = lambda v: f"{v:.1f}"
num = lambda x, d=2: f"{x:.{d}f}".replace("-", "−")
def nz(x, d=2):
    s = f"{abs(x):.{d}f}".lstrip("0") or "0"
    return ("−" if x < 0 else "") + s
p_apa = lambda p: "p &lt; .001" if p < .001 else f"p = {nz(p, 3)}"
t_apa = lambda r: f"t({r['df']}) = {num(r['t'])}, {p_apa(r['p'])}"
def tcrit(df):
    from scipy import stats
    return float(stats.t.ppf(.975, df))

def txt(x, y, s, anchor="start", fam=SANS, size=12, fill=SEC, weight=None):
    w = f' font-weight="{weight}"' if weight else ""
    return f'<text x="{f1(x)}" y="{f1(y)}" text-anchor="{anchor}" font-family="{fam}" font-size="{size}"{w} fill="{fill}">{s}</text>'
def ln(x1, y1, x2, y2, stroke, sw=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{f1(x1)}" y1="{f1(y1)}" x2="{f1(x2)}" y2="{f1(y2)}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"{d}></line>'
def dot(x, y, fill, r=4, ring=True, op=None, stroke=None):
    a = f' stroke="{stroke or PAPER}" stroke-width="2"' if ring else ""
    o = f' fill-opacity="{op}"' if op else ""
    return f'<circle cx="{f1(x)}" cy="{f1(y)}" r="{r}" fill="{fill}"{o}{a}></circle>'
def path(pts, stroke, dash=None, sw=2):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="{" ".join(("M" if i == 0 else "L") + f1(x) + " " + f1(y) for i, (x, y) in enumerate(pts))}" fill="none" '
            f'stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{d}></path>')
def svg(w, h, body, label):
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n' + "\n".join(body) + "\n</svg>"
def grid(o, x0, x1, Y, ticks, fmt, zero=None):
    for t in ticks:
        o.append(ln(x0, Y(t), x1, Y(t), AXIS if t == zero else GRID)); o.append(txt(x0 - 5, Y(t) + 4, fmt(t), "end", MONO, 12, MUT))

fits = [f for f in R["fits"] if f.get("fail", "") == ""]
by = lambda a: {f["participant"]: f for f in fits if int(f["angle"]) == a}
A0, A9 = by(0), by(90); ids = [i for i in A0 if i in A9]; n = len(ids); tc = tcrit(n - 1)
clipw = lambda v: min(max(v, 0.05), 3.0)

def paired_panel(w, h, vals0, vals9, Y, ticks, fmt, g0, g9, label, zero=None, glab=None, bench=None, xa=None, xb=None):
    """Participants as small paired dots, group estimates (m, lo, hi) as large dots with intervals."""
    L, Rm, Tp, B = 40, 10, 10, 26
    xa = xa or L + (w - L - Rm) * 0.38; xb = xb or L + (w - L - Rm) * 0.62; ga, gb = xa - (w * 0.17), xb + (w * 0.17)
    o = []; grid(o, L, w - Rm, Y, ticks, fmt, zero)
    for a, b in zip(vals0, vals9):
        o.append(ln(xa, Y(a), xb, Y(b), AXIS, 1))
    for a, b in zip(vals0, vals9):
        o.append(dot(xa, Y(a), BLUE, 3, False, 0.55)); o.append(dot(xb, Y(b), ORANGE, 3, False, 0.55))
    for gx, g, col, anc, off in ((ga, g0, BLUE, "end", -9), (gb, g9, ORANGE, "start", 9)):
        o.append(ln(gx, Y(g[1]), gx, Y(g[2]), col, 2)); o.append(dot(gx, Y(g[0]), col, 5))
        o.append(txt(gx + off, Y(g[0]) + 4, (glab or fmt)(g[0]), anc, SANS, 12, INK, 600))
    if bench:
        for gx, b in ((ga, bench[0]), (gb, bench[1])):
            o.append(ln(gx - 16, Y(b), gx + 16, Y(b), INK, 2, "2 3"))
    o.append(txt((xa + ga) / 2, h - 8, "0°", "middle")); o.append(txt((xb + gb) / 2, h - 8, "90°", "middle"))
    return svg(w, h, o, label)

# ── row 1 ───────────────────────────────────────────────────────────────────────
W3, W2, H1, H2, H3 = 223, 342, 160, 160, 150
c = R["checks"]["accuracy"]
Yacc = lambda v: (H1 - 26) - (v - 0.60) / 0.20 * (H1 - 36)
se = lambda sd: tc * sd / math.sqrt(n)
P = R["checks"]["acc_points"]
svg_acc = paired_panel(W3, H1, [p["a0"] for p in P], [p["a90"] for p in P], Yacc, [0.60, 0.70, 0.80], lambda t: nz(t),
                       (c["mean_a"], c["mean_a"] - se(c["sd_a"]), c["mean_a"] + se(c["sd_a"])), (c["mean_b"], c["mean_b"] - se(c["sd_b"]), c["mean_b"] + se(c["sd_b"])),
                       f"Accuracy by mapping: {nz(c['mean_a'])} at 0 degrees and {nz(c['mean_b'])} at 90 degrees, no difference.")

def conf_panel(a):
    w, h, L, Rm, Tp, B = W3, H1, 30, 36, 10, 26
    Y = lambda v: (h - B) - (v - 1) / 8 * (h - B - Tp); xs = [L + 22, (L + w - Rm) / 2, w - Rm - 22]
    o = []; grid(o, L, w - Rm, Y, [1, 3, 5, 7, 9], lambda t: str(t)); o.append(ln(L, Y(1), w - Rm, Y(1), AXIS))
    for i, s in enumerate(("none", "low", "high")):
        o.append(txt(xs[i], h - 8, s, "middle"))
    ends = {}
    for corr, dash in ((1, None), (0, "6 5")):
        cs = sorted([x for x in R["cells"] if x["angle"] == a and x["correct"] == corr], key=lambda x: x["level"])
        o.append(path([(xs[i], Y(cs[i]["mean"])) for i in range(3)], COL[a], dash))
        for i in range(3):
            o.append(ln(xs[i], Y(cs[i]["mean"] - cs[i]["ci"]), xs[i], Y(cs[i]["mean"] + cs[i]["ci"]), COL[a], 1.5))
        for i in range(3):
            o.append(dot(xs[i], Y(cs[i]["mean"]), COL[a] if corr else PAPER, 4, True, None, PAPER if corr else COL[a]))
        ends[corr] = cs[2]["mean"]; o.append(txt(xs[2] + 10, Y(cs[2]["mean"]) + 4, f"{cs[2]['mean']:.1f}", "start", SANS, 12, INK, 600))
    return svg(w, h, o, f"Confidence by evidence level at {a} degrees. After the strong sample, confidence is {ends[1]:.1f} for correct and {ends[0]:.1f} for incorrect choices."), ends
svg_c0, e0 = conf_panel(0); svg_c9, e9 = conf_panel(90)

# ── row 2 ───────────────────────────────────────────────────────────────────────
lo, hi = math.log(0.06), math.log(3.2)
Ywd = lambda v: (H2 - 26) - (math.log(v) - lo) / (hi - lo) * (H2 - 36)
h2, bb = T["H2_wd_both"], T["b_both"]; g = T["H1_by_angle"]; ge = lambda a: tuple(math.exp(x) for x in (g[a]["mean"], g[a]["ci"][0], g[a]["ci"][1]))
ideal = R.get("ideal"); boot = R.get("boot")
bench = (math.exp(ideal["by_angle"]["0"]["null_mean"]), math.exp(ideal["by_angle"]["90"]["null_mean"])) if ideal else None
svg_wd = paired_panel(W2, H2, [clipw(A0[i]["w_d_both"]) for i in ids], [clipw(A9[i]["w_d_both"]) for i in ids], Ywd, [0.125, 0.25, 0.5, 1, 2], lambda t: f"{t:g}",
                      ge("0"), ge("90"), f"Disconfirmatory weight by mapping: {ge('0')[0]:.2f} at 0 degrees, {ge('90')[0]:.2f} at 90 degrees.", zero=1,
                      glab=lambda v: f"{v:.2f}", bench=bench)
bs = [f["b_both"] for f in fits]; blo, bhi = min(-0.6, min(bs) - 0.1), max(1.4, max(bs) + 0.1)
Yb = lambda v: (H2 - 26) - (v - blo) / (bhi - blo) * (H2 - 36)
eb = lambda m, sd: (m, m - se(sd), m + se(sd))
svg_b = paired_panel(W2, H2, [A0[i]["b_both"] for i in ids], [A9[i]["b_both"] for i in ids], Yb, [t for t in (-0.5, 0, 0.5, 1.0) if blo <= t <= bhi], lambda t: num(t, 1),
                     eb(bb["mean_a"], bb["sd_a"]), eb(bb["mean_b"], bb["sd_b"]), f"Commitment by mapping: {bb['mean_a']:.2f} at 0 degrees, {bb['mean_b']:.2f} at 90 degrees.",
                     zero=0, glab=lambda v: num(v))

# ── row 3 (validation) ──────────────────────────────────────────────────────────
def scatter_wd():
    V = R["validation"]; w, h, L, Rm, Tp, B = W3, H3, 40, 10, 10, 30
    X = lambda v: L + (math.log(v) - lo) / (hi - lo) * (w - L - Rm); Y = lambda v: (h - B) - (math.log(v) - lo) / (hi - lo) * (h - B - Tp)
    o = []
    for t in (0.125, 0.5, 2):
        o.append(ln(L, Y(t), w - Rm, Y(t), GRID)); o.append(txt(L - 5, Y(t) + 4, f"{t:g}", "end", MONO, 12, MUT))
        o.append(ln(X(t), Tp, X(t), h - B, GRID)); o.append(txt(X(t), h - B + 14, f"{t:g}", "middle", MONO, 12, MUT))
    o.append(ln(X(0.07), Y(0.07), X(3), Y(3), AXIS, 1.25, "5 4"))
    for p in V["points"]:
        o.append(dot(X(p["wd_true"]), Y(clipw(p["wd_fit"])), COL[p["angle"]], 3.5, True))
    o.append(txt((L + w - Rm) / 2, h - 2, "put in", "middle", MONO, 12, MUT))
    return svg(w, h, o, f"Recovered against generating disconfirmatory weight, correlation {nz(V['r_wd'])}.")
def scatter_delta():
    d = R["validation"]["delta"]; w, h, L, Rm, Tp, B = W3, H3, 40, 10, 10, 30
    vals = [q for p in d["pairs"] for q in (p["true"], p["fit"])]; a, b = min(-2.0, min(vals) - .1), max(0.6, max(vals) + .1)
    X = lambda v: L + (v - a) / (b - a) * (w - L - Rm); Y = lambda v: (h - B) - (v - a) / (b - a) * (h - B - Tp)
    o = []
    for t in (-2, -1, 0):
        if a <= t <= b:
            o.append(ln(L, Y(t), w - Rm, Y(t), AXIS if t == 0 else GRID)); o.append(txt(L - 5, Y(t) + 4, num(t, 0), "end", MONO, 12, MUT))
            o.append(ln(X(t), Tp, X(t), h - B, AXIS if t == 0 else GRID)); o.append(txt(X(t), h - B + 14, num(t, 0), "middle", MONO, 12, MUT))
    o.append(ln(X(a), Y(a), X(b), Y(b), AXIS, 1.25, "5 4"))
    for p in d["pairs"]:
        o.append(dot(X(p["true"]), Y(p["fit"]), SEC, 3.5, True, 0.7))
    o.append(f'<rect x="{f1(X(d["true_mean"]) - 6)}" y="{f1(Y(d["fit_mean"]) - 6)}" width="12" height="12" fill="{INK}" stroke="{PAPER}" stroke-width="2"></rect>')
    o.append(txt((L + w - Rm) / 2, h - 2, "put in", "middle", MONO, 12, MUT))
    return svg(w, h, o, f"Recovered against generating difference between mappings: put in {d['true_mean']:.2f}, recovered {d['fit_mean']:.2f}.")
def hist_boot():
    w, h, L, Rm, Tp, B = W3, H3, 14, 10, 16, 30
    hist = boot["hist"]; mx = max(hist); X = lambda v: L + (v + 6) / 12 * (w - L - Rm); Y = lambda c: (h - B) - c / mx * (h - B - Tp)
    o = [ln(L, h - B, w - Rm, h - B, AXIS)]
    for i, cnt in enumerate(hist):
        if cnt:
            o.append(f'<rect x="{f1(X(-6 + i * .5) + 1)}" y="{f1(Y(cnt))}" width="{f1(X(.5) - X(0) - 2)}" height="{f1(h - B - Y(cnt))}" fill="{AXIS}"></rect>')
    for t in (-4, 0, 4):
        o.append(txt(X(t), h - B + 14, num(t, 0), "middle", MONO, 12, MUT))
    to = max(min(boot["t_obs"], 5.8), -5.8)
    o.append(ln(X(to), Tp - 4, X(to), h - B, INK, 2)); o.append(txt(X(to) + (7 if to < 0 else -7), Tp + 6, "observed", "start" if to < 0 else "end", SANS, 12, INK, 600))
    o.append(txt((L + w - Rm) / 2, h - 2, "t under the null", "middle", MONO, 12, MUT))
    return svg(w, h, o, f"Bootstrap distribution of the test statistic under the null hypothesis; the observed value {boot['t_obs']:.2f} lies in its tail.")

# ── assemble ────────────────────────────────────────────────────────────────────
EYE = f"font-family: {MONO}; font-size: 12px; line-height: 16px; letter-spacing: 0.08em; text-transform: uppercase; color: {MUT}"
NOTE = f"font-size: 12px; line-height: 16px; color: {MUT}"
sw = lambda col: f'<div style="width: 12px; height: 12px; border-radius: 3px; background: {col}"></div>'
key = lambda dash: (f'<svg width="22" height="8" viewBox="0 0 22 8" fill="none" aria-hidden="true"><line x1="1" y1="4" x2="21" y2="4" stroke="{INK}" stroke-width="2" '
                    f'stroke-linecap="round"' + (f' stroke-dasharray="{dash}"' if dash else "") + '></line></svg>')
def panel(title, s, cap1, cap2=None):
    c2 = f'\n<div style="{NOTE}">{cap2}</div>' if cap2 else ""
    return (f'<div style="flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; gap: 4px">\n'
            f'<div style="font-size: 14px; line-height: 18px; font-weight: 600">{title}</div>\n{s}\n'
            f'<div style="font-size: 13px; line-height: 17px; color: {SEC}">{cap1}</div>{c2}\n</div>')
def row(eyebrow, right, panels, extra=""):
    return (f'<div style="display: flex; flex-direction: column; gap: 8px">\n<div style="display: flex; justify-content: space-between; align-items: center; gap: 16px">\n'
            f'<div style="{EYE}">{eyebrow}</div>\n<div style="display: flex; gap: 12px; align-items: center; font-size: 12px; line-height: 16px; color: {SEC}">{right}</div>\n</div>\n'
            f'<div style="display: flex; gap: 14px">\n' + "\n".join(panels) + f'\n</div>{extra}\n</div>')
item = lambda inner, label: f'<div style="display: flex; gap: 6px; align-items: center">{inner}<div>{label}</div></div>'

ratio = math.exp(h2["mean"])
r1 = row("What the data look like", item(sw(BLUE), "0°") + item(sw(ORANGE), "90°") + item(key(None), "correct") + item(key("6 4"), "incorrect"),
         [panel("Accuracy", svg_acc, f"{nz(c['mean_a'])} at 0° · {nz(c['mean_b'])} at 90°", t_apa(c)),
          panel("Confidence (1–9) · 0°", svg_c0, f"Wrong choices end at {e0[0]:.1f}.", "evidence after the choice"),
          panel("Confidence (1–9) · 90°", svg_c9, f"Wrong choices end at {e9[0]:.1f}.", "evidence after the choice")])
r2 = row("Computational model", f'<div style="color: {MUT}">small: participants · large: group, 95 % CI' + (" · dotted: ideal observer" if ideal else "") + "</div>",
         [panel("Weight on disconfirming evidence, w<sub>d</sub>", svg_wd, f"{100 * (1 - ratio):.0f} % lower at 0° · {t_apa(h2)}",
                f"d<sub>z</sub> = {num(h2['d'])}" + (f" · bootstrap null: {p_apa(boot['p'])}" if boot else f" · 95 % CI [{num(h2['ci'][0])}, {num(h2['ci'][1])}]")),
          panel("Commitment to the choice, b", svg_b, f"No difference · {t_apa(bb)}", "as built in")])
rows = [r1, r2]
if SIM:
    V = R["validation"]; d = V["delta"]
    ps = [panel("w<sub>d</sub>: put in vs. recovered", scatter_wd(), f"r = {nz(V['r_wd'])}", "dashed: perfect recovery"),
          panel("Difference between mappings", scatter_delta(), f"put in {num(d['true_mean'])} · recovered {num(d['fit_mean'])}", "square: group mean")]
    if boot:
        ps.append(panel("Primary test against its null", hist_boot(), f"observed t = {num(boot['t_obs'])} · {p_apa(boot['p'])}", f"{boot['n']} simulated replications"))
    rows.append(row("Validation · what went in against what came out", f'<div style="color: {MUT}">log scale for weights</div>', ps))
    lv = V["params"]
    concl = ("The built-in difference between mappings is recovered. The level of w<sub>d</sub> comes out too low "
             "and is judged against an ideal observer run through the same analysis.")
else:
    concl = f"Disconfirming evidence was used {100 * (1 - ratio):.0f} % less under the direct mapping, {t_apa(h2)}."

html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{"Simulated results — validation poster" if SIM else "A Second Look — results poster"}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@500;600&display=swap">
<style>
body{{margin:0;background:{PAPER}}}
</style>
</helmet>
<div style="width: 794px; height: 1123px; box-sizing: border-box; padding: 46px 48px 40px; display: flex; flex-direction: column; justify-content: space-between; background: {PAPER}; color: {INK}; font-family: 'IBM Plex Sans', 'Helvetica Neue', Helvetica, sans-serif">

<div style="display: flex; flex-direction: column; gap: 10px">
<div style="display: flex; justify-content: space-between; align-items: center; gap: 16px">
<div style="{EYE}">A Second Look · work package 3 · {"validation run" if SIM else "results"}</div>
{f'<div style="font-family: {MONO}; font-size: 12px; line-height: 16px; letter-spacing: 0.08em; text-transform: uppercase; color: {INK}; border: 1.5px solid {INK}; border-radius: 4px; padding: 2px 8px">Simulated data · N = {n}</div>' if SIM else f'<div style="{EYE}">N = {n}</div>'}
</div>
<h1 style="margin: 0; font-family: 'IBM Plex Serif', Georgia, serif; font-weight: 600; font-size: 76px; line-height: 78px; letter-spacing: -0.02em">{"Simulated Results" if SIM else "A Second Look"}</h1>
<p style="margin: 0; max-width: 670px; font-size: 21px; line-height: 29px; color: {SEC}; text-wrap: pretty">{"What the planned analysis returns when the hypothesis is true: ten simulated participants with known parameters." if SIM else "Confidence in our own control after evidence that arrives too late to change the choice."}</p>
</div>

{chr(10).join(rows)}

<div style="box-sizing: border-box; padding: 12px 16px; border-radius: 8px; background: #ECEEF0; font-size: 15px; line-height: 22px">{concl}</div>

</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":794,"height":1123}}}}'>
class Component extends DCLogic {{
renderVals() {{
return {{}};
}}
}}
</script>
</body>
</html>
'''
assert "{{" not in html.split("<script type")[0]
open(OUT, "w", encoding="utf-8").write(html)
print(f"[poster] {OUT}  {len(html.encode()) // 1024} KB · svg {html.count('<svg ')}/{html.count('</svg>')} · div {html.count('<div')}/{html.count('</div>')}")
