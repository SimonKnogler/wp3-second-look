/* CDT motion engine — a faithful port of the run_trial motion loop from
   CDT_windows_blockwise_fast_response.py (lines ~984-1046), plus the lab's trajectory
   handling (matched pairs, consistent smoothing) and a fixed-rate simulation clock.
   Pure math, no DOM, so it runs identically in the browser and in Node (test_engine.js).

   Coordinate system matches PsychoPy: origin at screen center, y up. The browser
   renderer flips y at draw time. All velocities/positions are in px.

   The lab loop takes one physics step per win.flip(), and the WP1 lab data show it ran at
   ~119 steps/s on the lab machine (120 Hz display): that is the stimulus the task was built
   and piloted with. The browser renders at whatever the monitor does (60, 120, 144 Hz):
   SimClock converts wall time into 120 Hz steps, so the motion is the same on every display.
   At 60 steps/s the same constants give slow motion: directions persist twice as long and the
   speed cap (20 px/step) bites at 1200 instead of 2400 px/s — the circles crawl along the box
   walls. The same hand movement must yield the same on-screen behaviour everywhere.     */

const LOWPASS = 0.5;
const MAX_SPEED = 20.0;          // px per physics step
const MIN_SPEED_FLOOR = 2.0;     // logged as low_move; not used for control here
const OFFSET_X = 300;
const BOX_HW = 200, BOX_HH = 250;
const SIM_DT = 1 / 120;          // physics step; the lab ran at ~120 steps/s (WP1 kinematics, design doc §10k)

function rotate(vx, vy, deg) {
  const a = deg * Math.PI / 180;
  return [vx * Math.cos(a) - vy * Math.sin(a), vx * Math.sin(a) + vy * Math.cos(a)];
}
function hypot(x, y) { return Math.sqrt(x * x + y * y); }
function confine(px, py, cx) {
  return [Math.min(Math.max(px, cx - BOX_HW), cx + BOX_HW),
          Math.min(Math.max(py, -BOX_HH), BOX_HH)];
}

/* ── fixed-rate simulation clock ─────────────────────────────────────────────
   steps(wallNow): how many physics steps the time since the last call covers
   (2 on a 60 Hz display, 1 on 120 Hz, more after dropped frames).
   A gap > 100 ms (tab hidden, pause overlay) is capped so the motion never jumps.   */
class SimClock {
  constructor(now) { this.last = now; this.accum = 0; this.k = 0; }
  steps(now) {
    this.accum += Math.min(Math.max(now - this.last, 0), 0.1);
    this.last = now;
    const n = Math.floor(this.accum / SIM_DT);
    this.accum -= n * SIM_DT;
    return n;
  }
  // Steps are COUNTED, never summed as time: 180 additions of 1/60 gave 2.9999999999999942,
  // and a loop waiting for simT >= 3 then stalled for ever (the first-trial freeze of 2026-10-05).
  advance() { this.k++; }
  get simT() { return this.k * SIM_DT; }
  resume(now) { this.last = now; }      // after a pause: do not count the paused time
}

/* ── trajectory pipeline (lab lines 343-355, 656-760) ────────────────────────
   A snippet is an array of [dx,dy] velocities. The pool file already holds the lab's
   validity-filtered, normalised snippets in universal-set order (export_pool_for_web.py). */
function cumsum2(vel) {
  const out = new Array(vel.length); let x = 0, y = 0;
  for (let i = 0; i < vel.length; i++) { x += vel[i][0]; y += vel[i][1]; out[i] = [x, y]; }
  return out;
}
function diff2(pts) {
  const out = new Array(pts.length - 1);
  for (let i = 1; i < pts.length; i++) out[i - 1] = [pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]];
  return out;
}
function trajectorySignature(traj) {            // of POSITIONS
  const vel = diff2(traj);
  if (!vel.length) return { mean_speed: 0, speed_variability: 0, path_length: 0 };
  const sp = vel.map(v => hypot(v[0], v[1]));
  const m = sp.reduce((a, b) => a + b, 0) / sp.length;
  const sd = Math.sqrt(sp.reduce((a, s) => a + (s - m) ** 2, 0) / sp.length);
  return { mean_speed: m, speed_variability: sd, path_length: sp.reduce((a, b) => a + b, 0) };
}
/* Both snippets of a trial get the same 3-point moving average on their positions
   (lab apply_consistent_smoothing), so target and distractor are equally smooth. */
function applyConsistentSmoothing(vel1, vel2) {
  const smooth = pts => pts.map((_, i) => {
    const s = Math.max(0, i - 1), e = Math.min(pts.length, i + 2);
    let sx = 0, sy = 0;
    for (let k = s; k < e; k++) { sx += pts[k][0]; sy += pts[k][1]; }
    return [sx / (e - s), sy / (e - s)];
  });
  return [diff2(smooth(cumsum2(vel1))), diff2(smooth(cumsum2(vel2)))];
}

/* The pool as the lab sees it: a primary set, an overflow set, and the used-set of this
   session. matchedPair() = find_matched_trajectory_pair: among 100 unused candidates, the
   two most alike in speed, speed variability and path length. */
class TrajectoryState {
  constructor(data, frames, n, nPrimary, nOverflow) {
    if (data.length !== n * frames * 2) throw new Error(`motion pool: ${data.length} values for ${n} x ${frames} x 2 — stale or truncated pool file`);
    if (!nPrimary) { nPrimary = n; nOverflow = 0; }          // a pool file without set sizes: everything is primary
    this.data = data; this.F = frames; this.n = n;
    this.primary = [...Array(nPrimary).keys()];
    this.overflow = [...Array(nOverflow).keys()].map(i => nPrimary + i);
    this.all = this.primary.concat(this.overflow);
    this.used = new Set();
    this.sig = new Array(n);
    for (let i = 0; i < n; i++) this.sig[i] = trajectorySignature(cumsum2(this.snip(i)));
  }
  snip(i) {
    const out = new Array(this.F), base = i * this.F * 2;
    for (let f = 0; f < this.F; f++) out[f] = [this.data[base + 2 * f], this.data[base + 2 * f + 1]];
    return out;
  }
  _avail() {
    const p = this.primary.filter(i => !this.used.has(i));
    const o = this.overflow.filter(i => !this.used.has(i));
    return [p, p.length >= 2 ? p : p.concat(o)];
  }
  matchedPair(rnd) {
    const [availP, avail] = this._avail();
    if (avail.length < 2) {
      if (avail.length === 1) { const t = avail[0]; const others = this.all.filter(i => i !== t); return others.length ? [t, pick(rnd, others)] : [null, null]; }
      return [null, null];
    }
    const samplePool = availP.length >= 2 ? availP : avail;
    const cand = choiceNoReplace(rnd, samplePool, Math.min(100, samplePool.length));
    let best = Infinity, pair = [null, null];
    for (let i = 0; i < cand.length; i++) for (let j = i + 1; j < cand.length; j++) {
      const s1 = this.sig[cand[i]], s2 = this.sig[cand[j]];
      const score = Math.abs(s1.mean_speed - s2.mean_speed) + Math.abs(s1.speed_variability - s2.speed_variability)
                  + Math.abs(s1.path_length - s2.path_length) / Math.max(s1.path_length, s2.path_length) * 10;
      if (score < best) { best = score; pair = [cand[i], cand[j]]; }
    }
    if (pair[0] !== null) { this.used.add(pair[0]); this.used.add(pair[1]); }
    return pair;
  }
  fallbackPair(rnd) {                         // run_trial lines 977-1013: any two, used or not
    const [, avail] = this._avail();
    if (avail.length >= 2) { const s = choiceNoReplace(rnd, avail, 2); this.used.add(s[0]); this.used.add(s[1]); return s; }
    if (avail.length === 1) { const t = avail[0]; const d = pick(rnd, this.all.filter(i => i !== t)); this.used.add(t); this.used.add(d); return [t, d]; }
    return choiceNoReplace(rnd, this.all, 2);
  }
  pair(rnd) { const p = this.matchedPair(rnd); return p[0] === null ? this.fallbackPair(rnd) : p; }
}
function pick(rnd, arr) { return arr[Math.floor(rnd() * arr.length)]; }
function choiceNoReplace(rnd, arr, k) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a.slice(0, k);
}

/* ── one trial's motion state ─────────────────────────────────────────────────
   tSnip / dSnip: velocity snippets (already smoothed). Feed stepDelta() the mouse
   DISPLACEMENT of one physics step; it returns the two shapes' new positions and the
   momentary evidence.                                                           */
class TrialEngine {
  constructor(tSnip, dSnip, prop, appliedAngle, targetShape, leftShape) {
    this.tSnip = tSnip; this.dSnip = dSnip;
    this.prop = prop;
    this.angle = appliedAngle;        // 0, 90 or -90
    this.targetShape = targetShape;   // "square" | "dot"
    this.squareCx = leftShape === "square" ? -OFFSET_X : OFFSET_X;
    this.dotCx = leftShape === "square" ? OFFSET_X : -OFFSET_X;
    this.squarePos = [this.squareCx, 0];
    this.dotPos = [this.dotCx, 0];
    this.vt = [0, 0]; this.vd = [0, 0];
    this.magLp = 0;
    this.frame = 0;
    this.last = null;
    this.sumEvidence = 0;
    this.lowMove = 0;
  }
  /* absolute mouse position (centered, y up) — kept for the Node self-test */
  step(mx, my) {
    if (this.last === null) this.last = [mx, my];
    const d = [mx - this.last[0], my - this.last[1]]; this.last = [mx, my];
    return this.stepDelta(d[0], d[1]);
  }
  stepDelta(dx0, dy0) {
    let [dx, dy] = rotate(dx0, dy0, this.angle);
    const [tdx0, tdy0] = this.tSnip[this.frame % this.tSnip.length];
    const [ddx0, ddy0] = this.dSnip[this.frame % this.dSnip.length];
    this.frame++;

    let magM = hypot(dx, dy);
    if (magM > MAX_SPEED) { dx = dx * MAX_SPEED / magM; dy = dy * MAX_SPEED / magM; magM = MAX_SPEED; }
    this.magLp = (this.frame === 1) ? magM : 0.5 * this.magLp + 0.5 * magM;
    if (this.frame > 1 && this.magLp < MIN_SPEED_FLOOR) this.lowMove++;

    const mt = hypot(tdx0, tdy0), md = hypot(ddx0, ddy0);
    const tdir = mt > 0 ? [tdx0 / mt * this.magLp, tdy0 / mt * this.magLp] : [0, 0];
    const ddir = md > 0 ? [ddx0 / md * this.magLp, ddy0 / md * this.magLp] : [0, 0];

    const tdx = this.prop * dx + (1 - this.prop) * tdir[0];
    const tdy = this.prop * dy + (1 - this.prop) * tdir[1];
    const ddx = ddir[0], ddy = ddir[1];

    this.vt = [LOWPASS * this.vt[0] + (1 - LOWPASS) * tdx, LOWPASS * this.vt[1] + (1 - LOWPASS) * tdy];
    this.vd = [LOWPASS * this.vd[0] + (1 - LOWPASS) * ddx, LOWPASS * this.vd[1] + (1 - LOWPASS) * ddy];

    // evidence uses the low-passed (displayed) velocities, BEFORE speed-equalization
    const mouseSpeed = hypot(dx, dy) + 1e-9;
    const ntv = hypot(this.vt[0], this.vt[1]) + 1e-9, ndv = hypot(this.vd[0], this.vd[1]) + 1e-9;
    const cosT = (dx * this.vt[0] + dy * this.vt[1]) / (ntv * mouseSpeed);
    const cosD = (dx * this.vd[0] + dy * this.vd[1]) / (ndv * mouseSpeed);
    const evidence = (cosT - cosD) * (mouseSpeed - 1e-9);
    this.sumEvidence += evidence;

    // speed-equalize: both shapes move at the participant's low-passed speed
    const nt = hypot(this.vt[0], this.vt[1]), nd = hypot(this.vd[0], this.vd[1]);
    if (nt > 1e-9) this.vt = [this.vt[0] / nt * this.magLp, this.vt[1] / nt * this.magLp];
    if (nd > 1e-9) this.vd = [this.vd[0] / nd * this.magLp, this.vd[1] / nd * this.magLp];

    const [sqV, dtV] = this.targetShape === "square" ? [this.vt, this.vd] : [this.vd, this.vt];
    this.squarePos = confine(this.squarePos[0] + sqV[0], this.squarePos[1] + sqV[1], this.squareCx);
    this.dotPos = confine(this.dotPos[0] + dtV[0], this.dotPos[1] + dtV[1], this.dotCx);
    return { square: this.squarePos, dot: this.dotPos, evidence };
  }
  get lowMoveRatio() { return this.lowMove / Math.max(this.frame - 1, 1); }
}

/* Node (test_engine.js) reads module.exports; the browser reads the global. Both
   must exist: exporting only to module.exports made `Engine` undefined in the
   browser and the first trial died with a silent ReferenceError. */
const Engine = { TrialEngine, TrajectoryState, SimClock, applyConsistentSmoothing, trajectorySignature,
                 cumsum2, diff2, rotate, confine, OFFSET_X, BOX_HW, BOX_HH, SIM_DT, MAX_SPEED };
if (typeof module !== "undefined" && module.exports) module.exports = Engine;
else globalThis.Engine = Engine;
