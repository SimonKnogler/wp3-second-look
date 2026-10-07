/* Node self-test of the motion engine.  Run: node test_engine.js
   1. Control signal: higher `prop` -> a synthetic observer detects the target more often;
      ~chance at prop 0; the 90 deg rotation is applied by the engine.
   2. SimClock: the same wall time gives the same number of physics steps (120/s, as the lab
      ran) whether the display renders at 30, 60, 120 or 144 Hz (the "same feel on every screen" guarantee).
   3. Trajectory pairs: matched pairs are distinct, unused, and more alike than random pairs;
      consistent smoothing keeps the frame count.                                            */
const fs = require("fs");
const E = require("./engine.js");

const meta = JSON.parse(fs.readFileSync(__dirname + "/motion_pool.json"));
const buf = fs.readFileSync(__dirname + "/motion_pool.bin");
const data = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
console.log(`pool: ${meta.n} trajectories x ${meta.frames} frames (primary ${meta.n_primary}, overflow ${meta.n_overflow})`);
const TS = new E.TrajectoryState(data, meta.frames, meta.n, meta.n_primary, meta.n_overflow);

let seed = 12345;
function rnd() { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; }
const near = (a, b, tol) => Math.abs(a - b) < tol;

// ── 1. control signal ──
function runTrial(prop, angle) {
  const [ti, di] = TS.pair(rnd);
  const [tS, dS] = E.applyConsistentSmoothing(TS.snip(ti), TS.snip(di));
  const target = rnd() < 0.5 ? "square" : "dot", left = rnd() < 0.5 ? "square" : "dot";
  const applied = angle === 90 ? (rnd() < 0.5 ? 90 : -90) : 0;
  const eng = new E.TrialEngine(tS, dS, prop, applied, target, left);
  let heading = rnd() * 2 * Math.PI, speed = 6;
  for (let f = 0; f < 360; f++) {                      // 3 s at 120 steps/s, like the task
    heading += (rnd() - 0.5) * 0.6;
    speed = Math.max(2, Math.min(14, speed + (rnd() - 0.5) * 2));
    eng.stepDelta(Math.cos(heading) * speed, Math.sin(heading) * speed);
  }
  return eng.sumEvidence > 0 ? 1 : 0;
}
function accuracy(prop, angle, n = 600) { let c = 0; for (let i = 0; i < n; i++) c += runTrial(prop, angle); return c / n; }
const props = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7];
console.log("\nprop -> observer accuracy (0 deg / 90 deg):");
const acc0 = props.map(p => accuracy(p, 0)), acc90 = props.map(p => accuracy(p, 90));
props.forEach((p, i) => console.log(`  prop ${p.toFixed(2)}  ${acc0[i].toFixed(3)}  ${acc90[i].toFixed(3)}`));
if (!near(acc0[0], 0.5, 0.06)) throw new Error(`prop 0 not ~chance: ${acc0[0]}`);
for (let i = 1; i < props.length; i++) if (acc0[i] < acc0[i - 1] - 0.02) throw new Error(`not monotone at prop ${props[i]}`);
if (acc0[acc0.length - 1] < 0.8) throw new Error(`prop 0.7 too low: ${acc0[acc0.length - 1]}`);
console.log("PASS control signal");

// ── 2. fixed-rate clock ──
for (const hz of [30, 60, 120, 144]) {
  const clk = new E.SimClock(0); let steps = 0, t = 0;
  while (t < 3 - 1e-9) { t += 1 / hz; steps += clk.steps(t); }
  if (!near(steps, 360, 2)) throw new Error(`SimClock at ${hz} Hz: ${steps} steps for 3 s (want 360)`);
}
{ const clk = new E.SimClock(0); if (clk.steps(5.0) !== 12) throw new Error("a long gap must be capped to 100 ms"); }
{ const clk = new E.SimClock(0); for (let i = 0; i < 360; i++) clk.advance();
  if (clk.k !== 360 || !(clk.simT >= 3.0)) throw new Error(`360 steps must reach 3.0 s exactly (got ${clk.simT})`); }
console.log("PASS SimClock: 360 steps per 3 s at 30/60/120/144 Hz; long gaps capped");

// ── 3. trajectory pairs ──
const T2 = new E.TrajectoryState(data, meta.frames, meta.n, meta.n_primary, meta.n_overflow);
const score = (i, j) => { const a = T2.sig[i], b = T2.sig[j];
  return Math.abs(a.mean_speed - b.mean_speed) + Math.abs(a.speed_variability - b.speed_variability)
       + Math.abs(a.path_length - b.path_length) / Math.max(a.path_length, b.path_length) * 10; };
let matched = 0, random = 0;
for (let k = 0; k < 100; k++) {
  const [i, j] = T2.matchedPair(rnd);
  if (i === j || i === null) throw new Error("matched pair not distinct");
  matched += score(i, j);
  const a = Math.floor(rnd() * meta.n); let b = Math.floor(rnd() * meta.n); while (b === a) b = Math.floor(rnd() * meta.n);
  random += score(a, b);
}
if (!(matched < random / 3)) throw new Error(`matched pairs not more alike: ${matched} vs ${random}`);
if (T2.used.size !== 200) throw new Error("used set not tracked");
const [s1, s2] = E.applyConsistentSmoothing(T2.snip(0), T2.snip(1));
if (s1.length !== meta.frames - 1 || s2.length !== meta.frames - 1) throw new Error("smoothing changed the frame count unexpectedly");
// exhaustion: after all primary+overflow are used, pairs are still returned
const T3 = new E.TrajectoryState(data, meta.frames, meta.n, meta.n_primary, meta.n_overflow);
for (let k = 0; k < 700; k++) { const [i, j] = T3.pair(rnd); if (i === null || j === null || i === j) throw new Error("pair() failed after exhaustion"); }
console.log(`PASS trajectory pairs: matched score ${(matched / 100).toFixed(2)} vs random ${(random / 100).toFixed(2)}; recycling works`);
console.log("\nALL PASS");
