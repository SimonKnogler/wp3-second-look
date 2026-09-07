"""Export the real motion pool (core_pool.npy) to a compact Float32 binary the
browser port loads via fetch(). Run once:  python export_pool_for_web.py

Output next to this script:
  motion_pool.bin   little-endian Float32, shape [N, F, 2] flattened row-major
  motion_pool.json  {"n": N, "frames": F}   (metadata)
"""
import json, pathlib
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
POOL = HERE.parent.parent / "Motion_Library" / "core_pool.npy"
N_KEEP = 1200   # plenty for a session (~400 pairs used); keeps the asset ~2.9 MB

def main():
    a = np.load(POOL).astype(np.float32)   # [1600, 298, 2]
    a = a[:N_KEEP]
    n, f, _ = a.shape
    (HERE / "motion_pool.bin").write_bytes(a.tobytes(order="C"))
    (HERE / "motion_pool.json").write_text(json.dumps({"n": int(n), "frames": int(f)}))
    print(f"wrote motion_pool.bin  ({a.nbytes/1e6:.1f} MB)  shape [{n}, {f}, 2]")
    print(f"wrote motion_pool.json  {{n:{n}, frames:{f}}}")

if __name__ == "__main__":
    main()
