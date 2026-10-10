"""Bounded cold-start and mapping recovery with fake ADB, never hardware."""
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest

from vrization_host.usb import AdbReverse, UsbManager, WindowsUsbPresence
from test_usb import FakeAdbRunner


class RecoveryRunner(FakeAdbRunner):
    def __init__(self):
        super().__init__([("tcp:1111", "tcp:2222")])
        self.failed_devices = False
        self.failed_mapping = False
        self.probes = []

    def __call__(self, command, **kwargs):
        args = command[1:]
        self.probes.append((args, kwargs))
        if args == ["devices", "-l"]:
            if self.failed_devices:
                raise subprocess.TimeoutExpired(command, kwargs["timeout"], output="PRIVATE-SERIAL")
            return SimpleNamespace(returncode=0, stdout="PRIVATE-SERIAL device usb:1-4\n", stderr="")
        if self.failed_mapping:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return super().__call__(command, **kwargs)


class UsbRecoveryTests(unittest.TestCase):
    def test_cold_and_recovery_get_eight_seconds_then_return_to_three(self):
        runner, now = RecoveryRunner(), [0.0]
        def timed(command, **kwargs):
            now[0] += .125
            return runner(command, **kwargs)
        adb = AdbReverse(Path("private/adb.exe"), timed, clock=lambda: now[0])
        adb.devices()
        adb.devices()
        runner.failed_devices = True
        with self.assertRaises(subprocess.TimeoutExpired):
            adb.devices()
        self.assertFalse(adb.enumeration_ready)
        runner.failed_devices = False
        adb.devices()
        adb.devices()
        self.assertEqual([kw["timeout"] for args, kw in runner.probes], [8, 3, 3, 8, 3])
        self.assertEqual([p["result"] for p in adb.recent_commands], ["ok", "ok", "timeout", "ok", "ok"])
        self.assertEqual(adb.last_devices_probe["elapsedMs"], 125)
        for args, kw in runner.probes:
            self.assertEqual(args, ["devices", "-l"])
            self.assertEqual(kw["stdin"], subprocess.DEVNULL)
            self.assertEqual(kw["creationflags"], getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.assertNotIn("PRIVATE-SERIAL", json.dumps(list(adb.recent_commands)))
        self.assertNotIn("private", json.dumps(list(adb.recent_commands)))
        for _ in range(10):
            adb.devices()
        self.assertEqual(len(adb.recent_commands), 8)

    def test_uncertain_cleanup_retains_claim_then_recovers_without_cable_cycle(self):
        runner = RecoveryRunner()
        adb = AdbReverse(Path("adb.exe"), runner)
        self.assertTrue(adb.ensure("PRIVATE-SERIAL", 8765))
        runner.failed_mapping = True
        self.assertFalse(adb.release())
        self.assertEqual(adb.owned, ("PRIVATE-SERIAL", "tcp:18765", "tcp:8765"))
        runner.failed_mapping = False
        self.assertTrue(adb.ensure("PRIVATE-SERIAL", 8765))
        self.assertEqual(sum("--no-rebind" in c for c in runner.commands), 1)
        self.assertTrue(adb.release())
        self.assertEqual(runner.mappings, {("tcp:1111", "tcp:2222")})

    def test_failed_remove_and_foreign_replacement_are_distinguished(self):
        runner = FakeAdbRunner()
        fail_remove = [False]
        def run(command, **kwargs):
            if fail_remove[0] and "--remove" in command:
                raise subprocess.TimeoutExpired(command, kwargs["timeout"])
            return runner(command, **kwargs)
        adb = AdbReverse(Path("adb.exe"), run)
        adb.ensure("PRIVATE-SERIAL", 8765)
        fail_remove[0] = True
        self.assertFalse(adb.release())
        self.assertIsNotNone(adb.owned)
        runner.mappings = {("tcp:18765", "tcp:9999")}
        self.assertTrue(adb.release())
        self.assertIsNone(adb.owned)
        self.assertEqual(runner.mappings, {("tcp:18765", "tcp:9999")})
        self.assertFalse(adb.ensure("PRIVATE-SERIAL", 8765))

    def test_manager_revokes_during_uncertainty_and_recovers_or_recreates_owned_reverse(self):
        runner, events = RecoveryRunner(), []
        adb = AdbReverse(Path("adb.exe"), runner)
        manager = UsbManager(SimpleNamespace(port=8765, running=False), events.append,
                             adb=adb, mux=SimpleNamespace(devices=lambda: []))
        manager.set_enabled(True)
        manager.scan()
        self.assertTrue(manager.authorized.is_set())
        runner.failed_devices = runner.failed_mapping = True
        manager.scan()
        self.assertFalse(manager.authorized.is_set())
        self.assertIsNotNone(adb.owned)
        self.assertTrue(manager._scan_failed)
        runner.failed_devices = runner.failed_mapping = False
        manager.scan()
        self.assertTrue(manager.authorized.is_set())
        self.assertFalse(manager._scan_failed)
        runner.mappings.discard(("tcp:18765", "tcp:8765"))  # Daemon lost only our mapping.
        manager.scan()
        self.assertTrue(manager.authorized.is_set())
        self.assertEqual(runner.mappings, {("tcp:1111", "tcp:2222"), ("tcp:18765", "tcp:8765"),
                                            ("tcp:18764", "tcp:18764")})
        self.assertEqual(sum(c[-2:-1] == ["tcp:18765"] and "--no-rebind" in c for c in runner.commands), 2)
        self.assertFalse(any("kill-server" in c or "start-server" in c or "reconnect" in c
                             for c, _ in runner.probes))

    def test_negative_physical_proof_retries_after_two_seconds_not_ten(self):
        now, calls = [0.0], []
        def read():
            calls.append(True)
            return [] if len(calls) == 1 else [r"USB\VID_12D1&PID_107E\PHONE"]
        presence = WindowsUsbPresence(read, windows=True, clock=lambda: now[0])
        self.assertFalse(presence("PHONE"))
        now[0] = 1.9
        self.assertFalse(presence("PHONE"))
        self.assertEqual(len(calls), 1)
        now[0] = 2
        self.assertTrue(presence("PHONE"))
        now[0] = 11
        self.assertTrue(presence("PHONE"))
        self.assertEqual(len(calls), 2)

    def test_failed_scans_back_off_serially_and_healthy_scans_reset_delay(self):
        waits, scans = [], [True, True, True, False]
        class Stop:
            def is_set(self):
                return not scans
            def wait(self, delay):
                waits.append(delay)
            def clear(self):
                pass
        manager = UsbManager(SimpleNamespace(), mux=SimpleNamespace(devices=lambda: []))
        manager._stop = Stop()
        manager._wake = manager._stop
        def scan():
            manager._scan_failed = scans.pop(0)
        manager.scan = scan
        manager._run()
        self.assertEqual(waits, [2, 4, 8, 2])


if __name__ == "__main__":
    unittest.main()
