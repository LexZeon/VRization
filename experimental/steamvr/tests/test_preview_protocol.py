"""Strict preview messages and capability intersection, independent of native APIs."""
import json
import math
import unittest

from vrization_host.protocol import ProtocolError
from vrization_steamvr.session import MAX_SAFE, Session, parse_preview_message
from preview_fixtures import CAPS, packet


class PreviewProtocolTests(unittest.TestCase):
    def parse(self, **patch):
        values = packet()
        values.update(patch)
        return parse_preview_message(json.dumps(values))

    def test_full_xyzw_packet_normalizes_only_a_unit_length_quaternion(self):
        q = (.1, -.2, .3, math.sqrt(.86))
        result = self.parse(q=q)
        self.assertEqual(result["type"], "hmdPose")
        self.assertEqual(len(result["q"]), 4)
        self.assertAlmostEqual(sum(x*x for x in result["q"]), 1, places=14)
        self.assertNotIn("yaw", result)
        self.assertNotIn("pitch", result)

    def test_unavailable_tracking_may_omit_quaternion_but_never_invents_one(self):
        result = parse_preview_message(json.dumps(packet(q=None, valid=False)))
        self.assertFalse(result["trackingValid"])
        self.assertNotIn("q", result)
        values = packet(q=None)
        with self.assertRaises(ProtocolError):
            parse_preview_message(json.dumps(values))

    def test_every_required_field_and_unknown_fields_are_checked(self):
        for field in packet(q=None, valid=False):
            values = packet(q=None, valid=False)
            del values[field]
            with self.subTest(missing=field), self.assertRaises(ProtocolError):
                parse_preview_message(json.dumps(values))
        for unknown in ("position", "yaw", "pitch", "mouseDx", "future"):
            with self.subTest(unknown=unknown), self.assertRaises(ProtocolError):
                self.parse(**{unknown: 0})

    def test_epoch_sequence_and_phone_clock_require_bounded_actual_integers(self):
        for field in ("epoch", "seq", "timeUs"):
            for bad in (True, 1.0, "1", None, -1, MAX_SAFE+1):
                with self.subTest(field=field, bad=bad), self.assertRaises(ProtocolError):
                    self.parse(**{field: bad})
        with self.assertRaises(ProtocolError):
            self.parse(epoch=0)
        self.assertEqual(self.parse(seq=0, timeUs=0)["seq"], 0)
        self.assertEqual(self.parse(epoch=MAX_SAFE)["epoch"], MAX_SAFE)

    def test_quaternion_numbers_shapes_and_norms_are_strict(self):
        for bad in (None, {}, "xyzw", [], [0,0,1], [0,0,0,0], [1,1,0,0],
                    [True,0,0,1], ["0",0,0,1], [float("nan"),0,0,1], [float("inf"),0,0,1]):
            with self.subTest(q=bad), self.assertRaises(ProtocolError):
                self.parse(q=bad)
        for bad in (0, 1, "true", None):
            with self.subTest(flag=bad), self.assertRaises(ProtocolError):
                self.parse(trackingValid=bad)

    def test_huge_finite_json_integer_reports_protocol_error_not_overflow(self):
        with self.assertRaises(ProtocolError):
            self.parse(q=[10**400, 0, 0, 1])

    def test_nested_json_under_the_byte_limit_reports_protocol_error_not_recursion(self):
        raw = "[" * 1000 + "0" + "]" * 1000
        self.assertLess(len(raw), 4096)
        with self.assertRaises(ProtocolError):
            parse_preview_message(raw)

    def test_size_invalid_json_wrong_version_and_ordinary_messages(self):
        for raw in (b"{}", "{" , "x" * 4097):
            with self.subTest(raw=repr(raw)[:30]), self.assertRaises(ProtocolError):
                parse_preview_message(raw)
        for version in (True, 1.0, 0, 2):
            with self.assertRaises(ProtocolError):
                self.parse(v=version)
        self.assertEqual(parse_preview_message('{"v":1,"type":"pose","seq":1,"yaw":0,"pitch":0}')["type"], "pose")
        self.assertEqual(parse_preview_message('{"v":1,"type":"hello","editing":true}')["editing"], True)

    def test_only_complete_capability_intersection_accepts_the_stereo_hmd_route(self):
        for missing in ([], ["stereo-sbs"], ["hmd-orientation"], ["enhanced-first-person"]):
            session = Session("steamvr-phone")
            session.open(9)
            with self.subTest(capabilities=missing), self.assertRaises(ProtocolError):
                session.negotiate(missing)
            self.assertFalse(session.accepted)
        session = Session("steamvr-phone")
        session.open(9)
        session.negotiate(CAPS)
        self.assertEqual(session.descriptor(), {"v":1,"epoch":9,"accepted":True,"streamLayout":"sbs","inputTarget":"virtual-hmd"})
        session.close()
        self.assertFalse(session.accepted)

    def test_direct_route_is_mono_mouse_without_capabilities(self):
        session = Session("direct-phone")
        session.open(5)
        self.assertEqual(session.descriptor(), {"v":1,"epoch":5,"accepted":True,"streamLayout":"mono","inputTarget":"mouse"})
        session.negotiate([])
        self.assertTrue(session.accepted)
        with self.assertRaises(ValueError):
            Session("steamvr-headset")


if __name__ == "__main__":
    unittest.main()
