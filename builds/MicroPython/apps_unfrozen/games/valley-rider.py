from array import array
from math import sin, cos, pi
from random import randint
import micropython
from micropython import const
from ujson import loads as json_loads
from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_NONE,
    BUTTON_SPACE,
    BUTTON_M,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_CENTER,
)

_W = const(96)
_H = const(96)
_N = const(_W * _H)
_W16 = const(_W << 16)
_H16 = const(_H << 16)
_GRASS = const(0)
_WATER = const(1)
_FOREST = const(2)
_ROCK = const(3)
_SNOW = const(4)
_HOUSE = const(5)
_ROAD = const(6)
_BRIDGE = const(7)
_NPC = const(8)
_SHRINE = const(9)
_HORSE = const(10)
_WAYSTONE = const(11)
_BLK = bytes((0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0))
_MAXD = 11.0
_PL = 0.66
_EYE = 1.1
_BASE = (
    (70, 150, 60),
    (50, 100, 200),
    (30, 95, 45),
    (120, 110, 100),
    (240, 245, 250),
    (170, 110, 70),
    (190, 170, 120),
    (130, 90, 50),
    (190, 170, 120),
    (190, 120, 230),
    (130, 90, 50),
    (80, 190, 180),
)
_SKY = (150, 190, 235)
_NAMES = (
    "Grassland",
    "River",
    "Forest",
    "Mountains",
    "Peaks",
    "Town",
    "Road",
    "Bridge",
    "Town",
    "Shrine",
    "Stable",
    "Waystone",
)
_TOWNS = ((12, 78, "Oakhaven"), (78, 18, "Highfall"), (78, 78, "Eastmere"))
_SHRINE_POS = (14, 12)
_WAYSTONE_POS = (83, 48)
_HORSE_POS = (17, 78)
_FOES = (("Wolf", 12, 4, 6), ("Bandit", 16, 5, 12), ("Boar", 20, 6, 9))
_FOE_POS = ((23, 57), (49, 36), (69, 55))
_DIRS = ("E", "SE", "S", "SW", "W", "NW", "N", "NE")
_TURN_SPEED = 0.18
_WALK_SPEED = 0.7
_BACK_SPEED = 0.5
_HORSE_SPEED = 1.8
_HORSE_BACK_SPEED = 1.2
_MP_API = "https://www.jblanked.com/picoware/api/valleyrider/"
_MP_WS = "wss://www.jblanked.com/ws/picoware/valleyrider/"
_MP_MAX_PLAYERS = 4
_MP_MAX_LOBBIES = 4
_MP_SEND_INTERVAL_MS = 200
_MP_REMOTE_TIMEOUT_MS = 30000
_MP_COLORS = (0x07FF, 0xF800, 0xFD20)


def _integer_to_ascii_bytes(value, base=10):
    """Convert an integer to ASCII bytes. Returns the encoded value."""
    negative = value < 0
    if negative:
        value = -value
    digits = b"0123456789abcdef"
    result = bytearray()
    while value:
        result.append(digits[value % base])
        value //= base
    if not result:
        result.append(48)
    left = 0
    right = len(result) - 1
    while left < right:
        digit = result[left]
        result[left] = result[right]
        result[right] = digit
        left += 1
        right -= 1
    return (b"-" if negative else b"") + bytes(result)


def _float_to_ascii_bytes(value, precision=3):
    """Convert a float to fixed-point ASCII bytes. Returns the encoded value."""
    scale = 10**precision
    scaled = int(abs(value) * scale + 0.5)
    integer = _integer_to_ascii_bytes(scaled // scale)
    if value < 0 and scaled:
        integer = b"-" + integer
    fraction = _integer_to_ascii_bytes(scaled % scale)
    return integer + b"." + b"0" * (precision - len(fraction)) + fraction


def _parse_ascii_float(value):
    """Parse a decimal ASCII float. Returns None for invalid input."""
    if not isinstance(value, bytes) or not value or len(value) > 16:
        return None
    sign = 1
    index = 0
    if value[0] == 45:
        sign = -1
        index = 1
    integer = 0
    fraction = 0
    scale = 1
    decimal_seen = False
    digit_seen = False
    while index < len(value):
        character = value[index]
        if character == 46 and not decimal_seen:
            decimal_seen = True
        elif 48 <= character <= 57:
            digit_seen = True
            if decimal_seen:
                fraction = fraction * 10 + character - 48
                scale *= 10
            else:
                integer = integer * 10 + character - 48
        else:
            return None
        index += 1
    if not digit_seen:
        return None
    number = integer + fraction / scale
    return -number if sign < 0 else number


def _pack_multiplayer_message(
    player_id, message_type, x=0.0, y=0.0, heading=0.0, mounted=False
):
    """Pack a multiplayer state or leave packet. Returns bytes."""
    return b",".join(
        (
            player_id,
            message_type,
            _float_to_ascii_bytes(x),
            _float_to_ascii_bytes(y),
            _float_to_ascii_bytes(heading),
            b"1" if mounted else b"0",
        )
    )


def _parse_multiplayer_message(message):
    """Validate and parse a multiplayer packet. Returns its fields or None."""
    if not isinstance(message, bytes) or len(message) > 160:
        return None
    fields = message.split(b",")
    if len(fields) != 6:
        return None
    player_id, message_type, x_bytes, y_bytes, heading_bytes, mounted_bytes = fields
    if not player_id or len(player_id) > 100:
        return None
    if message_type == b"leave":
        return player_id, message_type, 0.0, 0.0, 0.0, False
    if message_type != b"state":
        return None
    x = _parse_ascii_float(x_bytes)
    y = _parse_ascii_float(y_bytes)
    heading = _parse_ascii_float(heading_bytes)
    if x is None or y is None or heading is None:
        return None
    if mounted_bytes not in (b"0", b"1"):
        return None
    return player_id, message_type, x, y, heading, mounted_bytes == b"1"


def _set_multiplayer_error(st, message):
    """Show a multiplayer error and reset an unjoined connection."""
    st.multiplayer_status = str(message)
    st.multiplayer_view = "error"
    if not st.multiplayer_lobby_id:
        st.multiplayer_connection_state = "idle"


def _ensure_multiplayer_player_id(st, view_manager):
    """Create a stable device ID for this session. Returns whether it succeeded."""
    if st.multiplayer_player_id:
        return True
    try:
        from machine import unique_id
        from ubinascii import hexlify
        from utime import ticks_ms

        device_id = unique_id()
    except ImportError as error:
        _set_multiplayer_error(st, "Device ID unavailable")
        view_manager.log("[Valley Rider multiplayer] %s" % error, 2)
        return False
    if not device_id:
        _set_multiplayer_error(st, "Device ID unavailable")
        return False
    timestamp = ticks_ms()
    random_id = timestamp ^ sum(device_id)
    device_id_hex = hexlify(device_id)
    st.multiplayer_player_id = "%s-%x-%x" % (
        device_id_hex.decode(),
        timestamp,
        random_id,
    )
    st.multiplayer_player_id_bytes = (
        device_id_hex
        + b"-"
        + _integer_to_ascii_bytes(timestamp, 16)
        + b"-"
        + _integer_to_ascii_bytes(random_id, 16)
    )
    return True


def _begin_multiplayer_request(view_manager, st, action, payload=None):
    """Start one lobby API request asynchronously. Returns whether it started."""
    from picoware.system.http import HTTP

    if st.multiplayer_http is not None:
        _set_multiplayer_error(st, "A request is already in progress")
        return False
    # wait until websocket is done
    if st.multiplayer_ws and st.multiplayer_ws.is_connected:
        while st.multiplayer_ws.is_running:
            pass
    http = HTTP(thread_manager=view_manager.thread_manager)
    st.multiplayer_http = http
    st.multiplayer_http_action = action
    headers = {
        "Content-Type": "application/json",
        "HTTP_USER_AGENT": "Pico",
        "Setting": "X-Flipper-Redirect",
        "User-Agent": "Raspberry Pi Pico W",
    }
    if action == "list":
        url = "%slobbies/%d/%d/" % (_MP_API, _MP_MAX_PLAYERS, _MP_MAX_LOBBIES)
        started = http.get_async(url, headers=headers)
        status = "Fetching lobbies..."
    else:
        paths = {
            "create": "lobby/create/",
            "join": "lobby/join/",
            "remove": "lobby/remove/",
        }
        path = paths.get(action)
        if path is None:
            http.close()
            st.multiplayer_http = None
            st.multiplayer_http_action = None
            _set_multiplayer_error(st, "Unsupported multiplayer request")
            return False
        started = http.post_async(_MP_API + path, payload, headers=headers)
        status = {
            "create": "Creating lobby...",
            "join": "Joining lobby...",
            "remove": "Leaving lobby...",
        }[action]
    if not started:
        error = http.error or "Could not start the request"
        http.close()
        st.multiplayer_http = None
        st.multiplayer_http_action = None
        if action == "remove":
            _finish_multiplayer_leave(view_manager, st, error)
        else:
            _set_multiplayer_error(st, error)
        return False
    st.multiplayer_status = status
    st.multiplayer_view = "pending"
    return True


def _request_multiplayer_lobbies(view_manager, st):
    """Fetch open Valley Rider lobbies."""
    st.multiplayer_lobbies = []
    st.multiplayer_lobby_index = 0
    _begin_multiplayer_request(view_manager, st, "list")


def _join_multiplayer_lobby(view_manager, st, lobby_id):
    """Request membership in one lobby."""
    if not _ensure_multiplayer_player_id(st, view_manager):
        return
    st.multiplayer_target_lobby_id = lobby_id
    _begin_multiplayer_request(
        view_manager,
        st,
        "join",
        {"lobby_id": lobby_id, "player_id": st.multiplayer_player_id},
    )


def _create_multiplayer_lobby(view_manager, st):
    """Create a lobby and join it when creation succeeds."""
    if not _ensure_multiplayer_player_id(st, view_manager):
        return
    st.multiplayer_target_lobby_id = ""
    _begin_multiplayer_request(
        view_manager,
        st,
        "create",
        {"max_players": _MP_MAX_PLAYERS, "data": {}},
    )


def _multiplayer_response_data(st, text):
    """Decode a lobby response object. Returns None if invalid."""
    try:
        data = json_loads(text)
    except (TypeError, ValueError):
        _set_multiplayer_error(st, "Invalid server response")
        return None
    if not isinstance(data, dict):
        _set_multiplayer_error(st, "Unexpected server response")
        return None
    return data


def _finish_multiplayer_leave(view_manager, st, error=None):
    """Close a lobby session and update its menu state."""
    exit_after = st.multiplayer_exit_after_leave
    notice = st.multiplayer_notice
    st.multiplayer_exit_after_leave = False
    st.multiplayer_notice = ""
    st.multiplayer_connection_state = "error" if error else "idle"
    if not error:
        st.multiplayer_lobby_id = ""
    st.multiplayer_target_lobby_id = ""
    if st.multiplayer_ws is not None:
        st.multiplayer_ws.close()
        st.multiplayer_ws = None
    st.multiplayer_leave_pending = False
    st.remote_players = {}
    st.dirty = True
    if error:
        st.multiplayer_status = "Leave failed: %s" % error
        st.multiplayer_view = "error"
        view_manager.log("[Valley Rider multiplayer] %s" % st.multiplayer_status, 2)
    elif notice:
        st.multiplayer_status = notice
        st.multiplayer_view = "error"
    else:
        st.multiplayer_status = "Left lobby"
        st.multiplayer_view = None if exit_after else "menu"
    if exit_after:
        st.multiplayer_exit_ready = True


def _poll_multiplayer_http(view_manager, st):
    """Apply a completed lobby API response."""
    http = st.multiplayer_http
    if http is None or not http.is_request_complete():
        return
    action = st.multiplayer_http_action
    error = http.error
    response = http.response
    status_code = response.status_code if response is not None else 0
    response_text = response.text if response is not None else ""
    http.close()
    st.multiplayer_http = None
    st.multiplayer_http_action = None
    if action == "remove":
        # Closing the WebSocket can remove the last player's lobby before
        # this cleanup request arrives. Only that specific 404 is success.
        lobby_gone = False
        if status_code == 404:
            try:
                body = json_loads(response_text)
                lobby_gone = isinstance(body, dict) and body.get("error") == "Lobby not found"
            except (TypeError, ValueError):
                pass
        if error:
            _finish_multiplayer_leave(view_manager, st, error)
        elif response is None:
            _finish_multiplayer_leave(view_manager, st, "No HTTP response")
        elif status_code not in (200, 204) and not lobby_gone:
            _finish_multiplayer_leave(view_manager, st, "HTTP %d" % status_code)
        else:
            _finish_multiplayer_leave(view_manager, st)
        return
    if error or response is None:
        st.multiplayer_target_lobby_id = ""
        _set_multiplayer_error(st, "Request failed" if error else "No HTTP response")
        return
    if action == "list":
        if status_code != 200:
            _set_multiplayer_error(st, "Lobby list failed (HTTP %d)" % status_code)
            return
        data = _multiplayer_response_data(st, response_text)
        lobbies = data.get("lobbies") if data is not None else None
        if not isinstance(lobbies, list):
            _set_multiplayer_error(st, "Invalid lobby list")
            return
        for lobby in lobbies[:_MP_MAX_LOBBIES]:
            if not isinstance(lobby, dict):
                continue
            lobby_id = lobby.get("lobby_id")
            count = lobby.get("player_count")
            maximum = lobby.get("max_players")
            if (
                isinstance(lobby_id, str)
                and lobby_id
                and isinstance(count, int)
                and isinstance(maximum, int)
                and 0 <= count < maximum
                and maximum > 0
            ):
                st.multiplayer_lobbies.append(
                    {
                        "lobby_id": lobby_id,
                        "player_count": count,
                        "max_players": maximum,
                    }
                )
        st.multiplayer_lobby_index = 0
        st.multiplayer_view = "lobbies"
        st.multiplayer_status = ""
        return
    if action == "create":
        if status_code not in (200, 201):
            _set_multiplayer_error(st, "Lobby creation failed (HTTP %d)" % status_code)
            return
        data = _multiplayer_response_data(st, response_text)
        lobby_id = data.get("lobby_id") if data is not None else None
        if not isinstance(lobby_id, str) or not lobby_id:
            _set_multiplayer_error(st, "Server returned no lobby ID")
            return
        st.multiplayer_target_lobby_id = lobby_id
        _join_multiplayer_lobby(view_manager, st, lobby_id)
        return
    if action == "join":
        if status_code not in (200, 201):
            st.multiplayer_target_lobby_id = ""
            message = (
                "Lobby is full"
                if status_code == 409
                else (
                    "Lobby not found"
                    if status_code == 404
                    else "Join failed (HTTP %d)" % status_code
                )
            )
            _set_multiplayer_error(st, message)
            return
        st.multiplayer_lobby_id = st.multiplayer_target_lobby_id
        st.multiplayer_target_lobby_id = ""
        _connect_multiplayer(view_manager, st)
        return
    _set_multiplayer_error(st, "Unexpected multiplayer response")


def _connect_multiplayer(view_manager, st):
    """Start the Valley Rider WebSocket session."""
    from picoware.system.websocket import WebSocketAsync

    st.multiplayer_socket_error = ""
    st.multiplayer_connection_state = "connecting"
    st.multiplayer_view = "pending"
    st.multiplayer_status = "Connecting..."
    st.multiplayer_leave_pending = False
    st.multiplayer_ws = WebSocketAsync(
        uri="%s%s/" % (_MP_WS, st.multiplayer_lobby_id),
        on_receive=_on_multiplayer_message,
        thread_manager=view_manager.thread_manager,
        on_start=_on_multiplayer_start,
        on_tick=_on_multiplayer_tick,
        on_close=_on_multiplayer_close,
    )
    if not st.multiplayer_ws.connect():
        _leave_multiplayer(view_manager, st, False, "Connection failed")


def _on_multiplayer_start():
    """Mark the WebSocket active from its worker thread."""
    from utime import ticks_ms

    st = _st
    if st is None or st.multiplayer_connection_state != "connecting":
        return
    st.multiplayer_connection_state = "active"
    st.multiplayer_status = "Connected"
    st.multiplayer_view = None
    st.multiplayer_last_send = ticks_ms()
    st.dirty = True


def _on_multiplayer_close():
    """Flag a closed WebSocket for main-loop cleanup."""
    st = _st
    if st is not None and st.multiplayer_connection_state == "active":
        st.multiplayer_connection_state = "lost"


def _on_multiplayer_tick(websocket):
    """Send player state and expire peers in the WebSocket worker."""
    from utime import ticks_diff, ticks_ms

    st = _st
    if st is None:
        return
    if st.multiplayer_leave_pending:
        st.multiplayer_leave_pending = False
        packet = _pack_multiplayer_message(st.multiplayer_player_id_bytes, b"leave")
        websocket.send(packet)
    if st.multiplayer_connection_state != "active":
        return
    now = ticks_ms()
    for player_id, remote in list(st.remote_players.items()):
        if ticks_diff(now, remote["last_seen"]) > _MP_REMOTE_TIMEOUT_MS:
            del st.remote_players[player_id]
            st.dirty = True
    if ticks_diff(now, st.multiplayer_last_send) < _MP_SEND_INTERVAL_MS:
        return
    st.multiplayer_last_send = now
    packet = _pack_multiplayer_message(
        st.multiplayer_player_id_bytes,
        b"state",
        st.px,
        st.py,
        st.pa,
        st.mounted,
    )
    if not websocket.send(packet):
        st.multiplayer_socket_error = websocket.error or "WebSocket send failed"
        st.multiplayer_connection_state = "lost"


def _on_multiplayer_message(data):
    """Parse and apply packets in the WebSocket worker."""
    from utime import ticks_ms

    st = _st
    if st is None or st.multiplayer_connection_state not in ("connecting", "active"):
        return
    if data is None:
        st.multiplayer_connection_state = "lost"
        return
    if isinstance(data, Exception):
        st.multiplayer_socket_error = str(data)
        st.multiplayer_connection_state = (
            "connect_error"
            if st.multiplayer_connection_state == "connecting"
            else "lost"
        )
        return
    if data == "PONG":
        return
    if not isinstance(data, bytes):
        st.multiplayer_socket_error = "Expected a binary WebSocket message"
        st.multiplayer_connection_state = "lost"
        return
    packet = _parse_multiplayer_message(data)
    if packet is None:
        return
    player_id, message_type, x, y, heading, mounted = packet
    if player_id == st.multiplayer_player_id_bytes:
        return
    if message_type == b"leave":
        if st.remote_players.pop(player_id, None) is not None:
            st.dirty = True
        return
    if not (0.0 <= x < _W and 0.0 <= y < _H and -1000.0 <= heading <= 1000.0):
        return
    remote = st.remote_players.get(player_id)
    if remote is None:
        if len(st.remote_players) >= _MP_MAX_PLAYERS - 1:
            return
        index = len(st.remote_players)
        remote = {"color": _MP_COLORS[index]}
        st.remote_players[player_id] = remote
    remote["x"] = x
    remote["y"] = y
    remote["heading"] = heading
    remote["mounted"] = mounted
    remote["last_seen"] = ticks_ms()
    st.dirty = True


def _leave_multiplayer(view_manager, st, exit_after, notice=""):
    """Request server-side lobby removal and queue the leave packet."""
    st.multiplayer_exit_after_leave = exit_after
    st.multiplayer_notice = notice
    st.multiplayer_leave_pending = st.multiplayer_ws is not None
    st.multiplayer_connection_state = "leaving"
    st.multiplayer_view = "pending"
    if not st.multiplayer_lobby_id:
        _finish_multiplayer_leave(view_manager, st)
        return
    if st.multiplayer_ws is not None:
        st.multiplayer_ws.close()
        st.multiplayer_ws = None
    st.multiplayer_status = notice or "Leaving lobby..."
    _begin_multiplayer_request(
        view_manager,
        st,
        "remove",
        {"lobby_id": st.multiplayer_lobby_id, "player_id": st.multiplayer_player_id},
    )


def _multiplayer_input(view_manager, st, button):
    """Handle multiplayer menu input. Returns whether the button was consumed."""
    if st.multiplayer_view is None:
        if button != BUTTON_SPACE:
            return False
        st.multiplayer_view = "menu"
        st.multiplayer_selection = 0
        return True
    if st.multiplayer_view == "pending":
        return True
    if st.multiplayer_view == "error":
        if button in (BUTTON_BACK, BUTTON_CENTER, BUTTON_SPACE):
            st.multiplayer_view = None
        return True
    if st.multiplayer_view == "lobbies":
        if button == BUTTON_BACK:
            st.multiplayer_view = "menu"
            st.multiplayer_selection = 1
        elif button in (BUTTON_UP, BUTTON_DOWN) and st.multiplayer_lobbies:
            step = -1 if button == BUTTON_UP else 1
            st.multiplayer_lobby_index = (st.multiplayer_lobby_index + step) % len(
                st.multiplayer_lobbies
            )
        elif button == BUTTON_CENTER and st.multiplayer_lobbies:
            lobby = st.multiplayer_lobbies[st.multiplayer_lobby_index]
            _join_multiplayer_lobby(view_manager, st, lobby["lobby_id"])
        return True
    if button in (BUTTON_BACK, BUTTON_SPACE):
        if st.multiplayer_lobby_id:
            st.multiplayer_view = None
        else:
            st.multiplayer_view = None
        return True
    options = 2 if st.multiplayer_lobby_id else 3
    if button in (BUTTON_UP, BUTTON_DOWN):
        step = -1 if button == BUTTON_UP else 1
        st.multiplayer_selection = (st.multiplayer_selection + step) % options
    elif button == BUTTON_CENTER:
        if st.multiplayer_lobby_id:
            if st.multiplayer_selection == 0:
                _leave_multiplayer(view_manager, st, False)
            else:
                st.multiplayer_view = None
        elif st.multiplayer_selection == 0:
            _create_multiplayer_lobby(view_manager, st)
        elif st.multiplayer_selection == 1:
            _request_multiplayer_lobbies(view_manager, st)
        else:
            st.multiplayer_view = None
    return True


def _rgb(r, g, b):
    """Pack 8-bit channels into an RGB565 integer."""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


_BAR = _rgb(20, 20, 30)
_SKY_TOP = _rgb(100, 150, 225)
_SKY_LOW = _rgb(_SKY[0], _SKY[1], _SKY[2])
_WHITE = 0xFFFF
_GOLD = _rgb(250, 220, 120)
_MMC = (
    _rgb(70, 150, 60),
    _rgb(50, 100, 200),
    _rgb(30, 95, 45),
    _rgb(120, 110, 100),
    _rgb(240, 245, 250),
    _rgb(170, 110, 70),
    _rgb(190, 170, 120),
    _rgb(130, 90, 50),
    _rgb(250, 210, 60),
    _rgb(190, 120, 230),
    _rgb(130, 90, 50),
    _rgb(80, 190, 180),
)
_SKIN = (225, 185, 145)


def _shade(c, f):
    """Scale an (r, g, b) tuple by f, clamped to 255. Mirrors shadeColor565."""
    return (min(255, int(c[0] * f)), min(255, int(c[1] * f)), min(255, int(c[2] * f)))


def _box(x, y, w, h, c):
    """One model part: center x, center y, width, height, then r, g, b."""
    return (x, y, w, h, c[0], c[1], c[2])


def _humanoid(c, extra=()):
    """Humanoid parts with createHumanoid proportions (total height 1.0)."""
    m = [
        _box(-0.063, 0.225, 0.09, 0.45, _shade(c, 0.55)),
        _box(0.063, 0.225, 0.09, 0.45, _shade(c, 0.55)),
        _box(0, 0.625, 0.2, 0.35, c),
        _box(-0.16, 0.675, 0.07, 0.25, _shade(c, 0.75)),
        _box(0.16, 0.675, 0.07, 0.25, _shade(c, 0.75)),
        _box(0, 0.88, 0.24, 0.24, _SKIN),
    ]
    m.extend(extra)
    return tuple(m)


def _npc_models():
    """Return the Elder, Merchant, Innkeeper, and horse models."""
    elder = _humanoid(
        (110, 80, 170),
        (
            _box(0, 0.79, 0.12, 0.12, (235, 235, 235)),
            _box(-0.25, 0.5, 0.03, 0.95, (130, 90, 50)),
        ),
    )
    merchant = _humanoid(
        (60, 130, 170),
        (
            _box(0, 1.0, 0.32, 0.05, (120, 60, 40)),
            _box(0.24, 0.42, 0.13, 0.16, (150, 100, 50)),
        ),
    )
    inn = _humanoid((190, 110, 60), (_box(0, 0.5, 0.16, 0.28, (240, 240, 240)),))
    horse = (
        _box(-0.3, 0.16, 0.1, 0.32, (100, 65, 40)),
        _box(-0.08, 0.16, 0.1, 0.32, (100, 65, 40)),
        _box(0.25, 0.16, 0.1, 0.32, (100, 65, 40)),
        _box(0.44, 0.16, 0.1, 0.32, (100, 65, 40)),
        _box(0, 0.48, 0.62, 0.38, (150, 95, 55)),
        _box(0.27, 0.75, 0.2, 0.46, (150, 95, 55)),
        _box(0.36, 0.98, 0.32, 0.18, (150, 95, 55)),
        _box(0.4, 1.1, 0.09, 0.16, (100, 65, 40)),
        _box(0.35, 1.01, 0.04, 0.04, (30, 25, 20)),
        _box(0.12, 0.77, 0.34, 0.09, (65, 40, 30)),
    )
    return (elder, merchant, inn, horse)


def _foe_models():
    """Return the Wolf, Bandit, and Boar models, in _FOES order."""
    g = (120, 120, 130)
    wolf = (
        _box(-0.25, 0.13, 0.07, 0.26, _shade(g, 0.55)),
        _box(-0.15, 0.13, 0.07, 0.26, _shade(g, 0.55)),
        _box(0.15, 0.13, 0.07, 0.26, _shade(g, 0.55)),
        _box(0.25, 0.13, 0.07, 0.26, _shade(g, 0.55)),
        _box(-0.38, 0.46, 0.14, 0.06, _shade(g, 0.8)),
        _box(0, 0.38, 0.62, 0.24, g),
        _box(0.4, 0.5, 0.2, 0.18, _shade(g, 1.1)),
        _box(0.54, 0.46, 0.12, 0.09, _shade(g, 0.9)),
        _box(0.42, 0.63, 0.05, 0.07, _shade(g, 0.6)),
        _box(0.47, 0.53, 0.03, 0.03, (250, 220, 60)),
    )
    bandit = _humanoid(
        (140, 45, 45),
        (
            _box(0, 0.95, 0.27, 0.1, (70, 25, 25)),
            _box(0.27, 0.55, 0.03, 0.22, (200, 200, 210)),
        ),
    )
    b = (110, 70, 45)
    boar = (
        _box(-0.22, 0.1, 0.08, 0.2, _shade(b, 0.55)),
        _box(-0.1, 0.1, 0.08, 0.2, _shade(b, 0.55)),
        _box(0.14, 0.1, 0.08, 0.2, _shade(b, 0.55)),
        _box(0.26, 0.1, 0.08, 0.2, _shade(b, 0.55)),
        _box(0, 0.33, 0.6, 0.32, b),
        _box(0, 0.52, 0.4, 0.06, _shade(b, 0.6)),
        _box(0.36, 0.3, 0.22, 0.22, _shade(b, 1.1)),
        _box(0.5, 0.26, 0.08, 0.1, (200, 150, 140)),
        _box(0.47, 0.2, 0.03, 0.07, (240, 240, 230)),
        _box(0.33, 0.46, 0.06, 0.06, _shade(b, 0.6)),
        _box(0.4, 0.36, 0.03, 0.03, (250, 220, 60)),
    )
    return (wolf, bandit, boar)


def _draw_model(draw, model, ox, gy, scale):
    """Draw a model for the battle screen: outline pass, then fill pass."""
    rects = []
    for cx, cy, w, h, r, g, b in model:
        x0 = ox + int((cx - w * 0.5) * scale)
        x1 = ox + int((cx + w * 0.5) * scale)
        yt = gy - int((cy + h * 0.5) * scale)
        yb = gy - int((cy - h * 0.5) * scale)
        rects.append((x0, yt, max(1, x1 - x0), max(1, yb - yt), r, g, b))
    for x, y, w, h, r, g, b in rects:
        draw._fill_rectangle(x - 1, y - 1, w + 2, h + 2, _rgb(r >> 2, g >> 2, b >> 2))
    for x, y, w, h, r, g, b in rects:
        draw._fill_rectangle(x, y, w, h, _rgb(r, g, b))


_st = None


class _State:
    """Mutable game state container."""

    def __init__(self):
        """Set default player and view values."""
        self.tiles = None
        self.hts = None
        self.world = None
        self.fog = None
        self.npcs = None
        self.foes = None
        self.hm = None
        self.hx = _HORSE_POS[0] + 0.5
        self.hy = _HORSE_POS[1] + 0.5
        self.mounted = False
        self.fm = None
        self.mmt = 4
        self.camq = None
        self.tab = None
        self.buf = None
        self.px = 12.5
        self.py = 82.5
        self.pa = -pi / 2
        self.hp = 30
        self.mhp = 30
        self.gold = 15
        self.xp = 0
        self.lvl = 1
        self.quest = 0
        self.map_open = False
        self.mode = 0
        self.enemy = None
        self.msg = ("Welcome to the valley.", "Talk to the elder in Oakhaven.")
        self.last = (-1, -1)
        self.dirty = True
        self.vw = 320
        self.vh = 320
        self.fw = 6
        self.fh = 8
        self.y0 = 0
        self.vb = 0
        self.hor = 0
        self.cw = 5
        self.foc = 240.0
        self.multiplayer_view = None
        self.multiplayer_selection = 0
        self.multiplayer_lobbies = []
        self.multiplayer_lobby_index = 0
        self.multiplayer_status = ""
        self.multiplayer_http = None
        self.multiplayer_http_action = None
        self.multiplayer_ws = None
        self.multiplayer_connection_state = "idle"
        self.multiplayer_socket_error = ""
        self.multiplayer_player_id = ""
        self.multiplayer_player_id_bytes = b""
        self.multiplayer_target_lobby_id = ""
        self.multiplayer_lobby_id = ""
        self.multiplayer_leave_pending = False
        self.multiplayer_exit_after_leave = False
        self.multiplayer_notice = ""
        self.multiplayer_exit_ready = False
        self.multiplayer_last_send = 0
        self.remote_players = {}
        self.remote_model = None
        self.remote_horse_model = None


def _fog_table():
    """Build shaded, fogged colors. Returns a flat list indexed by tile, face, fog."""
    out = []
    for r, g, b in _BASE:
        for shade in (1.0, 0.75):
            for f in range(4):
                a = f * 0.22
                out.append(
                    _rgb(
                        int(r * shade * (1 - a) + _SKY[0] * a),
                        int(g * shade * (1 - a) + _SKY[1] * a),
                        int(b * shade * (1 - a) + _SKY[2] * a),
                    )
                )
    return out


def _grid(n):
    """Return an n by n grid of random floats."""
    from random import random

    return [[random() for _ in range(n)] for _ in range(n)]


@micropython.native
def _sample(g, n, fx, fy):
    """Bilinear sample of grid g at unit coordinates fx, fy. Returns a float."""
    gx = fx * (n - 1)
    gy = fy * (n - 1)
    x0 = min(int(gx), n - 2)
    y0 = min(int(gy), n - 2)
    tx = gx - x0
    ty = gy - y0
    tx = tx * tx * (3 - 2 * tx)
    ty = ty * ty * (3 - 2 * ty)
    r0 = g[y0]
    r1 = g[y0 + 1]
    a = r0[x0] + (r0[x0 + 1] - r0[x0]) * tx
    b = r1[x0] + (r1[x0 + 1] - r1[x0]) * tx
    return a + (b - a) * ty


@micropython.native
def _river_x(y):
    """Return the river center column for row y."""
    return int(32 + 9 * sin(y * 0.12))


def _carve(tiles, hts, x0, y0, x1, y1):
    """Lay a two-wide road between two points, bridging any water."""
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i // n
        y = y0 + (y1 - y0) * i // n
        for oy in (0, 1):
            for ox in (0, 1):
                xx = x + ox
                yy = y + oy
                if 0 <= xx < _W and 0 <= yy < _H:
                    k = yy * _W + xx
                    if tiles[k] == _WATER or tiles[k] == _BRIDGE:
                        tiles[k] = _BRIDGE
                        hts[k] = 1
                    else:
                        tiles[k] = _ROAD
                        hts[k] = 0


def _town(tiles, hts, cx, cy):
    """Flatten a site, then place the plaza, four houses, and the resident NPC."""
    for y in range(cy - 6, cy + 7):
        for x in range(cx - 6, cx + 7):
            k = y * _W + x
            tiles[k] = _GRASS
            hts[k] = 0
    for y in range(cy - 2, cy + 3):
        for x in range(cx - 2, cx + 3):
            tiles[y * _W + x] = _ROAD
    for sx in (-1, 1):
        for sy in (-1, 1):
            for a in (3, 4):
                for b in (3, 4):
                    k = (cy + sy * b) * _W + cx + sx * a
                    tiles[k] = _HOUSE
                    hts[k] = 20
    k = cy * _W + cx
    tiles[k] = _NPC
    hts[k] = 0


@micropython.native
def _build_world(st):
    """Generate terrain, river, roads, towns, and the shrine into the state arrays."""
    from random import seed
    from time import ticks_ms

    seed(20260)
    ea = _grid(9)
    eb = _grid(17)
    wt = _grid(9)
    tiles = bytearray(_N)
    hts = bytearray(_N)
    for y in range(_H):
        rx = _river_x(y)
        fy = y / (_H - 1)
        for x in range(_W):
            fx = x / (_W - 1)
            e = _sample(ea, 9, fx, fy) * 0.65 + _sample(eb, 17, fx, fy) * 0.35
            e = 0.5 + (e - 0.5) * 1.3
            d = abs(x - rx)
            if d < 8:
                e *= 0.45 + d * 0.07
            k = y * _W + x
            if d <= 1:
                tiles[k] = _WATER
            elif e > 0.68:
                h = (e - 0.5) * 14
                tiles[k] = _SNOW if h > 5.0 else _ROCK
                hts[k] = min(int(h * 16), 255)
            elif e > 0.2 and e <= 0.56 and _sample(wt, 9, fx, fy) > 0.42:
                tiles[k] = _FOREST
                hts[k] = int((0.5 + ((x * 7 + y * 13) % 5) * 0.12) * 16)
            else:
                hts[k] = int(max(0.0, (e - 0.5) * 6) * 16)
    _carve(tiles, hts, _TOWNS[0][0], _TOWNS[0][1], _SHRINE_POS[0], _SHRINE_POS[1])
    for a, b in ((0, 1), (0, 2), (1, 2)):
        _carve(tiles, hts, _TOWNS[a][0], _TOWNS[a][1], _TOWNS[b][0], _TOWNS[b][1])
    for tx, ty, _name in _TOWNS:
        _town(tiles, hts, tx, ty)
    sx, sy = _SHRINE_POS
    hx, hy = _HORSE_POS
    tiles[hy * _W + hx] = _HORSE
    hts[hy * _W + hx] = 0
    for y in range(sy - 1, sy + 2):
        for x in range(sx - 1, sx + 2):
            tiles[y * _W + x] = _ROAD
            hts[y * _W + x] = 0
    tiles[sy * _W + sx] = _SHRINE
    hts[sy * _W + sx] = 24
    wx, wy = _WAYSTONE_POS
    tiles[wy * _W + wx] = _WAYSTONE
    hts[wy * _W + wx] = 24
    for fx, fy in _FOE_POS:
        k = fy * _W + fx
        tiles[k] = _FOREST
        hts[k] = 8
    st.tiles = tiles
    st.hts = hts
    seed(ticks_ms())


def _prep(st):
    """Build the integer step table, the packed world, and the viper buffers.

    tab layout (int32): [n, off_kf, off_fi, off_fog, ts..., kf..., fi..., fog...]
    ts  = ray distance in Q8
    kf  = focal / distance, pre-scaled so (height64 - eye64) * kf >> 8 is pixels
    fi  = fog level for that step
    buf layout (int32): [px_q16, py_q16, eye64, hor, y0, vb, rx_q8, ry_q8, ..., runs from 16]
    """
    ts = []
    t = 0.3
    while t < _MAXD:
        ts.append(t)
        t += 0.16 + t * 0.05
    n = len(ts)
    fog = st.fog
    nf = len(fog)
    tab = array("i", [0] * (4 + n * 3 + nf))
    tab[0] = n
    tab[1] = 4 + n
    tab[2] = 4 + n * 2
    tab[3] = 4 + n * 3
    foc = st.foc
    for s in range(n):
        t = ts[s]
        tab[4 + s] = int(t * 256)
        tab[4 + n + s] = int(foc / t * 4)
        tab[4 + n * 2 + s] = int(t * 0.33)
    for j in range(nf):
        tab[4 + n * 3 + j] = fog[j]
    st.tab = tab
    st.buf = array("i", [0] * (16 + n * 3))
    st.world = st.tiles + st.hts


def _open(st, x, y):
    """Return True if the world position is walkable."""
    if x < 0 or y < 0 or x >= _W or y >= _H:
        return False
    return not _BLK[st.tiles[int(y) * _W + int(x)]]


def _step(st, dist):
    """Move along the facing direction with collision. Returns True if moved."""
    nx = st.px + cos(st.pa) * dist
    ny = st.py + sin(st.pa) * dist
    moved = False
    if _open(st, nx, st.py):
        st.px = nx
        moved = True
    if _open(st, st.px, ny):
        st.py = ny
        moved = True
    return moved


def _where(st):
    """Return the nearest town name or the terrain label under the player."""
    for tx, ty, name in _TOWNS:
        if abs(st.px - tx) < 7 and abs(st.py - ty) < 7:
            return name
    return _NAMES[st.tiles[int(st.py) * _W + int(st.px)]]


def _gain(st, xp, gold):
    """Add xp and gold, applying level ups. Returns True if a level was gained."""
    st.xp += xp
    st.gold += gold
    up = False
    while st.xp >= st.lvl * 20:
        st.xp -= st.lvl * 20
        st.lvl += 1
        st.mhp += 8
        st.hp = st.mhp
        up = True
    return up


def _respawn(st):
    """Return the player to Oakhaven after defeat, losing half the gold."""
    st.px = 12.5
    st.py = 82.5
    st.pa = -pi / 2
    st.hp = st.mhp
    st.gold //= 2
    st.mode = 0
    st.msg = ("You were defeated.", "You wake in Oakhaven.")


def _encounter(st, i):
    """Start a battle with the encountered foe, scaled to the player level."""
    f = _FOES[i]
    hp = f[1] + st.lvl * 3
    st.enemy = [f[0], hp, hp, f[2] + st.lvl // 2, f[3], i]
    st.mode = 1
    st.msg = (f"A {f[0]} attacks!", "OK attack. DOWN flee.")


def _arrive(st, oldx, oldy):
    """Handle foe contact and events along the player's movement path."""
    dx = st.px - oldx
    dy = st.py - oldy
    length2 = dx * dx + dy * dy
    for fx, fy, i in st.foes:
        if length2:
            t = ((fx - oldx) * dx + (fy - oldy) * dy) / length2
            t = max(0.0, min(1.0, t))
            nearx = oldx + t * dx
            neary = oldy + t * dy
        else:
            nearx = st.px
            neary = st.py
        if (nearx - fx) ** 2 + (neary - fy) ** 2 < 0.85**2:
            _encounter(st, i)
            return
    cell = (int(st.px), int(st.py))
    if cell == st.last:
        return
    st.last = cell
    tile = st.tiles[cell[1] * _W + cell[0]]
    if tile == _SHRINE and st.quest == 1:
        st.quest = 2
        st.msg = ("You take the ancient relic.", "Return it to the elder.")
    elif tile == _WAYSTONE and st.quest == 6:
        st.quest = 7
        st.msg = ("The waystone answers your touch.", "Return to the elder.")


def _shop(st, who, cost, heal):
    """Sell healing. who is the speaker, cost is gold, heal is hit points restored."""
    if st.hp >= st.mhp:
        st.msg = (f"{who}: You look healthy.", "")
    elif st.gold < cost:
        st.msg = (f"{who}: That costs {cost} gold.", "You cannot afford it.")
    else:
        st.gold -= cost
        st.hp = min(st.mhp, st.hp + heal)
        st.msg = (f"{who}: Healed for {cost} gold.", "")


def _talk(st, n):
    """Run dialogue and services for the NPC in town index n."""
    if n == 0:
        if st.quest == 0:
            st.quest = 1
            st.msg = ("Elder: Bring the relic from", "the shrine far to the north.")
        elif st.quest == 1:
            st.msg = ("Elder: Follow the north road", "to the shrine in the peaks.")
        elif st.quest == 2:
            st.quest = 3
            up = _gain(st, 40, 60)
            st.msg = (
                "Elder: Take this letter to Highfall.",
                "Level up! +60 gold." if up else "The valley needs your help.",
            )
        elif st.quest == 3:
            st.msg = ("Elder: Deliver the letter", "to the merchant in Highfall.")
        elif st.quest == 4:
            st.msg = ("Elder: The innkeeper in", "Eastmere is waiting for you.")
        elif st.quest == 5:
            st.quest = 6
            st.msg = ("Elder: Find the eastern waystone.", "It lies beyond Eastmere.")
        elif st.quest == 6:
            st.msg = ("Elder: Find the eastern waystone.", "It lies beyond Eastmere.")
        elif st.quest == 7:
            st.quest = 8
            up = _gain(st, 60, 100)
            st.msg = (
                "Elder: You restored the waystone!",
                "Level up! +100 gold." if up else "The valley is at peace.",
            )
        elif st.quest == 8:
            st.msg = ("Elder: You are a friend of", "every town in the valley.")
        else:
            st.msg = ("Elder: The valley is at peace.", "")
    elif n == 1:
        if st.quest == 3:
            st.quest = 4
            st.msg = ("Merchant: Letter received.", "Take this map to Eastmere.")
        else:
            _shop(st, "Merchant", 10, 20)
    else:
        if st.quest == 4:
            st.quest = 5
            st.msg = ("Innkeeper: The map is marked.", "Return to the elder.")
        else:
            _shop(st, "Innkeeper", 5, 999)


def _interact(st):
    """Talk to an adjacent NPC. Always returns True so the view redraws."""
    if st.mounted:
        st.mounted = False
        hx = int(st.px)
        hy = int(st.py)
        st.hx = hx + 0.5
        st.hy = hy + 0.5
        st.tiles[hy * _W + hx] = _HORSE
        st.msg = ("You dismount.", "Press OK near your horse to ride.")
        return True
    if (st.px - st.hx) ** 2 + (st.py - st.hy) ** 2 < 6.25:
        hx = int(st.hx)
        hy = int(st.hy)
        st.tiles[hy * _W + hx] = _GRASS
        st.mounted = True
        st.msg = ("You mount your horse.", "Ride faster across the valley!")
        return True
    ix = int(st.px)
    iy = int(st.py)
    for ty in range(iy - 1, iy + 2):
        for tx in range(ix - 1, ix + 2):
            if 0 <= tx < _W and 0 <= ty < _H and st.tiles[ty * _W + tx] == _NPC:
                for n in range(3):
                    if _TOWNS[n][0] == tx and _TOWNS[n][1] == ty:
                        _talk(st, n)
                        return True
    st.msg = ("Nobody is close enough.", "")
    return True


def _battle_input(st, button):
    """Apply a battle action for the pressed button. Returns True if state changed."""
    e = st.enemy
    if button == BUTTON_CENTER:
        dmg = randint(3, 6) + st.lvl * 2
        e[1] -= dmg
        if e[1] <= 0:
            gold = e[4] + randint(0, 4)
            up = _gain(st, 8 + st.lvl * 3, gold)
            st.msg = (
                f"{e[0]} defeated. +{gold} gold.",
                "Level up!" if up else "Victory.",
            )
            st.mode = 0
            return True
        line = f"You hit {e[0]} for {dmg}."
    elif button == BUTTON_DOWN:
        if randint(0, 1):
            st.msg = ("You escaped.", "")
            st.mode = 0
            return True
        line = "You could not escape."
    else:
        return False
    hit = randint(1, e[3])
    st.hp -= hit
    if st.hp <= 0:
        _respawn(st)
        return True
    st.msg = (line, f"{e[0]} hits you for {hit}.")
    return True


def _bar(draw, x, y, w, h, cur, mx, color):
    """Draw a filled progress bar. cur and mx set the filled fraction."""
    draw._fill_rectangle(x, y, w, h, _rgb(60, 60, 70))
    fill = w * max(0, cur) // max(1, mx)
    if fill > 0:
        draw._fill_rectangle(x, y, fill, h, color)


def _draw_battle(view_manager, st):
    """Draw the battle screen with both health bars and the message log."""
    draw = view_manager.draw
    w = st.vw
    fh = st.fh
    e = st.enemy
    draw._fill_rectangle(0, 0, w, st.vh, _rgb(25, 20, 30))
    draw._text(10, 10, e[0], _WHITE)
    _bar(draw, 10, 12 + fh, w - 20, 10, e[1], e[2], _rgb(200, 50, 50))
    gy = st.vh // 2 - 8
    sc = (gy - (26 + fh)) / 1.05
    draw._fill_rectangle(w // 2 - int(sc * 0.45), gy, int(sc * 0.9), 3, _rgb(10, 8, 14))
    _draw_model(draw, st.fm[e[5]], w // 2, gy, sc)
    draw._text(10, st.vh // 2, f"You  Lv {st.lvl}  HP {st.hp}/{st.mhp}", _WHITE)
    _bar(draw, 10, st.vh // 2 + fh + 2, w - 20, 10, st.hp, st.mhp, _rgb(60, 190, 80))
    draw._text(10, st.vh - fh * 4, st.msg[0], _WHITE)
    draw._text(10, st.vh - fh * 3 + 2, st.msg[1], _GOLD)
    draw._text(10, st.vh - fh - 4, "OK attack   DOWN flee", _rgb(160, 160, 170))
    draw.swap()


def _quest_target(st):
    """Return the current objective's tile and label, or None after completion."""
    if st.quest in (0, 2, 5, 7):
        return _TOWNS[0][0], _TOWNS[0][1], "Elder"
    if st.quest == 1:
        return _SHRINE_POS[0], _SHRINE_POS[1], "Shrine"
    if st.quest == 3:
        return _TOWNS[1][0], _TOWNS[1][1], "Merchant"
    if st.quest == 4:
        return _TOWNS[2][0], _TOWNS[2][1], "Innkeeper"
    if st.quest == 6:
        return _WAYSTONE_POS[0], _WAYSTONE_POS[1], "Waystone"
    return None


def _draw_quest_indicator(draw, st):
    """Show a camera-relative bearing: up ahead, right right, down behind."""
    target = _quest_target(st)
    if target is None:
        return
    width = st.vw - 13 * st.mmt - 9
    height = max(19, st.fh + 4)
    if width < 19 or st.y0 + 3 + height > st.vb:
        return
    label = target[2][:max(0, (width - 23) // st.fw)]
    fill = draw._fill_rectangle
    left = 3
    top = st.y0 + 3
    fill(left, top, min(width, 23 + len(label) * st.fw), height, _BAR)
    draw._text(left + 23, top + (height - st.fh) // 2, label, _GOLD)
    cx = left + 9
    cy = top + height // 2
    tx = target[0] + 0.5 - st.px
    ty = target[1] + 0.5 - st.py
    distance = (tx * tx + ty * ty) ** 0.5
    if distance < 0.25:
        fill(cx - 2, cy - 2, 5, 5, _GOLD)
        return
    # Project the objective onto camera-right and camera-forward axes.
    dx = (-sin(st.pa) * tx + cos(st.pa) * ty) / distance
    dy = -(cos(st.pa) * tx + sin(st.pa) * ty) / distance
    for forward in range(-5, 8):
        fill(cx + int(round(forward * dx)),
             cy + int(round(forward * dy)), 1, 1, _GOLD)
    for back in range(1, 5):
        for side in (-back, back):
            fill(cx + int(round((7 - back) * dx - side * dy)),
                 cy + int(round((7 - back) * dy + side * dx)), 1, 1, _GOLD)


def _hud(view_manager, st):
    """Draw the status bars with stats, heading, location, and messages."""
    draw = view_manager.draw
    w = st.vw
    draw._fill_rectangle(0, 0, w, st.y0, _BAR)
    draw._fill_rectangle(0, st.vb, w, st.vh - st.vb, _BAR)
    left = f"HP {st.hp}/{st.mhp}  Lv {st.lvl}  G {st.gold}"
    right = f"{_DIRS[int(round(st.pa / (pi / 4))) % 8]} {_where(st)}"
    draw._text(3, 2, left, _WHITE)
    draw._text(w - len(right) * st.fw - 3, 2, right, _WHITE)
    mc = w // st.fw
    draw._text(3, st.vb + 3, st.msg[0][:mc], _WHITE)
    draw._text(3, st.vb + 4 + st.fh, st.msg[1][:mc], _GOLD)
    if st.multiplayer_connection_state == "active":
        draw._text(w - st.fw * 7 - 3, st.vb - st.fh - 2, "ONLINE", _GOLD)


def _blocked(st, nx, ny, eye):
    """Return True if terrain hides the point (nx, ny) from the player."""
    px = st.px
    py = st.py
    ex = nx - px
    ey = ny - py
    n = int((ex * ex + ey * ey) ** 0.5 * 2) + 1
    hts = st.hts
    for i in range(1, n):
        s = i / n
        k = int(py + ey * s) * _W + int(px + ex * s)
        if hts[k] * 0.0625 > eye + (0.9 - eye) * s:
            return True
    return False


def _draw_npcs(draw, st, dx, dy, eye):
    """Draw visible NPC models as camera-facing billboards, far to near."""
    vw = st.vw
    foc = st.foc
    hor = st.hor
    y0 = st.y0
    vb = st.vb
    fill = draw._fill_rectangle
    vis = []
    for nx, ny, model in st.npcs:
        if st.mounted and model is st.hm:
            continue
        if model is st.hm:
            nx = st.hx
            ny = st.hy
        ex = nx - st.px
        ey = ny - st.py
        f = ex * dx + ey * dy
        if f < 0.5 or f > _MAXD:
            continue
        sxc = vw / 2 + (-ex * dy + ey * dx) / f * foc
        if sxc < -40 or sxc > vw + 40 or _blocked(st, nx, ny, eye):
            continue
        vis.append((f, sxc, model))
    for remote in list(st.remote_players.values()):
        nx = remote["x"]
        ny = remote["y"]
        model = st.remote_horse_model if remote["mounted"] else st.remote_model
        ex = nx - st.px
        ey = ny - st.py
        f = ex * dx + ey * dy
        if f < 0.5 or f > _MAXD:
            continue
        sxc = vw / 2 + (-ex * dy + ey * dx) / f * foc
        if sxc < -40 or sxc > vw + 40 or _blocked(st, nx, ny, eye):
            continue
        vis.append((f, sxc, model))
    vis.sort()
    for v in range(len(vis) - 1, -1, -1):
        f, sxc, model = vis[v]
        inv = foc / f
        fa = min(3, int(f * 0.33)) * 0.22
        for cx, cy, w, h, r, g, b in model:
            x0 = int(sxc + (cx - w * 0.5) * inv)
            x1 = max(int(sxc + (cx + w * 0.5) * inv), x0 + 1)
            ya = hor - int((cy + h * 0.5 - eye) * inv)
            yb = hor - int((cy - h * 0.5 - eye) * inv)
            x0 = max(x0, 0)
            x1 = min(x1, vw)
            ya = max(ya, y0)
            yb = min(yb, vb)
            if x1 > x0 and yb > ya:
                fill(
                    x0,
                    ya,
                    x1 - x0,
                    yb - ya,
                    _rgb(
                        int(r * (1 - fa) + _SKY[0] * fa),
                        int(g * (1 - fa) + _SKY[1] * fa),
                        int(b * (1 - fa) + _SKY[2] * fa),
                    ),
                )


def _minimap(draw, st):
    """Draw a north-up minimap of the nearby tiles in the top-right corner."""
    r = 6
    n = r * 2 + 1
    ts = st.mmt
    size = n * ts
    ox = st.vw - size - 3
    oy = st.y0 + 3
    cx = int(st.px) - r
    cy = int(st.py) - r
    tiles = st.tiles
    fill = draw._fill_rectangle
    fill(ox - 1, oy - 1, size + 2, size + 2, _WHITE)
    for j in range(n):
        ty = cy + j
        row = ty * _W
        i = 0
        while i < n:
            tx = cx + i
            if 0 <= tx < _W and 0 <= ty < _H:
                c = _MMC[tiles[row + tx]]
            else:
                c = _BAR
            k = i + 1
            while k < n:
                tx = cx + k
                if 0 <= tx < _W and 0 <= ty < _H:
                    c2 = _MMC[tiles[row + tx]]
                else:
                    c2 = _BAR
                if c2 != c:
                    break
                k += 1
            fill(ox + i * ts, oy + j * ts, (k - i) * ts, ts, c)
            i = k
    mx = ox + int((st.px - cx) * ts)
    my = oy + int((st.py - cy) * ts)
    fill(mx - 1, my - 1, 3, 3, _rgb(255, 60, 60))
    fill(mx + int(cos(st.pa) * 4), my + int(sin(st.pa) * 4), 1, 1, _WHITE)
    for remote in list(st.remote_players.values()):
        rx = ox + int((remote["x"] - cx) * ts)
        ry = oy + int((remote["y"] - cy) * ts)
        if ox <= rx < ox + size and oy <= ry < oy + size:
            fill(rx - 1, ry - 1, 3, 3, remote["color"])


def _draw_world_map(view_manager, st):
    """Fit the whole north-up valley on screen without a second tile buffer."""
    draw = view_manager.draw
    fill = draw._fill_rectangle
    draw.fill_screen(_BAR)
    size = max(1, min(st.vw - 4, st.vh - 2 * st.fh - 10))
    ox = (st.vw - size) // 2
    oy = st.fh + 5
    draw._text(3, 1, "VALLEY MAP  N ^", _GOLD)
    for y in range(_H):
        top = oy + y * size // _H
        bottom = oy + (y + 1) * size // _H
        x = 0
        while x < _W:
            color = _MMC[st.tiles[y * _W + x]]
            end = x + 1
            while end < _W and _MMC[st.tiles[y * _W + end]] == color:
                end += 1
            left = ox + x * size // _W
            right = ox + end * size // _W
            if right > left and bottom > top:
                fill(left, top, right - left, bottom - top, color)
            x = end
    for x, y, label in _TOWNS + (
        (_SHRINE_POS[0], _SHRINE_POS[1], "Shrine"),
        (_WAYSTONE_POS[0], _WAYSTONE_POS[1], "Waystone"),
    ):
        mx = ox + x * size // _W
        my = oy + y * size // _H
        fill(mx - 1, my - 1, 3, 3, _WHITE)
        tx = max(0, min(st.vw - len(label) * st.fw, mx + 4))
        ty = max(oy, my - st.fh - 2)
        fill(tx, ty, len(label) * st.fw, st.fh, _BAR)
        draw._text(tx, ty, label, _WHITE)
    for remote in st.remote_players.values():
        mx = ox + int(remote["x"] * size / _W)
        my = oy + int(remote["y"] * size / _H)
        if ox <= mx < ox + size and oy <= my < oy + size:
            fill(mx - 1, my - 1, 3, 3, remote["color"])
    mx = ox + int(st.px * size / _W)
    my = oy + int(st.py * size / _H)
    fill(mx - 2, my - 2, 5, 5, _rgb(255, 60, 60))
    # Rotate a shaft and two arrowhead wings; shift the whole arrow at edges
    # so its shape and heading remain visible without unsigned-coordinate wrap.
    dx = cos(st.pa)
    dy = sin(st.pa)
    points = []
    for forward in range(3, 10):
        points.append((int(round(forward * dx)), int(round(forward * dy))))
    for back in range(1, 5):
        for side in (-back, back):
            points.append((int(round((9 - back) * dx - side * dy)),
                           int(round((9 - back) * dy + side * dx))))
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    ax = max(ox - min_x, min(ox + size - 1 - max_x, mx))
    ay = max(oy - min_y, min(oy + size - 1 - max_y, my))
    for x, y in points:
        x += ax
        y += ay
        if ox <= x < ox + size and oy <= y < oy + size:
            fill(x, y, 1, 1, _WHITE)
    draw._text(3, st.vh - st.fh - 2, "M/Back: close", _GOLD)
    draw.swap()


def _draw_multiplayer_menu(view_manager, st):
    """Draw the lobby menu over the game."""
    draw = view_manager.draw
    width = st.vw
    line_height = st.fh + 3
    draw.fill_screen(_BAR)
    title = "VALLEY RIDER"
    draw._text(max(0, width // 2 - len(title) * st.fw // 2), st.fh, title, _GOLD)
    if st.multiplayer_view == "menu":
        if st.multiplayer_lobby_id:
            options = ("Leave lobby", "Resume")
            draw._text(3, st.fh * 3, "Peers: %d" % len(st.remote_players), _WHITE)
        else:
            options = ("Create lobby", "Join lobby", "Resume")
    elif st.multiplayer_view == "lobbies":
        options = tuple(
            "%s %d/%d"
            % (
                lobby["lobby_id"][:8],
                lobby["player_count"],
                lobby["max_players"],
            )
            for lobby in st.multiplayer_lobbies[:_MP_MAX_LOBBIES]
        )
        if not options:
            draw._text(3, st.fh * 3, "No open lobbies", _WHITE)
    else:
        options = ()
        message = st.multiplayer_status[: width // st.fw]
        draw._text(
            max(0, width // 2 - len(message) * st.fw // 2), st.vh // 2, message, _WHITE
        )
    first_y = st.vh // 2 - len(options) * line_height // 2
    selection = (
        st.multiplayer_lobby_index
        if st.multiplayer_view == "lobbies"
        else st.multiplayer_selection
    )
    for index, option in enumerate(options):
        y = first_y + index * line_height
        color = _GOLD if index == selection else _WHITE
        draw._text(max(3, width // 2 - len(option) * st.fw // 2), y, option, color)
    if st.multiplayer_view == "lobbies":
        footer = "UP/DOWN OK  BACK"
    elif st.multiplayer_view == "pending":
        footer = ""
    else:
        footer = "UP/DOWN OK  BACK"
    if footer:
        draw._text(3, st.vh - line_height, footer, _WHITE)
    draw.swap()


@micropython.native
def _march(buf, world, tab):
    """March one ray with integer math and write its draw runs into buf.

    Reads the ray and view setup from buf[0:8]. Writes (y, height, color)
    triples from buf[16]. Returns the number of runs written.
    """
    n = int(tab[0])
    okf = int(tab[1])
    ofi = int(tab[2])
    ofg = int(tab[3])
    pxq = int(buf[0])
    pyq = int(buf[1])
    eye64 = int(buf[2])
    hor = int(buf[3])
    y0 = int(buf[4])
    top = int(buf[5])
    rxq = int(buf[6])
    ryq = int(buf[7])
    lx = -2
    cnt = 0
    o = 16
    s = 0
    while s < n:
        tq = int(tab[4 + s])
        wx = pxq + rxq * tq
        wy = pyq + ryq * tq
        if wx < 0 or wy < 0 or wx >= _W16 or wy >= _H16:
            tile = _ROCK
            h16 = 96
            ix = -1
        else:
            ix = wx >> 16
            k = (wy >> 16) * _W + ix
            tile = int(world[k])
            h16 = int(world[_N + k])
        y = hor - (((h16 * 4 - eye64) * int(tab[okf + s])) >> 8)
        if y < top:
            if y < y0:
                y = y0
            face = 0
            if ix != lx and h16 > 6:
                face = 4
            buf[o] = y
            buf[o + 1] = top - y
            buf[o + 2] = int(tab[ofg + ((tile << 3) | face | int(tab[ofi + s]))])
            o += 3
            cnt += 1
            top = y
            if y <= y0:
                break
        lx = ix
        s += 1
    return cnt


@micropython.native
def _render(view_manager, st):
    """Draw the first-person terrain view, one integer-marched ray per column."""
    draw = view_manager.draw
    fill = draw._fill_rectangle
    tiles = st.tiles
    hts = st.hts
    fog = st.fog
    camq = st.camq
    buf = st.buf
    tab = st.tab
    world = st.world
    w = st.vw
    y0 = st.y0
    vb = st.vb
    hor = st.hor
    cw = st.cw
    px = st.px
    py = st.py
    dx = cos(st.pa)
    dy = sin(st.pa)
    dxq = int(dx * 256)
    dyq = int(dy * 256)
    plxq = int(-dy * _PL * 256)
    plyq = int(dx * _PL * 256)
    pk = int(py) * _W + int(px)
    eye64 = 70
    if tiles[pk] != _FOREST:
        eye64 += hts[pk] * 4
    buf[0] = int(px * 65536)
    buf[1] = int(py * 65536)
    buf[2] = eye64
    buf[3] = hor
    buf[4] = y0
    buf[5] = vb
    mid = (hor - y0) // 2
    fill(0, y0, w, mid, _SKY_TOP)
    fill(0, y0 + mid, w, hor - y0 - mid, _SKY_LOW)
    fill(0, hor, w, vb - hor, fog[tiles[pk] << 3])
    for i in range(len(camq)):
        c = camq[i]
        buf[6] = dxq + ((plxq * c) >> 12)
        buf[7] = dyq + ((plyq * c) >> 12)
        cnt = _march(buf, world, tab)
        sx = i * cw
        o = 16
        for _j in range(cnt):
            fill(sx, buf[o], cw, buf[o + 1], buf[o + 2])
            o += 3
    _draw_npcs(draw, st, dx, dy, eye64 / 64)
    _minimap(draw, st)
    _draw_quest_indicator(draw, st)
    draw._text(3, st.vb - st.fh - 2, "M: Map", _WHITE)
    _hud(view_manager, st)
    draw.swap()


def start(view_manager):
    """Show a loading note, build the world, and prepare view geometry. Returns True."""
    from gc import collect

    global _st
    draw = view_manager.draw
    draw.clear()
    draw._text(10, 10, "Generating valley...", _SKY_TOP)
    draw.swap()
    st = _State()
    size = draw.size
    st.vw = int(size.x)
    st.vh = int(size.y)
    st.fw = max(1, int(draw.font_size.x))
    st.fh = max(1, int(draw.font_size.y))
    st.y0 = st.fh + 4
    st.vb = st.vh - (st.fh * 2 + 8)
    st.hor = st.y0 + (st.vb - st.y0) * 45 // 100
    st.cw = max(3, st.vw // 64)
    cols = st.vw // st.cw
    st.camq = array("i", [int(((2 * i + 1) / cols - 1) * 4096) for i in range(cols)])
    st.foc = (st.vw / 2) / _PL
    st.fog = _fog_table()
    _build_world(st)
    _prep(st)
    st.mmt = 4 if st.vw >= 240 else 3
    st.fm = _foe_models()
    nm = _npc_models()
    st.remote_model = _humanoid((50, 180, 230))
    st.remote_horse_model = tuple(list(nm[3]))
    npcs = []
    foes = []
    for i in range(3):
        npcs.append((_TOWNS[i][0] + 0.5, _TOWNS[i][1] + 0.5, nm[i]))
        fx, fy = _FOE_POS[i]
        foes.append((fx + 0.5, fy + 0.5, i))
        npcs.append((fx + 0.5, fy + 0.5, st.fm[i]))
    st.hm = nm[3]
    npcs.append((st.hx, st.hy, st.hm))
    st.npcs = tuple(npcs)
    st.foes = tuple(foes)
    collect()
    _st = st
    view_manager.input_manager.reset()
    return True


def run(view_manager):
    """Read input, update the game, and redraw only when something changed."""
    st = _st
    button = view_manager.button
    _poll_multiplayer_http(view_manager, st)
    if st.multiplayer_connection_state in ("connect_error", "lost"):
        reason = st.multiplayer_socket_error or "Connection lost"
        _leave_multiplayer(view_manager, st, False, reason)
    if st.multiplayer_exit_ready:
        st.multiplayer_exit_ready = False
        view_manager.back()
        return
    if st.multiplayer_view is None and (st.map_open or button == BUTTON_M):
        if button == BUTTON_M or (st.map_open and button == BUTTON_BACK):
            st.map_open = not st.map_open
            st.dirty = True
        if button != BUTTON_NONE:
            view_manager.input_manager.reset()
        if st.dirty:
            st.dirty = False
            if st.map_open:
                _draw_world_map(view_manager, st)
            elif st.mode == 1:
                _draw_battle(view_manager, st)
            else:
                _render(view_manager, st)
        return
    if _multiplayer_input(view_manager, st, button):
        if button != BUTTON_NONE:
            view_manager.input_manager.reset()
        if st.multiplayer_view is not None:
            _draw_multiplayer_menu(view_manager, st)
        return
    if button == BUTTON_BACK:
        if st.multiplayer_lobby_id:
            _leave_multiplayer(view_manager, st, True)
            view_manager.input_manager.reset()
            _draw_multiplayer_menu(view_manager, st)
            return
        view_manager.back()
        return
    if st.mode == 1:
        if _battle_input(st, button):
            st.dirty = True
    elif button == BUTTON_UP:
        oldx = st.px
        oldy = st.py
        if _step(st, _HORSE_SPEED if st.mounted else _WALK_SPEED):
            if st.mounted:
                st.hx = st.px
                st.hy = st.py
            _arrive(st, oldx, oldy)
            st.dirty = True
    elif button == BUTTON_DOWN:
        oldx = st.px
        oldy = st.py
        if _step(st, -(_HORSE_BACK_SPEED if st.mounted else _BACK_SPEED)):
            if st.mounted:
                st.hx = st.px
                st.hy = st.py
            _arrive(st, oldx, oldy)
            st.dirty = True
    elif button == BUTTON_LEFT:
        st.pa -= _TURN_SPEED
        st.dirty = True
    elif button == BUTTON_RIGHT:
        st.pa += _TURN_SPEED
        st.dirty = True
    elif button == BUTTON_CENTER:
        st.dirty = _interact(st)
    if st.dirty:
        st.dirty = False
        if st.mode == 1:
            _draw_battle(view_manager, st)
        else:
            _render(view_manager, st)


def stop(view_manager):
    """Release game state and free memory."""
    from gc import collect

    global _st
    st = _st
    if st is not None:
        if st.multiplayer_ws is not None:
            st.multiplayer_connection_state = "idle"
            st.multiplayer_ws.close()
            st.multiplayer_ws = None
        if st.multiplayer_http is not None:
            st.multiplayer_http.close()
            st.multiplayer_http = None
    _st = None
    collect()
