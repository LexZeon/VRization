"""Input safety/quantization regressions using a recording sink only."""

from dataclasses import replace
import math
import random
import time
import unittest
from unittest.mock import patch

from vrization_host.input import PoseController
from vrization_host.protocol import Settings


class RecordingSink:
    def __init__(self):
        self.moves = []

    def move(self, dx, dy):
        self.moves.append((dx, dy))


class InputStabilizationTests(unittest.TestCase):
    def test_production_clock_is_high_resolution_for_filter_and_safety_timestamps(self):
        self.assertIs(PoseController.__init__.__defaults__[-1], time.perf_counter)
        self.assertTrue(time.get_clock_info("perf_counter").monotonic)

    def test_sub_tick_arrivals_preserve_small_turn_increments(self):
        controller, sink, now = self.make_controller()
        # Several valid poses fit inside one legacy GetTickCount64 15.625ms
        # interval. A QPC-like source keeps their actual spacing, rather than
        # treating them as duplicate timestamps and discarding each raw delta.
        seen_times = []
        for index in range(1, 16):
            now[0] += .001
            seen_times.append(now[0])
            controller.pose(controller.last_seq + 1, index * .001, 0)
        self.assertLess(seen_times[-1] - 100, .015625)
        self.assertGreater(sum(dx for dx, _ in sink.moves), 0)
        for _ in range(60):
            now[0] += .01
            controller.pose(controller.last_seq + 1, .015, 0)
        self.assertEqual(sum(dx for dx, _ in sink.moves), 15)

    def make_controller(self, strength=1, focus=None):
        now, sink = [100.0], RecordingSink()
        controller = PoseController(sink, clock=lambda: now[0], focus_provider=focus)
        controller.set_settings(Settings(mode="fps", stabilization=strength))
        controller.set_connected(True)
        controller.pose(1, 0, 0)
        self.assertTrue(controller.arm()[0])
        controller.pose(2, 0, 0)
        return controller, sink, now

    @staticmethod
    def next_pose(controller, now, yaw, pitch=0):
        now[0] += 1 / 60
        controller.pose(controller.last_seq + 1, yaw, pitch)

    def test_default_zero_matches_historical_quantization_bit_for_bit(self):
        controller, sink, now = self.make_controller(0)
        generator = random.Random(20261009)
        previous = (0.0, 0.0)
        remainder = (0.0, 0.0)
        expected = []
        # Independent historical oracle checks round-to-even, fractional
        # carry and deliberate removal of integer movement beyond the cap.
        with patch.object(controller.stabilizer, "step", side_effect=AssertionError("zero must bypass")):
            for index in range(1000):
                yaw = previous[0] + generator.uniform(-.39, .39)
                pitch = previous[1] + generator.uniform(-.39, .39)
                yaw = (yaw + math.pi) % (2 * math.pi) - math.pi
                pitch = (pitch + math.pi) % (2 * math.pi) - math.pi
                dyaw = (yaw - previous[0] + math.pi) % (2 * math.pi) - math.pi
                dpitch = (pitch - previous[1] + math.pi) % (2 * math.pi) - math.pi
                dx, dy = dyaw * 1000 + remainder[0], -dpitch * 1000 + remainder[1]
                expected.append((max(-120, min(120, round(dx))), max(-120, min(120, round(dy)))))
                remainder = (dx - round(dx), dy - round(dy))
                previous = (yaw, pitch)
                self.next_pose(controller, now, yaw, pitch)
                self.assertEqual(controller.remainder, remainder)
        self.assertEqual(sink.moves, expected)

    def test_fractional_movement_is_preserved_and_clipped_integer_debt_is_not_replayed(self):
        controller, sink, now = self.make_controller(0)
        for index in range(1, 1001):
            self.next_pose(controller, now, index * .0002)
        self.assertEqual(sum(dx for dx, _ in sink.moves), 200)
        controller.recenter()
        self.next_pose(controller, now, 0)
        self.next_pose(controller, now, .3)
        for _ in range(10):
            self.next_pose(controller, now, .3)
        self.assertEqual(sink.moves[-11], (120, 0))
        self.assertEqual(sink.moves[-10:], [(0, 0)] * 10)

    def test_zero_strength_gain_changes_preserve_legacy_baseline_and_fractional_carry(self):
        controller, sink, now = self.make_controller(0)
        self.next_pose(controller, now, .0002, .0002)
        remainder, baseline = controller.remainder, controller.baseline
        controller.set_settings(replace(controller.settings, sensitivity=2000, invertY=True))
        self.assertEqual(controller.remainder, remainder)
        self.assertEqual(controller.baseline, baseline)
        self.next_pose(controller, now, .0004, .0004)
        self.assertEqual(sink.moves[-1], (1, 0))

    def test_raw_spike_is_rejected_before_filter_and_cannot_leave_a_tail(self):
        controller, sink, now = self.make_controller()
        with patch.object(controller.stabilizer, "step", wraps=controller.stabilizer.step) as filtered:
            self.next_pose(controller, now, .1)
            self.assertEqual(filtered.call_count, 1)
            count = len(sink.moves)
            self.next_pose(controller, now, 1.5)
            self.assertEqual(filtered.call_count, 1)
            self.assertEqual(len(sink.moves), count)
            self.next_pose(controller, now, 1.5)
            self.assertEqual(sink.moves[-1], (0, 0))
            self.assertEqual(controller.remainder, (0, 0))

    def test_wraparound_is_a_small_accepted_turn_in_both_directions(self):
        for direction in (-1, 1):
            controller, sink, now = self.make_controller()
            controller.recenter()
            self.next_pose(controller, now, direction * (math.pi - .01))
            with patch.object(controller.stabilizer, "step", wraps=controller.stabilizer.step) as filtered:
                self.next_pose(controller, now, -direction * (math.pi - .01))
                self.assertAlmostEqual(filtered.call_args.args[0], direction * .02)
                self.assertGreater(sink.moves[-1][0] * direction, 0)
                self.assertLessEqual(abs(sink.moves[-1][0]), 20)

    def test_duplicate_out_of_order_and_nonfinite_packets_do_not_touch_filter_or_heartbeat(self):
        controller, sink, now = self.make_controller()
        original = (controller.last_seq, controller.last_pose_time, controller.baseline)
        now[0] += .1
        with patch.object(controller.stabilizer, "step", wraps=controller.stabilizer.step) as filtered:
            controller.pose(2, .1, 0)
            controller.pose(1, .1, 0)
            controller.pose(3, float("nan"), 0)
            controller.pose(3, 0, float("inf"))
            self.assertEqual(filtered.call_count, 0)
        self.assertEqual((controller.last_seq, controller.last_pose_time, controller.baseline), original)
        self.assertEqual(sink.moves, [])

    def test_expired_heartbeat_disarms_before_filter_and_new_pose_does_not_rearm(self):
        controller, sink, now = self.make_controller()
        self.next_pose(controller, now, .1)
        count = len(sink.moves)
        now[0] += .51
        with patch.object(controller.stabilizer, "step", wraps=controller.stabilizer.step) as filtered:
            controller.pose(4, .2, 0)
            self.assertEqual(filtered.call_count, 0)
        self.assertFalse(controller.armed)
        self.next_pose(controller, now, .21)
        self.assertEqual(len(sink.moves), count)
        self.assertTrue(controller.arm()[0])
        self.next_pose(controller, now, .21)
        self.next_pose(controller, now, .21)
        self.assertEqual(sink.moves[-1], (0, 0))

    def test_tick_never_emits_movement_and_disarm_clears_pending_filter_response(self):
        controller, sink, now = self.make_controller()
        self.next_pose(controller, now, .1)
        count = len(sink.moves)
        for _ in range(10):
            now[0] += .01
            controller.tick()
        self.assertEqual(len(sink.moves), count)
        controller.disarm("F8 test callback")
        self.next_pose(controller, now, .1)
        self.assertTrue(controller.arm()[0])
        self.next_pose(controller, now, .1)
        self.next_pose(controller, now, .1)
        self.assertEqual(sink.moves[-1], (0, 0))

    def test_recenter_clears_filter_tail_without_rearming(self):
        controller, sink, now = self.make_controller()
        self.next_pose(controller, now, .1)
        count = len(sink.moves)
        controller.recenter()
        self.assertTrue(controller.armed)
        self.next_pose(controller, now, 1)
        self.assertEqual(len(sink.moves), count)
        self.next_pose(controller, now, 1)
        self.assertEqual(sink.moves[-1], (0, 0))

    def test_connection_and_mode_boundaries_clear_filter_and_require_arm(self):
        controller, sink, now = self.make_controller()
        self.next_pose(controller, now, .1)
        controller.set_connected(False)
        self.assertFalse(controller.armed)
        controller.set_connected(True)
        controller.pose(1, .1, 0)
        self.assertTrue(controller.arm()[0])
        self.next_pose(controller, now, .1)
        self.next_pose(controller, now, .1)
        self.assertEqual(sink.moves[-1], (0, 0))
        controller.set_settings(replace(controller.settings, mode="full"))
        self.assertFalse(controller.armed)
        self.assertFalse(controller.arm()[0])

    def test_focus_claim_establishes_fresh_filter_and_focus_change_discards_tail(self):
        focus = [None]
        controller, sink, now = self.make_controller(focus=lambda: focus[0])
        self.next_pose(controller, now, .1)
        focus[0] = 10
        self.next_pose(controller, now, .2)
        self.next_pose(controller, now, .2)
        self.assertEqual(sink.moves, [(0, 0)])
        self.next_pose(controller, now, .3)
        focus[0] = 11
        self.next_pose(controller, now, .31)
        self.assertFalse(controller.armed)
        count = len(sink.moves)
        self.assertTrue(controller.arm()[0])
        self.next_pose(controller, now, .31)
        self.next_pose(controller, now, .31)
        self.assertEqual(len(sink.moves), count)
        self.next_pose(controller, now, .31)
        self.assertEqual(sink.moves[-1], (0, 0))

    def test_strength_and_filtered_gain_changes_drop_old_lag_and_fractional_carry(self):
        for changed in ({"stabilization": .5}, {"stabilization": 0},
                        {"sensitivity": 2000}, {"invertY": True}):
            with self.subTest(changed=changed):
                controller, sink, now = self.make_controller()
                self.next_pose(controller, now, .1, .1)
                controller.set_settings(replace(controller.settings, **changed))
                self.assertTrue(controller.armed)
                self.assertEqual(controller.remainder, (0, 0))
                count = len(sink.moves)
                self.next_pose(controller, now, .1, .1)
                self.assertEqual(len(sink.moves), count)
                self.next_pose(controller, now, .1, .1)
                self.assertEqual(sink.moves[-1], (0, 0))

    def test_filter_output_retains_pixel_cap_and_inverted_y_direction(self):
        controller, sink, now = self.make_controller()
        controller.set_settings(replace(controller.settings, sensitivity=3000, invertY=True))
        self.next_pose(controller, now, 0)
        self.next_pose(controller, now, .39, .39)
        self.assertEqual(sink.moves[-1], (120, 120))
        self.assertTrue(all(abs(value) <= 120 for move in sink.moves for value in move))
        for _ in range(10):
            self.next_pose(controller, now, .39, .39)
        self.assertEqual(sink.moves[-10:], [(0, 0)] * 10)

    def test_clipping_one_axis_does_not_remove_other_axis_small_motion(self):
        controller, sink, now = self.make_controller()
        self.next_pose(controller, now, .39, .01)
        self.assertEqual(sink.moves[-1][0], 120)
        self.next_pose(controller, now, .39, .01)
        self.assertEqual(sink.moves[-1][0], 0)
        self.assertLess(sink.moves[-1][1], 0)


if __name__ == "__main__":
    unittest.main()
