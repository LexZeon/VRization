"""Original, dependency-free adaptive filtering of accepted angular increments.

Algorithm: Casiez, Roussel and Vogel, "1€ Filter", CHI 2012,
https://doi.org/10.1145/2207676.2208639 and https://gery.casiez.net/1euro/ .
Reference inspected (no source copied): Nicolas Roussel and Géry Casiez,
OneEuroFilter Python 0.2.1, commit d78925584245597f2aa9c4c01a802eb0f0b77fb9.
Reference source copyright 2019 Inria; its BSD-3-Clause LICENSE copyright
2023 Inria (BSD-3-Clause license):
https://github.com/casiez/OneEuroFilter/blob/d78925584245597f2aa9c4c01a802eb0f0b77fb9/python/LICENSE
This implementation is covered by VRization's MIT license.

No timers, threads, mouse APIs or pending outputs. The caller checks raw
sensor spikes and unwraps angles BEFORE calling step, and resets on any
input/session/focus boundary. State uses a bounded lag rather than an
ever-growing absolute yaw, so crossing +/-pi needs no special filter path.
"""

import math


class PoseStabilizer:
    """One-Euro-style two-axis filter using radians and monotonic seconds.

    Strength 0 bypasses filtering. Positive strength s sets the minimum
    cutoff to 3/s² Hz, beta to 15 Hz/(rad/s), and derivative cutoff to 5 Hz.
    Thus .5 uses 12 Hz at rest and 1 uses 3 Hz; movement raises the cutoff.
    No deadzone removes deliberate slow motion. Calls more than .5 seconds
    apart, non-increasing timestamps, or an unseeded filter establish a new
    baseline and produce no movement. Invalid arguments leave state intact.
    """

    MIN_CUTOFF = 3.0
    BETA = 15.0
    DERIVATIVE_CUTOFF = 5.0
    MAX_INTERVAL = 0.5

    def __init__(self, strength: float = 0.0):
        self._strength = 0.0
        self.reset()
        self.configure(strength)

    @staticmethod
    def _finite(value: float) -> bool:
        if type(value) not in (int, float):
            return False
        try:
            return math.isfinite(value)
        except OverflowError:
            return False

    @property
    def strength(self) -> float:
        return self._strength

    def configure(self, strength: float) -> bool:
        if not self._finite(strength) or not 0 <= strength <= 1:
            raise ValueError("stabilization must be finite and within 0..1")
        changed = strength != self._strength
        if changed:
            self._strength = float(strength)
            self.reset()
        return changed

    def reset(self, timestamp: float | None = None) -> None:
        if timestamp is not None and (not self._finite(timestamp) or timestamp < 0):
            raise ValueError("timestamp must be finite and nonnegative")
        self._timestamp = timestamp
        self._lag = (0.0, 0.0)
        self._derivative = (0.0, 0.0)

    def discard_lag(self, *, yaw: bool = False, pitch: bool = False) -> None:
        """Drop only clipped axes so an output cap cannot create mouse debt."""
        if type(yaw) is not bool or type(pitch) is not bool:
            raise ValueError("axis flags must be boolean")
        self._lag = tuple(0.0 if drop else value for drop, value in zip((yaw, pitch), self._lag))
        self._derivative = tuple(0.0 if drop else value for drop, value in zip((yaw, pitch), self._derivative))

    def step(self, yaw_delta: float, pitch_delta: float, timestamp: float) -> tuple[float, float]:
        if not self._finite(timestamp) or timestamp < 0:
            raise ValueError("timestamp must be finite and nonnegative")
        if any(not self._finite(x) or abs(x) > math.pi for x in (yaw_delta, pitch_delta)):
            raise ValueError("angular increments must be finite and within +/-pi")
        if self._strength == 0:
            self.reset(timestamp)
            return yaw_delta, pitch_delta
        dt = None if self._timestamp is None else timestamp - self._timestamp
        if dt is None or not 0 < dt <= self.MAX_INTERVAL:
            self.reset(timestamp)
            return 0.0, 0.0

        # d = LP((raw - previous_filtered)/dt). This algebra avoids division
        # by tiny dt while matching the reference's filtered-position derivative.
        k = 2 * math.pi * self.DERIVATIVE_CUTOFF
        strength_squared = self._strength * self._strength
        lag, derivative, output = [], [], []
        for delta, old_lag, old_derivative in zip(
                (yaw_delta, pitch_delta), self._lag, self._derivative):
            error = old_lag + delta
            speed = (old_derivative + k * error) / (1 + k * dt)
            # Equivalent to alpha=2*pi*dt*cutoff/(1+2*pi*dt*cutoff),
            # cutoff=3/s²+beta*abs(speed). No 1/s² overflow near zero.
            q = 2 * math.pi * dt * (self.MIN_CUTOFF + self.BETA * abs(speed) * strength_squared)
            alpha = q / (strength_squared + q)
            movement = alpha * error
            output.append(movement)
            lag.append(error - movement)
            derivative.append(speed)
        self._timestamp = timestamp
        self._lag, self._derivative = tuple(lag), tuple(derivative)
        return tuple(output)
