#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
control_detection_task_v2_blockwise_fast_response.py - Fast response version
Windows-compatible version with early response capability

"""

import os, sys, math, random, pathlib, datetime, atexit, hashlib, json, subprocess


# Check if we're running with the correct Python interpreter
def check_and_run_with_correct_python():
    # If psychopy import fails, try to find anaconda Python
    try:
        import numpy as np
        import pandas as pd
        from psychopy import visual, event, core, data, gui
        return False  # Continue with current interpreter
    except ImportError as e:
        print(f"Missing required packages: {e}")
        print("Trying to find Python with required packages...")
        
        # Locate a PsychoPy-capable Python. Windows: probe the standard
        # Standalone-PsychoPy install dirs via env vars (works on any machine);
        # then macOS/Linux dev fallbacks. First existing path wins.
        python_paths = []
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                     os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
            if base:
                python_paths.append(os.path.join(base, "PsychoPy", "python.exe"))
        python_paths += [
            "/opt/anaconda3/bin/python",  # macOS
            "/usr/bin/python3",           # Linux
        ]

        for path in python_paths:
            if os.path.exists(path):
                print(f"Found Python at: {path}")
                result = subprocess.run([path] + sys.argv, check=False)
                sys.exit(result.returncode)
        
        print("Error: Python with required packages not found. Please install psychopy, numpy, and pandas.")
        sys.exit(1)

# Check interpreter and switch if needed
if check_and_run_with_correct_python():
    sys.exit(0)

# Import statements (will work after interpreter check)
import numpy as np
import pandas as pd
from psychopy import visual, event, core, data, gui

# ── BOT MODE: CDT_BOT=1 lets a synthetic human play the whole experiment ──
# (cdt_bot monkeypatches event.Mouse/getKeys/waitKeys; everything else is real)
BOT_MODE = os.environ.get("CDT_BOT", "0") == "1"
if BOT_MODE:
    import cdt_bot
    cdt_bot.install(event)

# ───────────────────────────────────────────────────────
#  Global variable for kinematics data
# ───────────────────────────────────────────────────────
kinematics_data = []
kinematics_csv_path = ""

# ───────────────────────────────────────────────────────
#  Auto‐save on quit
# ───────────────────────────────────────────────────────
_saved = False
def _save():
    global _saved
    if not _saved:
        if 'thisExp' in globals() and thisExp is not None:
            thisExp.saveAsWideText(csv_path)
            print("Main data auto-saved ->", csv_path)
            if kinematics_data:
                kinematics_df = pd.DataFrame(kinematics_data)
                kinematics_df.to_csv(kinematics_csv_path, index=False)
                print("Kinematics data auto-saved ->", kinematics_csv_path)
        else:
            print("Experiment not initialized - no data to save")
        _saved = True
atexit.register(_save)

# ───────────────────────────────────────────────────────
#  Participant dialog (skipped with --simulate flag)
# ───────────────────────────────────────────────────────
expName = "ControlDetection_v2_blockwise_fast_response"

expInfo = {"participant": "", "check_mode": True,
           "age": "", "gender": "", "handedness": ""}
# Bypass the dialogs via env vars so you can launch without the pop-ups (bot/testing):
#   CDT_PARTICIPANT=99 CDT_CHECK_MODE=1 python CDT_windows_blockwise_fast_response.py
# The dialog on macOS sometimes steals focus and then never regains it, which
# can also look like a "hang" on the first instruction screen.
_env_participant = os.environ.get("CDT_PARTICIPANT")
if _env_participant:
    expInfo["participant"] = _env_participant
    expInfo["check_mode"] = os.environ.get("CDT_CHECK_MODE", "1") == "1"
    print(f"[startup] Dialogs bypassed via env: participant={expInfo['participant']}, check_mode={expInfo['check_mode']}")
else:
    # Dialog 1 — participant number first (+ experimenter check_mode).
    _d1 = {"participant": "", "check_mode": False}
    dlg1 = gui.DlgFromDict(_d1, order=["participant", "check_mode"], title=expName)
    if not dlg1.OK:
        core.quit()
    expInfo["participant"] = _d1["participant"]
    expInfo["check_mode"] = _d1["check_mode"]
    # Dialog 2 — demographics (English). Lists render as dropdowns. Handedness is the
    # publication-relevant demographic for a mouse-based motor control task.
    _d2 = {"age": "", "gender": ["Female", "Male", "Other"],
           "handedness": ["Right-handed", "Left-handed", "Ambidextrous"]}
    dlg2 = gui.DlgFromDict(_d2, order=["age", "gender", "handedness"], title="Participant details")
    if not dlg2.OK:
        core.quit()
    expInfo["age"] = _d2["age"]
    expInfo["gender"] = _d2["gender"]
    expInfo["handedness"] = _d2["handedness"]
CHECK_MODE = bool(expInfo.pop("check_mode"))
# Staircase-only mode: run just the 70.7% calibration (both angles, long), print
# the converged medium props, then quit before learning/test. Set CDT_STAIRCASE_ONLY=1.
STAIRCASE_ONLY = os.environ.get("CDT_STAIRCASE_ONLY", "0") == "1"

# Fixed-prop test mode: skip calibration/learning, run a no-feedback block at
# given medium props (+ easy/hard) interleaved, to check whether the calibrated
# medium still yields ~70% without the staircase adapting. Set CDT_FIXED_TEST=1.
# Medium props default to participant 99's last good calibration (_99_23).
FIXED_TEST = os.environ.get("CDT_FIXED_TEST", "0") == "1"
FIXED_MED = {0: float(os.environ.get("CDT_MED0", "0.306")),
             90: float(os.environ.get("CDT_MED90", "0.331"))}
FIXED_N_MED = int(os.environ.get("CDT_NMED", "25"))    # medium trials PER ANGLE
FIXED_N_EASY = int(os.environ.get("CDT_NEASY", "6"))   # easy trials per angle
FIXED_N_HARD = int(os.environ.get("CDT_NHARD", "6"))   # hard trials per angle

# --- Method of Constant Stimuli (MOCS) diagnostic + QUEST+ seeding -------------
# CDT_MOCS=1: run a fixed-grid block (self/pilot), fit the psychometric curve per
# angle, write mocs_fit.json (alpha/beta/lambda) + mocs_curve.png, then quit.
# CDT_QUEST_CAL=1: per-participant calibration that reads mocs_fit.json, FIXES
# beta+lambda from it and estimates only alpha, then places easy/med/hard on the
# measured slope. See memory: measure the slope once, don't assume DELTA_LOGIT.
MOCS_MODE   = os.environ.get("CDT_MOCS", "0") == "1"
MOCS_REPS   = int(os.environ.get("CDT_MOCS_REPS", "18"))    # trials per (angle, prop) cell
MOCS_GRID   = [float(x) for x in os.environ.get(
    "CDT_MOCS_GRID", "0.06,0.12,0.20,0.30,0.42,0.56,0.72").split(",")]  # wide: floor->ceiling
MOCS_ANGLES = [0, 90]
QUEST_CAL   = os.environ.get("CDT_QUEST_CAL", "0") == "1"
QUEST_N     = int(os.environ.get("CDT_QUEST_N", "40"))     # QUEST+ trials PER ANGLE
# Accuracy targets the levels are placed at on the measured slope. Wider than the
# textbook 60/70.7/85 because the pilot curve saturates fast → easy/hard sat too
# close to medium. This spread is the knob for "obviously different" levels; the
# ceiling on it is chance (hard) and lapse-saturation (easy).
ACC_HARD = float(os.environ.get("CDT_ACC_HARD", "0.55"))
ACC_MED  = float(os.environ.get("CDT_ACC_MED",  "0.707"))
ACC_EASY = float(os.environ.get("CDT_ACC_EASY", "0.90"))
# Easy/hard as FIXED extreme props (strong anchors for the expectation manipulation)
# instead of accuracy targets. Fixed extremes are robust "obvious control / no
# control" poles for everyone (below/above every individual threshold) and give the
# vivid contrast the cue-learning needs. MEDIUM stays psychometrically calibrated.
# Set to "" to fall back to the ACC_HARD/ACC_EASY accuracy targets instead.
# NOTE: hard this low → near-chance → feedback on hard trials is near-random (by design).
_hp = os.environ.get("CDT_HARD_PROP", "0.08"); HARD_PROP = float(_hp) if _hp else None
_ep = os.environ.get("CDT_EASY_PROP", "0.60"); EASY_PROP = float(_ep) if _ep else None
_mp = os.environ.get("CDT_MED_PROP", ""); MED_PROP = float(_mp) if _mp else None  # feel-test override

# --- WP3: Rollwage-style post-decision evidence paradigm ------------------------
# CDT_WP3=1. Per angle block (order counterbalanced): 1u2d calibration (medium)
# -> Task 1 (decision + confidence) -> Task 2 (decision -> post-decision evidence
# sample -> confidence). No cues, no easy/hard — medium only. The evidence sample
# always clarifies the TRUE target (Rollwage et al. 2018, Curr Biol): same strength
# (low) or boosted (high). Correct choice -> confirmatory; wrong -> disconfirmatory.
WP3_MODE   = os.environ.get("CDT_WP3", "0") == "1"
WP3_T1_N   = int(os.environ.get("CDT_WP3_T1", "30"))       # Task-1 trials PER ANGLE
WP3_T2_N   = int(os.environ.get("CDT_WP3_T2", "60"))       # Task-2 trials PER ANGLE (half low/high)
WP3_BOOST  = float(os.environ.get("CDT_WP3_BOOST", "1.2")) # logit boost for high evidence
WP3_EV_DUR = float(os.environ.get("CDT_WP3_EVDUR", "3.0")) # evidence-sample duration (s)
# Confidence incentive (Rollwage 2018: quadratic scoring rule, both tasks, paid once at
# the end). CDT_WP3_BONUS = maximum bonus in currency units; 0 = lab mode (points only).
WP3_BONUS  = float(os.environ.get("CDT_WP3_BONUS", "0"))
# Keep the 1u2d running through Task 1 + Task 2 (default ON, CDT_WP3_TRACK=0 freezes
# the calibrated medium as in Rollwage). Guards the phase comparison against practice
# and fatigue: the evidence levels are time-ordered, so any accuracy drift would enter
# the confidence slope as if it were an evidence effect.
WP3_TRACK  = os.environ.get("CDT_WP3_TRACK", "1") == "1"
WP3_BONUS_UNIT = os.environ.get("CDT_WP3_BONUS_UNIT", "£")
# Decided design: per-block 1u2d staircase for MEDIUM only (70.7%); easy/hard are the
# fixed extreme props above. No MOCS/QUEST needed at runtime. Default ON.
PERBLOCK_CAL = os.environ.get("CDT_PERBLOCK", "1") == "1"
# CDT_FEEL=1: quick self-demo of the three difficulty levels (hard, then medium,
# then easy) at the MOCS-fit props, black shapes + brief feedback. No data logged.
FEEL_MODE  = os.environ.get("CDT_FEEL", "0") == "1"
FEEL_ANGLE = int(os.environ.get("CDT_FEEL_ANGLE", "0"))
FEEL_N     = int(os.environ.get("CDT_FEEL_N", "5"))
# CDT_TESTONLY=1: a quick self-run of the REAL test phase (medium+easy+hard mix,
# two cue colors, confidence+agency ratings, no feedback, live tracking). Skips
# calibration — medium is seeded (CDT_MED_PROP, default 0.36); easy/hard = med ± offset.
TESTONLY_MODE  = os.environ.get("CDT_TESTONLY", "0") == "1"
TESTONLY_N     = int(os.environ.get("CDT_TESTONLY_N", "40"))
TESTONLY_ANGLE = int(os.environ.get("CDT_TESTONLY_ANGLE", "0"))

# Combined mode: run a fresh calibration, then immediately the fixed-prop block at
# the just-derived medium props — same session, no stale cross-session values.
# This is the correct way to validate the 70% (avoids practice drift). CDT_CAL_THEN_FIXED=1.
CAL_THEN_FIXED = os.environ.get("CDT_CAL_THEN_FIXED", "0") == "1"
expInfo["session"] = "001"

# Feature flag: use QUEST+ training/test design
USE_QUEST_TRAINING = True
if CHECK_MODE:
    # Check mode: minimal trials to run through entire experiment quickly
    # Calibration: 6 trials per staircase (2 staircases = ~12 total)
    CHECK_CALIBRATION_TRIALS = 6
    # Learning: 2 mini-blocks per angle x 6 trials each = 12 per angle, 24 total
    LEARNING_MINIBLOCKS_PER_ANGLE = 2
    LEARNING_TRIALS_PER_MINIBLOCK = 6
    # Test: 2 mini-blocks per angle x 9 trials each = 18 per angle, 36 total
    TEST_MINIBLOCKS_PER_ANGLE = 2
    TEST_TRIALS_PER_MINIBLOCK = 9
else:
    # Full experiment settings
    # Calibration: 60 trials per staircase (2 staircases = ~120 total)
    CHECK_CALIBRATION_TRIALS = 60
    # Learning: 2 mini-blocks per angle x 30 trials each = 60 per angle, 120 total
    LEARNING_MINIBLOCKS_PER_ANGLE = 2
    LEARNING_TRIALS_PER_MINIBLOCK = 30
    # Test: 6 mini-blocks per angle x 25 trials each = 150 per angle, 300 total
    TEST_MINIBLOCKS_PER_ANGLE = 6
    TEST_TRIALS_PER_MINIBLOCK = 25

# counter‐balance cue colours (will be set per block based on angle)
# Initialize with placeholder - will be updated in block loop
low_col, high_col = None, None

# Derived constants
LEARNING_TOTAL_PER_ANGLE = LEARNING_MINIBLOCKS_PER_ANGLE * LEARNING_TRIALS_PER_MINIBLOCK
TEST_TOTAL_PER_ANGLE = TEST_MINIBLOCKS_PER_ANGLE * TEST_TRIALS_PER_MINIBLOCK
TOTAL_LEARNING_MINIBLOCKS = LEARNING_MINIBLOCKS_PER_ANGLE * 2  # both angles
TOTAL_TEST_MINIBLOCKS = TEST_MINIBLOCKS_PER_ANGLE * 2  # both angles

# Print check mode status
if CHECK_MODE:
    print("=" * 60)
    print("CHECK MODE ENABLED - Running minimal trials")
    print(f"   Calibration: {CHECK_CALIBRATION_TRIALS} trials/staircase")
    print(f"   Learning: {LEARNING_MINIBLOCKS_PER_ANGLE} mini-blocks/angle x {LEARNING_TRIALS_PER_MINIBLOCK} trials ({LEARNING_TOTAL_PER_ANGLE}/angle, {LEARNING_TOTAL_PER_ANGLE*2} total)")
    print(f"   Test: {TEST_MINIBLOCKS_PER_ANGLE} mini-blocks/angle x {TEST_TRIALS_PER_MINIBLOCK} trials ({TEST_TOTAL_PER_ANGLE}/angle, {TEST_TOTAL_PER_ANGLE*2} total)")
    print(f"   Total experiment: ~{CHECK_CALIBRATION_TRIALS*2 + LEARNING_TOTAL_PER_ANGLE*2 + TEST_TOTAL_PER_ANGLE*2} trials")
    print("=" * 60)
else:
    print("Running FULL experiment mode")
    print(f"   Calibration: {CHECK_CALIBRATION_TRIALS} trials/staircase (~{CHECK_CALIBRATION_TRIALS*2} total)")
    print(f"   Learning: {LEARNING_MINIBLOCKS_PER_ANGLE} mini-blocks/angle x {LEARNING_TRIALS_PER_MINIBLOCK} trials ({LEARNING_TOTAL_PER_ANGLE}/angle, {LEARNING_TOTAL_PER_ANGLE*2} total)")
    print(f"   Test: {TEST_MINIBLOCKS_PER_ANGLE} mini-blocks/angle x {TEST_TRIALS_PER_MINIBLOCK} trials ({TEST_TOTAL_PER_ANGLE}/angle, {TEST_TOTAL_PER_ANGLE*2} total)")
    print(f"   Total experiment: ~{CHECK_CALIBRATION_TRIALS*2 + LEARNING_TOTAL_PER_ANGLE*2 + TEST_TOTAL_PER_ANGLE*2} trials")

# Learning order will be set by counterbalancing system below
# (Placeholder - assigned after participant ID is processed)
learning_order = None

# Experiment structure (mini-block interleaved design):
# Phase 1: Calibration (both 0 deg and 90 deg interleaved, QUEST+)
# Phase 2: Learning (mini-blocks alternating angle A/B, easy+hard trials, colored cues, feedback)
# Phase 3: Test (mini-blocks alternating angle A/B, medium+easy+hard trials, colored cues, no feedback, ratings)

# ───────────────────────────────────────────────────────
#  Load motion library with cluster information
# ───────────────────────────────────────────────────────
# script lives in experiment/task/ ; Motion_Library is at metasoa/Motion_Library
# (two levels up) and data at experiment/data (one level up).
script_dir = pathlib.Path(__file__).parent
repo_root = script_dir.parent.parent           # metasoa/
LIB_NAME = repo_root / "Motion_Library" / "core_pool.npy"
FEATS_NAME = repo_root / "Motion_Library" / "core_pool_feats.npy"
LABELS_NAME = repo_root / "Motion_Library" / "core_pool_labels.npy"

motion_pool = np.load(LIB_NAME)
snippet_features = np.load(FEATS_NAME)
snippet_labels = np.load(LABELS_NAME)

SNIP_LEN = motion_pool.shape[1]
TOTAL_SNIPS = motion_pool.shape[0]
K_CLUST = 4

print(f"Loaded {TOTAL_SNIPS} snippets × {SNIP_LEN} frames from {LIB_NAME}")
print(f"Cluster distribution: {np.bincount(snippet_labels)}")

with open(repo_root / "Motion_Library" / "scaler_params.json", "r") as f:
    scp = json.load(f)
scaler_mean = np.array(scp["mean"], dtype=np.float32)
scaler_std = np.array(scp["scale"], dtype=np.float32)

with open(repo_root / "Motion_Library" / "cluster_centroids.json", "r") as f:
    CLUSTER_CENTROIDS = np.array(json.load(f), dtype=np.float32)

participant_clusters = None
seed = int(hashlib.sha256(expInfo["participant"].encode()).hexdigest(),16) & 0xFFFFFFFF
rng = np.random.default_rng(seed)

# ───────────────────────────────────────────────────────
#  Two color palette system - counterbalanced across blocks
# ───────────────────────────────────────────────────────
# Define two distinct color palettes for low/high cues across angle blocks
PALETTE_SET_1 = ("blue", "green")
PALETTE_SET_2 = ("red", "yellow")

# PROPER COUNTERBALANCING: Convert participant ID to index (0-7 for 8 conditions)
try:
    participant_num = int(expInfo["participant"])
except ValueError:
    participant_num = int(hashlib.sha256(expInfo["participant"].encode()).hexdigest(), 16) & 0xFFFF

cb_index = participant_num % 8

# Factor 1: Learning order (0 deg vs 90 deg first)
learning_order_first_angle = 0 if (cb_index & 1) == 0 else 90
learning_order = [learning_order_first_angle, 90 if learning_order_first_angle == 0 else 0]

# Factor 2: Which palette for first angle (blue/green vs red/yellow)
palette_first_is_blue_green = ((cb_index >> 1) & 1) == 0
if palette_first_is_blue_green:
    PALETTE_FOR_FIRST_ANGLE = PALETTE_SET_1
    PALETTE_FOR_SECOND_ANGLE = PALETTE_SET_2
else:
    PALETTE_FOR_FIRST_ANGLE = PALETTE_SET_2
    PALETTE_FOR_SECOND_ANGLE = PALETTE_SET_1

# Factor 3: Color-difficulty mapping within first palette
first_palette_flip = ((cb_index >> 2) & 1) == 1
if first_palette_flip:
    PALETTE_FOR_FIRST_ANGLE = (PALETTE_FOR_FIRST_ANGLE[1], PALETTE_FOR_FIRST_ANGLE[0])

# Second angle always flips to ensure variety
PALETTE_FOR_SECOND_ANGLE = (PALETTE_FOR_SECOND_ANGLE[1], PALETTE_FOR_SECOND_ANGLE[0])

# Log counterbalancing assignment
expInfo["learning_order"] = str(learning_order)
expInfo["counterbalance_index"] = cb_index
print("=" * 60)
print("COUNTERBALANCING ASSIGNMENT:")
print(f"  Participant: {expInfo['participant']} -> CB Index: {cb_index}/8")
print(f"  Learning order: {learning_order}")
print(f"  First angle ({learning_order[0]} deg): {PALETTE_FOR_FIRST_ANGLE} (low=hard, high=easy)")
print(f"  Second angle ({learning_order[1]} deg): {PALETTE_FOR_SECOND_ANGLE} (low=hard, high=easy)")
print("=" * 60)

# ───────────────────────────────────────────────────────
#  Trajectory signature function (needed for universal selection)
# ───────────────────────────────────────────────────────

def get_trajectory_signature(trajectory):
    """Key movement characteristics for matching"""
    velocities = np.diff(trajectory, axis=0)
    if len(velocities) == 0:
        return {'mean_speed':0,'speed_variability':0,'path_length':0,'net_displacement':0,'speed_percentiles':np.array([0,0,0])}
    speeds = np.linalg.norm(velocities, axis=1)
    return {
        'mean_speed': np.mean(speeds),
        'speed_variability': np.std(speeds),
        'path_length': np.sum(speeds),
        'net_displacement': np.linalg.norm(trajectory[-1] - trajectory[0]),
        'speed_percentiles': np.percentile(speeds, [25, 50, 75])
    }

# ───────────────────────────────────────────────────────
#  Universal trajectory set (same for all participants)
# ───────────────────────────────────────────────────────

def select_universal_trajectory_set():
    """Pre-select trajectories for all participants with deterministic ranking.
    Produces two sets:
      - Primary: best 1,240 trajectories used for all standard trials
      - Overflow: next-best 40 trajectories used only if extra trials are needed
    """
    global valid_snippet_indices, universal_trajectory_set_primary, universal_trajectory_set_overflow, universal_trajectory_set

    total_valid = len(valid_snippet_indices)
    if total_valid < 1240:
        print(f"Warning: Only {total_valid} valid trajectories, fewer than 1,240 required for primary set")
        universal_trajectory_set_primary = valid_snippet_indices.copy()
        universal_trajectory_set_overflow = []
        universal_trajectory_set = universal_trajectory_set_primary.copy()
        return universal_trajectory_set.copy()

    # Use a fixed seed for deterministic selection across all participants (kept for clarity)
    selection_rng = np.random.default_rng(42)

    print("Selecting universal trajectory sets (Primary 1,240 + Overflow 40)...")

    # Score all valid trajectories by quality
    trajectory_scores = []
    for idx in valid_snippet_indices:
        trajectory = motion_pool[idx]
        traj_cumsum = np.cumsum(trajectory, axis=0)
        sig = get_trajectory_signature(traj_cumsum)

        # Quality score: prefer moderate speeds, good variability, reasonable length
        speed_score = 1.0 / (1.0 + abs(sig['mean_speed'] - 8.0))
        variability_score = 1.0 / (1.0 + abs(sig['speed_variability'] - 3.0))
        length_score = min(1.0, sig['path_length'] / 100.0)

        overall_score = speed_score * variability_score * length_score
        trajectory_scores.append((overall_score, idx))

    # Sort by quality score (best first) and take primary + overflow slices
    trajectory_scores.sort(reverse=True)
    primary_indices = [idx for score, idx in trajectory_scores[:1240]]
    overflow_indices = [idx for score, idx in trajectory_scores[1240:1280]] if total_valid >= 1280 else []

    universal_trajectory_set_primary = primary_indices
    universal_trajectory_set_overflow = overflow_indices
    universal_trajectory_set = primary_indices + overflow_indices

    print(f"Selected Primary: {len(primary_indices)} (best={trajectory_scores[0][0]:.3f})")
    if overflow_indices:
        print(f"Selected Overflow: {len(overflow_indices)} (worst_primary={trajectory_scores[1239][0]:.3f}, best_overflow={trajectory_scores[1240][0]:.3f} if available)")
    else:
        print("No overflow set available (valid < 1,280)")

    return universal_trajectory_set.copy()

# Will be initialized after preprocessing
universal_trajectory_set_primary = []
universal_trajectory_set_overflow = []
universal_trajectory_set = []
used_trajectory_indices = set()  # Track which ones from universal set have been used
trajectory_usage_stats = {"used_count": 0, "total_needed": 1600}  # For monitoring

# Global trial counter (persists across all phases for consistent trial numbering)
global_trial_counter = 0

def wait_keys(keys=None):
    """Wait for a keypress, reliably. The 'press space several times' bug was macOS
    handing focus to the window a moment AFTER activate(), so the first press landed
    elsewhere and was lost while waitKeys kept waiting. Fix: activate, let focus
    settle, flush, THEN waitKeys. Keeps event.waitKeys (the bot patches it)."""
    try:
        win.winHandle.activate()
    except Exception:
        pass
    core.wait(0.15)                         # let macOS deliver focus before we listen
    event.clearEvents(eventType='keyboard')
    return event.waitKeys(keyList=keys)

def show_break_screen(trials_completed, total_trials_in_block, block_name):
    """Show a simple break info screen (no countdown, just press SPACE to continue)."""
    
    # Create break message
    break_msg = visual.TextStim(
        win=win,
        text=f"""Short Break

You have completed {trials_completed} of {total_trials_in_block} trials in {block_name}.

Take a moment to rest if needed.

Press SPACE when you are ready to continue.""",
        pos=(0, 0),
        color='white',
        height=28,
        wrapWidth=900
    )
    
    break_msg.draw()
    win.flip()
    wait_keys(['space', 'escape'])

def show_phase_transition(completed_block, next_block_info, rest_duration=30):
    """
    Show a rest screen between phases with countdown timer.
    
    Args:
        completed_block: The block number just completed (1-5)
        next_block_info: Brief neutral description of what comes next
        rest_duration: Duration of mandatory rest in seconds (default 30)
    """
    # Create transition message
    transition_msg = visual.TextStim(
        win=win,
        text="",
        pos=(0, 100),
        color='white',
        height=30,
        wrapWidth=800,
        alignText='center'
    )
    
    # Create countdown text. BLACK (not a cue colour) — yellow/red/green/blue are all
    # cue colours and would confound the expectation manipulation during the break.
    countdown_text = visual.TextStim(
        win=win,
        text='',
        pos=(0, -50),
        color='black',
        height=80
    )
    
    # Create "please wait" text
    wait_text = visual.TextStim(
        win=win,
        text='Please rest. The experiment will continue shortly.',
        pos=(0, -150),
        color='gray',
        height=20
    )
    
    # Countdown phase
    rest_clock = core.Clock()
    while rest_clock.getTime() < rest_duration:
        remaining_time = rest_duration - int(rest_clock.getTime())
        
        transition_msg.text = f"""Block {completed_block} Complete

{next_block_info}"""
        
        countdown_text.text = str(remaining_time)
        
        transition_msg.draw()
        countdown_text.draw()
        wait_text.draw()
        win.flip()
        
        # Check for escape during rest
        keys = event.getKeys(['escape'])
        if keys and 'escape' in keys:
            _save()
            core.quit()
        
        core.wait(0.1)
    
    # After countdown, show ready message
    ready_msg = visual.TextStim(
        win=win,
        text=f"""Block {completed_block} Complete

{next_block_info}

Press SPACE when you are ready to continue.""",
        pos=(0, 0),
        color='white',
        height=30,
        wrapWidth=800,
        alignText='center'
    )
    
    ready_msg.draw()
    win.flip()
    wait_keys(['space', 'escape'])

# ───────────────────────────────────────────────────────
#  Trajectory Quality Control and Preprocessing
# ───────────────────────────────────────────────────────

def analyze_trajectory_quality(trajectory):
    velocities = np.diff(trajectory, axis=0)
    speeds = np.linalg.norm(velocities, axis=1)
    mean_speed = np.mean(speeds)
    std_speed = np.std(speeds)
    max_speed = np.max(speeds)
    min_speed = np.min(speeds)
    zero_movement_ratio = np.sum(speeds < 0.5) / len(speeds)
    high_jitter_ratio = np.sum(speeds > mean_speed + 3*std_speed) / len(speeds)
    if len(velocities) > 1:
        unit_velocities = velocities / (sps := (speeds.reshape(-1, 1) + 1e-9))
        angle_changes = np.arccos(np.clip(np.sum(unit_velocities[:-1] * unit_velocities[1:], axis=1), -1, 1))
        mean_angle_change = np.mean(angle_changes)
        jerkiness = np.std(angle_changes)
    else:
        mean_angle_change = 0
        jerkiness = 0
    return {
        'mean_speed': mean_speed,
        'std_speed': std_speed,
        'zero_movement_ratio': zero_movement_ratio,
        'high_jitter_ratio': high_jitter_ratio,
        'mean_angle_change': mean_angle_change,
        'jerkiness': jerkiness,
        'speed_range': max_speed - min_speed
    }

def is_trajectory_valid(trajectory, min_speed=1.0, max_zero_ratio=0.3, max_jitter_ratio=0.1, max_jerkiness=1.5):
    quality = analyze_trajectory_quality(trajectory)
    if quality['mean_speed'] < min_speed:
        return False, "mean_speed_too_low"
    if quality['zero_movement_ratio'] > max_zero_ratio:
        return False, "too_much_zero_movement"
    if quality['high_jitter_ratio'] > max_jitter_ratio:
        return False, "too_much_jitter"
    if quality['jerkiness'] > max_jerkiness:
        return False, "too_jerky"
    return True, "valid"

def normalize_trajectory(trajectory, target_speed_range=(3.0, 12.0), smooth_factor=0.45):
	if len(trajectory) < 2:
		return trajectory
	velocities = np.diff(trajectory, axis=0)
	speeds = np.linalg.norm(velocities, axis=1)
	current_mean_speed = np.mean(speeds)
	if current_mean_speed > 0:
		target_mean_speed = np.mean(target_speed_range)
		speed_scale = target_mean_speed / current_mean_speed
		velocities = velocities * speed_scale
	smoothed_velocities = velocities.copy()
	for i in range(1, len(velocities)):
		smoothed_velocities[i] = smooth_factor * smoothed_velocities[i-1] + (1 - smooth_factor) * velocities[i]
	normalized_trajectory = [trajectory[0]]
	for vel in smoothed_velocities:
		next_point = normalized_trajectory[-1] + vel
		normalized_trajectory.append(next_point)
	return np.array(normalized_trajectory)

def preprocess_motion_pool():
    """Preprocess motion pool to ensure quality and consistency"""
    global motion_pool, snippet_features, snippet_labels
    print("Preprocessing motion pool for quality control...")
    initial_count = len(motion_pool)
    processed_snippets = []
    processed_features = []
    processed_labels = []
    for i, snippet in enumerate(motion_pool):
        trajectory = np.cumsum(snippet, axis=0)
        is_valid, reason = is_trajectory_valid(trajectory)
        if is_valid:
            normalized_trajectory = normalize_trajectory(trajectory)
            velocities = np.diff(normalized_trajectory, axis=0)
            processed_snippets.append(velocities)
            processed_features.append(snippet_features[i])
            processed_labels.append(snippet_labels[i])
        else:
            print(f"Removed snippet {i}: {reason}")
    motion_pool = np.array(processed_snippets)
    snippet_features = np.array(processed_features)
    snippet_labels = np.array(processed_labels)
    global SNIP_LEN
    SNIP_LEN = motion_pool.shape[1] if len(motion_pool) > 0 else 0
    print(f"Motion pool preprocessed: kept {len(processed_snippets)}/{initial_count} snippets")
    return list(range(len(processed_snippets)))

valid_snippet_indices = preprocess_motion_pool()

# Now initialize the universal trajectory sets after preprocessing
universal_trajectory_set = select_universal_trajectory_set()
print(
    f"Universal trajectory sets initialized: Primary={len(universal_trajectory_set_primary)}; "
    f"Overflow={len(universal_trajectory_set_overflow)}; Total={len(universal_trajectory_set)}"
)

def find_matched_trajectory_pair():
    """Find two UNUSED trajectories with similar movement characteristics.
    Prefer primary set; only use overflow if necessary.
    """
    global universal_trajectory_set, universal_trajectory_set_primary, universal_trajectory_set_overflow
    global used_trajectory_indices, trajectory_usage_stats
    
    # Safety check: ensure universal sets are initialized
    if not universal_trajectory_set:
        universal_trajectory_set = valid_snippet_indices.copy()
        universal_trajectory_set_primary = universal_trajectory_set.copy()
        universal_trajectory_set_overflow = []
    
    # Available (unused) trajectories by priority
    available_primary = [idx for idx in universal_trajectory_set_primary if idx not in used_trajectory_indices]
    available_overflow = [idx for idx in universal_trajectory_set_overflow if idx not in used_trajectory_indices]
    available_indices = available_primary if len(available_primary) >= 2 else (available_primary + available_overflow)
    
    # Check if we have enough unused trajectories
    if len(available_indices) < 2:
        pass  # Low number of unused trajectories
        # Emergency fallback: use any available trajectories (even if used before)
        if len(available_indices) == 1:
            # Can't use same trajectory - need to find a different one
            target_idx = available_indices[0]
            # Find different trajectory from universal set (even if used before)
            different_options = [idx for idx in universal_trajectory_set if idx != target_idx]
            if different_options:
                distractor_idx = rng.choice(different_options)
                return target_idx, distractor_idx
            else:
                # Absolute emergency - use different random trajectory
                return None, None  # Will trigger fallback
        elif len(available_indices) == 0:
            print("No unused trajectories! Using random valid trajectories.")
            return None, None  # Will trigger fallback in calling function
    
    # Sample from unused trajectories for matching (prefer primary pool)
    sample_pool = available_primary if len(available_primary) >= 2 else available_indices
    sample_size = min(100, len(sample_pool))
    candidate_indices = rng.choice(sample_pool, size=sample_size, replace=False)
    
    # Get signatures for all candidates
    signatures = []
    for idx in candidate_indices:
        trajectory = motion_pool[idx]
        sig = get_trajectory_signature(np.cumsum(trajectory, axis=0))
        signatures.append((idx, sig))
    
    # Find the best matching pair among unused trajectories
    best_score = float('inf')
    best_pair = (None, None)
    
    for i in range(len(signatures)):
        for j in range(i + 1, len(signatures)):
            idx1, sig1 = signatures[i]
            idx2, sig2 = signatures[j]
            
            # Calculate similarity score (lower is better)
            speed_diff = abs(sig1['mean_speed'] - sig2['mean_speed'])
            var_diff = abs(sig1['speed_variability'] - sig2['speed_variability'])
            length_diff = abs(sig1['path_length'] - sig2['path_length']) / max(sig1['path_length'], sig2['path_length'])
            
            # Combined similarity score
            similarity_score = speed_diff + var_diff + length_diff * 10
            
            if similarity_score < best_score:
                best_score = similarity_score
                best_pair = (idx1, idx2)
    
    # Mark trajectories as used if we found a valid pair
    if best_pair[0] is not None and best_pair[1] is not None:
        used_trajectory_indices.add(best_pair[0])
        used_trajectory_indices.add(best_pair[1])
        trajectory_usage_stats["used_count"] += 2
        
        # Progress monitoring
        remaining = trajectory_usage_stats["total_needed"] - trajectory_usage_stats["used_count"]
        unused_count = len([idx for idx in universal_trajectory_set if idx not in used_trajectory_indices])
        
        if trajectory_usage_stats["used_count"] % 100 == 0:  # Print every 50 trials
            pass  # Trajectory usage tracked silently
    
    return best_pair

def apply_consistent_smoothing(trajectory1, trajectory2):
    """Apply consistent smoothing to both trajectories"""
    def smooth_trajectory(traj, window_size=3):
        if len(traj) < window_size:
            return traj
        smoothed = traj.copy()
        for i in range(len(traj)):
            start = max(0, i - window_size // 2)
            end = min(len(traj), i + window_size // 2 + 1)
            smoothed[i] = np.mean(traj[start:end], axis=0)
        return smoothed
    pos1 = np.cumsum(trajectory1, axis=0)
    pos2 = np.cumsum(trajectory2, axis=0)
    smooth_pos1 = smooth_trajectory(pos1)
    smooth_pos2 = smooth_trajectory(pos2)
    vel1 = np.diff(smooth_pos1, axis=0)
    vel2 = np.diff(smooth_pos2, axis=0)
    return vel1, vel2

def sample_from_all_trajectories(n_samples=20):
    if len(valid_snippet_indices) >= n_samples:
        return rng.choice(valid_snippet_indices, size=n_samples, replace=False)
    else:
        print(f"Warning: Only {len(valid_snippet_indices)} trajectories available")
        return valid_snippet_indices.copy()

# ───────────────────────────────────────────────────────
#  Constants and Parameters
# ───────────────────────────────────────────────────────
OFFSET_X = 300
LOWPASS = 0.5
START_BOOST_EASY = 0.05
START_BOOST_EASY_TRIALS = 6

# Continuous-movement tracking: detects the "flick once, freeze, watch which shape
# responds" probing strategy. Per-trial fraction of frames with low-passed mouse
# speed below the floor is logged (low_move_ratio) so analysis can exclude/flag
# low-movement trials. No on-screen nudge (it distracted from the moving shapes).
# ponytail: log-only; add auto-requeue of low-movement trials if post-hoc exclusion proves insufficient.
MIN_SPEED_FLOOR = 2.0  # in mag_m_lp units (MAX_SPEED=20); tune from pilot kinematics

# Free-exploration trial at full control before each angle block (see
# run_block_exploration). Long enough to produce several movement bouts.
EXPLORE_DUR = float(os.environ.get("CDT_EXPLORE_DUR", "10.0"))

# ───────────────────────────────────────────────────────
#  Paths & ExperimentHandler
# ───────────────────────────────────────────────────────
# real participant data lives in experiment/data/real/raw (script is in task/).
# The bot (CDT_BOT=1) writes here too; sort bot runs into data/simulated afterwards.
root = script_dir.parent / "data" / "real"
subjects_dir = root / "raw"
subjects_dir.mkdir(parents=True, exist_ok=True)

participant_id = expInfo['participant']
base_filename = f"CDT_v2_blockwise_fast_response_{participant_id}"
csv_path = subjects_dir / f"{base_filename}.csv"
kinematics_csv_path = subjects_dir / f"{base_filename}_kinematics.csv"

i = 1
while csv_path.exists():
    new_filename = f"CDT_v2_blockwise_fast_response_{participant_id}_{i}"
    csv_path = subjects_dir / f"{new_filename}.csv"
    kinematics_csv_path = subjects_dir / f"{new_filename}_kinematics.csv"
    i += 1

thisExp = data.ExperimentHandler(
    name=expName, extraInfo=expInfo,
    savePickle=False, saveWideText=False,
    dataFileName=str(root / base_filename)
)

# ───────────────────────────────────────────────────────
#  Window & stimuli
# ───────────────────────────────────────────────────────
# Fullscreen by default (precise timing). On macOS a fullscreen window launched
# from Terminal/IDE sometimes does not receive keyboard focus — keys then go to
# whatever app was frontmost, which looks like the experiment "hangs" on the
# first instruction screen; win.winHandle.activate() below mitigates this, and if
# it still misbehaves click the window once to focus it. Set env CDT_WINDOWED=1
# to fall back to a windowed run for debugging.
import os
WINDOWED_MODE = os.environ.get("CDT_WINDOWED", "0") == "1"

# checkTiming=False is essential on macOS: the default frame-rate measurement at
# window creation renders a splash that often hangs a fullscreen window as an
# unresponsive BLACK screen. Skipping it fixes the "frozen black screen" launch.
if WINDOWED_MODE:
    # "Presentation" window: fills the WHOLE screen at native resolution but is a
    # non-exclusive window (fullscr=False), so a background-launched process (e.g.
    # started by Claude Code) does NOT hit the macOS exclusive-fullscreen freeze —
    # exclusive fullscreen needs foreground-app status a detached process can't get.
    # We then drop the title bar so it looks like true fullscreen to the participant.
    try:
        import pyglet
        _s = pyglet.canvas.get_display().get_default_screen()
        _wsize = (_s.width, _s.height)
    except Exception:
        _wsize = (1920, 1080)
    win = visual.Window(_wsize, fullscr=False, pos=(0, 0), color=[0.5]*3, units="pix",
                        allowGUI=True, checkTiming=False)
    for _ in range(3):
        win.flip()
else:
    # Match the display's NATIVE resolution — a mismatched fullscreen size is the
    # other common cause of a black screen on macOS.
    try:
        import pyglet
        _scr = pyglet.canvas.get_display().get_default_screen()
        _size = (_scr.width, _scr.height)
    except Exception:
        _size = (1920, 1080)
    # allowGUI=True as in the long-working original — allowGUI=False was blocking
    # keyboard focus on macOS (window rendered but received no keys -> 0 trials).
    win = visual.Window(_size, fullscr=True, color=[0.5]*3, units="pix",
                        allowGUI=True, checkTiming=False)

# Force the window to the foreground and paint grey a few times so macOS
# composites it (otherwise the first user-facing frame can stay black).
try:
    win.winHandle.activate()
except Exception:
    pass
for _ in range(3):
    win.flip()

# Keep the mouse visible on the instruction screens so the user can click the
# window to give it focus. It is hidden again at the start of the first trial
# (see run_trial()).
win.setMouseVisible(True)
# Two IDENTICAL circles, left and right. The response is purely spatial (a = left,
# s = right); the object is no longer distinguished by form, so shape can't act as an
# incidental cue. The internal names square/dot are kept as position tags only — both
# render as the same circle; data logs LEFT/RIGHT sides (see run_trial's true_side/resp_side).
square = visual.Circle(win, 20, fillColor="black", lineColor="black")
dot = visual.Circle(win, 20, fillColor="black", lineColor="black")
# Two opposing boxes (at ±OFFSET_X): each shape is confined to its own box so the
# two can be compared side by side without overlapping. Mouse cursor stays hidden.
BOX_HW, BOX_HH = 200, 250
left_box = visual.Rect(win, BOX_HW * 2, BOX_HH * 2, pos=(-OFFSET_X, 0),
                       fillColor=None, lineColor="white", lineWidth=2)
right_box = visual.Rect(win, BOX_HW * 2, BOX_HH * 2, pos=(OFFSET_X, 0),
                        fillColor=None, lineColor="white", lineWidth=2)
fix = visual.TextStim(win, "+", color="white", height=60)
msg = visual.TextStim(win, "", color="white", height=26, wrapWidth=1000)
# WP3 post-decision evidence markers. Rollwage's evidence appeared passively and
# needed no marker; ours re-uses the full active trial (fixation, wait for movement,
# motion), so unmarked it reads as a NEW trial. Wording matters: the sample draws
# FRESH trajectories and the participant moves anew — it is a second independent
# sample, NOT a recording being replayed. Constant are only the two circles, their
# sides, and which one is truly controlled.
evidence_cue = visual.TextStim(win, "EXTRA EVIDENCE\nsame two circles — a second look",
                               color="white", height=34, wrapWidth=1000, bold=True)
evidence_label = visual.TextStim(win, "EXTRA EVIDENCE  —  same circles, same sides  ·  keep moving, no response",
                                 color="white", height=22, pos=(0, 330), wrapWidth=1200)
feedbackTxt = visual.TextStim(win, "", color="black", height=80)

confine = lambda p, l=250: p if (r := math.hypot(*p)) <= l else (p[0]*l/r, p[1]*l/r)
# Clamp a point to the box centred at (cx, 0).
confine_box = lambda p, cx: (min(max(p[0], cx - BOX_HW), cx + BOX_HW),
                             min(max(p[1], -BOX_HH), BOX_HH))
rotate = lambda vx, vy, a: (
    vx * math.cos(math.radians(a)) - vy * math.sin(math.radians(a)),
    vx * math.sin(math.radians(a)) + vy * math.cos(math.radians(a))
)

# Demo trial function removed as requested

# ───────────────────────────────────────────────────────
#  Basic condition labels
# ───────────────────────────────────────────────────────

EXPECT = ["low", "high"]

# Difficulty levels in prop_used space:
#   medium = per-angle staircase threshold (~70.7% correct), found adaptively;
#   easy/hard = medium SYMMETRICALLY offset in logit space (easy = +Δ, hard = −Δ).
# Why logit-offset and not fixed props: the expectation manipulation needs medium
# to sit perceptually BETWEEN easy and hard so both cues are credible priors that
# can bias the (objectively constant) medium ratings symmetrically. Fixed 0.10/0.85
# left medium hugging hard (far from easy) → asymmetric bias. Offsetting around the
# measured threshold centres medium and depends only on the well-estimated 70.7%
# point — NOT on the psychometric slope (which a 1u2d can't estimate). The realised
# easy/hard accuracies are not fixed numbers; VERIFY them post-hoc from learning data
# and tune Δ until easy/hard feel clearly distinct from medium.
DELTA_LOGIT = float(os.environ.get("CDT_DELTA_LOGIT", "1.2"))  # easy/hard spacing around medium, logit units
FIXED_EASY_PROP = 0.85  # legacy fallback only (used if a threshold is unavailable)
FIXED_HARD_PROP = 0.10

# Legacy offset, no longer used (easy/hard are now fixed values above).
EASY_HARD_PROP_OFFSET = 0.15

# Target performance level that the staircase converges on (1u2d → 70.7%)
MEDIUM_TARGET_PCORR = 0.707

# Control-direction noise: legacy, unused (kept for backward-compat references).
CONTROL_DIR_NOISE_DEG = 0.0

# Legacy constant retained for any downstream references; no longer used for
# difficulty derivation now that easy/hard are defined by a fixed prop offset.
LEARNING_LOGIT_SEPARATION = 1.2

# Store per-angle learning levels (hard, easy) to reuse in test phase
learning_levels_by_angle = {}
# Store per-angle full difficulty levels (hard, medium, easy) computed from QUEST+
difficulty_levels_by_angle = {}

# ───────────────────────────────────────────────────────
#  Trial function with fast response capability
# ───────────────────────────────────────────────────────
def run_trial(
    trial_num, phase, angle_bias, expect_level, mode, catch_type="", target_shape=None, block_num=1,
    prop_override=None, cue_dur_range=None, motion_dur=None, response_window=None,
    cue_color_override=None, accept_response=True, left_shape=None, applied_angle_override=None
):
    # left_shape pins which side each object occupies. Normally random per trial,
    # but WP3's evidence sample MUST inherit the decision trial's layout: both
    # objects are identical black circles, so the participant can only identify
    # them by side. Re-rolling the side would put the confirming evidence on the
    # opposite side from a correct answer in ~50% of trials, which reads as
    # disconfirmation and inverts the core measure.
    if catch_type == "full":
        prop = 1.0
    elif prop_override is not None:
        prop = float(np.clip(prop_override, 0.02, 0.90))
    elif mode == "true":
        # Legacy path removed; treat as medium if no override is provided
        prop = 0.40
    else:
        prop = 0.40

    # Use black for calibration phase, colored cues for fixed practice phase.
    # cue_color_override forces a colour (e.g. truthful difficulty label in validation).
    if cue_color_override is not None:
        cue = cue_color_override
    elif phase == "calibration":
        cue = "black"
    else:
        cue = low_col if expect_level == "low" else high_col
    fix.color = cue; square.fillColor = square.lineColor = cue; dot.fillColor = dot.lineColor = cue
    is_evidence = (phase == "wp3_evidence")   # marked throughout so it never reads as a new trial

    (evidence_cue if is_evidence else fix).draw(); win.flip()
    if cue_dur_range is not None:
        core.wait(float(rng.uniform(cue_dur_range[0], cue_dur_range[1])))
    else:
        core.wait(1.0)

    if left_shape is None:
        left_shape = random.choice(['square', 'dot'])
    if left_shape == 'square':
        square.pos = (-OFFSET_X, 0); dot.pos = (OFFSET_X, 0)
        square_cx, dot_cx = -OFFSET_X, OFFSET_X
    else:
        square.pos = (OFFSET_X, 0); dot.pos = (-OFFSET_X, 0)
        square_cx, dot_cx = OFFSET_X, -OFFSET_X
    left_box.draw(); right_box.draw(); square.draw(); dot.draw(); (is_evidence and evidence_label.draw()); win.flip()
    
    mouse = cdt_bot.BotMouse() if BOT_MODE else event.Mouse(win=win, visible=False)
    mouse.setPos((0, 0))
    last = mouse.getPos()
    while True:
        left_box.draw(); right_box.draw(); square.draw(); dot.draw(); (is_evidence and evidence_label.draw()); win.flip()
        x, y = mouse.getPos()
        if math.hypot(x - last[0], y - last[1]) > 0: break
        if event.getKeys(["escape"]): _save(); core.quit()

    target = target_shape if target_shape is not None else random.choice(["square", "dot"])
    if BOT_MODE:
        cdt_bot.BOT.plan_trial(phase=phase, prop=prop, angle=angle_bias,
                               expect_level=expect_level, target=target, left_shape=left_shape)
    target_snippet_idx, distractor_snippet_idx = find_matched_trajectory_pair()
    if target_snippet_idx is None or distractor_snippet_idx is None:
        pass  # Trajectory matching failed, using fallback
        # Fallback: try to get unused trajectories, preferring primary then overflow
        available_primary = [idx for idx in universal_trajectory_set_primary if idx not in used_trajectory_indices]
        available_overflow = [idx for idx in universal_trajectory_set_overflow if idx not in used_trajectory_indices]
        available_indices = available_primary if len(available_primary) >= 2 else (available_primary + available_overflow)
        if len(available_indices) >= 2:
            selected = rng.choice(available_indices, size=2, replace=False)
            target_snippet_idx, distractor_snippet_idx = selected[0], selected[1]
            # Mark as used
            used_trajectory_indices.add(target_snippet_idx)
            used_trajectory_indices.add(distractor_snippet_idx)
            trajectory_usage_stats["used_count"] += 2
        elif len(available_indices) == 1:
            # Can't use same trajectory for both - use available + one random different from universal set
            target_snippet_idx = available_indices[0]
            # Find a different trajectory from primary then overflow
            combined_sets = universal_trajectory_set_primary + universal_trajectory_set_overflow
            different_options = [idx for idx in combined_sets if idx != target_snippet_idx]
            if different_options:
                distractor_snippet_idx = rng.choice(different_options)
            else:
                # Absolute emergency: use different random trajectory
                distractor_snippet_idx = rng.choice([idx for idx in range(len(motion_pool)) if idx != target_snippet_idx])
            used_trajectory_indices.add(target_snippet_idx)
            used_trajectory_indices.add(distractor_snippet_idx)
            trajectory_usage_stats["used_count"] += 2
        else:
            pass  # No unused trajectories in universal set
            combined_sets = universal_trajectory_set_primary + universal_trajectory_set_overflow if (universal_trajectory_set_primary or universal_trajectory_set_overflow) else universal_trajectory_set
            if len(combined_sets) >= 2:
                selected = rng.choice(combined_sets, size=2, replace=False)
                target_snippet_idx, distractor_snippet_idx = selected[0], selected[1]
            else:
                pass  # Insufficient trajectories in universal set
                # Ensure different trajectories even in emergency
                available_range = list(range(len(motion_pool)))
                selected = rng.choice(available_range, size=2, replace=False)
                target_snippet_idx, distractor_snippet_idx = selected[0], selected[1]
    target_snippet = motion_pool[target_snippet_idx]
    distractor_snippet = motion_pool[distractor_snippet_idx]
    target_snippet, distractor_snippet = apply_consistent_smoothing(target_snippet, distractor_snippet)

    trial_kinematics = []
    clk = core.Clock(); frame = 0
    vt = vd = np.zeros(2, np.float32)
    mag_m_lp = 0.0
    prev_d = np.zeros(2, np.float32)
    low_move_frames = 0
    
    # Variables for early response capability
    resp_shape = None
    rt_choice = np.nan
    early_response = False

    # All existing callers pass motion_dur=5.0 explicitly; WP3's evidence sample is shorter.
    total_motion_duration = float(motion_dur) if motion_dur else 5.0
    response_start_time = core.getTime()
    
    # Clear any existing events
    event.clearEvents(eventType='keyboard')
    
    # Determine applied rotation angle: randomize ±90 deg when angle_bias == 90.
    # The WP3 evidence sample overrides this with the decision trial's sign —
    # a flipped rotation would reverse the mapping the participant just learned.
    applied_angle = angle_bias
    if applied_angle_override is not None:
        applied_angle = int(applied_angle_override)
    elif angle_bias == 90:
        applied_angle = int(rng.choice([90, -90]))
    
    rt_frame = None

    while clk.getTime() < total_motion_duration and resp_shape is None:
        x, y = mouse.getPos()
        dx, dy = x - last[0], y - last[1]
        last = (x, y)
        dx, dy = rotate(dx, dy, applied_angle)
        # ── Wen-style stimuli: an INDEPENDENT trajectory per shape ───────────
        # Distractor = an independent pre-recorded trajectory (its random drift is
        # the protective noise that keeps every cue staircase-able and avoids the
        # shared-B exploits). Target = your movement blended with ITS OWN trajectory,
        # weighted by `prop`. The 90° bias is already baked into (dx,dy). Both move
        # at the participant's low-passed speed → no temporal cue. The participant
        # "intervenes" in the target's direction via the mouse.
        t_dx, t_dy = target_snippet[frame % len(target_snippet)]
        d_dx, d_dy = distractor_snippet[frame % len(distractor_snippet)]
        frame += 1
        mag_m = math.hypot(dx, dy)
        MAX_SPEED = 20.0
        if mag_m > MAX_SPEED:
            dx, dy = dx * MAX_SPEED / mag_m, dy * MAX_SPEED / mag_m
            mag_m = MAX_SPEED
        if frame == 1: mag_m_lp = mag_m
        else: mag_m_lp = 0.5 * mag_m_lp + 0.5 * mag_m
        below_floor = frame > 1 and mag_m_lp < MIN_SPEED_FLOOR
        if below_floor: low_move_frames += 1
        # each trajectory's direction, scaled to the participant's speed
        mt = math.hypot(t_dx, t_dy)
        t_dx, t_dy = (t_dx / mt * mag_m_lp, t_dy / mt * mag_m_lp) if mt > 0 else (0.0, 0.0)
        md = math.hypot(d_dx, d_dy)
        d_dx, d_dy = (d_dx / md * mag_m_lp, d_dy / md * mag_m_lp) if md > 0 else (0.0, 0.0)
        # target = prop*mouse + (1-prop)*own trajectory; distractor = independent
        tdx = prop * dx + (1 - prop) * t_dx
        tdy = prop * dy + (1 - prop) * t_dy
        ddx, ddy = d_dx, d_dy
        vt = LOWPASS * vt + (1 - LOWPASS) * np.array([tdx, tdy])
        vd = LOWPASS * vd + (1 - LOWPASS) * np.array([ddx, ddy])

        # --- EVIDENCE (momentary, displayed velocities) ---
        vm = np.array([dx, dy], dtype=float)
        mouse_speed = np.linalg.norm(vm) + 1e-9

        # use on-screen (mixed + low-pass) velocities for target and distractor
        vt_disp = np.array(vt, dtype=float)     # displayed target velocity this frame
        vd_disp = np.array(vd, dtype=float)     # displayed distractor velocity this frame

        ut = vt_disp / (np.linalg.norm(vt_disp) + 1e-9)
        ud = vd_disp / (np.linalg.norm(vd_disp) + 1e-9)

        cos_T = np.dot(vm, ut) / mouse_speed
        cos_D = np.dot(vm, ud) / mouse_speed

        evidence = (cos_T - cos_D) * (mouse_speed - 1e-9)  # identical scale as before

        # Equalize shape speed: both shapes move at the participant's (low-passed)
        # speed, so only DIRECTION carries the control signal. Removes the "pick the
        # shape that moves least" cue — the target's blended magnitude was otherwise
        # smaller than the distractor's (vector cancellation), leaking the answer.
        nt = float(np.linalg.norm(vt)); nd = float(np.linalg.norm(vd))
        if nt > 1e-9: vt = vt / nt * mag_m_lp
        if nd > 1e-9: vd = vd / nd * mag_m_lp

        sq_v, dt_v = (vt, vd) if target == "square" else (vd, vt)
        square.pos = confine_box(tuple(square.pos + sq_v), square_cx)
        dot.pos = confine_box(tuple(dot.pos + dt_v), dot_cx)

        trial_kinematics.append({
            'timestamp': clk.getTime(), 'frame': frame, 'mouse_x': x, 'mouse_y': y,
            'square_x': square.pos[0], 'square_y': square.pos[1], 'dot_x': dot.pos[0], 'dot_y': dot.pos[1],
            'evidence': evidence
        })
        
        # Check for early response during motion (WP3 evidence sample: escape only)
        keys = event.getKeys(['a', 's', 'escape'] if accept_response else ['escape'], timeStamped=True)
        if keys:
            key, key_time = keys[0]
            if key == "escape":
                _save(); core.quit()
            elif key == "a":   # 'a' = I think the target is on the LEFT
                resp_shape = left_shape
                rt_choice = key_time - response_start_time
                rt_frame = frame
                early_response = True
            elif key == "s":   # 's' = I think the target is on the RIGHT
                resp_shape = "dot" if left_shape == "square" else "square"
                rt_choice = key_time - response_start_time
                rt_frame = frame
                early_response = True

        left_box.draw(); right_box.draw(); square.draw(); dot.draw(); (is_evidence and evidence_label.draw()); win.flip()
    
    low_move_ratio = low_move_frames / max(frame - 1, 1)

    # If no response during motion, mark timeout and skip remaining screens.
    # A WP3 evidence sample (accept_response=False) ends here by design: no
    # timeout message, no ratings — kinematics still logged below.
    if resp_shape is None:
        if accept_response:
            msg.text = "Too slow!\n\nPlease respond faster next time."
            msg.draw(); win.flip(); core.wait(2.0)
            resp_shape = "timeout"
        else:
            resp_shape = "evidence"
        correct = np.nan
        # Log minimal kinematics metadata for timeout trial
        for frame_data in trial_kinematics:
            frame_data.update({
                'participant': expInfo['participant'], 'session': expInfo['session'],
                'trial_num': trial_num, 'phase': phase, 'angle_bias': angle_bias,
                'applied_angle_bias': applied_angle,
                'expect_level': expect_level, 'prop_used': prop, 'confidence_rating': np.nan,
                'agency_rating': np.nan, 'block_num': block_num, 'early_response': False,
                'true_shape': target, 'resp_shape': resp_shape, 'left_shape': left_shape
            })
            kinematics_data.append(frame_data)
        
        # Aggregate evidence across trial (even for timeout)
        frame_evidence = [d['evidence'] for d in trial_kinematics]
        mean_evidence = np.mean(frame_evidence)
        sum_evidence = np.sum(frame_evidence)
        var_evidence = np.var(frame_evidence)
        
        return dict(
            target_snippet_id=target_snippet_idx, distractor_snippet_id=distractor_snippet_idx,
            catch_type=catch_type, phase=phase, block_num=block_num,
            angle_bias=angle_bias, applied_angle_bias=applied_angle, expect_level=expect_level, true_shape=target, resp_shape=resp_shape,
            true_side=("left" if target == left_shape else "right"), resp_side="timeout",
            left_shape=left_shape,
            confidence_rating=np.nan, accuracy=np.nan, rt_choice=np.nan,
            agency_rating=np.nan, prop_used=prop, early_response=False, low_move_ratio=low_move_ratio,
            mean_evidence=mean_evidence, sum_evidence=sum_evidence, var_evidence=var_evidence,
            # Pre-response evidence metrics not applicable for timeout
            rt_frame=np.nan, num_frames_preRT=np.nan,
            mean_evidence_preRT=np.nan, sum_evidence_preRT=np.nan, var_evidence_preRT=np.nan,
            cum_evidence_preRT=np.nan, max_cum_evidence_preRT=np.nan, min_cum_evidence_preRT=np.nan,
            max_abs_cum_evidence_preRT=np.nan, prop_positive_evidence_preRT=np.nan
        )

    correct = int(resp_shape == target)
    # Side-based labels (the real answer is left vs right; both objects are circles).
    true_side = "left" if target == left_shape else "right"
    resp_side = "left" if resp_shape == left_shape else "right"

    # Confidence rating (1-4 scale) - separate screen (skip for calibration phase).
    # WP3 phases use their own 9-point probe AFTER the post-decision evidence sample.
    confidence_rating = np.nan
    if phase not in ["calibration", "practice", "fixedtest"] and not phase.startswith("wp3"):  # Only ask for confidence in test phase
        msg.text = "How confident are you in your choice?"
        conf_positions = [(-300, -100), (-100, -100), (100, -100), (300, -100)]
        conf_labels = ["1\nNot at all", "2\nSlightly", "3\nModerately", "4\nVery"]
        conf_stimuli = [visual.TextStim(win, text=label, pos=pos, height=24, color='white', alignText='center', bold=True)
                        for pos, label in zip(conf_positions, conf_labels)]
        conf_rating = None
        while conf_rating is None:
            msg.draw()
            for stim in conf_stimuli: stim.draw()
            win.flip()
            keys = event.getKeys(['1', '2', '3', '4', 'escape'])
            if keys:
                if 'escape' in keys: _save(); core.quit()
                else: conf_rating = int(keys[0])
            core.wait(0.01)
        confidence_rating = conf_rating
        core.wait(0.2)

    # Show feedback for calibration and learning trials (no feedback in test)
    if phase == "calibration" or (phase == "practice" and LEARNING_FEEDBACK):
        feedbackTxt.text = "Right" if correct else "Wrong"
        feedbackTxt.draw(); win.flip(); core.wait(0.8)
        win.flip(); core.wait(0.3)

    # Agency rating (only for test trials) - using memory preference [[memory:4144075]]
    agency_rating = np.nan
    if phase == "test":
        # Clear keyboard buffer to prevent carryover from confidence rating
        event.clearEvents(eventType='keyboard')

        msg.text = "How much control did you feel over the movement?"
        scale_positions = [(-540, -100), (-360, -100), (-180, -100), (0, -100), (180, -100), (360, -100), (540, -100)]
        scale_labels = ["1\nVery\nweak","2\nWeak","3\nSomewhat\nweak","4\nModerate","5\nSomewhat\nstrong","6\nStrong","7\nVery\nstrong"]
        scale_stimuli = [visual.TextStim(win, text=label, pos=pos, height=24, color='white', alignText='center', bold=True)
                         for pos, label in zip(scale_positions, scale_labels)]
        rating = None
        while rating is None:
            msg.draw()
            for stim in scale_stimuli: stim.draw()
            win.flip()
            keys = event.getKeys(['1','2','3','4','5','6','7','escape'])
            if keys:
                if 'escape' in keys: _save(); core.quit()
                else: rating = int(keys[0])
            core.wait(0.01)
        agency_rating = rating
        core.wait(0.2)

    for frame_data in trial_kinematics:
        frame_data.update({
            'participant': expInfo['participant'], 'session': expInfo['session'],
            'trial_num': trial_num, 'phase': phase, 'angle_bias': angle_bias,
            'applied_angle_bias': applied_angle,
            'expect_level': expect_level, 'prop_used': prop, 'confidence_rating': confidence_rating,
            'agency_rating': agency_rating, 'block_num': block_num, 'early_response': early_response,
            'true_shape': target, 'resp_shape': resp_shape, 'left_shape': left_shape
        })
        kinematics_data.append(frame_data)

    # Aggregate evidence across trial
    frame_evidence = [d['evidence'] for d in trial_kinematics]
    mean_evidence = np.mean(frame_evidence)
    sum_evidence = np.sum(frame_evidence)
    var_evidence = np.var(frame_evidence)

    # Pre-response evidence metrics (using all recorded frames which are pre-RT by construction)
    if early_response and len(trial_kinematics) > 0:
        pre_rt_evidence = frame_evidence
        cum = np.cumsum(pre_rt_evidence)
        mean_evidence_preRT = float(np.mean(pre_rt_evidence))
        sum_evidence_preRT = float(np.sum(pre_rt_evidence))
        var_evidence_preRT = float(np.var(pre_rt_evidence))
        max_cum_evidence_preRT = float(np.max(cum))
        min_cum_evidence_preRT = float(np.min(cum))
        max_abs_cum_evidence_preRT = float(np.max(np.abs(cum)))
        prop_positive_evidence_preRT = float(np.mean(np.array(pre_rt_evidence) > 0))
        rt_frame_out = int(trial_kinematics[-1]['frame']) if rt_frame is None else int(rt_frame)
        num_frames_preRT = int(len(pre_rt_evidence))
    else:
        mean_evidence_preRT = np.nan
        sum_evidence_preRT = np.nan
        var_evidence_preRT = np.nan
        max_cum_evidence_preRT = np.nan
        min_cum_evidence_preRT = np.nan
        max_abs_cum_evidence_preRT = np.nan
        prop_positive_evidence_preRT = np.nan
        rt_frame_out = np.nan
        num_frames_preRT = np.nan

    return dict(
        target_snippet_id=target_snippet_idx, distractor_snippet_id=distractor_snippet_idx,
        catch_type=catch_type, phase=phase, block_num=block_num,
        angle_bias=angle_bias, applied_angle_bias=applied_angle, expect_level=expect_level, true_shape=target, resp_shape=resp_shape,
        true_side=true_side, resp_side=resp_side, left_shape=left_shape,
        confidence_rating=confidence_rating, accuracy=correct, rt_choice=rt_choice,
        agency_rating=agency_rating, prop_used=prop, early_response=early_response, low_move_ratio=low_move_ratio,
        mean_evidence=mean_evidence, sum_evidence=sum_evidence, var_evidence=var_evidence,
        rt_frame=rt_frame_out, num_frames_preRT=num_frames_preRT,
        mean_evidence_preRT=mean_evidence_preRT, sum_evidence_preRT=sum_evidence_preRT, var_evidence_preRT=var_evidence_preRT,
        cum_evidence_preRT=sum_evidence_preRT, max_cum_evidence_preRT=max_cum_evidence_preRT, min_cum_evidence_preRT=min_cum_evidence_preRT,
        max_abs_cum_evidence_preRT=max_abs_cum_evidence_preRT, prop_positive_evidence_preRT=prop_positive_evidence_preRT
    )

# ───────────────────────────────────────────────────────
#  QUEST+ style adaptive training (Green=0.90, Blue=0.65)
# ───────────────────────────────────────────────────────

def logit(x):
    x = float(np.clip(x, 1e-6, 1-1e-6))
    return float(np.log(x/(1-x)))

def inv_logit(z):
    return float(1.0/(1.0 + np.exp(-z)))

def clamp_prop(s):
    return float(np.clip(s, 0.02, 0.90))

class QuestPlusStaircase:
    def __init__(self, target_type):
        """
        QUEST+ implementation with proper entropy-based stimulus selection
        target_type: "high" for 80% target, "low" for 60% target, or "neutral" for calibration
        """
        # Grids as specified
        self.s_grid = np.linspace(logit(0.05), logit(0.90), 61)  # Stimulus grid (logit domain)
        self.alpha_grid = np.linspace(logit(0.05), logit(0.90), 61)  # Threshold grid
        self.beta_grid = np.geomspace(1.0, 12.0, 25)  # Slope grid  
        self.lambda_grid = np.array([0.00, 0.01, 0.02, 0.04, 0.06])  # Lapse grid
        self.gamma = 0.5  # 2AFC chance level
        
        self.target_type = target_type
        
        # Priors adjusted based on pilot data (shifted down by ~0.22 from original)
        if target_type == "high":
            alpha_mu = logit(0.48)  # "high target" prior mean (was 0.70)
        elif target_type == "low":
            alpha_mu = logit(0.33)  # "low target" prior mean (was 0.55)
        else:
            alpha_mu = logit(0.40)  # Neutral prior from pilot participants (was 0.625)
        alpha_sd = 1.0  # Prior SD in logits
        
        self.prior_alpha = np.exp(-0.5 * ((self.alpha_grid - alpha_mu) / alpha_sd)**2)
        self.prior_alpha /= self.prior_alpha.sum()
        
        # Beta prior: log-normal with mean 2.5, gsd 2.0
        beta_mean = 2.5
        beta_gsd = 2.0
        ln_beta_mean = np.log(beta_mean)
        ln_beta_sd = np.log(beta_gsd)
        self.prior_beta = np.exp(-0.5 * ((np.log(self.beta_grid) - ln_beta_mean) / ln_beta_sd)**2)
        self.prior_beta /= self.prior_beta.sum()

        # Lambda prior: uniform
        self.prior_lambda = np.ones_like(self.lambda_grid) / len(self.lambda_grid)
        
        # Initialize posteriors to priors
        self.post_alpha = self.prior_alpha.copy()
        self.post_beta = self.prior_beta.copy()
        self.post_lambda = self.prior_lambda.copy()

        # Trial history
        self.trial_count = 0
        self.responses = []  # List of (stimulus_logit, correct) pairs
        
    def psychometric(self, s_logit, alpha, beta, lapse):
        """Psychometric function: p(correct | s; α, β, λ) = γ + (1 - γ - λ) σ(β [s - α])"""
        sigmoid = 1.0 / (1.0 + np.exp(-beta * (s_logit - alpha)))
        return self.gamma + (1.0 - self.gamma - lapse) * sigmoid
    
    def compute_entropy(self, posterior):
        """Compute entropy of a probability distribution"""
        posterior = posterior + 1e-12  # Avoid log(0)
        return -np.sum(posterior * np.log(posterior))
    
    def select_stimulus_entropy_fast(self):
        """Fast approximation of entropy-based stimulus selection for speed"""
        # Use a smaller subset of stimuli for entropy calculation to speed up
        # This maintains the core QUEST+ principle while being much faster
        
        # Subsample stimulus grid for faster computation (every 3rd point)
        s_grid_subset = self.s_grid[::3]  # Reduces from 61 to ~20 points
        
        current_entropy = self.compute_entropy(self.post_alpha)
        best_stimulus = None
        max_info_gain = -np.inf
        
        for s_logit in s_grid_subset:
            # Fast posterior predictive probability using current means
            alpha_mean = np.sum(self.alpha_grid * self.post_alpha)
            beta_mean = np.sum(self.beta_grid * self.post_beta)
            lambda_mean = np.sum(self.lambda_grid * self.post_lambda)
            
            p_correct = self.psychometric(s_logit, alpha_mean, beta_mean, lambda_mean)
            p_incorrect = 1.0 - p_correct
            
            # Skip if probability is too extreme
            if p_correct < 1e-6 or p_incorrect < 1e-6:
                continue
            
            # Simplified entropy approximation using only alpha updates
            # (since alpha/threshold is what we care most about)
            post_alpha_correct = np.zeros_like(self.post_alpha)
            post_alpha_incorrect = np.zeros_like(self.post_alpha)
            
            for i, alpha in enumerate(self.alpha_grid):
                # Use mean beta and lambda for speed
                like_correct = self.psychometric(s_logit, alpha, beta_mean, lambda_mean)
                like_incorrect = 1.0 - like_correct
                
                post_alpha_correct[i] = self.post_alpha[i] * like_correct
                post_alpha_incorrect[i] = self.post_alpha[i] * like_incorrect
            
            # Normalize
            post_alpha_correct /= (post_alpha_correct.sum() + 1e-12)
            post_alpha_incorrect /= (post_alpha_incorrect.sum() + 1e-12)
            
            # Expected entropy focusing on alpha
            entropy_correct = self.compute_entropy(post_alpha_correct)
            entropy_incorrect = self.compute_entropy(post_alpha_incorrect)
            expected_entropy = p_correct * entropy_correct + p_incorrect * entropy_incorrect
            
            # Information gain
            info_gain = current_entropy - expected_entropy
            
            if info_gain > max_info_gain:
                max_info_gain = info_gain
                best_stimulus = s_logit
        
        # Convert back to probability space and clamp
        if best_stimulus is None:
            best_stimulus = self.s_grid[len(self.s_grid)//2]  # Fallback to middle
            
        return clamp_prop(inv_logit(best_stimulus))
    
    def select_stimulus_entropy(self):
        """Select stimulus using fast entropy approximation"""
        # Use the fast version to avoid delays
        return self.select_stimulus_entropy_fast()
    
    def update(self, stimulus_prop, correct):
        """Update posterior after observing response"""
        s_logit = logit(clamp_prop(stimulus_prop))
        
        # Bayesian update using full joint posterior
        new_post = np.zeros((len(self.alpha_grid), len(self.beta_grid), len(self.lambda_grid)))
        
        for i, alpha in enumerate(self.alpha_grid):
            for j, beta in enumerate(self.beta_grid):
                for k, lapse in enumerate(self.lambda_grid):
                    prior_weight = self.post_alpha[i] * self.post_beta[j] * self.post_lambda[k]
                    likelihood = self.psychometric(s_logit, alpha, beta, lapse) if correct else (1.0 - self.psychometric(s_logit, alpha, beta, lapse))
                    new_post[i, j, k] = prior_weight * likelihood
        
        # Normalize
        new_post /= (new_post.sum() + 1e-12)
        
        # Marginalize to get individual posteriors
        self.post_alpha = new_post.sum(axis=(1, 2))
        self.post_beta = new_post.sum(axis=(0, 2))
        self.post_lambda = new_post.sum(axis=(0, 1))
        
        # Store trial data
        self.trial_count += 1
        self.responses.append((s_logit, correct))
    
    def get_threshold_sd(self):
        """Get standard deviation of alpha (threshold) posterior in logits"""
        alpha_mean = np.sum(self.alpha_grid * self.post_alpha)
        alpha_var = np.sum(self.post_alpha * (self.alpha_grid - alpha_mean)**2)
        return float(np.sqrt(alpha_var))
    
    def get_threshold_mean(self):
        """Get mean of alpha (threshold) posterior in logits"""
        return float(np.sum(self.alpha_grid * self.post_alpha))

    def posterior_summary(self):
        """Get summary statistics of posteriors"""
        alpha_mean = np.sum(self.alpha_grid * self.post_alpha)
        alpha_sd = np.sqrt(np.sum(self.post_alpha * (self.alpha_grid - alpha_mean)**2))
        
        beta_mean = np.sum(self.beta_grid * self.post_beta)
        beta_sd = np.sqrt(np.sum(self.post_beta * (self.beta_grid - beta_mean)**2))
        
        lambda_mean = np.sum(self.lambda_grid * self.post_lambda)
        lambda_sd = np.sqrt(np.sum(self.post_lambda * (self.lambda_grid - lambda_mean)**2))
        
        return {
            'alpha_mean': float(alpha_mean),
            'alpha_sd': float(alpha_sd),
            'beta_mean': float(beta_mean), 
            'beta_sd': float(beta_sd),
            'lambda_mean': float(lambda_mean),
            'lambda_sd': float(lambda_sd)
        }

    def threshold_for_target(self, p_target):
        """Compute threshold for target percentage correct using posterior predictive"""
        # Ensure feasibility: p_target <= 1 - lambda_hat
        lambda_hat = np.sum(self.lambda_grid * self.post_lambda)
        max_achievable = 1.0 - lambda_hat
        
        if p_target > max_achievable:
            p_target = min(0.85, max_achievable - 0.02)
        
        # Find stimulus that gives closest to target performance
        best_diff = float('inf')
        best_s = 0.5
        
        for s_logit in self.s_grid:
            # Posterior predictive probability
            p_pred = 0.0
            for i, alpha in enumerate(self.alpha_grid):
                for j, beta in enumerate(self.beta_grid):
                    for k, lapse in enumerate(self.lambda_grid):
                        weight = self.post_alpha[i] * self.post_beta[j] * self.post_lambda[k]
                        p_pred += weight * self.psychometric(s_logit, alpha, beta, lapse)
            
            diff = abs(p_pred - p_target)
            if diff < best_diff:
                best_diff = diff
                best_s = inv_logit(s_logit)
        
        return clamp_prop(best_s)

# 1u2d staircase lives in staircase.py so simulate_staircase.py drives the exact
# same logic the experiment runs (single source of truth, no drifting copy).
from staircase import TwoDownOneUpStaircase, WeightedUpDownStaircase

# Covert closed-loop tracking during test (default ON, CDT_TRACK_TEST=0 reverts
# to fixed calibration-derived levels). Rationale: the threshold is calibrated
# WITH feedback but test runs WITHOUT — pilot p99 showed the same prop yielding
# 69% in calibration but 57% in test, collapsing medium onto hard while easy sat
# at 100%. Design (2026-07-14): ONLY medium is tracked (the 1u2d has enough test
# trials to hold ~70.7% against drift); easy/hard are a SYMMETRIC logit offset from
# the LIVE medium — easy = medium + TEST_OFFSET, hard = medium − TEST_OFFSET. This
# is consistent (both derived the same way), adapts to the participant's threshold,
# and avoids near-chance staircasing on the flat part of the curve. Cue colors stay
# interleaved, so both cue conditions sample the same props in expectation.
TRACK_TEST = os.environ.get("CDT_TRACK_TEST", "1") == "1"
# Resume a split session: CDT_ONLY_BLOCK=2 runs ONLY the second angle block
# (calibration + learning + test for that angle), CDT_ONLY_BLOCK=1 only the first.
# Everything derived from the participant number - learning_order, palettes,
# counterbalancing - is unchanged, so block 2 is identical to what it would have
# been in one sitting. Data lands in its own file; merge afterwards.
ONLY_BLOCK = int(os.environ.get("CDT_ONLY_BLOCK", "0"))
TEST_OFFSET = float(os.environ.get("CDT_TEST_OFFSET", "1.5"))  # easy/hard logit distance from medium (learning + test)
# Feedback in the LEARNING phase (default OFF): teaches the cue->control association
# via the genuine felt difficulty only, not an explicit correct/incorrect label —
# purer expectation, matches the no-feedback test context. Calibration keeps feedback.
LEARNING_FEEDBACK = os.environ.get("CDT_LEARNING_FEEDBACK", "0") == "1"


# Global staircase system: one per angle (0 deg and 90 deg)
global_quest = None

def initialize_global_quest():
    """Initialize 2 staircases (1u2d) for the two angle conditions (0 deg and 90 deg)."""
    global global_quest
    global_quest = {
        '0': TwoDownOneUpStaircase(),
        '90': TwoDownOneUpStaircase(),
    }

def reset_quest_for_angle(angle_bias):
    """Reset the staircase for a specific angle (0 deg or 90 deg)."""
    global global_quest
    abs_angle = abs(angle_bias)
    print(f"Resetting staircase for angle condition: {angle_bias} deg")
    global_quest[f'{abs_angle}'] = TwoDownOneUpStaircase()

def run_calibration_both_angles(max_trials_per_staircase=70, min_trials_per_staircase=35, required_reversals=12, angle_keys=('0', '90')):
    """
    Block 1: Calibration phase with both 0 deg and 90 deg angles interleaved.
    Runs one 1-up-2-down staircase per angle (converges on 70.7% correct). Stops
    each staircase after `required_reversals` reversals (bounded by
    min/max_trials_per_staircase).

    Parameter rationale (Leek 2001; Wetherill & Levitt 1965):
    - 12 reversals: the first 3 occur at the large step size during initial
      descent and are conventionally excluded; the 9 reversals that follow are
      at the small step and 8 of them are averaged to estimate the threshold.
      8–12 usable reversals is standard in the literature; fewer risks
      over-estimating thresholds.
    - 35–70 trials per staircase: 35 is the minimum below which most
      participants will not yet have accumulated 12 reversals; 70 is a hard cap
      to prevent pathological cases from running forever. Typical sessions
      finish around 40–50 trials per staircase (~80–100 total calibration
      trials across both angles).
    """
    global global_quest, global_trial_counter
    if global_quest is None:
        raise ValueError("Global staircases not initialized. Call initialize_global_quest() first.")

    # Testing aid: CDT_CALIB_BLOCKED=1 runs 0deg fully, then 90deg fully (separated
    # blocks) instead of interleaved. Default = interleaved (Wen-correct: prevents
    # learning the 90deg transform).
    blocked = os.environ.get("CDT_CALIB_BLOCKED", "0") == "1"
    print(f"Starting Calibration Block - {'BLOCKED (0deg then 90deg)' if blocked else 'interleaved'}")

    staircase_keys = list(angle_keys)   # ('90',) for per-block calibration of one angle
    trials_per_staircase = {key: 0 for key in staircase_keys}

    trial_counter = 0
    safety_cap_total = max_trials_per_staircase * len(staircase_keys)

    while trial_counter < safety_cap_total:
        # Check stopping: a staircase is done once it hits required reversals AND min trials,
        # or it reaches the max-trial safety cap.
        all_done = True
        available = []
        for sk in staircase_keys:
            q = global_quest[sk]
            td = trials_per_staircase[sk]
            done = (q.has_converged(required_reversals) and td >= min_trials_per_staircase) or (td >= max_trials_per_staircase)
            if not done:
                all_done = False
                available.append(sk)

        if all_done:
            for sk in staircase_keys:
                q = global_quest[sk]
                td = trials_per_staircase[sk]
                thr = q.threshold_estimate()
                sd = q.threshold_sd()
                status = "converged" if q.has_converged(required_reversals) else "max trials reached"
                print(f"  Staircase {sk} deg: {td} trials, {q.n_reversals} reversals, "
                      f"threshold={thr:.3f} (SD={sd:.3f}) — {status}")
            print(f"All staircases done after {trial_counter} total trials")
            break

        if not available:
            break

        # Blocked: finish the first available angle before the next. Interleaved:
        # run whichever staircase has fewer trials so far.
        selected = available[0] if blocked else min(available, key=lambda k: trials_per_staircase[k])
        angle_bias = int(selected)

        trial_counter += 1
        global_trial_counter += 1
        trials_per_staircase[selected] += 1

        q = global_quest[selected]
        s_candidate = q.next_stimulus()

        expect_level = 'low'  # placeholder; cue is always black during calibration
        res = run_trial(
            trial_counter, "calibration", angle_bias=angle_bias, expect_level=expect_level, mode="calibration",
            prop_override=s_candidate, cue_dur_range=(0.5, 0.8), motion_dur=5.0
        )

        # Only update staircase on valid responses (exclude timeouts)
        if res.get('resp_shape') != 'timeout':
            correct = int(res.get('accuracy', 0))
            q.update(s_candidate, correct)

        staircase_threshold = q.threshold_estimate()
        staircase_threshold_sd = q.threshold_sd()

        thisExp.addData('trial_num', global_trial_counter)
        thisExp.addData('participant', expInfo['participant'])
        thisExp.addData('session', expInfo['session'])
        thisExp.addData('phase', 'calibration_interleaved')
        thisExp.addData('cue_color', 'black')
        thisExp.addData('target_difficulty', 'unknown')
        thisExp.addData('trial_index_within_staircase', trials_per_staircase[selected])
        used_prop = res.get('prop_used', s_candidate)
        thisExp.addData('prop_used', used_prop)
        thisExp.addData('stimulus_logit', logit(used_prop))
        thisExp.addData('staircase_id', selected)
        thisExp.addData('accuracy', res.get('accuracy', 0))
        thisExp.addData('low_move_ratio', res.get('low_move_ratio', np.nan))
        thisExp.addData('is_timeout', res.get('resp_shape') == 'timeout')
        thisExp.addData('rt_choice', res.get('rt_choice', np.nan))
        thisExp.addData('early_response', res.get('early_response', False))
        thisExp.addData('true_shape', res.get('true_shape', ''))
        thisExp.addData('resp_shape', res.get('resp_shape', ''))

        # New staircase-specific logging
        thisExp.addData('staircase_type', '1u2d')
        thisExp.addData('staircase_prop', used_prop)
        thisExp.addData('staircase_reversals', q.n_reversals)
        thisExp.addData('staircase_threshold', staircase_threshold)
        thisExp.addData('staircase_threshold_sd', staircase_threshold_sd)

        # Legacy QUEST columns kept as NaN for backwards-compat with old analysis scripts
        thisExp.addData('quest_alpha_mean', np.nan)
        thisExp.addData('quest_alpha_sd', np.nan)
        thisExp.addData('quest_beta_mean', np.nan)
        thisExp.addData('quest_beta_sd', np.nan)
        thisExp.addData('quest_lambda_mean', np.nan)
        thisExp.addData('quest_lambda_sd', np.nan)

        thisExp.addData('angle_bias', angle_bias)
        thisExp.addData('applied_angle_bias', res.get('applied_angle_bias', angle_bias))
        thisExp.addData('trials_completed_this_staircase', trials_per_staircase[selected])
        thisExp.addData('alpha_sd_current', staircase_threshold_sd)
        # Evidence metrics
        thisExp.addData('mean_evidence', res.get('mean_evidence', np.nan))
        thisExp.addData('sum_evidence', res.get('sum_evidence', np.nan))
        thisExp.addData('var_evidence', res.get('var_evidence', np.nan))
        # Pre-RT evidence metrics
        thisExp.addData('rt_frame', res.get('rt_frame', np.nan))
        thisExp.addData('num_frames_preRT', res.get('num_frames_preRT', np.nan))
        thisExp.addData('mean_evidence_preRT', res.get('mean_evidence_preRT', np.nan))
        thisExp.addData('sum_evidence_preRT', res.get('sum_evidence_preRT', np.nan))
        thisExp.addData('var_evidence_preRT', res.get('var_evidence_preRT', np.nan))
        thisExp.addData('cum_evidence_preRT', res.get('cum_evidence_preRT', np.nan))
        thisExp.addData('max_cum_evidence_preRT', res.get('max_cum_evidence_preRT', np.nan))
        thisExp.addData('min_cum_evidence_preRT', res.get('min_cum_evidence_preRT', np.nan))
        thisExp.addData('max_abs_cum_evidence_preRT', res.get('max_abs_cum_evidence_preRT', np.nan))
        thisExp.addData('prop_positive_evidence_preRT', res.get('prop_positive_evidence_preRT', np.nan))
        thisExp.nextEntry()
        # ponytail: no break inside calibration (by request — keeps it continuous)

def compute_difficulty_levels_for_angle(angle_bias):
    """
    Compute easy/hard/medium difficulty levels for a given angle from the 1u2d
    staircase threshold.

    medium = staircase threshold (~70.7% correct)
    easy   = inv_logit(logit(medium) + DELTA_LOGIT)   (more control, symmetric in logit)
    hard   = inv_logit(logit(medium) - DELTA_LOGIT)   (less control, symmetric in logit)

    Symmetric logit-offset centres medium between easy/hard for the expectation
    manipulation; depends only on the threshold, not the (unmeasured) slope.

    Returns (s_hard, s_medium, s_easy) and persists in learning_levels_by_angle
    and difficulty_levels_by_angle.
    """
    global global_quest
    staircase = global_quest[f'{angle_bias}']

    s_medium = clamp_prop(staircase.threshold_estimate())   # 70.7% from the staircase
    m_logit = logit(s_medium)
    # easy/hard = symmetric logit offset from the calibration medium — the SAME
    # scheme the test phase uses, so learning and test are consistent. Learning
    # anchors on the calibration medium; the test tracks the live medium.
    s_easy = clamp_prop(inv_logit(m_logit + TEST_OFFSET))
    s_hard = clamp_prop(inv_logit(m_logit - TEST_OFFSET))

    learning_levels_by_angle[angle_bias] = (s_hard, s_easy)
    difficulty_levels_by_angle[angle_bias] = (s_hard, s_medium, s_easy)

    print(f"Difficulty levels for {angle_bias} deg (medium +/- {TEST_OFFSET} logit):")
    print(f"  Easy   (medium +{TEST_OFFSET} logit): s={s_easy:.3f}")
    print(f"  Medium (1u2d threshold, ~70.7%):     s={s_medium:.3f}")
    print(f"  Hard   (medium -{TEST_OFFSET} logit): s={s_hard:.3f}")


# ── MOCS diagnostic + QUEST+ seeding ───────────────────────────────────────────
# One shared fit file the MOCS block writes and the QUEST+ calibration reads.
FIT_PATH = root / "mocs_fit.json"

def _fit_psychometric(pairs):
    """Bayesian 3-param fit reusing the QUEST+ posterior machinery (no scipy).
    pairs: list of (prop, correct, order_idx). Returns (alpha_logit, beta, lambda)."""
    q = QuestPlusStaircase("neutral")
    for prop, correct, _ in pairs:
        q.update(prop, correct)
    s = q.posterior_summary()
    return s['alpha_mean'], s['beta_mean'], s['lambda_mean']

def _mocs_plot(responses, fit):
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"[MOCS] plot skipped ({e})"); return
    grid = sorted(set(MOCS_GRID))
    fig, axes = plt.subplots(1, len(responses), figsize=(6 * len(responses), 5), squeeze=False)
    for ax, (ang, pairs) in zip(axes[0], responses.items()):
        xs, ys, ns = [], [], []
        for p in grid:
            cs = [c for pr, c, _ in pairs if abs(pr - p) < 1e-6]
            if cs:
                xs.append(p); ys.append(float(np.mean(cs))); ns.append(len(cs))
        ax.scatter(xs, ys, s=[20 + 5 * n for n in ns], color="steelblue", zorder=3, label="observed")
        f = fit.get(str(ang))
        if f:
            xx = np.linspace(min(grid) * 0.8, max(grid) * 1.1, 200)
            yy = [0.5 + (0.5 - f["lambda"]) /
                  (1 + np.exp(-f["beta"] * (logit(float(np.clip(x, 0.02, 0.9))) - f["alpha_logit"])))
                  for x in xx]
            ax.plot(xx, yy, color="crimson", lw=2, label="fit")
            for pt, ls in [(0.85, ":"), (0.707, "-"), (0.60, "--")]:
                ax.axhline(pt, color="gray", ls=ls, lw=0.8)
        ax.axhline(0.5, color="black", lw=0.5)
        ax.set_ylim(0.4, 1.02); ax.set_xlabel("control prop"); ax.set_ylabel("p(correct)")
        d = (f or {}).get("drift")
        ax.set_title(f"{ang} deg" + (f"   drift {d:+.2f}" if d is not None else ""))
        ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    png = root / "mocs_curve.png"
    fig.savefig(png, dpi=110); print(f"[MOCS] wrote {png}")

def _mocs_fit_and_report(responses):
    fit = {}
    for ang, pairs in responses.items():
        if len(pairs) < 10:
            print(f"[MOCS] angle {ang}: only {len(pairs)} valid trials — skipping fit"); continue
        a_log, beta, lam = _fit_psychometric(pairs)
        order = sorted(pairs, key=lambda t: t[2]); half = len(order) // 2
        acc1 = float(np.mean([c for _, c, _ in order[:half]]))
        acc2 = float(np.mean([c for _, c, _ in order[half:]]))
        fit[str(ang)] = {"alpha_logit": a_log, "alpha_prop": inv_logit(a_log),
                         "beta": beta, "lambda": lam, "n": len(pairs),
                         "acc_first_half": acc1, "acc_second_half": acc2, "drift": acc2 - acc1}
        print(f"[MOCS] {ang} deg: alpha={inv_logit(a_log):.3f} (logit {a_log:.2f})  "
              f"beta={beta:.2f}  lambda={lam:.3f}  n={len(pairs)}  "
              f"drift {acc1:.2f}->{acc2:.2f} ({acc2-acc1:+.2f})")
    FIT_PATH.write_text(json.dumps(fit, indent=2))
    print(f"[MOCS] wrote {FIT_PATH}")
    print("[MOCS] READ THE CURVE before trusting these: a graded slope + drift ~0 "
          "means QUEST+ can use beta/lambda; a steep step or big drift means fix "
          "that first (temporal manipulation / familiarization) — see chat.")
    _mocs_plot(responses, fit)

def run_mocs_block():
    """Fixed-grid method-of-constant-stimuli block. Reuses run_trial verbatim, then
    fits + reports. Diagnostic only: closes the window and quits at the end."""
    reps = 3 if CHECK_MODE else MOCS_REPS
    trials = [(ang, p) for ang in MOCS_ANGLES for p in MOCS_GRID for _ in range(reps)]
    random.shuffle(trials)
    msg.text = (f"Diagnostic block: {len(trials)} trials "
                f"({len(MOCS_GRID)} levels x {reps} x {len(MOCS_ANGLES)} angles).\n\n"
                "Black shapes, no feedback, no ratings. Keep the mouse moving.\n\n"
                "a = left, s = right.\n\nPress SPACE to start...")
    msg.draw(); win.flip(); wait_keys()
    responses = {ang: [] for ang in MOCS_ANGLES}
    for i, (ang, p) in enumerate(trials):
        res = run_trial(i + 1, "calibration", angle_bias=ang, expect_level="low",
                        mode="calibration", prop_override=p,
                        cue_dur_range=(0.5, 0.8), motion_dur=5.0)
        if res.get('resp_shape') != 'timeout':
            responses[ang].append((res.get('prop_used', p), int(res.get('accuracy', 0)), i))
        thisExp.addData('trial_num', i + 1)
        thisExp.addData('participant', expInfo['participant'])
        thisExp.addData('phase', 'mocs')
        thisExp.addData('angle_bias', ang)
        thisExp.addData('prop_used', res.get('prop_used', p))
        thisExp.addData('stimulus_logit', logit(res.get('prop_used', p)))
        thisExp.addData('accuracy', res.get('accuracy', 0))
        thisExp.addData('resp_shape', res.get('resp_shape', ''))
        thisExp.addData('rt_choice', res.get('rt_choice', np.nan))
        thisExp.nextEntry()
        if (i + 1) % 48 == 0 and (i + 1) < len(trials):
            show_break_screen(i + 1, len(trials), "diagnostic block")
    _save()
    win.close()
    _mocs_fit_and_report(responses)
    core.quit()

def run_quest_calibration_from_mocs(angles=None, n_per_angle=40):
    """Per-participant QUEST+ calibration seeded from mocs_fit.json: beta & lambda
    FIXED from MOCS (they transfer across people), alpha estimated fresh (it does
    not). Places hard/medium/easy on the measured slope at ACC_HARD/ACC_MED/ACC_EASY.
    Pass angles=[one] to calibrate a single angle right before its block."""
    if not FIT_PATH.exists():
        raise FileNotFoundError(f"{FIT_PATH} missing — run a CDT_MOCS=1 self/pilot run first")
    angles = angles or MOCS_ANGLES
    fit = json.loads(FIT_PATH.read_text())
    quests = {}
    for ang in angles:
        f = fit[str(ang)]
        q = QuestPlusStaircase("neutral")
        # Collapse beta & lambda grids to the single measured value (fixed).
        q.beta_grid = np.array([f["beta"]]);   q.post_beta = np.array([1.0]);   q.prior_beta = np.array([1.0])
        q.lambda_grid = np.array([f["lambda"]]); q.post_lambda = np.array([1.0]); q.prior_lambda = np.array([1.0])
        # Seed alpha prior around the MOCS alpha but keep it free (moderate SD).
        q.post_alpha = np.exp(-0.5 * ((q.alpha_grid - f["alpha_logit"]) / 0.7) ** 2)
        q.post_alpha /= q.post_alpha.sum()
        quests[ang] = q
    counts = {ang: 0 for ang in angles}
    for t in range(n_per_angle * len(angles)):
        ang = min(counts, key=lambda k: counts[k]); counts[ang] += 1
        q = quests[ang]
        s = q.select_stimulus_entropy()
        res = run_trial(t + 1, "calibration", angle_bias=ang, expect_level="low",
                        mode="calibration", prop_override=s,
                        cue_dur_range=(0.5, 0.8), motion_dur=5.0)
        if res.get('resp_shape') != 'timeout':
            q.update(res.get('prop_used', s), int(res.get('accuracy', 0)))
        thisExp.addData('trial_num', t + 1)
        thisExp.addData('participant', expInfo['participant'])
        thisExp.addData('phase', 'quest_calibration')
        thisExp.addData('angle_bias', ang)
        thisExp.addData('prop_used', res.get('prop_used', s))
        thisExp.addData('stimulus_logit', logit(res.get('prop_used', s)))
        thisExp.addData('accuracy', res.get('accuracy', 0))
        thisExp.addData('resp_shape', res.get('resp_shape', ''))
        thisExp.addData('quest_alpha_mean', q.get_threshold_mean())
        thisExp.addData('quest_alpha_sd', q.get_threshold_sd())
        thisExp.nextEntry()
    for ang in angles:
        q = quests[ang]
        s_med  = clamp_prop(q.threshold_for_target(ACC_MED))   # calibrated (the measured level)
        # easy/hard: fixed extreme props if set, else accuracy targets on the curve.
        s_easy = clamp_prop(EASY_PROP) if EASY_PROP is not None else clamp_prop(q.threshold_for_target(ACC_EASY))
        s_hard = clamp_prop(HARD_PROP) if HARD_PROP is not None else clamp_prop(q.threshold_for_target(ACC_HARD))
        difficulty_levels_by_angle[ang] = (s_hard, s_med, s_easy)
        learning_levels_by_angle[ang] = (s_hard, s_easy)
        etag = "fixed" if EASY_PROP is not None else f"{ACC_EASY:.0%}"
        htag = "fixed" if HARD_PROP is not None else f"{ACC_HARD:.0%}"
        print(f"[QUEST/{ang} deg] alpha={inv_logit(q.get_threshold_mean()):.3f} "
              f"(SD {q.get_threshold_sd():.2f})  hard={s_hard:.3f} ({htag})  "
              f"med={s_med:.3f} ({ACC_MED:.0%})  easy={s_easy:.3f} ({etag})")


def run_feel_test():
    """Quick self-demo: FEEL_N hard, then medium, then easy (in that order) at the
    MOCS-fit props for FEEL_ANGLE. Black shapes (no cue), brief feedback. Not logged."""
    if not FIT_PATH.exists():
        msg.text = "No mocs_fit.json — run CDT_MOCS=1 first."; msg.draw(); win.flip(); wait_keys(); return
    f = json.loads(FIT_PATH.read_text())[str(FEEL_ANGLE)]
    def prop_at(p):
        sig = (p - 0.5) / (0.5 - f["lambda"]); z = np.log(sig / (1 - sig))
        return clamp_prop(inv_logit(f["alpha_logit"] + z / f["beta"]))
    s_med  = clamp_prop(MED_PROP) if MED_PROP is not None else prop_at(ACC_MED)
    if os.environ.get("CDT_FEEL_OFFSET", "0") == "1":
        # symmetric offset from medium (the test-phase scheme): easy = med+Δ, hard = med−Δ
        s_easy = clamp_prop(inv_logit(logit(s_med) + TEST_OFFSET))
        s_hard = clamp_prop(inv_logit(logit(s_med) - TEST_OFFSET))
    else:
        s_hard = clamp_prop(HARD_PROP) if HARD_PROP is not None else prop_at(ACC_HARD)
        s_easy = clamp_prop(EASY_PROP) if EASY_PROP is not None else prop_at(ACC_EASY)
    levels = [("HARD", ACC_HARD, s_hard),
              ("MEDIUM", ACC_MED, s_med),
              ("EASY", ACC_EASY, s_easy)]
    msg.text = (f"Feel-check  ({FEEL_ANGLE} deg)\n\n{FEEL_N}x hard, then medium, then easy.\n"
                "Black shapes, brief feedback.\n\na = left, s = right. Keep moving.\n\nPress SPACE...")
    msg.draw(); win.flip(); wait_keys()
    results = {}
    for name, acc, prop in levels:
        msg.text = f"Next: {FEEL_N}x   {name}\n\n(target {acc:.0%} correct)\n\nPress SPACE..."
        msg.draw(); win.flip(); wait_keys()
        c = n = 0
        for i in range(FEEL_N):
            res = run_trial(i + 1, "feel", angle_bias=FEEL_ANGLE, expect_level="low", mode="test",
                            prop_override=prop, cue_dur_range=(0.5, 0.8), motion_dur=5.0,
                            cue_color_override="black")
            if res.get('resp_shape') == 'timeout':
                msg.text, msg.color = "Zeit abgelaufen", "orange"
            elif res.get('accuracy') == 1:
                c += 1; n += 1; msg.text, msg.color = "Richtig ✓", "green"
            else:
                n += 1; msg.text, msg.color = "Falsch ✗", "red"
            msg.draw(); win.flip(); core.wait(0.6); msg.color = "black"
        results[name] = (c, n, prop)
    summary = "\n".join(f"{nm:6s}  prop {p:.3f}  ->  {c}/{n} correct" for nm, (c, n, p) in results.items())
    print("\n=== FEEL-CHECK RESULT (" + str(FEEL_ANGLE) + " deg) ===\n" + summary)
    msg.text = "Done.\n\n" + summary + "\n\n(also in console)\n\nPress SPACE to exit."
    msg.draw(); win.flip(); wait_keys()


def run_test_only():
    """Quick self-run of the REAL test phase: medium+easy+hard mix, two cue colors,
    confidence+agency ratings, no feedback, live medium tracking. Seeds medium
    (skips calibration) so it is fast. Reuses generate_test_trials + run_test_miniblock."""
    global low_col, high_col
    initialize_global_quest()
    angle = TESTONLY_ANGLE
    med = clamp_prop(MED_PROP if MED_PROP is not None else 0.36)
    global_quest[str(angle)].current_prop = med   # threshold_estimate() -> med (no reversals yet)
    compute_difficulty_levels_for_angle(angle)     # easy/hard = med ± TEST_OFFSET
    low_col, high_col = "red", "yellow"            # low = hard-cue, high = easy-cue
    s_hard, s_med, s_easy = difficulty_levels_by_angle[angle]
    msg.text = (f"Test phase — {TESTONLY_N} trials ({angle} deg)\n\n"
                "Decide which side you control, then rate confidence and control.\n"
                "The two colors signal expected difficulty. No feedback.\n\n"
                "a = left, s = right. Keep the mouse moving.\n\nPress SPACE to start...")
    msg.draw(); win.flip(); wait_keys()
    trials = generate_test_trials(angle, TESTONLY_N, low_col, high_col)
    run_test_miniblock(angle, trials, 1, 1, low_col, high_col, 0)
    _save()
    msg.text = "Done — thank you!\n\nPress SPACE to exit."
    msg.draw(); win.flip(); wait_keys()


# ── WP3: Rollwage-style post-decision evidence paradigm ────────────────────────

def wp3_confidence():
    """Rollwage et al. (2018) 9-point scale: subjective probability that the
    DECISION was correct. Point 1 = 0% (sure the OTHER circle was the controlled
    one), 5 = 50% (pure guess), 9 = 100% (sure the chosen circle was correct).
    Below the midpoint expresses a change of mind — no second decision needed.
    Returns (rating 1-9, prob 0-100, rt). Bot-compatible via the '7' key branch."""
    event.clearEvents(eventType='keyboard')
    msg.text = "How likely is it that your choice was correct?   (press 1-9)"
    xs = np.linspace(-480, 480, 9)
    track = visual.Line(win, start=(-480, -62), end=(480, -62), lineColor='gray', lineWidth=2)
    nums = [visual.TextStim(win, text=str(i + 1), pos=(float(x), -95), height=26,
                            color='white', bold=True) for i, x in enumerate(xs)]
    pcts = [visual.TextStim(win, text=t, pos=(float(xs[i]), -132), height=18, color='white')
            for t, i in [("0%", 0), ("50%", 4), ("100%", 8)]]
    anchors = [visual.TextStim(win, text="the OTHER circle\nwas the one I controlled",
                               pos=(float(xs[0]), -180), height=15, color='gray', alignText='center'),
               visual.TextStim(win, text="pure guess", pos=(float(xs[4]), -172), height=15, color='gray'),
               visual.TextStim(win, text="MY choice\nwas correct",
                               pos=(float(xs[8]), -180), height=15, color='gray', alignText='center')]
    t0 = core.getTime()
    while True:
        msg.draw(); track.draw()
        for s in nums + pcts + anchors: s.draw()
        win.flip()
        keys = event.getKeys([str(i) for i in range(1, 10)] + ['escape'])
        if keys:
            if 'escape' in keys: _save(); core.quit()
            r = int(keys[0]); core.wait(0.2)
            return r, (r - 1) / 8.0 * 100.0, core.getTime() - t0
        core.wait(0.01)


def wp3_score(rating, correct):
    """Quadratic (Brier-type) scoring rule on the 9-point scale, p = (rating-1)/8.
    Correct: 1-(1-p)^2, incorrect: 1-p^2 — a proper scoring rule: reporting one's
    true belief maximises expected score; max score both for 'sure and right' and
    'sure I was wrong and was wrong'. Timeouts (no rating) score 0. NEVER shown
    per trial: the score reveals correctness exactly, and the task is feedback-free."""
    if rating is None or (isinstance(rating, float) and np.isnan(rating)):
        return 0.0
    p = (float(rating) - 1.0) / 8.0
    return float(1.0 - (1.0 - p) ** 2) if correct else float(1.0 - p ** 2)


def wp3_bonus_text(mean_score):
    if WP3_BONUS > 0:
        return f"{WP3_BONUS_UNIT}{WP3_BONUS * mean_score:.2f} (of a possible {WP3_BONUS_UNIT}{WP3_BONUS:.2f})"
    return f"{100 * mean_score:.0f} out of 100 points"


def wp3_bonus_instructions():
    """Explain the incentive in principle (not the formula) and enforce comprehension
    with two forced-choice questions; a wrong answer re-shows the explanation. The
    attempt count is logged so 'never understood it' is analysable, not invisible."""
    stake = (f"a bonus of up to {WP3_BONUS_UNIT}{WP3_BONUS:.2f}" if WP3_BONUS > 0
             else "points (up to 100)")
    explain = ("How your confidence ratings earn " + stake + "\n\n"
               "After each choice you rate how likely it is that you were RIGHT\n"
               "(1 = 0%, 5 = 50%, 9 = 100%).\n\n"
               "What is rewarded is KNOWING WHEN YOU ARE RIGHT - not performance.\n"
               "Both of these earn the full amount:\n"
               "     you were right   AND you rated 9\n"
               "     you were wrong   AND you rated 1\n\n"
               "So being wrong costs you nothing, as long as you notice it.\n"
               "It only costs you to be wrong AND convinced - or to be right\n"
               "and not trust yourself.\n\n"
               "Always pressing 5 earns a middling amount. Random pressing earns little.\n"
               "The best strategy is simple: report honestly what you believe.\n\n"
               "You will NOT see your score during the task - only your total at the end.\n\n"
               "Press SPACE for two quick questions.")
    # Answered ON THE 1-9 SCALE ITSELF: an earlier version offered 1/2/3 answer keys
    # describing ratings 8-9 / 5 / 1-2, so the key was nearly the opposite of its
    # meaning. Using the real scale removes the collision and rehearses the response.
    quiz = [
        ("Question 1 of 2\n\n"
         "You chose the LEFT circle.\n"
         "The extra evidence then clearly showed the RIGHT one was yours.\n\n"
         "Which rating earns you the most bonus?\n\n"
         "press 1 - 9", lambda r: r <= 2),
        ("Question 2 of 2\n\n"
         "You chose the LEFT circle.\n"
         "The extra evidence then clearly confirmed it WAS yours.\n\n"
         "Which rating earns you the most bonus?\n\n"
         "press 1 - 9", lambda r: r >= 8),
    ]
    if BOT_MODE:                       # the bot cannot answer content questions
        expInfo['bonus_quiz_attempts'] = 0
        return 0
    attempts = 0
    while True:
        attempts += 1
        msg.text = explain; msg.draw(); win.flip(); wait_keys()
        ok = True
        for q, accept in quiz:
            event.clearEvents(eventType='keyboard')
            msg.text = q
            k = None
            while k is None:
                # MUST draw+flip every iteration: on the pyglet backend win.flip() is
                # what dispatches window events, so a poll loop without it never sees
                # a keypress — the screen just sits there, ESC included.
                msg.draw(); win.flip()
                keys = event.getKeys([str(i) for i in range(1, 10)] + ['escape'])
                if 'escape' in keys: _save(); core.quit()
                if keys: k = int(keys[0])
                core.wait(0.01)
            if not accept(k):
                ok = False
                msg.text = ("Not quite. The most is earned when your rating matches\n"
                            "what really happened: a HIGH rating when you were right,\n"
                            "a LOW rating when you were wrong.\n\n"
                            "Press SPACE to read the explanation again.")
                msg.draw(); win.flip(); wait_keys()
                break
        if ok:
            break
    expInfo['bonus_quiz_attempts'] = attempts
    return attempts


def wp3_motivation_check():
    """Manipulation check, asked BEFORE the bonus is revealed (so the amount cannot
    colour the answer): did the rule actually change how carefully people rated?"""
    if BOT_MODE:
        expInfo['bonus_motivation_1to5'] = np.nan
        return
    event.clearEvents(eventType='keyboard')
    msg.text = ("One last question.\n\n"
                "How much did the bonus rule affect how carefully you chose your confidence ratings?\n\n"
                "1 = not at all    2 = a little    3 = somewhat    4 = quite a bit    5 = very much")
    while True:
        msg.draw(); win.flip()   # flip every iteration, else no key is ever dispatched
        keys = event.getKeys(['1', '2', '3', '4', '5', 'escape'])
        if 'escape' in keys: _save(); core.quit()
        if keys:
            expInfo['bonus_motivation_1to5'] = int(keys[0]); core.wait(0.2); return
        core.wait(0.01)


def run_wp3():
    """WP3 (belief updating, Rollwage et al. 2018 adapted to the CDT). Per angle
    block, order counterbalanced via learning_order:
      calibration (1u2d -> medium) -> Task 1 (decision + confidence)
      -> Task 2 (decision -> post-decision evidence sample -> confidence).
    Medium difficulty only, black shapes, no cues, no feedback outside calibration.
    The evidence sample re-runs the motion with the SAME true target, at the same
    (low) or boosted (high, +WP3_BOOST logit) control strength — so it confirms
    correct choices and disconfirms wrong ones."""
    global low_col, high_col
    initialize_global_quest()
    t1_n = 3 if CHECK_MODE else WP3_T1_N
    t2_n = 4 if CHECK_MODE else WP3_T2_N
    trial_no = 0

    scores = []   # quadratic-scoring-rule score per rated trial, both tasks, pooled
    blk = {'clipped': False, 'med_live': np.nan}   # per-trial: boost clipped? live threshold?

    def log_row(task, ev_level, res, prop_pre, prop_post, conf, conf_prob, conf_rt, angle):
        sc = wp3_score(conf, res.get('accuracy') == 1)
        scores.append(sc)
        thisExp.addData('wp3_score', sc)               # never shown to the participant
        thisExp.addData('prop_high_clipped', blk['clipped'])   # if True, high ≈ low: exclude
        thisExp.addData('med_live', blk['med_live'])           # live 1u2d threshold: drift trace
        thisExp.addData('trial_num', trial_no)
        thisExp.addData('participant', expInfo['participant'])
        thisExp.addData('session', expInfo['session'])
        thisExp.addData('phase', f'wp3_task{task}')
        thisExp.addData('wp3_task', task)
        thisExp.addData('evidence_level', ev_level)   # 0 = none, 1 = low, 2 = high
        thisExp.addData('angle_bias', angle)
        thisExp.addData('applied_angle_bias', res.get('applied_angle_bias', angle))
        thisExp.addData('prop_used', prop_pre)
        thisExp.addData('prop_post', prop_post)
        thisExp.addData('accuracy', res.get('accuracy', np.nan))
        thisExp.addData('true_shape', res.get('true_shape', ''))
        thisExp.addData('resp_shape', res.get('resp_shape', ''))
        thisExp.addData('rt_choice', res.get('rt_choice', np.nan))
        thisExp.addData('is_timeout', res.get('resp_shape') == 'timeout')
        thisExp.addData('wp3_confidence', conf)        # 1-9 rating (5 = 50% guess)
        thisExp.addData('wp3_prob', conf_prob)         # 0-100 subjective P(correct)
        thisExp.addData('wp3_conf_rt', conf_rt)
        thisExp.addData('low_move_ratio', res.get('low_move_ratio', np.nan))
        thisExp.nextEntry()

    msg.text = ("Two identical circles, one LEFT and one RIGHT.\n"
                "One of them follows your mouse; the other does not.\n\n"
                "Move the mouse, then judge which one you controlled.\n"
                "a = LEFT circle, s = RIGHT circle.\n"
                "After most choices you will rate your confidence (keys 1-9).\n\n"
                "Press SPACE to start...")
    msg.draw(); win.flip(); wait_keys()
    wp3_bonus_instructions()   # once, before any rated trial; covers Task 1 AND Task 2

    for block_i, angle in enumerate(learning_order, 1):
        low_col, high_col = "black", "black"

        # --- per-block calibration: 1u2d staircase -> this angle's medium ---
        msg.text = (f"Calibration {block_i} of 2\n\nWith feedback. Black shapes.\n"
                    "a = left, s = right. Keep moving.\n\nPress SPACE to start...")
        msg.draw(); win.flip(); wait_keys()
        run_calibration_both_angles(
            max_trials_per_staircase=80 if not CHECK_MODE else CHECK_CALIBRATION_TRIALS,
            min_trials_per_staircase=40 if not CHECK_MODE else CHECK_CALIBRATION_TRIALS,
            required_reversals=12, angle_keys=(str(angle),))
        sc = global_quest[str(angle)]
        med0 = clamp_prop(sc.threshold_estimate())      # seed; also the fixed prop if tracking is off
        print(f"[WP3/{angle} deg] calibrated medium={med0:.3f}  "
              + ("staircase KEEPS RUNNING through Task 1 + 2" if WP3_TRACK else "prop FROZEN (Rollwage-style)"))

        def next_props():
            """Props for one decision trial: the live staircase value, and the boosted
            evidence strength derived from it (exactly +WP3_BOOST logit apart, per trial).
            With tracking on, the same 1u2d that calibrated this block keeps running
            through BOTH tasks, so practice/fatigue cannot shift accuracy between the
            phases the confidence slopes are computed over (WP1 does the same in its
            test phase, CDT_TRACK_TEST; pilot p99 drifted 69% -> 57% without it).
            Updates come from the decision only — never from the evidence sample."""
            p = clamp_prop(sc.next_stimulus()) if WP3_TRACK else med0
            return p, clamp_prop(inv_logit(logit(p) + WP3_BOOST))

        def track(res, used):
            if WP3_TRACK and res.get('resp_shape') != 'timeout':
                sc.update(used, int(res.get('accuracy', 0)))
            blk['med_live'] = clamp_prop(sc.threshold_estimate())

        # --- TASK 1: decision + confidence (evidence level 0) ---
        msg.text = ("Part A\n\nChoose the side you control, then rate your confidence.\n"
                    "No feedback from now on.\n\nPress SPACE to start...")
        msg.draw(); win.flip(); wait_keys()
        for _ in range(t1_n):
            trial_no += 1
            p_dec, p_high = next_props()
            blk['clipped'] = bool(p_high >= 0.899)   # boost would hit the ceiling at this difficulty
            res = run_trial(trial_no, "wp3_task1", angle_bias=angle, expect_level="low",
                            mode="test", prop_override=p_dec, cue_dur_range=(0.5, 0.8), motion_dur=5.0)
            used = res.get('prop_used', p_dec)
            track(res, used)
            conf = conf_prob = conf_rt = np.nan
            if res.get('resp_shape') != 'timeout':
                conf, conf_prob, conf_rt = wp3_confidence()
            log_row(1, 0, res, used, np.nan, conf, conf_prob, conf_rt, angle)

        # --- TASK 2: decision -> post-decision evidence -> confidence ---
        msg.text = ("Part B\n\n"
                    "Each trial now has two parts.\n"
                    "1) Move, then choose the circle you controlled (a = left, s = right).\n"
                    "2) You then get EXTRA EVIDENCE about that same trial: the same two\n"
                    "   circles, on the same sides, and the same one is still truly yours —\n"
                    "   but a NEW stretch of movement. Keep moving and watch.\n"
                    "   This second sample is as clear as the first, or CLEARER.\n"
                    "   It is bonus information — no response during it.\n\n"
                    "Then rate how likely it is that your FIRST choice was correct.\n\n"
                    "Press SPACE to start...")
        msg.draw(); win.flip(); wait_keys()
        levels = ['low'] * (t2_n // 2) + ['high'] * (t2_n - t2_n // 2)
        random.shuffle(levels)
        for lev in levels:
            trial_no += 1
            p_dec, p_high = next_props()
            blk['clipped'] = bool(p_high >= 0.899)   # high collapses onto low for this trial
            res = run_trial(trial_no, "wp3_task2", angle_bias=angle, expect_level="low",
                            mode="test", prop_override=p_dec, cue_dur_range=(0.5, 0.8), motion_dur=5.0)
            used = res.get('prop_used', p_dec)
            track(res, used)   # decision only; the evidence sample never feeds the staircase
            conf = conf_prob = conf_rt = np.nan
            post_prop = np.nan
            if res.get('resp_shape') != 'timeout':
                # low = exactly this trial's own decision strength; high = that +WP3_BOOST logit
                post_prop = used if lev == 'low' else p_high
                run_trial(trial_no, "wp3_evidence", angle_bias=angle, expect_level="low",
                          mode="test", prop_override=post_prop, target_shape=res['true_shape'],
                          left_shape=res['left_shape'],   # keep the decision trial's layout
                          applied_angle_override=res['applied_angle_bias'],  # ...and its ±90° sign
                          cue_dur_range=(0.3, 0.5), motion_dur=WP3_EV_DUR, accept_response=False)
                conf, conf_prob, conf_rt = wp3_confidence()
            log_row(2, 1 if lev == 'low' else 2, res, used, post_prop, conf, conf_prob, conf_rt, angle)

        if block_i < len(learning_order):
            show_break_screen(trial_no, trial_no, "this block")

    mean_score = float(np.mean(scores)) if scores else 0.0
    bonus_amount = round(WP3_BONUS * mean_score, 2)
    wp3_motivation_check()     # before the reveal, so the amount cannot bias it
    # One explicit summary row. These keys are deliberately NOT also put into expInfo:
    # a key present in both addData and extraInfo is written twice and pandas renames
    # the second copy 'name.1' (quiz/motivation live in expInfo already, so they reach
    # this row via extraInfo; mean score / bonus are addData-only).
    thisExp.addData('phase', 'wp3_summary')
    thisExp.addData('wp3_mean_score', round(mean_score, 4))
    thisExp.addData('wp3_bonus', bonus_amount)
    thisExp.nextEntry()
    _save()
    msg.text = (f"Done — thank you!\n\nYour confidence bonus: {wp3_bonus_text(mean_score)}\n\n"
                "Press SPACE to exit.")
    msg.draw(); win.flip(); wait_keys()


def generate_learning_trials(angle_bias, n_trials, low_color, high_color):
    """
    Generate n_trials learning trials for a given angle.
    Balanced easy/hard, shuffled randomly.
    Returns list of (cue_color, difficulty_type, prop_value) tuples.
    """
    s_hard, s_easy = learning_levels_by_angle[angle_bias]

    trials = []
    n_half = n_trials // 2
    n_remainder = n_trials - 2 * n_half

    for _ in range(n_half):
        trials.append((low_color, 'learning_fixed', s_hard))
        trials.append((high_color, 'learning_fixed', s_easy))
    # If odd number, add one more (alternating hard/easy)
    if n_remainder > 0:
        trials.append((low_color, 'learning_fixed', s_hard))

    rng.shuffle(trials)
    return trials


def run_learning_miniblock(angle_bias, trials, mini_block_num, mini_block_angle_num,
                           low_color, high_color, learning_trial_counter_for_angle):
    """
    Run a single learning mini-block: execute trials with feedback and log data.
    Returns the updated trial counter for this angle.
    """
    global global_trial_counter

    staircase = global_quest[f'{angle_bias}']
    # Logging only: record the staircase threshold under both legacy column names.
    # The 1u2d staircase targets 70.7%; we no longer estimate 60%/80% thresholds.
    s_hat_low = staircase.threshold_estimate()
    s_hat_high = staircase.threshold_estimate()

    for idx, (cue_color, difficulty_type, prop_value) in enumerate(trials, 1):
        learning_trial_counter_for_angle += 1
        global_trial_counter += 1
        expect_level = 'low' if cue_color == low_color else 'high'

        res = run_trial(
            learning_trial_counter_for_angle, "practice", angle_bias=angle_bias,
            expect_level=expect_level, mode=difficulty_type,
            prop_override=prop_value, cue_dur_range=(0.5, 0.8), motion_dur=5.0
        )
        used_prop = res.get('prop_used', prop_value)

        # Log trial data
        thisExp.addData('trial_num', global_trial_counter)
        thisExp.addData('participant', expInfo['participant'])
        thisExp.addData('session', expInfo['session'])
        thisExp.addData('phase', f'learning_{angle_bias}')
        thisExp.addData('mini_block_num', mini_block_num)
        thisExp.addData('mini_block_angle_num', mini_block_angle_num)
        thisExp.addData('cue_color', cue_color)
        thisExp.addData('cue_difficulty_prediction', 'high' if cue_color == high_color else 'low')
        thisExp.addData('difficulty_type', difficulty_type)
        thisExp.addData('actual_difficulty_level', 'easy' if cue_color == high_color else 'hard')
        thisExp.addData('prop_used', used_prop)
        thisExp.addData('stimulus_logit', logit(used_prop))
        thisExp.addData('threshold_source', 'individualized_calibration')
        thisExp.addData('accuracy', res.get('accuracy', 0))
        thisExp.addData('low_move_ratio', res.get('low_move_ratio', np.nan))
        thisExp.addData('is_timeout', res.get('resp_shape') == 'timeout')
        thisExp.addData('rt_choice', res.get('rt_choice', np.nan))
        thisExp.addData('early_response', res.get('early_response', False))
        thisExp.addData('true_shape', res.get('true_shape', ''))
        thisExp.addData('resp_shape', res.get('resp_shape', ''))
        thisExp.addData('true_side', res.get('true_side', ''))     # LEFT/RIGHT = the real answer
        thisExp.addData('resp_side', res.get('resp_side', ''))
        thisExp.addData('s_threshold_60pct', s_hat_low)
        thisExp.addData('s_threshold_80pct', s_hat_high)
        thisExp.addData('angle_bias', angle_bias)
        thisExp.addData('applied_angle_bias', res.get('applied_angle_bias', angle_bias))
        thisExp.addData('mean_evidence', res.get('mean_evidence', np.nan))
        thisExp.addData('sum_evidence', res.get('sum_evidence', np.nan))
        thisExp.addData('var_evidence', res.get('var_evidence', np.nan))
        thisExp.addData('rt_frame', res.get('rt_frame', np.nan))
        thisExp.addData('num_frames_preRT', res.get('num_frames_preRT', np.nan))
        thisExp.addData('mean_evidence_preRT', res.get('mean_evidence_preRT', np.nan))
        thisExp.addData('sum_evidence_preRT', res.get('sum_evidence_preRT', np.nan))
        thisExp.addData('var_evidence_preRT', res.get('var_evidence_preRT', np.nan))
        thisExp.addData('cum_evidence_preRT', res.get('cum_evidence_preRT', np.nan))
        thisExp.addData('max_cum_evidence_preRT', res.get('max_cum_evidence_preRT', np.nan))
        thisExp.addData('min_cum_evidence_preRT', res.get('min_cum_evidence_preRT', np.nan))
        thisExp.addData('max_abs_cum_evidence_preRT', res.get('max_abs_cum_evidence_preRT', np.nan))
        thisExp.addData('prop_positive_evidence_preRT', res.get('prop_positive_evidence_preRT', np.nan))
        thisExp.nextEntry()

    return learning_trial_counter_for_angle

def generate_test_trials(angle_bias, n_trials, low_color, high_color):
    """
    Generate n_trials test trials for a given angle.
    Maintains ~2/3 medium, ~1/3 learning-level ratio.
    Returns list of (cue_color, difficulty_type, prop_value) tuples.
    """
    s_hard, s_easy = learning_levels_by_angle[angle_bias]
    # Medium is the 70% threshold, centered between hard and easy by construction
    _, s_medium, _ = difficulty_levels_by_angle[angle_bias]

    # Split: ~2/3 medium, ~1/3 learning-level
    n_learning = n_trials // 3
    n_medium = n_trials - n_learning

    trials = []

    # Medium trials: split evenly between low and high cue colors
    n_med_low = n_medium // 2
    n_med_high = n_medium - n_med_low
    for _ in range(n_med_low):
        trials.append((low_color, 'test_medium', s_medium))
    for _ in range(n_med_high):
        trials.append((high_color, 'test_medium', s_medium))

    # Learning-level trials: hard with low cue, easy with high cue
    n_learn_hard = n_learning // 2
    n_learn_easy = n_learning - n_learn_hard
    for _ in range(n_learn_hard):
        trials.append((low_color, 'test_learning_hard', s_hard))
    for _ in range(n_learn_easy):
        trials.append((high_color, 'test_learning_easy', s_easy))

    rng.shuffle(trials)
    return trials


def run_test_miniblock(angle_bias, trials, mini_block_num, mini_block_angle_num,
                       low_color, high_color, test_trial_counter_for_angle):
    """
    Run a single test mini-block: execute trials with ratings, no feedback, and log data.
    Returns the updated trial counter for this angle.
    """
    global global_trial_counter

    s_hard, s_medium, s_easy = difficulty_levels_by_angle[angle_bias]
    staircase = global_quest[f'{angle_bias}']
    # Logging only: record the staircase threshold under both legacy column names.
    # The 1u2d staircase targets 70.7%; we no longer estimate 60%/80% thresholds.
    s_hat_low = staircase.threshold_estimate()
    s_hat_high = staircase.threshold_estimate()

    for idx, (cue_color, difficulty_type, prop_value) in enumerate(trials, 1):
        test_trial_counter_for_angle += 1
        global_trial_counter += 1
        expect_level = 'low' if cue_color == low_color else 'high'

        if TRACK_TEST:
            # Only medium is tracked; easy/hard are a symmetric offset from it.
            med_now = clamp_prop(staircase.threshold_estimate())
            if difficulty_type == 'test_medium':
                prop_value = staircase.next_stimulus()
            elif difficulty_type == 'test_learning_easy':
                prop_value = clamp_prop(inv_logit(logit(med_now) + TEST_OFFSET))
            elif difficulty_type == 'test_learning_hard':
                prop_value = clamp_prop(inv_logit(logit(med_now) - TEST_OFFSET))

        res = run_trial(
            test_trial_counter_for_angle, "test", angle_bias=angle_bias,
            expect_level=expect_level, mode=difficulty_type,
            prop_override=prop_value, cue_dur_range=(0.5, 0.8), motion_dur=5.0
        )
        used_prop = res.get('prop_used', prop_value)

        # Covert tracking update: adapt from objective correctness (timeouts
        # excluded, mirroring calibration). No feedback is shown to the participant.
        if TRACK_TEST and res.get('resp_shape') != 'timeout':
            # Only medium feeds back into its staircase; easy/hard ride the offset.
            if difficulty_type == 'test_medium':
                staircase.update(used_prop, int(res.get('accuracy', 0)))

        # Determine the actual difficulty level for logging
        if difficulty_type == 'test_medium':
            actual_difficulty = 'medium'
            target_percentage = '70pct'
        elif difficulty_type == 'test_learning_hard':
            actual_difficulty = 'hard'
            target_percentage = 'hard_offset'
        elif difficulty_type == 'test_learning_easy':
            actual_difficulty = 'easy'
            target_percentage = 'easy_offset'
        else:
            actual_difficulty = 'unknown'
            target_percentage = 'unknown'

        # Log trial data
        thisExp.addData('trial_num', global_trial_counter)
        thisExp.addData('participant', expInfo['participant'])
        thisExp.addData('session', expInfo['session'])
        thisExp.addData('phase', f'test_{angle_bias}')
        thisExp.addData('mini_block_num', mini_block_num)
        thisExp.addData('mini_block_angle_num', mini_block_angle_num)
        thisExp.addData('cue_color', cue_color)
        thisExp.addData('cue_difficulty_prediction', 'high' if cue_color == high_color else 'low')
        thisExp.addData('actual_difficulty_level', actual_difficulty)
        thisExp.addData('target_percentage', target_percentage)
        thisExp.addData('difficulty_type', difficulty_type)
        thisExp.addData('prop_used', used_prop)
        thisExp.addData('stimulus_logit', logit(used_prop))
        thisExp.addData('threshold_source', 'individualized_calibration')
        thisExp.addData('accuracy', res.get('accuracy', 0))
        thisExp.addData('low_move_ratio', res.get('low_move_ratio', np.nan))
        thisExp.addData('is_timeout', res.get('resp_shape') == 'timeout')
        thisExp.addData('rt_choice', res.get('rt_choice', np.nan))
        thisExp.addData('confidence_rating', res.get('confidence_rating', np.nan))
        thisExp.addData('agency_rating', res.get('agency_rating', np.nan))
        thisExp.addData('early_response', res.get('early_response', False))
        thisExp.addData('true_shape', res.get('true_shape', ''))
        thisExp.addData('resp_shape', res.get('resp_shape', ''))
        thisExp.addData('true_side', res.get('true_side', ''))     # LEFT/RIGHT = the real answer
        thisExp.addData('resp_side', res.get('resp_side', ''))
        thisExp.addData('s_threshold_60pct', s_hat_low)
        thisExp.addData('s_threshold_80pct', s_hat_high)
        thisExp.addData('s_threshold_70pct', s_medium)
        thisExp.addData('angle_bias', angle_bias)
        thisExp.addData('applied_angle_bias', res.get('applied_angle_bias', angle_bias))
        thisExp.addData('mean_evidence', res.get('mean_evidence', np.nan))
        thisExp.addData('sum_evidence', res.get('sum_evidence', np.nan))
        thisExp.addData('var_evidence', res.get('var_evidence', np.nan))
        thisExp.addData('rt_frame', res.get('rt_frame', np.nan))
        thisExp.addData('num_frames_preRT', res.get('num_frames_preRT', np.nan))
        thisExp.addData('mean_evidence_preRT', res.get('mean_evidence_preRT', np.nan))
        thisExp.addData('sum_evidence_preRT', res.get('sum_evidence_preRT', np.nan))
        thisExp.addData('var_evidence_preRT', res.get('var_evidence_preRT', np.nan))
        thisExp.addData('cum_evidence_preRT', res.get('cum_evidence_preRT', np.nan))
        thisExp.addData('max_cum_evidence_preRT', res.get('max_cum_evidence_preRT', np.nan))
        thisExp.addData('min_cum_evidence_preRT', res.get('min_cum_evidence_preRT', np.nan))
        thisExp.addData('max_abs_cum_evidence_preRT', res.get('max_abs_cum_evidence_preRT', np.nan))
        thisExp.addData('prop_positive_evidence_preRT', res.get('prop_positive_evidence_preRT', np.nan))
        thisExp.nextEntry()

    return test_trial_counter_for_angle

# ───────────────────────────────────────────────────────
#  Initial Instructions
# ───────────────────────────────────────────────────────

def show_initial_instructions():
    instructions = [
        # Page 1: Welcome and overview
        """Welcome to the study.

You will see two circles, one on the LEFT and one on the RIGHT.
Both move with your mouse — but you control one of them more
than the other.

Your task: decide which side (left or right) you control more.

The study has two parts with short breaks in between.
Total duration: approximately 60 minutes.

Press SPACE to continue...""",

        # Page 2: Response instructions
        """Response Keys:

Press A if you think you control the LEFT circle
Press S if you think you control the RIGHT circle

Please respond as quickly and accurately as possible.
If you are unsure, make your best guess.

You have up to 5 seconds to respond on each trial.

Press SPACE to begin..."""
    ]
    
    for instruction in instructions:
        msg.text = instruction
        msg.draw()
        win.flip()
        keys = wait_keys(['space', 'escape'])
        if 'escape' in keys:
            _save()
            core.quit()

def run_block_exploration(angle_bias, duration=EXPLORE_DUR):
    """One free-exploration trial at FULL control (prop=1.0) before each angle block.

    Why: the regularity strategy ("watch which shape covaries with me") works in BOTH
    angle conditions, so a participant who starts at 90° has no error signal pushing
    them to switch strategies at 0° — the dual-mode contrast would then be carried
    only by the mapping, not by the processing mode. At prop=1.0 the action-effect
    mapping is unmistakable, so this re-anchors it without a word about what changed.

    Deliberately neutral: identical text and duration before BOTH blocks, so it can
    never itself signal that something is different; nothing about control strength
    (the dependent variable) and nothing about the colour cues; no decision, no
    feedback, no ratings — the participant only watches.
    ponytail: reuses run_trial's catch_type='full' + accept_response=False path.
    """
    msg.text = ("Warm-up\n\n"
                "Two circles will appear and start moving as soon as you move the mouse.\n\n"
                "Move the mouse freely and take a moment to see how the circles\n"
                "move in relation to your hand.\n\n"
                "There is nothing to decide here — just watch.\n\n"
                "Press SPACE to begin...")
    msg.draw(); win.flip()
    keys = wait_keys(['space', 'escape'])
    if keys and 'escape' in keys:
        _save(); core.quit()
    run_trial(0, "explore", angle_bias=angle_bias, expect_level="none", mode="explore",
              catch_type="full", cue_color_override="black",
              cue_dur_range=(0.5, 0.8), motion_dur=duration, accept_response=False)


def run_fixed_test():
    """Fixed-prop probe (no staircase): FIXED_N_MED medium + easy + hard trials per
    angle at the given props, interleaved, no feedback/ratings. Reports medium
    accuracy per angle — checks whether the calibrated medium still ~= 70%."""
    # Black stimuli + black fixation, exactly like the calibration in _99_23.
    # run_trial colours fixation AND shapes by the cue; without this they'd take the
    # placeholder grey low_col → grey cross + grey shapes on grey bg (invisible).
    global low_col, high_col
    low_col = high_col = "black"
    # Truthful difficulty colour-coding for this validation run (NOT the real
    # expectation cue — here the colour tells the truth so you can judge the feel).
    DIFF_COLOR = {'easy': 'green', 'medium': 'blue', 'hard': 'red'}
    msg.text = (f"Fixed-difficulty check — colours show the TRUE difficulty:\n"
                f"   GREEN = easy    BLUE = medium    RED = hard\n\n"
                f"Medium props: 0 deg = {FIXED_MED[0]:.3f},  90 deg = {FIXED_MED[90]:.3f}\n"
                f"{FIXED_N_MED} medium + {FIXED_N_EASY} easy + {FIXED_N_HARD} hard per angle, no feedback.\n\n"
                f"a = left, s = right. Keep moving.\n\nPress SPACE to start...")
    msg.draw(); win.flip(); wait_keys()

    trials = []
    for ang in (0, 90):
        # easy/hard from the logit-offset (difficulty_levels_by_angle) if a calibration
        # ran this session; else fall back to the legacy fixed props.
        if ang in difficulty_levels_by_angle:
            s_hard, _, s_easy = difficulty_levels_by_angle[ang]
        else:
            # no calibration this session: derive easy/hard from the medium prop via
            # the same logit-offset the real design uses (not the legacy 0.85/0.10).
            ml = logit(FIXED_MED[ang])
            s_easy = clamp_prop(inv_logit(ml + DELTA_LOGIT))
            s_hard = clamp_prop(inv_logit(ml - DELTA_LOGIT))
        trials += [(ang, 'medium', FIXED_MED[ang])] * FIXED_N_MED
        trials += [(ang, 'easy', s_easy)] * FIXED_N_EASY
        trials += [(ang, 'hard', s_hard)] * FIXED_N_HARD
    order = rng.permutation(len(trials))

    out = subjects_dir / f"fixed_test_{expInfo['participant']}.csv"
    j = 1
    while out.exists():
        out = subjects_dir / f"fixed_test_{expInfo['participant']}_{j}.csv"; j += 1

    rows = []
    for i, idx in enumerate(order, 1):
        ang, diff, prop = trials[int(idx)]
        res = run_trial(i, "fixedtest", angle_bias=ang, expect_level="low", mode="test",
                        prop_override=prop, cue_dur_range=(0.5, 0.8), motion_dur=5.0,
                        cue_color_override=DIFF_COLOR[diff])
        rows.append(dict(trial=i, angle=ang, difficulty=diff, prop=prop,
                         accuracy=res.get('accuracy'),
                         is_timeout=(res.get('resp_shape') == 'timeout'),
                         low_move_ratio=res.get('low_move_ratio'), rt=res.get('rt_choice')))
        pd.DataFrame(rows).to_csv(out, index=False)  # incremental: keep partial data if closed early
        # brief feedback
        if res.get('resp_shape') == 'timeout':
            msg.text = "Zeit abgelaufen"; msg.color = 'orange'
        elif res.get('accuracy') == 1:
            msg.text = "Richtig ✓"; msg.color = 'green'
        else:
            msg.text = "Falsch ✗"; msg.color = 'red'
        msg.draw(); win.flip(); core.wait(0.6)
        msg.color = 'black'

    df = pd.DataFrame(rows)

    print("\n=== FIXED-PROP TEST RESULT (medium should be ~0.707) ===")
    for ang in (0, 90):
        v = df[(df.angle == ang) & (~df.is_timeout)]
        for diff in ('medium', 'easy', 'hard'):
            s = v[v.difficulty == diff]
            tag = "  <-- target ~0.707" if diff == 'medium' else ""
            print(f"  {ang:>2} deg {diff:>6} (prop={s['prop'].iloc[0]:.3f} n={len(s)}): acc={s['accuracy'].mean():.3f}{tag}")
    print(f"Saved {out}")
    msg.text = "Done — thank you!\n\n(results printed to the console)\n\nPress SPACE to exit."
    msg.draw(); win.flip(); wait_keys()


# ───────────────────────────────────────────────────────
#  Main Experiment - Block-wise Design
# ───────────────────────────────────────────────────────

if CAL_THEN_FIXED:
    # Fresh calibration (exact _99_23 params), then the fixed block at the derived props.
    initialize_global_quest()
    msg.text = ("Part 1: calibration (with feedback, black shapes).\n"
                "Part 2: a short fixed-difficulty check (no feedback).\n\n"
                "a = left, s = right. Keep moving.\n\nPress SPACE to start...")
    msg.draw(); win.flip(); wait_keys()
    low_col, high_col = "black", "black"
    run_calibration_both_angles(
        max_trials_per_staircase=120, min_trials_per_staircase=40, required_reversals=15,
    )
    compute_difficulty_levels_for_angle(0)
    compute_difficulty_levels_for_angle(90)
    FIXED_MED[0] = difficulty_levels_by_angle[0][1]
    FIXED_MED[90] = difficulty_levels_by_angle[90][1]
    print(f"\n=== FRESH MEDIUM PROPS (this session) ===")
    print(f"  0 deg = {FIXED_MED[0]:.3f}   90 deg = {FIXED_MED[90]:.3f}")
    run_fixed_test()
    win.close(); core.quit()

if FIXED_TEST:
    run_fixed_test()
    win.close(); core.quit()

if MOCS_MODE:
    # Diagnostic: measure the full psychometric curve per angle, fit, report, quit.
    run_mocs_block()  # closes window + quits internally

if FEEL_MODE:
    # Self-demo of the three difficulty levels at the current MOCS-fit props.
    run_feel_test(); win.close(); core.quit()

if TESTONLY_MODE:
    # Quick self-run of the real test phase (cues, ratings, no feedback, tracking).
    run_test_only(); win.close(); core.quit()

if WP3_MODE:
    # WP3: Rollwage post-decision evidence paradigm (no cues, medium only).
    run_wp3()
    win.close(); core.quit()

# Show initial instructions
show_initial_instructions()

# Demo trial removed as requested

if USE_QUEST_TRAINING:
    # Initialize global 4-staircase system
    initialize_global_quest()
    
    # EXPERIMENT STRUCTURE (mini-block interleaved design):
    # Phase 1: Calibration (both 0 deg and 90 deg interleaved, QUEST+)
    # Phase 2: Learning (mini-blocks alternating angle A/B, easy+hard trials, colored cues, feedback)
    # Phase 3: Test (mini-blocks alternating angle A/B, medium+easy+hard trials, colored cues, no feedback, ratings)

    # === PHASE 1: CALIBRATION ===
    low_col, high_col = "black", "black"
    first_angle, second_angle = learning_order[0], learning_order[1]

    if PERBLOCK_CAL or QUEST_CAL:
        # PER-BLOCK design: no up-front calibration. Each angle is calibrated right
        # before its own block (in the block loop below) — anchors medium at the
        # current skill in both blocks (kills cross-block drift) and matches the
        # blocked test context. PERBLOCK_CAL = 1u2d for medium + fixed easy/hard.
        print("Per-block calibration: each angle calibrated right before its block")
    else:
        msg.text = ("Warm-up\n\nYou will practice deciding which side you control.\n"
                    "You will receive feedback after each response.\n\nPress SPACE to start...")
        msg.draw(); win.flip(); wait_keys()

    if PERBLOCK_CAL or QUEST_CAL:
        pass  # calibration happens per-block below
    elif STAIRCASE_ONLY:
        # Long run so the staircase can fully converge on 70.7%.
        run_calibration_both_angles(
            max_trials_per_staircase=120, min_trials_per_staircase=40, required_reversals=15,
        )
        compute_difficulty_levels_for_angle(first_angle)
        compute_difficulty_levels_for_angle(second_angle)
    else:
        run_calibration_both_angles(
            max_trials_per_staircase=CHECK_CALIBRATION_TRIALS + 20 if not CHECK_MODE else CHECK_CALIBRATION_TRIALS,
            min_trials_per_staircase=CHECK_CALIBRATION_TRIALS,
        )
        compute_difficulty_levels_for_angle(first_angle)
        compute_difficulty_levels_for_angle(second_angle)

    if STAIRCASE_ONLY:
        m1 = difficulty_levels_by_angle[first_angle][1]
        m2 = difficulty_levels_by_angle[second_angle][1]
        print("\n=== STAIRCASE-ONLY RESULT (medium = 70.7% threshold) ===")
        print(f"Medium prop {first_angle} deg = {m1:.4f}")
        print(f"Medium prop {second_angle} deg = {m2:.4f}")
        msg.text = (f"Staircase done.\n\nMedium (70.7%) prop:\n"
                    f"  {first_angle} deg:   {m1:.3f}\n"
                    f"  {second_angle} deg:   {m2:.3f}\n\n"
                    f"(also printed to the console)\n\nPress SPACE to exit.")
        msg.draw(); win.flip(); wait_keys()
        win.close(); core.quit()

    # Map angles to their color palettes
    palette_for_angle = {
        first_angle: PALETTE_FOR_FIRST_ANGLE,
        second_angle: PALETTE_FOR_SECOND_ANGLE,
    }

    # BLOCKED DESIGN (angles NOT interleaved per trial — by request, overriding the
    # Wen-2023 interleaving requirement). One shared interleaved calibration above,
    # then each angle gets its OWN self-contained block: learning (colored cues,
    # feedback) immediately followed by test (ratings, no feedback). Order of the
    # two angle blocks is counterbalanced across participants via learning_order.
    # ponytail: no re-calibration between blocks — user chose a single calibration.
    #   The 2nd angle's medium may drift above 70% (skill improves); if the data
    #   show that, add a short per-angle top-up staircase before each test loop.

    # 30-second transition: Calibration -> first angle block. Skipped for per-block
    # calibration, which is done inside the loop (no up-front calibration).
    if not (PERBLOCK_CAL or QUEST_CAL):
        show_phase_transition(
            completed_block=1,
            next_block_info="In the next part, the circles will appear in different colors."
            + ("\nYou will receive feedback after each response." if LEARNING_FEEDBACK else "\nThere is no feedback from here on.")
            + "\n\nPress SPACE when you are ready to continue.",
            rest_duration=30
        )

    _blocks = (learning_order if not ONLY_BLOCK
               else [learning_order[ONLY_BLOCK - 1]])
    if ONLY_BLOCK:
        print(f"*** ONLY BLOCK {ONLY_BLOCK} ({_blocks[0]} deg) - split session ***")
    for block_i, angle in enumerate(_blocks, ONLY_BLOCK or 1):
        low_col, high_col = palette_for_angle[angle]
        print(f"\n=== ANGLE BLOCK {block_i}/2: {angle} deg "
              f"(colors low/high = {low_col}/{high_col}) ===")

        # Full-control exploration, identically before BOTH blocks, so the current
        # action-effect mapping is re-anchored rather than carried over from block 1.
        run_block_exploration(angle)

        # --- PER-BLOCK CALIBRATION: calibrate THIS angle now, at current skill, in its
        # own blocked context. PERBLOCK_CAL = 1u2d for medium + fixed easy/hard (the
        # decided design); QUEST_CAL = optional MOCS-seeded alternative.
        if PERBLOCK_CAL or QUEST_CAL:
            msg.text = (f"Part {block_i} of 2\n\nWarm-up\n\n"
                        "Two plain circles. Decide which side you control, with feedback.\n"
                        "a = left, s = right. Keep the mouse moving.\n\nPress SPACE to start...")
            msg.draw(); win.flip(); wait_keys()
            if QUEST_CAL:
                run_quest_calibration_from_mocs(angles=[angle],
                                                n_per_angle=3 if CHECK_MODE else QUEST_N)
            else:
                low_col, high_col = "black", "black"   # calibration uses black shapes
                run_calibration_both_angles(
                    max_trials_per_staircase=80 if not CHECK_MODE else CHECK_CALIBRATION_TRIALS,
                    min_trials_per_staircase=40 if not CHECK_MODE else CHECK_CALIBRATION_TRIALS,
                    required_reversals=12, angle_keys=(str(angle),))
                compute_difficulty_levels_for_angle(angle)
                low_col, high_col = palette_for_angle[angle]   # restore for learning
            show_phase_transition(
                completed_block=block_i,
                next_block_info=f"Part {block_i} of 2 — Training\n\nThe circles will now appear in different colors."
                + ("\nYou will receive feedback after each response." if LEARNING_FEEDBACK else "\nThere is no feedback from here on.")
                + "\n\nPress SPACE when you are ready to continue.",
                rest_duration=10
            )

        # --- LEARNING (this angle only: easy+hard, colored cues, feedback) ---
        print(f"  Learning: {LEARNING_MINIBLOCKS_PER_ANGLE} mini-blocks x "
              f"{LEARNING_TRIALS_PER_MINIBLOCK} trials")
        # ponytail: no breaks within learning (by request) — run mini-blocks back-to-back
        learn_counter = 0
        for mb in range(1, LEARNING_MINIBLOCKS_PER_ANGLE + 1):
            trials = generate_learning_trials(
                angle, LEARNING_TRIALS_PER_MINIBLOCK, low_col, high_col)
            learn_counter = run_learning_miniblock(
                angle, trials, mb, mb, low_col, high_col, learn_counter)

        # --- Learning -> Test transition (ratings intro) ---
        show_phase_transition(
            completed_block=block_i,
            next_block_info=f"Part {block_i} of 2 — Main rounds\n\nAfter each response you will also rate your confidence\nand your sense of control.\n\nTry to use the full range of each scale.\nThere is no feedback.",
            rest_duration=30
        )

        # --- TEST (this angle only: medium+easy+hard, cues, no feedback, ratings) ---
        print(f"  Test: {TEST_MINIBLOCKS_PER_ANGLE} mini-blocks x "
              f"{TEST_TRIALS_PER_MINIBLOCK} trials")
        test_counter = 0
        test_done = 0
        for mb in range(1, TEST_MINIBLOCKS_PER_ANGLE + 1):
            trials = generate_test_trials(
                angle, TEST_TRIALS_PER_MINIBLOCK, low_col, high_col)
            test_counter = run_test_miniblock(
                angle, trials, mb, mb, low_col, high_col, test_counter)
            test_done += len(trials)
            if mb < TEST_MINIBLOCKS_PER_ANGLE:
                # neutral label — must NOT reveal the angle/condition to the participant
                show_break_screen(test_done, TEST_TOTAL_PER_ANGLE, "this block")

        # Rest between the two angle blocks (not after the last)
        if block_i < len(learning_order):
            show_phase_transition(
                completed_block=block_i,
                # Neutral by design: the old text ("works the same way, with different
                # colors") actively told participants nothing but the colours changed,
                # which discourages re-exploring the mapping at the start of block 2.
                # Says nothing about what is or is not different.
                next_block_info="Part 1 of 2 complete!\n\nPart 2 will begin with a warm-up.\nTake a rest before continuing.",
                rest_duration=30
            )

    # Final trajectory usage report (internal logging only)
    final_used = len(used_trajectory_indices)
    primary_total = len(universal_trajectory_set_primary)
    overflow_total = len(universal_trajectory_set_overflow)
    used_primary = len([i for i in used_trajectory_indices if i in set(universal_trajectory_set_primary)])
    used_overflow = len([i for i in used_trajectory_indices if i in set(universal_trajectory_set_overflow)])
    total_available = primary_total + overflow_total if (primary_total or overflow_total) else len(universal_trajectory_set)
    usage_percentage = (final_used / max(1, total_available)) * 100
    
    # Final QUEST convergence summary (logged to data file only, not shown to participant)

    # All reports logged to data file only - no output shown to participant
    
    # End screen
    msg.text = """Experiment Complete

Thank you for participating!
Your responses have been saved.

Press SPACE to exit."""
    msg.draw(); win.flip(); wait_keys()
    win.close(); core.quit()
