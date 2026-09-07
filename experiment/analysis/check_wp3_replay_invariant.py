"""Verify the WP3 replay invariant on a kinematics CSV: for every Task-2 trial,
the evidence sample must show the SAME side layout and the SAME applied rotation
as the decision trial. (Regression check for the 2026-09-03 bug, design doc §10b.)

Usage:  python3 check_wp3_replay_invariant.py <kinematics.csv> [more.csv ...]
Exit code 1 if any trial violates the invariant.
"""
import sys
import pandas as pd


def check(path):
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
