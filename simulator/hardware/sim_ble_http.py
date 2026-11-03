"""Opt-in BLE Wi-Fi command peer with explicit, offline HTTP GET fixtures.

Attach peer.reply with BLE.sim_set_command_peer(). Incoming commands may span
multiple writes. Replies are complete messages; radio timing is not modeled.
Set timeout_ms to the client's response timeout. An idle timeout or reset()
marks an abandoned request; command-looking payload bytes never do.
"""

import json
from utime import ticks_ms, ticks_diff
from sim_flipper_http import FlipperHTTP


class BLEHTTPPeer:
    def __init__(self, responses=None, timeout_ms=10000):
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        self.responses = responses or {}
        self.wifi = FlipperHTTP()
        self.timeout_ms = timeout_ms
        self.reset()

    def reset(self):
        """Explicitly abandon a request, for example when a peer reconnects."""
        self._pending = b""
        self._last_fragment_ms = None
        self._discard = False

    def reply(self, data):
        now = ticks_ms()
        if self._last_fragment_ms is not None and ticks_diff(now, self._last_fragment_ms) >= self.timeout_ms:
            self.reset()
        self._last_fragment_ms = now
        replies = []
        for byte in bytes(data):
            reply = self._feed(bytes((byte,)))
            if reply:
                replies.append(reply)
        return b"\n".join(replies) if replies else None

    @staticmethod
    def _json_state(data):
        """Track structural completion without treating quoted braces as syntax."""
        quoted = escaped = False
        depth = 0
        for byte in data:
            if quoted:
                if escaped:
                    escaped = False
                elif byte == 92:
                    escaped = True
                elif byte == 34:
                    quoted = False
            elif byte == 34:
                quoted = True
            elif byte in (123, 91):
                depth += 1
            elif byte in (125, 93):
                depth -= 1
        return quoted, depth

    def _feed(self, data):
        if self._discard:
            return None
        if not self._pending and data in (b"\r", b"\n", b" ", b"\t"):
            return None
        self._pending += bytes(data)
        pending = self._pending
        if len(pending) > 8192:
            self._pending = b""
            self._discard = True
            return b"[ERROR] BLE command too long"
        # Wi-Fi commands have no newline: JSON payload completion is their
        # boundary. HTTP commands are newline terminated by HTTPBLE.
        if b"\n" not in pending:
            if pending.startswith((b"[GET]", b"[GET/HTTP]")):
                return None
            if b"]" not in pending:
                return None
            if pending.startswith((b"[WIFI/SAVE]", b"[WIFI/AP]")):
                payload = pending.split(b"]", 1)[1].strip()
                quoted, depth = self._json_state(payload)
                if not payload or (payload.startswith(b"{") and (quoted or depth > 0)):
                    return None
        self._pending = b""
        try:
            command = pending.decode("utf-8").strip()
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
