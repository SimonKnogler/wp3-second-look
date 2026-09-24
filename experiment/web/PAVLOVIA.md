# Deploying to Pavlovia

## The one thing to know first

Pavlovia will **host** this study — it serves plain HTML/JS. But Pavlovia's **native data
saving only works for PsychoJS or jsPsych** experiments: saving is done by their plugin,
which opens a session at the start and closes it at the end. This study is hand-coded
vanilla JS and uses neither.

So: **Pavlovia hosts, OSF DataPipe saves.** DataPipe is free, host-agnostic and already
wired into `index.html`. Rewriting the task as a jsPsych plugin to get native saving would
mean rebuilding a verified engine for no scientific gain.

A consequence worth knowing: without the plugin handshake Pavlovia never "opens a session"
for a run. The first pilot on Pavlovia is also the test of whether it serves the study
happily that way (people do host plain HTML on it, but verify it yourself before Prolific).

## Repository layout Pavlovia expects

Per Pavlovia's own docs (`git add index.html` at the root) and the WP1 port that ran there:

```
wp3-pavlovia/           ← separate git repo, branch `master` (Pavlovia requires it)
  index.html            ← at the ROOT, not in a subfolder
  engine.js
  motion_pool.bin
  motion_pool.json
  README.md
  data/                 ← created by Pavlovia itself; never delete
```

Do **not** create a folder called `lib/` — Pavlovia symlinks its own `lib` into the run
location and the deploy breaks (WP1 hit this).

The source of truth stays in `experiment/web/` in the main repo. Never edit the Pavlovia
copy; push from here with `tools/deploy_pavlovia.sh`.

## Accounts and credentials (already on this machine)

Pavlovia uses its own GitLab at **gitlab.pavlovia.org** (not gitlab.com). The working
account from this Mac is `simonknogler` — HTTPS credentials are in the macOS keychain, so
`git push` works without a prompt. (Older repos under `Knoglersimon` are no longer
reachable; use `simonknogler`.)

## One-time setup

1. **Project — done (2026-09-24).** gitlab.pavlovia.org supports *push-to-create*: pushing
   `master` from `~/Desktop/PhD/Experiments/wp3-pavlovia` created the **private** project
   https://gitlab.pavlovia.org/simonknogler/wp3-second-look with the initial build. It
   appears in the Pavlovia dashboard automatically. (To recreate from scratch: `git init -b
   master`, add the four files, `git remote add origin <url>`, `git push -u origin master`.)
2. **Local repo** lives at `~/Desktop/PhD/Experiments/wp3-pavlovia`, tracking
   `origin/master`; the deploy script targets it by default.
3. **DataPipe.** At https://pipe.jspsych.org connect an OSF project and create an
   experiment; enable data collection on it; copy the experiment ID into
   `experiment/web/index.html`:
   ```js
   DATAPIPE_ID: Q.get("datapipe") || "PASTE_ID_HERE",
   ```
   then redeploy. Until then `?datapipe=<id>` on the URL works for testing.
4. **Activate.** pavlovia.org → Dashboard → the experiment → **PILOTING** (free, only
   you) for testing; **RUNNING** for real data. New projects start INACTIVE.
   RUNNING needs a licence or credits: check the Store for an LMU site licence; otherwise
   ~£0.20 per saved run.

## Testing on Pavlovia

Run URL: `https://run.pavlovia.org/simonknogler/wp3-second-look/`

Query parameters work the same as locally:

| Parameter | Purpose |
|---|---|
| `?t1=6&t2=12&calmin=10&calmax=15` | short run for a feel test |
| `?bonus=1.00` | quadratic scoring rule with a £1 maximum |
| `?datapipe=<id>` | DataPipe id without a redeploy |
| `?pid=<id>` | participant id |

The dashboard's *Pilot* button appends `&__pilotToken=…` automatically; tokens expire
after about an hour — regenerate from the dashboard.

## Prolific (later)

Study URL to give Prolific:

```
https://run.pavlovia.org/simonknogler/wp3-second-look/?PROLIFIC_PID={{%PROLIFIC_PID%}}&STUDY_ID={{%STUDY_ID%}}&SESSION_ID={{%SESSION_ID%}}&completion=https://app.prolific.com/submissions/complete?cc=XXXXXXXX
```

`index.html` reads the three Prolific ids (written into every data row) and, when
`completion` is set, redirects there after showing the bonus for four seconds — that is
what credits the participant. Prolific settings that matter: desktop only (Prolific cannot
filter mouse vs. trackpad — the instructions ask for a mouse and low movement is flagged
in the data), 18–50, no neurological/psychiatric history, ~75 min allowance.

## Everyday workflow

```bash
# 1. edit experiment/web/index.html (or engine.js) in the main repo
# 2. test locally
cd experiment/web && python3 -m http.server 8000     # → http://localhost:8000
# 3. commit to the main repo
git add -A && git commit -m "..." && git push
# 4. deploy to Pavlovia (default path ~/Desktop/PhD/Experiments/wp3-pavlovia)
./tools/deploy_pavlovia.sh
# 5. hard-reload the run URL — Pavlovia caches aggressively (Cmd+Shift+R)
```

## Known pitfalls

- **Caching.** After a deploy the old version often persists; hard-reload, and if still
  stale use the dashboard's synchronise/reset on the study.
- **`motion_pool.bin` is 2.9 MB** — expect a short blank moment on slow connections.
- **Credits are consumed in RUNNING mode**, including your own test runs. Pilot in PILOTING.
- **Fullscreen** is requested on the opening click; some browsers refuse it inside a frame.
  The study continues either way.
