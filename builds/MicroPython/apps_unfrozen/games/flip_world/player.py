"""FlipWorld Player class for MicroPython"""

from micropython import const
from math import sin
from picoware.system.vector import Vector
from picoware.engine.entity import (
    Entity,
    ENTITY_TYPE_PLAYER,
    ENTITY_TYPE_ENEMY,
    ENTITY_STATE_DEAD,
    ENTITY_STATE_ATTACKED,
)
from picoware.gui.loading import Loading
from ujson import loads as json_loads
from flip_world.assets import player_left_sword_15x11px, player_right_sword_15x11px
from flip_world.colorize import colorize, COL_PLAYER, COL_FLAME_OUTER, COL_FLAME_CORE

# Burn state constants
_BURN_FOLIAGE_DURATION = 10.0  # seconds a foliage fire burns before it chars out
_BURN_TICK_DT = 0.05  # matches this class's other per-frame timers
_BURN_SINGE_RADIUS2 = 26 * 26  # proximity radius (squared, px) for singe damage
_BURN_SINGE_INTERVAL = 0.5  # seconds between singe damage ticks
_BURN_SINGE_DAMAGE_FOLIAGE = 5.0
_BURN_SINGE_DAMAGE_STRUCTURE = 8.0

# GameMainView
GAME_VIEW_TITLE = const(0)  # title, start, and menu (menu)
GAME_VIEW_SYSTEM_MENU = const(1)  # profile, settings, about (menu)
GAME_VIEW_GAME = const(2)  # game view (gameplay)
GAME_VIEW_LOGIN = const(3)  # login view
GAME_VIEW_REGISTRATION = const(4)  # registration view
GAME_VIEW_USER_INFO = const(5)  # user info view
GAME_VIEW_LOBBIES = const(6)  # lobbies view
GAME_VIEW_JOIN_LOBBY = const(7)  # join lobby view

# LoginStatus
LOGIN_CREDENTIALS_MISSING = const(-1)
LOGIN_SUCCESS = const(0)
LOGIN_USER_NOT_FOUND = const(1)
LOGIN_WRONG_PASSWORD = const(2)
LOGIN_WAITING = const(3)
LOGIN_NOT_STARTED = const(4)
LOGIN_REQUEST_ERROR = const(5)

# RegistrationStatus
REGISTRATION_CREDENTIALS_MISSING = const(-1)
REGISTRATION_SUCCESS = const(0)
REGISTRATION_USER_EXISTS = const(1)
REGISTRATION_REQUEST_ERROR = const(2)
REGISTRATION_NOT_STARTED = const(3)
REGISTRATION_WAITING = const(4)

# UserInfoStatus
USER_INFO_CREDENTIALS_MISSING = const(-1)
USER_INFO_SUCCESS = const(0)
USER_INFO_REQUEST_ERROR = const(1)
USER_INFO_NOT_STARTED = const(2)
USER_INFO_WAITING = const(3)
USER_INFO_PARSE_ERROR = const(4)

# LobbiesStatus
LOBBIES_CREDENTIALS_MISSING = const(-1)
LOBBIES_SUCCESS = const(0)
LOBBIES_REQUEST_ERROR = const(1)
LOBBIES_NOT_STARTED = const(2)
LOBBIES_WAITING = const(3)
LOBBIES_PARSE_ERROR = const(4)

# JoinLobbyStatus
JOIN_LOBBY_CREDENTIALS_MISSING = const(-1)
JOIN_LOBBY_SUCCESS = const(0)
JOIN_LOBBY_REQUEST_ERROR = const(1)
JOIN_LOBBY_NOT_STARTED = const(2)
JOIN_LOBBY_WAITING = const(3)
JOIN_LOBBY_PARSE_ERROR = const(4)

# RequestType
REQUEST_TYPE_LOGIN = const(0)
REQUEST_TYPE_REGISTRATION = const(1)
REQUEST_TYPE_USER_INFO = const(2)
REQUEST_TYPE_LOBBIES = const(3)
REQUEST_TYPE_JOIN_LOBBY = const(4)
REQUEST_TYPE_START_WEBSOCKET = const(5)
REQUEST_TYPE_STOP_WEBSOCKET = const(6)
REQUEST_TYPE_SAVE_STATS = const(7)

# TitleIndex constants
TITLE_INDEX_STORY = const(0)  # story mode
TITLE_INDEX_PVE = const(1)  # pve multiplayer mode

# MenuIndex constants
MENU_INDEX_PROFILE = const(0)
MENU_INDEX_ABOUT = const(1)
MENU_INDEX_LEAVE_GAME = const(2)

# ToggleState constants
TOGGLE_STATE_OFF = const(0)
TOGGLE_STATE_ON = const(1)

# GameState constants
GAME_STATE_PLAYING = const(0)
GAME_STATE_MENU = const(1)
GAME_STATE_SWITCHING_LEVELS = const(2)
GAME_STATE_LEAVING_GAME = const(3)

# Input key constants
INPUT_KEY_UP = const(0)  # BUTTON_UP
INPUT_KEY_DOWN = const(1)  # BUTTON_DOWN
INPUT_KEY_RIGHT = const(2)  # BUTTON_RIGHT
INPUT_KEY_LEFT = const(3)  # BUTTON_LEFT
INPUT_KEY_OK = const(4)  # BUTTON_OK
INPUT_KEY_BACK = const(5)  # BUTTON_BACK
INPUT_KEY_MAX = const(-1)  # BUTTON_NONE

# Color constants
COLOR_WHITE = const(0x0000)  # inverted on purpose
COLOR_BLACK = const(0xFFFF)  # inverted on purpose

_MM_BG = const(0x0000)  # black
_MM_FRAME = const(0x7BEF)
_MM_VIEW = const(0x39C7)
_MM_PLAYER = const(0x1C9F)
_MM_ENEMY = const(0xF800)
_MM_BOSS = const(0xFD20)

class LobbyInfo:
    """Structure to store lobby information."""

    __slots__ = ("id", "name", "player_count", "max_players")

    def __init__(self):
        self.id: str = ""
        self.name: str = ""
        self.player_count: int = 0
        self.max_players: int = 0

    def __del__(self):
        del self.id
        self.id = None
        del self.name
        self.name = None
        self.player_count = 0
        self.max_players = 0


class Player(Entity):
    """Player entity for the FlipWorld game."""

    def __init__(self):
        from picoware.engine.image import Image

        super().__init__(
            "Player",
            ENTITY_TYPE_PLAYER,
            Vector(384, 192),
            Vector(15, 11),
            Image(Vector(15, 11), True, player_left_sword_15x11px),  # sprite
            Image(Vector(15, 11), True, player_left_sword_15x11px),  # sprite left
            Image(Vector(15, 11), True, player_right_sword_15x11px),  # sprite right
            None,  # start
            None,  # stop
            self.update,  # update
            self.render,  # render
            None,  # collision
            True,  # is 8_bit
        )

        self.ws = None
        self.ws_data = None

        # Mark this entity as a player
        self.is_player = True
        self.end_position = Vector(384, 192)
        self.start_position = Vector(384, 192)
        self.player_name = "Player"
        self.name = self.player_name

        # Initialize player stats
        self.level = 1
        self.health = 100
        self.max_health = 100
        self.strength = 10
        self.attack_timer = 1
        self.health_regen = 1
        self.xp = 0
        self.elapsed_health_regen = 0.0
        self.elapsed_attack_timer = 0.0
        self._singe_cd = 0.0  # cooldown gate for burning-scenery proximity damage

        # Current view and menu state
        self.current_title_index: int = TITLE_INDEX_STORY
        self.current_lobby_index: int = 0
        self.current_main_view: int = GAME_VIEW_TITLE
        self.current_system_menu_index: int = MENU_INDEX_PROFILE

        # Reference to run instance
        self.flip_world_run = None
        self.screen_size: Vector = Vector(128, 64)  # is set run.update_draw later
        self.game_state: int = GAME_STATE_PLAYING

        # Track various states
        self.has_been_positioned: bool = False
        self.input_held: bool = False
        self.just_started: bool = True
        self.just_switched_levels: bool = False
        self.level_completion_cooldown: float = 0.0
        self.last_input: int = INPUT_KEY_MAX
        self.leave_game: int = TOGGLE_STATE_OFF

        # Network/loading state
        self.loading = None
        self.lobbies: list = [LobbyInfo() for _ in range(4)]
        self.lobbies_status: int = LOBBIES_NOT_STARTED
        self.lobby_count: int = 0
        self.login_status: int = LOGIN_NOT_STARTED
        self.rain_frame: int = 0
        self.registration_status: int = REGISTRATION_NOT_STARTED
        self.system_menu_debounce_timer: float = 0.0
        self.user_info_status: int = USER_INFO_NOT_STARTED
        self.join_lobby_status: int = JOIN_LOBBY_NOT_STARTED

        # HTTP instance
        self.http = None

        # Loaded credentials
        self.loaded_username: str = ""
        self.loaded_password: str = ""

        self._update_new_pos = Vector(0, 0)
        self._update_old_pos = Vector(0, 0)
        # carried velocity for the slippery Frozen Lake (glide)
        self.slide_vx = 0.0
        self.slide_vy = 0.0

        self.old_xp = 0

        self.user_stats_pos = Vector(0, 0)
        self._img_size = Vector(0, 0)
        self._sprite_pos = Vector(0, 0)

        self._data_left = colorize(player_left_sword_15x11px, COL_PLAYER)
        self._data_right = colorize(player_right_sword_15x11px, COL_PLAYER)

        self._MM_ICON = {
            0: 0xB483,   # house
            1: 0x0480,   # plant
            2: 0x0480,   # tree
            3: 0x9340,   # fence
            4: 0xF81F,   # flower
            5: 0x8410,   # rock_large
            6: 0x8410,   # rock_medium
            7: 0x8410,   # rock_small
            8: 0x041F,   # water
            9: 0xE77F,   # ice
            10: 0x041F,  # lake_bottom
            11: 0x041F,  # lake_top
            12: 0x9340,  # fence_vertical_start
            13: 0x9340,  # fence_vertical_end
            14: 0x24BF,  # man
            15: 0xFD5A,  # woman
        }

        # both scaled in login_view
        self._MM_W = 64
        self._MM_H = 32


    def __del__(self):
        if self.loading:
            del self.loading
            self.loading = None
        if self.http:
            self.http.close()
            del self.http
            self.http = None
        #
        del self.screen_size
        self.screen_size = None
        self.lobbies.clear()
        self.lobbies = None
        del self.user_stats_pos
        self.user_stats_pos = None
        del self._img_size
        self._img_size = None
        del self._update_new_pos
        self._update_new_pos = None
        del self._update_old_pos
        self._update_old_pos = None
        self._sprite_pos = None
        self._data_left = None
        self._data_right = None

    @property
    def should_leave_game(self) -> bool:
        """Check if the player has chosen to leave the game."""
        return self.leave_game == TOGGLE_STATE_ON

    @property
    def password(self) -> str:
        """Get password from storage."""
        if self.loaded_password:
            return self.loaded_password
        if not self.flip_world_run or not self.flip_world_run.view_manager:
            return ""
        view_manager = self.flip_world_run.view_manager
        from picoware.system.settings import Settings
        settings = Settings(view_manager.storage)
        _loaded_password = settings.server_settings.get("password", "")
        if _loaded_password:
            self.loaded_password = _loaded_password
        return _loaded_password

    @property
    def username(self) -> str:
        """Get username from storage."""
        if self.loaded_username:
            return self.loaded_username
        if not self.flip_world_run or not self.flip_world_run.view_manager:
            return ""
        view_manager = self.flip_world_run.view_manager
        from picoware.system.settings import Settings
        settings = Settings(view_manager.storage)
        s_loaded_username = settings.server_settings.get("username", "")
        if s_loaded_username:
            self.loaded_username = s_loaded_username
        return s_loaded_username

    def are_all_enemies_dead(self, game) -> bool:
        """Check if all enemies in the current level are dead."""
        if not game or not game.current_level:
            return False

        current_level = game.current_level
        total_enemies = 0
        dead_enemies = 0

        for i in range(current_level.entity_count):
            entity = current_level.get_entity(i)
            if entity and entity.type == ENTITY_TYPE_ENEMY:
                total_enemies += 1
                if entity.state == ENTITY_STATE_DEAD or entity.health <= 0:
                    dead_enemies += 1
                else:
                    return False

        if total_enemies == 0:
            return False

        return dead_enemies == total_enemies

    def check_for_level_completion(self, game):
        """Check if all enemies are dead and switch to next level if needed."""
        if not self.flip_world_run or not self.flip_world_run.is_running:
            return
        if self.current_main_view != GAME_VIEW_GAME:
            return
        # Update cooldown timer
        self.level_completion_cooldown -= 1.0 / 60.0
        if self.level_completion_cooldown > 0:
            return

        if self.just_switched_levels:
            self.just_switched_levels = False
            self.level_completion_cooldown = 1.0
            return

        if self.are_all_enemies_dead(game):
            print("All enemies defeated! Switching levels...")
            current_level_index = self.flip_world_run.current_level_index
            total = self.flip_world_run.total_levels

            # Persist progress: clearing a map unlocks the next one.
            self.flip_world_run.unlock_up_to(current_level_index + 2)

            # Beat the final map -> campaign complete: return to the menu instead of
            # looping back to the start.
            if current_level_index >= total - 1:
                self.leave_game = TOGGLE_STATE_ON
                return

            next_level_index = current_level_index + 1
            if self.flip_world_run.engine and self.flip_world_run.engine.game:
                self.game_state = GAME_STATE_SWITCHING_LEVELS
                # switch_to_level creates the level on demand (the ported maps aren't
                # pre-built at start), switches to it, and sets its icon group.
                self.flip_world_run.switch_to_level(next_level_index)

                self.flip_world_run.sync_multiplayer_level()

                # Reset player position
                self.position = self.start_position

                self.just_switched_levels = True
                self.health = self.max_health
                self.level_completion_cooldown = 2.0
                self.game_state = GAME_STATE_PLAYING

    def draw_current_view(self, canvas):
        """Draw the current view based on the game state."""
        if not canvas:
            return

        # Update debounce timer
        if self.system_menu_debounce_timer > 0.0:
            self.system_menu_debounce_timer -= 1.0 / 120.0
            self.system_menu_debounce_timer = max(self.system_menu_debounce_timer, 0.0)

        if self.current_main_view == GAME_VIEW_TITLE:
            self.draw_title_view(canvas)
        elif self.current_main_view == GAME_VIEW_GAME:
            self.draw_game_view(canvas)
        elif self.current_main_view == GAME_VIEW_LOGIN:
            self.draw_login_view(canvas)
        elif self.current_main_view == GAME_VIEW_REGISTRATION:
            self.draw_registration_view(canvas)
        elif self.current_main_view == GAME_VIEW_USER_INFO:
            self.draw_user_info_view(canvas)
        elif self.current_main_view == GAME_VIEW_LOBBIES:
            self.draw_lobbies_view(canvas)
        elif self.current_main_view == GAME_VIEW_JOIN_LOBBY:
            self.draw_join_lobby_view(canvas)
        elif self.current_main_view == GAME_VIEW_SYSTEM_MENU:
            self.draw_system_menu_view(canvas)
        else:
            canvas.fill_screen(COLOR_WHITE)
            canvas._text(0, canvas.scale_y(10), "Unknown View", COLOR_BLACK)

        canvas.swap()

    def draw_game_view(self, canvas):
        """Draw the game view."""
        if self.flip_world_run.is_running:
            engine = self.flip_world_run.engine
            if engine:
                canvas.fill_screen(engine.game.background_color)
                # Handle system menu input
                current_input = self.flip_world_run.current_input
                if (
                    current_input == INPUT_KEY_BACK
                    and self.system_menu_debounce_timer <= 0.0
                ):
                    self.current_main_view = GAME_VIEW_SYSTEM_MENU
                    self.system_menu_debounce_timer = 0.05
                    self.flip_world_run.reset_input()
                    return

                engine.update_game_input(current_input)
                self.flip_world_run.reset_input()
                engine.run_async(False)
            return

        canvas.fill_screen(COLOR_WHITE)
        canvas._text(canvas.scale_x(25), canvas.scale_y(32), "Starting Game...", COLOR_BLACK)
        game_started = self.flip_world_run.start_game()
        if game_started and self.flip_world_run.engine:
            self.flip_world_run.engine.run_async(False)

    def draw_join_lobby_view(self, canvas):
        """Draw the join lobby view."""
        canvas.fill_screen(COLOR_WHITE)
        if self.join_lobby_status == JOIN_LOBBY_WAITING:
            if not self.loading:
                self.user_request(REQUEST_TYPE_JOIN_LOBBY)
                self.loading = Loading(canvas, COLOR_BLACK, COLOR_WHITE)
                self.loading.text = "Joining..."
            if self.http and not self.http.is_request_complete():
                self.loading.animate(swap=False)
            else:
                if self.loading:
                    del self.loading
                    self.loading = None
                if self.http:
                    response = self.http.response.text if self.http.response else ""
                    if response:
                        self.join_lobby_status = JOIN_LOBBY_SUCCESS
                        self.current_main_view = GAME_VIEW_GAME
                        self.http.close()
                        del self.http
                        self.http = None
                        self.user_request(REQUEST_TYPE_START_WEBSOCKET)
                        self.flip_world_run.set_pve_mode(True)
                        self.flip_world_run.start_game()
                    else:
                        self.join_lobby_status = JOIN_LOBBY_REQUEST_ERROR
                        self.http.close()
                        del self.http
                        self.http = None
        elif self.join_lobby_status == JOIN_LOBBY_SUCCESS:
            canvas._text(0, canvas.scale_y(10), "Joined lobby!", COLOR_BLACK)
        elif self.join_lobby_status == JOIN_LOBBY_CREDENTIALS_MISSING:
            canvas._text(0, canvas.scale_y(10), "Missing credentials!", COLOR_BLACK)
        elif self.join_lobby_status == JOIN_LOBBY_REQUEST_ERROR:
            canvas._text(0, canvas.scale_y(10), "Join lobby failed!", COLOR_BLACK)
            canvas._text(0, canvas.scale_y(20), "Check your network.", COLOR_BLACK)
        else:
            canvas._text(0, canvas.scale_y(10), "Joining lobby...", COLOR_BLACK)

    def draw_lobbies_view(self, canvas):
        """Draw the lobbies view."""
        canvas.fill_screen(COLOR_WHITE)
        if self.lobbies_status == LOBBIES_WAITING:
            if not self.loading:
                self.loading = Loading(canvas, COLOR_BLACK, COLOR_WHITE)
                self.loading.text = "Fetching..."
                self.user_request(REQUEST_TYPE_LOBBIES)
                return
            if self.http and not self.http.is_request_complete():
                self.loading.animate(swap=False)
            else:
                if self.loading:
                    del self.loading
                    self.loading = None
                if self.http:
                    response = self.http.response.text if self.http.response else ""
                    if response:
                        self.lobbies_status = LOBBIES_SUCCESS
                        self.lobby_count = 0
                        self.current_lobby_index = 0
                        try:
                            data = json_loads(response)
                            lobbies_list = data.get("lobbies", [])
                            for i, lobby in enumerate(lobbies_list[:4]):
                                self.lobbies[i].id = lobby.get("id", "")
                                self.lobbies[i].name = lobby.get("name", f"Lobby {i}")
                                self.lobbies[i].player_count = lobby.get(
                                    "player_count", 0
                                )
                                self.lobbies[i].max_players = lobby.get(
                                    "max_players", 10
                                )
                                self.lobby_count += 1
                        except Exception:
                            self.lobbies_status = LOBBIES_PARSE_ERROR
                    else:
                        self.lobbies_status = LOBBIES_REQUEST_ERROR
                    del self.http
                    self.http = None
        elif self.lobbies_status == LOBBIES_SUCCESS:
            canvas._text(canvas.scale_x(5), canvas.scale_y(10), "Select a Lobby:", COLOR_BLACK)
            if self.lobby_count == 0:
                canvas._text(canvas.scale_x(5), canvas.scale_y(25), "No lobbies available", COLOR_BLACK)
            else:
                start_y = int(self.screen_size.y) // 5
                item_height = int(self.screen_size.y) // 10
                for i in range(min(4, self.lobby_count)):
                    y = start_y + i * item_height
                    if i == self.current_lobby_index:
                        canvas._fill_rectangle(
                            canvas.scale_x(3), 
                            canvas.scale_y(y - 2),
                            self.screen_size.x - canvas.scale_x(6), 
                            canvas.scale_y(item_height),
                            COLOR_BLACK,
                        )
                        color = COLOR_WHITE
                    else:
                        color = COLOR_BLACK
                    lobby_text = f"{self.lobbies[i].name} ({self.lobbies[i].player_count}/{self.lobbies[i].max_players})"
                    canvas._text(canvas.scale_x(5), canvas.scale_y(y + 7), lobby_text[:canvas.scale_x(25)], color)
        elif self.lobbies_status == LOBBIES_CREDENTIALS_MISSING:
            canvas._text(canvas.scale_x(0), canvas.scale_y(10), "Missing credentials!", COLOR_BLACK)
        elif self.lobbies_status == LOBBIES_REQUEST_ERROR:
            canvas._text(canvas.scale_x(0), canvas.scale_y(10), "Lobbies request failed!", COLOR_BLACK)
        else:
            canvas._text(canvas.scale_x(0), canvas.scale_y(10), "Loading lobbies...", COLOR_BLACK)

    def draw_login_view(self, canvas):
        """Draw the login view."""
        canvas.fill_screen(COLOR_WHITE)
        if self.login_status == LOGIN_WAITING:
            if not self.loading:
                self.user_request(REQUEST_TYPE_LOGIN)
                self.loading = Loading(canvas, COLOR_BLACK, COLOR_WHITE)
                self.loading.text = "Logging in..."
            if self.http and not self.http.is_request_complete():
                self.loading.animate(swap=False)
            else:
                if self.loading:
                    del self.loading
                    self.loading = None
                if self.http:
                    response = self.http.response.text if self.http.response else ""
                    if "[SUCCESS]" in response:
                        self.login_status = LOGIN_SUCCESS
                        self.current_main_view = GAME_VIEW_USER_INFO
                        self.user_info_status = USER_INFO_WAITING
                        self._MM_W = canvas.scale_x(64)
                        self._MM_H = canvas.scale_y(32)
                    elif "User not found" in response:
                        self.login_status = LOGIN_NOT_STARTED
                        self.current_main_view = GAME_VIEW_REGISTRATION
                        self.registration_status = REGISTRATION_WAITING
                    elif "Incorrect password" in response:
                        self.login_status = LOGIN_WRONG_PASSWORD
                    else:
                        self.login_status = LOGIN_REQUEST_ERROR
                    self.http.close()
                    del self.http
                    self.http = None
        elif self.login_status == LOGIN_SUCCESS:
            canvas._text(0, canvas.scale_y(10), "Login successful!", COLOR_BLACK)
        elif self.login_status == LOGIN_CREDENTIALS_MISSING:
            canvas._text(0, canvas.scale_y(10), "Missing credentials!", COLOR_BLACK)
            canvas._text(0, canvas.scale_y(20), "Set username/password", COLOR_BLACK)
        elif self.login_status == LOGIN_REQUEST_ERROR:
            canvas._text(0, canvas.scale_y(10), "Login failed!", COLOR_BLACK)
            canvas._text(0, canvas.scale_y(20), "Check your network.", COLOR_BLACK)
        elif self.login_status == LOGIN_WRONG_PASSWORD:
            canvas._text(0, canvas.scale_y(10), "Wrong password!", COLOR_BLACK)
        else:
            canvas._text(0, canvas.scale_y(10), "Logging in...", COLOR_BLACK)

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
        if self.registration_status == REGISTRATION_WAITING:
            if not self.loading:
                self.user_request(REQUEST_TYPE_REGISTRATION)
                self.loading = Loading(canvas, COLOR_BLACK, COLOR_WHITE)
                self.loading.text = "Registering..."
            if self.http and not self.http.is_request_complete():
                self.loading.animate(swap=False)
            else:
                if self.loading:
                    del self.loading
                    self.loading = None
                if self.http:
                    response = self.http.response.text if self.http.response else ""
                    if "[SUCCESS]" in response:
                        self.registration_status = REGISTRATION_SUCCESS
                        self.current_main_view = GAME_VIEW_USER_INFO
                        self.user_info_status = USER_INFO_WAITING
                    else:
                        self.registration_status = REGISTRATION_REQUEST_ERROR
                    self.http.close()
                    del self.http
                    self.http = None
        elif self.registration_status == REGISTRATION_SUCCESS:
            canvas._text(0, canvas.scale_y(10), "Registration successful!", COLOR_BLACK)
        elif self.registration_status == REGISTRATION_CREDENTIALS_MISSING:
            canvas._text(0, canvas.scale_y(10), "Missing credentials!", COLOR_BLACK)
        elif self.registration_status == REGISTRATION_REQUEST_ERROR:
            canvas._text(0, canvas.scale_y(10), "Registration failed!", COLOR_BLACK)
        else:
            canvas._text(0, canvas.scale_y(10), "Registering...", COLOR_BLACK)

    def draw_system_menu_view(self, canvas):
        """Draw the system menu view."""
        current_input = self.flip_world_run.current_input

        if current_input == INPUT_KEY_BACK and self.system_menu_debounce_timer <= 0.0:
            self.current_main_view = GAME_VIEW_GAME
            self.system_menu_debounce_timer = 0.05
            self.flip_world_run.reset_input()
            return

        if current_input == INPUT_KEY_UP and self.system_menu_debounce_timer <= 0.0:
            if self.current_system_menu_index > MENU_INDEX_PROFILE:
                self.current_system_menu_index -= 1
            self.system_menu_debounce_timer = 0.05
            self.flip_world_run.reset_input()
        elif current_input == INPUT_KEY_DOWN and self.system_menu_debounce_timer <= 0.0:
            if self.current_system_menu_index < MENU_INDEX_LEAVE_GAME:
                self.current_system_menu_index += 1
            self.system_menu_debounce_timer = 0.05
            self.flip_world_run.reset_input()
        elif current_input == INPUT_KEY_OK and self.system_menu_debounce_timer <= 0.0:
            if self.current_system_menu_index == MENU_INDEX_LEAVE_GAME:
                self.leave_game = TOGGLE_STATE_ON
                return
            self.system_menu_debounce_timer = 0.3
            self.flip_world_run.reset_input()

        canvas.fill_screen(COLOR_WHITE)

        # Menu box dimensions
        menu_x = int(self.screen_size.x * 0.625)
        menu_y = int(self.screen_size.y * 0.1875)
        menu_width = int(self.screen_size.x * 0.28125)
        menu_height = int(self.screen_size.y * 0.65625)

        # Menu item positions
        menu_item_y_offset = int(self.screen_size.y * 0.15625)
        menu_item_spacing = int(self.screen_size.y * 0.15625)
        menu_text_x = menu_x + 6

        if self.current_system_menu_index == MENU_INDEX_PROFILE:
            # Content positions using screen_size
            content_x = int(self.screen_size.x * 0.0546875)
            content_start_y = int(self.screen_size.y * 0.25)
            line_height = int(self.screen_size.y * 0.109375)

            canvas._text(
                content_x, content_start_y, self.name or "Player", COLOR_BLACK
            )
            canvas._text(
                content_x, content_start_y + line_height * 2, f"Level   : {int(self.level)}", COLOR_BLACK
            )
            canvas._text(
                content_x, content_start_y + line_height * 3, f"Health  : {int(self.health)}", COLOR_BLACK
            )
            canvas._text(
                content_x, content_start_y + line_height * 4, f"XP      : {int(self.xp)}", COLOR_BLACK
            )
            canvas._text(
                content_x, content_start_y + line_height * 5, f"Strength: {int(self.strength)}", COLOR_BLACK
            )

        elif self.current_system_menu_index == MENU_INDEX_ABOUT:
            # Content positions using screen_size
            content_x = int(self.screen_size.x * 0.0546875)
            content_start_y = int(self.screen_size.y * 0.25)
            line_height = int(self.screen_size.y * 0.109375)

            canvas._text(content_x, content_start_y, "FlipWorld v0.1", COLOR_BLACK)
            canvas._text(content_x, content_start_y + line_height, "Developed by", COLOR_BLACK)
            canvas._text(content_x, content_start_y + line_height * 2, "JBlanked and Derek", COLOR_BLACK)
            canvas._text(content_x, content_start_y + line_height * 3, "Jamison. Graphics", COLOR_BLACK)
            canvas._text(content_x, content_start_y + line_height * 4, "from Pr3!", COLOR_BLACK)

        elif self.current_system_menu_index == MENU_INDEX_LEAVE_GAME:
            # Content positions using screen_size
            content_x = int(self.screen_size.x * 0.0546875)
            content_start_y = int(self.screen_size.y * 0.25)
            line_height = int(self.screen_size.y * 0.109375)

            canvas._text(content_x, content_start_y, "Leave Game", COLOR_BLACK)
            canvas._text(content_x, content_start_y + line_height * 2, "Are you sure you", COLOR_BLACK)
            canvas._text(content_x, content_start_y + line_height * 3, "want to leave", COLOR_BLACK)
            canvas._text(content_x, content_start_y + line_height * 4, "the game?", COLOR_BLACK)

        # Draw menu box
        canvas._rectangle(
            menu_x, menu_y, menu_width, menu_height, COLOR_BLACK
        )

        # Draw menu items with highlight rectangle around current selection
        menu_items = ["Info", "More", "Quit"]
        highlight_padding = 2
        highlight_height = int(self.screen_size.y * 0.125)

        for i, item in enumerate(menu_items):
            item_y = menu_y + menu_item_y_offset + (i * menu_item_spacing)

            # Draw highlight rectangle around current menu item
            if i == self.current_system_menu_index:
                canvas._rectangle(
                    menu_text_x - highlight_padding, item_y - highlight_padding,
                    menu_width - 12, highlight_height,
                    COLOR_BLACK,
                )

            canvas._text(menu_text_x, item_y, item, COLOR_BLACK)

    def draw_title_view(self, canvas):
        """Draw the title view."""
        canvas.fill_screen(COLOR_WHITE)
        self.draw_rain_effect(canvas)

        button_x = int(self.screen_size.x * 0.28125)
        button_y1 = int(self.screen_size.y * 0.25)
        button_width = int(self.screen_size.x * 0.4375)
        button_height = int(self.screen_size.y * 0.25)
        button_y2 = int(self.screen_size.y * 0.5)
        text_x = int(self.screen_size.x * 0.421875)
        text_y1 = button_y1 + int(button_height * 0.6875)
        text_y2 = button_y2 + int(button_height * 0.625)

        if self.current_title_index == TITLE_INDEX_STORY:
            canvas._fill_rectangle(
                button_x, button_y1,
                button_width, button_height,
                COLOR_BLACK,
            )
            canvas._text(text_x, text_y1, "Story", COLOR_WHITE)
            canvas._fill_rectangle(
                button_x, button_y2,
                button_width, button_height,
                COLOR_WHITE,
            )
            canvas._text(text_x, text_y2, "PvE", COLOR_BLACK)
        else:
            canvas._fill_rectangle(
                button_x, button_y1,
                button_width, button_height,
                COLOR_WHITE,
            )
            canvas._text(text_x, text_y1, "Story", COLOR_BLACK)
            canvas._fill_rectangle(
                button_x, button_y2,
                button_width, button_height,
                COLOR_BLACK,
            )
            canvas._text(text_x, text_y2, "PvE", COLOR_WHITE)

        # Map picker: show which map Story will start on (< > to change). All maps can be
        # browsed, but locked ones are flagged and can't be launched.
        if self.current_title_index == TITLE_INDEX_STORY and self.flip_world_run:
            run = self.flip_world_run
            idx = run.start_level_index
            name = run.level_names[idx] if 0 <= idx < len(run.level_names) else "?"
            locked = idx >= run.unlocked_count
            lx = int(self.screen_size.x * 0.08)
            canvas._text(
                lx, int(self.screen_size.y * 0.80),
                "Map %d/%d: %s%s" % (idx + 1, run.total_levels, name, " (Locked)" if locked else ""),
                COLOR_BLACK,
            )
            canvas._text(
                lx, int(self.screen_size.y * 0.88),
                "< > choose map" if not locked else "< > locked - play earlier maps",
                COLOR_BLACK,
            )

    def draw_user_info_view(self, canvas):
        """Draw the user info view."""
        canvas.fill_screen(COLOR_WHITE)
        if self.user_info_status == USER_INFO_WAITING:
            if not self.loading:
                self.user_request(REQUEST_TYPE_USER_INFO)
                self.loading = Loading(canvas, COLOR_BLACK, COLOR_WHITE)
                self.loading.text = "Syncing..."
            if self.http and not self.http.is_request_complete():
                self.loading.animate(swap=False)
            else:
                if self.loading:
                    del self.loading
                    self.loading = None
                if self.http:
                    response = self.http.response.text if self.http.response else ""
                    if response:
                        try:
                            data = json_loads(response)
                            game_stats = data.get("game_stats", {})
                            if game_stats:
                                self.player_name = game_stats.get("username", "Player")
                                self.name = self.player_name
                                self.level = game_stats.get("level", 1)
                                self.xp = game_stats.get("xp", 0)
                                self.health = game_stats.get("health", 100)
                                self.strength = game_stats.get("strength", 10)
                                self.max_health = game_stats.get("max_health", 100)
                                self.user_info_status = USER_INFO_SUCCESS

                                if self.current_title_index == TITLE_INDEX_STORY:
                                    self.current_main_view = GAME_VIEW_GAME
                                    self.flip_world_run.start_game()
                                else:
                                    self.current_main_view = GAME_VIEW_LOBBIES
                                    self.lobbies_status = LOBBIES_WAITING
                            else:
                                self.user_info_status = USER_INFO_PARSE_ERROR
                        except Exception:
                            self.user_info_status = USER_INFO_PARSE_ERROR
                    else:
                        self.user_info_status = USER_INFO_REQUEST_ERROR
                    self.http.close()
                    del self.http
                    self.http = None
        elif self.user_info_status == USER_INFO_SUCCESS:
            canvas._text(0, 10, "User info loaded!", COLOR_BLACK)
        elif self.user_info_status == USER_INFO_CREDENTIALS_MISSING:
            canvas._text(0, 10, "Missing credentials!", COLOR_BLACK)
        elif self.user_info_status == USER_INFO_REQUEST_ERROR:
            canvas._text(0, 10, "User info request failed!", COLOR_BLACK)
        elif self.user_info_status == USER_INFO_PARSE_ERROR:
            canvas._text(0, 10, "Failed to parse user info!", COLOR_BLACK)
        else:
            canvas._text(0, 10, "Loading user info...", COLOR_BLACK)

    def draw_username(self, pos: Vector, game):
        """Draw the username at the specified position."""
        if not self.name or not game:
            return

        # Calculate the center of the player horizontally
        player_center_x = int(pos.x + self.size.x / 2)
        screen_x = int(player_center_x - game.position.x)
        screen_y = int(pos.y - game.position.y)

        # Calculate text width using font size
        text_width = game.draw.len(self.name)
        font_height = game.draw.font_size.y

        # Calculate box dimensions with padding
        box_padding = 2
        box_width = int(text_width + (box_padding * 2))
        box_height = int(font_height + (box_padding * 2))

        # Position box above the player at consistent height
        vertical_offset = int(self.screen_size.x // 18)

        # Center the box horizontally on the player
        box_x = int(screen_x - box_width // 2)
        box_y = int(screen_y - vertical_offset)

        # Check if box is within screen bounds
        if box_x < 0 or box_x + box_width > self.screen_size.x:
            return
        if box_y < 0 or box_y + box_height > self.screen_size.y:
            return

        # Draw centered box
        game.draw._fill_rectangle(
            box_x, box_y,
            box_width, box_height,
            0xFFFF,  # white box (visible on the dark game background)
        )

        # Center the text in the box
        text_x = int(screen_x - text_width // 2)
        text_y = int(box_y + box_padding)
        game.draw._text(
            text_x,
            text_y,
            self.name,
            0x0000,  # black text
        )

    def draw_user_stats(self, pos: Vector, canvas):
        """Draw the user stats at the specified position."""
        canvas._fill_rectangle(
            pos.x - canvas.scale_x(2),
            pos.y - canvas.scale_y(5),
            0,
            0,
            COLOR_WHITE,
        )

        health_str = f"HP : {int(self.health)}"
        level_str = f"LVL: {int(self.level)}"
        if self.xp < 10000:
            xp_str = f"XP : {int(self.xp)}"
        else:
            xp_str = f"XP : {int(self.xp // 1000)}K"

        canvas._text(pos.x, pos.y, health_str, COLOR_BLACK)
        canvas._text(pos.x, pos.y + canvas.scale_y(9), xp_str, COLOR_BLACK)
        canvas._text(pos.x, pos.y + canvas.scale_y(18), level_str, COLOR_BLACK)

    def _update_burning_icons(self, game):
        """Advance on-fire timers for scenery, char foliage out, singe the player.
        Foliage (burn_kind 1) burns for a fixed duration then chars and goes inert; a structure like a
        house (burn_kind 2) has no char condition here, so once lit it keeps
        blazing indefinitely. Standing too close to anything currently on fire
        deals periodic damage.
        """
        run = self.flip_world_run
        if not run or not run.current_icon_group:
            return

        if self._singe_cd > 0:
            self._singe_cd -= _BURN_TICK_DT

        px = self.position.x + self.size.x * 0.5
        py = self.position.y + self.size.y * 0.5
        can_singe = self._singe_cd <= 0
        singed = False

        for spec in run.current_icon_group.icons:
            if spec.on_fire <= 0.0:
                continue
            spec.on_fire += _BURN_TICK_DT

            if spec.burn_kind == 1 and spec.on_fire >= _BURN_FOLIAGE_DURATION:
                # Foliage chars out and goes inert; it can never reignite.
                spec.charred = True
                spec.on_fire = 0.0
                spec.burn_kind = 0
                continue

            if can_singe and not singed:
                cx = spec.x + spec.width * 0.5
                cy = spec.y + spec.height * 0.5
                dx = cx - px
                dy = cy - py
                if dx * dx + dy * dy <= _BURN_SINGE_RADIUS2:
                    dmg = (
                        _BURN_SINGE_DAMAGE_STRUCTURE
                        if spec.burn_kind == 2
                        else _BURN_SINGE_DAMAGE_FOLIAGE
                    )
                    self.health -= dmg
                    if self.health <= 0:
                        self.state = ENTITY_STATE_DEAD
                        self.health = self.max_health
                        self.position = self.start_position
                    else:
                        self.state = ENTITY_STATE_ATTACKED
                    singed = True

        if singed:
            self._singe_cd = _BURN_SINGE_INTERVAL

    def _draw_icon_flame(self, draw, spec, x, y):
        """Flicker a flame over a burning icon (screen coords in self._img_vec)."""
        flames = spec.width // 8
        if flames < 1:
            flames = 1
        step = spec.width / flames
        top_y = y
        for i in range(flames):
            fx = int(x + step * (i + 0.5))
            flick = sin(spec.on_fire * 9.0 + i * 2.1) * 2.0
            fy = int(top_y - 2 + flick)
            draw._fill_circle(fx, fy, 3, COL_FLAME_OUTER)
            draw._fill_circle(fx, fy, 1, COL_FLAME_CORE)

    def icon_group_render(self, game):
        """Render the icon group for the current level."""
        if not self.flip_world_run or not game or not game.draw:
            return

        # Camera bounds for visibility culling
        cam_x = game.position.x
        cam_y = game.position.y
        cam_right = cam_x + self.screen_size.x
        cam_bottom = cam_y + self.screen_size.y

        # Expand by small margin to prevent pop-in
        margin = 20
        cull_left = cam_x - margin
        cull_top = cam_y - margin
        cull_right = cam_right + margin
        cull_bottom = cam_bottom + margin

        icon_data_map = self.flip_world_run.icon_map
        char_map = self.flip_world_run.icon_char_map

        for spec in self.flip_world_run.current_icon_group.icons:
            half_w = spec.width >> 1
            half_h = spec.height >> 1

            # Fast rejection test - is icon center even close to camera?
            if spec.x + half_w < cull_left or spec.x - half_w > cull_right:
                continue
            if spec.y + half_h < cull_top or spec.y - half_h > cull_bottom:
                continue

            # Icon is potentially visible, calculate screen position
            _img_vec_x = int(spec.x - cam_x - half_w)
            _img_vec_y = int(spec.y - cam_y - half_h)

            # Final bounds check
            if (
                _img_vec_x + spec.width < 0
                or _img_vec_x > self.screen_size.x
                or _img_vec_y + spec.height < 0
                or _img_vec_y > self.screen_size.y
            ):
                continue

            self._img_size.x = spec.width
            self._img_size.y = spec.height

            # Draw the icon (charred tint once foliage has fully burned out)
            data = icon_data_map[spec.id]
            if spec.charred:
                data = char_map.get(spec.id, data)
            game.draw._bytearray(_img_vec_x, _img_vec_y, spec.width, spec.height, data)

            # Flame overlay while actively on fire (foliage mid-burn, or a
            # structure like a house, which stays ablaze indefinitely)
            if spec.on_fire > 0.0:
                self._draw_icon_flame(game.draw, spec, _img_vec_x, _img_vec_y)

    def draw_minimap(self, draw, game):
        """Top-right minimap: world objects, enemies, the boss, the player, camera view."""
        lvl = game.current_level
        if not lvl:
            return
        world_w = lvl.size.x
        world_h = lvl.size.y
        if world_w <= 0 or world_h <= 0:
            return
        mm_x = int(self.screen_size.x - self._MM_W - 4)
        mm_y = 4
        sx = self._MM_W / world_w
        sy = self._MM_H / world_h

        # background + grey frame
        pos_x = mm_x
        pos_y = mm_y
        size_x = self._MM_W
        size_y = self._MM_H
        draw._fill_rectangle(pos_x, pos_y, size_x, size_y, _MM_BG)
        size_y = 1
        draw._fill_rectangle(pos_x, pos_y, size_x, size_y, _MM_FRAME)
        pos_y = mm_y + self._MM_H - 1
        draw._fill_rectangle(pos_x, pos_y, size_x, size_y, _MM_FRAME)
        pos_y = mm_y
        size_x = 1
        size_y = self._MM_H
        draw._fill_rectangle(pos_x, pos_y, size_x, size_y, _MM_FRAME)
        pos_x = mm_x + self._MM_W - 1
        draw._fill_rectangle(pos_x, pos_y, size_x, size_y, _MM_FRAME)

        # camera view box (clamped inside the minimap)
        vx = mm_x + int(game.position.x * sx)
        vy = mm_y + int(game.position.y * sy)
        vw = int(self.screen_size.x * sx)
        vh = int(self.screen_size.y * sy)
        if vx < mm_x:
            vw -= mm_x - vx
            vx = mm_x
        if vy < mm_y:
            vh -= mm_y - vy
            vy = mm_y
        if vw > self._MM_W - (vx - mm_x):
            vw = self._MM_W - (vx - mm_x)
        if vh > self._MM_H - (vy - mm_y):
            vh = self._MM_H - (vy - mm_y)
        if vw > 0 and vh > 0:
            pos_x = vx
            pos_y = vy
            size_x = vw
            size_y = 1
            draw._fill_rectangle(pos_x, pos_y, size_x, size_y, _MM_VIEW)
            pos_y = vy + vh - 1
            draw._fill_rectangle(pos_x, pos_y, size_x, size_y, _MM_VIEW)
            pos_y = vy
            size_x = 1
            size_y = vh
            draw._fill_rectangle(pos_x, pos_y, size_x, size_y, _MM_VIEW)
            pos_x = vx + vw - 1
            draw._fill_rectangle(pos_x, pos_y, size_x, size_y, _MM_VIEW)

        # world objects
        run = self.flip_world_run
        if run and run.current_icon_group:
            icons = run.current_icon_group.icons
            n = len(icons)
            step = 1 + (n // 120)
            for k in range(0, n, step):
                spec = icons[k]
                col = self._MM_ICON.get(spec.id)
                if col is None:
                    continue
                dx = mm_x + int(spec.x * sx)
                dy = mm_y + int(spec.y * sy)
                if mm_x <= dx < mm_x + self._MM_W and mm_y <= dy < mm_y + self._MM_H:
                    draw._pixel(dx, dy, col)

        # entities: enemies, the boss, and the player
        for i in range(lvl.entity_count):
            e = lvl.get_entity(i)
            if not e:
                continue
            if e.type == ENTITY_TYPE_PLAYER:
                col = _MM_PLAYER
                r = 2
            elif e.type == ENTITY_TYPE_ENEMY:
                if e.state == ENTITY_STATE_DEAD or e.health <= 0:
                    continue
                if e.size.x >= 40:  # the big dragon boss
                    col = _MM_BOSS
                    r = 4
                else:
                    col = _MM_ENEMY
                    r = 1
            else:
                continue
            dx = mm_x + int(e.position.x * sx)
            dy = mm_y + int(e.position.y * sy)
            if dx < mm_x:
                dx = mm_x
            elif dx > mm_x + self._MM_W - r - 1:
                dx = mm_x + self._MM_W - r - 1
            if dy < mm_y:
                dy = mm_y
            elif dy > mm_y + self._MM_H - r - 1:
                dy = mm_y + self._MM_H - r - 1

            draw._fill_rectangle(dx, dy, r + 1, r + 1, col)

    def process_input(self):
        """Process input for all views."""
        if not self.flip_world_run:
            return

        current_input = self.last_input
        if current_input == INPUT_KEY_MAX:
            return

        if self.current_main_view == GAME_VIEW_TITLE:
            if current_input == INPUT_KEY_UP:
                self.current_title_index = TITLE_INDEX_STORY

            elif current_input == INPUT_KEY_DOWN:
                self.current_title_index = TITLE_INDEX_PVE

            elif current_input in (INPUT_KEY_LEFT, INPUT_KEY_RIGHT) and (
                self.current_title_index == TITLE_INDEX_STORY and self.flip_world_run
            ):
                # Map picker: choose which map Story starts on (any of the maps).
                run = self.flip_world_run
                idx = run.start_level_index + (1 if current_input == INPUT_KEY_RIGHT else -1)
                run.start_level_index = max(0, min(idx, run.total_levels - 1))

            elif current_input == INPUT_KEY_OK:
                # A locked map can be browsed but not played.
                if (
                    self.current_title_index == TITLE_INDEX_STORY
                    and self.flip_world_run.start_level_index
                    >= self.flip_world_run.unlocked_count
                ):
                    return
                self.current_main_view = GAME_VIEW_LOGIN
                self.login_status = LOGIN_WAITING
            elif current_input == INPUT_KEY_BACK:
                self.leave_game = TOGGLE_STATE_ON

        elif self.current_main_view == GAME_VIEW_LOGIN:
            if current_input == INPUT_KEY_BACK:
                self.current_main_view = GAME_VIEW_TITLE

            elif current_input == INPUT_KEY_OK:
                if self.login_status == LOGIN_SUCCESS:
                    self.current_main_view = GAME_VIEW_USER_INFO
                    self.user_info_status = USER_INFO_WAITING

        elif self.current_main_view == GAME_VIEW_REGISTRATION:
            if current_input == INPUT_KEY_BACK:
                self.current_main_view = GAME_VIEW_TITLE

            elif current_input == INPUT_KEY_OK:
                if self.registration_status == REGISTRATION_SUCCESS:
                    self.current_main_view = GAME_VIEW_USER_INFO
                    self.user_info_status = USER_INFO_WAITING

        elif self.current_main_view == GAME_VIEW_USER_INFO:
            if current_input == INPUT_KEY_BACK:
                self.current_main_view = GAME_VIEW_TITLE

        elif self.current_main_view == GAME_VIEW_LOBBIES:
            if current_input == INPUT_KEY_BACK:
                self.current_main_view = GAME_VIEW_TITLE

            elif current_input == INPUT_KEY_UP:
                if self.lobbies_status == LOBBIES_SUCCESS and self.lobby_count > 0:
                    self.current_lobby_index = (
                        self.current_lobby_index - 1 + self.lobby_count
                    ) % self.lobby_count

            elif current_input == INPUT_KEY_DOWN:
                if self.lobbies_status == LOBBIES_SUCCESS and self.lobby_count > 0:
                    self.current_lobby_index = (
                        self.current_lobby_index + 1
                    ) % self.lobby_count

            elif current_input == INPUT_KEY_OK:
                if self.lobbies_status == LOBBIES_SUCCESS and self.lobby_count > 0:
                    self.current_main_view = GAME_VIEW_JOIN_LOBBY

                    self.join_lobby_status = JOIN_LOBBY_WAITING
                    self.flip_world_run.set_is_lobby_host(
                        self.lobbies[self.current_lobby_index].player_count == 0
                    )
                elif self.lobbies_status != LOBBIES_SUCCESS:
                    self.current_main_view = GAME_VIEW_TITLE

    def render(self, draw, game):
        """Render callback for the player."""
        if self.current_main_view != GAME_VIEW_GAME:
            return

        # Draw player sprite explicitly
        screen_x = int(self.position.x - game.position.x)
        screen_y = int(self.position.y - game.position.y)
        if (
            screen_x + self.size.x >= 0
            and screen_x < game.draw.size.x
            and screen_y + self.size.y >= 0
            and screen_y < game.draw.size.y
        ):
            _data = self._data_left if self.direction.x == -1 else self._data_right
            self._sprite_pos.x = screen_x
            self._sprite_pos.y = screen_y
            draw.image_bytearray(self._sprite_pos, self.size, _data)

        self.draw_username(self.position, game)
        self.draw_user_stats(self.user_stats_pos, canvas=draw)
        self.draw_minimap(draw, game)
        # Suppress engine auto-draw (sprite already drawn above)
        self.is_visible = False

    def sync_multiplayer_state(self):
        """Sync's the sprites data for multiplayer"""
        if (
            self.flip_world_run is None  # class must be set
            or self.ws is None  # ws must be set
        ):
            return
        # send sprite data to server
        self.flip_world_run.sync_multiplayer_entity(self)

    def update(self, game):
        """Update callback for the player."""
        if self.current_main_view != GAME_VIEW_GAME:
            return

        self.flip_world_run.icons_rendered = False

        # Health regeneration
        self.elapsed_health_regen += 0.05
        if self.elapsed_health_regen >= 1 and self.health < self.max_health:
            self.health += self.health_regen
            self.elapsed_health_regen = 0
            self.health = min(self.health, self.max_health)

        self.elapsed_attack_timer += 0.05
        self._update_burning_icons(game)
        self.update_stats()
        self.check_for_level_completion(game)

        self.old_position = self.position
        self._update_old_pos = self.position
        self._update_new_pos.x = self._update_old_pos.x
        self._update_new_pos.y = self._update_old_pos.y
        should_set_position = False

        # Input direction (one axis at a time, matching the rest of the game).
        in_dx = 0
        in_dy = 0
        if game.input == INPUT_KEY_UP:
            in_dy = -1
            self.direction = Vector(0, -1)
        elif game.input == INPUT_KEY_DOWN:
            in_dy = 1
            self.direction = Vector(0, 1)
        elif game.input == INPUT_KEY_LEFT:
            in_dx = -1
            self.direction = Vector(-1, 0)
        elif game.input == INPUT_KEY_RIGHT:
            in_dx = 1
            self.direction = Vector(1, 0)
        # Consume a movement input so it isn't re-applied, but LEAVE an attack (CENTER)
        # in place so the enemies' collision handler can read it and take the hit.
        if in_dx != 0 or in_dy != 0:
            game.input = INPUT_KEY_MAX

        # Frozen Lake is slippery: input builds a carried velocity and friction lets the
        # player glide to a stop instead of moving in fixed 5px steps.
        lvl = game.current_level
        icy = lvl is not None and lvl.name == "Frozen Lake"
        if icy:
            self.slide_vx += in_dx * 1.6
            self.slide_vy += in_dy * 1.6
            self.slide_vx *= 0.90
            self.slide_vy *= 0.90
            sp = (self.slide_vx * self.slide_vx + self.slide_vy * self.slide_vy) ** 0.5
            if sp > 5.0:
                self.slide_vx = self.slide_vx / sp * 5.0
                self.slide_vy = self.slide_vy / sp * 5.0
            elif sp < 0.05:
                self.slide_vx = 0.0
                self.slide_vy = 0.0
            if self.slide_vx != 0.0 or self.slide_vy != 0.0:
                self._update_new_pos.x += self.slide_vx
                self._update_new_pos.y += self.slide_vy
                should_set_position = True
                # face the way we're actually gliding
                if abs(self.slide_vx) >= abs(self.slide_vy):
                    self.direction = Vector(-1 if self.slide_vx < 0 else 1, 0)
                else:
                    self.direction = Vector(0, -1 if self.slide_vy < 0 else 1)
        else:
            self.slide_vx = 0.0
            self.slide_vy = 0.0
            if in_dx != 0:
                self._update_new_pos.x += in_dx * 5
                should_set_position = True
            if in_dy != 0:
                self._update_new_pos.y += in_dy * 5
                should_set_position = True

        # Check boundaries
        if (
            self._update_new_pos.x < 0
            or self._update_new_pos.x + self.size.x > game.size.x
        ):
            should_set_position = False
            self.slide_vx = 0.0  # stop the glide at the edge
        if (
            self._update_new_pos.y < 0
            or self._update_new_pos.y + self.size.y > game.size.y
        ):
            should_set_position = False
            self.slide_vy = 0.0

        if should_set_position:
            has_collision = False

            # Loop over all icon specifications in the current icon group.
            for icon in self.flip_world_run.current_icon_group.icons:
                if icon.id == 9:  # ICON_ID_ICE
                    continue

                if (
                    abs(self._update_new_pos.x - icon.x) > 30
                    or abs(self._update_new_pos.y - icon.y) > 30
                ):
                    continue

                # Calculate the difference between the NEW position and the icon's center.
                dx = self._update_new_pos.x - icon.x
                dy = self._update_new_pos.y - icon.y
                radius = (icon.width + icon.height) / 4.0

                # Collision: if player's distance to the icon center is less than the collision radius.
                if (dx * dx + dy * dy) < (radius * radius):
                    has_collision = True
                    break

            # Only update position if there's no collision
            if not has_collision:
                self.position = self._update_new_pos
                self.sync_multiplayer_state()
            else:
                # ran into scenery — stop sliding
                self.slide_vx = 0.0
                self.slide_vy = 0.0

        # update player sprite based on direction
        if self.direction.x == -1 and self.direction.y == 0:
            self.sprite = self.sprite_left
        elif self.direction.x == 1 and self.direction.y == 0:
            self.sprite = self.sprite_right

        # Update camera
        viewport_width = self.screen_size.x
        viewport_height = self.screen_size.y

        camera_x = self.position.x - (viewport_width / 2)
        camera_y = self.position.y - (viewport_height / 2)

        _pos_x = max(0, min(camera_x, game.size.x - viewport_width))
        _pos_y = max(0, min(camera_y, game.size.y - viewport_height))
        game.position = Vector(_pos_x, _pos_y)

    def update_stats(self):
        """Update player stats based on XP."""
        if self.xp == self.old_xp:
            return

        self.level = 1
        xp_required = 100

        while self.level < 100 and self.xp >= xp_required:
            self.level += 1
            xp_required = int(xp_required * 1.5)

        self.strength = 10 + (self.level * 1)
        self.max_health = 100 + ((self.level - 1) * 10)

        self.old_xp = self.xp

    def __user_request_ws_callback(self, data):
        """WebSocket callback for handling incoming messages."""
        if not data:
            return
        self.ws_data = data

    def user_request(self, request_type: int):
        """Send a user request to the server."""
        if not self.flip_world_run:
            return

        username = self.username
        password = self.password

        if not username or not password:
            if request_type == REQUEST_TYPE_LOGIN:
                self.login_status = LOGIN_CREDENTIALS_MISSING
            elif request_type == REQUEST_TYPE_REGISTRATION:
                self.registration_status = REGISTRATION_CREDENTIALS_MISSING
            elif request_type == REQUEST_TYPE_USER_INFO:
                self.user_info_status = USER_INFO_CREDENTIALS_MISSING
            elif request_type == REQUEST_TYPE_LOBBIES:
                self.lobbies_status = LOBBIES_CREDENTIALS_MISSING
            elif request_type == REQUEST_TYPE_JOIN_LOBBY:
                self.join_lobby_status = JOIN_LOBBY_CREDENTIALS_MISSING
            return

        from picoware.system.http import HTTP

        if self.http:
            self.http.close()
            del self.http
            self.http = None

        view_manager = self.flip_world_run.view_manager
        self.http = HTTP(thread_manager=view_manager.thread_manager)

        try:
            # Create JSON payload for login/registration
            payload = {"username": username, "password": password}
            headers = {
                "Content-Type": "application/json",
                "HTTP_USER_AGENT": "Pico",
                "Setting": "X-Flipper-Redirect",
                "username": username,
                "password": password,
                "User-Agent": "Raspberry Pi Pico W",
            }

            if request_type == REQUEST_TYPE_LOGIN:
                self.http.post_async(
                    "https://www.jblanked.com/flipper/api/user/login/",
                    payload,
                    headers,
                )
            elif request_type == REQUEST_TYPE_REGISTRATION:
                self.http.post_async(
                    "https://www.jblanked.com/flipper/api/user/register/",
                    payload,
                    headers,
                )
            elif request_type == REQUEST_TYPE_USER_INFO:
                self.http.get_async(
                    f"https://www.jblanked.com/flipper/api/user/game-stats/{username}/",
                    headers,
                )
            elif request_type == REQUEST_TYPE_LOBBIES:
                self.http.get_async(
                    "https://www.jblanked.com/flipper/api/world/pve/lobbies/10/4/",
                    headers,
                )
            elif request_type == REQUEST_TYPE_JOIN_LOBBY:
                lobby_id = self.lobbies[self.current_lobby_index].id
                payload2 = {"username": username, "game_id": lobby_id}
                self.http.post_async(
                    "https://www.jblanked.com/flipper/api/world/pve/lobby/join/",
                    payload2,
                    headers,
                )
            elif request_type == REQUEST_TYPE_START_WEBSOCKET:
                self.http.close()
                del self.http
                self.http = None
                if self.ws is not None:
                    self.ws.close()
                    del self.ws
                    self.ws = None

                from picoware.system.websocket import WebSocketAsync

                self.ws = WebSocketAsync(
                    f"ws://www.jblanked.com/ws/game/{self.lobbies[self.current_lobby_index].id}/",
                    callback=self.__user_request_ws_callback,
                    thread_manager=view_manager.thread_manager,
                )
                if not self.ws or not self.ws.connect():
                    view_manager.log("Failed to start WebSocket", 2)
                    self.join_lobby_status = JOIN_LOBBY_REQUEST_ERROR
                    del self.ws
                    self.ws = None
            elif request_type == REQUEST_TYPE_STOP_WEBSOCKET:
                self.http.close()
                del self.http
                self.http = None
                if self.ws is not None:
                    self.ws.close()
                    del self.ws
                    self.ws = None
            elif request_type == REQUEST_TYPE_SAVE_STATS:
                player_json = self.flip_world_run.entity_to_json(self)
                if not self.http.post_async(
                    "https://www.jblanked.com/flipper/api/user/update-game-stats/",
                    player_json,
                    headers,
                ):
                    view_manager.log("Failed to save player stats", 2)

        except Exception:
            if request_type == REQUEST_TYPE_LOGIN:
                self.login_status = LOGIN_REQUEST_ERROR
            elif request_type == REQUEST_TYPE_REGISTRATION:
                self.registration_status = REGISTRATION_REQUEST_ERROR
            elif request_type == REQUEST_TYPE_USER_INFO:
                self.user_info_status = USER_INFO_REQUEST_ERROR
            elif request_type == REQUEST_TYPE_LOBBIES:
                self.lobbies_status = LOBBIES_REQUEST_ERROR
            elif request_type == REQUEST_TYPE_JOIN_LOBBY:
                self.join_lobby_status = JOIN_LOBBY_REQUEST_ERROR
