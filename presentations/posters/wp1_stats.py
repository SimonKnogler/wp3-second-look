#!/usr/bin/env python3
"""Behavioural statistics for the WP1 poster, from participant cell means.

Input : a results bundle (wp1_results.json) whose "cells" hold, per measure and participant,
        the four medium-trial cell means  0_low, 0_high, 90_low, 90_high.
Output: the same bundle with "stats" recomputed: cell means, 95 % within-participant CIs
        (Cousineau-Morey), the 2 x 2 repeated-measures ANOVA (cue, rotation, interaction) and
        the cue effect at each rotation.

    python wp1_stats.py wp1_results.json            recompute and write back
    python wp1_stats.py wp1_results.json --check    compare against the stored values, change nothing

With two levels per factor every ANOVA effect is a one-sample t-test on a per-participant
contrast (F = t^2), so no ANOVA library is needed.

ponytail: starts from cell means, not raw trials. The raw-trial step (which trials count as
"medium test trials", timeout and RT exclusions) is added once real files are here to validate
it against -- the N = 18 cell means in the bundle are the regression target for that.
"""
import json, math, sys
import numpy as np
from scipy import stats as st

CELLS = ("0_low", "0_high", "90_low", "90_high")
MEASURES = ("agency_rating", "confidence_rating", "accuracy", "rt_choice")


def analyse(cells):
    pids = sorted(cells, key=int)
    X = np.array([[cells[p][k] for k in CELLS] for p in pids], float)
    n, J = X.shape
    tc = st.t.ppf(.975, n - 1)
    Xn = X - X.mean(1, keepdims=True) + X.mean()                       # Cousineau normalisation
    ci = tc * Xn.std(0, ddof=1) * math.sqrt(J / (J - 1)) / math.sqrt(n)  # Morey correction

    def contrast(v):
        t, p = st.ttest_1samp(v, 0)
        sd = v.std(ddof=1); h = tc * sd / math.sqrt(n)
        return dict(M=float(v.mean()), ci=[float(v.mean() - h), float(v.mean() + h)], t=float(t), p=float(p),
                    dz=float(v.mean() / sd), n_pos=int((v > 0).sum()), n=int(n))

    def effect(v):
        c = contrast(v)
        return dict(F=c["t"] ** 2, df1=1, df2=n - 1, p=c["p"])

    a, b, c, d = X.T                       # 0_low, 0_high, 90_low, 90_high
    return dict(means=dict(zip(CELLS, map(float, X.mean(0)))), ci=dict(zip(CELLS, map(float, ci))),
                anova=dict(cue=effect(((b + d) - (a + c)) / 2), angle=effect(((c + d) - (a + b)) / 2),
                           interaction=effect((d - c) - (b - a)), eff0=contrast(b - a), eff90=contrast(d - c)))


def main():
    path = sys.argv[1]; check = "--check" in sys.argv
    B = json.load(open(path))
    worst = 0.0
    for m in MEASURES:
        if m not in B["cells"]:
            continue
        new = analyse(B["cells"][m])
        if check:
            old = B["stats"][m]
            for k in ("cue", "angle", "interaction", "eff0", "eff90"):
                worst = max(worst, abs(new["anova"][k]["p"] - old["anova"][k]["p"]))
            for k in CELLS:
                worst = max(worst, abs(new["means"][k] - old["means"][k]), abs(new["ci"][k] - old["ci"][k]))
        else:
            B["stats"][m] = new
    if check:
        print(f"largest difference to the stored values: {worst:.4f}")
        assert worst < 0.01, "recomputed statistics differ from the stored ones"
        print("OK")
    else:
        B["N"] = len(B["cells"]["agency_rating"]); B["participants"] = sorted(map(int, B["cells"]["agency_rating"]))
        json.dump(B, open(path, "w"), indent=1)
        print(f"statistics recomputed for N = {B['N']} -> {path}")


if __name__ == "__main__":
    main()
