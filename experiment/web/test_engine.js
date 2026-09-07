/* Node self-test of the ported motion engine: does higher `prop` produce a
   stronger, more detectable control signal? A synthetic "participant" moves the
   mouse on a smooth wandering path; an observer decides the target is the shape
   whose cumulative evidence is higher (sign of sumEvidence). Accuracy must rise
   monotonically with prop and be ~chance at prop 0.  Run: node test_engine.js   */
const fs = require("fs");
const { TrialEngine } = require("./engine.js");

const meta = JSON.parse(fs.readFileSync(__dirname + "/motion_pool.json"));
const buf = fs.readFileSync(__dirname + "/motion_pool.bin");
const data = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
const pool = { data, F: meta.frames, n: meta.n };
console.log(`pool: ${pool.n} trajectories x ${pool.F} frames`);

// deterministic RNG so the test is reproducible
let seed = 12345;
function rnd() { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; }
function randIdx() { return Math.floor(rnd() * pool.n); }

function runTrial(prop, angle) {
  const ti = randIdx(); let di = randIdx(); while (di === ti) di = randIdx();
  const target = rnd() < 0.5 ? "square" : "dot";
  const left = rnd() < 0.5 ? "square" : "dot";
  const applied = angle === 90 ? (rnd() < 0.5 ? 90 : -90) : 0;
  const eng = new TrialEngine(pool, ti, di, prop, applied, target, left);
  // synthetic mouse: smooth wandering velocity (integrate small heading changes)
  let mx = 0, my = 0, heading = rnd() * 2 * Math.PI, speed = 6;
  for (let f = 0; f < pool.F; f++) {
    heading += (rnd() - 0.5) * 0.6;
    speed = Math.max(2, Math.min(14, speed + (rnd() - 0.5) * 2));
    mx += Math.cos(heading) * speed; my += Math.sin(heading) * speed;
    eng.step(mx, my);
  }
  // observer: target is whichever shape carries the higher self-correspondence.
  // sumEvidence > 0 means the (true) target shape led -> observer would pick it.
  return eng.sumEvidence > 0 ? 1 : 0;
}

function accuracy(prop, angle, n = 800) {
  let c = 0; for (let i = 0; i < n; i++) c += runTrial(prop, angle);
  return c / n;
}

console.log("\nprop -> observer accuracy (0 deg):");
const props = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7];
const acc0 = props.map(p => accuracy(p, 0));
props.forEach((p, i) => console.log(`  prop ${p.toFixed(2)}  acc ${acc0[i].toFixed(3)}`));
console.log("\n90 deg (control preserved through rotation, engine applies it):");
const acc90 = props.map(p => accuracy(p, 90));
props.forEach((p, i) => console.log(`  prop ${p.toFixed(2)}  acc ${acc90[i].toFixed(3)}`));

// assertions: chance at prop 0, monotone rise, high at prop 0.7
const near = (a, b, tol) => Math.abs(a - b) < tol;
if (!near(acc0[0], 0.5, 0.06)) throw new Error(`prop 0 not ~chance: ${acc0[0]}`);
for (let i = 1; i < props.length; i++)
  if (acc0[i] < acc0[i - 1] - 0.02) throw new Error(`not monotone at prop ${props[i]}`);
if (acc0[acc0.length - 1] < 0.8) throw new Error(`prop 0.7 too low: ${acc0[acc0.length - 1]}`);
console.log("\nPASS: chance at prop 0, monotone rise with prop, strong control at 0.7");
