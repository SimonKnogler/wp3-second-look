"""1-up-2-down transformed staircase (Levitt 1971), converging on 70.7% correct.

Extracted from CDT_windows_blockwise_fast_response.py so the convergence
simulation (simulate_staircase.py) drives the EXACT same logic the experiment
runs — no drifting copy. Pure numpy, no PsychoPy.
"""
import numpy as np


class TwoDownOneUpStaircase:
    """
    Classical 1-up 2-down transformed staircase (Levitt, 1971). Converges on the
    70.7% correct threshold.

    Step sizes operate in prop_used space. Two correct in a row → decrease prop
    (make harder). One wrong → increase prop (make easier). Reversals are the
    points where the direction changes. After a set number of reversals, the
    threshold is estimated as the mean of the last N reversal props, and its
    uncertainty as the SD of those reversals.
    """
    def __init__(self,
                 start_prop=0.85,   # start EASY (lots of control), descend to ~70.7%
                 step_large=0.10,
                 step_small=0.05,
                 reversals_before_small_step=3,
                 min_prop=0.02,
                 max_prop=0.90,
                 reversals_for_threshold=8):
        self.current_prop = float(np.clip(start_prop, min_prop, max_prop))
        self.step_large = step_large
        self.step_small = step_small
        self.reversals_before_small_step = reversals_before_small_step
        self.min_prop = min_prop
        self.max_prop = max_prop
        self.reversals_for_threshold = reversals_for_threshold

        self.n_correct_in_row = 0
        self.last_direction = 0  # +1 = just went up (easier), -1 = just went down (harder)
        self.reversal_props = []  # prop_used values at each reversal
        self.trial_history = []  # list of (prop, correct)

    @property
    def current_step(self):
        return self.step_small if len(self.reversal_props) >= self.reversals_before_small_step else self.step_large

    @property
    def n_reversals(self):
        return len(self.reversal_props)

    def next_stimulus(self):
        """Return the prop_used for the upcoming trial."""
        return float(self.current_prop)

    def update(self, stimulus_prop, correct):
        """Update internal state after observing a response."""
        self.trial_history.append((float(stimulus_prop), int(bool(correct))))

        direction = 0
        if correct:
            self.n_correct_in_row += 1
            if self.n_correct_in_row >= 2:
                # Step down (harder) after 2 correct in a row
                new_prop = max(self.current_prop - self.current_step, self.min_prop)
                direction = -1
                self.n_correct_in_row = 0
                self.current_prop = new_prop
        else:
            # Any single error → step up (easier)
            new_prop = min(self.current_prop + self.current_step, self.max_prop)
            direction = +1
            self.n_correct_in_row = 0
            self.current_prop = new_prop

        # Detect a reversal: direction flipped from previous non-zero direction
        if direction != 0 and self.last_direction != 0 and direction != self.last_direction:
            self.reversal_props.append(float(self.current_prop))
        if direction != 0:
            self.last_direction = direction

    def threshold_estimate(self):
        """Mean of the last reversals_for_threshold reversal props. Falls back to
        the current level if there are no reversals yet (e.g. a very short
        CHECK_MODE calibration or a non-converged staircase), so difficulty never
        propagates as NaN into the trials."""
        if len(self.reversal_props) == 0:
            return float(self.current_prop)
        tail = self.reversal_props[-self.reversals_for_threshold:]
        return float(np.mean(tail))

    def threshold_sd(self):
        """SD of the last reversals_for_threshold reversal props. NaN if fewer than 2."""
        tail = self.reversal_props[-self.reversals_for_threshold:]
        if len(tail) < 2:
            return float('nan')
        return float(np.std(tail, ddof=1))

    def has_converged(self, required_reversals=8):
        return self.n_reversals >= required_reversals


class WeightedUpDownStaircase:
    """
    Weighted up-down staircase (Kaernbach, 1991). Converges on
    p_correct = step_up / (step_up + step_down); for a 90% target the
    up-step is 9x the down-step. Steps operate in prop_used space, like
    TwoDownOneUpStaircase. Used to covertly track the easy level during
    the (no-feedback) test phase, where fixed logit offsets overshoot
    into ceiling.
    """
    def __init__(self, start_prop, target_pcorr=0.90, step_down=0.03,
                 min_prop=0.02, max_prop=0.90):
        self.current_prop = float(np.clip(start_prop, min_prop, max_prop))
        self.step_down = step_down
        self.step_up = step_down * target_pcorr / (1.0 - target_pcorr)
        self.min_prop = min_prop
        self.max_prop = max_prop
        self.trial_history = []  # list of (prop, correct)

    def next_stimulus(self):
        return float(self.current_prop)

    def update(self, stimulus_prop, correct):
        self.trial_history.append((float(stimulus_prop), int(bool(correct))))
        if correct:
            self.current_prop = max(self.current_prop - self.step_down, self.min_prop)
        else:
            self.current_prop = min(self.current_prop + self.step_up, self.max_prop)
