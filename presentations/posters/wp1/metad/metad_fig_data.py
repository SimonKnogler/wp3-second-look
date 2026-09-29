"""Hierarchical + paired meta-d' on the included sample; saves group posteriors
and empirical-Bayes shrunk individual M-ratios for the publication figure."""
import sys, json, numpy as np
from scipy.stats import norm
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # migrated: use the copies next to this file
import hmetad as H
data_dir, out = sys.argv[1], sys.argv[2]
cells = H.load_cells(data_dir)
fit = H.fit_hierarchical(cells)
s = H.summarise(fit)
mu = {0: s["mu0"][1], 90: s["mu90"][1]}; sg = s["sigma"][1]
indiv = []
for p in fit["per"]:
    if p["ll"] is None:
        continue
    w = np.exp(p["ll"] - np.nanmax(p["ll"])); w[~np.isfinite(w)] = 0
    post = w * norm.pdf(fit["logM"], mu[p["cond"]], sg); post /= post.sum()
    indiv.append(dict(subject=p["subject"], cond=int(p["cond"]), d1=float(p["d1"]), n=int(p["n"]),
                      logM_shrunk=float((post * fit["logM"]).sum()),
                      logM_ml=float(fit["logM"][np.argmax(w)])))
pair = H.fit_paired(cells)
conv = lambda v: v.tolist() if isinstance(v, np.ndarray) else v
json.dump(dict(summary={k: conv(v) for k, v in s.items()},
               paired={k: conv(v) for k, v in pair.items()},
               indiv=indiv), open(out, "w"))
print("META-D DONE")
