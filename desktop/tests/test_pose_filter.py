"""Synthetic algorithm behavior; these tests never inject OS/game input."""

import math
import unittest

from vrization_host.pose_filter import PoseStabilizer


def filtered_signal(values, frequency, strength):
    stabilizer = PoseStabilizer(strength)
    stabilizer.reset(0)
    previous = position = 0.0
    output = []
    for index, value in enumerate(values, 1):
        movement, _ = stabilizer.step(value - previous, 0, index / frequency)
        previous = value
        position += movement
        output.append(position)
    return output


def rms(values):
    return math.sqrt(sum(value * value for value in values) / len(values))


class PoseFilterTests(unittest.TestCase):
    def test_strength_zero_is_exact_identity_even_without_seed_and_repeated_time(self):
        stabilizer = PoseStabilizer()
        for value in (0.0, .0001, -.0001, .39, -math.pi, math.pi):
            self.assertEqual(stabilizer.step(value, -value, 0), (value, -value))

    def test_idle_ten_hz_jitter_reduced_at_sixty_and_hundred_hz(self):
        for frequency in (60, 100):
            values = [.002 * math.sin(2 * math.pi * 10 * index / frequency)
                      for index in range(1, frequency * 3 + 1)]
            low = filtered_signal(values, frequency, .5)[frequency:]
            high = filtered_signal(values, frequency, 1)[frequency:]
            with self.subTest(frequency=frequency):
                self.assertLess(rms(high) / rms(values[frequency:]), .4)
                self.assertLess(rms(low) / rms(values[frequency:]), .8)
                self.assertLess(rms(high), rms(low))

    def test_slow_deliberate_turn_is_not_swallowed_by_a_deadzone(self):
        for frequency in (30, 60, 100, 120):
            duration, speed = 3, .002
            values = [speed * index / frequency for index in range(1, duration * frequency + 1)]
            for strength in (.5, 1):
                output = filtered_signal(values, frequency, strength)
                with self.subTest(frequency=frequency, strength=strength):
                    self.assertGreater(output[-1], values[-1] * .97)
                    self.assertAlmostEqual((output[-1] - output[-frequency - 1]), speed, delta=.00001)

    def test_adaptive_rapid_turn_tracks_with_less_than_twelve_ms_angular_lag(self):
        for frequency in (30, 60, 100, 120):
            speed = 1.5
            values = [speed * index / frequency for index in range(1, int(frequency * .4) + 1)]
            for strength in (.5, 1):
                output = filtered_signal(values, frequency, strength)
                errors = [raw - filtered for raw, filtered in zip(values, output)]
                with self.subTest(frequency=frequency, strength=strength):
                    self.assertLess(sum(errors) / len(errors) / speed, .012)
                    self.assertLess(errors[-1] / speed, .012)
                    self.assertGreater(output[-1], values[-1] * .95)

    def test_step_response_reaches_ninety_percent_by_fifty_ms(self):
        for frequency in (60, 100):
            for strength in (.5, 1):
                output = filtered_signal([.2] * frequency, frequency, strength)
                with self.subTest(frequency=frequency, strength=strength):
                    self.assertGreaterEqual(output[0], .1)
                    first_ninety = next(i for i, value in enumerate(output, 1) if value >= .18)
                    self.assertLessEqual(first_ninety / frequency, .05)
                    self.assertTrue(all(0 <= value <= .2 + 1e-12 for value in output))

    def test_variable_time_steps_remain_finite_monotonic_and_reach_the_target(self):
        stabilizer = PoseStabilizer(1)
        stabilizer.reset(0)
        total = now = 0.0
        for index in range(200):
            now += (1 / 30, 1 / 100, 1 / 120)[index % 3]
            movement, _ = stabilizer.step(.1 if index == 0 else 0, 0, now)
            self.assertTrue(math.isfinite(movement))
            self.assertGreaterEqual(movement, 0)
            total += movement
        self.assertAlmostEqual(total, .1, places=12)

    def test_reset_and_non_increasing_or_late_time_discard_filter_tail(self):
        for boundary in (0, -.01, .6):
            stabilizer = PoseStabilizer(1)
            stabilizer.reset(1)
            self.assertGreater(stabilizer.step(.1, 0, 1.01)[0], 0)
            time = 1.01 + boundary
            self.assertEqual(stabilizer.step(0, 0, time), (0, 0))
            self.assertEqual(stabilizer.step(0, 0, time + .01), (0, 0))
        stabilizer.reset(2)
        self.assertEqual(stabilizer.step(0, 0, 2.01), (0, 0))

    def test_invalid_inputs_are_atomic_and_cannot_poison_next_valid_sample(self):
        first, second = PoseStabilizer(1), PoseStabilizer(1)
        first.reset(0)
        second.reset(0)
        for invalid in (True, float("nan"), float("inf"), 10**1000, "1", None):
            with self.subTest(invalid=str(invalid)[:30]):
                with self.assertRaises(ValueError):
                    first.configure(invalid)
                with self.assertRaises(ValueError):
                    first.step(invalid, 0, .01)
                with self.assertRaises(ValueError):
                    first.step(0, 0, invalid)
        self.assertEqual(first.step(.01, -.02, .02), second.step(.01, -.02, .02))

    def test_near_zero_strength_is_stable_and_converges_to_identity(self):
        for strength in (1e-3, 1e-100, 5e-324):
            stabilizer = PoseStabilizer(strength)
            stabilizer.reset(0)
            yaw, pitch = stabilizer.step(.02, -.01, .01)
            self.assertAlmostEqual(yaw, .02, delta=2e-7)
            self.assertAlmostEqual(pitch, -.01, delta=1e-7)

    def test_reconfiguring_strength_clears_previous_response(self):
        stabilizer = PoseStabilizer(1)
        stabilizer.reset(0)
        stabilizer.step(.1, 0, .01)
        self.assertTrue(stabilizer.configure(.5))
        self.assertEqual(stabilizer.step(0, 0, .02), (0, 0))
        self.assertEqual(stabilizer.step(0, 0, .03), (0, 0))

    def test_axis_clip_removes_only_that_axis_tail(self):
        stabilizer = PoseStabilizer(1)
        stabilizer.reset(0)
        stabilizer.step(.1, .01, .01)
        stabilizer.discard_lag(yaw=True)
        yaw, pitch = stabilizer.step(0, 0, .02)
        self.assertEqual(yaw, 0)
        self.assertGreater(pitch, 0)


if __name__ == "__main__":
    unittest.main()
