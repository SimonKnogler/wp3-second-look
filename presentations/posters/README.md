# Posters

Both posters live on one canvas: https://claude.ai/artifact/UtUMRipxKyuW9JpaScgnLp
(private; share and export to PDF from the page's Share menu).

| Poster | Artboard | Source |
|---|---|---|
| Expecting Control (WP1 results) | `Experiment1.dc.html` | generated from `wp1_results.json` |
| A Second Look (WP3 plan) | `Main.dc.html` | written by hand on the canvas |

## Routine: new WP1 data

```bash
python3 monitor_wp1.py /Volumes/INTENSO --dry-run    # look first, writes nothing
python3 monitor_wp1.py /Volumes/INTENSO              # behavioural statistics + poster
python3 monitor_wp1.py /Volumes/INTENSO --metad      # also refit the M-ratio, about 3 min
```

Then publish `out/project/Experiment1.dc.html` to the canvas.

What the command does:

1. Reads every `CDT_..._response_<id>.csv`; ignores kinematics files and other name patterns.
2. Excludes by the pre-specified learning check (below 0.10) and by name (`exclude` in the
   bundle). Flags high timeout rates and out-of-range medium accuracy without excluding.
3. **Re-derives the participants it already knows and compares them with the stored cell
   means.** A difference above 0.005 means the trial selection or the files changed.
4. Recomputes means, within-participant CIs, the 2 x 2 ANOVA and the cue effect per rotation.
5. Prints the key effects and p-values before and after, appends to `history`, rebuilds the poster.

The drift-diffusion model is not part of the routine. Its section keeps the last fit, and
every section of the poster states the N it rests on.

## Files

| File | Role |
|---|---|
| `monitor_wp1.py` | the routine above |
| `wp1_stats.py` | statistics from cell means; `--check` reproduces the stored values |
| `build_wp1_poster.py` | poster from the bundle |
| `wp1_results.json` | the bundle: cell means, statistics, M-ratio, drift-diffusion results, conclusion |
| `wp1/` | analysis scripts copied from the analysis chat, see `wp1/SOURCES.md` |
| `out/` | generated poster, not tracked |

## Status

| Part | Status |
|---|---|
| Statistics from cell means | reproduces the N = 18 values to within 0.004 |
| Raw trials to cell means | runs on the real file format; **not yet checked against the N = 18 cell means**, because the study data are on the USB drive. The first run on the drive does that check. |
| M-ratio | scripts migrated; same check pending |
| Drift-diffusion model | scripts migrated; HSSM not installed on this machine; on request only |

The main-result row always shows, under each plot: the cue effect at 90° and at 0° with its
p-value, then the p-values of the cue effect, the rotation effect and their interaction.
The closing sentence is `conclusion` in the bundle and is never generated: reread it
whenever the numbers change.
