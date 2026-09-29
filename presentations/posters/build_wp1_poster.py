#!/usr/bin/env python3
"""Build the WP1 results poster ("Expecting Control") from a results bundle.

    python build_wp1_poster.py wp1_results.json OUT/Experiment1.dc.html

Every number and every chart comes from the bundle; nothing on the poster is typed by hand
except the closing sentence, which is read from bundle["conclusion"] so that it has to be
reconsidered whenever the results change. Same format as the "A Second Look" poster:
A4 portrait (794 x 1123 px), IBM Plex, blue = 0 deg, orange = 90 deg.
"""
import json, math, sys

BLUE, ORANGE, INK, SEC, MUT, GRID, AXIS, PAPER = "#2A78D6", "#D95926", "#15181C", "#2B3036", "#4A5058", "#DDE0E3", "#9AA1A9", "#FAFAF7"
MONO = "'IBM Plex Mono', Menlo, monospace"
SANS = "'IBM Plex Sans', Helvetica, sans-serif"
EYE = f"font-family: {MONO}; font-size: 12px; line-height: 16px; letter-spacing: 0.08em; text-transform: uppercase; color: {MUT}"

r1 = lambda v: f"{v:.1f}"
sg = lambda v, d=2: f"{v:+.{d}f}".replace("-", "−")            # signed, typographic minus
nm = lambda v, d=2: f"{v:.{d}f}".replace("-", "−")


def lead0(s):
    """.013 instead of 0.013, but 1.00 stays 1.00."""
    return s[1:] if s.startswith("0") else s


def pfmt(p):
    """APA style: three decimals below .10, where the third one matters."""
    if p != p:
        return "p n/a"
    if p < .001:
        return "p &lt; .001"
    return "p = " + lead0(f"{p:.3f}" if p < .10 else f"{p:.2f}")


def txt(x, y, t, anchor="start", fam=SANS, size=12, fill=SEC, weight=None):
    w = f' font-weight="{weight}"' if weight else ""
    return f'<text x="{r1(x)}" y="{r1(y)}" text-anchor="{anchor}" font-family="{fam}" font-size="{size}"{w} fill="{fill}">{t}</text>'


def line(x1, y1, x2, y2, stroke, sw=1):
    return f'<line x1="{r1(x1)}" y1="{r1(y1)}" x2="{r1(x2)}" y2="{r1(y2)}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"></line>'


def dot(x, y, fill, r=4):
    return f'<circle cx="{r1(x)}" cy="{r1(y)}" r="{r}" fill="{fill}" stroke="{PAPER}" stroke-width="2"></circle>'


def nice_axis(lo, hi, n=3):
    """Round tick positions that enclose [lo, hi]."""
    span = hi - lo
    step = min((s for s in (.01, .02, .05, .1, .2, .25, .5, 1, 2) if span / s <= n + 1), default=2)
    a, b = math.floor(lo / step) * step, math.ceil(hi / step) * step
    ticks = [round(a + i * step, 4) for i in range(int(round((b - a) / step)) + 1)]
    return a - step * .15, b + step * .15, ticks


def cue_panel(series, tfmt, aria, w=223, h=150):
    """series: [(colour, (mean, lo, hi) at low cue, (mean, lo, hi) at high cue)] for 0 deg, 90 deg."""
    L, R, T, B = 40, 10, 10, 30
    x0, x1, y0, y1 = L, w - R, T, h - B
    vals = [v for _, lo, hi in series for v in lo[1:] + hi[1:]]
    ymin, ymax, ticks = nice_axis(min(vals), max(vals))
    Y = lambda v: y1 - (v - ymin) / (ymax - ymin) * (y1 - y0)
    xl, xh = x0 + (x1 - x0) * .27, x0 + (x1 - x0) * .73
    o = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{aria}">']
    for t in ticks:
        o += [line(x0, Y(t), x1, Y(t), GRID), txt(x0 - 5, Y(t) + 4, tfmt(t), "end", MONO, 12, MUT)]
    o += [line(x0, y1, x1, y1, AXIS), txt(xl, h - 10, "low cue", "middle"), txt(xh, h - 10, "high cue", "middle")]
    for i, (col, lo, hi) in enumerate(series):
        dx = -5 if i == 0 else 5                                   # dodge so the intervals do not overlap
        o.append(line(xl + dx, Y(lo[0]), xh + dx, Y(hi[0]), col, 2))
        o += [line(x, Y(a), x, Y(b), col, 1.5) for x, (_, a, b) in ((xl + dx, lo), (xh + dx, hi))]
    for i, (col, lo, hi) in enumerate(series):
        dx = -5 if i == 0 else 5
        o += [dot(xl + dx, Y(lo[0]), col), dot(xh + dx, Y(hi[0]), col)]
    return "\n".join(o + ["</svg>"])


def forest(C, w=223, h=150):
    L, R, T, B = 92, 10, 10, 30
    x0, x1, y0, y1 = L, w - R, T, h - B
    rows = [("drift · 0°", "v_0", BLUE), ("drift · 90°", "v_90", ORANGE), ("boundary · 0°", "a_0", BLUE), ("boundary · 90°", "a_90", ORANGE)]
    ext = max(abs(v) for _, k, _ in rows for v in C[k]["hdi95"])
    xmin, xmax = -ext * 1.15, ext * 1.15
    X = lambda v: x0 + (v - xmin) / (xmax - xmin) * (x1 - x0)
    tick = .1 if ext >= .1 else .05
    o = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Effect of the high cue on drift and boundary at each rotation, posterior mean with 50 and 95 percent intervals.">']
    for t in (-tick, 0.0, tick):
        o += [line(X(t), y0, X(t), y1, AXIS if t == 0 else GRID), txt(X(t), h - 10, "0" if t == 0 else sg(t, 2 if tick < .1 else 1), "middle", MONO, 12, MUT)]
    step = (y1 - y0) / len(rows)
    for i, (lab, k, col) in enumerate(rows):
        c, yy = C[k], y0 + step * (i + .5)
        o += [txt(L - 8, yy + 4, lab, "end"), line(X(c["hdi95"][0]), yy, X(c["hdi95"][1]), yy, col, 1.5),
              line(X(c["hdi50"][0]), yy, X(c["hdi50"][1]), yy, col, 4), dot(X(c["mean"]), yy, col)]
    return "\n".join(o + ["</svg>"])


def mratio_axis(vals):
    lo, hi = min(vals + [.5]), max(vals + [1.0])
    return nice_axis(lo, hi, 4)


def mratio_rotation(md, w=342, h=140):
    ind = {}
    for r in md["indiv"]:
        ind.setdefault(r["subject"], {})[r["cond"]] = math.exp(r["logM_shrunk"])
    pairs = [(v[0], v[90]) for v in ind.values() if 0 in v and 90 in v]
    g0, g90 = [[math.exp(x) for x in md["summary"][k]] for k in ("mu0", "mu90")]
    ymin, ymax, ticks = mratio_axis([x for p in pairs for x in p] + g0 + g90)
    L, R, T, B = 40, 12, 10, 30
    x0, x1, y0, y1 = L, w - R, T, h - B
    Y = lambda v: y1 - (v - ymin) / (ymax - ymin) * (y1 - y0)
    xa, xb, ga, gb = 150, 232, 92, 290
    o = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Metacognitive efficiency by rotation: group M-ratio {g0[1]:.2f} at 0 degrees and {g90[1]:.2f} at 90 degrees, with participants as small dots.">']
    for t in ticks:
        o += [line(x0, Y(t), x1, Y(t), AXIS if t == 1 else GRID), txt(x0 - 5, Y(t) + 4, f"{t:.2f}", "end", MONO, 12, MUT)]
    o.append(line(x0, y1, x1, y1, AXIS))
    o += [line(xa, Y(a), xb, Y(b), AXIS, 1) for a, b in pairs]
    for a, b in pairs:
        o.append(f'<circle cx="{xa}" cy="{r1(Y(a))}" r="3" fill="{BLUE}" fill-opacity="0.55"></circle>')
        o.append(f'<circle cx="{xb}" cy="{r1(Y(b))}" r="3" fill="{ORANGE}" fill-opacity="0.55"></circle>')
    for gx, g, col, anchor, off in ((ga, g0, BLUE, "end", -10), (gb, g90, ORANGE, "start", 10)):
        o += [line(gx, Y(g[0]), gx, Y(g[2]), col, 2), dot(gx, Y(g[1]), col, 5), txt(gx + off, Y(g[1]) + 4, f"{g[1]:.2f}", anchor, SANS, 12, INK, 600)]
    o += [txt((ga + xa) / 2, h - 10, "0°", "middle"), txt((gb + xb) / 2, h - 10, "90°", "middle")]
    return "\n".join(o + ["</svg>"])


def mratio_cue(bc, w=342, h=140):
    ymin, ymax, ticks = mratio_axis(bc["low"] + bc["high"])
    L, R, T, B = 40, 12, 10, 30
    x0, x1, y0, y1 = L, w - R, T, h - B
    Y = lambda v: y1 - (v - ymin) / (ymax - ymin) * (y1 - y0)
    xa, xb = 130, 252
    o = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Metacognitive efficiency by cue: group M-ratio {bc["low"][1]:.2f} under the low cue and {bc["high"][1]:.2f} under the high cue.">']
    for t in ticks:
        o += [line(x0, Y(t), x1, Y(t), AXIS if t == 1 else GRID), txt(x0 - 5, Y(t) + 4, f"{t:.2f}", "end", MONO, 12, MUT)]
    o += [line(x0, y1, x1, y1, AXIS), line(xa, Y(bc["low"][1]), xb, Y(bc["high"][1]), INK, 2)]
    for gx, g in ((xa, bc["low"]), (xb, bc["high"])):
        o += [line(gx, Y(g[0]), gx, Y(g[2]), INK, 2), dot(gx, Y(g[1]), INK, 5), txt(gx + 10, Y(g[1]) - 8, f"{g[1]:.2f}", "start", SANS, 12, INK, 600)]
    o += [txt(xa, h - 10, "low cue", "middle"), txt(xb, h - 10, "high cue", "middle")]
    return "\n".join(o + ["</svg>"])


def stats_block(a):
    """Always shown under the main-result plots: the cue effect at each rotation, then the ANOVA."""
    row = lambda lab, val: (f'<div style="display: flex; justify-content: space-between; gap: 8px"><div>{lab}</div>'
                            f'<div style="font-family: {MONO}">{val}</div></div>')
    return (f'<div style="display: flex; flex-direction: column; font-size: 12px; line-height: 16px; color: {SEC}">\n'
            + row("cue at 90°", f'{sg(a["eff90"]["M"])} · {pfmt(a["eff90"]["p"])}') + "\n"
            + row("cue at 0°", f'{sg(a["eff0"]["M"])} · {pfmt(a["eff0"]["p"])}') + "\n"
            + f'<div style="display: flex; flex-direction: column; margin-top: 3px; padding-top: 3px; border-top: 1px solid #C2C7CD">\n'
            + row("cue", pfmt(a["cue"]["p"])) + "\n" + row("rotation", pfmt(a["angle"]["p"])) + "\n"
            + row("cue × rotation", pfmt(a["interaction"]["p"])) + "\n</div>\n</div>")


def panel(title, svg, below):
    if not below.startswith("<div"):
        below = f'<div style="font-size: 13px; line-height: 17px; color: {SEC}">{below}</div>'
    return (f'<div style="flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; gap: 4px">\n'
            f'<div style="font-size: 14px; line-height: 18px; font-weight: 600">{title}</div>\n{svg}\n{below}\n</div>')


def excludes_zero(c):
    return c["hdi95"][0] > 0 or c["hdi95"][1] < 0


def build(B):
    S, D, md = B["stats"], B["ddm"], B["metad"]
    cells = lambda k: [(BLUE,) + tuple((S[k]["means"][c], S[k]["means"][c] - S[k]["ci"][c], S[k]["means"][c] + S[k]["ci"][c]) for c in ("0_low", "0_high")),
                       (ORANGE,) + tuple((S[k]["means"][c], S[k]["means"][c] - S[k]["ci"][c], S[k]["means"][c] + S[k]["ci"][c]) for c in ("90_low", "90_high"))]
    post = lambda p: [(BLUE,) + tuple((D["params"][f"{p}_0_{c}"]["mean"], *D["params"][f"{p}_0_{c}"]["hdi95"]) for c in ("low", "high")),
                      (ORANGE,) + tuple((D["params"][f"{p}_90_{c}"]["mean"], *D["params"][f"{p}_90_{c}"]["hdi95"]) for c in ("low", "high"))]
    main = "\n".join(panel(t, cue_panel(cells(k), f, f"{t} by cue and rotation, group means with 95 percent confidence intervals."), stats_block(S[k]["anova"]))
                     for t, k, f in (("Sense of agency (1–7)", "agency_rating", lambda v: f"{v:.1f}"),
                                     ("Confidence (1–4)", "confidence_rating", lambda v: f"{v:.1f}"),
                                     ("Accuracy", "accuracy", lambda v: f"{v:.2f}"[1:])))
    pr, bc = md["paired"], B["mratio_by_cue"]
    prob = lambda v: lead0("%.2f" % v)
    span = lambda d: "Δ log M = %s [%s, %s]" % (sg(d[1]), nm(d[0]), nm(d[2]))
    meta = "\n".join((panel("By rotation", mratio_rotation(md), span(pr["diff"]) + " · P(90° &gt; 0°) = " + prob(pr["p_gt0"])),
                      panel("By cue", mratio_cue(bc), span(bc["paired_dlogM"]) + " · P(high &gt; low) = " + prob(bc["p_gt0"]))))
    C = D["contrasts"]
    verdict = lambda a, b, what: f"{what} unchanged." if not (excludes_zero(C[a]) or excludes_zero(C[b])) else f"{what} shifts with the cue."
    k = sum(excludes_zero(C[x]) for x in ("v_0", "v_90", "a_0", "a_90"))
    ddm = "\n".join((panel("Drift rate", cue_panel(post("v"), lambda v: f"{v:.2f}"[1:], "Drift rate by cue and rotation, posterior mean with 95 percent interval."), verdict("v_0", "v_90", "Evidence quality")),
                     panel("Boundary separation", cue_panel(post("a"), lambda v: f"{v:.2f}", "Boundary separation by cue and rotation, posterior mean with 95 percent interval."), verdict("a_0", "a_90", "Caution")),
                     panel("Effect of the high cue", forest(C), "All 95 % intervals include 0." if k == 0 else f"{k} of 4 intervals exclude 0.")))
    cmp_ = sorted(D["compare"], key=lambda c: c["diff"])
    names = dict(null="null", drift="drift", full="full", bound="boundary")
    loo = f'LOO: {names[cmp_[0]["model"]]} model best · ' + " · ".join(f'{names[c["model"]]} +{c["diff"]:.1f} ± {c["dse"]:.1f}' for c in cmp_[1:])
    sw = lambda col: f'<div style="width: 12px; height: 12px; border-radius: 3px; background: {col}"></div>'
    head = lambda left, right: (f'<div style="display: flex; justify-content: space-between; align-items: center; gap: 16px">\n'
                                f'<div style="{EYE}">{left}</div>\n{right}\n</div>')
    note = lambda t: f'<div style="font-size: 12px; line-height: 16px; color: {MUT}">{t}</div>'
    legend = (f'<div style="display: flex; gap: 14px; align-items: center; font-size: 12px; line-height: 16px; color: {SEC}">\n'
              f'<div style="display: flex; gap: 6px; align-items: center">{sw(BLUE)}<div>0°</div></div>\n'
              f'<div style="display: flex; gap: 6px; align-items: center">{sw(ORANGE)}<div>90°</div></div>\n'
              f'<div style="color: {MUT}">mean ± 95 % CI</div>\n</div>')
    section = lambda h, body, extra="": ('<div style="display: flex; flex-direction: column; gap: 8px">\n' + h
                                         + '\n<div style="display: flex; gap: 14px">\n' + body + "\n</div>" + extra + "\n</div>")
    sec_main = section(head("Main result · same objective control", legend), main)
    sec_meta = section(head("Metacognitive efficiency · M-ratio · N = %d" % md.get("n", B["N"]), note("large: group, 95 % interval · small: participants")), meta)
    loo_line = '\n<div style="font-family: ' + MONO + '; font-size: 12px; line-height: 16px; color: ' + MUT + '">' + loo + "</div>"
    sec_ddm = section(head("Drift-diffusion model · N = %d · %s trials" % (D.get("n_participants", B["N"]), format(D["n_trials"], ",")), note("posterior mean, 95 % interval")), ddm, loo_line)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Expecting Control — results poster</title>
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
<div style="{EYE}">Work package 1 · lab experiment · N = {B["N"]} · {B.get("updated", "")}</div>
<h1 style="margin: 0; font-family: 'IBM Plex Serif', Georgia, serif; font-weight: 600; font-size: 76px; line-height: 78px; letter-spacing: -0.02em">Expecting Control</h1>
<p style="margin: 0; max-width: 670px; font-size: 21px; line-height: 29px; color: {SEC}; text-wrap: pretty">Does expecting control change how much control we feel, and how sure we are of it?</p>
</div>

{sec_main}

{sec_meta}

{sec_ddm}

<div style="box-sizing: border-box; padding: 12px 16px; border-radius: 8px; background: #ECEEF0; font-size: 16px; line-height: 24px">{B["conclusion"]}</div>

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


if __name__ == "__main__":
    bundle = json.load(open(sys.argv[1]))
    html = build(bundle)
    markup = html.split("<script type")[0]
    assert "{{" not in markup, "double braces would be read as template holes"
    assert markup.count("<div") == markup.count("</div>") and markup.count("<svg ") == markup.count("</svg>"), "unbalanced markup"
    open(sys.argv[2], "w", encoding="utf-8").write(html)
    print(f"poster built for N = {bundle['N']} -> {sys.argv[2]} ({len(html.encode()) // 1024} KB)")
