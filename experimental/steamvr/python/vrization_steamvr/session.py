"""Transient, capability-gated stereo metadata outside saved VRSettings."""
import json
import math
from vrization_host.protocol import ProtocolError, parse_message

STEREO = "stereo-sbs"
ORIENTATION = "hmd-orientation"
MAX_SAFE = 9_007_199_254_740_991

class Session:
    def __init__(self, route):
        if route not in {"direct-phone", "steamvr-phone"}:
            raise ValueError("Unknown phone route")
        self.route = route
        self.epoch = 0
        self.accepted = False

    def open(self, epoch):
        self.epoch = epoch
        self.accepted = self.route == "direct-phone"

    def close(self):
        self.accepted = False

    def negotiate(self, capabilities):
        if self.route == "steamvr-phone" and not {STEREO, ORIENTATION} <= set(capabilities):
            raise ProtocolError("SteamVR phone needs stereo-sbs and hmd-orientation capabilities")
        self.accepted = True

    def descriptor(self):
        virtual = self.route == "steamvr-phone"
        return {"v": 1, "epoch": self.epoch, "accepted": self.accepted,
                "streamLayout": "sbs" if virtual else "mono",
                "inputTarget": "virtual-hmd" if virtual else "mouse"}


def parse_preview_message(data):
    if not isinstance(data, str) or len(data.encode("utf-8")) > 4096:
        raise ProtocolError("Message exceeds 4096 bytes")
    try:
        msg = json.loads(data)
    except (ValueError, TypeError) as error:
        raise ProtocolError("Invalid JSON") from error
    if not isinstance(msg, dict) or msg.get("type") != "hmdPose":
        return parse_message(data)
    allowed = {"v", "type", "epoch", "seq", "timeUs", "trackingValid", "q"}
    required = allowed - {"q"}
    if not required <= msg.keys() or msg.keys() - allowed or type(msg["v"]) is not int or msg["v"] != 1:
        raise ProtocolError("Invalid HMD pose fields")
    for key in ("epoch", "seq", "timeUs"):
        if type(msg[key]) is not int or not (1 if key == "epoch" else 0) <= msg[key] <= MAX_SAFE:
            raise ProtocolError("Invalid HMD pose integer")
    if type(msg["trackingValid"]) is not bool:
        raise ProtocolError("Invalid tracking flag")
    if msg["trackingValid"] and "q" not in msg:
        raise ProtocolError("Valid tracking needs a quaternion")
    if "q" in msg:
        q = msg["q"]
        if (not isinstance(q, list) or len(q) != 4 or
                any(type(x) not in (int, float) or not math.isfinite(x) for x in q)):
            raise ProtocolError("Quaternion must contain four finite numbers")
        norm = math.sqrt(sum(x*x for x in q))
        if not .999 <= norm <= 1.001:
            raise ProtocolError("Quaternion must have unit length")
        msg["q"] = tuple(x/norm for x in q)
    return msg
