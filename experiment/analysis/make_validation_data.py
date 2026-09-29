#!/usr/bin/env python3
"""Simulate a small sample that behaves as the hypothesis says, in the web task's exact
file layout, so the planned analysis can be checked against a known truth.

What goes in (per participant, drawn around these group values):
  w_d(90 deg) ~ 1.0      disconfirming evidence used at its worth under the rotated mapping
  w_d(0 deg)  = 0.6 x    ...and at 60 % of its worth under the direct mapping   <- the hypothesis
  b           ~ 0.4      commitment to the choice, the same at both mappings
  w_c         ~ 0.9      confirming evidence, the same at both mappings
Everything else (staircase, psychometric function, rating noise, baseline confidence) is the
Rollwage-calibrated observer of power_wp3.py.

Files are written the way web/index.html's toCSV() writes them: same columns, same order,
JavaScript number and boolean formatting. ground_truth.csv holds the generating parameters.

  python make_validation_data.py OUTDIR [--n 10] [--seed 20260929]
"""
import argparse, pathlib, sys
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import simulate_wp3 as S      # noqa: E402
import power_wp3 as PW        # noqa: E402

WD0_OVER_WD90 = 0.6           # the hypothesis, as drawn on the poster


def js(v):
    """Format one cell the way JavaScript's String() would."""
    if v is None or (isinstance(v, (float, np.floating)) and np.isnan(v)):
        return ""
    if isinstance(v, (bool, np.bool_)):
        return "true" if v else "false"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return str(int(v)) if float(v).is_integer() else repr(float(v))
    return str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260929)
    a = ap.parse_args()
    out = pathlib.Path(a.outdir); (out / "data").mkdir(parents=True, exist_ok=True)
    cond = dict(pool=a.n, mu_delta=float(np.log(WD0_OVER_WD90)), sd_delta=0.30, b_mean=0.40, b_sd=0.30,
                b_shift0=0.0, noise=1.2, t1=30, t2=60, boost=1.2)
    P = PW.draw_pool(cond, a.seed)
    S.T1_N, S.T2_N, S.BOOST = cond["t1"], cond["t2"], cond["boost"]
    ids = [f"sim{i + 1:02d}" for i in range(a.n)]
    for i in range(a.n):
        rng = np.random.default_rng(a.seed * 1000 + i)
        df = S.simulate_participant(P.iloc[i], rng, "web", 0.005, 1)
        df["participant"] = ids[i]
        lines = [",".join(df.columns)] + [",".join(js(v) for v in row) for row in df.itertuples(index=False)]
        (out / "data" / f"CDT_wp3_{ids[i]}.csv").write_text("\n".join(lines))
    T = P.drop(columns=["order", "pdi"]).copy(); T["participant"] = ids
    T.to_csv(out / "ground_truth.csv", index=False)
    g = lambda c: float(np.exp(np.log(T[c]).mean()))
    print(f"[validation data] {a.n} participants, seed {a.seed} -> {out}/data")
    print(f"  generating group values (geometric means): w_d(0)={g('wd0'):.2f}  w_d(90)={g('wd90'):.2f}  "
          f"ratio={g('wd0') / g('wd90'):.2f}   b={T.b0.mean():.2f}   w_c={g('wc0'):.2f}")
    print(f"  true mode effect, log w_d(0) - log w_d(90): mean {T.delta_true.mean():+.3f}  SD {T.delta_true.std(ddof=1):.3f}")


if __name__ == "__main__":
    main()
