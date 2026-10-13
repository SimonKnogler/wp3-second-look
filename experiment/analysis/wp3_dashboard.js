// Interactive part of the WP3 data overview (inlined by wp3_overview.py). Reads window.WP3 = {real, sim?}:
// each {label, simulated, fields, rows, people: {id: {ex, test}}}. Redraws the panels for the chosen data set,
// person, mapping and inclusion rule. Drawn as SVG with the page's CSS classes, so both themes work.
(function () {
  const D = window.WP3; if (!D) return;
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  const f1 = v => v.toFixed(1);
  const pct = v => (v == null || !isFinite(v)) ? "–" : Math.round(100 * v) + " %";
  const num = (v, d = 2) => (v == null || !isFinite(v)) ? "–" : v.toFixed(d).replace("-", "−");
  const mean = a => { const b = a.filter(x => x != null && isFinite(x)); return b.length ? b.reduce((s, x) => s + x, 0) / b.length : NaN; };
  const median = a => { const b = a.filter(x => x != null && isFinite(x)).sort((x, y) => x - y); if (!b.length) return NaN;
    const m = b.length >> 1; return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2; };
  const ANG = [0, 90], CLS = {0: "c0", 90: "c90"};

  // rows -> objects once per data set
  for (const k of Object.keys(D)) {
    const F = D[k].fields;
    D[k].trials = D[k].rows.map(r => Object.fromEntries(F.map((f, i) => [f, r[i]])));
  }
  const st = {ds: "real", pid: "all", ang: "both", incl: "inc"};

  // ── a tiny plot helper, same geometry rules as the Python Plot class ──────────
  function Plot(w, h, x0, x1, y0, y1, pad = [14, 12, 34, 44]) {
    const [pt, pr, pb, pl] = pad, el = [];
    const X = v => pl + (v - x0) / (x1 - x0 || 1) * (w - pl - pr);
    const Y = v => h - pb - (v - y0) / (y1 - y0) * (h - pt - pb);
    return {
      X, Y, el,
      gridY(ticks, fmt, label) {
        for (const t of ticks) {
          el.push(`<line class="grid" x1="${pl}" x2="${w - pr}" y1="${f1(Y(t))}" y2="${f1(Y(t))}"/>`);
          el.push(`<text class="tick" x="${pl - 6}" y="${f1(Y(t) + 4)}" text-anchor="end">${fmt(t)}</text>`);
        }
        if (label) el.push(`<text class="axl" transform="translate(12 ${f1((pt + h - pb) / 2)}) rotate(-90)" text-anchor="middle">${label}</text>`);
      },
      ticksX(ticks, fmt, label) {
        el.push(`<line class="axis" x1="${pl}" x2="${w - pr}" y1="${h - pb}" y2="${h - pb}"/>`);
        for (const t of ticks) el.push(`<text class="tick" x="${f1(X(t))}" y="${h - pb + 15}" text-anchor="middle">${fmt(t)}</text>`);
        if (label) el.push(`<text class="axl" x="${f1((pl + w - pr) / 2)}" y="${h - 4}" text-anchor="middle">${label}</text>`);
      },
      band(lo, hi) { el.push(`<rect class="band" x="${pl}" y="${f1(Y(hi))}" width="${w - pl - pr}" height="${f1(Y(lo) - Y(hi))}"/>`); },
      ref(v, label) {
        el.push(`<line class="ref" x1="${pl}" x2="${w - pr}" y1="${f1(Y(v))}" y2="${f1(Y(v))}"/>`);
        el.push(`<text class="reft" x="${w - pr}" y="${f1(Y(v) - 4)}" text-anchor="end">${label}</text>`);
      },
      line(pts, cls) {          // a missing y breaks the line
        let d = "", pen = false;
        for (const [x, y] of pts) {
          if (y == null || !isFinite(y)) { pen = false; continue; }
          d += (pen ? "L" : " M") + f1(X(x)) + " " + f1(Y(y)); pen = true;
        }
        if (d.includes("L")) el.push(`<path class="${cls}" d="${d.trim()}"/>`);
      },
      dot(x, y, cls, r = 4, tip = "") {
        if (y == null || !isFinite(y)) return;
        el.push(`<circle class="${cls}" cx="${f1(X(x))}" cy="${f1(Y(y))}" r="${r}">${tip ? `<title>${esc(tip)}</title>` : ""}</circle>`);
      },
      text(x, y, s, cls = "reft", anchor = "middle") { el.push(`<text class="${cls}" x="${f1(x)}" y="${f1(y)}" text-anchor="${anchor}">${s}</text>`); },
      svg(label) { return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}">${el.join("")}</svg>`; },
    };
  }
  const pctTick = v => Math.round(100 * v);

  // ── selection ─────────────────────────────────────────────────────────────────
  function selected() {
    const d = D[st.ds], P = d.people;
    let ids = Object.keys(P);
    if (st.incl === "inc") ids = ids.filter(p => !P[p].ex);
    if (st.pid !== "all") ids = ids.filter(p => p === st.pid);
    const set = new Set(ids), angs = st.ang === "both" ? ANG : [+st.ang];
    return {d, ids, angs, T: d.trials.filter(t => set.has(t.p) && angs.includes(t.a))};
  }
  const task = t => t.ph === "t1" || t.ph === "t2";
  const valid = t => !t.to && t.acc != null;

  // ── panels ────────────────────────────────────────────────────────────────────
  function kpis(S) {
    const tiles = [["Personen", S.ids.length, ""], ["Trials", S.T.length, "inkl. Kalibrierung"]];
    for (const a of S.angs) {
      const std = S.T.filter(t => task(t) && valid(t) && t.tt === "std" && t.a === a);
      const str = S.T.filter(t => task(t) && valid(t) && t.tt === "str" && t.a === a);
      tiles.push([`Acc Standard ${a}°`, pct(mean(std.map(t => t.acc))), `Ziel 71 % · ${std.length} Trials`, CLS[a]]);
      tiles.push([`Acc Stärke ${a}°`, pct(mean(str.map(t => t.acc))), `Ziel 85 % · ${str.length} Trials`, CLS[a]]);
    }
    tiles.push(["Timeouts", pct(mean(S.T.map(t => t.to ? 1 : 0))), "aller Entscheidungen"]);
    tiles.push(["Konfidenz-RT", num(median(S.T.filter(t => t.crt != null).map(t => t.crt))) + " s", "Median"]);
    $("db-kpis").innerHTML = tiles.map(([k, v, s, c]) =>
      `<div class="stat"><span class="k">${c ? `<i class="sw ${c}"></i> ` : ""}${k}</span><span class="v">${v}</span><span class="k">${s}</span></div>`).join("");
  }

  function rolling(a, w) { return a.map((_, i) => i < 2 ? NaN : mean(a.slice(Math.max(0, i - w + 1), i + 1))); }

  function convergence(S, tt) {
    const w = tt === "std" ? 20 : 10, curves = [];
    for (const p of S.ids) for (const a of S.angs) {
      const acc = S.T.filter(t => t.p === p && t.a === a && task(t) && valid(t) && t.tt === tt).sort((x, y) => x.i - y.i).map(t => t.acc);
      if (acc.length) curves.push({p, a, y: rolling(acc, w)});
    }
    const xmax = Math.max(10, ...curves.map(c => c.y.length));
    const P = Plot(480, 220, 1, xmax, 0.4, 1);
    P.gridY([.4, .5, .6, .7, .8, .9, 1], pctTick, "Genauigkeit, gleitend (%)");
    P.ticksX([1, Math.round(xmax / 2), xmax], v => v, `${tt === "std" ? "Standardtrial" : "Stärketrial"} in Task 1 + 2 (Fenster ${w})`);
    if (tt === "std") { P.band(.6, .8); P.ref(.707, "Ziel 70,7 %"); } else { P.band(.8, 1); P.ref(.85, "Ziel 85 %"); }
    const many = S.ids.length > 1, faint = S.ids.length > 4 ? " faint" : "";
    for (const a of S.angs) {
      const cs = curves.filter(c => c.a === a);
      for (const c of cs) P.line(c.y.map((y, i) => [i + 1, y]), `trace ${CLS[a]}${many ? " thin" + faint : ""}`);
      if (many && cs.length) {
        const L = Math.max(...cs.map(c => c.y.length));
        P.line(Array.from({length: L}, (_, i) => [i + 1, mean(cs.map(c => c.y[i]))]), `trace ${CLS[a]}`);
      }
    }
    if (!curves.some(c => c.y.some(isFinite)))
      P.text(P.X((1 + xmax) / 2), P.Y(.7), curves.length ? "zu wenige Trials (Kurve ab dem 3. Trial)" : "keine Trials in dieser Auswahl");
    return P.svg("Gleitende Genauigkeit");
  }

  function confidence(S) {
    const P = Plot(480, 240, -0.4, 2.4, 1, 9);
    P.gridY([1, 3, 5, 7, 9], v => v, "Konfidenz (1–9)");
    P.ticksX([0, 1, 2], v => ["Task 1: keine", "Task 2: schwach", "Task 2: stark"][v], "Zusatzevidenz nach der Wahl");
    for (const a of S.angs) for (const acc of [1, 0]) {
      const pts = [0, 1, 2].map(lev => {
        const per = S.ids.map(p => mean(S.T.filter(t => t.p === p && t.a === a && task(t) && valid(t) && t.tt === "std"
          && t.acc === acc && t.ev === lev && t.conf != null).map(t => t.conf)));
        return [lev + (a === 0 ? -.05 : .05), mean(per), per.filter(isFinite).length];
      });
      P.line(pts, `trace ${CLS[a]}${acc ? "" : " dashed"}`);
      for (const [x, y, n] of pts) P.dot(x, y, `pt ${CLS[a]}${acc ? "" : " err"}`, 4.5,
        `${a}° · ${acc ? "richtig" : "falsch"}: ${num(y)} (${n} Pers.)`);
    }
    return P.svg("Konfidenz nach Evidenz");
  }

  function psychometric(S) {
    const edges = [0, .15, .25, .35, .45, .55, .65, .75, .95];
    const P = Plot(480, 220, 0, .95, .4, 1);
    P.gridY([.4, .5, .6, .7, .8, .9, 1], pctTick, "Genauigkeit (%)");
    P.ticksX([0, .2, .4, .6, .8], v => v.toFixed(1), "Eigenanteil der Bewegung (alle Entscheidungen)");
    P.ref(.5, "Zufall");
    for (const a of S.angs) {
      const pts = [];
      for (let k = 0; k < edges.length - 1; k++) {
        const b = S.T.filter(t => t.a === a && valid(t) && t.prop > edges[k] && t.prop <= edges[k + 1]);
        if (b.length) pts.push([(edges[k] + edges[k + 1]) / 2 + (a ? .006 : -.006), mean(b.map(t => t.acc)), b.length]);
      }
      P.line(pts, `trace ${CLS[a]}`);
      for (const [x, y, n] of pts) P.dot(x, Math.max(y, .4), `pt ${CLS[a]}`, 2.5 + Math.sqrt(Math.min(n, 40)) * .6, `${a}°: ${pct(y)} (n = ${n})`);
    }
    return P.svg("Genauigkeit nach Eigenanteil");
  }

  function staircase(S) {
    // one person: the trial-by-trial staircase; several: mean standard prop per standard-trial index
    const one = S.ids.length === 1;
    const series = S.angs.map(a => {
      if (one) return {a, pts: S.T.filter(t => t.a === a).sort((x, y) => x.i - y.i).map((t, k) => ({x: k + 1, t}))};
      const per = S.ids.map(p => S.T.filter(t => t.p === p && t.a === a && t.tt !== "str").sort((x, y) => x.i - y.i).map(t => t.prop));
      const L = Math.max(0, ...per.map(s => s.length));
      return {a, mean: Array.from({length: L}, (_, i) => [i + 1, mean(per.map(s => s[i]))])};
    });
    const xmax = Math.max(10, ...series.map(s => one ? s.pts.length : s.mean.length));
    const P = Plot(980, 230, 1, xmax, 0, 1);
    P.gridY([0, .25, .5, .75, 1], v => v, "Eigenanteil");
    P.ticksX([1, Math.round(xmax / 2), xmax], v => v, one ? "Trial im Block (Kalibrierung, Task 1, Task 2)" : "Kalibrierungs- und Standardtrial");
    for (const s of series) {
      if (!one) { P.line(s.mean, `trace ${CLS[s.a]}`); continue; }
      // the line skips strength trials and pauses over the strength calibration
      P.line(s.pts.filter(q => q.t.tt !== "str" || q.t.ph === "cals").map(q => [q.x, q.t.ph === "cals" ? null : q.t.prop]), `trace ${CLS[s.a]}`);
      for (const q of s.pts) {
        if (q.t.prop == null) continue;
        const t = q.t, tip = `${t.ph} · ${num(t.prop)} · ${t.to ? "Timeout" : t.acc ? "richtig" : "falsch"}`;
        if (t.to) P.text(P.X(q.x), P.Y(t.prop) + 4, `×<title>${esc(tip)}</title>`, "tmark");
        else P.dot(q.x, t.prop, `pt ${CLS[s.a]}${t.tt === "str" ? " strength" : ""}${t.acc ? "" : " err"}`, t.tt === "str" ? 3.2 : 2.6, tip);
      }
    }
    if (!series.some(s => one ? s.pts.length : s.mean.length)) P.text(P.X((1 + xmax) / 2), P.Y(.5), "keine Trials in dieser Auswahl");
    return P.svg("Treppe");
  }

  // ── controls ──────────────────────────────────────────────────────────────────
  function fillPeople() {
    const P = D[st.ds].people;
    const ids = Object.keys(P).filter(p => st.incl === "all" || !P[p].ex);
    if (st.pid !== "all" && !ids.includes(st.pid)) st.pid = "all";
    $("db-pid").innerHTML = `<option value="all">alle (${ids.length})</option>` +
      ids.map(p => `<option value="${esc(p)}"${p === st.pid ? " selected" : ""}>${esc(p)}${P[p].test ? " · Test" : P[p].ex ? " · ausgeschlossen" : ""}</option>`).join("");
  }
  function render() {
    const d = D[st.ds];
    $("db-sim").hidden = !d.simulated;
    const nInc = Object.values(d.people).filter(p => !p.ex).length;
    $("db-empty").hidden = !(st.incl === "inc" && nInc === 0);
    const S = selected();
    kpis(S);
    $("db-conv-std").innerHTML = convergence(S, "std");
    $("db-conv-str").innerHTML = convergence(S, "str");
    $("db-conf").innerHTML = confidence(S);
    $("db-psy").innerHTML = psychometric(S);
    $("db-stair").innerHTML = staircase(S);
    $("db-stair-cap").textContent = S.ids.length === 1
      ? "Eigenanteil pro Trial: Linie = 1-up-2-down, Punkte mit Rand = Stärketrials, hohl = falsch, × = Timeout."
      : "Mittlerer Eigenanteil der Treppe über die gewählten Personen (Kalibrierung und Standardtrials).";
  }
  function bind(id, key, after) {
    $(id).addEventListener("change", e => { st[key] = e.target.value; if (after) after(); render(); });
  }
  const dsSel = $("db-ds");
  dsSel.innerHTML = Object.keys(D).map(k => `<option value="${k}">${esc(D[k].label)}</option>`).join("");
  const init = () => { const d = D[st.ds]; st.incl = Object.values(d.people).some(p => !p.ex) ? "inc" : "all"; $("db-incl").value = st.incl; fillPeople(); };
  bind("db-ds", "ds", () => { st.pid = "all"; init(); });
  bind("db-pid", "pid");
  bind("db-ang", "ang");
  bind("db-incl", "incl", fillPeople);
  init(); render();
})();
