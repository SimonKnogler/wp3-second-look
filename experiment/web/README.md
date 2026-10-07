# WP3 Control-Detection Task — Web port (Pavlovia)

Browser version of the WP3 belief-updating paradigm (Rollwage-style post-decision
evidence, no cues, medium only, 0°/90° blocked). Faithful JS port of the PsychoPy
motion engine. Exports a CSV with the **same columns** the Python analysis reads,
so `analysis/analyze_wp3.py` works unchanged.

## Files
| file | what |
|---|---|
| `index.html` | the whole experiment (canvas + flow + confidence + CSV export) |
| `engine.js` | the motion engine, ported line-for-line from `run_trial`, plus the lab's matched trajectory pairs and consistent smoothing, and a fixed 60 Hz simulation clock |
| `motion_pool.bin` / `.json` | the trajectory library **as the lab uses it**: validity-filtered, speed-normalised, in universal-set order (1240 primary + 40 overflow × 297 × 2, Float32) |
| `export_pool_for_web.py` | regenerates the pool binary from `core_pool.npy` with the lab's own preprocessing |
| `test_engine.js` | Node self-test: prop → control signal, 120-steps/s clock at 30/60/120/144 Hz display rates, matched pairs |

## Same feel on every screen (port parity with WP1 online)
Three things make the browser version behave like the lab and like the WP1 online port:
- **Pointer Lock.** The task reads relative mouse movement; the system cursor is hidden by the
  OS, cannot leave the window or reach a second monitor, and macOS "shake to locate" cannot
  enlarge it. There is no screen edge where the circles freeze. Esc releases the lock (and
  fullscreen); the task pauses and asks for a click. If the browser refuses the lock four times
  the task continues on plain mouse deltas and records `pointer_lock = 0`.
- **Physics at a fixed 120 steps/s.** The lab loop steps once per `win.flip()`, and the WP1 lab
  kinematics show it ran at ~119 steps/s on the lab machine (120 Hz display). The browser renders
  at the monitor's rate (60, 120, 144 Hz) but the simulation always takes 120 steps per second,
  with a frame's mouse movement spread over the steps it covers. At 60 steps/s the same constants
  give slow motion (directions persist twice as long, the speed cap bites at 1200 instead of
  2400 px/s) and the circles crawl along the box walls.
- **Matched trajectory pairs and consistent smoothing**, as in the lab: target and distractor
  snippets are alike in speed and path length and get the same smoothing.
Per-trial quality markers: `display_fps` (rendered frames per second of motion; well below the
display rate = dropped frames) and `low_move_ratio` (share of steps with the hand nearly still).
Participant-level: `input_device` (1 mouse, 2 trackpad, 3 other — asked at the start),
`pointer_lock`, `pointer_lock_exits`.

## Test it locally FIRST
`fetch()` needs a server (won't work from `file://`). From this folder:
```
python3 -m http.server 8000
```
then open **http://localhost:8000** in Chrome. Use a real **mouse**, not a trackpad.
Quick run: **http://localhost:8000/?t1=6&t2=12** (short), or `?pid=99` to set an ID.

Check by feel: shapes move, one follows your mouse, calibration converges, the
Part-B second look is clearly visible, the 1–9 confidence works, a CSV downloads
at the end. Then run the analysis on it:
```
cd ../analysis && python analyze_wp3.py ../web/CDT_wp3_<pid>.csv   # (move the downloaded file here)
```

## Upload to Pavlovia
Pavlovia serves any static site from a git repo.
1. Create a new experiment on pavlovia.org → it gives you a GitLab repo URL.
2. Put `index.html`, `engine.js`, `motion_pool.bin`, `motion_pool.json` in the repo root, commit, push.
3. Set the experiment to **Piloting** (free) to test, then **Running** for the study.
4. Give the Pavlovia URL to Prolific as the study link; use `?pid={{%PROLIFIC_PID%}}` to capture IDs.

## Data — two options (host-agnostic)
- **Download (default):** every run downloads `CDT_wp3_<pid>.csv`. Fine for piloting.
- **OSF DataPipe (recommended for the real study):** create a DataPipe experiment at
  pipe.jspsych.org (free, sends to OSF), then set `DATAPIPE_ID` near the top of the
  `<script>` in `index.html`. Data then auto-uploads from any host (Pavlovia included).
  (Native Pavlovia/PsychoJS saving needs their wrapper — DataPipe is simpler and works everywhere.)

## Config via URL params
`t1`, `t2` (standard trials/angle), `d0`, `d1`, `d2` (strength trials/angle: calibration block,
Task 1, Task 2; default 20 / 10 / 25, all 0 restores the old fixed boost), `calmin`, `calmax`, `boost`
(fixed high-evidence logit, used only when there are no strength trials), `evdur`
(evidence-sample seconds), `pid`, `seed`, `bonus` (maximum bonus in £; 0 = points only — set it
for Prolific, the instructions quote it with a worked example), `nolock=1` (TESTING ONLY: no
pointer lock, cursor visible).

Strength trials (design doc §10j) are Part-A-style trials (choose, rate, no second look)
whose first look is already at the high strength. They drive a weighted up-down track on the
high offset (target 85 %) and measure what that strength supports; flagged
`trial_type = "strength"` in the CSV (`phase = calibration_strength` for the feedback-free
block), not part of the confidence model. `delta_live` is the offset in force on each trial.

## Honest status / what still needs YOUR check
- **Browser-test the feel** — I can't run a browser here. Verify mouse tracking,
  control feel, and timing on your machine.
- **Trajectory matching simplified:** target/distractor are random distinct snippets
  (the engine's speed-equalisation is the main anti-cue protection; per-pair speed
  matching from the Python is a later refinement).
- **No consent / instructions / demographics screens yet** — add before real data.
- **Motor task online caveat:** trackpad vs mouse / DPI / frame-rate variance. Enforce
  mouse + fullscreen, log frame rate, apply Rollwage exclusions (already in analyze_wp3.py).
