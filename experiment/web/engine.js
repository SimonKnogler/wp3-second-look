/* CDT motion engine — a faithful port of the run_trial motion loop from
   CDT_windows_blockwise_fast_response.py (lines ~984-1046). Pure math, no DOM,
   so it runs identically in the browser and in Node (for the port self-test).

   Coordinate system matches PsychoPy: origin at screen center, y up. The browser
   renderer flips y at draw time. All velocities/positions are in px.            */

const LOWPASS = 0.5;
const MAX_SPEED = 20.0;
const MIN_SPEED_FLOOR = 2.0;   // logged as low_move; not used for control here
const OFFSET_X = 300;
const BOX_HW = 200, BOX_HH = 250;

function rotate(vx, vy, deg) {
  const a = deg * Math.PI / 180;
  return [vx * Math.cos(a) - vy * Math.sin(a), vx * Math.sin(a) + vy * Math.cos(a)];
}
function hypot(x, y) { return Math.sqrt(x * x + y * y); }
function confine(px, py, cx) {
  return [Math.min(Math.max(px, cx - BOX_HW), cx + BOX_HW),
          Math.min(Math.max(py, -BOX_HH), BOX_HH)];
}

/* One trial's motion state. Feed it the mouse position each frame; it returns the
   two shapes' new positions and the momentary evidence. */
class TrialEngine {
  constructor(pool, targetIdx, distractorIdx, prop, appliedAngle, targetShape, leftShape) {
    this.pool = pool;                 // {data:Float32Array, F:int}
    this.ti = targetIdx; this.di = distractorIdx;
    this.prop = prop;
    this.angle = appliedAngle;        // 0, 90 or -90
    this.targetShape = targetShape;   // "square" | "dot"
    // left/right layout: square on left or right
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
  _snip(i, f) { const d = this.pool.data, k = (i * this.pool.F + (f % this.pool.F)) * 2; return [d[k], d[k + 1]]; }

  /* mx,my = current mouse position (centered, y up). Returns {square, dot, evidence}. */
  step(mx, my) {
    if (this.last === null) { this.last = [mx, my]; }
    let dx = mx - this.last[0], dy = my - this.last[1];
    this.last = [mx, my];
    [dx, dy] = rotate(dx, dy, this.angle);

    let [tdx0, tdy0] = this._snip(this.ti, this.frame);
    let [ddx0, ddy0] = this._snip(this.di, this.frame);
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
    const cosT = (dx * this.vt[0] + dy * this.vt[1]) / (ntv * mouseSpeed);   // dot(vm, unit(vt)) / |vm|
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
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { TrialEngine, rotate, confine, OFFSET_X, BOX_HW, BOX_HH };
}
