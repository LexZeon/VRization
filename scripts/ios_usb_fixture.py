"""A fake usbmux daemon for CI; it tunnels to the Mac's real iOS Simulator.

This validates the original relay and native framed-TCP client, not a USB cable,
Apple driver, physical iPhone, trust prompt or USB throughput.
"""
from contextlib import suppress
from http.server import ThreadingHTTPServer
import plistlib
import socket
import socketserver
import struct
import threading


class LoopbackObservationServer(ThreadingHTTPServer):
    """Numeric local fixture binding must not depend on reverse DNS readiness."""
    def server_bind(self):
        if self.server_address[0] != "127.0.0.1":
            raise ValueError("The iOS observation fixture must stay on loopback")
        # HTTPServer.server_bind calls getfqdn/gethostbyaddr even for 127.0.0.1.
        # A captured Mac startup stack stalled there; this local server needs
        # neither a system hostname nor an external DNS lookup.
        socketserver.TCPServer.server_bind(self)
        self.server_name = "localhost"
        self.server_port = self.server_address[1]


def receive_exact(stream, size):
    result = bytearray()
    while len(result) < size:
        data = stream.recv(size - len(result))
        if not data:
            raise ConnectionError("Fixture peer disconnected")
        result.extend(data)
    return bytes(result)


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        stream = self.request
        stream.settimeout(3)
        try:
            length, version, kind, tag = struct.unpack("<IIII", receive_exact(stream, 16))
            if not 16 <= length <= 65536 or version != 1 or kind != 8:
                return
            request = plistlib.loads(receive_exact(stream, length - 16))
            if request.get("MessageType") == "ListDevices":
                self.reply({"DeviceList": [{"DeviceID": 1, "Properties": {
                    "ConnectionType": "USB", "SerialNumber": "VRization-Simulated-USB-Fixture"}}]}, tag)
            elif request.get("MessageType") == "ReadPairRecord":
                self.reply({"PairRecordData": plistlib.dumps({"HostID": "VRization-Fixture",
                    "SystemBUID": "VRization-Fixture"})}, tag)
            elif request.get("MessageType") == "Connect":
                port = socket.ntohs(request.get("PortNumber", 0))
                if request.get("DeviceID") != 1 or port not in (18766, 18767):
                    self.reply({"Number": 3}, tag)
                    return
                try:
                    phone = socket.create_connection(("127.0.0.1", port), timeout=1)
                except OSError:
                    self.reply({"Number": 3}, tag)
                    return
                self.reply({"Number": 0}, tag)
                stream.settimeout(None); phone.settimeout(None)
                with phone:
                    done = threading.Event()

                    def pump(source, target):
                        try:
                            while not done.is_set():
                                data = source.recv(32768)
                                if not data:
                                    break
                                target.sendall(data)
                        except OSError:
                            pass
                        finally:
                            done.set()
                            for endpoint in (source, target):
                                with suppress(OSError):
                                    endpoint.shutdown(socket.SHUT_RDWR)

                    worker = threading.Thread(target=pump, args=(stream, phone), daemon=True)
                    worker.start()
                    pump(phone, stream)
                    worker.join(timeout=2)
        except (OSError, ValueError, plistlib.InvalidFileException):
            return

    def reply(self, response, tag):
        payload = plistlib.dumps(response)
        self.request.sendall(struct.pack("<IIII", 16 + len(payload), 1, 8, tag) + payload)


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class SimulatedAppleMux:
    def __init__(self):
        self.server = Server(("127.0.0.1", 0), Handler)
        self.address = self.server.server_address
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class NoAndroid:
    def devices(self):
        return []

    def release(self):
        pass
