#!/usr/bin/env python3
"""Running overview of all WP3 data collected so far: one self-contained HTML page (the "poster" the
team checks after every new data set). Works from the first pilot file on.

  1. Inventory          files, builds, test vs. study participants, session length
  2. Quality            per-participant flags exactly as the planned analysis applies them
  3. Does the task work 1-up-2-down and delta tracks per participant, accuracy against both targets,
                        accuracy by strength, choice and rating times
  4. Behaviour          mean confidence by evidence level x correctness x mapping (Rollwage Fig 4B analog)
  5. Planned tests      wp3_paper_analysis.py on the included participants (H1, H2 primary, b, checks);
                        shown as "waiting" until enough people are in
  6. Canvas posters     poster 2 ("What we expect") with observed data and the ideal observer, and poster 3
                        (wp3_poster.py on the results; the simulated one from --sim-results until then)

Descriptives use every participant with data (excluded ones drawn hollow); the planned tests use only
the included ones. Test runs (participant id starting with "test", or no Prolific id) are labelled as
such and never counted toward the study sample.

  python wp3_overview.py DATA_DIR OUT.html [--boot 300] [--sim-results results.json]
"""
import argparse, datetime as dt, html, json, pathlib, subprocess, sys, tempfile, warnings
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import analyze_wp3 as A             # noqa: E402
import fit_wp3_model as F           # noqa: E402
import wp3_paper_analysis as W      # noqa: E402

ANGLES = (0, 90)
N_PLANNED, N_ANALYSABLE = 150, 127      # design doc §10h
MIN_FOR_TESTS = 3                       # paired t-tests need at least three included people
MAX_TRACES = 12                         # per-person small multiples; beyond that only group summaries

esc = html.escape
f1 = lambda v: f"{v:.1f}"
def num(x, d=2):
    return "–" if x is None or not np.isfinite(x) else f"{x:.{d}f}".replace("-", "−")
def pct(x):
    return "–" if x is None or not np.isfinite(x) else f"{100 * x:.0f} %"
def p_fmt(p):
    return "p < .001" if p < .001 else "p = " + f"{p:.3f}".lstrip("0")


# ── data ────────────────────────────────────────────────────────────────────────

def load(path):
    df = W.load(path)
    if "trial_idx" not in df.columns:                  # lab and simulated files: file order
        df["trial_idx"] = df.groupby("participant").cumcount() + 1
    df["is_test"] = df.participant.str.lower().str.startswith("test")
    if "prolific_session_id" in df.columns:
        df["is_test"] |= df.groupby("participant").prolific_session_id.transform(lambda s: s.isna().all())
    return df


def first(dp, col):
    return dp[col].iloc[0] if col in dp.columns and len(dp) else np.nan


# ── SVG helpers (colours come from CSS classes, so both themes work) ────────────

class Plot:
    """A plot area with linear scales; everything is drawn in viewBox units."""
    def __init__(self, w, h, x0, x1, y0, y1, pad=(14, 12, 34, 44)):
        self.w, self.h, self.pt, self.pr, self.pb, self.pl = w, h, *pad
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        self.el = []
    def X(self, v): return self.pl + (v - self.x0) / (self.x1 - self.x0) * (self.w - self.pl - self.pr)
    def Y(self, v): return self.h - self.pb - (v - self.y0) / (self.y1 - self.y0) * (self.h - self.pt - self.pb)
    def add(self, s): self.el.append(s)
    def grid_y(self, ticks, fmt=lambda v: f"{v:g}", label=None):
        for t in ticks:
            self.add(f'<line class="grid" x1="{f1(self.pl)}" x2="{f1(self.w - self.pr)}" y1="{f1(self.Y(t))}" y2="{f1(self.Y(t))}"/>')
            self.add(f'<text class="tick" x="{f1(self.pl - 6)}" y="{f1(self.Y(t) + 4)}" text-anchor="end">{fmt(t)}</text>')
        if label:
            self.add(f'<text class="axl" transform="translate(12 {f1((self.pt + self.h - self.pb) / 2)}) rotate(-90)" text-anchor="middle">{label}</text>')
    def ticks_x(self, ticks, fmt=lambda v: f"{v:g}", label=None):
        yb = self.h - self.pb
        self.add(f'<line class="axis" x1="{f1(self.pl)}" x2="{f1(self.w - self.pr)}" y1="{f1(yb)}" y2="{f1(yb)}"/>')
        for t in ticks:
            self.add(f'<text class="tick" x="{f1(self.X(t))}" y="{f1(yb + 15)}" text-anchor="middle">{fmt(t)}</text>')
        if label:
            self.add(f'<text class="axl" x="{f1((self.pl + self.w - self.pr) / 2)}" y="{f1(self.h - 4)}" text-anchor="middle">{label}</text>')
    def ref(self, v, label):
        y = self.Y(v)
        self.add(f'<line class="ref" x1="{f1(self.pl)}" x2="{f1(self.w - self.pr)}" y1="{f1(y)}" y2="{f1(y)}"/>')
        self.add(f'<text class="reft" x="{f1(self.w - self.pr)}" y="{f1(y - 4)}" text-anchor="end">{label}</text>')
    def line(self, pts, cls):
        pts = [(x, y) for x, y in pts if np.isfinite(y)]
        if len(pts) > 1:
            d = " ".join(("M" if i == 0 else "L") + f"{f1(self.X(x))} {f1(self.Y(y))}" for i, (x, y) in enumerate(pts))
            self.add(f'<path class="{cls}" d="{d}"/>')
    def dot(self, x, y, cls, r=4, tip=None):
        if not np.isfinite(y):
            return
        t = f"<title>{esc(tip)}</title>" if tip else ""
        self.add(f'<circle class="{cls}" cx="{f1(self.X(x))}" cy="{f1(self.Y(y))}" r="{r}">{t}</circle>')
    def text(self, x, y, s, cls="lab", anchor="start"):
        self.add(f'<text class="{cls}" x="{f1(x)}" y="{f1(y)}" text-anchor="{anchor}">{s}</text>')
    def svg(self, title):
        return (f'<svg viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{esc(title)}">'
                + "".join(self.el) + "</svg>")


def legend():
    return ('<div class="legend"><span><i class="sw c0"></i>0° (direkte Zuordnung)</span>'
            '<span><i class="sw c90"></i>90° (rotierte Zuordnung)</span>'
            '<span><i class="sw hollow"></i>ausgeschlossen / Test</span></div>')


# ── panels ──────────────────────────────────────────────────────────────────────

def quality_table(df, q, fits, tests):
    rows = []
    for pid, dp in df.groupby("participant", sort=False):
        r = q[q.participant == pid]
        r = r.iloc[0] if len(r) else None
        flags = [] if r is None else [c for c in r.index if c not in W.QUALITY_INFO and c != "excluded" and bool(r[c])]
        names = dict(acc_out_of_range="Genauigkeit außerhalb 60–85 %", block_acc_out="Block-Genauigkeit außerhalb 55–85 %",
                     conf_degenerate="eine Konfidenzstufe > 90 %", conf_rt_too_fast="Konfidenz-RT < 850 ms",
                     too_many_timeouts="Timeouts > 5 %", failed_instruction_check="Instruktionscheck",
                     not_mouse_only="nicht nur Maus", no_pointer_lock="kein Pointer Lock",
                     low_frame_rate="fps < 50", too_little_movement="zu wenig Bewegung")
        fl = ", ".join(names.get(f, f) for f in flags) or "keine"
        fit = fits[fits.participant == pid]
        fit_s = "–" if fit.empty else ("ok" if (fit.fail == "").all() else
                                       ", ".join(sorted(set(f.replace("too_few_trials", "zu wenige Trials") for f in fit.fail if f))))
        status = ('<span class="pill test">Test</span>' if pid in tests else
                  '<span class="pill out">ausgeschlossen</span>' if r is not None and r.excluded else
                  '<span class="pill in">eingeschlossen</span>')
        start = str(first(dp, "started_at"))[:16].replace("T", " ") if "started_at" in dp.columns else "–"
        rows.append(f"<tr><td class='mono'>{esc(pid)}</td><td>{status}</td><td class='mono'>{esc(str(first(dp, 'build')))}</td>"
                    f"<td class='mono'>{esc(start)}</td><td class='n'>{num(float(first(dp, 'duration_min')), 1)}</td>"
                    f"<td class='n'>{pct(r.acc_0) if r is not None else '–'}</td><td class='n'>{pct(r.acc_90) if r is not None else '–'}</td>"
                    f"<td class='n'>{pct(r.timeouts) if r is not None else '–'}</td>"
                    f"<td class='n'>{num(r.median_conf_rt, 2) if r is not None else '–'}</td>"
                    f"<td>{esc(fl)}</td><td>{esc(fit_s)}</td></tr>")
    return ("<div class='tablewrap'><table><thead><tr><th>ID</th><th>Status</th><th>Build</th><th>Start (UTC)</th>"
            "<th class='n'>Dauer min</th><th class='n'>Acc 0°</th><th class='n'>Acc 90°</th><th class='n'>Timeouts</th>"
            "<th class='n'>Konf.-RT s</th><th>Ausschlussgründe</th><th>Modellfit</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>"
            "<p class='note'>Genauigkeit, Timeouts und Konfidenz-RT über Standardtrials (Task 1 + 2), wie in der geplanten Analyse. "
            "Ausschlussgründe = <code>exclusion_flags</code> + Block-Fenster; der Modellfit braucht ≥ 10 Task-1-Trials, "
            "genug Fehler in Task 2 und ≥ 8 Stärketrials pro Zuordnung.</p>")


def track_panel(dp, ang, cls):
    """Staircase (standard prop) and the high strength of strength trials over the block."""
    d = dp[dp.angle_bias == ang].sort_values("trial_idx")
    if d.empty:
        return ""
    idx = np.arange(len(d))
    p = Plot(480, 210, 0, max(len(d) - 1, 1), 0, 1)
    p.grid_y([0, .25, .5, .75, 1], lambda v: f"{v:.2f}".lstrip("0") if v not in (0, 1) else f"{v:g}", "Eigenanteil")
    p.ticks_x([0, len(d) - 1], lambda v: f"{int(v) + 1}", "Trial im Block")
    std = d.trial_type.ne("strength").values
    p.line(list(zip(idx[std], d.prop_used.values[std])), f"trace {cls}")
    for i, (_, r) in enumerate(d.iterrows()):
        st = r.trial_type == "strength"
        k = f"pt {cls}" + (" strength" if st else "")
        tip = f"{r.phase} · Eigenanteil {r.prop_used:.2f} · " + ("Timeout" if r.is_timeout else ("richtig" if r.accuracy == 1 else "falsch"))
        if r.is_timeout:
            p.add(f'<text class="tmark" x="{f1(p.X(i))}" y="{f1(p.Y(r.prop_used) + 4)}" text-anchor="middle">×<title>{esc(tip)}</title></text>')
        else:
            p.dot(i, r.prop_used, k + (" err" if r.accuracy == 0 else ""), r=3.2 if st else 2.6, tip=tip)
    for k, (ph, lab) in enumerate((("calibration_strength", "Stärke-Kal."), ("wp3_task1", "Task 1"), ("wp3_task2", "Task 2"))):
        m = np.where(d.phase.values == ph)[0]
        if len(m):
            x = p.X(m[0] - .5)
            p.add(f'<line class="phase" x1="{f1(x)}" x2="{f1(x)}" y1="{p.pt}" y2="{f1(p.h - p.pb)}"/>')
            p.text(x + 3, p.pt + 9 + 12 * (k % 2), lab, "phl")      # staggered: phases can be close together
    return p.svg(f"Treppe {ang}°")


def delta_panel(dp, ang, cls):
    d = dp[(dp.angle_bias == ang) & (dp.trial_type == "strength")].sort_values("trial_idx")
    if d.empty or "delta_live" not in d.columns:
        return ""
    v = pd.to_numeric(d.delta_live, errors="coerce").values
    p = Plot(480, 150, 0, max(len(v) - 1, 1), 0, 2)
    p.grid_y([0, 1, 2], label="δ (Logit)")
    p.ticks_x([0, len(v) - 1], lambda x: f"{int(x) + 1}", "Stärketrial")
    p.line(list(enumerate(v)), f"trace {cls}")
    for i, (val, a) in enumerate(zip(v, d.accuracy.values)):
        p.dot(i, val, f"pt {cls}" + (" err" if a == 0 else ""), 2.8, f"δ {val:.2f} · {'richtig' if a == 1 else 'falsch' if a == 0 else 'Timeout'}")
    return p.svg(f"Delta-Spur {ang}°")


def accuracy_panel(df, excl):
    """Accuracy per person and mapping: standard trials vs. strength trials, against their targets."""
    v = df[df.phase.str.startswith("wp3_task") & ~df.is_timeout & df.accuracy.notna()]
    p = Plot(420, 230, -0.5, 3.5, 0.4, 1.0)
    p.grid_y([.4, .5, .6, .7, .8, .9, 1], lambda x: f"{100 * x:.0f}", "Genauigkeit (%)")
    p.ticks_x([0, 1, 2, 3], lambda x: ["0° Standard", "90° Standard", "0° Stärke", "90° Stärke"][int(x)])
    p.add(f'<line class="ref" x1="{f1(p.X(-.4))}" x2="{f1(p.X(1.4))}" y1="{f1(p.Y(.707))}" y2="{f1(p.Y(.707))}"/>')
    p.text(p.X(-.4), p.Y(.707) - 4, "Ziel 70,7 %", "reft")
    p.add(f'<line class="ref" x1="{f1(p.X(1.6))}" x2="{f1(p.X(3.4))}" y1="{f1(p.Y(.85))}" y2="{f1(p.Y(.85))}"/>')
    p.text(p.X(1.6), p.Y(.85) - 4, "Ziel 85 %", "reft")
    rng = np.random.default_rng(3)
    for k, (tt, ang) in enumerate([("standard", 0), ("standard", 90), ("strength", 0), ("strength", 90)]):
        s = v[(v.trial_type == tt) & (v.angle_bias == ang)].groupby("participant").accuracy.agg(["mean", "size"])
        cls = "c0" if ang == 0 else "c90"
        for pid, r in s.iterrows():
            ho = pid in excl
            p.dot(k + rng.uniform(-.18, .18), max(r["mean"], .4), f"{'pth' if ho else 'pt'} {cls}", 3.5,
                  f"{pid}: {100 * r['mean']:.0f} % von {int(r['size'])} Trials")
        inc = s[~s.index.isin(excl)]["mean"]
        if len(inc):
            m = inc.mean()
            p.add(f'<line class="mean {cls}" x1="{f1(p.X(k - .3))}" x2="{f1(p.X(k + .3))}" y1="{f1(p.Y(m))}" y2="{f1(p.Y(m))}"/>')
    return p.svg("Genauigkeit gegen Zielwerte")


def psychometric_panel(df):
    v = df[df.prop_used.notna() & ~df.is_timeout & df.accuracy.notna()]
    bins = np.array([0, .15, .25, .35, .45, .55, .65, .75, .95])
    p = Plot(420, 230, 0, .95, 0.4, 1.0)
    p.grid_y([.4, .5, .6, .7, .8, .9, 1], lambda x: f"{100 * x:.0f}", "Genauigkeit (%)")
    p.ticks_x([0, .2, .4, .6, .8], lambda x: f"{x:.1f}", "Eigenanteil der Bewegung (alle Entscheidungstrials)")
    p.ref(.5, "Zufall")
    for ang, cls, off in ((0, "c0", -.006), (90, "c90", .006)):
        d = v[v.angle_bias == ang]
        g = d.groupby(pd.cut(d.prop_used, bins)).accuracy.agg(["mean", "size"])
        pts = [((iv.left + iv.right) / 2 + off, r["mean"], int(r["size"])) for iv, r in g.iterrows() if r["size"] > 0]
        p.line([(x, y) for x, y, _ in pts], f"trace {cls}")
        for x, y, n in pts:
            p.dot(x, max(y, .4), f"pt {cls}", 2.5 + min(n, 40) ** .5 * .6, f"{ang}° · {x - off:.2f}: {100 * y:.0f} % (n = {n})")
    p.text(p.w - p.pr, p.h - p.pb - 8, "Punktgröße ~ Anzahl Trials", "reft", "end")
    return p.svg("Genauigkeit nach Eigenanteil")


def confidence_panel(df, excl):
    """Mean confidence by evidence (Task 1 / Task 2 low / Task 2 high) x correctness x mapping."""
    v = df[df.phase.str.startswith("wp3_task") & (df.trial_type != "strength") & ~df.is_timeout & df.wp3_confidence.notna()]
    v = v[~v.participant.isin(excl)] if (~v.participant.isin(excl)).any() else v
    p = Plot(420, 260, -0.4, 2.4, 1, 9)
    p.grid_y([1, 3, 5, 7, 9], label="Konfidenz (1–9)")
    p.ticks_x([0, 1, 2], lambda x: ["Task 1: keine", "Task 2: schwach", "Task 2: stark"][int(x)], "Zusatzevidenz nach der Wahl")
    for ang, cls, off in ((0, "c0", -.05), (90, "c90", .05)):
        for acc, lc in ((1, ""), (0, " dashed")):
            d = v[(v.angle_bias == ang) & (v.accuracy == acc)]
            cell = d.groupby(["participant", "evidence_level"]).wp3_confidence.mean().unstack()
            mean = cell.mean()
            pts = [(lev + off, float(mean.get(lev, np.nan))) for lev in (0, 1, 2)]
            p.line(pts, f"trace {cls}{lc}")
            for (x, y), lev in zip(pts, (0, 1, 2)):
                n = int(d[d.evidence_level == lev].shape[0])
                p.dot(x, y, f"pt {cls}" + ("" if acc else " err"), 4.5 if acc else 4,
                      f"{ang}° · {'richtig' if acc else 'falsch'} · Stufe {lev}: {y:.2f} ({n} Trials, {cell.shape[0]} Pers.)")
    yl = p.Y(8.6)
    p.add(f'<line class="trace k" x1="{f1(p.X(-.35))}" x2="{f1(p.X(-.2))}" y1="{f1(yl)}" y2="{f1(yl)}"/>')
    p.text(p.X(-.17), yl + 4, "erste Wahl richtig")
    p.add(f'<line class="trace k dashed" x1="{f1(p.X(.75))}" x2="{f1(p.X(.9))}" y1="{f1(yl)}" y2="{f1(yl)}"/>')
    p.text(p.X(.93), yl + 4, "erste Wahl falsch")
    return p.svg("Konfidenz nach Evidenz und Korrektheit"), v


def rt_panel(df, excl):
    v = df[df.phase.str.startswith(("wp3_task", "calibration")) & ~df.is_timeout]
    rows = []
    for (pid, ang), d in v.groupby(["participant", "angle_bias"]):
        rows.append(dict(pid=pid, ang=ang, rt=d.rt_choice.median(), crt=d.wp3_conf_rt.median(),
                         slow=int((d.wp3_conf_rt > 15).sum()), to=int(df[(df.participant == pid) & (df.angle_bias == ang)].is_timeout.sum())))
    body = "".join(f"<tr><td class='mono' style='white-space:nowrap'>{esc(r['pid'])}{' *' if r['pid'] in excl else ''}</td><td>{int(r['ang'])}°</td>"
                   f"<td class='n'>{num(r['rt'])}</td><td class='n'>{num(r['crt'])}</td><td class='n'>{r['slow']}</td>"
                   f"<td class='n'>{r['to']}</td></tr>" for r in rows)
    return ("<div class='tablewrap'><table><thead><tr><th>ID</th><th>Zuordnung</th><th class='n'>Wahl-RT s</th>"
            "<th class='n'>Konf.-RT s</th><th class='n'>Konf. > 15 s</th><th class='n'>Timeouts</th></tr></thead><tbody>"
            + body + "</tbody></table></div><p class='note'>Mediane. Wahl-RT ab Ende des 3-s-Bewegungsfensters (20 s Antwortfenster). "
            "* = ausgeschlossen oder Test.</p>")


# ── planned tests ───────────────────────────────────────────────────────────────

def run_planned(data_dir, boot):
    with tempfile.TemporaryDirectory() as td:
        out = pathlib.Path(td) / "results.json"
        cmd = [sys.executable, str(pathlib.Path(__file__).parent / "wp3_paper_analysis.py"), str(data_dir),
               "--boot", str(boot), "--boot-ideal", str(max(boot * 2 // 3, 0)), "--out", str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            return None, (r.stdout + r.stderr)[-1500:]
        return json.loads(out.read_text()), r.stdout


def test_row(name, what, res, kind="paired", note=""):
    if not res:
        val = "<span class='pill wait'>wartet</span>"
    else:
        val = (f"<span class='mono'>t({res['df']}) = {num(res['t'])}, {p_fmt(res['p'])}, d<sub>z</sub> = {num(res['d'])}</span>"
               f"<br><span class='sub'>M<sub>diff</sub> = {num(res['mean'], 3)}, 95 %-KI [{num(res['ci'][0], 3)}, {num(res['ci'][1], 3)}]"
               + (f", Wilcoxon {p_fmt(res['wilcoxon_p'])}" if 'wilcoxon_p' in res and np.isfinite(res['wilcoxon_p']) else "") + "</span>")
    return f"<tr><th scope='row'>{name}</th><td>{what}</td><td>{val}{note}</td></tr>"


def planned_section(R, n_inc, log):
    if R is None:
        reason = (f"Eingeschlossen sind {n_inc} Personen; die gepaarten Tests brauchen mindestens {MIN_FOR_TESTS} "
                  "mit einem Modellfit in beiden Zuordnungen." if n_inc < MIN_FOR_TESTS else
                  "Die Analyse lief, lieferte aber kein Ergebnis (Log unten).")
        T, S, ideal, boot = {}, None, None, None
    else:
        reason = None
        T, S, ideal, boot = R.get("tests", {}), R.get("strength"), R.get("ideal"), R.get("boot")
    h1 = T.get("H1_wd_both")
    ideal_note = (f"<br><span class='sub'>gegen Idealbeobachter-Benchmark ({ideal['n']} Replikate): ideal {num(ideal['null_mean'], 3)}, "
                  f"beobachtet {num(ideal['obs'], 3)}, {p_fmt(ideal['p'])}</span>") if ideal else ""
    boot_note = (f"<br><span class='sub'>Bootstrap-Null ({boot['n']} Replikate): {p_fmt(boot['p'])}</span>") if boot else ""
    rows = "".join([
        test_row("H2 (primär)", "log w<sub>d</sub> ist bei 0° kleiner als bei 90° (gepaart, Modell „both“)", T.get("H2_wd_both"), note=boot_note),
        test_row("H1", "widersprechende Evidenz wird untergewichtet: log w<sub>d</sub> unter dem Idealbeobachter", h1, note=ideal_note),
        test_row("Sekundär", "Commitment b, 0° vs 90°", T.get("b_both")),
        test_row("Kontrolle", "Genauigkeit Standardtrials gleich über Zuordnungen", (R or {}).get("checks", {}).get("accuracy")),
        test_row("Kontrolle", "Stärketrials gleich über Zuordnungen (TOST ±5 Punkte)", (S or {}).get("diff"),
                 note=(f"<br><span class='sub'>TOST {p_fmt(S['tost']['p'])}</span>" if S else "")),
        test_row("Explorativ", "meta-d′ (Task 1), 0° vs 90°", (R or {}).get("meta", {}).get("meta_d")),
    ])
    head = "" if reason is None else f"<p class='waiting'>{esc(reason)}</p>"
    extra = ""
    if R is not None and T.get("bic"):
        b = T["bic"]
        extra = ("<p class='note'>Modellvergleich (BIC-Summe, Δ zum besten): "
                 + ", ".join(f"{m} {num(b['delta'][m], 1)} ({b['wins'][m]} Siege)" for m in ("null", "weight", "choice", "both"))
                 + f"; {b['n_fits']} Fits.</p>")
    logblk = "" if R is not None or n_inc < MIN_FOR_TESTS else f"<pre class='log'>{esc(log)}</pre>"
    return (head + "<div class='tablewrap'><table class='tests'><thead><tr><th>Test</th><th>Hypothese</th><th>Ergebnis</th></tr></thead><tbody>"
            + rows + "</tbody></table></div>" + extra + logblk)


# ── posters from the "Second Look Poster" canvas, rebuilt from the data ─────────
# Poster 2 (Main: "What we expect") and poster 3 (results, made by wp3_poster.py). Both keep the print look of
# the canvas: their own paper ground and literal colours, in either theme.

PAPER, P_INK, P_SEC, P_MUT, P_GRID, P_AXIS = "#FAFAF7", "#15181C", "#2B3036", "#4A5058", "#DDE0E3", "#9AA1A9"
P_COL = {0: "#2A78D6", 90: "#D95926"}
P_MONO, P_SANS = "'IBM Plex Mono', Menlo, monospace", "'IBM Plex Sans', Helvetica, sans-serif"
EXP_X = (62, 154, 246)                     # none / low / high, as on the canvas
EXP_Y = lambda p: 148 - 140 * p            # 0-100 % on a 140-px axis


def expectation_cells(df, keep):
    """Per person and mapping, after a WRONG first choice: observed confidence (probability scale) at evidence
    none / low / high, the ideal observer's, and the per-person slope.
    Ideal observer = the model's null (w_c = w_d = 1, b = 0): logit conf = L0 - e, with L0 from Task-1
    confidence after wrong choices and e from the measured accuracies (standard first looks -> low,
    strength trials -> high, never below low), as in fit_wp3_model; group shrinkage from three people on.
    Slope = analyze_wp3.evidence_betas' disconfirmatory beta (rating points lost per evidence level, Task 1 + 2)."""
    v = df[df.phase.str.startswith("wp3_task") & ~df.is_timeout & df.accuracy.notna() & df.participant.isin(keep)]
    std, strn = v[v.trial_type != "strength"], v[v.trial_type == "strength"]
    rated = std[std.wp3_confidence.notna()].assign(pr=lambda d: (d.wp3_confidence - 1) / 8)
    # group shrinkage of the strength accuracy as in fit_wp3_model, once there are enough people to estimate it
    prior = F.acc_priors(F.strength_counts(df[df.participant.isin(keep)])) if len(set(strn.participant)) >= MIN_FOR_TESTS else {}
    rows = []
    for (pid, ang), d in rated.groupby(["participant", "angle_bias"]):
        wrong = d[d.accuracy == 0]
        obs = wrong.groupby("evidence_level").pr.mean()
        first = d.accuracy.mean()
        sa = strn[(strn.participant == pid) & (strn.angle_bias == ang)].accuracy
        el = max(float(F.logit(np.clip(first, .5, .99))), 0.0)
        a0, b0 = prior.get(int(ang), (0.0, 0.0))
        acc_h = (sa.sum() + a0) / (len(sa) + a0 + b0) if len(sa) + a0 + b0 > 0 else np.nan
        # the strong sample is never weaker than the first look (prop_post >= prop_used by design), so its e
        # is at least e_low; a few strength trials alone can otherwise put it below (2026-10-08: 1 of 2 wrong)
        eh = max(float(F.logit(np.clip(acc_h, .5, .99))) if np.isfinite(acc_h) else 0.0, el)
        q = wrong[wrong.wp3_task == 1].pr.mean()
        L0 = float(F.logit(np.clip(q, .01, .99))) if np.isfinite(q) else np.nan
        ideal = [F.sig(L0), F.sig(L0 - el), F.sig(L0 - eh)]
        rows.append(dict(participant=pid, angle=int(ang), n_wrong=len(wrong), n_wrong_high=int((wrong.evidence_level == 2).sum()),
                         obs=[float(obs.get(l, np.nan)) for l in (0, 1, 2)], ideal=[float(x) for x in ideal],
                         slope=A.evidence_betas(d)["beta_disconfirmatory"] if len(wrong) >= A.MIN_TRIALS_BETA else np.nan))
    P = pd.DataFrame(rows)
    out = {}
    for ang in ANGLES:
        a = P[P.angle == ang] if len(P) else P
        mean = lambda col: (np.nanmean(np.vstack(a[col].values), axis=0) if len(a) else np.full(3, np.nan))
        out[ang] = dict(n=int((a.n_wrong > 0).sum()) if len(a) else 0, obs=mean("obs"), ideal=mean("ideal"))
    if len(P):
        P["gap"] = [o[2] - i[2] for o, i in zip(P.obs, P.ideal)]             # observed minus ideal after strong evidence
    return out, P


def wrong_choice_svg(C):
    """Both mappings in one panel: confidence after a wrong first choice; dotted = that mapping's ideal observer."""
    el = []
    for t in (1, .75, .5, .25, 0):
        y = EXP_Y(t)
        el.append(f'<line x1="44" y1="{f1(y)}" x2="256" y2="{f1(y)}" stroke="{P_AXIS if t == 0 else P_GRID}" stroke-width="1"></line>')
        el.append(f'<text x="38" y="{f1(y + 4)}" text-anchor="end" font-family="{P_MONO}" font-size="12" fill="{P_MUT}">{100 * t:.0f} %</text>')
    for x, lab in zip(EXP_X, ("none", "low", "high")):
        el.append(f'<text x="{x}" y="165" text-anchor="middle" font-family="{P_SANS}" font-size="12" fill="{P_SEC}">{lab}</text>')
    el.append(f'<text x="154" y="182" text-anchor="middle" font-family="{P_MONO}" font-size="12" fill="{P_MUT}">evidence after the choice</text>')
    def poly(vals, stroke, sw, dash):
        pts = [(x, EXP_Y(v)) for x, v in zip(EXP_X, vals) if np.isfinite(v)]
        if len(pts) < 2:
            return ""
        d = " ".join(("M" if i == 0 else "L") + f"{f1(x)} {f1(y)}" for i, (x, y) in enumerate(pts))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{da}></path>'
    labs = []
    for ang in ANGLES:
        c, col = C[ang], P_COL[ang]
        el.append(poly(c["ideal"], col, 1.5, "1.5 4"))
        el.append(poly(c["obs"], col, 2, None))
        for x, val in zip(EXP_X, c["obs"]):
            if np.isfinite(val):
                el.append(f'<circle cx="{x}" cy="{f1(EXP_Y(val))}" r="4" fill="{col}" stroke="{PAPER}" stroke-width="2">'
                          f'<title>{ang}°: {100 * val:.0f} %</title></circle>')
        if np.isfinite(c["obs"][2]):
            labs.append([EXP_Y(c["obs"][2]), f"{ang}°", f"{100 * c['obs'][2]:.0f} %"])
    if len(labs) == 2 and abs(labs[0][0] - labs[1][0]) < 34:
        lo, hi = sorted(labs, key=lambda l: l[0]); mid = (lo[0] + hi[0]) / 2; lo[0], hi[0] = mid - 17, mid + 17
    for y, name, val in labs:
        el.append(f'<text x="258" y="{f1(y)}" font-family="{P_SANS}" font-size="12" fill="{P_INK}">{name}</text>')
        el.append(f'<text x="258" y="{f1(y + 15)}" font-family="{P_SANS}" font-size="12" font-weight="600" fill="{P_INK}">{val}</text>')
    if not any(np.isfinite(C[a]["obs"]).any() for a in ANGLES):
        el.append(f'<text x="150" y="80" text-anchor="middle" font-family="{P_SANS}" font-size="12" fill="{P_MUT}">no wrong choices yet</text>')
    return (f'<svg class="exp" width="342" height="186" viewBox="0 0 342 186" role="img" aria-label="Confidence after a wrong first '
            f'choice by evidence after the choice, 0 versus 90 degrees, with each mapping\'s ideal observer.">' + "".join(el) + "</svg>")


def paired_svg(P, col, lo, hi, ticks, fmt, zero=None):
    """Per-person values at 0° and 90°, joined by a line; large dot = group mean."""
    X = {0: 110, 90: 230}
    Y = lambda v: 148 - (np.clip(v, lo, hi) - lo) / (hi - lo) * 140
    el = []
    for t in ticks:
        el.append(f'<line x1="44" y1="{f1(Y(t))}" x2="296" y2="{f1(Y(t))}" stroke="{P_AXIS if t == zero else P_GRID}" stroke-width="1"></line>')
        el.append(f'<text x="38" y="{f1(Y(t) + 4)}" text-anchor="end" font-family="{P_MONO}" font-size="12" fill="{P_MUT}">{fmt(t)}</text>')
    for ang in ANGLES:
        el.append(f'<text x="{X[ang]}" y="165" text-anchor="middle" font-family="{P_SANS}" font-size="12" fill="{P_SEC}">{ang}°</text>')
    w = P.pivot_table(index="participant", columns="angle", values=col) if len(P) else pd.DataFrame()
    w = w.reindex(columns=list(ANGLES))
    for pid, r in w.iterrows():
        if r.notna().all():
            el.append(f'<line x1="{X[0] + 14}" y1="{f1(Y(r[0]))}" x2="{X[90] - 14}" y2="{f1(Y(r[90]))}" stroke="{P_AXIS}" stroke-width="1"></line>')
        for ang in ANGLES:
            if np.isfinite(r[ang]):
                el.append(f'<circle cx="{X[ang] + (14 if ang == 0 else -14)}" cy="{f1(Y(r[ang]))}" r="3" fill="{P_COL[ang]}" fill-opacity=".55">'
                          f'<title>{esc(pid)} {ang}°: {r[ang]:.2f}</title></circle>')
    for ang in ANGLES:
        m = w[ang].mean() if len(w) else np.nan
        if np.isfinite(m):
            el.append(f'<circle cx="{X[ang] + (-14 if ang == 0 else 14)}" cy="{f1(Y(m))}" r="5" fill="{P_COL[ang]}" stroke="{PAPER}" stroke-width="2"></circle>')
            el.append(f'<text x="{X[ang] + (-24 if ang == 0 else 24)}" y="{f1(Y(m) + 4)}" text-anchor="{"end" if ang == 0 else "start"}" '
                      f'font-family="{P_SANS}" font-size="12" font-weight="600" fill="{P_INK}">{fmt(m)}</text>')
    if not len(w) or not w.notna().any().any():
        el.append(f'<text x="170" y="80" text-anchor="middle" font-family="{P_SANS}" font-size="12" fill="{P_MUT}">no data yet</text>')
    return f'<svg class="exp" width="342" height="186" viewBox="0 0 342 186" role="img" aria-label="{col} by mapping, per person">' + "".join(el) + "</svg>"


def paired_line(P, col, unit):
    w = P.pivot_table(index="participant", columns="angle", values=col).dropna() if len(P) and col in P else pd.DataFrame()
    if len(w) < MIN_FOR_TESTS or 0 not in w or 90 not in w:
        return f"waiting · {len(w)} of {MIN_FOR_TESTS} people with both mappings"
    r = W.paired(w[0], w[90])
    return f"0° − 90° = {num(r['mean'])} {unit} · t({r['df']}) = {num(r['t'])}, {p_fmt(r['p'])}"


def poster2_section(df, keep, label, R=None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)          # empty cells (no errors yet) stay NaN
        C, P = expectation_cells(df, keep)
    leg = (f'<div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:12px;line-height:16px;color:{P_SEC}">'
           + "".join(f'<div style="display:flex;gap:6px;align-items:center"><svg width="22" height="8" viewBox="0 0 22 8" fill="none" aria-hidden="true">'
                     f'<line x1="1" y1="4" x2="21" y2="4" stroke="{c}" stroke-width="{w}" stroke-linecap="round"{d}></line></svg><div>{t}</div></div>'
                     for t, c, w, d in (("0°", P_COL[0], 2, ""), ("90°", P_COL[90], 2, ""),
                                        ("ideal observer", P_SEC, 1.5, ' stroke-dasharray="1.5 4"'))) + "</div>")
    h2 = (R or {}).get("tests", {}).get("H2_wd_both")
    h2_line = (f"model (H2): log w<sub>d</sub> 0° − 90° = {num(h2['mean'])} · t({h2['df']}) = {num(h2['t'])}, {p_fmt(h2['p'])}"
               if h2 else "model (H2): waiting for the planned analysis")
    def col(title, svg, line1, line2):
        return (f'<div style="flex:1 1 300px;min-width:0;display:flex;flex-direction:column;gap:4px">'
                f'<div style="font-size:14px;line-height:18px;font-weight:600">{title}</div>{svg}'
                f'<div style="font-size:13px;line-height:17px;color:{P_SEC}">{line1}</div>'
                f'<div style="font-family:{P_MONO};font-size:11.5px;line-height:15px;color:{P_MUT}">{line2}</div></div>')
    n0, n90 = C[0]["n"], C[90]["n"]
    cols = [
        col("Confidence after a wrong choice", wrong_choice_svg(C),
            "Should fall as evidence against the choice grows.", f"people with wrong choices: 0° {n0} · 90° {n90}"),
        col("Slope: how fast it falls", paired_svg(P, "slope", -1, 3, [-1, 0, 1, 2, 3], lambda v: f"{v:.1f}".replace("-", "−"), zero=0),
            "Rating points lost per evidence level (higher = more revision).", paired_line(P, "slope", "points")),
        col("Gap to the ideal observer", paired_svg(P.assign(gap=100 * P.gap) if len(P) else P, "gap", -40, 60, [-40, -20, 0, 20, 40, 60],
                                                    lambda v: f"{v:+.0f}".replace("-", "−") if v else "0", zero=0),
            "Observed minus ideal after strong evidence, in %-points (higher = stays too sure).", paired_line(P.assign(gap=100 * P.gap) if len(P) else P, "gap", "pp") + "<br>" + h2_line),
    ]
    return (f'<div class="sheet"><div style="display:flex;flex-direction:column;gap:10px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap">'
            f'<div style="font-family:{P_MONO};font-size:12px;line-height:16px;letter-spacing:.08em;text-transform:uppercase;color:{P_MUT}">'
            f'After a wrong first choice · 0° vs 90° · {esc(label)}</div>{leg}</div>'
            f'<div style="display:flex;gap:18px;flex-wrap:wrap">{"".join(cols)}</div></div></div>')


def poster3_markup(results_json):
    """Runs wp3_poster.py on a results.json and returns the artboard's markup for embedding."""
    with tempfile.TemporaryDirectory() as td:
        out = pathlib.Path(td) / "poster.dc.html"
        r = subprocess.run([sys.executable, str(pathlib.Path(__file__).parent / "wp3_poster.py"), str(results_json), str(out)],
                           capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            return None, (r.stdout + r.stderr)[-1200:]
        s = out.read_text()
    body = s.split("</helmet>", 1)[1].split("</x-dc>", 1)[0]
    return body, ""


def poster3_section(R, sim_results):
    if R is not None:
        with tempfile.TemporaryDirectory() as td:
            pj = pathlib.Path(td) / "results.json"; pj.write_text(json.dumps(R, default=float))
            body, log = poster3_markup(pj)
        note = "Aus den eingeschlossenen Studienteilnehmenden, mit <code>wp3_poster.py</code> wie auf dem Canvas."
    elif sim_results and pathlib.Path(sim_results).exists():
        body, log = poster3_markup(sim_results)
        note = ("<b>SIMULATED.</b> Noch keine echten Ergebnisse: hier steht das Poster aus der Validierungssimulation, "
                "erzeugt mit demselben Skript. Sobald 3 Personen eingeschlossen sind, ersetzen die echten Daten es.")
    else:
        return "<p class='waiting'>Erscheint, sobald die geplanten Tests laufen.</p>"
    if body is None:
        return f"<p class='waiting'>wp3_poster.py ist fehlgeschlagen.</p><pre class='log'>{esc(log)}</pre>"
    return f"<p class='note'>{note}</p><div class='posterwrap'><div class='poster'>{body}</div></div>"


# ── page ────────────────────────────────────────────────────────────────────────

CSS = """
/* Layout: a lab poster on screen. Header strip with the counts, then a two-column grid of panels
   that stacks on phones. Blue = 0°, orange = 90° throughout, as on the WP3 posters. */
:root{
  --bg:#F6F7F5; --panel:#FFFFFF; --ink:#15181C; --sec:#3D434A; --mut:#6A7179; --line:#DDE0E3; --axis:#9AA1A9;
  --c0:#2A78D6; --c90:#D95926; --ok:#2E7D4F; --warn:#B26B00; --bad:#B3261E;
  --sans:'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif; --mono:'IBM Plex Mono', Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#101215; --panel:#16191D; --ink:#ECEEF0; --sec:#C3C8CE; --mut:#8D949C; --line:#2A2F35; --axis:#5C636B;
  --c0:#4F8FE6; --c90:#E86A35; --ok:#5DBB86; --warn:#E0A23C; --bad:#F07167; color-scheme:dark } }
:root[data-theme="dark"]{
  --bg:#101215; --panel:#16191D; --ink:#ECEEF0; --sec:#C3C8CE; --mut:#8D949C; --line:#2A2F35; --axis:#5C636B;
  --c0:#4F8FE6; --c90:#E86A35; --ok:#5DBB86; --warn:#E0A23C; --bad:#F07167; color-scheme:dark }
body{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5}
.wrap{max-width:1180px;margin:0 auto;padding-inline:20px;padding-block:28px 48px;display:flex;flex-direction:column;gap:22px}
header{display:flex;flex-direction:column;gap:6px}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}
h1{font-size:clamp(26px,4vw,38px);line-height:1.1;margin:0;font-weight:600;text-wrap:balance}
h2{font-size:18px;margin:0;font-weight:600}
h3{font-size:14px;margin:0;font-weight:600;color:var(--sec)}
.lede{color:var(--sec);margin:0;max-width:72ch}
.banner{border:1.5px solid var(--warn);color:var(--ink);padding:10px 14px;border-radius:6px;font-size:14px}
.banner b{color:var(--warn)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px 14px;display:flex;flex-direction:column;gap:2px}
.stat .v{font-family:var(--mono);font-size:26px;font-variant-numeric:tabular-nums}
.stat .k{font-size:12px;color:var(--mut)}
.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden;margin-top:6px}
.bar i{display:block;height:100%;background:var(--c0)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
section{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px 18px;display:flex;flex-direction:column;gap:10px;min-width:0}
section.wide{grid-column:1/-1}
.num{font-family:var(--mono);color:var(--mut);font-size:12px;margin-right:8px}
.note,.sub{color:var(--mut);font-size:12.5px;margin:0}
.waiting{margin:0;color:var(--warn);font-weight:500}
svg{width:100%;height:auto;display:block;font-family:var(--sans)}
.traces{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px 18px}
.traces figure{margin:0;display:flex;flex-direction:column;gap:2px;min-width:0}
figcaption{font-size:12.5px;color:var(--sec)}
.grid line.grid,line.grid{stroke:var(--line);stroke-width:1}
line.axis{stroke:var(--axis);stroke-width:1}
line.ref{stroke:var(--mut);stroke-width:1;stroke-dasharray:4 4}
line.phase{stroke:var(--axis);stroke-width:1;stroke-dasharray:2 3}
text.tick{fill:var(--mut);font-size:10.5px;font-family:var(--mono)}
text.axl{fill:var(--sec);font-size:11px}
text.reft,text.phl{fill:var(--mut);font-size:10.5px}
text.lab{fill:var(--sec);font-size:11px}
text.tmark{fill:var(--bad);font-size:12px;font-weight:600}
path.trace{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
path.trace.c0,line.trace.c0,line.mean.c0{stroke:var(--c0)} path.trace.c90,line.mean.c90{stroke:var(--c90)}
line.trace.k{stroke:var(--sec);stroke-width:2} .dashed{stroke-dasharray:5 4}
line.mean{stroke-width:3;stroke-linecap:round}
circle.pt{stroke:var(--panel);stroke-width:1.5} circle.pt.c0{fill:var(--c0)} circle.pt.c90{fill:var(--c90)}
circle.pth{fill:var(--panel);stroke-width:1.6} circle.pth.c0{stroke:var(--c0)} circle.pth.c90{stroke:var(--c90)}
circle.pt.err{fill:var(--panel);stroke-width:2} circle.pt.err.c0{stroke:var(--c0)} circle.pt.err.c90{stroke:var(--c90)}
circle.strength{stroke:var(--ink);stroke-width:1}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12.5px;color:var(--sec)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:11px;height:11px;border-radius:50%;display:inline-block} .sw.c0{background:var(--c0)} .sw.c90{background:var(--c90)}
.sw.hollow{border:1.6px solid var(--sec)}
.tablewrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
thead th{font-size:11.5px;color:var(--mut);font-weight:500;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;font-family:var(--mono)}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
table.tests th[scope=row]{white-space:nowrap;font-weight:600}
.pill{display:inline-block;font-size:11.5px;padding:1px 8px;border-radius:10px;border:1px solid currentColor;white-space:nowrap}
.pill.in{color:var(--ok)} .pill.out{color:var(--bad)} .pill.test{color:var(--warn)} .pill.wait{color:var(--mut)}
pre.log{font-family:var(--mono);font-size:11px;color:var(--mut);white-space:pre-wrap;margin:0;max-height:200px;overflow:auto}
code{font-family:var(--mono);font-size:.92em}
footer{color:var(--mut);font-size:12px}
.sheet svg.exp{width:342px;max-width:100%}
.sheet svg:not(.exp){width:auto;display:inline-block}
.sheet{background:#FAFAF7;color:#15181C;border-radius:6px;padding:18px 20px;font-family:var(--sans)}
.posterwrap{overflow-x:auto;border-radius:6px}
.poster{width:794px;margin:0 auto}
@media (max-width:820px){.grid{grid-template-columns:minmax(0,1fr)} .wrap{padding-inline:16px}}
"""


def build(df, data_dir, boot, sim_results=None):
    allp = list(dict.fromkeys(df.participant))
    d = pathlib.Path(data_dir)
    simulated = (d / "ground_truth.csv").exists() or (d.parent / "ground_truth.csv").exists()
    tests = set() if simulated else set(df[df.is_test].participant)     # simulated people have no Prolific id
    dwp = df[df.phase.str.startswith("wp3_task")]
    dstd = dwp[dwp.trial_type != "strength"]
    q = W.quality(dstd) if len(dstd) else pd.DataFrame(columns=["participant", "excluded"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fits = W.fit_all(df) if len(dstd) else pd.DataFrame(columns=["participant", "fail"])
    excl = set(q[q.excluded].participant) | tests
    study = [p for p in allp if p not in tests]
    inc = [p for p in study if p not in excl]

    R, log = (None, "")
    if len(inc) >= MIN_FOR_TESTS:
        with tempfile.TemporaryDirectory() as td:          # the planned analysis on study participants only
            for p in study:
                df[df.participant == p].to_csv(pathlib.Path(td) / f"{p}.csv", index=False)
            R, log = run_planned(td, boot)

    traces = []
    for pid in allp[-MAX_TRACES:]:
        dp = df[df.participant == pid]
        hol = pid in excl
        for ang, cls in ((0, "c0"), (90, "c90")):
            s, dl = track_panel(dp, ang, cls), delta_panel(dp, ang, cls)
            if s:
                traces.append(f"<figure>{s}{dl}<figcaption><span class='mono'>{esc(pid)}</span> · {ang}°"
                              f"{' · ausgeschlossen/Test' if hol else ''}</figcaption></figure>")
    conf_svg, _ = confidence_panel(df, excl)
    builds = ", ".join(sorted({str(b) for b in df.get("build", pd.Series(dtype=str)).dropna()})) or "–"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    files = len(list(pathlib.Path(data_dir).glob("*.csv")))
    banner = ("<div class='banner'><b>SIMULATED.</b> Diese Seite zeigt simulierte Daten (ground_truth.csv liegt bei den Dateien); "
              "sie prüft nur die Auswertung.</div>") if simulated else ("<div class='banner'><b>Nur Test- und Pilotdaten.</b> Bisher sind keine Studienteilnehmenden dabei; "
              "alle Zahlen dienen der Funktionsprüfung und sind kein Befund.</div>") if not study else ""
    prog = min(len(inc) / N_ANALYSABLE, 1)

    page = f"""<title>WP3 Datenübersicht</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header>
  <div class="eyebrow">WP3 · A Second Look · Stand {now}</div>
  <h1>Datenübersicht und geplante Tests</h1>
  <p class="lede">Alle bisher gesammelten Datensätze der Online-Version (Pavlovia) an einem Ort: ob die Aufgabe so läuft wie geplant,
  wie sich die Teilnehmenden verhalten, und die präregistrierten Tests, sobald genug Personen eingeschlossen sind.</p>
</header>
{banner}
<div class="stats">
  <div class="stat"><span class="v">{len(allp)}</span><span class="k">Datensätze ({files} {'Datei' if files == 1 else 'Dateien'})</span></div>
  <div class="stat"><span class="v">{len(tests)}</span><span class="k">davon Testläufe</span></div>
  <div class="stat"><span class="v">{len(study)}</span><span class="k">Studienteilnehmende</span></div>
  <div class="stat"><span class="v">{len(inc)}<span class="k"> / {N_ANALYSABLE}</span></span><span class="k">eingeschlossen (Ziel {N_ANALYSABLE} von N = {N_PLANNED})</span>
    <div class="bar" aria-hidden="true"><i style="width:{100 * prog:.1f}%"></i></div></div>
</div>
<div class="grid">
<section class="wide"><h2><span class="num">1</span>Datensätze und Datenqualität</h2>
  <p class="note">Builds: <span class="mono">{esc(builds)}</span></p>{quality_table(df, q, fits, tests)}</section>
<section class="wide"><h2><span class="num">2</span>Läuft die Aufgabe? Treppen pro Person</h2>
  <p class="note">Oben: Eigenanteil pro Trial. Linie = 1-up-2-down (Kalibrierung und Standardtrials), Punkte mit dunklem Rand = Stärketrials
  (Eigenanteil + δ), hohle Punkte = falsch, × = Timeout. Unten: die δ-Spur der Stärketrials (Ziel 85 %), nur bei Stärketrials bewegt.
  {'Gezeigt sind die letzten ' + str(MAX_TRACES) + ' Datensätze.' if len(allp) > MAX_TRACES else ''}</p>
  {legend()}<div class="traces">{''.join(traces)}</div></section>
<section><h2><span class="num">3</span>Genauigkeit gegen die Zielwerte</h2>
  <p class="note">Ein Punkt pro Person; Balken = Mittel der Eingeschlossenen. Standardtrials sollen bei ~71 % liegen, Stärketrials bei ~85 %.</p>
  {accuracy_panel(df, excl)}{legend()}</section>
<section><h2><span class="num">4</span>Genauigkeit nach Eigenanteil</h2>
  <p class="note">Alle Entscheidungstrials (Kalibrierung, Task 1 und 2) gepoolt, in Klassen des Eigenanteils.</p>
  {psychometric_panel(df)}{legend()}</section>
<section><h2><span class="num">5</span>Konfidenz nach Zusatzevidenz</h2>
  <p class="note">Mittelwert über Personen{' (nur Eingeschlossene)' if inc else ' (alle, da noch niemand eingeschlossen ist)'}. Erwartung:
  nach richtiger Wahl steigt die Konfidenz mit stärkerer Evidenz, nach falscher fällt sie (Rollwage et al., 2018, Abb. 4B).</p>
  {conf_svg}{legend()}</section>
<section><h2><span class="num">6</span>Antwortzeiten</h2>{rt_panel(df, excl)}</section>
<section class="wide"><h2><span class="num">7</span>Geplante Tests</h2>
  <p class="note">Läuft <code>wp3_paper_analysis.py</code> auf den eingeschlossenen Studienteilnehmenden (Testläufe nie).
  Primärer Test H2: Kontrast 0° vs 90° auf log w<sub>d</sub> aus dem Modell „both“, mit parametrischer Bootstrap-Null.</p>
  {planned_section(R, len(inc), log)}</section>
<section class="wide"><h2><span class="num">8</span>Poster 2 · Nach einer falschen Wahl: 0° gegen 90°</h2>
  <p class="note">Die Kernfrage: Wie stark sinkt die Konfidenz in eine falsche erste Wahl, wenn danach Evidenz dagegen kommt, und
  unterscheidet sich das zwischen den Modi? Links die Mittelwerte beider Modi mit ihrem Idealbeobachter (punktiert: nutzt die Evidenz voll,
  w<sub>c</sub> = w<sub>d</sub> = 1, kein Commitment). Mitte die Steigung pro Person, rechts der Abstand zum Idealbeobachter pro Person.
  Der präregistrierte Test dieses Abstands ist H2 auf w<sub>d</sub> aus dem Modell.</p>
  {poster2_section(df, inc if inc else allp, ('included participants' if inc else 'all data sets, tests included'), R)}</section>
<section class="wide"><h2><span class="num">9</span>Poster 3 · Ergebnisposter</h2>
  {poster3_section(R, sim_results)}</section>
</div>
<footer>Erzeugt mit <code>experiment/analysis/wp3_overview.py</code> aus {files} CSV-Dateien. Rohdaten liegen nicht im Repository.</footer>
</div>
"""
    return page


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data_dir"); ap.add_argument("out")
    ap.add_argument("--boot", type=int, default=300, help="bootstrap replicates for the planned tests")
    ap.add_argument("--sim-results", help="results.json of a validation run: shown as poster 3 until real results exist")
    a = ap.parse_args()
    df = load(a.data_dir)
    pathlib.Path(a.out).write_text(build(df, a.data_dir, a.boot, a.sim_results))
    print(f"[out] {a.out}")


if __name__ == "__main__":
    main()
