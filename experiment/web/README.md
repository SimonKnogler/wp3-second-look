# WP3 Control-Detection Task — Web port (Pavlovia)

Browser version of the WP3 belief-updating paradigm (Rollwage-style post-decision
evidence, no cues, medium only, 0°/90° blocked). Faithful JS port of the PsychoPy
motion engine. Exports a CSV with the **same columns** the Python analysis reads,
so `analysis/analyze_wp3.py` works unchanged.

## Files
| file | what |
|---|---|
| `index.html` | the whole experiment (canvas + flow + confidence + CSV export) |
| `engine.js` | the motion engine, ported line-for-line from `run_trial` |
| `motion_pool.bin` / `.json` | the real trajectory library (1200 × 298 × 2, Float32) |
| `export_pool_for_web.py` | regenerates the pool binary from `core_pool.npy` |
| `test_engine.js` | Node self-test of the engine (prop → control signal) |

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
`t1`, `t2` (trials/angle), `calmin`, `calmax`, `boost` (high-evidence logit), `evdur`
(evidence-sample seconds), `pid`, `seed`.

## Honest status / what still needs YOUR check
- **Browser-test the feel** — I can't run a browser here. Verify mouse tracking,
  control feel, and timing on your machine.
- **Trajectory matching simplified:** target/distractor are random distinct snippets
  (the engine's speed-equalisation is the main anti-cue protection; per-pair speed
  matching from the Python is a later refinement).
- **No consent / instructions / demographics screens yet** — add before real data.
- **Motor task online caveat:** trackpad vs mouse / DPI / frame-rate variance. Enforce
  mouse + fullscreen, log frame rate, apply Rollwage exclusions (already in analyze_wp3.py).
