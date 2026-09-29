#!/usr/bin/env python3
"""One command to refresh the WP1 behavioural results and rebuild the poster.

    python monitor_wp1.py DATA_DIR              behavioural statistics + poster
    python monitor_wp1.py DATA_DIR --metad      also refit the hierarchical M-ratio (about 3 min)
    python monitor_wp1.py DATA_DIR --dry-run    report only, write nothing

DATA_DIR holds the raw files CDT_v2_blockwise_fast_response_<id>.csv (the USB drive itself
works: /Volumes/INTENSO). Kinematics files and files with other name patterns are ignored.

Trial selection is the one used for the publication figures (wp1/behaviour/pub_figures.py):
rows without a phase dropped, timeouts dropped, test phase, actual_difficulty_level == medium,
cell = participant x rotation x cue. Participants are excluded by the pre-specified learning
check (accuracy high cue - low cue in the learning phase below 0.10) or by name in
bundle["exclude"]. Everything else is flagged, never silently dropped.

The drift-diffusion model is NOT part of this routine; its section on the poster keeps the
last fit and states the N it was fitted on.
"""
import argparse, datetime, glob, json, os, re, sys, tempfile
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wp1_stats                       # noqa: E402
import build_wp1_poster                # noqa: E402

CELLS = ("0_low", "0_high", "90_low", "90_high")
MEASURES = ("agency_rating", "confidence_rating", "accuracy", "rt_choice")
LEARNING_CHECK = 0.10
NAME = re.compile(r"CDT_.*_response_(\d+)\.csv$")


def load(data_dir):
    frames, ignored = [], []
    for f in sorted(glob.glob(os.path.join(data_dir, "CDT_*.csv"))):
        m = NAME.search(os.path.basename(f))
        if "kinematics" in f:
            continue
        if not m:
            ignored.append(os.path.basename(f)); continue
        d = pd.read_csv(f, low_memory=False)
        if "phase" not in d.columns:
            ignored.append(os.path.basename(f)); continue
        d = d[d.phase.notna()].copy()
        d["subj"] = m.group(1)                      # id from the file name: "004" and "4" stay distinct
        d["file"] = f
        frames.append(d)
    if not frames:
        sys.exit(f"no participant files found in {data_dir}")
    df = pd.concat(frames, ignore_index=True)
    df["ph"] = (df.phase.astype(str).str.replace(r"_-?\d+$", "", regex=True).str.replace("_interleaved", "", regex=False))
    df["to"] = df.is_timeout.astype(str).eq("True")
    for c in ("angle_bias", "accuracy", "rt_choice", "agency_rating", "confidence_rating"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df, ignored


def quality(df):
    rows = []
    for s, d in df.groupby("subj"):
        ok = d[~d.to]
        learn, test = ok[ok.ph.eq("learning")], ok[ok.ph.eq("test")]
        med = test[test.actual_difficulty_level.eq("medium")] if "actual_difficulty_level" in test else test.iloc[0:0]
        cue = "cue_difficulty_prediction"
        acc = lambda t, level: t.loc[t[cue].eq(level), "accuracy"].mean() if cue in t and len(t) else np.nan
        task = d[d.ph.isin(["learning", "test"])]
        rows.append(dict(P=s, timeouts=float(task.to.mean()) if len(task) else np.nan,
                         learn_delta=float(acc(learn, "high") - acc(learn, "low")),
                         med_acc=float(med.accuracy.mean()) if len(med) else np.nan, med_n=int(len(med)),
                         file=os.path.basename(d.file.iloc[0])))
    return pd.DataFrame(rows)


def cell_means(df, subjects):
    ok = df[~df.to & df.ph.eq("test") & df.subj.isin(subjects)]
    med = ok[ok.actual_difficulty_level.eq("medium")]
    out = {m: {} for m in MEASURES}
    for m in MEASURES:
        g = med.groupby(["subj", "angle_bias", "cue_difficulty_prediction"])[m].mean()
        for s in subjects:
            try:
                out[m][str(int(s))] = {f"{a}_{c}": float(g[(s, a, c)]) for a in (0, 90) for c in ("low", "high")}
            except KeyError:
                pass
    return out, med


def metad(med_files, bundle):
    """Hierarchical M-ratio by rotation and by cue, with the migrated scripts in wp1/metad."""
    sys.path.insert(0, os.path.join(HERE, "wp1", "metad"))
    import hmetad as H
    from metad import trials2counts
    from scipy.stats import norm
    strip = lambda d: {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in d.items() if k not in ("dgrid", "pdiff")}
    with tempfile.TemporaryDirectory() as tmp:
        for f in med_files:
            os.symlink(f, os.path.join(tmp, os.path.basename(f)))
        cells = H.load_cells(tmp)
        fit = H.fit_hierarchical(cells); s = H.summarise(fit)
        mu, sg = {0: s["mu0"][1], 90: s["mu90"][1]}, s["sigma"][1]
        indiv = []
        for p in fit["per"]:
            if p["ll"] is None:
                continue
            w = np.exp(p["ll"] - np.nanmax(p["ll"])); w[~np.isfinite(w)] = 0
            post = w * norm.pdf(fit["logM"], mu[p["cond"]], sg); post /= post.sum()
            indiv.append(dict(subject=p["subject"], cond=int(p["cond"]), d1=float(p["d1"]), n=int(p["n"]),
                              logM_shrunk=float((post * fit["logM"]).sum()), logM_ml=float(fit["logM"][np.argmax(w)])))
        bundle["metad"] = dict(summary=strip(s), paired=strip(H.fit_paired(cells)), indiv=indiv, n=len({c["subject"] for c in cells}))
        # by cue: same model, the two conditions are the cues (low -> slot 0, high -> slot 90), rotations pooled
        df = pd.concat([pd.read_csv(f, low_memory=False) for f in med_files], ignore_index=True)
        df["s"] = df.participant.astype(str).str.zfill(3)
        t = df[(df.phase.astype(str).str.startswith("test")) & (df.is_timeout != True)]   # noqa: E712
        med = t[t.actual_difficulty_level.eq("medium")].dropna(subset=["confidence_rating"])
        by = []
        for sj in sorted(med.s.unique()):
            for level, slot in (("low", 0), ("high", 90)):
                g = med[med.s.eq(sj) & med.cue_difficulty_prediction.eq(level)]
                if len(g) < 20:
                    continue
                n1, n2 = trials2counts((g.true_side == "right").astype(int).values, (g.resp_side == "right").astype(int).values,
                                       g.confidence_rating.astype(int).values, 4)
                by.append(dict(subject=sj, cond=slot, nR_S1=n1, nR_S2=n2, n=len(g)))
        sc, pc = H.summarise(H.fit_hierarchical(by)), H.fit_paired(by)
        e = lambda q: [float(np.exp(x)) for x in q]
        bundle["mratio_by_cue"] = dict(low=e(sc["mu0"]), high=e(sc["mu90"]), paired_dlogM=[float(x) for x in pc["diff"]],
                                       p_gt0=float(pc["p_gt0"]), n=len({c["subject"] for c in by}))


def key_numbers(stats):
    return {m: dict(cue_p=stats[m]["anova"]["cue"]["p"], rotation_p=stats[m]["anova"]["angle"]["p"],
                    interaction_p=stats[m]["anova"]["interaction"]["p"], eff90=stats[m]["anova"]["eff90"]["M"],
                    eff90_p=stats[m]["anova"]["eff90"]["p"], eff0=stats[m]["anova"]["eff0"]["M"], eff0_p=stats[m]["anova"]["eff0"]["p"])
            for m in ("agency_rating", "confidence_rating", "accuracy")}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data_dir")
    ap.add_argument("--bundle", default=os.path.join(HERE, "wp1_results.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "out", "project", "Experiment1.dc.html"))
    ap.add_argument("--metad", action="store_true", help="refit the hierarchical M-ratio (about 3 min)")
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    a = ap.parse_args()

    B = json.load(open(a.bundle))
    old_cells, old_keys, old_n = B["cells"], key_numbers(B["stats"]), B["N"]
    df, ignored = load(a.data_dir)
    q = quality(df)

    manual = B.get("exclude", {})
    q["excluded"] = ""
    for i, r in q.iterrows():
        if r.P in manual:
            q.at[i, "excluded"] = manual[r.P]
        elif not np.isfinite(r.learn_delta) or r.med_n == 0:
            q.at[i, "excluded"] = "no learning or no medium test trials"
        elif r.learn_delta < LEARNING_CHECK:
            q.at[i, "excluded"] = f"learning check {r.learn_delta:.2f} below {LEARNING_CHECK:.2f}"
    incl = list(q[q.excluded.eq("")].P)
    cells, med = cell_means(df, incl)
    complete = [p for p in cells["agency_rating"] if all(np.isfinite(cells[m].get(p, {}).get(c, np.nan)) for m in MEASURES for c in CELLS)]
    for s in incl:
        if str(int(s)) not in complete:
            q.loc[q.P.eq(s), "excluded"] = "a cell of the 2 x 2 design is empty"
    cells = {m: {p: cells[m][p] for p in complete} for m in MEASURES}
    n = len(complete)

    print(f"\n=== WP1 monitor · {a.data_dir} ===")
    print(f"files read: {q.shape[0]}   included: {n}   excluded: {(q.excluded != '').sum()}   ignored by name: {len(ignored)}")
    for _, r in q[q.excluded != ""].iterrows():
        print(f"  excluded  P{r.P:<5} {r.excluded}")
    flags = q[q.excluded.eq("") & ((q.timeouts > .10) | (q.med_acc < .55) | (q.med_acc > .85))]
    for _, r in flags.iterrows():
        print(f"  flagged   P{r.P:<5} timeouts {r.timeouts:.1%}, medium accuracy {r.med_acc:.2f}  (kept)")

    # regression check: participants we already know must come out exactly as before
    known = [p for p in complete if p in old_cells["agency_rating"]]
    worst, who = 0.0, None
    for m in MEASURES:
        for p in known:
            for c in CELLS:
                dlt = abs(cells[m][p][c] - old_cells[m][p][c])
                if dlt > worst:
                    worst, who = dlt, (p, m, c)
    new = sorted((p for p in complete if p not in old_cells["agency_rating"]), key=int)
    gone = sorted((p for p in old_cells["agency_rating"] if p not in complete), key=int)
    print(f"\nknown participants re-derived: {len(known)} of {old_n}   largest difference to the stored cell means: {worst:.4f}"
          + (f"  (P{who[0]}, {who[1]}, {who[2]})" if who and worst > .005 else ""))
    if worst > .005:
        print("  WARNING: known participants do not reproduce. Trial selection or the files differ; do not trust the update.")
    if gone:
        print(f"  WARNING: in the stored results but not in this folder: {', '.join('P' + p for p in gone)}")
    print(f"new participants: {', '.join('P' + p for p in new) if new else 'none'}")
    if n < 3:
        print("\nfewer than 3 complete participants: no statistics."); return

    stats = {m: wp1_stats.analyse(cells[m]) for m in MEASURES}
    now = key_numbers(stats)
    pf = lambda p: "n/a" if p != p else "<.001" if p < .001 else build_wp1_poster.lead0(f"{p:.3f}")
    print(f"\n{'':<22}{'N = ' + str(old_n):>16}{'N = ' + str(n):>16}")
    for m, label in (("agency_rating", "agency"), ("confidence_rating", "confidence"), ("accuracy", "accuracy")):
        for k, lab in (("eff90", "cue effect at 90°"), ("eff0", "cue effect at 0°")):
            print(f"{label + ' · ' + lab:<32}{old_keys[m][k]:>+8.2f} p {pf(old_keys[m][k + '_p']):<6}{now[m][k]:>+8.2f} p {pf(now[m][k + '_p'])}")
        for k, lab in (("cue_p", "cue"), ("rotation_p", "rotation"), ("interaction_p", "cue × rotation")):
            print(f"{label + ' · ' + lab:<32}{'':>8} p {pf(old_keys[m][k]):<6}{'':>8} p {pf(now[m][k])}")

    if a.dry_run:
        print("\ndry run: nothing written."); return
    B.update(N=n, participants=sorted(map(int, complete)), cells=cells, stats=stats, updated=datetime.date.today().strftime("%d %b %Y"),
             sample=q.drop(columns=["file"]).replace({np.nan: None}).to_dict("records"))
    if n != old_n or not B.get("history"):
        B.setdefault("history", []).append(dict(date=datetime.date.today().isoformat(), N=n, **{m: now[m] for m in now}))
    if a.metad:
        print("\nrefitting the hierarchical M-ratio ...")
        files = sorted(set(df[df.subj.isin([s for s in incl if str(int(s)) in complete])].file))
        metad(files, B)
    json.dump(B, open(a.bundle, "w"), indent=1, ensure_ascii=False)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(build_wp1_poster.build(B))
    stale = [f"{k} (N = {v})" for k, v in (("M-ratio", B["metad"].get("n")), ("drift-diffusion", B["ddm"].get("n_participants"))) if v != n]
    print(f"\nresults -> {a.bundle}\nposter  -> {a.out}")
    if stale:
        print("not refitted, still from an earlier sample: " + ", ".join(stale))
    print("the closing sentence on the poster is bundle['conclusion']: reread it against the numbers above.")


if __name__ == "__main__":
    main()
