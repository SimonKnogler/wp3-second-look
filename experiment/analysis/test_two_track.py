"""Checks for the two-track design (design doc §10j). Plain asserts: `python test_two_track.py`
(pytest also collects the test_* functions)."""
import pathlib, sys
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import simulate_wp3 as S      # noqa: E402
import fit_wp3_model as F     # noqa: E402


def test_delta_track_holds_85_percent():
    """The weighted up-down aims at up/(up+down) = 85 %. The floor on the offset (0.3 logit) and the
    jitter of the offset (SD ~0.3) push the delivered accuracy up by about two points: 85-88 %."""
    rng = np.random.default_rng(1)
    t = S.logit(0.5) + 0.346 / 2.2          # threshold such that the standard prop 0.5 gives 70.7 % correct
    acc = []
    for _ in range(40):
        dt, hits = S.DeltaTrack(), []
        for _ in range(300):
            p = S.p_correct(S.clamp(S.sig(S.logit(0.5) + dt.v)), t, 2.2)                # strength trial: standard prop + offset
            c = rng.random() < p; dt.update(c); hits.append(c)
        acc.append(np.mean(hits[100:]))
    assert 0.85 <= np.mean(acc) <= 0.88, np.mean(acc)


def test_acc_priors_and_shrinkage():
    same = pd.DataFrame(dict(angle_bias=0, n=35, k=[30] * 20))                           # identical people
    a, b = F.acc_priors(same)[0]
    assert a + b >= 999 and abs(a / (a + b) - 30 / 35) < 1e-9                           # complete pooling
    rng = np.random.default_rng(2); p = rng.beta(8, 2, 400)                              # genuinely different people
    spread = pd.DataFrame(dict(angle_bias=0, n=35, k=rng.binomial(35, p)))
    a, b = F.acc_priors(spread)[0]
    assert 3 < a + b < 40, a + b                                                         # near the true Beta(8, 2): 10
    shrunk = lambda k, n: (k + a) / (n + a + b)
    assert abs(shrunk(0, 0) - a / (a + b)) < 1e-12                                       # no data -> group value
    assert abs(shrunk(900, 1000) - 0.9) < 0.01                                           # lots of data -> raw accuracy


def test_old_files_still_fit():
    """No strength trials -> the psychometric route, exactly as before."""
    c = dict(pool=1, mu_delta=0.0, sd_delta=0.3, b_mean=0.4, b_sd=0.3, b_shift0=0.0, noise=1.2, t1=30, t2=60, boost=1.2)
    import power_wp3 as PW
    S.T1_N, S.T2_N, S.D0_N, S.D1_N, S.D2_N = 30, 60, 0, 0, 0
    df = S.simulate_participant(PW.draw_pool(c, 3).iloc[0], np.random.default_rng(3), "web", 0.0, 1)
    df["is_timeout"] = F._bool(df["is_timeout"]); df["prop_high_clipped"] = F._bool(df["prop_high_clipped"])
    rows = F.fit_participant(df)
    assert all(r["fail"] == "" and "acc_high" not in r for r in rows), rows


def test_measured_route_uses_strength_accuracy():
    c = dict(pool=1, mu_delta=0.0, sd_delta=0.3, b_mean=0.4, b_sd=0.3, b_shift0=0.0, noise=1.2, t1=30, t2=60, boost=1.2)
    import power_wp3 as PW
    S.T1_N, S.T2_N, S.D0_N, S.D1_N, S.D2_N = 30, 60, 20, 10, 25
    df = S.simulate_participant(PW.draw_pool(c, 3).iloc[0], np.random.default_rng(3), "web", 0.0, 1)
    df["is_timeout"] = F._bool(df["is_timeout"]); df["prop_high_clipped"] = F._bool(df["prop_high_clipped"])
    st = df[df.trial_type == "strength"]
    assert st.prop_post.isna().all() and (st[st.wp3_task.notna()].evidence_level == 0).all()           # rated, never a second look
    assert st[st.wp3_task.notna()].wp3_confidence.notna().all() and st[st.phase == "calibration_strength"].wp3_confidence.isna().all()
    assert (st.phase == "calibration_strength").sum() == 40                                            # 20 per mapping
    for r in F.fit_participant(df):
        assert r["fail"] == "" and r["n_strength"] == 35 and r["n_task1"] == 30 and r["n_task2"] == 60, r   # strength trials stay out of the model
        raw = df[(df.angle_bias == r["angle"]) & (df.trial_type == "strength") & df.wp3_task.isin([1, 2])].accuracy.mean()
        assert abs(r["acc_high_raw"] - raw) < 1e-12 and abs(r["e_high"] - F.logit(r["acc_high"])) < 1e-9
    S.D0_N = S.D1_N = S.D2_N = 0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok  ", name)
