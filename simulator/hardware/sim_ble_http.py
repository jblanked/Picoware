"""Opt-in BLE Wi-Fi command peer with explicit, offline HTTP GET fixtures.

Attach peer.reply with BLE.sim_set_command_peer(). Replies are complete
messages; this does not model ATT fragmentation or radio timing.
"""

import json
from sim_flipper_http import FlipperHTTP


class BLEHTTPPeer:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.wifi = FlipperHTTP()

    def reply(self, data):
        try:
            command = bytes(data).decode("utf-8").strip()
            if command.startswith("[GET/HTTP]"):
                url = json.loads(command[len("[GET/HTTP]"):])["url"]
            elif command.startswith("[GET]"):
                url = command[len("[GET]"):]
            else:
                return self.wifi._command(command).encode("utf-8")
            body = self.responses.get(url)
            if body is None:
                return b"[ERROR] No BLE HTTP fixture for URL"
            return body.encode("utf-8") if isinstance(body, str) else bytes(body)
        except (ValueError, KeyError, TypeError, UnicodeError):
            return b"[ERROR] Invalid BLE command"
