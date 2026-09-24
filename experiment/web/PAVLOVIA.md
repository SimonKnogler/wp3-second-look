# Deploying to Pavlovia

## The one thing to know first

Pavlovia will **host** this study without trouble — it serves plain HTML/JS. But Pavlovia's
**native data saving only works for PsychoJS or jsPsych** experiments, because saving is
done by their plugin, which opens a session at the start and closes it at the end. This
study is hand-coded vanilla JS and uses neither.

So: **Pavlovia hosts, OSF DataPipe saves.** DataPipe is free, host-agnostic and already
wired into `index.html`. The alternative — rewriting the task as a jsPsych plugin to get
native saving — is a large change to a verified engine and is not recommended.

## Repository layout Pavlovia expects

```
<pavlovia-repo>/
  html/                 ← Pavlovia git-pulls THIS folder to the run URL
    index.html
    engine.js
    motion_pool.bin
    motion_pool.json
  data/                 ← created by Pavlovia itself; never delete
```

The source of truth stays in `experiment/web/` in the main repo. Never edit the Pavlovia
copy directly — push from here with `tools/deploy_pavlovia.sh`.

## One-time setup

1. **Account.** Create one at pavlovia.org. Check first whether LMU has a site licence —
   if it does, participant credits are free; otherwise budget roughly £0.20–0.25 per
   participant (~£40 for 175).
2. **DataPipe.** At pipe.jspsych.org, connect an OSF project and create an experiment.
   Copy the experiment ID. Set it in `index.html`:
   ```js
   DATAPIPE_ID: Q.get("datapipe") || "PASTE_ID_HERE",
   ```
   Enable "data collection" on the DataPipe experiment, otherwise uploads are rejected.
3. **Create the Pavlovia study.** Dashboard → Experiments → New. This creates a GitLab
   repo at `gitlab.pavlovia.org/<user>/<study>`. Clone it locally.
4. **First deploy:**
   ```bash
   ./tools/deploy_pavlovia.sh ~/path/to/<study> "Initial WP3 web build"
   ```
5. **Activate.** In the Pavlovia dashboard set the study to **PILOTING** (free, only you)
   for testing, then **RUNNING** for real data collection. New studies start INACTIVE and
   cannot be opened until this is changed.

## Testing on Pavlovia

Study URL: `https://run.pavlovia.org/<user>/<study>/`

Query parameters work the same as locally:

| Parameter | Purpose |
|---|---|
| `?t1=6&t2=12&calmin=10&calmax=15` | short run for a feel test |
| `?bonus=1.00` | activate the quadratic scoring rule with a £1 maximum |
| `?datapipe=<id>` | override the DataPipe id without a redeploy |
| `?pid=<id>` | set the participant id manually |

A piloting run appends `&__pilotToken=...` automatically — leave it alone.

## Prolific integration

Study URL given to Prolific:

```
https://run.pavlovia.org/<user>/<study>/?PROLIFIC_PID={{%PROLIFIC_PID%}}&STUDY_ID={{%STUDY_ID%}}&SESSION_ID={{%SESSION_ID%}}&completion=https://app.prolific.com/submissions/complete?cc=XXXXXXXX
```

`index.html` reads all three Prolific ids (they are written into every data row) and, when
`completion` is set, redirects there after showing the bonus for four seconds — that is
what credits the participant. Without `completion` it simply shows a closing screen.

**Prolific settings that matter for this study:** desktop only (Prolific cannot filter for
mouse vs. trackpad — the instructions ask for a mouse, and low movement is flagged in the
data), 18–50, no neurological or psychiatric history, and a time allowance of ~75 minutes
for a ~55-minute task.

## Everyday workflow

```bash
# 1. edit experiment/web/index.html (or engine.js) in the main repo
# 2. test locally
cd experiment/web && python3 -m http.server 8000     # → http://localhost:8000
# 3. commit to the main repo
git add -A && git commit -m "..." && git push
# 4. deploy to Pavlovia
./tools/deploy_pavlovia.sh ~/path/to/<study> "what changed"
# 5. hard-reload the run URL (Pavlovia caches aggressively: Cmd+Shift+R)
```

## Known pitfalls

- **Caching.** After a deploy the old version often persists. Hard-reload, and if it still
  looks stale, use the dashboard's "reset/synchronise" on the study.
- **`motion_pool.bin` is 2.9 MB.** It loads fine but is the bulk of the transfer; expect a
  short blank moment on a slow connection before the first screen.
- **Piloting tokens expire** after about an hour. Regenerate from the dashboard.
- **Credits are consumed in RUNNING mode**, including your own test runs. Pilot in
  PILOTING mode.
- **Fullscreen.** The study requests fullscreen on the opening click. Some browsers refuse
  it when the page is embedded in a frame; the study continues either way.
