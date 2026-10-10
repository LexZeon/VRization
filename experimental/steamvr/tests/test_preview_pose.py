"""Recorded full-quaternion safety tests; no named memory or mouse injection."""
import json
import math
import unittest

from vrization_steamvr.pose import HmdPoseGate
from vrization_steamvr.session import parse_preview_message
from preview_fixtures import RecordingPoseSink, packet


def yaw(a):
    return (0., math.sin(a/2), 0., math.cos(a/2))


class HmdPoseTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.sink = RecordingPoseSink()
        self.gate = HmdPoseGate(self.sink, lambda: self.now)

    def pose(self, seq, q=(0,0,0,1), *, epoch=7, valid=True, time_us=None):
        return self.gate.pose(parse_preview_message(json.dumps(packet(epoch,seq,q,valid=valid,time_us=time_us))))

    def ready(self):
        self.gate.open(7)
        self.gate.negotiate()

    def assertQ(self, expected):
        self.assertIsNotNone(self.sink.last[0])
        for actual, value in zip(self.sink.last[0], expected):
            self.assertAlmostEqual(actual, value, places=12)

    def test_opening_the_transport_does_not_authorize_hmd_tracking(self):
        self.assertFalse(self.pose(1))
        self.gate.open(7)
        self.assertFalse(self.pose(1))
        self.assertIsNone(self.sink.last[0])
        self.gate.negotiate()
        self.assertTrue(self.pose(1))
        self.assertQ((0,0,0,1))

    def test_shared_compound_golden_preserves_roll_yaw_pitch_without_euler(self):
        self.ready()
        q=(-.021869850273803754,-.3837819133455947,-.4617914702766405,.7993633658215358)
        self.pose(1,q)
        self.assertQ(q)
        self.assertAlmostEqual(sum(x*x for x in self.sink.last[0]),1,places=14)

    def test_epoch_and_sequence_replays_cannot_change_or_refresh_tracking(self):
        self.ready()
        self.pose(4,yaw(.5))
        before=self.sink.snapshot()
        self.now+=300
        self.assertFalse(self.pose(5,yaw(.8),epoch=6))
        self.assertFalse(self.pose(4,yaw(.8)))
        self.assertFalse(self.pose(3,yaw(.8)))
        self.assertEqual(before,self.sink.snapshot())
        self.assertEqual(self.gate.last_tick,1000)

    def test_missing_sensor_packet_is_unavailable_tracking_without_identity_pose(self):
        self.ready()
        self.pose(1,yaw(.4))
        self.assertTrue(self.pose(2,None,valid=False))
        self.assertIsNone(self.sink.last[0])
        self.assertIsNone(self.gate.current)
        self.assertIsNone(self.gate.output)

    def test_increasing_sequence_with_a_backward_phone_clock_is_rejected(self):
        self.ready()
        self.pose(1,yaw(.4),time_us=10000)
        before=self.sink.snapshot()
        self.assertFalse(self.pose(2,yaw(.8),time_us=9999))
        self.assertEqual(before,self.sink.snapshot())
        self.assertTrue(self.pose(2,yaw(.5),time_us=10000))
        self.assertQ(yaw(.5))

    def test_emergency_latch_survives_remote_recenter_enable_and_new_sessions(self):
        self.ready()
        self.pose(1,yaw(.4))
        self.gate.pause()
        self.gate.recenter(phone_reset=True)
        self.gate.enable(True)
        self.pose(2,yaw(.8))
        self.assertTrue(self.gate.paused)
        self.assertIsNone(self.sink.last[0])
        self.gate.close()
        self.gate.open(8)
        self.gate.negotiate()
        self.pose(1,yaw(.9),epoch=8)
        self.assertTrue(self.gate.paused)
        self.assertIsNone(self.sink.last[0])

    def test_only_local_resume_clears_pause_and_drops_accumulated_motion(self):
        self.ready()
        self.pose(1,yaw(.2))
        self.gate.pause()
        self.pose(2,yaw(1))
        self.gate.resume()
        self.assertIsNone(self.sink.last[0])
        self.pose(3,yaw(1.2))
        self.assertQ((0,0,0,1))
        self.pose(4,yaw(1.4))
        self.assertQ(yaw(.2))

    def test_disabling_tracking_does_not_clear_the_pause_latch(self):
        self.ready()
        self.gate.enable(False)
        self.pose(1)
        self.assertIsNone(self.sink.last[0])
        self.gate.pause()
        self.gate.enable(True)
        self.pose(2)
        self.assertTrue(self.gate.paused)
        self.assertIsNone(self.sink.last[0])

    def test_phone_recenter_uses_identity_after_the_phone_resets_its_own_baseline(self):
        self.ready()
        self.pose(20,yaw(.8))
        self.gate.recenter(phone_reset=True)
        self.assertEqual(self.gate.last_seq,20)
        self.pose(21,(0,0,0,1))
        self.assertQ((0,0,0,1))
        self.pose(22,yaw(.1))
        self.assertQ(yaw(.1))

    def test_pc_recenter_uses_current_full_orientation_as_the_local_baseline(self):
        self.ready()
        self.pose(1,yaw(.8))
        self.gate.recenter()
        self.pose(2,yaw(1))
        self.assertQ(yaw(.2))

    def test_stale_tracking_expires_and_a_replay_cannot_revive_it(self):
        self.ready()
        self.pose(1,yaw(.4))
        self.now+=501
        self.gate.tick()
        self.assertIsNone(self.sink.last[0])
        self.assertFalse(self.pose(1,yaw(.4)))
        self.assertIsNone(self.sink.last[0])
        self.assertTrue(self.pose(2,yaw(.5)))
        self.assertQ(yaw(.5))

    def test_quaternion_sign_continuity_does_not_flip_at_the_same_rotation(self):
        self.ready()
        self.pose(1,yaw(.8))
        self.pose(2,tuple(-x for x in yaw(.8)))
        self.assertQ(yaw(.8))

    def test_disconnect_immediately_invalidates_tracking_and_rejects_late_pose(self):
        self.ready()
        self.pose(1)
        self.gate.close()
        self.assertFalse(self.sink.last[2])
        self.assertIsNone(self.sink.last[0])
        self.assertFalse(self.pose(2,yaw(.2)))


if __name__ == "__main__":
    unittest.main()
