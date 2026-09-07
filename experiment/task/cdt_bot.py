"""Live bot for the CDT: plays the REAL experiment end-to-end.

Activated with CDT_BOT=1. Installs itself into PsychoPy's input layer
(event.Mouse / event.getKeys / event.waitKeys), so the full experiment runs
unchanged — real rendering, real motion blending, real staircases, real
kinematics logging — only mouse and keys come from a synthetic human.

Human model (same family as simulate_participants.py):
- mouse: Ornstein-Uhlenbeck velocity + direction wander + speed bursts,
  brief pauses, tremor — bounded around screen centre
- choice: psychometric observer (per-angle alpha/sigma/lapse + practice),
  RT from shifted lognormal (harder -> slower, errors slower), timeouts
- ratings 1-4 / 1-7 with individual cutpoints

BUILT-IN HYPOTHESES (what the data should show afterwards):
  H1  cue shifts agency+confidence on identical medium trials, accuracy flat
  H2  INTERACTION: the cue effect is LARGER at 90 deg than at 0 deg —
      the regularity process (90) is metacognitively accessible, so the
      conscious expectation can bias its read-out; prediction (0) is largely
      unconscious and resists the cue  (delta_90 >> delta_0)
  H3  metacognitive sensitivity (type-2) higher at 90 than 0
      (meta_eff multiplied by META_MULT_90 at 90 deg)

Usage:  CDT_BOT=1 CDT_BOT_SEED=7 CDT_PARTICIPANT=97 ... python CDT_windows_...py
"""
import os
import math
import numpy as np
from psychopy import core

# ── true effect sizes (latent units) — the hypotheses to be recovered ──
DELTA_AGENCY = {0: 0.08, 90: 0.45}   # H1 + H2: cue -> agency, much larger at 90
DELTA_CONF = {0: 0.04, 90: 0.22}     # H1 + H2 for confidence
META_MULT_90 = 1.55                  # H3: better metacognitive access at 90


class _HumanMouse:
    """Human-like 2D trajectory: OU velocity, wandering heading, bursts/pauses."""

    def __init__(self, rng):
        self.rng = rng
        self.pos = np.zeros(2)
        self.vel = np.zeros(2)
        self.heading = rng.uniform(0, 2 * np.pi)
        self.speed_env = 6.0
        self.pause = 0

    def step(self):
        r = self.rng
        if self.pause > 0:                      # brief hesitations
            self.pause -= 1
            self.pos += r.normal(0, 0.15, 2)    # tremor only
            return self.pos.copy()
        if r.random() < 0.004:
            self.pause = r.integers(3, 20)
        if r.random() < 0.03:                   # new movement burst
            self.speed_env = float(np.clip(r.normal(7, 3), 2.0, 14.0))
        self.heading += r.normal(0, 0.25)       # wandering direction
        target_v = self.speed_env * np.array([math.cos(self.heading), math.sin(self.heading)])
        self.vel = 0.82 * self.vel + 0.18 * target_v + r.normal(0, 0.6, 2)
        self.pos += self.vel + r.normal(0, 0.2, 2)
        # soft confinement so the trajectory stays plausible
        for k in (0, 1):
            lim = 320 if k == 0 else 240
            if abs(self.pos[k]) > lim:
                self.heading = math.atan2(-self.pos[1], -self.pos[0]) + r.normal(0, 0.4)
                self.pos[k] = np.sign(self.pos[k]) * lim
        return self.pos.copy()


class Bot:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        r = self.rng
        # observer parameters (one synthetic participant)
        self.alpha = {0: float(np.clip(r.normal(0.30, 0.05), 0.20, 0.42))}
        self.alpha[90] = self.alpha[0] + float(abs(r.normal(0.05, 0.03)))
        self.sigma = float(np.clip(r.normal(0.13, 0.03), 0.08, 0.20))
        self.lapse = float(np.clip(r.beta(2, 60), 0.005, 0.07))
        self.kappa = float(r.uniform(0.05, 0.15))
        self.t0 = float(r.uniform(0.35, 0.60))
        self.mu_rt = float(r.normal(0.62, 0.10))
        self.s_rt = float(r.uniform(0.30, 0.40))
        self.meta_eff = float(np.clip(r.normal(0.85, 0.15), 0.4, 1.3))
        self.agency_gain = float(r.uniform(0.6, 1.0))
        self.bias = float(r.normal(0, 0.3))
        self.scale_use = float(r.uniform(0.85, 1.2))
        self.mouse_model = _HumanMouse(r)
        # trial state
        self.trials_done = 0
        self.plan = None            # dict for the current trial
        self.rt_clock_start = None  # first poll of the choice context
        self.screen_t0 = {}         # first-poll time per rating/space context
        print(f"[BOT] observer: alpha0={self.alpha[0]:.3f} alpha90={self.alpha[90]:.3f} "
              f"sigma={self.sigma:.3f} | H2 deltas agency {DELTA_AGENCY}, conf {DELTA_CONF}, "
              f"meta x{META_MULT_90} at 90")

    # ── observer model ──
    def _alpha_eff(self, angle):
        practice = 1 - self.kappa * (1 - math.exp(-self.trials_done / 250))
        return self.alpha[angle] * practice

    def _p_correct(self, prop, angle):
        F = 0.5 * (1 + math.erf((prop - self._alpha_eff(angle)) / (self.sigma * math.sqrt(2))))
        return 0.5 + 0.5 * (1 - self.lapse) * F

    def plan_trial(self, phase, prop, angle, expect_level, target, left_shape):
        r = self.rng
        pc = self._p_correct(prop, angle)
        correct = r.random() < pc
        mu = self.mu_rt + 0.60 * (1 - pc) + (0.12 if not correct else 0.0) \
            + 0.0002 * self.trials_done + r.normal(0, 0.10)
        rt = self.t0 + float(r.lognormal(mu, self.s_rt))
        correct_key = 'a' if target == left_shape else 's'
        wrong_key = 's' if correct_key == 'a' else 'a'
        cue_high = expect_level == 'high'
        # ratings with the built-in interaction (H2) + meta access (H3)
        z = float(np.clip((prop - self._alpha_eff(angle)) / self.sigma, -3, 3))
        # meta scales the correctness signal (drives type-2 sensitivity, H3)
        meta = self.meta_eff * (META_MULT_90 if angle == 90 else 1.0)
        felt = 0.6 * z + meta * (0.55 if correct else -0.40) + r.normal(0, 0.5)
        conf_lat = self.bias + 0.75 * felt \
            + (DELTA_CONF[angle] if cue_high else 0.0) + r.normal(0, 1)
        agn_lat = self.bias + self.agency_gain * z + 0.45 * correct \
            + (DELTA_AGENCY[angle] if cue_high else 0.0) + r.normal(0, 1)
        cc = np.sort(np.array([-0.9, 0.0, 0.9]) * self.scale_use + r.normal(0, 0.05, 3))
        ca = np.sort(np.array([-1.9, -1.1, -0.37, 0.37, 1.1, 1.9]) * self.scale_use
                     + r.normal(0, 0.05, 6))
        self.plan = dict(
            key=correct_key if correct else wrong_key,
            rt=rt, timeout=rt >= 4.90,
            conf=str(int(1 + np.sum(conf_lat > cc))),
            agency=str(int(1 + np.sum(agn_lat > ca))),
            answered=False,
        )
        self.rt_clock_start = None
        self.screen_t0 = {}
        self.trials_done += 1

    # ── input layer ──
    def get_keys(self, key_list, time_stamped):
        now = core.getTime()
        kl = set(key_list or [])
        if 'a' in kl and 's' in kl:                       # choice during motion
            p = self.plan
            if p is None or p['answered'] or p['timeout']:
                return []
            if self.rt_clock_start is None:
                self.rt_clock_start = now
            if now - self.rt_clock_start >= p['rt']:
                p['answered'] = True
                return [(p['key'], now)] if time_stamped else [p['key']]
            return []
        if '4' in kl and '5' not in kl:                   # confidence 1-4
            return self._delayed('conf', now, 0.5, 1.6)
        if '7' in kl:                                     # agency 1-7
            return self._delayed('agency', now, 0.5, 1.6)
        return []

    def _delayed(self, which, now, lo, hi):
        if self.plan is None or self.plan['timeout']:
            return []
        key = f"{which}_{self.trials_done}"
        if key not in self.screen_t0:
            self.screen_t0[key] = (now, float(self.rng.uniform(lo, hi)))
            return []
        t0, delay = self.screen_t0[key]
        return [self.plan[which]] if now - t0 >= delay else []

    def wait_keys(self, key_list):
        core.wait(float(self.rng.uniform(0.8, 1.8)))      # "reads" the screen
        kl = key_list or ['space']
        return ['space' if 'space' in kl else kl[0]]


BOT = None


class BotMouse:
    """Drop-in replacement ONLY for the trial mouse in run_trial (we must not
    replace event.Mouse globally — PsychoPy internals subclass/instantiate it)."""

    def __init__(self, *a, **k):
        pass

    def getPos(self):
        return tuple(BOT.mouse_model.step())

    def setPos(self, pos=(0, 0)):
        BOT.mouse_model.pos = np.array(pos, dtype=float)

    def setVisible(self, v):
        pass


def install(event_module, seed=None):
    """Monkeypatch psychopy.event.getKeys/waitKeys so the bot supplies keys."""
    global BOT
    BOT = Bot(int(seed if seed is not None else os.environ.get("CDT_BOT_SEED", "1")))

    real_get = event_module.getKeys

    def bot_getKeys(keyList=None, timeStamped=False, **kw):
        real = real_get(keyList=['escape'])               # human can still abort
        if real:
            return [('escape', core.getTime())] if timeStamped else ['escape']
        return BOT.get_keys(keyList, timeStamped)

    def bot_waitKeys(keyList=None, **kw):
        return BOT.wait_keys(keyList)

    event_module.getKeys = bot_getKeys
    event_module.waitKeys = bot_waitKeys
    print("[BOT] installed — experiment will play itself")
