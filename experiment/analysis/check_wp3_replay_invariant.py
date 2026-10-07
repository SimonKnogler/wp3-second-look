"""Verify the WP3 replay invariant on a kinematics CSV: for every Task-2 trial,
the evidence sample must show the SAME side layout and the SAME applied rotation
as the decision trial. (Regression check for the 2026-09-03 bug, design doc §10b.)

Usage:  python3 check_wp3_replay_invariant.py <kinematics.csv | web trial CSV> [more.csv ...]

The lab writes a kinematics file; the web build (experiment/web) writes the layout of both
looks into its trial CSV instead (left_shape / applied_angle_bias / true_shape and their
post_* twins, design doc §10l). Either file works.
Exit code 1 if any trial violates the invariant.
"""
import sys
import pandas as pd


def check_web(path, d):
    t = d[(d.phase == "wp3_task2") & (d.get("trial_type", "standard") != "strength")]
    t = t.dropna(subset=["post_left_shape"])          # timeouts have no second look
    if t.empty:
        return path, 0, 0, "no Task-2 trials with a second look"
    ok = ((t.left_shape == t.post_left_shape)
          & (t.applied_angle_bias.astype(float) == t.post_applied_angle_bias.astype(float))
          & (t.true_shape == t.post_true_shape))
    bad = t.loc[~ok, ["trial_idx", "left_shape", "post_left_shape", "applied_angle_bias",
                      "post_applied_angle_bias", "true_shape", "post_true_shape"]]
    return path, len(t), len(bad), bad


def check(path):
    head = pd.read_csv(path, nrows=0).columns
    if "post_left_shape" in head:
        return check_web(path, pd.read_csv(path, low_memory=False))
    k = pd.read_csv(path, usecols=lambda c: c in {
        "trial_num", "phase", "left_shape", "applied_angle_bias", "true_shape"})
    sub = k[k.phase.isin(["wp3_task2", "wp3_evidence"])]
    if sub.empty:
        return path, 0, 0, "no Task-2 trials"
    first = sub.groupby(["trial_num", "phase"]).first().reset_index()
    p = first.pivot(index="trial_num", columns="phase",
                    values=["left_shape", "applied_angle_bias", "true_shape"])
    n_raw = len(p)
    p = p.dropna()
    if n_raw and p.empty:
        # every trial lost a value in one phase -> logging gap, not a pass
        return path, n_raw, n_raw, "all trials have missing left_shape/applied_angle in one phase (logging gap?)"
    side_ok = p[("left_shape", "wp3_task2")] == p[("left_shape", "wp3_evidence")]
    rot_ok = p[("applied_angle_bias", "wp3_task2")] == p[("applied_angle_bias", "wp3_evidence")]
    tgt_ok = p[("true_shape", "wp3_task2")] == p[("true_shape", "wp3_evidence")]
    bad = p[~(side_ok & rot_ok & tgt_ok)]
    return path, len(p), len(bad), bad


if __name__ == "__main__":
    fail = False
    for f in sys.argv[1:]:
        path, n, nbad, detail = check(f)
        status = "OK" if nbad == 0 else "VIOLATION"
        print(f"{status:9s} {n:3d} trials, {nbad} bad  — {path}")
        if nbad:
            fail = True
            print(detail if isinstance(detail, str) else detail.to_string())
    sys.exit(1 if fail else 0)
