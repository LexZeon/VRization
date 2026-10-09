from dataclasses import replace
import json
import unittest

from vrization_host.protocol import ProtocolError, Settings, parse_message


class StabilizationProtocolTests(unittest.TestCase):
    def test_default_and_legacy_snapshot_migration_are_zero_without_losing_values(self):
        self.assertEqual(Settings().stabilization, 0)
        expected = replace(Settings(), mode="fps", sensitivity=1500, eyeSeparation=-.4)
        old = expected.to_dict()
        del old["stabilization"]
        restored = Settings().update(old)
        self.assertEqual(restored, expected)

    def test_stabilization_round_trips_and_keeps_protocol_v1(self):
        for value in (0, .5, 1):
            settings = Settings().update({"stabilization": value})
            message = {"v": 1, "type": "settings", "clientSeq": 3, "settings": settings.to_dict()}
            restored = Settings().update(parse_message(json.dumps(message))["settings"])
            self.assertEqual(restored.stabilization, value)
            self.assertEqual(restored, settings)

    def test_invalid_stabilization_is_rejected_atomically(self):
        original = Settings(mode="fps", stabilization=.5)
        for value in (True, "0.5", None, -.0001, 1.0001, float("nan"), float("inf"), 10**1000):
            with self.subTest(value=str(value)[:30]):
                with self.assertRaises(ProtocolError):
                    original.update({"scale": .6, "stabilization": value})
        self.assertEqual(original, Settings(mode="fps", stabilization=.5))


if __name__ == "__main__":
    unittest.main()
