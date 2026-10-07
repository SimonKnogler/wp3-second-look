"""Export the motion pool for the browser port, preprocessed EXACTLY as the lab script does.

The lab (CDT_windows_blockwise_fast_response.py) does not use core_pool.npy raw: every snippet is
validity-checked, speed-normalised and smoothed (preprocess_motion_pool), then a fixed "universal
set" is ranked by quality (select_universal_trajectory_set: 1240 primary + 40 overflow). The
functions below are copied from the lab script so the browser runs on the same trajectories in
the same order. Run once:  python export_pool_for_web.py

Output next to this script:
  motion_pool.bin   little-endian Float32, shape [N, F, 2] (velocities), primary set first
  motion_pool.json  {"n": N, "frames": F, "n_primary": 1240, "n_overflow": 40}
"""
import json, pathlib
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
POOL = HERE.parent.parent / "Motion_Library" / "core_pool.npy"


# ── copied from the lab script (analyze_trajectory_quality .. select_universal_trajectory_set) ──

def analyze_trajectory_quality(trajectory):
    velocities = np.diff(trajectory, axis=0)
    speeds = np.linalg.norm(velocities, axis=1)
    mean_speed = np.mean(speeds); std_speed = np.std(speeds)
    zero_movement_ratio = np.sum(speeds < 0.5) / len(speeds)
    high_jitter_ratio = np.sum(speeds > mean_speed + 3 * std_speed) / len(speeds)
    if len(velocities) > 1:
        unit = velocities / (speeds.reshape(-1, 1) + 1e-9)
        angle_changes = np.arccos(np.clip(np.sum(unit[:-1] * unit[1:], axis=1), -1, 1))
        jerkiness = np.std(angle_changes)
    else:
        jerkiness = 0
    return dict(mean_speed=mean_speed, zero_movement_ratio=zero_movement_ratio,
                high_jitter_ratio=high_jitter_ratio, jerkiness=jerkiness)


def is_trajectory_valid(trajectory, min_speed=1.0, max_zero_ratio=0.3, max_jitter_ratio=0.1, max_jerkiness=1.5):
    q = analyze_trajectory_quality(trajectory)
    return (q["mean_speed"] >= min_speed and q["zero_movement_ratio"] <= max_zero_ratio
            and q["high_jitter_ratio"] <= max_jitter_ratio and q["jerkiness"] <= max_jerkiness)


def normalize_trajectory(trajectory, target_speed_range=(3.0, 12.0), smooth_factor=0.45):
    velocities = np.diff(trajectory, axis=0)
    cur = np.mean(np.linalg.norm(velocities, axis=1))
    if cur > 0:
        velocities = velocities * (np.mean(target_speed_range) / cur)
    sm = velocities.copy()
    for i in range(1, len(velocities)):
        sm[i] = smooth_factor * sm[i - 1] + (1 - smooth_factor) * velocities[i]
    out = [trajectory[0]]
    for v in sm:
        out.append(out[-1] + v)
    return np.array(out)


def signature(trajectory):
    speeds = np.linalg.norm(np.diff(trajectory, axis=0), axis=1)
    return dict(mean_speed=np.mean(speeds), speed_variability=np.std(speeds), path_length=np.sum(speeds))


def main():
    raw = np.load(POOL)                                     # [1600, 298, 2] velocities
    kept, dropped = [], 0
    for snip in raw:
        traj = np.cumsum(snip, axis=0)
        if is_trajectory_valid(traj):
            kept.append(np.diff(normalize_trajectory(traj), axis=0))
        else:
            dropped += 1
    pool = np.array(kept)                                   # [N_valid, 297, 2]
    scores = []
    for idx, snip in enumerate(pool):
        s = signature(np.cumsum(snip, axis=0))
        score = (1.0 / (1.0 + abs(s["mean_speed"] - 8.0))) * (1.0 / (1.0 + abs(s["speed_variability"] - 3.0))) \
                * min(1.0, s["path_length"] / 100.0)
        scores.append((score, idx))
    scores.sort(reverse=True)                               # best first, ties by index desc (as the lab's tuple sort)
    primary = [i for _, i in scores[:1240]]
    overflow = [i for _, i in scores[1240:1280]] if len(pool) >= 1280 else []
    order = primary + overflow
    out = pool[order].astype(np.float32)
    n, f, _ = out.shape
    (HERE / "motion_pool.bin").write_bytes(out.tobytes(order="C"))
    (HERE / "motion_pool.json").write_text(json.dumps(dict(n=int(n), frames=int(f), n_primary=len(primary), n_overflow=len(overflow))))
    print(f"valid {len(pool)}/{len(raw)} (dropped {dropped}); wrote motion_pool.bin [{n}, {f}, 2] "
          f"({out.nbytes / 1e6:.1f} MB): primary {len(primary)}, overflow {len(overflow)}")


if __name__ == "__main__":
    main()
