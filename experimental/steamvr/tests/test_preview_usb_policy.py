"""USB authority regressions: real loopback HTTP, synthetic video, fake USB only."""
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from aiohttp.test_utils import TestClient, TestServer, make_mocked_request

from vrization_host.connection import ConnectionCoordinator, UsbConnectService
from vrization_host.server import HostServer
from vrization_host.usb import AdbReverse, AppleDevice, UsbManager, pack_frame
from vrization_steamvr.host import PreviewHost
from preview_fixtures import RecordingMouse, RecordingPoseSink, SyntheticStereoSource
from test_ios_usb import OwnedSocket
from test_usb_connect import ConnectRunner


def ordinary(**kwargs):
    return HostServer(capture_source=SyntheticStereoSource(), input_sink=RecordingMouse(), **kwargs)


def preview(route="direct-phone", **kwargs):
    return PreviewHost(route=route, capture_source=SyntheticStereoSource(), input_sink=RecordingMouse(),
                       pose_sink=RecordingPoseSink() if route == "steamvr-phone" else None, **kwargs)


async def duplicate_hosts(port, path, authority, method="GET"):
    # aiohttp's client deduplicates identical Host values. Send actual separate
    # header lines so the server's single-Host guard is exercised on the wire.
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    try:
        request = (f"{method} {path} HTTP/1.1\r\nHost: {authority}\r\nHost: {authority}\r\n"
                   "Content-Length: 0\r\nConnection: close\r\n\r\n")
        writer.write(request.encode("ascii"))
        await writer.drain()
        response = await asyncio.wait_for(reader.read(), 3)
        return int(response.split(b" ", 2)[1]), response
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.parametrize("ports", [None, 18775, "18775", {18775}, {"port": 18775},
                                   (True,), ("18775",), (18775.0,), (0,), (-1,), (65536,), ((),)])
def test_bootstrap_allowlist_rejects_nonexplicit_or_invalid_port_configuration(ports):
    with pytest.raises(ValueError, match="USB bootstrap ports"):
        ordinary(usb_bootstrap_ports=ports)


@pytest.mark.asyncio
@pytest.mark.parametrize("factory,video_port,forbidden", [
    (ordinary, 18765, (18775,)),
    (preview, 18775, (18765, 18774, 18776, 18777)),
    (lambda **kwargs: preview("steamvr-phone", **kwargs), 18775, (18765, 18774, 18776, 18777)),
])
async def test_real_bootstrap_uses_only_this_variant_video_port_and_actual_server(factory, video_port, forbidden):
    host = factory(usb_authorized=lambda: True)
    async with TestClient(TestServer(host.make_app(), host="127.0.0.1")) as client:
        host.port, host.running = client.server.port, True
        for name in ("127.0.0.1", "localhost", "[::1]"):
            for port in (host.port, video_port):
                response = await client.get("/usb-bootstrap", headers={"Host": f"{name}:{port}"})
                assert response.status == 200
                assert await response.json() == {"v": 1, "name": "VRization", "version": host._host_version(),
                                                  "port": host.port, "token": host.token}
                assert response.headers["Cache-Control"] == "no-store"
                assert response.headers["X-Content-Type-Options"] == "nosniff"
        for port in set(forbidden) - {host.port}:
            response = await client.get("/usb-bootstrap", headers={"Host": f"127.0.0.1:{port}"})
            assert response.status == 403 and "token" not in await response.json()


@pytest.mark.asyncio
async def test_bootstrap_copies_explicit_allowlist_and_empty_policy_is_server_only():
    ports = [18775, 18775]
    host = ordinary(usb_bootstrap_ports=ports, usb_authorized=lambda: True)
    ports.append(18776)  # A caller's later mutation must not widen token access.
    async with TestClient(TestServer(host.make_app())) as client:
        host.port, host.running = client.server.port, True
        assert (await client.get("/usb-bootstrap", headers={"Host": "localhost:18775"})).status == 200
        for port in {18765, 18776} - {host.port}:
            response = await client.get("/usb-bootstrap", headers={"Host": f"localhost:{port}"})
            assert response.status == 403
    host = ordinary(usb_bootstrap_ports=(), usb_authorized=lambda: True)
    async with TestClient(TestServer(host.make_app())) as client:
        host.port, host.running = client.server.port, True
        assert (await client.get("/usb-bootstrap")).status == 200
        if host.port != 18765:
            assert (await client.get("/usb-bootstrap", headers={"Host": "localhost:18765"})).status == 403


@pytest.mark.asyncio
async def test_preview_bootstrap_keeps_loopback_single_host_origin_and_usb_authorization_boundaries():
    authorized = Mock(return_value=True)
    host = preview(usb_authorized=authorized)
    async with TestClient(TestServer(host.make_app())) as client:
        host.port, host.running = client.server.port, True
        bad_headers = [
            {"Host": "attacker.example:18775"}, {"Host": "127.0.0.1.attacker.example:18775"},
            {"Host": "127.0.0.1:18775@attacker.example"}, {"Host": "127.0.0.1:018775"},
            *({"Host": "localhost:18775", "Origin": value} for value in ("", "null", "https://attacker.example")),
        ]
        for headers in bad_headers:
            response = await client.get("/usb-bootstrap", headers=headers)
            assert response.status == 403 and "token" not in await response.json(), headers
        status, response = await duplicate_hosts(client.server.port, "/usb-bootstrap", "127.0.0.1:18775")
        # Newer aiohttp rejects duplicate Host in its HTTP parser (400); older
        # parsers reach the application's independent single-Host guard (403).
        assert status in (400, 403) and b'"token"' not in response
        duplicate = make_mocked_request("GET", "/usb-bootstrap",
            headers=[("Host", "localhost:18775"), ("Host", "localhost:18775")],
            transport=SimpleNamespace(get_extra_info=lambda *args: ("127.0.0.1", 1234)))
        assert (await host._usb_bootstrap(duplicate)).status == 403
        request = make_mocked_request("GET", "/usb-bootstrap",
            headers={"Host": "localhost:18775", "X-Forwarded-For": "127.0.0.1"},
            transport=SimpleNamespace(get_extra_info=lambda *args: ("192.0.2.4", 1234)))
        assert (await host._usb_bootstrap(request)).status == 403
        authorized.assert_not_called()
        authorized.return_value = False
        assert (await client.get("/usb-bootstrap", headers={"Host": "localhost:18775"})).status == 403
        authorized.side_effect = OSError("fixture USB authorization unavailable")
        assert (await client.get("/usb-bootstrap", headers={"Host": "localhost:18775"})).status == 403
        authorized.side_effect, authorized.return_value = None, True
        host.running = False
        assert (await client.get("/usb-bootstrap", headers={"Host": "localhost:18775"})).status == 503
        host.running = True
        host._stopping.set()
        response = await client.get("/usb-bootstrap", headers={"Host": "localhost:18775"})
        assert response.status == 503 and "token" not in await response.json()


@pytest.mark.asyncio
async def test_preview_control_accepts_18774_but_rejects_other_authorities_before_queuing():
    events, arrived = [], asyncio.Event()
    def post(event):
        events.append(event)
        arrived.set()
    coordinator = ConnectionCoordinator(post, lambda: False)
    control = UsbConnectService(coordinator, lambda: True, port=18774)
    async with TestClient(TestServer(control.make_app())) as client:
        for headers in ({"Host": "localhost:18764"}, {"Host": "localhost:18775"},
                        {"Host": "localhost:18777"}, {"Host": "attacker.example:18774"},
                        {"Host": "localhost:18774", "Origin": "null"}):
            assert (await client.post("/connect", headers=headers)).status == 403
        status, _ = await duplicate_hosts(client.server.port, "/connect", "localhost:18774", "POST")
        assert status in (400, 403)
        duplicate = make_mocked_request("POST", "/connect",
            headers=[("Host", "localhost:18774"), ("Host", "localhost:18774")],
            transport=SimpleNamespace(get_extra_info=lambda *args: ("127.0.0.1", 1234)))
        assert (await control._connect(duplicate)).status == 403
        assert not events
        pending = asyncio.create_task(client.post("/connect", headers={"Host": "localhost:18774"}))
        await asyncio.wait_for(arrived.wait(), 2)
        future = events[0]["request"]
        assert coordinator.accept(future)
        coordinator.complete(future, True)
        response = await pending
        assert response.status == 200
        assert await response.json() == {"v": 1, "name": "VRization", "ready": True}


@pytest.mark.asyncio
async def test_preview_control_stop_invalidates_pending_request_without_resuming_input():
    arrived, stopping, events = asyncio.Event(), [False], []
    host = preview()
    host.disarm("fixture emergency stop")
    def post(event):
        events.append(event)
        arrived.set()
    coordinator = ConnectionCoordinator(post, lambda: False, lambda: stopping[0])
    control = UsbConnectService(coordinator, lambda: True, port=18774)
    async with TestClient(TestServer(control.make_app())) as client:
        pending = asyncio.create_task(client.post("/connect", headers={"Host": "localhost:18774"}))
        await asyncio.wait_for(arrived.wait(), 2)
        stopping[0] = True
        coordinator.cancel()
        assert (await pending).status == 503
        assert not coordinator.accept(events[0]["request"])
        assert (await client.post("/connect", headers={"Host": "localhost:18774"})).status == 503
        assert len(events) == 1
        assert host.controller.suspended and not host.controller.armed


def test_preview_usb_maps_and_explicit_activity_target_do_not_use_ordinary_ports():
    runner = ConnectRunner([("tcp:1111", "tcp:2222")])
    server = SimpleNamespace(port=8766, running=False, controller=SimpleNamespace(connected=False))
    manager = UsbManager(server, adb=AdbReverse(Path("fixture/adb.exe"), runner, remote_port=18775),
        mux=SimpleNamespace(devices=lambda: []), android_video_port=18775, android_control_port=18774,
        android_component="org.vrization.steamvr/org.vrization.app.MainActivity", ios_video_port=18776,
        ios_control_port=18777)
    manager.set_enabled(True)
    manager.scan()
    assert runner.mappings == {("tcp:1111", "tcp:2222"), ("tcp:18775", "tcp:8766"),
                               ("tcp:18774", "tcp:18774")}
    assert manager.authorized.is_set() and manager.control_authorized.is_set()
    assert not server.running and not runner.notifications
    server.running = True
    assert manager.request_connect()
    manager.scan()
    assert len(runner.notifications) == 1
    assert "org.vrization.steamvr/org.vrization.app.MainActivity" in runner.notifications[0]
    manager.set_enabled(False)
    manager.scan()
    assert runner.mappings == {("tcp:1111", "tcp:2222")}


def test_preview_ios_connect_stop_and_listener_probe_use_configured_paired_ports():
    device = AppleDevice(1, "FIXTURE")
    server = SimpleNamespace(port=8766, running=False, controller=SimpleNamespace(connected=False))
    mux = Mock()
    manager = UsbManager(server, adb=Mock(), mux=mux, ios_video_port=18776, ios_control_port=18777)
    assert manager.relay.video_port == 18776
    connect_sock = OwnedSocket()
    mux.connect.return_value = connect_sock
    manager.ios_notify(mux, device)
    mux.connect.assert_called_once_with(device, port=18777)
    assert connect_sock.closed and connect_sock.sent == [pack_frame(1, b'{"v":1,"type":"connect"}')]
    stop_sock = OwnedSocket()
    reply = bytearray(pack_frame(1, b'{"v":1,"type":"stopped"}'))
    def recv(size):
        result = bytes(reply[:size])
        del reply[:size]
        return result
    stop_sock.recv = recv
    mux.connect.reset_mock()
    mux.connect.return_value = stop_sock
    assert manager.ios_stop_notify(mux, device) is True
    mux.connect.assert_called_once_with(device, port=18777)
    assert stop_sock.closed and stop_sock.sent == [pack_frame(1, b'{"v":1,"type":"stop"}')]
    video_sock = OwnedSocket()
    mux.connect.reset_mock()
    mux.connect.return_value = video_sock
    manager._probe_ios_stopped(device, 0)
    mux.connect.assert_called_once_with(device, port=18776)
    assert video_sock.closed and not video_sock.sent
