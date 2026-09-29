"""Rebuild test-phase trial table from a CDT kinematics file (for when the behavioral CSV is missing)."""
import sys, numpy as np, pandas as pd
def rebuild(kin):
    k = pd.read_csv(kin, dtype={"session": str})
    k = k[k.phase == "test"]
    g = k.groupby(["angle_bias", "trial_num"], sort=False)
    t = g.last().reset_index()
    f = g.first().reset_index()
    tx = np.where(f.true_shape == "square", f.square_x, f.dot_x)
    t["true_side"] = np.where(tx > 0, "right", "left")
    other = np.where(t.true_side == "right", "left", "right")
    t["resp_side"] = np.where(t.resp_shape == t.true_shape, t.true_side, np.where(t.resp_shape.isin(["dot", "square"]), other, "timeout"))
    t["rt_choice"] = g.timestamp.max().values
    t["accuracy"] = np.where(t.resp_shape.isin(["dot", "square"]), (t.true_shape == t.resp_shape).astype(float), np.nan)
    t["is_timeout"] = np.where(t.resp_shape.isin(["dot", "square"]), "False", "True")
    # ponytail: medium = staircase grid value (multiple of 0.05); easy/hard are off-grid offsets. Validated against real CSVs.
    on = lambda x: np.isclose(x * 20, np.round(x * 20), atol=1e-6)
    grid = on(t.prop_used) | on(t.prop_used - 0.02)  # staircase grids: k*0.05 and 0.02+k*0.05
    med = t[grid].groupby("angle_bias").prop_used.median()
    t["actual_difficulty_level"] = np.where(grid, "medium", np.where(t.prop_used > t.angle_bias.map(med), "easy", "hard"))
    t["cue_difficulty_prediction"] = t.expect_level
    t["phase"] = "test_" + t.angle_bias.astype(str)
    return t[["phase", "angle_bias", "trial_num", "prop_used", "actual_difficulty_level", "cue_difficulty_prediction",
              "accuracy", "is_timeout", "rt_choice", "true_side", "resp_side", "confidence_rating", "agency_rating", "early_response"]]
if __name__ == "__main__":
    t = rebuild(sys.argv[1])
    if len(sys.argv) > 2:  # validate against real CSV
        c = pd.read_csv(sys.argv[2]); c = c[c.phase.fillna("").str.startswith("test")].reset_index(drop=True)
        c = c.sort_values(["angle_bias"], kind="stable").reset_index(drop=True); r = t.sort_values(["angle_bias"], kind="stable").reset_index(drop=True)
        print(len(c), len(r))
        for col in ["actual_difficulty_level", "cue_difficulty_prediction", "accuracy", "confidence_rating", "agency_rating", "is_timeout"]:
            a = c[col].astype(str).replace("nan","nan").str.replace(".0", "", regex=False); b = r[col].astype(str).str.replace(".0", "", regex=False)
            print(f"{col:28s} match {np.mean(a.values == b.values):.4f}")
        print("rt corr", np.corrcoef(c.rt_choice.astype(float).fillna(5), r.rt_choice)[0, 1], "median abs diff", np.nanmedian(abs(c.rt_choice.astype(float) - r.rt_choice)))
    else:
        t.to_csv(sys.argv[1].replace("_kinematics.csv", "_REBUILT_from_kinematics.csv"), index=False)

def calib_threshold(kin):
    """Replay the experiment's own 1u2d staircase on the calibration trials -> threshold per angle."""
    sys.path.insert(0, "/Users/simonknogler/Desktop/PhD/Experiments/metasoa/CDT_experiment_deploy/experiment/task")
    from staircase import TwoDownOneUpStaircase
    k = pd.read_csv(kin, usecols=["phase", "angle_bias", "trial_num", "prop_used", "true_shape", "resp_shape"])
    t = k[k.phase == "calibration"].groupby(["angle_bias", "trial_num"], sort=False).last().reset_index()
    out = {}
    for a, g in t.groupby("angle_bias"):
        q = TwoDownOneUpStaircase()
        for _, r in g.sort_values("trial_num").iterrows():
            if r.resp_shape in ("dot", "square"):
                q.update(r.prop_used, r.true_shape == r.resp_shape)
        out[a] = q.threshold_estimate()
    return out

def rebuild_full(kin, participant):
    """All phases in the behavioral-CSV layout used by the analysis scripts."""
    test = rebuild(kin)
    k = pd.read_csv(kin, usecols=["timestamp", "phase", "angle_bias", "trial_num", "prop_used", "expect_level", "true_shape", "resp_shape"])
    k = k[k.phase.isin(["calibration", "practice"])]
    g = k.groupby(["phase", "angle_bias", "trial_num"], sort=False)
    o = g.last().reset_index(); o["rt_choice"] = g.timestamp.max().values
    resp = o.resp_shape.isin(["dot", "square"])
    o["accuracy"] = np.where(resp, (o.true_shape == o.resp_shape).astype(float), np.nan)
    o["is_timeout"] = np.where(resp, "False", "True")
    o["cue_difficulty_prediction"] = np.where(o.phase == "practice", o.expect_level, np.nan)
    o["actual_difficulty_level"] = np.where(o.phase == "practice", o.expect_level.map({"high": "easy", "low": "hard"}), np.nan)
    thr = calib_threshold(kin)
    o["staircase_threshold"] = np.where(o.phase == "calibration", o.angle_bias.map(thr), np.nan)
    o["phase"] = np.where(o.phase == "calibration", "calibration_interleaved", "learning_" + o.angle_bias.astype(str))
    out = pd.concat([o.drop(columns=["expect_level", "true_shape", "resp_shape", "timestamp"]), test], ignore_index=True)
    out["participant"] = participant
    return out
