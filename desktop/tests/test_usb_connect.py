"""Explicit dual-ended Connect, fake ADB and synthetic localhost video only."""
import asyncio
from pathlib import Path
import queue
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from aiohttp import ClientSession
from vrization_host.connection import ConnectionCoordinator, UsbConnectService
from vrization_host.gui import HostWindow
from vrization_host.server import HostServer
from vrization_host.usb import AdbReverse, AppleDevice, AppleEndpointUnavailable, UsbManager
from test_native_client_wire import SyntheticJpegSource, RecordingInputSink
from test_server_stop import free_port
from test_usb import FakeAdbRunner


class ConnectRunner(FakeAdbRunner):
    def __init__(self, mappings=()):
        super().__init__(mappings)
        self.attached = "PHONE device usb:1-4\n"
        self.notifications = []
    def __call__(self, command, **kwargs):
        args = command[1:]
        if args == ["devices", "-l"]:
            return SimpleNamespace(returncode=0, stdout=self.attached, stderr="")
        if "shell" in args:
            self.notifications.append(args)
            return SimpleNamespace(returncode=0, stdout="Starting: Intent", stderr="")
        return super().__call__(command, **kwargs)


class UsbConnectTests(unittest.TestCase):
    def manager(self, runner):
        server = SimpleNamespace(port=8765, running=False, controller=SimpleNamespace(connected=False))
        manager = UsbManager(server, adb=AdbReverse(Path("fixture/adb.exe"), runner),
                             mux=SimpleNamespace(devices=lambda: []))
        manager.set_enabled(True)
        return manager

    def test_detection_owns_two_maps_without_starting_or_notifying_and_cleanup_is_targeted(self):
        runner = ConnectRunner([("tcp:1111", "tcp:2222")])
        manager = self.manager(runner)
        manager.scan()
        manager.scan()
        self.assertTrue(manager.authorized.is_set())
        self.assertTrue(manager.control_authorized.is_set())
        self.assertFalse(manager.server.running)
        self.assertEqual(runner.notifications, [])
        self.assertEqual(runner.mappings, {("tcp:1111", "tcp:2222"), ("tcp:18765", "tcp:8765"),
                                            ("tcp:18764", "tcp:18764")})
        manager.set_enabled(False)
        manager.scan()
        self.assertFalse(manager.authorized.is_set())
        self.assertFalse(manager.control_authorized.is_set())
        self.assertEqual(runner.mappings, {("tcp:1111", "tcp:2222")})

    def test_explicit_connect_waits_for_device_then_sends_targeted_intent_exactly_once(self):
        runner = ConnectRunner()
        runner.attached = ""
        manager = self.manager(runner)
        manager.server.running = True
        self.assertTrue(manager.request_connect())
        manager.scan()
        self.assertEqual(runner.notifications, [])
        runner.attached = "PHONE device usb:1-4\n"
        manager.scan()
        manager.scan()
        self.assertEqual(runner.notifications, [["-s", "PHONE", "shell", "am", "start", "--activity-single-top",
                            "--activity-clear-top", "-n", "org.vrization.app/.MainActivity",
                            "--ez", "vrization_connect_usb", "true"]])
        self.assertTrue(manager.request_connect())
        manager.scan()
        self.assertEqual(len(runner.notifications), 2)  # Two actual user gestures.

    def test_cancel_expire_and_unauthorized_devices_never_receive_intent(self):
        runner = ConnectRunner()
        manager = self.manager(runner)
        manager.server.running = True
        manager.request_connect()
        manager.cancel_connect()
        manager.scan()
        manager.request_connect()
        manager._connect_pending = (manager._connect_generation, 0)
        manager.scan()
        for devices in ("PHONE unauthorized usb:1-4\n", "PHONE offline usb:1-4\n",
                        "emulator-5556 device\n192.0.2.1:5555 device\n"):
            runner.attached = devices
            manager.request_connect()
            manager.scan()
        manager.set_enabled(False)
        self.assertFalse(manager.request_connect())
        manager.scan()
        self.assertEqual(runner.notifications, [])

    def test_foreign_control_map_is_never_claimed_or_notified(self):
        for local in ("tcp:18764", "tcp:9000"):
            with self.subTest(local=local):
                runner = ConnectRunner([("tcp:18764", local)])
                manager = self.manager(runner)
                manager.server.running = True
                manager.request_connect()
                manager.scan()
                self.assertTrue(manager.authorized.is_set())
                self.assertFalse(manager.control_authorized.is_set())
                self.assertIsNone(manager.control_adb.owned)
                self.assertEqual(runner.notifications, [])
                manager.set_enabled(False)
                manager.scan()
                self.assertEqual(runner.mappings, {("tcp:18764", local)})

    def test_multiple_devices_require_explicit_selection(self):
        runner = ConnectRunner()
        runner.attached = "PHONE device usb:1-4\nSECOND device usb:1-5\n"
        manager = self.manager(runner)
        manager.server.running = True
        manager.request_connect()
        manager.scan()
        self.assertEqual(runner.notifications, [])
        self.assertFalse(manager.control_authorized.is_set())
        manager.preferred_serial = "SECOND"
        manager.scan()
        self.assertEqual(runner.notifications[0][:2], ["-s", "SECOND"])

    def test_active_gui_connect_retries_phone_once_and_phone_request_never_echoes_notify(self):
        window = HostWindow.__new__(HostWindow)
        window._stop_in_progress = False
        window.server = SimpleNamespace(running=True)
        notified = []
        window.usb = SimpleNamespace(request_connect=lambda: notified.append(True))
        self.assertTrue(window.start())
        self.assertTrue(window.start(notify_phone=False))
        self.assertEqual(notified, [True])
        window._stop_in_progress = True
        self.assertFalse(window.start())
        self.assertEqual(notified, [True])

    def test_phone_control_event_uses_ui_adapter_without_notifying_phone_and_stop_invalidates_it(self):
        window = HostWindow.__new__(HostWindow)
        window._stop_in_progress = False
        window._stop_generation = 0
        window.events = queue.SimpleQueue()
        window.root = SimpleNamespace(after=lambda *args: None)
        window._refresh_input_status = Mock()
        window.connection = ConnectionCoordinator(window.events.put, lambda: False)
        calls = []
        def start(**kwargs):
            calls.append(kwargs)
            return True
        window.start = start
        pending = window.connection.request()
        window._pump()
        self.assertTrue(pending.result())
        self.assertEqual(calls, [{"notify_phone": False}])
        cancelled = window.connection.request()
        window.connection.cancel()
        window._pump()
        self.assertFalse(cancelled.result())
        self.assertEqual(len(calls), 1)


class ControlVideoIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_control_survives_video_stop_and_can_request_new_video_through_ui_adapter(self):
        events = queue.SimpleQueue()
        host = HostServer(SyntheticJpegSource(), RecordingInputSink(), host="127.0.0.1", port=free_port())
        coordinator = ConnectionCoordinator(events.put, lambda: host.running,
                         lambda: bool(host._thread and host._thread.is_alive() and host._stopping.is_set()))
        control = UsbConnectService(coordinator, lambda: True, port=0)
        await asyncio.to_thread(control.start)
        try:
            async with ClientSession() as client:
                for _ in range(2):
                    pending = asyncio.create_task(client.post(f"http://127.0.0.1:{control.port}/connect"))
                    for _ in range(100):
                        if not events.empty():
                            break
                        await asyncio.sleep(.01)
                    event = events.get_nowait()
                    self.assertTrue(coordinator.accept(event["request"]))
                    await asyncio.to_thread(host.start)
                    coordinator.complete(event["request"], host.running)
                    response = await pending
                    self.assertEqual(response.status, 200)
                    self.assertTrue((await response.json())["ready"])
                    async with client.get(f"http://127.0.0.1:{host.port}/health") as health:
                        self.assertTrue((await health.json())["running"])
                    coordinator.cancel()
                    self.assertTrue(await asyncio.to_thread(host.stop))
                    self.assertTrue(control._thread.is_alive())
                    self.assertFalse(host.controller.armed)
        finally:
            await asyncio.to_thread(host.stop)
            await asyncio.to_thread(control.stop)


class IosStopGateTests(unittest.TestCase):
    def manager(self, *, acknowledgment=False):
        runner = ConnectRunner()
        runner.attached = ""
        device = AppleDevice(1, "FIXTURE")
        self.peer = Mock()
        self.mux = SimpleNamespace(devices=lambda: [device], connect=Mock(return_value=self.peer))
        self.requests = []
        self.notify, self.stop_notify = Mock(), Mock(return_value=acknowledgment)
        host = SimpleNamespace(port=8765, running=False, controller=SimpleNamespace(connected=False))
        manager = UsbManager(host, adb=AdbReverse(Path("fixture/adb.exe"), runner), mux=self.mux,
                             start_request=lambda: self.requests.append(True) or True,
                             ios_notify=self.notify, ios_stop_notify=self.stop_notify)
        self.relay = manager.relay = Mock()
        manager.set_enabled(True)
        manager.scan()  # Detecting a phone does not request capture.
        self.assertEqual(self.requests, [])
        self.relay.reset_mock()
        return manager, device

    def test_unconfirmed_stop_cannot_reuse_pending_listener_or_start_video(self):
        manager, device = self.manager()
        manager.request_stop_phone()
        manager.scan()
        manager.scan()
        self.stop_notify.assert_called_once_with(self.mux, device)
        self.relay.request_stop.assert_called_once()
        self.relay.start.assert_not_called()
        self.assertFalse(manager._ios_request_start())
        self.assertEqual(self.requests, [])
        self.assertFalse(manager.server.running)
        self.assertEqual(self.peer.close.call_count, 2)
        self.notify.assert_not_called()

    def test_paired_refusal_reopens_detection_but_other_failures_do_not(self):
        manager, _ = self.manager()
        manager.request_stop_phone()
        for error in (PermissionError("trust absent"), ConnectionError("service absent"), TimeoutError("timeout")):
            self.mux.connect.side_effect = error
            manager.scan()
            self.assertFalse(manager._ios_request_start())
            self.relay.start.assert_not_called()
        self.mux.connect.side_effect = AppleEndpointUnavailable("video listener absent")
        manager.scan()
        self.assertFalse(manager._ios_start_blocked)
        self.assertEqual(self.requests, [])
        self.mux.connect.side_effect = None
        manager.scan()
        self.relay.start.assert_called_once()
        self.assertTrue(manager._ios_request_start())  # New native readiness.
        self.assertEqual(self.requests, [True])

    def test_processed_stop_ack_unlocks_without_notifying_connect(self):
        manager, device = self.manager(acknowledgment=True)
        manager.request_stop_phone()
        manager.scan()
        manager.scan()
        self.stop_notify.assert_called_once_with(self.mux, device)
        self.assertFalse(manager._ios_start_blocked)
        self.assertEqual(self.requests, [])
        self.notify.assert_not_called()

    def test_new_explicit_pc_connect_supersedes_unconfirmed_stop_once(self):
        manager, device = self.manager()
        manager.request_stop_phone()
        manager.scan()
        self.assertTrue(manager._ios_start_blocked)
        manager.server.running = True
        self.assertTrue(manager.request_connect())
        manager.scan()
        manager.scan()
        self.assertFalse(manager._ios_start_blocked)
        self.notify.assert_called_once_with(self.mux, device)
        self.stop_notify.assert_called_once()

    def test_late_ack_and_absence_cannot_unlock_a_newer_stop(self):
        manager, device = self.manager()
        manager.request_stop_phone()
        old_generation = manager._ios_generation
        manager.request_connect()
        manager.request_stop_phone()
        manager._ios_stop_confirmed(old_generation, device)
        self.assertTrue(manager._ios_start_blocked)
        self.assertFalse(manager._ios_request_start())
        # A captured callback from before Stop likewise cannot clear its gate.
        manager._ios_stop_confirmed(old_generation - 1, device)
        self.assertTrue(manager._ios_start_blocked)

    def test_old_inflight_stop_ack_is_rejected_after_a_new_stop_gesture(self):
        manager, _ = self.manager()
        def old_ack(mux, device):
            manager.request_connect()
            manager.request_stop_phone()
            return True
        manager.ios_stop_notify = old_ack
        manager.request_stop_phone()
        manager._service_ios_stop()
        self.assertTrue(manager._ios_start_blocked)
        self.assertIsNotNone(manager._ios_stop_pending)
        self.assertFalse(manager._ios_request_start())

    def test_stop_deadline_and_missing_device_never_timeout_unlock(self):
        manager, _ = self.manager()
        manager.request_stop_phone()
        self.mux.devices = lambda: []
        manager._ios_stop_pending = (manager._ios_generation, 0)
        manager.scan()
        self.assertTrue(manager._ios_start_blocked)
        self.assertIsNone(manager._ios_stop_pending)
        self.stop_notify.assert_not_called()
        self.relay.start.assert_not_called()
        self.assertFalse(manager._ios_request_start())

    def test_same_phone_replug_uses_fresh_device_id_and_refusal_can_clear_gate(self):
        manager, device = self.manager()
        manager.request_stop_phone()
        replugged = AppleDevice(17, device.serial)
        self.mux.devices = lambda: [replugged]
        self.mux.connect.side_effect = AppleEndpointUnavailable("new paired endpoint is closed")
        manager.scan()
        self.stop_notify.assert_called_once_with(self.mux, replugged)
        self.mux.connect.assert_called_once_with(replugged)
        self.assertFalse(manager._ios_start_blocked)
        self.assertEqual(self.requests, [])

    def test_reused_id_on_different_phone_is_not_sent_old_stop_or_permanently_blocked(self):
        manager, device = self.manager()
        manager.request_stop_phone()
        other = AppleDevice(device.device_id, "DIFFERENT-FIXTURE")
        self.mux.devices = lambda: [other]
        manager.scan()
        self.stop_notify.assert_not_called()
        self.mux.connect.assert_not_called()
        self.relay.start.assert_called_once()
        self.assertTrue(manager._ios_start_blocked)  # Retain original phone's gate.
        self.assertTrue(manager._ios_request_start())  # New phone's readiness.
        self.assertEqual(self.requests, [True])

    def test_captured_readiness_cannot_queue_after_stop_ack_new_gesture_or_selection(self):
        for transition in ("stop_ack", "new_connect", "selection"):
            with self.subTest(transition=transition):
                manager, device = self.manager(acknowledgment=True)
                manager.scan()
                old_readiness = self.relay.start.call_args.kwargs["start_request"]
                if transition == "stop_ack":
                    manager.request_stop_phone()
                    manager.scan()
                    self.assertFalse(manager._ios_start_blocked)
                elif transition == "new_connect":
                    manager.request_connect()
                else:
                    self.mux.devices = lambda: [AppleDevice(9, "NEW-FIXTURE")]
                    manager.scan()
                self.assertFalse(old_readiness())
                self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
