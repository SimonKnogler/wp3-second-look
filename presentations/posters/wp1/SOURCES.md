# Migrated analysis scripts

Copied on 29 Sep 2026 so that the poster routine does not depend on folders in `~/Downloads`.
The originals were left where they are. Files are unchanged unless noted.

| Here | Copied from | Role |
|---|---|---|
| `behaviour/pub_figures.py` | `~/Downloads/CDT_Publikationsabbildungen/scripts/` | publication figures and `stats.md`; defines the trial selection that `monitor_wp1.py` reuses |
| `behaviour/hypothesen_uebersicht.py` | same | hypotheses overview figure |
| `behaviour/agency_sens.R` | `~/Downloads/CDT_Analysen_N14/scripts/` | sensitivity analysis for agency (R, lme4) |
| `metad/metad.py`, `metad/hmetad.py` | `metasoa/analysis/comprehensive_analysis/` | meta-d' and the hierarchical M-ratio, NumPy/SciPy only, no sampler |
| `metad/metad_fig_data.py` | `~/Downloads/CDT_Publikationsabbildungen/scripts/` | **changed:** imports the copies next to it instead of a hard-coded path |
| `ddm/prep.py`, `fit_hssm.py`, `report.py`, `recover.py`, `fig_hypotheses.py`, `kin2trials.py` | `~/Downloads/CDT_HDDM/` | drift-diffusion pipeline; needs HSSM, run on request only |
| `ddm/HDDM_analysis_plan.md` | same | analysis plan |

Participant data are not copied here. They live on the USB drive (`/Volumes/INTENSO`).
