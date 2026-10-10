import asyncio
import threading

import pytest
from aiohttp.test_utils import TestClient, TestServer

from vrization_host.connection import ConnectionCoordinator, UsbConnectService


def test_requests_coalesce_and_stop_invalidates_queued_connect():
    events = []
    coordinator = ConnectionCoordinator(events.append, lambda: False)
    first = coordinator.request()
    assert coordinator.request() is first
    assert len(events) == 1 and coordinator.accept(first)
    coordinator.cancel()
    assert first.result() is False and not coordinator.accept(first)
    second = coordinator.request()
    assert second is not first and coordinator.accept(second)
    coordinator.complete(second, True)
    assert second.result() is True and not coordinator.accept(second)


def test_close_rejects_future_requests_and_active_server_needs_no_new_start():
    events = []
    coordinator = ConnectionCoordinator(events.append, lambda: True)
    assert coordinator.request().result() is True and not events
    coordinator.cancel(close=True)
    assert coordinator.request().result() is False and not events


def test_stopping_rejects_connect_without_queuing_a_late_start():
    events, stopping = [], [True]
    coordinator = ConnectionCoordinator(events.append, lambda: False, lambda: stopping[0])
    assert coordinator.request().result() is False and not events
    stopping[0] = False
    pending = coordinator.request()
    stopping[0] = True
    assert not coordinator.accept(pending)
    coordinator.cancel()
    assert pending.result() is False


@pytest.mark.asyncio
async def test_trusted_phone_connect_starts_through_adapter_once():
    events = []
    coordinator = ConnectionCoordinator(events.append, lambda: False)
    control = UsbConnectService(coordinator, lambda: True)
    async with TestClient(TestServer(control.make_app())) as client:
        request = asyncio.create_task(client.post('/connect', headers={'Host': '127.0.0.1:18764'}))
        for _ in range(30):
            if events:
                break
            await asyncio.sleep(.01)
        assert len(events) == 1
        future = events[0]['request']
        assert coordinator.accept(future)
        coordinator.complete(future, True)
        response = await request
        assert response.status == 200
        assert await response.json() == {'v': 1, 'name': 'VRization', 'ready': True}
        assert response.headers['Cache-Control'] == 'no-store'


@pytest.mark.asyncio
@pytest.mark.parametrize('authorized,headers', [
    (False, {'Host': '127.0.0.1:18764'}),
    (True, {'Host': 'attacker.example:18764'}),
    (True, {'Host': '127.0.0.1:18764', 'Origin': 'https://attacker.example'}),
    (True, {'Host': '127.0.0.1:8765'}),
])
async def test_control_rejects_missing_usb_trust_and_browser_requests(authorized, headers):
    events = []
    control = UsbConnectService(ConnectionCoordinator(events.append, lambda: False), lambda: authorized)
    async with TestClient(TestServer(control.make_app())) as client:
        response = await client.post('/connect', headers=headers)
        assert response.status == 403 and not events


@pytest.mark.asyncio
async def test_stop_during_phone_request_does_not_start_late_event():
    events = []
    coordinator = ConnectionCoordinator(events.append, lambda: False)
    control = UsbConnectService(coordinator, lambda: True)
    async with TestClient(TestServer(control.make_app())) as client:
        pending = asyncio.create_task(client.post('/connect', headers={'Host': 'localhost:18764'}))
        for _ in range(30):
            if events:
                break
            await asyncio.sleep(.01)
        coordinator.cancel()
        assert not coordinator.accept(events[0]['request'])
        assert (await pending).status == 503


@pytest.mark.asyncio
async def test_ui_timeout_rejects_late_start_without_retrying_itself():
    events = []
    coordinator = ConnectionCoordinator(events.append, lambda: False)
    control = UsbConnectService(coordinator, lambda: True, timeout=.03)
    async with TestClient(TestServer(control.make_app())) as client:
        response = await client.post('/connect', headers={'Host': '127.0.0.1:18764'})
        assert response.status == 503 and len(events) == 1
        assert not coordinator.accept(events[0]['request'])


@pytest.mark.asyncio
async def test_control_coalesces_http_requests_and_rejects_revoked_trust_before_response():
    events, authorized = [], [True]
    coordinator = ConnectionCoordinator(events.append, lambda: False)
    control = UsbConnectService(coordinator, lambda: authorized[0])
    async with TestClient(TestServer(control.make_app())) as client:
        requests = [asyncio.create_task(client.post('/connect', headers={'Host': 'localhost:18764'})) for _ in range(2)]
        await asyncio.sleep(.03)
        assert len(events) == 1
        authorized[0] = False
        coordinator.complete(events[0]['request'], True)
        responses = await asyncio.gather(*requests)
        assert [response.status for response in responses] == [503, 503]


@pytest.mark.asyncio
async def test_oversized_body_cannot_queue_connect():
    events = []
    control = UsbConnectService(ConnectionCoordinator(events.append, lambda: False), lambda: True)
    async with TestClient(TestServer(control.make_app())) as client:
        response = await client.post('/connect', data=b'x' * 1025, headers={'Host': 'localhost:18764'})
        assert response.status == 413 and not events


def test_control_service_can_close_without_an_embedding_event_loop():
    control = UsbConnectService(ConnectionCoordinator(lambda event: None, lambda: False), lambda: False, port=0)
    control.start()
    assert control.port > 0 and control._thread.is_alive()
    control.stop()
    assert not control._thread.is_alive()
