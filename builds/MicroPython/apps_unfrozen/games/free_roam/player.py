from micropython import const
from picoware.system.vector import Vector
from picoware.engine.entity import (
    Entity,
    ENTITY_TYPE_PLAYER,
    SPRITE_3D_HUMANOID,
    SPRITE_3D_NONE,
    ENTITY_TYPE_3D_SPRITE,
    SPRITE_3D_CUSTOM,
)
from picoware.gui.loading import Loading
from math import sqrt, atan2, pi, cos, sin
from ujson import loads as json_loads

# GameMainView
GAME_VIEW_TITLE = const(0)  # title, start, and menu (menu)
GAME_VIEW_SYSTEM_MENU = const(1)  # profile, settings, about (menu)
GAME_VIEW_LOBBY_MENU = const(2)  # local or online (menu)
GAME_VIEW_GAME_LOCAL = const(3)  # game view local (gameplay)
GAME_VIEW_GAME_ONLINE = const(4)  # game view online (gameplay)
GAME_VIEW_WELCOME = const(5)  # welcome view
GAME_VIEW_LOGIN = const(6)  # login view
GAME_VIEW_REGISTRATION = const(7)  # registration view
GAME_VIEW_USER_INFO = const(8)  # user info view
GAME_VIEW_LOBBY_BROWSER = const(9)  # browse/join online games

# LoginStatus
LOGIN_CREDENTIALS_MISSING = const(-1)  # Credentials missing
LOGIN_SUCCESS = const(0)  # Login successful
LOGIN_USER_NOT_FOUND = const(1)  # User not found
LOGIN_WRONG_PASSWORD = const(2)  # Wrong password
LOGIN_WAITING = const(3)  # Waiting for response
LOGIN_NOT_STARTED = const(4)  # Login not started
LOGIN_REQUEST_ERROR = const(5)  # Request error

# RegistrationStatus
REGISTRATION_CREDENTIALS_MISSING = const(-1)  # Credentials missing
REGISTRATION_SUCCESS = const(0)  # Registration successful
REGISTRATION_USER_EXISTS = const(1)  # User already exists
REGISTRATION_REQUEST_ERROR = const(2)  # Request error
REGISTRATION_NOT_STARTED = const(3)  # Registration not started
REGISTRATION_WAITING = const(4)  # Waiting for response

# UserInfoStatus
USER_INFO_CREDENTIALS_MISSING = const(-1)  # Credentials missing
USER_INFO_SUCCESS = const(0)  # User info retrieved successfully
USER_INFO_REQUEST_ERROR = const(1)  # Request error
USER_INFO_NOT_STARTED = const(2)  # User info request not started
USER_INFO_WAITING = const(3)  # Waiting for response
USER_INFO_PARSE_ERROR = const(4)  # Error parsing user info

# RequestType
REQUEST_TYPE_LOGIN = const(0)  # Login request
REQUEST_TYPE_REGISTRATION = const(1)  # Registration request
REQUEST_TYPE_USER_INFO = const(2)  # User info request
REQUEST_TYPE_GAME_CREATE = const(3)  # Request to create a game
REQUEST_TYPE_GAME_LIST = const(4)  # Request list of active games


# TitleIndex constants
TITLE_INDEX_START = const(0)  # switch to lobby options (local or online)
TITLE_INDEX_MENU = const(1)  # switch to system menu

# MenuIndex constants
MENU_INDEX_PROFILE = const(0)  # profile
MENU_INDEX_MAP = const(1)  # map
MENU_INDEX_SETTINGS = const(2)  # settings
MENU_INDEX_ABOUT = const(3)  # about

# MenuSettingsIndex constants
MENU_SETTINGS_MAIN = const(0)  # hovering over `Settings` in system menu
MENU_SETTINGS_SOUND = const(1)  # sound settings
MENU_SETTINGS_VIBRATION = const(2)  # vibration settings
MENU_SETTINGS_SHOW_PLAYER = const(3)  # show/hide local player
MENU_SETTINGS_LEAVE = const(4)  # leave game

# LobbyMenuIndex constants
LOBBY_MENU_INDEX_LOCAL = const(0)  # local game
LOBBY_MENU_INDEX_ONLINE = const(1)  # online game

# ToggleState constants
TOGGLE_STATE_OFF = const(0)  # toggle is off
TOGGLE_STATE_ON = const(1)  # toggle is on

# GameState constants
GAME_STATE_PLAYING = const(0)  # Game is currently playing
GAME_STATE_MENU = const(1)  # Game is in menu state
GAME_STATE_SWITCHING_LEVELS = const(2)  # Game is switching levels
GAME_STATE_LEAVING_GAME = const(3)  # Game is leaving

# OnlineGameState constants
ONLINE_STATE_IDLE = const(0)  # Not started — ready to create/join a session
ONLINE_STATE_FETCHING_SESSION = const(
    1
)  # HTTP request to create a game session in progress
ONLINE_STATE_CONNECTING = const(2)  # WebSocket connecting to the game server
ONLINE_STATE_PLAYING = const(3)  # Active online game
ONLINE_STATE_JOINING_EXISTING = const(4)  # Joining an existing lobby (skip create)
ONLINE_STATE_ERROR = const(5)  # Connection or request error

INPUT_KEY_UP = const(0)
INPUT_KEY_DOWN = const(1)
INPUT_KEY_RIGHT = const(2)
INPUT_KEY_LEFT = const(3)
INPUT_KEY_OK = const(4)
INPUT_KEY_BACK = const(5)
INPUT_KEY_MAX = const(-1)

COLOR_WHITE = const(0x0000)  # inverted on purpose
COLOR_BLACK = const(0xFFFF)  # inverted on purpose

CAMERA_THIRD_PERSON = const(1)  # Render from external camera position

MAX_LOBBY_ENTRIES = const(8)


def toggle_to_string(state: int) -> str:
    """Convert a toggle state to a string value"""
    return "On" if state == TOGGLE_STATE_ON else "Off"


class LobbyEntry:
    """Class representing a lobby entry."""

    __slots__ = ("game_id", "game_name")

    def __init__(self, game_id: str = "", game_name: str = ""):
        self.game_id = game_id
        self.game_name = game_name


# current bug -> adding self.render to super.init() causes freezing when the engine tries to run it!
class Player(Entity):
    """Player entity for the free roam game."""

    def __init__(self, name: str = "Player"):
        super().__init__(
            name,
            ENTITY_TYPE_PLAYER,
            Vector(10, 10),  # position
            Vector(1.0, 1.5),  # size
            None,  # Image
            None,  # Image left
            None,  # Image right
            None,  # start
            None,  # stop
            self.update,  # update
            self.render,  # render
            None,  # collision
            True,  # is_8bit
            SPRITE_3D_HUMANOID,
            0x915C,  # 3d color
        )
        # facing east initially (better for 3rd person view)
        self.set_direction = Vector(1, 0)
        self.set_plane = Vector(0, 0.66)  # camera plane perpendicular to direction
        # Mark this entity as a player (so level doesn't delete it)
        self.is_player = True
        self.set_end_position = Vector(10, 10)  # Initialize end position
        self.set_start_position = Vector(10, 10)  # Initialize start position
        self.player_name = name  # Copy default player name
        self.name = self.player_name  # Point Entity's name to our writable buffer

        # non-Entity attributes
        self.current_dynamic_map = None  # current dynamic map

        # current lobby menu index (must be in the GameViewLobbyMenu)
        self.current_lobby_menu_index: int = LOBBY_MENU_INDEX_LOCAL

        # current menu index (must be in the GameViewSystemMenu)
        self.current_menu_index: int = MENU_INDEX_PROFILE
        self.current_main_view: int = GAME_VIEW_WELCOME  # current main view of the game

        # current settings index (must be in the GameViewSystemMenu in the Settings tab)
        self.current_settings_index: int = MENU_SETTINGS_MAIN

        # current title index (must be in the GameViewTitle)
        self.current_title_index: int = TITLE_INDEX_START
        self.free_roam_game = None  # Reference to the main game instance
        self.game_state: int = GAME_STATE_PLAYING  # current game state

        # Track if player has been positioned to prevent repeated resets
        self.has_been_positioned: bool = False
        self.just_started: bool = True  # whether the player just started the game

        # whether the player just switched levels
        self.just_switched_levels: bool = False
        self.last_input: int = -1  # Last input key
        self.leave_game: int = TOGGLE_STATE_OFF  # leave game toggle state
        self.level_switch_counter: int = 0  # counter for level switch delay
        self.http = None  # HTTP instance for network requests
        self.loading = None  # loading animation instance
        self.login_status: int = LOGIN_NOT_STARTED  # Current login status
        self.rain_frame: int = 0  # frame counter for rain effect

        # Current registration status
        self.registration_status: int = REGISTRATION_NOT_STARTED
        self.sound_toggle: int = TOGGLE_STATE_ON  # sound toggle state

        # Current user info status
        self.user_info_status: int = USER_INFO_NOT_STARTED
        self.vibration_toggle: int = TOGGLE_STATE_ON  # vibration toggle state
        self.show_player_toggle: int = TOGGLE_STATE_ON  # show/hide local player toggle
        self.welcome_frame: int = 0  # frame counter for welcome animation

        self.loaded_username: str = ""  # loaded username from storage
        self.loaded_password: str = ""  # loaded password from storage

        # online stuff
        self.online_game_state: int = ONLINE_STATE_IDLE  # online game connection state
        self.online_game_id: str = ""  # UUID of the active game session
        self.online_port: int = 0  # WebSocket port assigned by the server
        self.lobby_entries: list[LobbyEntry] = [
            LobbyEntry() for _ in range(MAX_LOBBY_ENTRIES)
        ]
        self.lobby_count: int = 0
        self.lobby_selected_index: int = 0
        self.lobby_fetched: bool = False

        self.remote_player_name_pool: set[str] = (
            set()
        )  # stable name storage for dynamically spawned remote player entities

        self.ws = None  # WebSocketAsync instance for online games
        self.last_ws_response: str = ""  # Last WebSocket message received
        self._last_game_state: int = GAME_STATE_PLAYING  # previous render game state

    def __del__(self):
        if self.current_dynamic_map:
            del self.current_dynamic_map
            self.current_dynamic_map = None
        if self.loading:
            del self.loading
            self.loading = None
        if self.http:
            del self.http
            self.http = None
        if self.ws:
            self.ws.close()
            del self.ws
            self.ws = None
        self.player_name = None
        self.loaded_password = None
        self.loaded_username = None

    @property
    def should_leave_game(self) -> bool:
        """Check if the player has chosen to leave the game."""
        return self.leave_game == TOGGLE_STATE_ON

    @property
    def password(self) -> str:
        """Get password from storage."""
        if self.loaded_password:
            return self.loaded_password
        if not self.free_roam_game or not self.free_roam_game.view_manager:
            return ""
        view_manager = self.free_roam_game.view_manager
        data: str = view_manager.storage.read("picoware/flip_social/password.json")

        if data is not None:
            try:

                obj: dict = json_loads(data)
                if "password" in obj:
                    self.loaded_password = obj["password"]
                    return self.loaded_password
            except Exception:
                pass

        return ""

    @property
    def username(self) -> str:
        """Get username from storage."""
        if self.loaded_username:
            return self.loaded_username
        if not self.free_roam_game or not self.free_roam_game.view_manager:
            return ""
        view_manager = self.free_roam_game.view_manager
        data: str = view_manager.storage.read("picoware/flip_social/username.json")

        if data is not None:
            try:

                obj: dict = json_loads(data)
                if "username" in obj:
                    self.loaded_username = obj["username"]
                    return self.loaded_username
            except Exception:
                pass

        return ""

    def collision_map_check(self, new_position: Vector) -> bool:
        """Check if the new position collides with any walls in the map."""
        if self.current_dynamic_map is None:
            return False

        # Check multiple points around the player to prevent clipping through walls
        offset = 0.2  # Small offset to check around player position

        check_points = [
            new_position,
            Vector(new_position.x - offset, new_position.y - offset),
            Vector(new_position.x + offset, new_position.y - offset),
            Vector(new_position.x - offset, new_position.y + offset),
            Vector(new_position.x + offset, new_position.y + offset),
        ]

        for point in check_points:
            map_x = int(point.x)
            map_y = int(point.y)

            # Check bounds
            if (
                map_x < 0
                or map_y < 0
                or map_x >= self.current_dynamic_map.width
                or map_y >= self.current_dynamic_map.height
            ):
                return True  # Collision with map boundary

            # Check tile type (assuming TILE_WALL = 1)
            if self.current_dynamic_map.get_tile(map_x, map_y) == 1:  # TILE_WALL
                return True  # Collision detected

        return False  # No collision detected

    def draw_current_view(self, canvas):
        """Draw the current view based on current_main_view."""
        if self.current_main_view == GAME_VIEW_TITLE:
            self.draw_title_view(canvas)
        elif self.current_main_view == GAME_VIEW_SYSTEM_MENU:
            self.draw_system_menu_view(canvas)
        elif self.current_main_view == GAME_VIEW_LOBBY_MENU:
            self.draw_lobby_menu_view(canvas)
        elif self.current_main_view == GAME_VIEW_GAME_LOCAL:
            self.draw_game_local_view(canvas)
        elif self.current_main_view == GAME_VIEW_GAME_ONLINE:
            self.draw_game_online_view(canvas)
        elif self.current_main_view == GAME_VIEW_WELCOME:
            self.draw_welcome_view(canvas)
        elif self.current_main_view == GAME_VIEW_LOGIN:
            self.draw_login_view(canvas)
        elif self.current_main_view == GAME_VIEW_REGISTRATION:
            self.draw_registration_view(canvas)
        elif self.current_main_view == GAME_VIEW_USER_INFO:
            self.draw_user_info_view(canvas)
        elif self.current_main_view == GAME_VIEW_LOBBY_BROWSER:
            self.draw_lobby_browser_view(canvas)
        else:
            canvas.fill_screen(COLOR_WHITE)
            canvas._text(0, 10, "Unknown View", COLOR_BLACK)
        canvas.swap()

    def draw_game_local_view(self, canvas):
        """Draw the local game view."""
        canvas.fill_screen(COLOR_BLACK)
        if self.free_roam_game.is_running:
            if self.free_roam_game.engine:
                if self.should_leave_game:
                    self.free_roam_game.end_game()
                    return
                self.free_roam_game.reset_input()
                self.free_roam_game.engine.run_async(False)
            return

        canvas._text(25, 32, "Starting Game...", COLOR_WHITE)
        game_started = self.free_roam_game.start_game()
        if game_started and self.free_roam_game.engine:
            self.free_roam_game.engine.run_async(False)

    def draw_game_online_view(self, canvas):
        """Draw the online game view."""
        canvas.fill_screen(COLOR_BLACK)
        view_manager = self.free_roam_game.view_manager

        if self.should_leave_game:
            if self.ws:
                self.ws.close()
                del self.ws
                self.ws = None
            self.online_game_state = ONLINE_STATE_IDLE
            self.free_roam_game.end_game()
            return

        if self.online_game_state == ONLINE_STATE_IDLE:
            canvas.fill_screen(COLOR_WHITE)
            canvas._text(0, 10, "Connecting to server...", COLOR_BLACK)
            self.user_request(REQUEST_TYPE_GAME_CREATE)

        elif self.online_game_state == ONLINE_STATE_FETCHING_SESSION:
            canvas.fill_screen(COLOR_WHITE)
            if self.loading is None:
                self.loading = Loading(
                    self.free_roam_game.draw, COLOR_BLACK, COLOR_WHITE
                )
                self.loading.text = "Creating game..."
                self.loading.animate(swap=False)

            if not self.http or not self.http.is_request_complete():
                if self.loading:
                    self.loading.animate(swap=False)
            else:
                if self.loading:
                    del self.loading
                    self.loading = None

                _response = self.http.response if self.http else None
                if _response is None:
                    self.online_game_state = ONLINE_STATE_ERROR
                else:
                    try:
                        data = json_loads(_response.text)
                        port = data.get("port", 0)
                        game_id = data.get("game_id", "")
                        if port and game_id:
                            self.online_port = int(port)
                            self.online_game_id = str(game_id)
                            ws_url = f"ws://www.jblanked.com/ws/game-server/{self.online_game_id}/"

                            def _ws_callback(data):
                                if data is not None and data != "":
                                    self.last_ws_response = str(data)
                                elif data is None:
                                    self.last_ws_response = "[SOCKET/STOPPED]"

                            from picoware.system.websocket import WebSocketAsync

                            if self.ws:
                                self.ws.close()
                                del self.ws
                                self.ws = None
                            self.ws = WebSocketAsync(
                                uri=ws_url,
                                callback=_ws_callback,
                                thread_manager=view_manager.thread_manager,
                                headers={
                                    "Content-Type": "application/json",
                                    "HTTP_USER_AGENT": "Pico",
                                    "Setting": "X-Flipper-Redirect",
                                    "username": self.username,
                                    "password": self.password,
                                    "User-Agent": "Raspberry Pi Pico W",
                                },
                            )
                            if self.ws.connect():
                                self.online_game_state = ONLINE_STATE_CONNECTING
                            else:
                                self.online_game_state = ONLINE_STATE_ERROR
                        else:
                            view_manager.log(
                                "[ONLINE] Missing 'port' or 'game_id' in response", 2
                            )
                            self.online_game_state = ONLINE_STATE_ERROR
                    except Exception as e:
                        view_manager.log(
                            f"[ONLINE] Failed to parse game session response: {e}", 2
                        )
                        self.online_game_state = ONLINE_STATE_ERROR

                if self.http:
                    del self.http
                    self.http = None

        elif self.online_game_state == ONLINE_STATE_CONNECTING:
            canvas.fill_screen(COLOR_WHITE)
            if self.ws and self.ws.is_connected:
                self.online_game_state = ONLINE_STATE_PLAYING
                if not self.free_roam_game.is_running:
                    self.free_roam_game.start_game_online()
                if self.free_roam_game.engine and self.free_roam_game.engine.game:
                    self.free_roam_game.engine.game.level_switch("Online")
            else:
                canvas._text(0, 10, "Connecting...", COLOR_BLACK)

        elif self.online_game_state == ONLINE_STATE_PLAYING:
            if not self.free_roam_game.is_running:
                canvas.fill_screen(COLOR_WHITE)
                canvas._text(25, 32, "Starting Game...", COLOR_BLACK)
                self.free_roam_game.start_game_online()
                if self.free_roam_game.engine and self.free_roam_game.engine.game:
                    self.free_roam_game.engine.game.level_switch("Online")
                return

            # Send current button input to server as an integer string.
            # Only forward movement/rotation inputs (Up/Down/Left/Right); OK and other
            # non-movement keys must not be sent to the server.
            current_input = self.free_roam_game.last_input
            if current_input != INPUT_KEY_MAX:
                if current_input != INPUT_KEY_BACK:
                    if self.game_state == GAME_STATE_PLAYING:
                        input_msg = f'{{"username": "{self.player_name}", "input": {current_input}}}'
                        if self.ws:
                            self.ws.send(input_msg)
                        else:
                            # ws closed so leave the game and/or go to error
                            self.online_game_state = ONLINE_STATE_ERROR
                        # Prevent local engine from also moving the player —
                        # server position update is the authoritative source.
                        if self.free_roam_game.engine:
                            self.free_roam_game.engine.update_game_input(INPUT_KEY_MAX)
                    else:  # menu
                        if self.free_roam_game.engine:
                            self.free_roam_game.engine.update_game_input(current_input)
                else:
                    if self.free_roam_game.engine:
                        self.free_roam_game.engine.update_game_input(INPUT_KEY_BACK)
                self.free_roam_game.reset_input()

            # Apply server-authoritative entity positions from the latest WebSocket
            # message, then let the local engine render the updated state.
            last_resp = self.last_ws_response
            if last_resp and last_resp != "":
                if last_resp == "[SOCKET/STOPPED]":
                    view_manager.log("[ONLINE] WebSocket stopped unexpectedly", 2)
                    self.online_game_state = ONLINE_STATE_ERROR
                else:
                    self.update_entities_from_server(last_resp)
                    self.last_ws_response = ""

            if self.free_roam_game.engine:
                self.free_roam_game.engine.run_async(False)

                if self.game_state != GAME_STATE_MENU:
                    # Name tag overlay — project each humanoid entity's world position
                    # to screen space and draw a small username label above it.
                    og = self.free_roam_game.engine.game
                    if og and og.current_level:
                        cam = og.camera
                        ss = og.draw.size
                        vh = cam.height

                        _dx = self.direction.x
                        _dy = self.direction.y
                        _dl = (_dx * _dx + _dy * _dy) ** 0.5
                        if _dl < 0.001:
                            _dl = 1.0
                        _ndx = _dx / _dl
                        _ndy = _dy / _dl
                        _cpx = self.position.x - _ndx * cam.distance
                        _cpy = self.position.y - _ndy * cam.distance

                        entity_count = og.current_level.entity_count
                        for i in range(entity_count):
                            ent = og.current_level.get_entity(i)
                            if not ent or not ent.is_active or not ent.name:
                                continue
                            if ent.sprite_3d_type != SPRITE_3D_HUMANOID:
                                continue
                            # Skip local player when show-player is off
                            if (
                                ent is self
                                and self.show_player_toggle == TOGGLE_STATE_OFF
                            ):
                                continue

                            wdx = ent.position.x - _cpx
                            wdz = ent.position.y - _cpy
                            wdy = (ent.size.y + 0.2) - vh

                            cx = wdx * (-_ndy) + wdz * _ndx
                            cz = wdx * _ndx + wdz * _ndy
                            if cz <= 0.1:
                                continue  # behind camera

                            sx = (cx / cz) * ss.y + ss.x * 0.5
                            sy = (-wdy / cz) * ss.y + ss.y * 0.5

                            tw = og.draw.len(ent.name)
                            tx = int(sx) - tw // 2
                            ty = int(sy)

                            # Clamp to screen bounds
                            if tx + tw < 0 or tx >= ss.x or ty < 0 or ty >= ss.y:
                                continue
                            tx = max(0, min(tx, ss.x - tw))
                            ty = max(0, min(ty, ss.y - 8))
                            og.draw._text(tx, ty, ent.name, 0x9A60)

        elif self.online_game_state == ONLINE_STATE_ERROR:
            canvas.fill_screen(COLOR_WHITE)
            canvas._text(0, 10, "Connection failed!", COLOR_BLACK)
            canvas._text(0, 20, "Check network and", COLOR_BLACK)
            canvas._text(0, 30, "try again.", COLOR_BLACK)
            canvas._text(0, 50, "Press BACK to return.", COLOR_BLACK)

        elif self.online_game_state == ONLINE_STATE_JOINING_EXISTING:
            canvas.fill_screen(COLOR_WHITE)
            canvas._text(0, 10, "Joining game...", COLOR_BLACK)

            ws_url = f"ws://www.jblanked.com/ws/game-server/{self.online_game_id}/"

            def _ws_callback(data):
                if data is not None and data != "":
                    self.last_ws_response = str(data)
                elif data is None:
                    self.last_ws_response = "[SOCKET/STOPPED]"

            from picoware.system.websocket import WebSocketAsync

            if self.ws:
                self.ws.close()
                del self.ws
                self.ws = None
            self.ws = WebSocketAsync(
                uri=ws_url,
                callback=_ws_callback,
                thread_manager=view_manager.thread_manager,
                headers={
                    "Content-Type": "application/json",
                    "HTTP_USER_AGENT": "Pico",
                    "Setting": "X-Flipper-Redirect",
                    "username": self.username,
                    "password": self.password,
                    "User-Agent": "Raspberry Pi Pico W",
                },
            )
            if self.ws.connect():
                self.online_game_state = ONLINE_STATE_CONNECTING
            else:
                self.online_game_state = ONLINE_STATE_ERROR

        else:
            view_manager.log(
                f"[ONLINE] Unknown online game state: {self.online_game_state}", 2
            )

    def draw_lobby_browser_view(self, canvas):
        """Draw the lobby browser view — fetch and display active online sessions."""
        width = canvas.size.x
        height = canvas.size.y

        if not self.lobby_fetched:
            canvas.fill_screen(COLOR_WHITE)

            if self.http is None:
                # Start the request and show loading animation
                self.user_request(REQUEST_TYPE_GAME_LIST)
                if self.http is not None:
                    if self.loading:
                        del self.loading
                        self.loading = None
                    self.loading = Loading(
                        self.free_roam_game.draw, COLOR_BLACK, COLOR_WHITE
                    )
                    self.loading.text = "Fetching lobbies..."
                    self.loading.animate(swap=False)
                return

            if not self.http.is_request_complete():
                if self.loading:
                    self.loading.animate(swap=False)
                return

            # Request complete — stop animation
            if self.loading:
                del self.loading
                self.loading = None

            # Parse the list of active game sessions
            self.lobby_count = 0
            _response = self.http.response
            if _response is not None:
                try:
                    data = json_loads(_response.text)
                    games = data.get("games", [])
                    for i in range(min(MAX_LOBBY_ENTRIES, len(games))):
                        entry = games[i]
                        gid = entry.get("game_id", "")
                        gname = entry.get("game_name", "")
                        if gid and gname:
                            self.lobby_entries[self.lobby_count].game_id = str(gid)
                            self.lobby_entries[self.lobby_count].game_name = str(gname)
                            self.lobby_count += 1
                except Exception:
                    pass

            del self.http
            self.http = None
            self.lobby_fetched = True
            self.lobby_selected_index = 0
            return

        # ── Draw the lobby list ──────────────────────────────────────
        canvas.fill_screen(COLOR_WHITE)
        self.draw_rain_effect(canvas)

        canvas.text(
            Vector(width * 20 // 128, height * 10 // 64), "Online Lobbies", COLOR_BLACK
        )

        total_items = 1 + self.lobby_count  # index 0 = "New Game"
        start_y = height * 18 // 64
        line_h = max(height * 10 // 64, 1)
        max_visible = 4

        scroll_offset = 0
        if self.lobby_selected_index >= max_visible:
            scroll_offset = self.lobby_selected_index - max_visible + 1

        for i in range(scroll_offset, total_items):
            if (i - scroll_offset) >= max_visible:
                break
            y = start_y + (i - scroll_offset) * line_h

            if i == self.lobby_selected_index:
                canvas._fill_rectangle(0, y, width, line_h, COLOR_BLACK)
                text_color = COLOR_WHITE
            else:
                text_color = COLOR_BLACK

            label = "> New Game" if i == 0 else self.lobby_entries[i - 1].game_name
            canvas._text(width * 4 // 128, y + height * 8 // 64, label, text_color)

        # Scroll indicators
        if scroll_offset > 0:
            canvas._text(width * 120 // 128, height * 20 // 64, "^", COLOR_BLACK)
        if scroll_offset + max_visible < total_items:
            canvas._text(width * 120 // 128, height * 55 // 64, "v", COLOR_BLACK)

        canvas._text(
            width * 4 // 128,
            height * 62 // 64,
            "OK:Select  BACK:Return",
            COLOR_BLACK,
        )

    def draw_lobby_menu_view(self, canvas):
        """Draw the lobby menu."""
        self.draw_menu_type1(canvas, self.current_lobby_menu_index, "Local", "Online")

    def draw_login_view(self, canvas):
        """Draw the login view."""
        canvas.fill_screen(COLOR_WHITE)
        if self.login_status == LOGIN_NOT_STARTED:
            self.user_request(REQUEST_TYPE_LOGIN)

            # Only proceed if the request was initiated successfully
            if self.http is not None:

                if self.loading:
                    del self.loading
                    self.loading = None
                self.loading = Loading(
                    self.free_roam_game.draw, COLOR_BLACK, COLOR_WHITE
                )
                self.loading.text = "Logging in..."
                self.loading.animate(swap=False)

                self.login_status = LOGIN_WAITING
            # else: user_request already set the error status
        elif self.login_status == LOGIN_WAITING:
            if self.http is None:
                self.login_status = LOGIN_REQUEST_ERROR
                return
            if not self.http.is_request_complete():
                self.loading.animate(swap=False)
                return
            # Request is complete, process the response
            _response = self.http.response
            if _response is None:
                self.login_status = LOGIN_REQUEST_ERROR
                return
            response = _response.text
            if "[SUCCESS]" in response:
                self.login_status = LOGIN_SUCCESS
                self.current_main_view = GAME_VIEW_TITLE  # bring to the next view
            else:
                # Parse error response if needed
                self.login_status = LOGIN_REQUEST_ERROR
            # refresh for next requests
            if self.http:
                del self.http
                self.http = None
            if self.loading:
                del self.loading
                self.loading = None
        elif self.login_status == LOGIN_SUCCESS:
            canvas._text(0, 10, "Login successful!", COLOR_BLACK)
            canvas._text(0, 20, "Press OK to continue.", COLOR_BLACK)
        elif self.login_status == LOGIN_CREDENTIALS_MISSING:
            canvas._text(0, 10, "Missing credentials!", COLOR_BLACK)
            canvas._text(0, 20, "Please set your username", COLOR_BLACK)
            canvas._text(0, 30, "and password in the app.", COLOR_BLACK)
        elif self.login_status == LOGIN_REQUEST_ERROR:
            canvas._text(0, 10, "Login request failed!", COLOR_BLACK)
            canvas._text(0, 20, "Check your network and", COLOR_BLACK)
            canvas._text(0, 30, "try again later.", COLOR_BLACK)
        else:
            canvas._text(0, 10, "Logging in...", COLOR_BLACK)

    def draw_menu_type1(self, canvas, selected_index: int, option1: str, option2: str):
        """Draw a menu with two options."""
        width = canvas.size.x
        height = canvas.size.y

        canvas.fill_screen(COLOR_WHITE)

        # Rain effect
        self.draw_rain_effect(canvas)

        # Calculate proportional positioning based on original 128x64 dimensions
        button1_x = width * 36 // 128
        button1_y = height * 22 // 64
        button2_y = height * 38 // 64
        button_width = width * 56 // 128
        button_height = height * 12 // 64
        text1_x = width * 54 // 128
        text1_y = height * 27 // 64
        text2_x = width * 54 // 128
        text2_y = height * 42 // 64

        # Draw buttons
        if selected_index == 0:
            canvas._fill_rectangle(
                button1_x,
                button1_y,
                button_width,
                button_height,
                COLOR_BLACK,
            )
            canvas._text(text1_x, text1_y, option1, COLOR_WHITE)
            canvas._rectangle(
                button1_x,
                button2_y,
                button_width,
                button_height,
                COLOR_BLACK,
            )
            canvas._text(text2_x, text2_y, option2, COLOR_BLACK)
        else:
            canvas._rectangle(
                button1_x,
                button1_y,
                button_width,
                button_height,
                COLOR_BLACK,
            )
            canvas._text(text1_x, text1_y, option1, COLOR_BLACK)
            canvas._fill_rectangle(
                button1_x,
                button2_y,
                button_width,
                button_height,
                COLOR_BLACK,
            )
            canvas._text(text2_x, text2_y, option2, COLOR_WHITE)

    def draw_menu_type2(
        self, canvas, selected_index_main: int, selected_index_settings: int
    ):
        """Draw the system menu."""
        height = canvas.size.y

        canvas.fill_screen(COLOR_WHITE)
        current_color = COLOR_BLACK

        left_column_x = 20
        left_column_width = 180
        right_column_x = 210
        right_column_width = 100
        right_column_height = 230
        menu_box_y = 30

        # Text spacing
        title_y = 40
        content_start_y = 80

        if selected_index_main == MENU_INDEX_PROFILE:
            # Draw profile header
            canvas._text(left_column_x, title_y, "PROFILE", COLOR_BLACK)

            # Draw horizontal separator line
            canvas._fill_rectangle(
                left_column_x,
                title_y + 15,
                left_column_width,
                2,
                COLOR_BLACK,
            )

            # Draw profile info
            name_y = content_start_y
            stats_y = name_y + 40

            # Name with larger emphasis
            if self.name is None or len(self.name) == 0:
                canvas._text(left_column_x, name_y, "Unknown", current_color)
            else:
                canvas._text(left_column_x, name_y, self.name, current_color)

            # Stats with aligned labels
            canvas._text(
                left_column_x,
                stats_y,
                f"Level    : {int(self.level)}",
                current_color,
            )
            canvas._text(
                left_column_x,
                stats_y + 25,
                f"Health   : {int(self.health)}",
                current_color,
            )
            canvas._text(
                left_column_x,
                stats_y + 50,
                f"XP       : {int(self.xp)}",
                current_color,
            )
            canvas._text(
                left_column_x,
                stats_y + 75,
                f"Strength : {int(self.strength)}",
                current_color,
            )

            # Draw the right column menu items with selection highlighting
            profile_y = 35
            map_y = 90
            settings_y = 145
            about_y = 200
            item_height = 50

            # Profile item
            if self.current_menu_index == MENU_INDEX_PROFILE:
                canvas._fill_rectangle(
                    right_column_x,
                    profile_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(right_column_x + 10, profile_y + 18, "Profile", current_color)

            # Map item
            if self.current_menu_index == MENU_INDEX_MAP:
                canvas._fill_rectangle(
                    right_column_x,
                    map_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(right_column_x + 10, map_y + 18, "Map", current_color)

            # Settings item
            if self.current_menu_index == MENU_INDEX_SETTINGS:
                canvas._fill_rectangle(
                    right_column_x,
                    settings_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(
                right_column_x + 10, settings_y + 18, "Settings", current_color
            )

            # About item
            if self.current_menu_index == MENU_INDEX_ABOUT:
                canvas._fill_rectangle(
                    right_column_x,
                    about_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(right_column_x + 10, about_y + 18, "About", current_color)

            # Draw border around the menu area
            current_color = COLOR_BLACK
            canvas._rectangle(
                right_column_x,
                menu_box_y,
                right_column_width,
                right_column_height,
                COLOR_BLACK,
            )

        elif selected_index_main == MENU_INDEX_MAP:
            # Draw mini map in the left column area
            map_pos = Vector(left_column_x, menu_box_y + 5)
            map_size = Vector(left_column_width - 10, right_column_height - 10)
            if self.current_dynamic_map is not None:
                self.current_dynamic_map.render_mini_map(
                    canvas,
                    map_pos,
                    map_size,
                    self.position,
                    self.direction,
                    COLOR_BLACK,
                    COLOR_WHITE,
                )
            else:
                canvas.text(
                    Vector(left_column_x, content_start_y), "No map loaded", COLOR_BLACK
                )

            # Draw the right column menu items with selection highlighting
            profile_y = 35
            map_y = 90
            settings_y = 145
            about_y = 200
            item_height = 50

            # Profile item
            if self.current_menu_index == MENU_INDEX_PROFILE:
                canvas._fill_rectangle(
                    right_column_x,
                    profile_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(right_column_x + 10, profile_y + 18, "Profile", current_color)

            # Map item (currently selected)
            if self.current_menu_index == MENU_INDEX_MAP:
                canvas._fill_rectangle(
                    right_column_x,
                    map_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(right_column_x + 10, map_y + 18, "Map", current_color)

            # Settings item
            if self.current_menu_index == MENU_INDEX_SETTINGS:
                canvas._fill_rectangle(
                    right_column_x,
                    settings_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(
                right_column_x + 10, settings_y + 18, "Settings", current_color
            )

            # About item
            if self.current_menu_index == MENU_INDEX_ABOUT:
                canvas._fill_rectangle(
                    right_column_x,
                    about_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(right_column_x + 10, about_y + 18, "About", current_color)

            # Draw border around the menu area
            current_color = COLOR_BLACK
            canvas._rectangle(
                right_column_x,
                menu_box_y,
                right_column_width,
                right_column_height,
                COLOR_BLACK,
            )

        elif selected_index_main == MENU_INDEX_SETTINGS:
            # Draw settings header
            canvas._text(left_column_x, title_y, "SETTINGS", COLOR_BLACK)

            # Draw horizontal separator line
            canvas._fill_rectangle(
                left_column_x,
                title_y + 15,
                left_column_width,
                2,
                COLOR_BLACK,
            )

            # Settings options
            option_y = content_start_y
            option_spacing = 35

            sound_status = f"Sound    : {toggle_to_string(self.sound_toggle)}"
            vibration_status = f"Vibrate  : {toggle_to_string(self.vibration_toggle)}"
            show_player_status = (
                f"Show Me  : {toggle_to_string(self.show_player_toggle)}"
            )

            # Draw settings info based on selected settings index
            if selected_index_settings == MENU_SETTINGS_MAIN:
                canvas._text(left_column_x, option_y, sound_status, current_color)
                canvas._text(
                    left_column_x,
                    option_y + option_spacing,
                    vibration_status,
                    current_color,
                )
                canvas._text(
                    left_column_x,
                    option_y + option_spacing * 2,
                    show_player_status,
                    current_color,
                )
                canvas._text(
                    left_column_x,
                    option_y + option_spacing * 3,
                    "Leave Game",
                    current_color,
                )

            elif selected_index_settings == MENU_SETTINGS_SOUND:
                # Highlight sound option
                canvas._fill_rectangle(
                    left_column_x - 5,
                    option_y - 8,
                    left_column_width,
                    25,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
                canvas._text(left_column_x, option_y, sound_status, current_color)
                current_color = COLOR_BLACK
                canvas._text(
                    left_column_x,
                    option_y + option_spacing,
                    vibration_status,
                    current_color,
                )
                canvas._text(
                    left_column_x,
                    option_y + option_spacing * 2,
                    show_player_status,
                    current_color,
                )
                canvas._text(
                    left_column_x,
                    option_y + option_spacing * 3,
                    "Leave Game",
                    current_color,
                )

            elif selected_index_settings == MENU_SETTINGS_VIBRATION:
                canvas._text(left_column_x, option_y, sound_status, current_color)
                # Highlight vibration option
                canvas._fill_rectangle(
                    left_column_x - 5,
                    option_y + option_spacing - 8,
                    left_column_width,
                    25,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
                canvas._text(
                    left_column_x,
                    option_y + option_spacing,
                    vibration_status,
                    current_color,
                )
                current_color = COLOR_BLACK
                canvas._text(
                    left_column_x,
                    option_y + option_spacing * 2,
                    show_player_status,
                    current_color,
                )
                canvas._text(
                    left_column_x,
                    option_y + option_spacing * 3,
                    "Leave Game",
                    current_color,
                )

            elif selected_index_settings == MENU_SETTINGS_SHOW_PLAYER:
                canvas._text(left_column_x, option_y, sound_status, current_color)
                canvas._text(
                    left_column_x,
                    option_y + option_spacing,
                    vibration_status,
                    current_color,
                )
                # Highlight show player option
                canvas._fill_rectangle(
                    left_column_x - 5,
                    option_y + option_spacing * 2 - 8,
                    left_column_width,
                    25,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
                canvas._text(
                    left_column_x,
                    option_y + option_spacing * 2,
                    show_player_status,
                    current_color,
                )
                current_color = COLOR_BLACK
                canvas._text(
                    left_column_x,
                    option_y + option_spacing * 3,
                    "Leave Game",
                    current_color,
                )

            elif selected_index_settings == MENU_SETTINGS_LEAVE:
                canvas._text(left_column_x, option_y, sound_status, current_color)
                canvas._text(
                    left_column_x,
                    option_y + option_spacing,
                    vibration_status,
                    current_color,
                )
                canvas._text(
                    left_column_x,
                    option_y + option_spacing * 2,
                    show_player_status,
                    current_color,
                )
                # Highlight leave game option
                canvas._fill_rectangle(
                    left_column_x - 5,
                    option_y + option_spacing * 3 - 8,
                    left_column_width,
                    25,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
                canvas._text(
                    left_column_x,
                    option_y + option_spacing * 3,
                    "Leave Game",
                    current_color,
                )
                current_color = COLOR_BLACK

            # Draw the right column menu items with selection highlighting
            profile_y = 35
            map_y = 90
            settings_y = 145
            about_y = 200
            item_height = 50

            # Profile item
            if self.current_menu_index == MENU_INDEX_PROFILE:
                canvas._fill_rectangle(
                    right_column_x,
                    profile_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(right_column_x + 10, profile_y + 18, "Profile", current_color)

            # Map item
            if self.current_menu_index == MENU_INDEX_MAP:
                canvas._fill_rectangle(
                    right_column_x,
                    map_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(right_column_x + 10, map_y + 18, "Map", current_color)

            # Settings item
            if self.current_menu_index == MENU_INDEX_SETTINGS:
                canvas._fill_rectangle(
                    right_column_x,
                    settings_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(
                right_column_x + 10, settings_y + 18, "Settings", current_color
            )

            # About item
            if self.current_menu_index == MENU_INDEX_ABOUT:
                canvas._fill_rectangle(
                    right_column_x,
                    about_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(right_column_x + 10, about_y + 18, "About", current_color)

            # Draw border around the menu area
            current_color = COLOR_BLACK
            canvas._rectangle(
                right_column_x,
                menu_box_y,
                right_column_width,
                right_column_height,
                COLOR_BLACK,
            )

        elif selected_index_main == MENU_INDEX_ABOUT:
            # Draw about header
            canvas._text(left_column_x, title_y, "ABOUT", COLOR_BLACK)

            # Draw horizontal separator line
            canvas._fill_rectangle(
                left_column_x,
                title_y + 15,
                left_column_width,
                2,
                COLOR_BLACK,
            )

            # About content
            about_y = content_start_y

            canvas._text(left_column_x, about_y, "Free Roam", COLOR_BLACK)
            canvas._text(left_column_x, about_y + 30, "Creator:  JBlanked", COLOR_BLACK)

            # Website at bottom
            canvas._text(
                left_column_x,
                height - 40,
                "https://www.github.com/jblanked",
                COLOR_BLACK,
            )

            # Draw the right column menu items with selection highlighting
            profile_y = 35
            map_y = 90
            settings_y = 145
            about_y = 200
            item_height = 50

            # Profile item
            if self.current_menu_index == MENU_INDEX_PROFILE:
                canvas._fill_rectangle(
                    right_column_x,
                    profile_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(right_column_x + 10, profile_y + 18, "Profile", current_color)

            # Map item
            if self.current_menu_index == MENU_INDEX_MAP:
                canvas._fill_rectangle(
                    right_column_x,
                    map_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(right_column_x + 10, map_y + 18, "Map", current_color)

            # Settings item
            if self.current_menu_index == MENU_INDEX_SETTINGS:
                canvas._fill_rectangle(
                    right_column_x,
                    settings_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(
                right_column_x + 10, settings_y + 18, "Settings", current_color
            )

            # About item
            if self.current_menu_index == MENU_INDEX_ABOUT:
                canvas._fill_rectangle(
                    right_column_x,
                    about_y,
                    right_column_width,
                    item_height,
                    COLOR_BLACK,
                )
                current_color = COLOR_WHITE
            else:
                current_color = COLOR_BLACK
            canvas._text(right_column_x + 10, about_y + 18, "About", current_color)

            # Draw border around the menu area
            current_color = COLOR_BLACK
            canvas._rectangle(
                right_column_x,
                menu_box_y,
                right_column_width,
                right_column_height,
                COLOR_BLACK,
            )

        else:
            # Unknown menu
            canvas.fill_screen(COLOR_WHITE)
            canvas._text(left_column_x, content_start_y, "Unknown Menu", COLOR_BLACK)

    def draw_rain_effect(self, canvas):
        """Draw rain/star droplet effect."""
        width = canvas.size.x
        height = canvas.size.y

        # Rain droplets/star droplets effect
        for i in range(16):
            # Use pseudo-random offsets based on frame and droplet index
            seed = (self.rain_frame + i * 37) & 0xFF
            x = (self.rain_frame + seed * 13) % width
            y = (self.rain_frame * 2 + seed * 7 + i * 23) % height

            # Draw star-like droplet with bounds checking
            canvas._pixel(x, y, COLOR_BLACK)
            if x >= 1:
                canvas._pixel(x - 1, y, COLOR_BLACK)
            if x <= width - 2:
                canvas._pixel(x + 1, y, COLOR_BLACK)
            if y >= 1:
                canvas._pixel(x, y - 1, COLOR_BLACK)
            if y <= height - 2:
                canvas._pixel(x, y + 1, COLOR_BLACK)

        self.rain_frame += 1
        if self.rain_frame >= width:
            self.rain_frame = 0

    def draw_registration_view(self, canvas):
        """Draw the registration view."""
        canvas.fill_screen(COLOR_WHITE)
        if self.registration_status == REGISTRATION_NOT_STARTED:
            self.user_request(REQUEST_TYPE_REGISTRATION)

            # Only proceed if the request was initiated successfully
            if self.http is not None:

                if self.loading:
                    del self.loading
                    self.loading = None
                self.loading = Loading(
                    self.free_roam_game.draw, COLOR_BLACK, COLOR_WHITE
                )
                self.loading.text = "Registering..."
                self.loading.animate(swap=False)

                self.registration_status = REGISTRATION_WAITING
            # else: user_request already set the error status
        elif self.registration_status == REGISTRATION_WAITING:
            if self.http is None:
                self.registration_status = REGISTRATION_REQUEST_ERROR
                return
            if not self.http.is_request_complete():
                self.loading.animate(swap=False)
                return
            response = self.http.response.text
            if "[SUCCESS]" in response:
                self.registration_status = REGISTRATION_SUCCESS
                self.current_main_view = GAME_VIEW_TITLE  # bring to the next view
            else:
                # Parse error response if needed
                self.registration_status = REGISTRATION_REQUEST_ERROR
            # refresh for next requests
            del self.http
            self.http = None
            del self.loading
            self.loading = None
        elif self.registration_status == REGISTRATION_SUCCESS:
            canvas._text(0, 10, "Registration successful!", COLOR_BLACK)
            canvas._text(0, 20, "Press OK to continue.", COLOR_BLACK)
        elif self.registration_status == REGISTRATION_CREDENTIALS_MISSING:
            canvas._text(0, 10, "Missing credentials!", COLOR_BLACK)
            canvas._text(0, 20, "Please update your username", COLOR_BLACK)
            canvas._text(0, 30, "and password in the settings.", COLOR_BLACK)
        elif self.registration_status == REGISTRATION_REQUEST_ERROR:
            canvas._text(0, 10, "Registration request failed!", COLOR_BLACK)
            canvas._text(0, 20, "Check your network and", COLOR_BLACK)
            canvas._text(0, 30, "try again later.", COLOR_BLACK)
        else:
            canvas._text(0, 10, "Registering...", COLOR_BLACK)

    def draw_system_menu_view(self, canvas):
        """Draw the system menu view."""
        self.draw_menu_type2(
            canvas, self.current_menu_index, self.current_settings_index
        )

    def draw_title_view(self, canvas):
        """Draw the title view."""
        self.draw_menu_type1(canvas, self.current_title_index, "Start", "Menu")

    def draw_user_info_view(self, canvas):
        """Draw the user info view."""
        canvas.fill_screen(COLOR_WHITE)
        if self.user_info_status == USER_INFO_NOT_STARTED:
            self.user_request(REQUEST_TYPE_USER_INFO)

            # Only proceed if the request was initiated successfully
            if self.http is not None:

                if self.loading:
                    del self.loading
                    self.loading = None
                self.loading = Loading(
                    self.free_roam_game.draw, COLOR_BLACK, COLOR_WHITE
                )
                self.loading.text = "Loading user info..."
                self.loading.animate(swap=False)

                self.user_info_status = USER_INFO_WAITING
            # else: user_request already set the error status
        elif self.user_info_status == USER_INFO_WAITING:
            if self.http is None:
                self.user_info_status = USER_INFO_REQUEST_ERROR
                return
            if not self.http.is_request_complete():
                self.loading.animate(swap=False)
                return
            if not self.http.response:
                self.user_info_status = USER_INFO_REQUEST_ERROR
                return

            response = self.http.response.text

            try:
                doc = json_loads(response)

                # Extract user info from response
                game_stats = doc.get("game_stats", {})
                username = game_stats.get("username", "")
                level = game_stats.get("level", 0)
                xp = game_stats.get("xp", 0)
                health = game_stats.get("health", 0)
                strength = game_stats.get("strength", 0)
                max_health = game_stats.get("max_health", 0)

                if (
                    not username
                    or level < 0
                    or xp < 0
                    or health < 0
                    or strength < 0
                    or max_health < 0
                ):
                    self.user_info_status = USER_INFO_PARSE_ERROR
                    return

                self.user_info_status = USER_INFO_SUCCESS

                canvas.fill_screen(COLOR_WHITE)
                canvas._text(0, 10, "User data found!", COLOR_BLACK)

                # Update player info
                self.player_name = username
                self.name = self.player_name
                self.level = level
                self.xp = xp
                self.health = health
                self.strength = strength
                self.max_health = max_health

                canvas.fill_screen(COLOR_WHITE)
                canvas._text(0, 10, "Player info updated!", COLOR_BLACK)

                if self.current_lobby_menu_index == LOBBY_MENU_INDEX_LOCAL:
                    self.current_main_view = (
                        GAME_VIEW_GAME_LOCAL  # Switch to local game view
                    )
                    if self.free_roam_game:
                        game_started = self.free_roam_game.start_game()
                        print("Game started:", game_started)

                elif self.current_lobby_menu_index == LOBBY_MENU_INDEX_ONLINE:
                    # Show the lobby browser so the user can create or join a game
                    self.lobby_fetched = False
                    self.lobby_selected_index = 0
                    self.current_main_view = GAME_VIEW_LOBBY_BROWSER

            except Exception as e:
                print(f"Error parsing user info: {e}")
                self.user_info_status = USER_INFO_PARSE_ERROR

            # refresh for next requests
            del self.http
            self.http = None
            del self.loading
            self.loading = None
        elif self.user_info_status == USER_INFO_SUCCESS:
            canvas._text(0, 10, "User info loaded successfully!", COLOR_BLACK)
            canvas._text(0, 20, "Press OK to continue.", COLOR_BLACK)
        elif self.user_info_status == USER_INFO_CREDENTIALS_MISSING:
            canvas._text(0, 10, "Missing credentials!", COLOR_BLACK)
            canvas._text(0, 20, "Please update your username", COLOR_BLACK)
            canvas._text(0, 30, "and password in the settings.", COLOR_BLACK)
        elif self.user_info_status == USER_INFO_REQUEST_ERROR:
            canvas._text(0, 10, "User info request failed!", COLOR_BLACK)
            canvas._text(0, 20, "Check your network and", COLOR_BLACK)
            canvas._text(0, 30, "try again later.", COLOR_BLACK)
        elif self.user_info_status == USER_INFO_PARSE_ERROR:
            canvas._text(0, 10, "Failed to parse user info!", COLOR_BLACK)
            canvas._text(0, 20, "Try again...", COLOR_BLACK)
        else:
            canvas._text(0, 10, "Loading user info...", COLOR_BLACK)

    def draw_welcome_view(self, canvas):
        """Draw the welcome view."""
        canvas.fill_screen(COLOR_WHITE)

        # Rain effect
        self.draw_rain_effect(canvas)

        width = canvas.size.x
        height = canvas.size.y

        # Draw welcome text with blinking effect
        if (self.welcome_frame // 15) % 2 == 0:
            canvas._text(
                width * 46 // 128,
                height * 60 // 64,
                "Press OK to start",
                COLOR_BLACK,
            )
        self.welcome_frame += 1

        # Reset frame counter to prevent overflow
        if self.welcome_frame >= 30:
            self.welcome_frame = 0

        # Draw a box around the OK button
        canvas._fill_rectangle(
            width * 40 // 128,
            height * 25 // 64,
            width * 56 // 128,
            height * 16 // 64,
            COLOR_BLACK,
        )
        canvas._text(width * 58 // 128, height * 32 // 64, "Welcome", COLOR_WHITE)

    def find_safe_spawn_position(self, level_name: str) -> Vector:
        """Find a safe spawn position for the given level."""
        default_pos = self.start_position

        if level_name == "Tutorial":
            default_pos = Vector(10, 10)  # Center of tutorial room
        elif level_name == "First":
            # Try several safe positions in the First level
            candidates = [
                Vector(12, 12),  # Upper left room
                Vector(8, 15),  # Left side of middle room
                Vector(5, 12),  # Lower in middle room
                Vector(3, 12),  # Even lower
                Vector(20, 12),  # Right side of middle room
            ]
            for candidate in candidates:
                if self.is_position_safe(candidate):
                    return candidate
            default_pos = Vector(12, 12)  # Fallback
        elif level_name == "Second":
            # Try several safe positions in the Second level
            candidates = [
                Vector(12, 10),  # Upper left room
                Vector(8, 8),  # Safe spot in starting room
                Vector(15, 10),  # Another spot in starting room
                Vector(10, 12),  # Lower in starting room
                Vector(35, 25),  # Central hub
            ]
            for candidate in candidates:
                if self.is_position_safe(candidate):
                    return candidate
            default_pos = Vector(12, 10)  # Fallback

        return default_pos

    def force_map_reload(self):
        """Force reload of the current map."""
        self.current_dynamic_map = None  # reset

    def handle_menu(self, draw, game):
        """Handle menu navigation and input."""
        if not draw or not game:
            return

        if self.current_menu_index != MENU_INDEX_SETTINGS:
            if game.input == INPUT_KEY_UP:
                if self.current_menu_index > MENU_INDEX_PROFILE:
                    self.current_menu_index -= 1

            elif game.input == INPUT_KEY_DOWN:
                if self.current_menu_index < MENU_INDEX_ABOUT:
                    self.current_menu_index += 1

        else:
            # Handle settings menu
            if self.current_settings_index == MENU_SETTINGS_MAIN:
                if game.input == INPUT_KEY_UP:
                    if self.current_menu_index > MENU_INDEX_PROFILE:
                        self.current_menu_index -= 1

                elif game.input == INPUT_KEY_DOWN:
                    if self.current_menu_index < MENU_INDEX_ABOUT:
                        self.current_menu_index += 1

                elif game.input == INPUT_KEY_LEFT:
                    self.current_settings_index = MENU_SETTINGS_SOUND

            elif self.current_settings_index == MENU_SETTINGS_SOUND:
                # sound on/off (using OK button), down to vibration, right to MainSettingsMain
                if game.input == INPUT_KEY_OK:
                    # Toggle sound on/off
                    self.sound_toggle = (
                        TOGGLE_STATE_OFF
                        if self.sound_toggle == TOGGLE_STATE_ON
                        else TOGGLE_STATE_ON
                    )

                elif game.input == INPUT_KEY_RIGHT:
                    self.current_settings_index = (
                        MENU_SETTINGS_MAIN  # Switch back to main settings
                    )

                elif game.input == INPUT_KEY_DOWN:
                    self.current_settings_index = (
                        MENU_SETTINGS_VIBRATION  # Switch to vibration settings
                    )

            elif self.current_settings_index == MENU_SETTINGS_VIBRATION:
                # vibration on/off (using OK button), up to sound, right to MainSettingsMain, down to show player
                if game.input == INPUT_KEY_OK:
                    # Toggle vibration on/off
                    self.vibration_toggle = (
                        TOGGLE_STATE_OFF
                        if self.vibration_toggle == TOGGLE_STATE_ON
                        else TOGGLE_STATE_ON
                    )

                elif game.input == INPUT_KEY_RIGHT:
                    self.current_settings_index = (
                        MENU_SETTINGS_MAIN  # Switch back to main settings
                    )

                elif game.input == INPUT_KEY_UP:
                    self.current_settings_index = (
                        MENU_SETTINGS_SOUND  # Switch to sound settings
                    )

                elif game.input == INPUT_KEY_DOWN:
                    self.current_settings_index = (
                        MENU_SETTINGS_SHOW_PLAYER  # Switch to show player settings
                    )

            elif self.current_settings_index == MENU_SETTINGS_SHOW_PLAYER:
                # show/hide player (using OK), up to vibration, down to leave game, right to main
                if game.input == INPUT_KEY_OK:
                    self.show_player_toggle = (
                        TOGGLE_STATE_OFF
                        if self.show_player_toggle == TOGGLE_STATE_ON
                        else TOGGLE_STATE_ON
                    )

                elif game.input == INPUT_KEY_RIGHT:
                    self.current_settings_index = (
                        MENU_SETTINGS_MAIN  # Switch back to main settings
                    )

                elif game.input == INPUT_KEY_UP:
                    self.current_settings_index = (
                        MENU_SETTINGS_VIBRATION  # Switch to vibration settings
                    )

                elif game.input == INPUT_KEY_DOWN:
                    self.current_settings_index = (
                        MENU_SETTINGS_LEAVE  # Switch to leave game settings
                    )

            elif self.current_settings_index == MENU_SETTINGS_LEAVE:
                # leave game (using OK button), up to show player, right to MainSettingsMain
                if game.input == INPUT_KEY_OK:
                    # Leave game
                    self.leave_game = TOGGLE_STATE_ON

                elif game.input == INPUT_KEY_RIGHT:
                    self.current_settings_index = (
                        MENU_SETTINGS_MAIN  # Switch back to main settings
                    )

                elif game.input == INPUT_KEY_UP:
                    self.current_settings_index = (
                        MENU_SETTINGS_SHOW_PLAYER  # Switch to show player settings
                    )

        self.draw_menu_type2(draw, self.current_menu_index, self.current_settings_index)

    def is_position_safe(self, pos: Vector) -> bool:
        """Check if a position is safe (not a wall)."""
        if self.current_dynamic_map is None:
            return True

        # Check if position is within bounds
        if (
            pos.x < 0
            or pos.y < 0
            or pos.x >= self.current_dynamic_map.width
            or pos.y >= self.current_dynamic_map.height
        ):
            return False

        # Check if the tile at this position is safe (not a wall)
        tile = self.current_dynamic_map.get_tile(int(pos.x), int(pos.y))
        return tile != 1  # TILE_WALL = 1

    def process_input(self):
        """Process player input for menu navigation."""
        if not self.free_roam_game:
            return

        current_input = self.last_input

        if current_input == INPUT_KEY_MAX:
            return  # No input to process

        if self.current_main_view == GAME_VIEW_WELCOME:
            if current_input == INPUT_KEY_OK:
                # Check if we should attempt login or skip to title
                if self.login_status != LOGIN_SUCCESS:
                    self.current_main_view = GAME_VIEW_LOGIN
                    self.login_status = (
                        LOGIN_NOT_STARTED  # Let draw_login_view handle the request
                    )
                else:
                    self.current_main_view = GAME_VIEW_TITLE

            elif current_input in (INPUT_KEY_BACK, INPUT_KEY_LEFT):
                if self.free_roam_game:
                    self.free_roam_game.end_game()

        elif self.current_main_view == GAME_VIEW_TITLE:
            if current_input == INPUT_KEY_UP:
                self.current_title_index = TITLE_INDEX_START

            elif current_input == INPUT_KEY_DOWN:
                self.current_title_index = TITLE_INDEX_MENU

            elif current_input == INPUT_KEY_OK:
                if self.current_title_index == TITLE_INDEX_START:
                    # Start button pressed - go to lobby menu
                    self.current_main_view = GAME_VIEW_LOBBY_MENU

                elif self.current_title_index == TITLE_INDEX_MENU:
                    # Menu button pressed - go to system menu
                    self.current_main_view = GAME_VIEW_SYSTEM_MENU

            elif current_input in (INPUT_KEY_BACK, INPUT_KEY_LEFT):
                self.free_roam_game.end_game()

        elif self.current_main_view == GAME_VIEW_LOBBY_MENU:
            if current_input == INPUT_KEY_UP:
                self.current_lobby_menu_index = LOBBY_MENU_INDEX_LOCAL

            elif current_input == INPUT_KEY_DOWN:
                self.current_lobby_menu_index = LOBBY_MENU_INDEX_ONLINE

            elif current_input == INPUT_KEY_OK:
                # Switch to GameViewUserInfo and load player stats
                self.current_main_view = GAME_VIEW_USER_INFO
                self.user_info_status = (
                    USER_INFO_NOT_STARTED  # Let draw_user_info_view handle the request
                )

            elif current_input in (INPUT_KEY_BACK, INPUT_KEY_LEFT):
                self.current_main_view = GAME_VIEW_TITLE

        elif self.current_main_view == GAME_VIEW_LOBBY_BROWSER:
            if current_input == INPUT_KEY_UP:
                if self.lobby_selected_index > 0:
                    self.lobby_selected_index -= 1
            elif current_input == INPUT_KEY_DOWN:
                if self.lobby_selected_index < self.lobby_count:
                    self.lobby_selected_index += 1
            elif current_input == INPUT_KEY_OK:
                if self.lobby_selected_index == 0:
                    # Create a new game — use existing create flow
                    self.online_game_state = ONLINE_STATE_IDLE
                    self.online_port = 0
                    self.online_game_id = ""
                    self.current_main_view = GAME_VIEW_GAME_ONLINE
                else:
                    # Join an existing lobby
                    idx = self.lobby_selected_index - 1
                    self.online_game_id = self.lobby_entries[idx].game_id
                    self.online_port = 80
                    self.online_game_state = ONLINE_STATE_JOINING_EXISTING
                    self.current_main_view = GAME_VIEW_GAME_ONLINE
            elif current_input == INPUT_KEY_BACK:
                self.lobby_fetched = False
                self.current_main_view = GAME_VIEW_LOBBY_MENU

        elif self.current_main_view == GAME_VIEW_SYSTEM_MENU:
            # Handle system menu with full navigation logic
            if self.current_menu_index != MENU_INDEX_SETTINGS:
                if current_input in (INPUT_KEY_BACK, INPUT_KEY_LEFT):
                    self.current_main_view = GAME_VIEW_TITLE

                elif current_input == INPUT_KEY_UP:
                    if self.current_menu_index > MENU_INDEX_PROFILE:
                        self.current_menu_index -= 1

                elif current_input == INPUT_KEY_DOWN:
                    if self.current_menu_index < MENU_INDEX_ABOUT:
                        self.current_menu_index += 1

                elif current_input == INPUT_KEY_OK:
                    # Enter the selected menu item
                    if self.current_menu_index == MENU_INDEX_SETTINGS:
                        # Entering settings - this doesn't change the main menu
                        self.current_settings_index = MENU_SETTINGS_MAIN

            else:  # current_menu_index == MENU_INDEX_SETTINGS
                if self.current_settings_index == MENU_SETTINGS_MAIN:
                    if current_input == INPUT_KEY_BACK:
                        self.current_main_view = GAME_VIEW_TITLE

                    elif current_input == INPUT_KEY_UP:
                        if self.current_menu_index > MENU_INDEX_PROFILE:
                            self.current_menu_index -= 1

                    elif current_input == INPUT_KEY_DOWN:
                        if self.current_menu_index < MENU_INDEX_ABOUT:
                            self.current_menu_index += 1

                    elif current_input == INPUT_KEY_LEFT:
                        self.current_settings_index = MENU_SETTINGS_SOUND

                elif self.current_settings_index == MENU_SETTINGS_SOUND:
                    if current_input == INPUT_KEY_OK:
                        # Toggle sound
                        self.sound_toggle = (
                            TOGGLE_STATE_OFF
                            if self.sound_toggle == TOGGLE_STATE_ON
                            else TOGGLE_STATE_ON
                        )
                        # Update the game's sound settings
                        if self.free_roam_game:
                            self.free_roam_game.sound_toggle = self.sound_toggle

                    elif current_input == INPUT_KEY_RIGHT:
                        self.current_settings_index = MENU_SETTINGS_MAIN

                    elif current_input == INPUT_KEY_DOWN:
                        self.current_settings_index = MENU_SETTINGS_VIBRATION

                elif self.current_settings_index == MENU_SETTINGS_VIBRATION:
                    if current_input == INPUT_KEY_OK:
                        # Toggle vibration
                        self.vibration_toggle = (
                            TOGGLE_STATE_OFF
                            if self.vibration_toggle == TOGGLE_STATE_ON
                            else TOGGLE_STATE_ON
                        )
                        # Update the game's vibration settings
                        if self.free_roam_game:
                            self.free_roam_game.vibration_toggle = self.vibration_toggle

                    elif current_input == INPUT_KEY_RIGHT:
                        self.current_settings_index = MENU_SETTINGS_MAIN

                    elif current_input == INPUT_KEY_UP:
                        self.current_settings_index = MENU_SETTINGS_SOUND

                    elif current_input == INPUT_KEY_DOWN:
                        self.current_settings_index = MENU_SETTINGS_SHOW_PLAYER

                elif self.current_settings_index == MENU_SETTINGS_SHOW_PLAYER:
                    if current_input == INPUT_KEY_OK:
                        self.show_player_toggle = (
                            TOGGLE_STATE_OFF
                            if self.show_player_toggle == TOGGLE_STATE_ON
                            else TOGGLE_STATE_ON
                        )

                    elif current_input == INPUT_KEY_RIGHT:
                        self.current_settings_index = MENU_SETTINGS_MAIN

                    elif current_input == INPUT_KEY_UP:
                        self.current_settings_index = MENU_SETTINGS_VIBRATION

                    elif current_input == INPUT_KEY_DOWN:
                        self.current_settings_index = MENU_SETTINGS_LEAVE

                elif self.current_settings_index == MENU_SETTINGS_LEAVE:
                    if current_input == INPUT_KEY_OK:
                        self.leave_game = TOGGLE_STATE_ON

                    elif current_input == INPUT_KEY_RIGHT:
                        self.current_settings_index = MENU_SETTINGS_MAIN

                    elif current_input == INPUT_KEY_UP:
                        self.current_settings_index = MENU_SETTINGS_SHOW_PLAYER

        elif self.current_main_view == GAME_VIEW_LOGIN:
            if current_input in (INPUT_KEY_BACK, INPUT_KEY_LEFT):
                self.current_main_view = GAME_VIEW_WELCOME

            elif current_input == INPUT_KEY_OK:
                if self.login_status == LOGIN_SUCCESS:
                    self.current_main_view = GAME_VIEW_TITLE

        elif self.current_main_view == GAME_VIEW_REGISTRATION:
            if current_input in (INPUT_KEY_BACK, INPUT_KEY_LEFT):
                self.current_main_view = GAME_VIEW_WELCOME

            elif current_input == INPUT_KEY_OK:
                if self.registration_status == REGISTRATION_SUCCESS:
                    self.current_main_view = GAME_VIEW_TITLE

        elif self.current_main_view == GAME_VIEW_USER_INFO:
            if current_input in (INPUT_KEY_BACK, INPUT_KEY_LEFT):
                self.current_main_view = GAME_VIEW_TITLE

        elif self.current_main_view in (GAME_VIEW_GAME_LOCAL, GAME_VIEW_GAME_ONLINE):
            # In game views, we need to handle input differently
            # The game engine itself will handle input through its update() method
            # We don't intercept input here to avoid conflicts with the in-game menu system
            pass

    def render(self, canvas, game):
        """Render the player view."""
        if not game.current_level:
            print("No current level to render.")
            return

        if self.just_switched_levels and not self.just_started:
            # Show message after switching levels
            canvas.fill_screen(COLOR_WHITE)
            canvas._text(5, 15, "New Level", COLOR_BLACK)
            canvas._text(5, 30, game.current_level.name, COLOR_BLACK)
            canvas._text(5, 58, "Tip: Press BACK to open the menu.", COLOR_BLACK)
            self.is_visible = False
            if self.level_switch_counter < 50:
                self.level_switch_counter += 1
            else:
                self.just_switched_levels = False
                self.level_switch_counter = 0
                self.is_visible = True
            return

        self.switch_levels(game)

        if self.game_state == GAME_STATE_PLAYING:
            if self._last_game_state != GAME_STATE_PLAYING:
                # Make entities active again
                for i in range(game.current_level.entity_count):
                    entity = game.current_level.get_entity(i)
                    if entity and not entity.is_active and not entity.is_player:
                        entity.is_active = True  # Activate all entities
                self.is_visible = True  # Show player entity in game
            self._last_game_state = GAME_STATE_PLAYING

            if self.current_dynamic_map is not None:
                # Check if the game is using 3rd person perspective
                if game.camera.perspective == CAMERA_THIRD_PERSON:
                    # Calculate 3rd person camera position for map rendering
                    # Normalize direction vector to ensure consistent behavior

                    dir_length = sqrt(
                        self.direction.x * self.direction.x
                        + self.direction.y * self.direction.y
                    )
                    normalized_dir = Vector(
                        self.direction.x / dir_length, self.direction.y / dir_length
                    )

                    if self.has_3d_sprite():
                        # Use Entity's methods instead of direct Sprite3D access
                        self.update_3d_sprite_position()

                        # Make sprite face the same direction as the camera (forward)
                        # Add π/2 offset to correct sprite orientation
                        camera_direction_angle = (
                            atan2(normalized_dir.y, normalized_dir.x) + pi / 2
                        )
                        self.set_3d_sprite_rotation(camera_direction_angle)

        elif self.game_state == GAME_STATE_MENU:
            if self._last_game_state != GAME_STATE_MENU:
                # Make entities inactive
                for i in range(game.current_level.entity_count):
                    entity = game.current_level.get_entity(i)
                    if entity and entity.is_active and not entity.is_player:
                        entity.is_active = False  # Deactivate all entities
                self.is_visible = False  # Hide player entity in menu
            self._last_game_state = GAME_STATE_MENU
            self.handle_menu(canvas, game)

    def switch_levels(self, game):
        """Switch to a new level if necessary."""
        if not game.current_level:
            print("No current level to switch to.")
            return
        if (
            self.current_dynamic_map is None
            or self.current_dynamic_map.name != game.current_level.name
        ):
            self.current_dynamic_map = None  # Reset

            posi = self.start_position
            if game.current_level.name == "Tutorial":
                from free_roam.maps import map_tutorial

                self.current_dynamic_map = map_tutorial()
            elif game.current_level.name == "First":
                from free_roam.maps import map_first

                self.current_dynamic_map = map_first()
            elif game.current_level.name == "Second":
                from free_roam.maps import map_second

                self.current_dynamic_map = map_second()
            elif game.current_level.name == "Online":
                from free_roam.maps import map_online

                self.current_dynamic_map = map_online()

            if self.current_dynamic_map is None:
                print(f"Error: No map found for level '{game.current_level.name}'")
                return

            if self.current_dynamic_map is not None:
                # Find a safe spawn position for the new level
                posi = self.find_safe_spawn_position(game.current_level.name)

                # Always set position when switching levels to avoid being stuck
                self.position = posi
                self.has_been_positioned = True

                # update 3D sprite position immediately after setting player position
                if self.has_3d_sprite():
                    self.update_3d_sprite_position()

                    # Also ensure the sprite rotation and scale are set correctly
                    self.set_3d_sprite_rotation(
                        atan2(self.direction.y, self.direction.x) + (pi / 2)
                    )  # Face forward with orientation correction
                    self.set_3d_sprite_scale(1.0)  # Normal scale

                # Register wall Sprite3Ds as Entity objects so Level renders them automatically.
                # Only do this once per level – if any "Wall" entities already exist, skip.
                walls_already_registered = False
                for i in range(game.current_level.entity_count):
                    e = game.current_level.get_entity(i)
                    if (
                        e
                        and e.name
                        and e.name == "Wall"
                        and e.type == ENTITY_TYPE_3D_SPRITE
                    ):
                        walls_already_registered = True
                        print(
                            "Wall entities already registered for this level, skipping registration."
                        )
                        break

                if not walls_already_registered:
                    # Transfer Sprite3D ownership from DynamicMap to new Entity objects

                    for wall in self.current_dynamic_map._render_walls:
                        if wall is None:
                            continue
                        wall_entity = Entity(
                            "Wall",
                            ENTITY_TYPE_3D_SPRITE,
                            wall.position,
                            Vector(1, 1),
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            False,
                            SPRITE_3D_NONE,
                            0x7BEF,  # Light gray color for walls
                        )
                        # Assign the Sprite3D directly – entity now owns it
                        wall_entity.sprite_3d = wall
                        wall_entity.sprite_3d_type = SPRITE_3D_CUSTOM
                        wall_entity.is_visible = True
                        game.current_level.entity_add(wall_entity)
                    self.current_dynamic_map.release_render_walls()

                # Indicate that we just switched levels
                self.just_switched_levels = True
                # Reset counter for level switch delay
                self.level_switch_counter = 0

    def update(self, game):
        """Update player state."""

        if game.input == INPUT_KEY_BACK:
            self.game_state = (
                GAME_STATE_PLAYING
                if self.game_state == GAME_STATE_MENU
                else GAME_STATE_MENU
            )
            return

        if self.game_state == GAME_STATE_MENU:
            return  # Don't update player position in menu

        self.is_visible = self.show_player_toggle == TOGGLE_STATE_ON

        if self.current_main_view == GAME_VIEW_GAME_ONLINE:
            # Don't update player position in online game view
            # its returned and handled by the server
            return

        rot_speed = 0.2  # Rotation speed in radians

        if game.input == INPUT_KEY_UP:
            # Calculate new position
            new_pos = Vector(
                self.position.x + self.direction.x * rot_speed,
                self.position.y + self.direction.y * rot_speed,
            )

            # Check collision with dynamic map
            if self.current_dynamic_map is None or not self.collision_map_check(
                new_pos
            ):
                # Move forward in the direction the player is facing
                self.position = new_pos

                # Update 3D sprite position and rotation to match camera direction
                if self.has_3d_sprite():
                    self.update_3d_sprite_position()
                    camera_direction_angle = atan2(
                        self.direction.y, self.direction.x
                    ) + (
                        pi / 2
                    )  # Face forward with orientation correction
                    self.set_3d_sprite_rotation(camera_direction_angle)

            game.input = INPUT_KEY_MAX
            self.just_started = False
            self.just_switched_levels = False
            self.is_visible = True

        elif game.input == INPUT_KEY_DOWN:
            # Calculate new position
            new_pos = Vector(
                self.position.x - self.direction.x * rot_speed,
                self.position.y - self.direction.y * rot_speed,
            )

            # Check collision with dynamic map
            if self.current_dynamic_map is None or not self.collision_map_check(
                new_pos
            ):
                self.position = new_pos

                # Update 3D sprite position and rotation to match camera direction
                if self.has_3d_sprite():
                    self.update_3d_sprite_position()
                    camera_direction_angle = atan2(
                        self.direction.y, self.direction.x
                    ) + (
                        pi / 2
                    )  # Face forward with orientation correction
                    self.set_3d_sprite_rotation(camera_direction_angle)
            game.input = INPUT_KEY_MAX
            self.just_started = False
            self.just_switched_levels = False
            self.is_visible = True

        elif game.input == INPUT_KEY_LEFT:
            old_dir_x = self.direction.x
            old_plane_x = self.plane.x
            self.direction = Vector(
                self.direction.x * cos(-rot_speed) - self.direction.y * sin(-rot_speed),
                old_dir_x * sin(-rot_speed) + self.direction.y * cos(-rot_speed),
            )
            self.plane = Vector(
                self.plane.x * cos(-rot_speed) - self.plane.y * sin(-rot_speed),
                old_plane_x * sin(-rot_speed) + self.plane.y * cos(-rot_speed),
            )

            # Update sprite rotation to match new camera direction
            if self.has_3d_sprite():
                camera_direction_angle = atan2(self.direction.y, self.direction.x) + (
                    pi / 2
                )  # Face forward with orientation correction
                self.set_3d_sprite_rotation(camera_direction_angle)

            game.input = INPUT_KEY_MAX
            self.just_started = False
            self.just_switched_levels = False
            self.is_visible = True

        elif game.input == INPUT_KEY_RIGHT:
            old_dir_x = self.direction.x
            old_plane_x = self.plane.x

            self.direction = Vector(
                self.direction.x * cos(rot_speed) - self.direction.y * sin(rot_speed),
                old_dir_x * sin(rot_speed) + self.direction.y * cos(rot_speed),
            )
            self.plane = Vector(
                self.plane.x * cos(rot_speed) - self.plane.y * sin(rot_speed),
                old_plane_x * sin(rot_speed) + self.plane.y * cos(rot_speed),
            )

            # Update sprite rotation to match new camera direction
            if self.has_3d_sprite():
                camera_direction_angle = atan2(self.direction.y, self.direction.x) + (
                    pi / 2
                )  # Face forward with orientation correction
                self.set_3d_sprite_rotation(camera_direction_angle)

            game.input = INPUT_KEY_MAX
            self.just_started = False
            self.just_switched_levels = False
            self.is_visible = True

        # Check for teleport tile
        if (
            self.current_dynamic_map is not None
            and self.current_dynamic_map.get_tile(
                int(self.position.x), int(self.position.y)
            )
            == 3
        ):
            # Switch to the next level or map
            if game.current_level is not None:
                if game.current_level.name == "Tutorial":
                    game.level_switch("First")
                elif game.current_level.name == "First":
                    game.level_switch("Second")
                elif game.current_level.name == "Second":
                    game.level_switch("Tutorial")

    def update_entities_from_server(self, csv: str) -> None:
        """Parse server entity state and update local entity positions.

        Expected CSV format:
          Entity update: name,x,y,z,dir_x,dir_y,plane_x,plane_y  (8 fields)
          Removal:       name,R                                    (2 fields)
        """
        if not csv or not self.free_roam_game or not self.free_roam_game.engine:
            return

        game = self.free_roam_game.engine.game
        if not game or not game.current_level:
            return

        # Field 0: name (up to first comma)
        comma = csv.find(",")
        if comma <= 0:
            return  # no comma or empty name

        entity_name = csv[:comma]
        rest = csv[comma + 1 :]

        # Check for removal marker: "R" as the second field
        if rest == "R" or rest.startswith("R\n") or rest.startswith("R\r"):
            if entity_name != self.player_name:
                level = game.current_level
                for i in range(level.entity_count):
                    e = level.get_entity(i)
                    if e and e.name == entity_name:
                        level.entity_remove(e)
                        self.remote_player_name_pool.discard(entity_name)
                        break
            return

        # Parse 7 float fields: x,y,z,dir_x,dir_y,plane_x,plane_y
        try:
            parts = rest.split(",", 6)
            if len(parts) < 7:
                return
            ex = float(parts[0])
            ey = float(parts[1])
            ez = float(parts[2])
            e_dir_x = float(parts[3])
            e_dir_y = float(parts[4])
            e_pl_x = float(parts[5])
            e_pl_y = float(parts[6])
        except (ValueError, IndexError):
            return

        # Update or spawn entity in the level
        level = game.current_level
        found = False
        for i in range(level.entity_count):
            e = level.get_entity(i)
            if e and e.name == entity_name:
                found = True
                e.position = Vector(ex, ey, ez)
                e.direction = Vector(e_dir_x, e_dir_y)
                e.plane = Vector(e_pl_x, e_pl_y)
                if e.has_3d_sprite():
                    rotation_angle = atan2(e.direction.y, e.direction.x) + pi / 2
                    e.set_3d_sprite_rotation(rotation_angle)
                    e.update_3d_sprite_position()
                break

        if not found:
            # First time seeing this remote player — add them to the level.
            self.remote_player_name_pool.add(entity_name)
            remote = Entity(
                entity_name,
                ENTITY_TYPE_PLAYER,
                Vector(ex, ey, ez),
                Vector(1.0, 1.5),
                None,  # sprite
                None,  # sprite_left
                None,  # sprite_right
                None,  # start
                None,  # stop
                None,  # update
                None,  # render
                None,  # collision
                False,  # is_8bit
                SPRITE_3D_HUMANOID,
                0xF800,  # 3d color (red)
            )
            remote.is_player = False
            remote.direction = Vector(e_dir_x, e_dir_y)
            remote.plane = Vector(e_pl_x, e_pl_y)
            level.entity_add(remote)

    def user_request(self, request_type: int) -> None:
        """Make a user request (login, registration, user info).

        Args:
            request_type: The type of request to make (LOGIN, REGISTRATION, USER_INFO)

        Returns:
            None
        """
        view_manager = self.free_roam_game.view_manager
        if not self.http:
            from picoware.system.http import HTTP

            self.http = HTTP(thread_manager=view_manager.thread_manager)

        if self.http is None:
            view_manager.log("[USER_REQUEST] Failed to create HTTP instance.", 2)
            if request_type == REQUEST_TYPE_LOGIN:
                self.login_status = LOGIN_REQUEST_ERROR
            elif request_type == REQUEST_TYPE_REGISTRATION:
                self.registration_status = REGISTRATION_REQUEST_ERROR
            elif request_type == REQUEST_TYPE_USER_INFO:
                self.user_info_status = USER_INFO_REQUEST_ERROR
            return

        user = self.username
        password = self.password

        if not user or not password:
            view_manager.log("[USER_REQUEST] Missing credentials for user request.", 2)
            if request_type == REQUEST_TYPE_LOGIN:
                self.login_status = LOGIN_CREDENTIALS_MISSING
            elif request_type == REQUEST_TYPE_REGISTRATION:
                self.registration_status = REGISTRATION_CREDENTIALS_MISSING
            elif request_type == REQUEST_TYPE_USER_INFO:
                self.user_info_status = USER_INFO_CREDENTIALS_MISSING
            return

        # Create JSON payload for login/registration
        payload = {"username": user, "password": password}
        headers = {
            "Content-Type": "application/json",
            "HTTP_USER_AGENT": "Pico",
            "Setting": "X-Flipper-Redirect",
            "username": user,
            "password": password,
            "User-Agent": "Raspberry Pi Pico W",
        }
        try:
            if request_type == REQUEST_TYPE_LOGIN:
                if not self.http.post_async(
                    "https://www.jblanked.com/flipper/api/user/login/",
                    payload,
                    headers=headers,
                ):
                    view_manager.log("[USER_REQUEST] Login request failed to start.", 2)
                    self.login_status = LOGIN_REQUEST_ERROR
            elif request_type == REQUEST_TYPE_REGISTRATION:
                if not self.http.post_async(
                    "https://www.jblanked.com/flipper/api/user/register/",
                    payload,
                    headers=headers,
                ):
                    view_manager.log(
                        "[USER_REQUEST] Registration request failed to start.", 2
                    )
                    self.registration_status = REGISTRATION_REQUEST_ERROR
            elif request_type == REQUEST_TYPE_USER_INFO:
                if not self.http.get_async(
                    f"https://www.jblanked.com/flipper/api/user/game-stats/{user}/",
                    headers=headers,
                ):
                    view_manager.log(
                        "[USER_REQUEST] User info request failed to start.", 2
                    )
                    self.user_info_status = USER_INFO_REQUEST_ERROR
            elif request_type == REQUEST_TYPE_GAME_CREATE:
                game_payload = {"game_name": "Free Roam", "username": user}
                if not self.http.post_async(
                    "https://www.jblanked.com/game-server/games/create/",
                    game_payload,
                    headers=headers,
                ):
                    view_manager.log(
                        "[USER_REQUEST] Game create request failed to start.", 2
                    )
                    self.online_game_state = ONLINE_STATE_ERROR
                else:
                    self.online_game_state = ONLINE_STATE_FETCHING_SESSION
            elif request_type == REQUEST_TYPE_GAME_LIST:
                if not self.http.get_async(
                    "https://www.jblanked.com/game-server/games/",
                    headers=headers,
                ):
                    view_manager.log(
                        "[USER_REQUEST] Game list request failed to start.", 2
                    )
                    self.lobby_fetched = True
                    self.lobby_count = 0
            else:
                self.login_status = LOGIN_REQUEST_ERROR
                self.registration_status = REGISTRATION_REQUEST_ERROR
                self.user_info_status = USER_INFO_REQUEST_ERROR
        except Exception as e:
            view_manager.log(f"[USER_REQUEST] HTTP request error: {e}", 2)
            if request_type == REQUEST_TYPE_LOGIN:
                self.login_status = LOGIN_REQUEST_ERROR
            elif request_type == REQUEST_TYPE_REGISTRATION:
                self.registration_status = REGISTRATION_REQUEST_ERROR
            elif request_type == REQUEST_TYPE_USER_INFO:
                self.user_info_status = USER_INFO_REQUEST_ERROR
