"""Picoware open-world city game."""

from math import atan2, cos, pi, sin
from picoware.system.vector import Vector
from picoware.engine.entity import Entity
from ujson import loads as json_loads

_city = None
_seed = 0x5A3C1D7


def _next_random(limit):
    """Return a pseudo-random integer below limit."""
    global _seed

    _seed = (_seed * 1103515245 + 12345) & 0x7FFFFFFF
    return _seed % limit


def _integer_to_ascii_bytes(value, base=10):
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
    scale = 10**precision
    scaled = int(abs(value) * scale + 0.5)
    integer = _integer_to_ascii_bytes(scaled // scale)
    if value < 0 and scaled:
        integer = b"-" + integer
    fraction = _integer_to_ascii_bytes(scaled % scale)
    return integer + b"." + b"0" * (precision - len(fraction)) + fraction


def _parse_ascii_float(value):
    if not isinstance(value, bytes) or not value or len(value) > 16:
        return None

    sign = 1
    index = 0
    if value[0] == 45:
        sign = -1
        index = 1
    if index == len(value):
        return None

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


def _hex_bytes_to_text(data):
    digits = "0123456789abcdef"
    result = []
    for value in data:
        result.append(digits[value >> 4])
        result.append(digits[value & 0x0F])
    return "".join(result)


def _pack_multiplayer_message(
    player_id, message_type, x=0.0, z=0.0, heading=0.0, in_car=False
):
    return b",".join(
        (
            player_id,
            message_type,
            _float_to_ascii_bytes(x),
            _float_to_ascii_bytes(z),
            _float_to_ascii_bytes(heading),
            b"1" if in_car else b"0",
        )
    )


def _parse_multiplayer_message(message):
    if not isinstance(message, bytes) or len(message) > 160:
        return None

    fields = message.split(b",")
    if len(fields) != 6:
        return None
    player_id, message_type, x_bytes, z_bytes, heading_bytes, in_car_bytes = fields
    if not player_id or len(player_id) > 100:
        return None
    if message_type == b"leave":
        return player_id, message_type, 0.0, 0.0, 0.0, False
    if message_type != b"state":
        return None

    x = _parse_ascii_float(x_bytes)
    z = _parse_ascii_float(z_bytes)
    heading = _parse_ascii_float(heading_bytes)
    if x is None or z is None or heading is None or in_car_bytes not in (b"0", b"1"):
        return None
    return player_id, message_type, x, z, heading, in_car_bytes == b"1"


def _cell_hash(col, row, salt):
    """Return a stable hash for a block cell and salt."""
    value = (col * 73856093) ^ (row * 19349663) ^ (salt * 83492791)
    return value & 0x7FFFFFFF


def _player_update(entity, game):
    """Forward the player callback to the active city."""
    if _city is not None:
        _city.update_player(entity, game)


def _person_update(entity, _game):
    """Forward a pedestrian callback to the active city."""
    if _city is not None:
        _city.update_person(entity)


def _traffic_update(entity, _game):
    """Forward a traffic car callback to the active city."""
    if _city is not None:
        _city.update_traffic(entity)


def _player_render(_entity, draw, _game):
    """Draw the HUD from the player render pass."""
    if _city is not None:
        _city.draw_hud(draw)


def _background_render(_entity, draw, _game):
    """Draw the sky and distant city horizon."""
    if _city is not None:
        _city.draw_background(draw)


class _City:
    """Own the city scene and open-world state."""

    WORLD_SIZE = 840.0
    WORLD_HALF = 420.0
    GRID_LIMIT = 5
    ROAD_SPACING = 84.0
    ROAD_WIDTH = 5.5
    ROAD_HEIGHT = 0.06
    ROAD_SEGMENT = 4.2
    SIDEWALK_WIDTH = 1.2
    SIDEWALK_OFFSET = 3.35
    SIDEWALK_HEIGHT = 0.03
    SIDEWALK_SEGMENT = 6.0
    MARK_SPACING = 14.0
    MARK_OFFSET = 7.0
    MARK_WIDTH = 0.12
    MARK_LENGTH = 2.6
    MARK_HEIGHT = 0.10
    BLOCK_CENTER = 42.0
    BLOCK_REACH = 40.0
    BUILDING_REACH = 8.0
    SCENE_ANCHOR_Z = -1000.0
    BACKGROUND_Z = 2000.0
    FIELD_OF_VIEW = 40.0
    CHUNK_LAG = 12.0
    MINIMAP_SIZE = 60.0
    MINIMAP_RANGE = 44.0
    WALK_SPEED = 0.36
    WALK_TURN = 0.25
    CAR_ACCEL = 0.05
    CAR_BRAKE = 0.085
    CAR_FRICTION = 0.012
    CAR_STEER = 0.16
    CAR_MAX_SPEED = 1.0
    CAR_MAX_REVERSE = -0.35
    CAR_RADIUS = 0.72
    TRAFFIC_OFFSET = 1.2
    PERSON_COUNT = 6
    RECYCLE_DISTANCE = 56.0
    TRAFFIC_COUNT = 6
    TRAFFIC_SPEED = 0.45
    TRAFFIC_TURN = 0.6
    TRAFFIC_DECISION = 30
    TRAVEL_SPEED = 0.45
    CAR_COLORS = (0xF800, 0xFD20, 0x001F, 0x07FF, 0xF81F, 0x001F)
    CAMERA_DISTANCE = 8.2
    CAMERA_INDOOR_DISTANCE = 2.6
    MULTIPLAYER_API = "https://www.jblanked.com/picoware/api/picocity/"
    MULTIPLAYER_WS = "wss://www.jblanked.com/ws/picoware/picocity/"
    MULTIPLAYER_MAX_PLAYERS = 4
    MULTIPLAYER_MAX_LOBBIES = 4
    MULTIPLAYER_SEND_INTERVAL = 6
    MULTIPLAYER_REMOTE_TIMEOUT = 900
    MULTIPLAYER_INBOX_SIZE = 24

    COLOR_BLACK = 0x0000
    COLOR_SKY = 0x5D9F
    COLOR_HORIZON = 0x8C71
    COLOR_GROUND = 0xBDF7
    COLOR_SIDEWALK = 0xD69A
    COLOR_ROAD = 0x39C7
    COLOR_LINE = 0xFFE0
    COLOR_WINDOW = 0x2A8A
    COLOR_ROOF = 0x632C
    COLOR_DOOR = 0x1080
    COLOR_PLAYER = 0x07FF
    COLOR_SKIN = 0xFD20
    COLOR_GLASS = 0x5D9B
    COLOR_TRUNK = 0x6B4D
    COLOR_LEAF = 0x07E0
    BUILDING_COLORS = (
        (0xB5B6, 0x7BEF),
        (0xD69A, 0xFBE0),
        (0x6B4D, 0xC618),
        (0xA145, 0xFD20),
        (0x9CB2, 0x5D9B),
        (0xFBE0, 0xFD20),
        (0xC618, 0x9CB2),
        (0xA145, 0xFFE0),
    )
    PERSON_COLORS = (0x001F, 0xF800, 0x07E0, 0xFD20, 0xF81F, 0x001F)
    GARAGE_DOOR_WIDTH = 2.4
    GARAGE_DOOR_HEIGHT = 2.0
    FLOOR_COLOR = 0x9C8A
    CEILING_COLOR = 0x734E

    BLOCK_SLOTS = (
        (-30.0, -20.0),
        (-30.0, 20.0),
        (30.0, -20.0),
        (30.0, 20.0),
        (-20.0, -30.0),
        (20.0, -30.0),
        (-20.0, 30.0),
        (20.0, 30.0),
    )

    def __init__(self, view_manager):
        self.view_manager = view_manager
        self.draw = view_manager.draw
        self.game = None
        self.level = None
        self.engine = None
        self.meshes = []
        self.city_mesh = None
        self.buildings = []
        self.people = []
        self.people_dir_x = []
        self.people_dir_z = []
        self.people_walk = []
        self.people_speeds = []
        self.traffic = []
        self.traffic_speed = []
        self.traffic_axis = []
        self.traffic_line = []
        self.traffic_dir = []
        self.player = None
        self.in_car = False
        self.speed = 0.0
        self.heading = pi * 0.5
        self.message = ""
        self.message_timer = 0
        self.multiplayer_view = "title"
        self.multiplayer_menu_origin = None
        self.multiplayer_selection = 0
        self.multiplayer_lobbies = []
        self.multiplayer_lobby_index = 0
        self.multiplayer_status = ""
        self.multiplayer_http = None
        self.multiplayer_http_action = None
        self.multiplayer_ws = None
        self.multiplayer_socket_error = ""
        self.multiplayer_socket_closed = False
        self.multiplayer_inbox = []
        self.multiplayer_player_id = ""
        self.multiplayer_player_id_bytes = b""
        self.multiplayer_target_lobby_id = ""
        self.multiplayer_lobby_id = ""
        self.multiplayer_connection_state = "idle"
        self.multiplayer_exit_after_leave = False
        self.multiplayer_exit_ready = False
        self.multiplayer_leave_notice = ""
        self.multiplayer_frame = 0
        self.multiplayer_frames_since_send = 0
        self.multiplayer_remote_players = {}

    def _start_game(self):
        """Create the city scene and engine after a game mode is selected."""
        if self.engine is not None:
            return True

        from picoware.engine.camera import CAMERA_THIRD_PERSON, Camera
        from picoware.engine.engine import GameEngine
        from picoware.engine.game import Game
        from picoware.engine.level import Level

        game = Game(
            "Pico City",
            self.draw.size,
            self.draw,
            self.view_manager.input_manager,
            self.COLOR_LINE,
            self.COLOR_SKY,
            Camera(
                direction=Vector(0, 1),
                plane=Vector(-0.72, 0),
                height=2.2,
                distance=self.CAMERA_DISTANCE,
                perspective=CAMERA_THIRD_PERSON,
            ),
        )
        self.game = game
        self.level = Level("Downtown", self.draw.size, game)
        self.level.set_light_direction(-0.35, 1.0, -0.5)
        self.level.set_shadow_color(0)
        self._build_background()
        self._build_city()
        self._build_player()
        self._build_traffic()
        self._build_people()
        self.anchor_x = self.player.position.x
        self.anchor_z = self.player.position.y
        self._fill_city(self.anchor_x, self.anchor_z)
        game.level_add(self.level)
        self.engine = GameEngine(game, 30)
        return self.engine is not None

    def _multiplayer_menu_options(self):
        if self.multiplayer_lobby_id:
            return ("Leave lobby", "Close")
        back_option = "Back" if self.multiplayer_menu_origin == "title" else "Close"
        return ("Create lobby (4)", "Join lobby", back_option)

    def handle_multiplayer_input(self, button):
        """Handle multiplayer menu input without consuming gameplay controls."""
        from picoware.system.buttons import (
            BUTTON_BACK,
            BUTTON_CENTER,
            BUTTON_DOWN,
            BUTTON_START,
            BUTTON_UP,
        )

        if self.multiplayer_view is None:
            if button != BUTTON_START:
                return False
            self.multiplayer_menu_origin = None
            self.multiplayer_view = "menu"
            self.multiplayer_selection = 0
            return True

        if self.multiplayer_view == "title":
            if button == BUTTON_BACK:
                self.multiplayer_exit_ready = True
            elif button in (BUTTON_UP, BUTTON_DOWN):
                direction = -1 if button == BUTTON_UP else 1
                self.multiplayer_selection = (
                    self.multiplayer_selection + direction
                ) % 2
            elif button == BUTTON_CENTER:
                self.multiplayer_menu_origin = "title"
                if not self._start_game():
                    self._set_multiplayer_error("Unable to start Pico City")
                elif self.multiplayer_selection == 0:
                    self.multiplayer_view = None
                    self.multiplayer_menu_origin = None
                else:
                    self.multiplayer_view = "menu"
                    self.multiplayer_menu_origin = "title"
                    self.multiplayer_selection = 0
            return True

        if self.multiplayer_view == "pending":
            return True

        if self.multiplayer_view == "error":
            if button in (BUTTON_BACK, BUTTON_CENTER):
                self.multiplayer_view = "menu"
                self.multiplayer_selection = 0
            return True

        if self.multiplayer_view == "lobbies":
            if button == BUTTON_BACK:
                self.multiplayer_view = "menu"
                self.multiplayer_selection = 1
            elif button in (BUTTON_UP, BUTTON_DOWN) and self.multiplayer_lobbies:
                direction = -1 if button == BUTTON_UP else 1
                self.multiplayer_lobby_index = (
                    self.multiplayer_lobby_index + direction
                ) % len(self.multiplayer_lobbies)
            elif button == BUTTON_CENTER and self.multiplayer_lobbies:
                lobby = self.multiplayer_lobbies[self.multiplayer_lobby_index]
                self._join_multiplayer_lobby(lobby["lobby_id"])
            return True

        if self.multiplayer_view == "menu":
            if button in (BUTTON_BACK, BUTTON_START):
                if self.multiplayer_menu_origin == "title":
                    self.multiplayer_view = "title"
                    self.multiplayer_selection = 1
                    self.multiplayer_menu_origin = None
                else:
                    self.multiplayer_view = None
                return True

            options = self._multiplayer_menu_options()
            if button in (BUTTON_UP, BUTTON_DOWN):
                direction = -1 if button == BUTTON_UP else 1
                self.multiplayer_selection = (
                    self.multiplayer_selection + direction
                ) % len(options)
            elif button == BUTTON_CENTER:
                if self.multiplayer_lobby_id:
                    if self.multiplayer_selection == 0:
                        self._leave_multiplayer(False)
                    else:
                        self.multiplayer_view = None
                elif self.multiplayer_selection == 0:
                    self._create_multiplayer_lobby()
                elif self.multiplayer_selection == 1:
                    self._fetch_multiplayer_lobbies()
                elif self.multiplayer_menu_origin == "title":
                    self.multiplayer_view = "title"
                    self.multiplayer_selection = 1
                    self.multiplayer_menu_origin = None
                else:
                    self.multiplayer_view = None
            return True

        return True

    def _ensure_multiplayer_player_id(self):
        if self.multiplayer_player_id:
            return True

        try:
            from machine import unique_id
            from time import ticks_ms
            from ubinascii import hexlify
        except ImportError as error:
            self._set_multiplayer_error("Device ID unavailable")
            self.view_manager.log(
                "[PicoCity multiplayer] Device ID unavailable: %s" % error, 2
            )
            return False

        device_id = unique_id()
        if not device_id:
            self._set_multiplayer_error("Device ID unavailable")
            self.view_manager.log("[PicoCity multiplayer] Device ID unavailable", 2)
            return False
        timestamp = ticks_ms()
        random_id = _next_random(0x7FFFFFFF)
        device_id_hex = hexlify(device_id)
        self.multiplayer_player_id = "%s-%x-%x" % (
            _hex_bytes_to_text(device_id),
            timestamp,
            random_id,
        )
        self.multiplayer_player_id_bytes = (
            device_id_hex
            + b"-"
            + _integer_to_ascii_bytes(timestamp, 16)
            + b"-"
            + _integer_to_ascii_bytes(random_id, 16)
        )
        return True

    def _begin_multiplayer_request(self, action, payload=None):
        from picoware.system.http import HTTP

        if self.multiplayer_http is not None:
            self._set_multiplayer_error("A request is already in progress")
            return False

        http = HTTP(thread_manager=self.view_manager.thread_manager)
        self.multiplayer_http = http
        self.multiplayer_http_action = action
        headers = {
            "Content-Type": "application/json",
            "HTTP_USER_AGENT": "Pico",
            "Setting": "X-Flipper-Redirect",
            "User-Agent": "Raspberry Pi Pico W",
        }
        if action == "list":
            url = "%slobbies/%d/%d/" % (
                self.MULTIPLAYER_API,
                self.MULTIPLAYER_MAX_PLAYERS,
                self.MULTIPLAYER_MAX_LOBBIES,
            )
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
                self.multiplayer_http = None
                self.multiplayer_http_action = None
                self._set_multiplayer_error("Unsupported multiplayer request")
                return False
            started = http.post_async(
                self.MULTIPLAYER_API + path, payload, headers=headers
            )
            statuses = {
                "create": "Creating lobby...",
                "join": "Joining lobby...",
                "remove": "Leaving lobby...",
            }
            status = statuses[action]

        if not started:
            error = http.error or "Could not start the request"
            http.close()
            self.multiplayer_http = None
            self.multiplayer_http_action = None
            if action == "join":
                self.multiplayer_target_lobby_id = ""
            if action == "remove":
                self._finish_multiplayer_leave(error)
            else:
                self._set_multiplayer_error(error)
            return False

        self.multiplayer_status = status
        self.multiplayer_view = "pending"
        return True

    def _fetch_multiplayer_lobbies(self):
        self.multiplayer_lobbies = []
        self.multiplayer_lobby_index = 0
        self._begin_multiplayer_request("list")

    def _create_multiplayer_lobby(self):
        if not self._ensure_multiplayer_player_id():
            return
        self.multiplayer_target_lobby_id = ""
        self._begin_multiplayer_request(
            "create",
            {"max_players": self.MULTIPLAYER_MAX_PLAYERS, "data": {}},
        )

    def _join_multiplayer_lobby(self, lobby_id):
        if not self._ensure_multiplayer_player_id():
            return
        self.multiplayer_target_lobby_id = lobby_id
        self._begin_multiplayer_request(
            "join",
            {
                "lobby_id": lobby_id,
                "player_id": self.multiplayer_player_id,
            },
        )

    def _set_multiplayer_error(self, message):
        self.multiplayer_status = str(message)
        self.multiplayer_view = "error"
        if not self.multiplayer_lobby_id:
            self.multiplayer_connection_state = "idle"
        self.view_manager.log("[PicoCity multiplayer] %s" % self.multiplayer_status, 2)

    def _multiplayer_response_data(self, text):
        try:
            data = json_loads(text)
        except (TypeError, ValueError) as error:
            self._set_multiplayer_error("Invalid server response")
            self.view_manager.log(
                "[PicoCity multiplayer] Invalid JSON response: %s" % error, 2
            )
            return None
        if not isinstance(data, dict):
            self._set_multiplayer_error("Unexpected server response")
            return None
        return data

    def _poll_multiplayer_http(self):
        http = self.multiplayer_http
        if http is None or not http.is_request_complete():
            return

        action = self.multiplayer_http_action
        error = http.error
        response = http.response
        status_code = response.status_code if response is not None else 0
        response_text = response.text if response is not None else ""
        http.close()
        self.multiplayer_http = None
        self.multiplayer_http_action = None

        if action == "remove":
            if error:
                self._finish_multiplayer_leave(error)
            elif response is None:
                self._finish_multiplayer_leave("No HTTP response")
            elif status_code not in (200, 204):
                self._finish_multiplayer_leave("HTTP %d" % status_code)
            else:
                self._finish_multiplayer_leave()
            return

        if error:
            if action == "join":
                self.multiplayer_target_lobby_id = ""
            self._set_multiplayer_error("Request failed: %s" % error)
            return
        if response is None:
            if action == "join":
                self.multiplayer_target_lobby_id = ""
            self._set_multiplayer_error("No HTTP response")
            return

        if action == "list":
            if status_code != 200:
                self._set_multiplayer_error("Lobby list failed (HTTP %d)" % status_code)
                return
            data = self._multiplayer_response_data(response_text)
            if data is None:
                return
            lobbies = data.get("lobbies")
            if not isinstance(lobbies, list):
                self._set_multiplayer_error("Invalid lobby list")
                return
            for lobby in lobbies[: self.MULTIPLAYER_MAX_LOBBIES]:
                if not isinstance(lobby, dict):
                    continue
                lobby_id = lobby.get("lobby_id")
                player_count = lobby.get("player_count")
                max_players = lobby.get("max_players")
                if (
                    isinstance(lobby_id, str)
                    and lobby_id
                    and isinstance(player_count, int)
                    and isinstance(max_players, int)
                    and 0 <= player_count < max_players
                    and max_players > 0
                ):
                    self.multiplayer_lobbies.append(
                        {
                            "lobby_id": lobby_id,
                            "player_count": player_count,
                            "max_players": max_players,
                        }
                    )
            self.multiplayer_lobby_index = 0
            self.multiplayer_view = "lobbies"
            self.multiplayer_status = ""
            return

        if action == "create":
            if status_code not in (200, 201):
                self._set_multiplayer_error(
                    "Lobby creation failed (HTTP %d)" % status_code
                )
                return
            data = self._multiplayer_response_data(response_text)
            if data is None:
                return
            lobby_id = data.get("lobby_id")
            if not isinstance(lobby_id, str) or not lobby_id:
                self._set_multiplayer_error("Server returned no lobby ID")
                return
            self.multiplayer_target_lobby_id = lobby_id
            self._join_multiplayer_lobby(lobby_id)
            return

        if action == "join":
            if status_code not in (200, 201):
                self.multiplayer_target_lobby_id = ""
                if status_code == 409:
                    message = "Lobby is full"
                elif status_code == 404:
                    message = "Lobby not found"
                else:
                    message = "Join failed (HTTP %d)" % status_code
                self._set_multiplayer_error(message)
                return
            self.multiplayer_lobby_id = self.multiplayer_target_lobby_id
            self.multiplayer_target_lobby_id = ""
            self._connect_multiplayer()
            return

        self._set_multiplayer_error("Unexpected multiplayer response")

    def _connect_multiplayer(self):
        from picoware.system.websocket import WebSocketAsync

        self.multiplayer_inbox = []
        self.multiplayer_socket_error = ""
        self.multiplayer_socket_closed = False
        self.multiplayer_connection_state = "connecting"
        self.multiplayer_status = "Connecting..."
        self.multiplayer_view = "pending"
        self.multiplayer_ws = WebSocketAsync(
            uri="%s%s/" % (self.MULTIPLAYER_WS, self.multiplayer_lobby_id),
            callback=self._on_multiplayer_message,
            thread_manager=self.view_manager.thread_manager,
        )
        if not self.multiplayer_ws.connect():
            error = self.multiplayer_ws.error or "WebSocket could not start"
            self._leave_multiplayer(False, "Connection failed: %s" % error)

    def _on_multiplayer_message(self, data):
        if self.multiplayer_connection_state not in ("connecting", "active"):
            return
        if data is None:
            self.multiplayer_socket_closed = True
        elif isinstance(data, Exception):
            self.multiplayer_socket_error = str(data)
        else:
            if data == "PONG":
                return
            if not isinstance(data, bytes):
                self.multiplayer_socket_error = "Expected a binary WebSocket message"
                return
            if len(self.multiplayer_inbox) >= self.MULTIPLAYER_INBOX_SIZE:
                del self.multiplayer_inbox[0]
            self.multiplayer_inbox.append(data)

    def _poll_multiplayer_websocket(self):
        websocket = self.multiplayer_ws
        if self.multiplayer_connection_state == "connecting":
            if self.multiplayer_socket_error:
                self._leave_multiplayer(
                    False,
                    "Connection failed: %s" % self.multiplayer_socket_error,
                )
            elif websocket is not None and websocket.is_connected:
                self.multiplayer_connection_state = "active"
                self.multiplayer_status = "Connected"
                self.multiplayer_view = "menu"
                self.multiplayer_menu_origin = None
                self.multiplayer_selection = 0
                self.multiplayer_frames_since_send = self.MULTIPLAYER_SEND_INTERVAL
        elif self.multiplayer_connection_state == "active":
            if (
                self.multiplayer_socket_error
                or self.multiplayer_socket_closed
                or websocket is None
                or not websocket.is_connected
            ):
                reason = self.multiplayer_socket_error or "Connection lost"
                self._leave_multiplayer(False, reason)

    def _leave_multiplayer(self, exit_after, notice=""):
        self.multiplayer_exit_after_leave = exit_after
        self.multiplayer_leave_notice = notice
        if (
            self.multiplayer_ws is not None
            and self.multiplayer_ws.is_connected
            and self.multiplayer_lobby_id
        ):
            leave_message = _pack_multiplayer_message(
                self.multiplayer_player_id_bytes, b"leave"
            )
            if not self.multiplayer_ws.send(leave_message):
                self.view_manager.log(
                    "[PicoCity multiplayer] Could not relay leave message", 2
                )

        self.multiplayer_connection_state = "leaving"
        if not self.multiplayer_lobby_id:
            self._finish_multiplayer_leave()
            return
        self._begin_multiplayer_request(
            "remove",
            {
                "lobby_id": self.multiplayer_lobby_id,
                "player_id": self.multiplayer_player_id,
            },
        )

    def _finish_multiplayer_leave(self, error=None):
        exit_after = self.multiplayer_exit_after_leave
        notice = self.multiplayer_leave_notice
        self.multiplayer_exit_after_leave = False
        self.multiplayer_leave_notice = ""
        self.multiplayer_connection_state = "error" if error else "idle"
        if not error:
            self.multiplayer_lobby_id = ""
        self.multiplayer_target_lobby_id = ""
        if self.multiplayer_ws is not None:
            self.multiplayer_ws.close()
            self.multiplayer_ws = None
        self.multiplayer_socket_error = ""
        self.multiplayer_socket_closed = False
        self.multiplayer_inbox = []
        self._remove_all_remote_players()

        if error:
            self.multiplayer_status = (
                "%s; leave failed" % notice if notice else "Leave failed: %s" % error
            )
            self.multiplayer_view = "error"
            self.view_manager.log("[PicoCity multiplayer] Leave failed: %s" % error, 2)
        elif notice:
            self.multiplayer_status = notice
            self.multiplayer_view = "error"
            self.view_manager.log("[PicoCity multiplayer] %s" % notice, 2)
        else:
            self.multiplayer_status = "Left lobby"
            self.multiplayer_view = "menu"

        if exit_after:
            self.multiplayer_view = None
            self.multiplayer_exit_ready = True

    def _create_remote_player(self):
        if len(self.multiplayer_remote_players) >= self.MULTIPLAYER_MAX_PLAYERS - 1:
            return None

        from picoware.engine.entity import (
            ENTITY_TYPE_3D_SPRITE,
            SPRITE_3D_HUMANOID,
        )

        index = len(self.multiplayer_remote_players)
        color = self.CAR_COLORS[(index + 1) % len(self.CAR_COLORS)]
        name = "Online %d" % (index + 1)
        player = Entity(
            name,
            ENTITY_TYPE_3D_SPRITE,
            Vector(0, 0),
            Vector(0.6, 1.5),
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
            SPRITE_3D_HUMANOID,
            color,
        )
        self.level.entity_add(player)
        car = self._mesh_entity(
            name + " Car",
            Vector(0, 0),
            Vector(1.05, 1.85),
            self._car_mesh(color),
        )
        car.is_visible = False
        return {
            "player": player,
            "car": car,
            "color": color,
            "last_seen": self.multiplayer_frame,
        }

    def _remove_remote_player(self, player_id):
        remote = self.multiplayer_remote_players.pop(player_id, None)
        if remote is None:
            return
        car = remote["car"]
        mesh = car.sprite_3d
        if self.level is not None:
            self.level.entity_remove(car)
            self.level.entity_remove(remote["player"])
        if mesh is not None and mesh in self.meshes:
            self.meshes.remove(mesh)

    def _remove_all_remote_players(self):
        for player_id in list(self.multiplayer_remote_players.keys()):
            self._remove_remote_player(player_id)

    def _process_multiplayer_message(self, message):
        packet = _parse_multiplayer_message(message)
        if packet is None:
            self.view_manager.log(
                "[PicoCity multiplayer] Ignored invalid binary packet", 2
            )
            return

        player_id, message_type, x, z, heading, in_car = packet
        if player_id == self.multiplayer_player_id_bytes:
            return
        if message_type == b"leave":
            self._remove_remote_player(player_id)
            return
        if message_type != b"state":
            return

        if (
            not -self.WORLD_HALF <= x <= self.WORLD_HALF
            or not -self.WORLD_HALF <= z <= self.WORLD_HALF
            or not -1000.0 <= heading <= 1000.0
        ):
            return

        remote = self.multiplayer_remote_players.get(player_id)
        if remote is None:
            remote = self._create_remote_player()
            if remote is None:
                return
            self.multiplayer_remote_players[player_id] = remote

        dx = cos(heading)
        dz = sin(heading)
        rotation = atan2(dz, dx) - pi * 0.5
        remote["player"].position_set(x, z)
        remote["player"].direction_set(dx, dz)
        remote["player"].set_3d_sprite_rotation(rotation)
        remote["player"].is_visible = not in_car
        remote["car"].position_set(x, z)
        remote["car"].direction_set(dx, dz)
        remote["car"].set_3d_sprite_rotation(rotation)
        remote["car"].is_visible = in_car
        remote["last_seen"] = self.multiplayer_frame

    def _process_multiplayer_inbox(self):
        for _ in range(8):
            if not self.multiplayer_inbox:
                break
            self._process_multiplayer_message(self.multiplayer_inbox.pop(0))

        stale_players = []
        for player_id, remote in self.multiplayer_remote_players.items():
            if (
                self.multiplayer_frame - remote["last_seen"]
                > self.MULTIPLAYER_REMOTE_TIMEOUT
            ):
                stale_players.append(player_id)
        for player_id in stale_players:
            self._remove_remote_player(player_id)

    def _send_multiplayer_state(self):
        if (
            self.multiplayer_connection_state != "active"
            or self.multiplayer_ws is None
            or not self.multiplayer_ws.is_connected
        ):
            return
        self.multiplayer_frames_since_send += 1
        if self.multiplayer_frames_since_send < self.MULTIPLAYER_SEND_INTERVAL:
            return
        self.multiplayer_frames_since_send = 0
        state = _pack_multiplayer_message(
            self.multiplayer_player_id_bytes,
            b"state",
            float(self.player.position.x),
            float(self.player.position.y),
            float(self.heading),
            self.in_car,
        )
        if not self.multiplayer_ws.send(state):
            self.multiplayer_socket_error = "WebSocket send failed"

    def _mesh_entity(
        self, name, position, size, mesh, update=None, render=None, collision=None
    ):
        from picoware.engine.entity import ENTITY_TYPE_3D_SPRITE, SPRITE_3D_CUSTOM

        entity = Entity(
            name,
            ENTITY_TYPE_3D_SPRITE,
            position,
            size,
            None,
            None,
            None,
            None,
            None,
            update,
            render,
            collision,
            False,
            SPRITE_3D_CUSTOM,
            self.COLOR_BLACK,
        )
        mesh.set_wireframe(False)
        entity.sprite_3d = mesh
        entity.sprite_3d_type = SPRITE_3D_CUSTOM
        entity.is_visible = True
        self.meshes.append(mesh)
        self.level.entity_add(entity)
        return entity

    def _triangle(self, mesh, first, second, third, color):
        mesh.add_triangle(
            first[0],
            first[1],
            first[2],
            second[0],
            second[1],
            second[2],
            third[0],
            third[1],
            third[2],
            color,
            False,
        )

    def _quad(self, mesh, first, second, third, fourth, color):
        self._triangle(mesh, first, second, third, color)
        self._triangle(mesh, first, fourth, second, color)

    def _ground_rect(self, mesh, x, z, width, depth, height, color, segment_size):
        """Add a flat rectangle split into near plane safe strips."""
        z -= self.SCENE_ANCHOR_Z
        if width >= depth:
            width_steps = max(1, int((width + segment_size - 0.001) / segment_size))
            depth_steps = 1
        else:
            width_steps = 1
            depth_steps = max(1, int((depth + segment_size - 0.001) / segment_size))

        cell_width = width / width_steps
        cell_depth = depth / depth_steps
        start_x = x - width * 0.5
        start_z = z - depth * 0.5
        _quad = self._quad
        for width_index in range(width_steps):
            cell_x = start_x + cell_width * (width_index + 0.5)
            for depth_index in range(depth_steps):
                cell_z = start_z + cell_depth * (depth_index + 0.5)
                half_width = cell_width * 0.5
                half_depth = cell_depth * 0.5
                _quad(
                    mesh,
                    (cell_x - half_width, height, cell_z - half_depth),
                    (cell_x + half_width, height, cell_z + half_depth),
                    (cell_x + half_width, height, cell_z - half_depth),
                    (cell_x - half_width, height, cell_z + half_depth),
                    color,
                )

    def _add_building(
        self, mesh, x, z, width, depth, height, wall_color, roof_color, building_type
    ):
        """Add one building and register its collision rectangle."""
        scene_z = z - self.SCENE_ANCHOR_Z
        is_house = building_type == 1
        is_tower = building_type == 2
        if is_house:
            self._build_house(mesh, x, z, width, depth, height, wall_color, roof_color)
        else:
            mesh.create_cube(x, height * 0.5, scene_z, width, height, depth, wall_color)
            mesh.create_cube(
                x,
                height + 0.10,
                scene_z,
                width + 0.12,
                0.20,
                depth + 0.12,
                roof_color,
            )
            window_height = min(0.14, height * 0.07)
            window_y = min(height - 0.35, 1.2)
            front = scene_z + depth * 0.5 + 0.02
            half_width = width * 0.275
            self._window(mesh, x, window_y, front, half_width, window_height)
            if height > 4.5:
                self._window(mesh, x, height * 0.58, front, half_width, window_height)
            if is_tower:
                mesh.create_cube(
                    x, height + 0.5, scene_z, 0.10, 1.0, 0.10, self.COLOR_ROOF
                )
        self.buildings.append((x, z, width * 0.5, depth * 0.5, is_house))

    def _window(self, mesh, x, y, z, half_width, half_height):
        """Add a flat window quad facing south, double sided."""
        xl = x - half_width
        xr = x + half_width
        yb = y - half_height
        yt = y + half_height
        self._triangle(mesh, (xl, yb, z), (xr, yb, z), (xr, yt, z), self.COLOR_WINDOW)
        self._triangle(mesh, (xl, yb, z), (xr, yt, z), (xl, yt, z), self.COLOR_WINDOW)
        self._triangle(mesh, (xr, yb, z), (xl, yb, z), (xl, yt, z), self.COLOR_WINDOW)
        self._triangle(mesh, (xr, yb, z), (xl, yt, z), (xr, yt, z), self.COLOR_WINDOW)

    def _car_to_mesh(self, mesh, cx, cz, color):
        """Add a small car's three cubes to a mesh at (cx, cz)."""
        mesh.create_cube(cx, 0.36, cz, 1.05, 0.34, 1.85, color)
        mesh.create_cube(cx, 0.62, cz + 0.10, 0.68, 0.24, 0.72, self.COLOR_GLASS)
        mesh.create_cube(cx, 0.20, cz - 0.78, 0.85, 0.10, 0.12, self.COLOR_LINE)

    def _car_mesh(self, color):
        """Build the shared car geometry for one color."""
        from picoware.engine.sprite3d import Sprite3D

        mesh = Sprite3D()
        self._car_to_mesh(mesh, 0, 0, color)
        mesh.set_wireframe(False)
        return mesh

    def _add_tree(self, mesh, x, z):
        """Add a tree trunk and canopy to the city mesh."""
        scene_z = z - self.SCENE_ANCHOR_Z
        mesh.create_cube(x, 0.50, scene_z, 0.24, 1.00, 0.24, self.COLOR_TRUNK)
        mesh.create_cube(x, 1.15, scene_z, 0.85, 0.60, 0.85, self.COLOR_LEAF)
        mesh.create_cube(x, 1.55, scene_z, 0.55, 0.35, 0.55, self.COLOR_LEAF)

    def _squad(self, mesh, first, second, third, fourth, color, both_sides=False):
        """Add a quad. Optional both_sides draws two facing windings."""
        self._quad(mesh, first, second, third, fourth, color)
        if both_sides:
            self._triangle(mesh, first, third, second, color)
            self._triangle(mesh, first, second, fourth, color)

    def _build_garage(self, mesh, x, z, width, depth, height, wall_color):
        """Add a hollow garage inside a house: floor, ceiling, double-sided walls, doorway."""
        scene_z = z - self.SCENE_ANCHOR_Z
        hw = width * 0.5
        hd = depth * 0.5
        floor_y = 0.05
        ceil_y = height - 0.15
        z0 = scene_z - hd + 0.1
        z1 = scene_z + hd - 0.1
        door_half = self.GARAGE_DOOR_WIDTH * 0.5
        # Floor (both sides so it reads from inside and out).
        self._squad(
            mesh,
            (x - hw, floor_y, z0),
            (x + hw, floor_y, z1),
            (x + hw, floor_y, z0),
            (x - hw, floor_y, z1),
            self.FLOOR_COLOR,
            True,
        )
        # Ceiling, both sides.
        self._squad(
            mesh,
            (x - hw, ceil_y, z0),
            (x + hw, ceil_y, z1),
            (x + hw, ceil_y, z0),
            (x - hw, ceil_y, z1),
            self.CEILING_COLOR,
            True,
        )
        # Back wall (north side), both sides.
        self._squad(
            mesh,
            (x - hw, floor_y, z0),
            (x + hw, ceil_y, z0),
            (x + hw, floor_y, z0),
            (x - hw, ceil_y, z0),
            wall_color,
            True,
        )
        # Front wall (south side) with a doorway: two slabs flanking the opening.
        if door_half < hw:
            self._squad(
                mesh,
                (x - hw, floor_y, z1),
                (x - door_half, ceil_y, z1),
                (x - door_half, floor_y, z1),
                (x - hw, ceil_y, z1),
                wall_color,
                True,
            )
            self._squad(
                mesh,
                (x + door_half, floor_y, z1),
                (x + hw, ceil_y, z1),
                (x + hw, floor_y, z1),
                (x + door_half, ceil_y, z1),
                wall_color,
                True,
            )
        # Left wall (west side), both sides.
        self._squad(
            mesh,
            (x - hw, floor_y, z0),
            (x - hw, ceil_y, z1),
            (x - hw, floor_y, z1),
            (x - hw, ceil_y, z0),
            wall_color,
            True,
        )
        # Right wall (east side), both sides.
        self._squad(
            mesh,
            (x + hw, floor_y, z0),
            (x + hw, ceil_y, z1),
            (x + hw, floor_y, z1),
            (x + hw, ceil_y, z0),
            wall_color,
            True,
        )
        # Parked car inside the garage (static triangles on the city mesh).
        self._car_to_mesh(mesh, x + hw * 0.45, z, self.COLOR_PLAYER)

    def _build_house(self, mesh, x, z, width, depth, height, wall_color, roof_color):
        """Add a hollow house (garage) with an open front doorway and double-sided walls."""
        scene_z = z - self.SCENE_ANCHOR_Z
        hw = width * 0.5
        hd = depth * 0.5
        # Roof slab.
        mesh.create_cube(
            x, height - 0.05, scene_z, width + 0.10, 0.10, depth + 0.10, roof_color
        )
        # Hollow interior with open front doorway.
        self._build_garage(mesh, x, z, width, depth, height, wall_color)

    def _build_player(self):
        """Create the player pedestrian entity."""
        from picoware.engine.entity import ENTITY_TYPE_3D_SPRITE, SPRITE_3D_HUMANOID

        self.player = Entity(
            "Player",
            ENTITY_TYPE_3D_SPRITE,
            Vector(self.SIDEWALK_OFFSET, -10.0),
            Vector(0.6, 1.5),
            None,
            None,
            None,
            None,
            None,
            _player_update,
            _player_render,
            None,
            False,
            SPRITE_3D_HUMANOID,
            self.COLOR_SKIN,
        )
        self.player.is_player = True
        self.player.is_visible = True
        self.level.entity_add(self.player)
        self.player_car = self._mesh_entity(
            "PlayerCar",
            Vector(self.SIDEWALK_OFFSET, -10.0),
            Vector(1.05, 1.85),
            self._car_mesh(0x07FF),
            render=_player_render,
        )
        self.player_car.is_visible = False

    def _build_traffic(self):
        """Create the AI traffic cars."""
        for index in range(self.TRAFFIC_COUNT):
            color = self.CAR_COLORS[index % len(self.CAR_COLORS)]
            car = self._mesh_entity(
                "Traffic %d" % (index + 1),
                Vector(0, 0),
                Vector(1.05, 1.85),
                self._car_mesh(color),
                _traffic_update,
            )
            self.traffic.append(car)
            self.traffic_axis.append(0)
            self.traffic_line.append(0)
            self.traffic_dir.append(1)
            self.traffic_speed.append(0.0)
            self._spawn_traffic(index)

    def _spawn_traffic(self, index):
        """Place a traffic car on a free street lane near the player."""
        position = self.player.position
        for _attempt in range(10):
            axis = _next_random(2)
            line = _next_random(2 * self.GRID_LIMIT + 1) - self.GRID_LIMIT
            direction = 1 if _next_random(2) == 0 else -1
            lane = -self.TRAFFIC_OFFSET if direction == 1 else self.TRAFFIC_OFFSET
            if axis == 0:
                x = line * self.ROAD_SPACING + lane
                z = position.y + _next_random(41) - 20
            else:
                x = position.x + _next_random(41) - 20
                z = line * self.ROAD_SPACING + lane
            if not self._car_blocked(x, z, index):
                break
        edge = self.WORLD_HALF - 4.0
        if x < -edge:
            x = -edge
        elif x > edge:
            x = edge
        if z < -edge:
            z = -edge
        elif z > edge:
            z = edge
        self.traffic_axis[index] = axis
        self.traffic_line[index] = line
        self.traffic_dir[index] = direction
        car = self.traffic[index]
        car.position_set(x, z)
        self.traffic_speed[index] = self.TRAFFIC_SPEED
        car.is_visible = True

    def _build_people(self):
        """Create the sidewalk pedestrian entities."""
        from picoware.engine.entity import ENTITY_TYPE_3D_SPRITE, SPRITE_3D_HUMANOID

        for index in range(self.PERSON_COUNT):
            person = Entity(
                "Person %d" % (index + 1),
                ENTITY_TYPE_3D_SPRITE,
                Vector(0, 0),
                Vector(0.6, 1.5),
                None,
                None,
                None,
                None,
                None,
                _person_update,
                None,
                None,
                False,
                SPRITE_3D_HUMANOID,
                self.PERSON_COLORS[index],
            )
            person.is_visible = True
            self.people.append(person)
            self.people_dir_x.append(0.0)
            self.people_dir_z.append(1.0)
            self.people_walk.append(0.0)
            self.people_speeds.append(0.020 + (index % 4) * 0.004)
            self.level.entity_add(person)
            self._spawn_person(index)

    def _spawn_person(self, index):
        """Place one pedestrian on a sidewalk near the player."""
        position = self.player.position
        offset = _next_random(41) - 20
        along = -1.0 if _next_random(2) == 0 else 1.0
        roll = _next_random(4)
        if roll < 2:
            line = int(position.x // self.ROAD_SPACING)
            if line < -self.GRID_LIMIT:
                line = -self.GRID_LIMIT
            elif line > self.GRID_LIMIT:
                line = self.GRID_LIMIT
            x = line * self.ROAD_SPACING
            x += -self.SIDEWALK_OFFSET if roll == 0 else self.SIDEWALK_OFFSET
            z = position.y + offset
            self.people_dir_x[index] = 0.0
            self.people_dir_z[index] = along
        else:
            line = int(position.y // self.ROAD_SPACING)
            if line < -self.GRID_LIMIT:
                line = -self.GRID_LIMIT
            elif line > self.GRID_LIMIT:
                line = self.GRID_LIMIT
            x = position.x + offset
            z = line * self.ROAD_SPACING
            z += -self.SIDEWALK_OFFSET if roll == 2 else self.SIDEWALK_OFFSET
            self.people_dir_x[index] = along
            self.people_dir_z[index] = 0.0
        edge = self.WORLD_HALF - 4.0
        if x < -edge:
            x = -edge
        elif x > edge:
            x = edge
        if z < -edge:
            z = -edge
        elif z > edge:
            z = edge
        self.people_walk[index] = 12.0 + _next_random(17)
        person = self.people[index]
        person.position_set(x, z)
        person.set_3d_sprite_rotation(
            atan2(self.people_dir_z[index], self.people_dir_x[index]) - pi * 0.5
        )
        person.is_visible = True

    def _build_background(self):
        """Create the sky and horizon entity."""
        from picoware.engine.entity import ENTITY_TYPE_3D_SPRITE, SPRITE_3D_NONE

        background = Entity(
            "Background",
            ENTITY_TYPE_3D_SPRITE,
            Vector(0, self.BACKGROUND_Z),
            Vector(1, 1),
            None,
            None,
            None,
            None,
            None,
            None,  # update
            _background_render,
            None,
            False,
            SPRITE_3D_NONE,
            self.COLOR_BLACK,
        )
        background.is_visible = True
        self.level.entity_add(background)

    def _build_city(self):
        """Create the city mesh entity."""
        from picoware.engine.sprite3d import Sprite3D

        mesh = Sprite3D()
        self.city_mesh = mesh
        self._mesh_entity(
            "Downtown",
            Vector(0, self.SCENE_ANCHOR_Z),
            Vector(self.WORLD_SIZE, self.WORLD_SIZE),
            mesh,
        )

    def _fill_city(self, center_x, center_z):
        """Build the city geometry inside the field of view box."""
        mesh = self.city_mesh
        mesh.clear_triangles()
        self.buildings = []
        half = self.FIELD_OF_VIEW + self.CHUNK_LAG
        self.box_west = center_x - half
        self.box_east = center_x + half
        self.box_north = center_z - half
        self.box_south = center_z + half
        self._add_streets(mesh)
        specs = []
        self._add_blocks(mesh, specs, center_x, center_z)
        specs.sort(reverse=True)
        for spec in specs:
            self._add_building(
                mesh,
                spec[1],
                spec[2],
                spec[3],
                spec[4],
                spec[5],
                spec[6],
                spec[7],
                spec[8],
            )
        mesh.set_wireframe(False)

    def _update_city(self):
        """Refill the city mesh when the player drifts from the anchor."""
        if not self.player.has_changed_position():
            return
        position = self.player.position
        offset_x = position.x - self.anchor_x
        offset_z = position.y - self.anchor_z
        if (
            offset_x > self.CHUNK_LAG
            or offset_x < -self.CHUNK_LAG
            or offset_z > self.CHUNK_LAG
            or offset_z < -self.CHUNK_LAG
        ):
            self.anchor_x = position.x
            self.anchor_z = position.y
            self._fill_city(self.anchor_x, self.anchor_z)

    def _add_streets(self, mesh):
        """Add the roads, sidewalks and lane marks inside the box."""
        west = self.box_west
        east = self.box_east
        north = self.box_north
        south = self.box_south
        if west < -self.WORLD_HALF:
            west = -self.WORLD_HALF
        if east > self.WORLD_HALF:
            east = self.WORLD_HALF
        if north < -self.WORLD_HALF:
            north = -self.WORLD_HALF
        if south > self.WORLD_HALF:
            south = self.WORLD_HALF
        if west >= east or north >= south:
            return
        spacing = self.ROAD_SPACING
        limit = self.GRID_LIMIT
        first = -int(-(west - 4.0) // spacing)
        last = int((east + 4.0) // spacing)
        if first < -limit:
            first = -limit
        if last > limit:
            last = limit
        for index in range(first, last + 1):
            self._add_road_line(mesh, index * spacing, north, south, True)
        first = -int(-(north - 4.0) // spacing)
        last = int((south + 4.0) // spacing)
        if first < -limit:
            first = -limit
        if last > limit:
            last = limit
        for index in range(first, last + 1):
            self._add_road_line(mesh, index * spacing, west, east, False)

    def _add_road_line(self, mesh, line, begin, end, vertical):
        """Add one road strip with sidewalks and lane dashes."""
        length = end - begin
        middle = (begin + end) * 0.5
        _ground_rect = self._ground_rect
        if vertical:
            _ground_rect(
                mesh,
                line,
                middle,
                self.ROAD_WIDTH,
                length,
                self.ROAD_HEIGHT,
                self.COLOR_ROAD,
                self.ROAD_SEGMENT,
            )
            _ground_rect(
                mesh,
                line - self.SIDEWALK_OFFSET,
                middle,
                self.SIDEWALK_WIDTH,
                length,
                self.SIDEWALK_HEIGHT,
                self.COLOR_SIDEWALK,
                self.SIDEWALK_SEGMENT,
            )
            _ground_rect(
                mesh,
                line + self.SIDEWALK_OFFSET,
                middle,
                self.SIDEWALK_WIDTH,
                length,
                self.SIDEWALK_HEIGHT,
                self.COLOR_SIDEWALK,
                self.SIDEWALK_SEGMENT,
            )
        else:
            _ground_rect(
                mesh,
                middle,
                line,
                length,
                self.ROAD_WIDTH,
                self.ROAD_HEIGHT,
                self.COLOR_ROAD,
                self.ROAD_SEGMENT,
            )
            _ground_rect(
                mesh,
                middle,
                line - self.SIDEWALK_OFFSET,
                length,
                self.SIDEWALK_WIDTH,
                self.SIDEWALK_HEIGHT,
                self.COLOR_SIDEWALK,
                self.SIDEWALK_SEGMENT,
            )
            _ground_rect(
                mesh,
                middle,
                line + self.SIDEWALK_OFFSET,
                length,
                self.SIDEWALK_WIDTH,
                self.SIDEWALK_HEIGHT,
                self.COLOR_SIDEWALK,
                self.SIDEWALK_SEGMENT,
            )
        position = begin + (self.MARK_OFFSET - begin) % self.MARK_SPACING
        while position <= end:
            if vertical:
                _ground_rect(
                    mesh,
                    line,
                    position,
                    self.MARK_WIDTH,
                    self.MARK_LENGTH,
                    self.MARK_HEIGHT,
                    self.COLOR_LINE,
                    self.MARK_LENGTH,
                )
            else:
                _ground_rect(
                    mesh,
                    position,
                    line,
                    self.MARK_LENGTH,
                    self.MARK_WIDTH,
                    self.MARK_HEIGHT,
                    self.COLOR_LINE,
                    self.MARK_LENGTH,
                )
            position += self.MARK_SPACING

    def _add_blocks(self, mesh, specs, center_x, center_z):
        """Collect the block buildings and trees whose lots touch the box."""
        spacing = self.ROAD_SPACING
        reach = self.BLOCK_REACH
        first = int((self.box_west - reach) // spacing)
        last = int((self.box_east + reach) // spacing)
        first_row = int((self.box_north - reach) // spacing)
        last_row = int((self.box_south + reach) // spacing)
        limit = self.GRID_LIMIT
        for col in range(first, last + 1):
            if col < -limit or col >= limit:
                continue
            block_x = col * spacing + self.BLOCK_CENTER
            for row in range(first_row, last_row + 1):
                if row < -limit or row >= limit:
                    continue
                self._add_block(
                    mesh,
                    specs,
                    col,
                    row,
                    block_x,
                    row * spacing + self.BLOCK_CENTER,
                    center_x,
                    center_z,
                )

    def _add_block(self, mesh, specs, col, row, block_x, block_z, center_x, center_z):
        """Collect the hash varied buildings and trees of one city block."""
        if _cell_hash(col, row, 1) % 7 == 0:
            self._add_tree(mesh, block_x, block_z)
            return
        reach = self.BUILDING_REACH
        for index, slot in enumerate(self.BLOCK_SLOTS):
            detail = _cell_hash(col, row, index + 2)
            x = block_x + slot[0]
            z = block_z + slot[1]
            if x < self.box_west - reach or x > self.box_east + reach:
                continue
            if z < self.box_north - reach or z > self.box_south + reach:
                continue
            if detail % 5 == 0:
                self._add_tree(mesh, x, z)
                continue
            wall, roof = self.BUILDING_COLORS[detail % 8]
            width = 9.0 + (detail >> 4) % 5
            depth = 9.0 + (detail >> 7) % 5
            height = 3.2 + ((detail >> 10) % 5) * 0.9
            building_type = (detail >> 12) % 3
            if building_type == 1:
                width = 7.0
                depth = 7.0
                height = 2.5
            elif building_type == 2:
                height = 10.0 + (detail >> 10) % 6
            distance = (x - center_x) ** 2 + (z - center_z) ** 2
            specs.append(
                (distance, x, z, width, depth, height, wall, roof, building_type)
            )

    def _blocked(self, x, z, is_car):
        """Return whether a position would hit a building or the world edge."""
        limit = self.WORLD_HALF - self.CAR_RADIUS
        if abs(x) > limit or abs(z) > limit:
            return True
        for building in self.buildings:
            if not is_car and building[4]:
                continue
            if abs(x - building[0]) < building[2] + self.CAR_RADIUS:
                if abs(z - building[1]) < building[3] + self.CAR_RADIUS:
                    return True
        return False

    def _car_blocked(self, x, z, skip_index):
        """Return whether a position hits another car or a person."""
        for index, car in enumerate(self.traffic):
            if index == skip_index:
                continue
            if not car.is_visible:
                continue
            dx = x - car.position.x
            if dx < 0:
                dx = -dx
            dz = z - car.position.y
            if dz < 0:
                dz = -dz
            if dx < 1.05 and dz < 1.85:
                return True
        if skip_index < self.TRAFFIC_COUNT:
            dx = x - self.player.position.x
            if dx < 0:
                dx = -dx
            dz = z - self.player.position.y
            if dz < 0:
                dz = -dz
            if dx < 1.05 and dz < 1.85:
                return True
        for index, person in enumerate(self.people):
            if not person.is_visible:
                continue
            pos = person.position
            dx = x - pos.x
            if dx < 0:
                dx = -dx
            dz = z - pos.y
            if dz < 0:
                dz = -dz
            if dx < 0.825 and dz < 1.675:
                return True
        return False

    def update_player(self, player, game):
        """Move the player on foot or in a car."""
        from picoware.system.buttons import BUTTON_CENTER

        if self.multiplayer_view is not None:
            return
        self._update_message()
        if game.input == BUTTON_CENTER:
            self._toggle_car(player)
        if self.in_car:
            self._drive_car(player, game)
        else:
            self._walk_player(player, game)
        self._update_city()

    def _walk_player(self, player, game):
        """Walk the player on foot."""
        from picoware.system.buttons import (
            BUTTON_DOWN,
            BUTTON_LEFT,
            BUTTON_RIGHT,
            BUTTON_UP,
        )

        button = game.input
        if button == BUTTON_UP:
            self.speed = self.WALK_SPEED
        elif button == BUTTON_DOWN:
            self.speed = -self.WALK_SPEED * 0.5
        else:
            self.speed = 0.0

        if button == BUTTON_LEFT:
            self.heading -= self.WALK_TURN
        elif button == BUTTON_RIGHT:
            self.heading += self.WALK_TURN

        dx = cos(self.heading)
        dz = sin(self.heading)
        old_x = player.position.x
        old_z = player.position.y
        next_x = old_x + dx * self.speed
        next_z = old_z + dz * self.speed
        if not self._blocked(next_x, next_z, False) and not self._car_blocked(
            next_x, next_z, self.TRAFFIC_COUNT
        ):
            player.position_set(next_x, next_z)
        else:
            if not self._blocked(next_x, old_z, False) and not self._car_blocked(
                next_x, old_z, self.TRAFFIC_COUNT
            ):
                player.position_set(next_x, old_z)
            elif not self._blocked(old_x, next_z, False) and not self._car_blocked(
                old_x, next_z, self.TRAFFIC_COUNT
            ):
                player.position_set(old_x, next_z)
            self.speed *= 0.25

        player.direction_set(dx, dz)
        player.set_3d_sprite_rotation(atan2(dz, dx) - pi * 0.5)
        self._update_camera_distance()

    def _drive_car(self, player, game):
        """Drive the player car with building collision."""
        from picoware.system.buttons import (
            BUTTON_DOWN,
            BUTTON_LEFT,
            BUTTON_RIGHT,
            BUTTON_UP,
        )

        button = game.input
        if button == BUTTON_UP:
            self.speed += self.CAR_ACCEL
        elif button == BUTTON_DOWN:
            self.speed -= self.CAR_BRAKE
        elif self.speed > 0:
            self.speed = max(0.0, self.speed - self.CAR_FRICTION)
        else:
            self.speed = min(0.0, self.speed + self.CAR_FRICTION)

        if button == BUTTON_LEFT:
            steering = -1.0
        elif button == BUTTON_RIGHT:
            steering = 1.0
        else:
            steering = 0.0

        if steering != 0.0:
            turn_scale = 0.70 + min(1.0, abs(self.speed) / self.CAR_MAX_SPEED) * 0.30
            if self.speed < 0:
                turn_scale = -turn_scale
            self.heading += steering * self.CAR_STEER * turn_scale

        self.speed = max(self.CAR_MAX_REVERSE, min(self.CAR_MAX_SPEED, self.speed))
        dx = cos(self.heading)
        dz = sin(self.heading)
        old_x = player.position.x
        old_z = player.position.y
        next_x = old_x + dx * self.speed
        next_z = old_z + dz * self.speed

        if not self._blocked(next_x, next_z, True) and not self._car_blocked(
            next_x, next_z, self.TRAFFIC_COUNT
        ):
            player.position_set(next_x, next_z)
        else:
            if not self._blocked(next_x, old_z, True) and not self._car_blocked(
                next_x, old_z, self.TRAFFIC_COUNT
            ):
                player.position_set(next_x, old_z)
            elif not self._blocked(old_x, next_z, True) and not self._car_blocked(
                old_x, next_z, self.TRAFFIC_COUNT
            ):
                player.position_set(old_x, next_z)
            self.speed *= 0.25

        player.direction_set(dx, dz)
        player.plane_set(-0.72, 0)
        player.set_3d_sprite_rotation(atan2(dz, dx) - pi * 0.5)
        self._sync_player_car(player)
        self._update_camera_distance()

    def _toggle_car(self, player):
        """Toggle the player between walking and driving."""
        if self.in_car:
            self.in_car = False
            self.speed = 0.0
            player.is_visible = True
            player.set_3d_sprite_rotation(
                atan2(sin(self.heading), cos(self.heading)) - pi * 0.5
            )
            self.player_car.is_visible = False
            self.message = "Walk mode"
            self.message_timer = 60
        else:
            self.in_car = True
            self.speed = 0.0
            player.is_visible = False
            self.player_car.is_visible = True
            self.message = "Drive mode"
            self.message_timer = 60

    def _sync_player_car(self, player):
        """Track the player car to the player position and heading."""
        dx = cos(self.heading)
        dz = sin(self.heading)
        self.player_car.position = player.position
        self.player_car.direction_set(dx, dz)
        self.player_car.plane_set(-0.72, 0)
        self.player_car.set_3d_sprite_rotation(atan2(dz, dx) - pi * 0.5)

    def _update_camera_distance(self):
        """Pull the camera closer when the player is inside a building."""
        if self.game is None:
            return
        px = self.player.position.x
        py = self.player.position.y
        inside = False
        for building in self.buildings:
            if abs(px - building[0]) < building[2]:
                if abs(py - building[1]) < building[3]:
                    inside = True
                    break
        if inside:
            self.game.camera.distance = self.CAMERA_INDOOR_DISTANCE
        else:
            self.game.camera.distance = self.CAMERA_DISTANCE

    def update_traffic(self, car):
        """Drive a traffic car along the street grid."""
        index = int(car.name[-1]) - 1
        speed = self.traffic_speed[index]
        axis = self.traffic_axis[index]
        direction = self.traffic_dir[index]

        if axis == 0:
            heading = pi * 0.5 if direction == 1 else -pi * 0.5
        else:
            heading = 0.0 if direction == 1 else pi

        dx = cos(heading)
        dz = sin(heading)
        old_x = car.position.x
        old_z = car.position.y
        next_x = old_x + dx * speed
        next_z = old_z + dz * speed

        if not self._blocked(next_x, next_z, True) and not self._car_blocked(
            next_x, next_z, index
        ):
            car.position_set(next_x, next_z)
        else:
            direction = -direction
            self.traffic_dir[index] = direction
            if axis == 0:
                heading = pi * 0.5 if direction == 1 else -pi * 0.5
            else:
                heading = 0.0 if direction == 1 else pi
            dx = cos(heading)
            dz = sin(heading)
            next_x = old_x + dx * speed
            next_z = old_z + dz * speed
            car.position_set(next_x, next_z)

        car.direction_set(dx, dz)
        car.plane_set(-0.72, 0)
        car.set_3d_sprite_rotation(atan2(dz, dx) - pi * 0.5)

        player = self.player.position
        offset_x = car.position.x - player.x
        offset_z = car.position.y - player.y
        if offset_x < 0.0:
            offset_x = -offset_x
        if offset_z < 0.0:
            offset_z = -offset_z
        edge = self.WORLD_HALF - 4.0
        if (
            offset_x > self.RECYCLE_DISTANCE
            or offset_z > self.RECYCLE_DISTANCE
            or car.position.x < -edge
            or car.position.x > edge
            or car.position.y < -edge
            or car.position.y > edge
        ):
            self._spawn_traffic(index)
        elif offset_x > self.FIELD_OF_VIEW + 8.0 or offset_z > self.FIELD_OF_VIEW + 8.0:
            car.is_visible = False
        else:
            car.is_visible = True

    def update_person(self, person):
        """Walk one pedestrian and recycle it when far away."""
        index = int(person.name[7:]) - 1
        position = person.position
        x = position.x + self.people_dir_x[index] * self.people_speeds[index]
        z = position.y + self.people_dir_z[index] * self.people_speeds[index]
        walk = self.people_walk[index] - self.people_speeds[index]
        if walk <= 0.0:
            self.people_dir_x[index] = -self.people_dir_x[index]
            self.people_dir_z[index] = -self.people_dir_z[index]
            walk = 12.0 + _next_random(17)
            person.set_3d_sprite_rotation(
                atan2(self.people_dir_z[index], self.people_dir_x[index]) - pi * 0.5
            )
        self.people_walk[index] = walk
        person.position_set(x, z)
        car = self.player.position
        offset_x = x - car.x
        offset_z = z - car.y
        if offset_x < 0.0:
            offset_x = -offset_x
        if offset_z < 0.0:
            offset_z = -offset_z
        edge = self.WORLD_HALF - 4.0
        if (
            offset_x > self.RECYCLE_DISTANCE
            or offset_z > self.RECYCLE_DISTANCE
            or x < -edge
            or x > edge
            or z < -edge
            or z > edge
        ):
            self._spawn_person(index)
            return
        if offset_x > self.FIELD_OF_VIEW + 8.0 or offset_z > self.FIELD_OF_VIEW + 8.0:
            person.is_visible = False
            return
        person.is_visible = not self._hidden_by_building(x, z)

    def _hidden_by_building(self, x, z):
        """Return whether a building blocks the view of a point."""
        car = self.player.position
        _cross_building = self._crosses_building
        for building in self.buildings:
            if _cross_building(car.x, car.y, x, z, building):
                return True
        return False

    def _crosses_building(self, x0, z0, x1, z1, building):
        """Return whether a segment crosses a building rectangle."""
        left = building[0] - building[2]
        right = building[0] + building[2]
        near = building[1] - building[3]
        far = building[1] + building[3]
        dx = x1 - x0
        dz = z1 - z0
        begin = 0.0
        end = 1.0
        if -0.0001 < dx < 0.0001:
            if x0 < left or x0 > right:
                return False
        else:
            inverse = 1.0 / dx
            enter = (left - x0) * inverse
            leave = (right - x0) * inverse
            if enter > leave:
                enter, leave = leave, enter
            begin = max(begin, enter)
            end = min(end, leave)
            if begin > end:
                return False
        if 0.0001 > dz > -0.0001:
            if z0 < near or z0 > far:
                return False
        else:
            inverse = 1.0 / dz
            enter = (near - z0) * inverse
            leave = (far - z0) * inverse
            if enter > leave:
                enter, leave = leave, enter
            begin = max(begin, enter)
            end = min(end, leave)
            if begin > end:
                return False
        return True

    def _update_message(self):
        """Count down the message timer."""
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""

    def draw_background(self, draw):
        """Draw the sky, horizon haze and distant ground."""
        width = draw.size.x
        height = draw.size.y
        horizon = int(height * 0.52)
        haze = draw.scale_y(18)
        draw._fill_rectangle(0, 0, width, horizon, self.COLOR_SKY)
        draw._fill_rectangle(0, horizon, width, haze, self.COLOR_HORIZON)
        draw._fill_rectangle(
            0, horizon + haze, width, height - horizon - haze, self.COLOR_GROUND
        )
        draw._fill_rectangle(
            0, horizon - draw.scale_y(2), width, draw.scale_y(2), self.COLOR_ROOF
        )

    def draw_hud(self, draw=None):
        """Draw the mode, speed and control hints."""
        if self.engine is None:
            return
        draw = self.draw if draw is None else draw
        width = draw.size.x
        bar_height = draw.scale_y(16)
        draw._fill_rectangle(0, 0, width, bar_height, self.COLOR_BLACK)

        if self.in_car:
            label = "DRIVE  %d MPH" % int(abs(self.speed) * 150)
        else:
            label = "WALK"
        draw._text(draw.scale_x(3), draw.scale_y(2), label, self.COLOR_LINE)

        if self.message_timer > 0:
            draw._text(
                width // 2 - draw.scale_x(len(self.message) * 3),
                draw.size.y // 2 - draw.scale_y(4),
                self.message,
                self.COLOR_LINE,
            )
        self._draw_minimap(draw)
        if self.multiplayer_connection_state == "active":
            hint = "ONLINE %d" % (len(self.multiplayer_remote_players) + 1)
        else:
            hint = "START: MENU"
        draw._text(draw.scale_x(3), draw.scale_y(19), hint, self.COLOR_LINE)

    def _draw_fullscreen_options(self, options, selection, first_y, line_height):
        draw = self.draw
        width = draw.size.x
        row_width = width * 3 // 4
        row_x = (width - row_width) // 2
        for index, option in enumerate(options):
            row_y = first_y + index * line_height
            if index == selection:
                draw._fill_rectangle(
                    row_x, row_y, row_width, line_height, self.COLOR_LINE
                )
                color = self.COLOR_BLACK
            else:
                color = self.COLOR_LINE
            text_x = max(
                row_x + draw.scale_x(2),
                width // 2 - draw.scale_x(len(option) * 3),
            )
            draw._text(text_x, row_y, option, color)

    def _draw_fullscreen_menu(self):
        """Draw the title, lobby, and status menus without the game scene."""
        draw = self.draw
        width = draw.size.x
        height = draw.size.y
        line_height = draw.font_size.y + 1
        footer_y = height - line_height - draw.scale_y(2)
        draw.fill_screen(self.COLOR_BLACK)

        if self.multiplayer_view == "title":
            title = "PICO CITY"
        elif self.multiplayer_view == "lobbies":
            title = "OPEN LOBBIES"
        elif self.multiplayer_view == "error":
            title = "MULTIPLAYER ERROR"
        else:
            title = "MULTIPLAYER"
        title_x = max(0, width // 2 - draw.scale_x(len(title) * 3))
        draw._text(title_x, draw.scale_y(6), title, self.COLOR_LINE)

        if self.multiplayer_view == "title":
            options = ("Play solo", "Multiplayer")
            first_y = height // 2 - line_height
            self._draw_fullscreen_options(
                options, self.multiplayer_selection, first_y, line_height
            )
            footer = "UP/DOWN OK  BACK"
        elif self.multiplayer_view == "menu":
            options = self._multiplayer_menu_options()
            if self.multiplayer_lobby_id:
                peers = "Online: %d peers" % len(self.multiplayer_remote_players)
                draw._text(
                    max(0, width // 2 - draw.scale_x(len(peers) * 3)),
                    height // 3,
                    peers,
                    self.COLOR_LINE,
                )
                first_y = height // 2
            else:
                first_y = height // 2 - (len(options) * line_height) // 2
            self._draw_fullscreen_options(
                options, self.multiplayer_selection, first_y, line_height
            )
            footer = "UP/DOWN OK  BACK"
        elif self.multiplayer_view == "lobbies":
            if self.multiplayer_lobbies:
                visible_count = 4
                start = max(
                    0,
                    min(
                        self.multiplayer_lobby_index - visible_count + 1,
                        len(self.multiplayer_lobbies) - visible_count,
                    ),
                )
                end = min(start + visible_count, len(self.multiplayer_lobbies))
                options = []
                for lobby in self.multiplayer_lobbies[start:end]:
                    options.append(
                        "%s %d/%d"
                        % (
                            lobby["lobby_id"][:8],
                            lobby["player_count"],
                            lobby["max_players"],
                        )
                    )
                self._draw_fullscreen_options(
                    options,
                    self.multiplayer_lobby_index - start,
                    height // 3,
                    line_height,
                )
            else:
                message = "No open lobbies"
                draw._text(
                    max(0, width // 2 - draw.scale_x(len(message) * 3)),
                    height // 2,
                    message,
                    self.COLOR_LINE,
                )
            footer = "UP/DOWN OK  BACK"
        elif self.multiplayer_view == "pending":
            message = self.multiplayer_status
            draw._text(
                max(0, width // 2 - draw.scale_x(len(message[:22]) * 3)),
                height // 2,
                message[:22],
                self.COLOR_LINE,
            )
            footer = ""
        else:
            message = self.multiplayer_status
            draw._text(
                max(0, width // 2 - draw.scale_x(len(message[:22]) * 3)),
                height // 2 - line_height,
                message[:22],
                self.COLOR_LINE,
            )
            if len(message) > 22:
                draw._text(
                    max(0, width // 2 - draw.scale_x(len(message[22:44]) * 3)),
                    height // 2,
                    message[22:44],
                    self.COLOR_LINE,
                )
            footer = "CENTER/BACK MENU"

        if footer:
            draw._text(draw.scale_x(2), footer_y, footer, self.COLOR_LINE)
        draw.swap()

    def _draw_minimap(self, draw):
        """Draw the local street and building overview."""
        width = draw.size.x
        size = draw.scale_y(self.MINIMAP_SIZE)
        left = width - size - draw.scale_x(3)
        top = draw.scale_y(19)
        car = self.player.position
        step = size / (self.MINIMAP_RANGE * 2.0)
        middle_x = left + size * 0.5
        middle_z = top + size * 0.5
        thickness = max(1, draw.scale_y(2))
        _fill_rectangle = draw._fill_rectangle
        _fill_rectangle(left, top, size, size, self.COLOR_BLACK)
        first = int((car.x - self.MINIMAP_RANGE) // self.ROAD_SPACING)
        last = int((car.x + self.MINIMAP_RANGE) // self.ROAD_SPACING)
        for index in range(first, last + 1):
            line = index * self.ROAD_SPACING
            if line < -self.WORLD_HALF or line > self.WORLD_HALF:
                continue
            offset = middle_x + (line - car.x) * step - thickness // 2
            _fill_rectangle(offset, top, thickness, size, self.COLOR_HORIZON)
        first = int((car.y - self.MINIMAP_RANGE) // self.ROAD_SPACING)
        last = int((car.y + self.MINIMAP_RANGE) // self.ROAD_SPACING)
        for index in range(first, last + 1):
            line = index * self.ROAD_SPACING
            if line < -self.WORLD_HALF or line > self.WORLD_HALF:
                continue
            offset = middle_z + (line - car.y) * step - thickness // 2
            _fill_rectangle(left, offset, size, thickness, self.COLOR_HORIZON)
        for building in self.buildings:
            start_x = middle_x + (building[0] - car.x) * step - building[2] * step
            end_x = start_x + building[2] * step * 2.0
            start_z = middle_z + (building[1] - car.y) * step - building[3] * step
            end_z = start_z + building[3] * step * 2.0
            start_x = max(start_x, left)
            start_z = max(start_z, top)
            end_x = min(end_x, left + size)
            end_z = min(end_z, top + size)
            if end_x - start_x < 1.0 or end_z - start_z < 1.0:
                continue
            _fill_rectangle(
                start_x,
                start_z,
                end_x - start_x,
                end_z - start_z,
                self.COLOR_SIDEWALK,
            )
        draw._rectangle(left, top, size, size, self.COLOR_HORIZON)
        dot = max(draw.scale_y(3), 2)
        tip = dot + draw.scale_y(3)
        _fill_rectangle(
            middle_x + cos(self.heading) * tip - 1,
            middle_z + sin(self.heading) * tip - 1,
            2,
            2,
            self.COLOR_LINE,
        )
        _fill_rectangle(
            middle_x - dot // 2,
            middle_z - dot // 2,
            dot,
            dot,
            self.COLOR_PLAYER,
        )
        remote_dot = max(draw.scale_y(2), 2)
        for remote in self.multiplayer_remote_players.values():
            remote_position = remote["player"].position
            remote_x = middle_x + (remote_position.x - car.x) * step
            remote_z = middle_z + (remote_position.y - car.y) * step
            if left <= remote_x < left + size and top <= remote_z < top + size:
                _fill_rectangle(
                    remote_x - remote_dot // 2,
                    remote_z - remote_dot // 2,
                    remote_dot,
                    remote_dot,
                    remote["color"],
                )
        draw._text(
            left,
            top + size + draw.scale_y(2),
            "%d,%d"
            % (
                int(car.x // self.ROAD_SPACING),
                int(car.y // self.ROAD_SPACING),
            ),
            self.COLOR_LINE,
        )

    def run(self, skip_engine=False):
        """Poll multiplayer activity, draw menus or run one game frame."""
        self.multiplayer_frame += 1
        self._poll_multiplayer_http()
        self._poll_multiplayer_websocket()
        self._process_multiplayer_inbox()
        if self.multiplayer_exit_ready:
            self.multiplayer_exit_ready = False
            self.view_manager.back()
            return
        if self.multiplayer_view is not None:
            self._draw_fullscreen_menu()
            return
        if self.engine is None:
            self.multiplayer_view = "title"
            self.multiplayer_selection = 0
            self._draw_fullscreen_menu()
            return
        if skip_engine:
            return
        self._update_city()
        self.engine.run_async(False)
        self._send_multiplayer_state()

    def stop(self):
        """Stop the engine and release the city resources."""
        if self.multiplayer_ws is not None:
            if self.multiplayer_lobby_id and self.multiplayer_ws.is_connected:
                leave_message = _pack_multiplayer_message(
                    self.multiplayer_player_id_bytes, b"leave"
                )
                if not self.multiplayer_ws.send(leave_message):
                    self.view_manager.log(
                        "[PicoCity multiplayer] Could not relay leave message",
                        2,
                    )
            self.multiplayer_connection_state = "idle"
            self.multiplayer_ws.close()
            self.multiplayer_ws = None
        if self.multiplayer_http is not None:
            self.multiplayer_http.close()
            self.multiplayer_http = None
        self._remove_all_remote_players()
        if self.engine is not None:
            self.engine.stop()
            self.engine = None
        self.game = None
        self.meshes = []
        self.city_mesh = None
        self.buildings = []
        self.people = []
        self.people_dir_x = []
        self.people_dir_z = []
        self.people_walk = []
        self.people_speeds = []
        self.traffic = []
        self.traffic_speed = []
        self.traffic_axis = []
        self.traffic_line = []
        self.traffic_dir = []
        self.player = None


def start(view_manager) -> bool:
    """Start the Pico City view."""
    global _city

    _city = _City(view_manager)
    return _city is not None


def run(view_manager) -> None:
    """Run one Pico City frame."""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_NONE

    button = view_manager.button
    if _city is None:
        view_manager.back()
        return

    if _city.handle_multiplayer_input(button):
        if button != BUTTON_NONE:
            view_manager.input_manager.reset()
        _city.run(skip_engine=True)
        return
    if button == BUTTON_BACK:
        if _city.multiplayer_lobby_id:
            _city._leave_multiplayer(True)
            view_manager.input_manager.reset()
            _city.run(skip_engine=True)
        else:
            view_manager.back()
        return

    _city.run()


def stop(_view_manager) -> None:
    """Stop Pico City and release engine resources."""
    from gc import collect

    global _city

    if _city is not None:
        _city.stop()
        del _city
        _city = None
    collect()
