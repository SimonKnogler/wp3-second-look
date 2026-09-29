"""Build the DDM trial table from a folder of CDT files. Re-run whenever files are added.

    python prep.py <data_dir> <out_dir>

Writes <out_dir>/ddm_trials.csv, ddm_trials.sha (hash of the table -> fit cache key)
and prep_report.txt. Behavioural CSV missing but kinematics present -> rebuilt
(kin2trials.rebuild_full, validated 100 % on ratings/accuracy/cue for 14 participants).
"""
import sys, glob, re, hashlib, os
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kin2trials import rebuild_full

data_dir, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
EXCLUDE = {"13"}  # failed learning check (see memory/cdt-exclusions)

frames, notes = [], []
for kin in sorted(glob.glob(f"{data_dir}/CDT_*_kinematics.csv")):
    pid = re.search(r"_0*(\d+)_kinematics\.csv$", kin).group(1)
    if pid in EXCLUDE:
        notes.append(f"P{pid}: excluded (learning check)"); continue
    csv = kin.replace("_kinematics.csv", ".csv")
    if os.path.exists(csv):
        d = pd.read_csv(csv, low_memory=False)
    else:
        d = rebuild_full(kin, int(pid)); notes.append(f"P{pid}: behavioural CSV missing -> rebuilt from kinematics")
    d = d[d.phase.notna()]
    d = d[d.phase.astype(str).str.startswith("test")].copy()
    d["participant_id"] = pid
    frames.append(d)
t = pd.concat(frames, ignore_index=True)
t["timeout"] = t.is_timeout.astype(str).eq("True")
rates = t.groupby(["angle_bias", "cue_difficulty_prediction"]).timeout.mean().round(3)
t = t[~t.timeout & t.rt_choice.notna() & t.accuracy.notna()]
ddm = pd.DataFrame({
    "participant_id": t.participant_id.values,
    "trial_num": t.trial_num.values if "trial_num" in t else np.arange(len(t)),
    "rt": t.rt_choice.astype(float).values,
    "response": np.where(t.accuracy.astype(float) == 1, 1, -1),   # accuracy coding: upper = correct
    "cue": t.cue_difficulty_prediction.map({"low": -0.5, "high": 0.5}).values,
    "angle": t.angle_bias.astype(int).map({0: -0.5, 90: 0.5}).values,
    "cue_label": t.cue_difficulty_prediction.values,
    "angle_label": t.angle_bias.astype(int).values,
    "difficulty": t.actual_difficulty_level.values,
    "prop_used": t.prop_used.astype(float).values,
    "evidence": t.get("mean_evidence_preRT", pd.Series(np.nan, index=t.index)).values,
})
ddm = ddm[(ddm.rt > 0.25) & (ddm.rt < 5.0)]
ddm.to_csv(f"{out}/ddm_trials.csv", index=False)
sha = hashlib.sha256(pd.util.hash_pandas_object(ddm, index=False).values.tobytes()).hexdigest()[:12]
open(f"{out}/ddm_trials.sha", "w").write(sha)
med = ddm[ddm.difficulty == "medium"]
rep = [f"data hash {sha}", f"participants {ddm.participant_id.nunique()}: {sorted(ddm.participant_id.unique(), key=int)}",
       f"test trials {len(ddm)}, medium {len(med)}", "timeout rate per cell (dropped, treated as censored):", rates.to_string(),
       "medium trials per participant x cell (min): %d" % med.groupby(["participant_id", "angle", "cue"]).size().min(),
       "RT range %.2f-%.2f s" % (ddm.rt.min(), ddm.rt.max()), *notes]
open(f"{out}/prep_report.txt", "w").write("\n".join(rep))
print("\n".join(rep))
