"""First-person control lifecycle checks with a fake clock and recording sink."""

from dataclasses import replace
import math
import threading
import unittest
from unittest.mock import Mock

from vrization_host.input import PoseController
from vrization_host.protocol import Settings


class RecordingSink:
    def __init__(self):
        self.moves = []

    def move(self, dx, dy):
        self.moves.append((dx, dy))


class AutoInputTests(unittest.TestCase):
    def make_controller(self, focus=101, strength=0, sink=None):
        now, foreground = [100.0], [focus]
        sink = sink if sink is not None else RecordingSink()
        states = []
        controller = PoseController(sink, lambda active, reason: states.append((active, reason)),
                                    focus_provider=lambda: foreground[0], clock=lambda: now[0],
                                    auto_control=True)
        controller.set_settings(Settings(mode="fps", stabilization=strength))
        controller.set_connected(True)
        return controller, sink, now, foreground, states

    @staticmethod
    def pose(controller, now, yaw, pitch=0):
        now[0] += 1 / 60
        controller.pose(controller.last_seq + 1, yaw, pitch)

    def test_fresh_first_person_pose_enables_control_without_manual_arm(self):
        controller, sink, now, _, states = self.make_controller()
        self.assertFalse(controller.armed)
        self.pose(controller, now, 1, .5)
        self.assertTrue(controller.armed)
        self.assertEqual(sink.moves, [])
        self.pose(controller, now, 1.02, .51)
        self.assertEqual(sink.moves, [(20, -10)])
        self.assertEqual([active for active, _ in states], [True])

    def test_embedded_controller_keeps_explicit_arm_by_default(self):
        sink = RecordingSink()
        controller = PoseController(sink, clock=lambda: 100)
        controller.set_settings(Settings(mode="fps"))
        controller.set_connected(True)
        controller.pose(1, 0, 0)
        controller.pose(2, .02, 0)
        self.assertFalse(controller.auto_control)
        self.assertFalse(controller.armed)
        self.assertEqual(sink.moves, [])
        self.assertTrue(controller.arm()[0])
        controller.pose(3, .02, 0)
        controller.pose(4, .04, 0)
        self.assertEqual(sink.moves, [(20, 0)])

    def test_desktop_control_continues_beyond_five_seconds_without_game_focus(self):
        controller, sink, now, foreground, _ = self.make_controller(focus=None)
        for index in range(20):
            now[0] += .4
            controller.pose(index, index * .001, 0)
        self.assertTrue(controller.armed)
        self.assertFalse(controller.suspended)
        self.assertEqual(sink.moves, [(1, 0)] * 19)
        foreground[0] = 101
        self.pose(controller, now, .02)
        self.assertTrue(controller.armed)
        self.assertEqual(sink.moves, [(1, 0)] * 20)

    def test_external_focus_change_preserves_immediate_mouse_deltas(self):
        controller, sink, now, foreground, _ = self.make_controller()
        self.pose(controller, now, 0)
        self.pose(controller, now, .1)
        foreground[0] = 202
        self.pose(controller, now, .12)
        self.assertTrue(controller.armed)
        self.assertFalse(controller.suspended)
        self.assertEqual(sink.moves, [(100, 0), (20, 0)])

    def test_host_ui_focus_retains_continuous_mouse_control(self):
        controller, sink, now, foreground, states = self.make_controller()
        self.pose(controller, now, 0)
        self.pose(controller, now, .1)
        foreground[0] = None
        self.pose(controller, now, .2)
        self.assertTrue(controller.armed)
        self.assertFalse(controller.suspended)
        self.pose(controller, now, .21)
        foreground[0] = 101
        self.pose(controller, now, .22)
        self.assertTrue(controller.armed)
        self.assertEqual(sink.moves, [(100, 0), (100, 0), (10, 0), (10, 0)])
        self.assertEqual([active for active, _ in states], [True])

    def test_auto_policy_never_queries_a_foreground_window_provider(self):
        controller, sink, now, _, _ = self.make_controller(focus=None)
        controller.focus_provider = Mock(side_effect=AssertionError("no foreground restriction"))
        self.pose(controller, now, 0)
        self.pose(controller, now, .02, .01)
        controller.focus_provider.assert_not_called()
        self.assertEqual(sink.moves, [(20, -10)])

    def test_stale_pose_and_watchdog_resume_with_baseline_only_first_sample(self):
        for watchdog in (False, True):
            with self.subTest(watchdog=watchdog):
                controller, sink, now, _, _ = self.make_controller(strength=1)
                self.pose(controller, now, 0)
                self.pose(controller, now, .1)
                before = len(sink.moves)
                now[0] += .6
                if watchdog:
                    controller.tick()
                    self.assertFalse(controller.armed)
                self.pose(controller, now, 2)
                self.assertTrue(controller.armed)
                self.assertFalse(controller.suspended)
                self.assertEqual(len(sink.moves), before)
                self.pose(controller, now, 2)
                self.assertEqual(sink.moves[-1], (0, 0))

    def test_disconnect_and_other_modes_never_move_then_new_session_rebases(self):
        controller, sink, now, _, _ = self.make_controller()
        self.pose(controller, now, 0)
        self.pose(controller, now, .02)
        controller.set_connected(False)
        self.pose(controller, now, .2)
        self.assertFalse(controller.armed)
        self.assertEqual(sink.moves, [(20, 0)])
        controller.set_connected(True)
        self.pose(controller, now, 2)
        self.pose(controller, now, 2.01)
        self.assertEqual(sink.moves[-1], (10, 0))
        for mode in ("full", "cinema"):
            controller.set_settings(replace(controller.settings, mode=mode))
            before = len(sink.moves)
            self.pose(controller, now, .5)
            self.pose(controller, now, .6)
            self.assertFalse(controller.armed)
            self.assertEqual(len(sink.moves), before)
        controller.set_settings(replace(controller.settings, mode="fps"))
        before = len(sink.moves)
        self.pose(controller, now, 2.5)
        self.assertTrue(controller.armed)
        self.assertEqual(len(sink.moves), before)
        self.pose(controller, now, 2.51)
        self.assertEqual(sink.moves[-1], (10, 0))

    def test_explicit_stops_stay_suspended_across_poses_focus_and_new_session(self):
        for reason in ("emergency stop", "capture unavailable", "headset editor opened",
                       "desktop stopped", "stream connection stalled"):
            with self.subTest(reason=reason):
                controller, sink, now, foreground, _ = self.make_controller()
                self.pose(controller, now, 0)
                self.pose(controller, now, .02)
                before = len(sink.moves)
                controller.disarm(reason)
                self.assertTrue(controller.suspended)
                self.pose(controller, now, .03)
                foreground[0] = 202
                self.pose(controller, now, .04)
                controller.set_settings(replace(controller.settings, mode="cinema"))
                controller.set_settings(replace(controller.settings, mode="fps"))
                controller.set_connected(False)
                controller.set_connected(True)
                self.pose(controller, now, .05)
                controller.recenter()
                self.pose(controller, now, .06)
                self.assertFalse(controller.armed)
                self.assertTrue(controller.suspended)
                self.assertEqual(len(sink.moves), before)

    def test_stop_before_first_pose_also_latches_and_resume_requires_new_baseline(self):
        controller, sink, now, _, _ = self.make_controller()
        controller.disarm("headset editor opened")
        self.pose(controller, now, 0)
        self.assertFalse(controller.armed)
        controller.resume_control()
        self.assertFalse(controller.suspended)
        self.assertFalse(controller.armed)
        self.assertEqual(sink.moves, [])
        self.pose(controller, now, 2)
        self.assertTrue(controller.armed)
        self.assertEqual(sink.moves, [])
        self.pose(controller, now, 2.01)
        self.assertEqual(sink.moves, [(10, 0)])

    def test_policy_toggle_does_not_undo_f8_or_replay_old_motion(self):
        controller, sink, now, _, _ = self.make_controller()
        self.pose(controller, now, 0)
        self.pose(controller, now, .02)
        controller.disarm("F8")
        controller.configure_auto_control(False)
        controller.configure_auto_control(True)
        self.pose(controller, now, .03)
        self.assertTrue(controller.suspended)
        self.assertFalse(controller.armed)
        self.assertEqual(sink.moves, [(20, 0)])
        controller.resume_control()
        self.pose(controller, now, 1)
        self.assertEqual(sink.moves, [(20, 0)])
        self.pose(controller, now, 1.01)
        self.assertEqual(sink.moves[-1], (10, 0))

    def test_disabling_policy_stops_auto_control_and_explicit_arm_remains_available(self):
        controller, sink, now, _, _ = self.make_controller()
        self.pose(controller, now, 0)
        self.pose(controller, now, .02)
        controller.configure_auto_control(False)
        self.pose(controller, now, .03)
        self.assertFalse(controller.armed)
        self.assertEqual(sink.moves, [(20, 0)])
        self.assertTrue(controller.arm()[0])
        self.pose(controller, now, .03)
        self.pose(controller, now, .04)  # Manual policy first claims the external window.
        self.assertEqual(sink.moves, [(20, 0)])
        self.pose(controller, now, .05)
        self.assertEqual(sink.moves[-1], (10, 0))

    def test_invalid_or_replayed_pose_cannot_arm_or_clear_suspension(self):
        controller, sink, now, _, _ = self.make_controller()
        controller.pose(1, math.nan, 0)
        controller.pose(1, 0, math.inf)
        self.assertFalse(controller.armed)
        self.assertEqual(controller.last_seq, -1)
        self.pose(controller, now, 0)
        controller.disarm("F8")
        controller.resume_control()
        controller.pose(controller.last_seq, .1, 0)
        controller.pose(controller.last_seq - 1, .1, 0)
        self.assertFalse(controller.armed)
        self.assertEqual(sink.moves, [])

    def test_sink_failure_latches_until_explicit_resume_without_repeated_failures(self):
        class FailingSink(RecordingSink):
            attempts = 0
            fail = True

            def move(self, dx, dy):
                self.attempts += 1
                if self.fail:
                    raise OSError("SendInput rejected")
                super().move(dx, dy)

        sink = FailingSink()
        controller, _, now, _, _ = self.make_controller(sink=sink)
        self.pose(controller, now, 0)
        self.pose(controller, now, .01)
        self.assertTrue(controller.suspended)
        self.assertFalse(controller.armed)
        self.pose(controller, now, .02)
        self.pose(controller, now, .03)
        self.assertEqual(sink.attempts, 1)
        sink.fail = False
        controller.resume_control()
        self.pose(controller, now, 2)
        self.assertEqual(sink.attempts, 1)
        self.pose(controller, now, 2.01)
        self.assertEqual(sink.moves, [(10, 0)])

    def test_tick_and_resume_do_not_emit_mouse_events(self):
        controller, sink, now, _, _ = self.make_controller(strength=1)
        self.pose(controller, now, 0)
        self.pose(controller, now, .1)
        before = len(sink.moves)
        for _ in range(10):
            now[0] += .1
            controller.tick()
        controller.resume_control()
        self.assertEqual(len(sink.moves), before)
        self.assertFalse(controller.armed)
        self.pose(controller, now, .1)
        self.pose(controller, now, .1)
        self.assertEqual(sink.moves[-1], (0, 0))

    def test_stop_serializes_with_an_inflight_sink_and_blocks_all_later_poses(self):
        entered, release, stopped = threading.Event(), threading.Event(), threading.Event()

        class BlockingSink(RecordingSink):
            def move(self, dx, dy):
                entered.set()
                if not release.wait(2):
                    raise TimeoutError("test sink was not released")
                super().move(dx, dy)

        controller, sink, now, _, _ = self.make_controller(sink=BlockingSink())
        self.pose(controller, now, 0)
        mover = threading.Thread(target=lambda: controller.pose(2, .01, 0))
        stopper = threading.Thread(target=lambda: (controller.disarm("F8"), stopped.set()))
        mover.start()
        try:
            self.assertTrue(entered.wait(2))
            stopper.start()
            self.assertFalse(stopped.wait(.02))
        finally:
            release.set()
            mover.join(2)
            if stopper.ident is not None:
                stopper.join(2)
        self.assertFalse(mover.is_alive())
        self.assertFalse(stopper.is_alive())
        self.assertTrue(stopped.is_set())
        self.pose(controller, now, .02)
        self.assertEqual(sink.moves, [(10, 0)])
        self.assertTrue(controller.suspended)

    def test_engine_adapter_can_opt_in_without_a_window_focus_provider(self):
        sink = RecordingSink()
        controller = PoseController(sink, clock=lambda: 100, auto_control=True)
        controller.set_settings(Settings(mode="fps"))
        controller.set_connected(True)
        controller.pose(1, 0, 0)
        controller.pose(2, .02, .01)
        self.assertEqual(sink.moves, [(20, -10)])


if __name__ == "__main__":
    unittest.main()
