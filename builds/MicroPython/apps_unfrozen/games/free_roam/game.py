from micropython import const

GAME_VIEW_GAME_LOCAL = const(3)  # game view local (gameplay)
GAME_VIEW_GAME_ONLINE = const(4)  # game view online (gameplay)
INPUT_KEY_BACK = const(5)
COLOR_WHITE = const(0x0000)  # inverted on purpose
COLOR_BLACK = const(0xFFFF)  # inverted on purpose


class FreeRoamGame:
    """Free Roam Game class"""

    def __init__(self, view_manager):
        self.current_level_index: int = 0
        self.engine = None
        self.is_game_running: bool = False
        self.last_input: int = -1
        self.level_names: list[str] = ["Tutorial", "First", "Second"]
        self.player = None
        self.should_return_to_menu: bool = False
        self.sound_toggle: int = 1  # ToggleOn
        self.total_levels: int = 3
        self.vibration_toggle: int = 1  # ToggleOn
        self.view_manager = view_manager

    def __del__(self):
        """Destructor to clean up resources"""
        if self.engine:
            del self.engine
            self.engine = None
        if self.player:
            del self.player
            self.player = None
        self.level_names.clear()

    @property
    def draw(self):
        """get the draw object from the view manager"""
        return self.view_manager.draw

    @property
    def is_active(self):
        """Check if the game is active"""
        return self.should_return_to_menu is False

    @property
    def is_running(self):
        """Check if the game engine is running"""
        return self.is_game_running

    def end_game(self):
        """end the game and return to the submenu"""
        self.should_return_to_menu = True
        self.is_game_running = False

        if self.engine:
            self.engine.stop()

    def input_manager(self):
        """manage input for the game, called from updateInput"""
        # Pass input to player for processing
        if self.player:
            self.player.last_input = self.last_input
            self.player.process_input()

    def reset_input(self):
        """Reset input after processing"""
        self.last_input = -1

    def start_game(self) -> bool:
        """start the actual game"""
        from math import pi
        from picoware.engine.engine import GameEngine
        from picoware.engine.level import Level
        from picoware.engine.game import Game
        from picoware.system.vector import Vector
        from picoware.engine.camera import Camera, CAMERA_THIRD_PERSON
        from picoware.engine.entity import (
            SPRITE_3D_HUMANOID,
            SPRITE_3D_HOUSE,
            SPRITE_3D_TREE,
        )
        from free_roam.sprite import Sprite

        self.view_manager.log("Initializing Free Roam Game...")

        if self.is_game_running or self.engine:
            # Game already running, skipping start
            self.view_manager.log("Game already running, skipping initialization")
            return True

        # Create the game instance with 3rd person perspective
        game = Game(
            "Free Roam",
            self.draw.size,
            self.draw,
            self.view_manager.input_manager,
            COLOR_WHITE,  # foreground color (actually black)
            COLOR_BLACK,  # background color (actually white)
            Camera(
                perspective=CAMERA_THIRD_PERSON
            ),  # Use 3rd person camera perspective
        )
        if not game:
            # Failed to create Game object
            self.view_manager.log("Failed to create Game object", 2)
            return False

        # Create the player instance if it doesn't exist
        if not self.player:
            from free_roam.player import Player
            from json import loads as json_loads

            data: str = self.view_manager.storage.read(
                "picoware/flip_social/username.json"
            )
            player = "Player"
            if data is not None:
                try:
                    obj: dict = json_loads(data)
                    if "username" in obj:
                        player = obj["username"]
                except Exception:
                    pass

            self.player = Player(player)
            if not self.player:
                self.view_manager.log("Failed to create Player object", 2)
                # Failed to create Player object
                return False

        self.view_manager.log("Player object created successfully")

        # set sound/vibration toggle states
        self.player.sound_toggle = self.sound_toggle
        self.player.vibration_toggle = self.vibration_toggle

        # add levels and player to the game
        level1 = Level("Tutorial", self.draw.size, game)
        level2 = Level("First", self.draw.size, game)
        level3 = Level("Second", self.draw.size, game)

        # we'll clear ourselves and swap afterwards too
        level1.clear_allowed = False
        level2.clear_allowed = False
        level3.clear_allowed = False

        level1.entity_add(self.player)
        level2.entity_add(self.player)
        level3.entity_add(self.player)

        # add some 3D sprites
        tutorial_guard_1 = Sprite(
            "Tutorial Guard 1",
            Vector(3, 7),
            SPRITE_3D_HUMANOID,
            1.5,
            1.0,
            pi / 4,
            Vector(9, 7),
        )
        tutorial_guard_2 = Sprite(
            "Tutorial Guard 2",
            Vector(6, 2),
            SPRITE_3D_HUMANOID,
            1.5,
            1.0,
            pi / 4,
            Vector(1, 2),
        )
        level1.entity_add(tutorial_guard_1)
        level1.entity_add(tutorial_guard_2)

        # Town (level 2) - 4 houses spread across the open map
        house1 = Sprite(
            "House 1",
            Vector(14, 13),
            SPRITE_3D_HOUSE,
            10.0,
            10.0,
            0.0,
            Vector(-1, -1),
            0x03EF,
        )
        house2 = Sprite(
            "House 2",
            Vector(48, 13),
            SPRITE_3D_HOUSE,
            10.0,
            10.0,
            pi / 2,
            Vector(-1, -1),
            0x03EF,
        )
        house3 = Sprite(
            "House 3",
            Vector(14, 43),
            SPRITE_3D_HOUSE,
            10.0,
            10.0,
            pi,
            Vector(-1, -1),
            0x03EF,
        )
        house4 = Sprite(
            "House 4",
            Vector(48, 43),
            SPRITE_3D_HOUSE,
            10.0,
            10.0,
            pi * 1.5,
            Vector(-1, -1),
            0x03EF,
        )
        level2.entity_add(house1)
        level2.entity_add(house2)
        level2.entity_add(house3)
        level2.entity_add(house4)

        # Forest (level 3) - trees scattered throughout the open map
        tree_positions = [
            Vector(8, 8),
            Vector(20, 6),
            Vector(35, 9),
            Vector(50, 7),
            Vector(6, 20),
            Vector(18, 22),
            Vector(30, 18),
            Vector(44, 24),
            Vector(55, 15),
            Vector(10, 35),
            Vector(25, 40),
            Vector(40, 36),
            Vector(52, 42),
            Vector(8, 48),
            Vector(22, 50),
            Vector(38, 48),
        ]
        tree_names = [
            "Tree 1",
            "Tree 2",
            "Tree 3",
            "Tree 4",
            "Tree 5",
            "Tree 6",
            "Tree 7",
            "Tree 8",
            "Tree 9",
            "Tree 10",
            "Tree 11",
            "Tree 12",
            "Tree 13",
            "Tree 14",
            "Tree 15",
            "Tree 16",
        ]
        for i in range(16):
            level3.entity_add(
                Sprite(
                    tree_names[i],
                    tree_positions[i],
                    SPRITE_3D_TREE,
                    3.0,
                    1.0,
                    0.0,
                    Vector(-1, -1),
                    0x07E0,
                )
            )

        game.level_add(level1)
        game.level_add(level2)
        game.level_add(level3)

        self.view_manager.log("Levels and player added to game successfully")

        self.engine = GameEngine(game, 240)
        if not self.engine:
            # Failed to create GameEngine
            self.view_manager.log("Failed to create GameEngine", 2)
            return False

        self.view_manager.log("GameEngine created successfully")
        self.view_manager.log("Starting Free Roam Game...")
        self.is_game_running = True  # Set the flag to indicate game is running
        return True

    def start_game_online(self) -> bool:
        """Start the online multiplayer game"""
        from math import pi
        from picoware.engine.engine import GameEngine
        from picoware.engine.level import Level
        from picoware.engine.game import Game
        from picoware.system.vector import Vector
        from picoware.engine.camera import Camera, CAMERA_THIRD_PERSON
        from picoware.engine.entity import (
            SPRITE_3D_HOUSE,
            SPRITE_3D_TREE,
        )
        from free_roam.sprite import Sprite

        self.view_manager.log("Initializing Free Roam Game...")

        if self.is_game_running or self.engine:
            # Game already running, skipping start
            self.view_manager.log("Game already running, skipping initialization")
            return True

        # Create the game instance with 3rd person perspective
        game = Game(
            "Free Roam",
            self.draw.size,
            self.draw,
            self.view_manager.input_manager,
            COLOR_WHITE,  # foreground color (actually black)
            COLOR_BLACK,  # background color (actually white)
            Camera(
                perspective=CAMERA_THIRD_PERSON
            ),  # Use 3rd person camera perspective
        )
        if not game:
            # Failed to create Game object
            self.view_manager.log("Failed to create Game object", 2)
            return False

        # Create the player instance if it doesn't exist
        if not self.player:
            from free_roam.player import Player
            from json import loads as json_loads

            data: str = self.view_manager.storage.read(
                "picoware/flip_social/username.json"
            )
            player = "Player"
            if data is not None:
                try:
                    obj: dict = json_loads(data)
                    if "username" in obj:
                        player = obj["username"]
                except Exception:
                    pass

            self.player = Player(player)
            if not self.player:
                self.view_manager.log("Failed to create Player object", 2)
                # Failed to create Player object
                return False

        self.view_manager.log("Player object created successfully")

        # set sound/vibration toggle states
        self.player.sound_toggle = self.sound_toggle
        self.player.vibration_toggle = self.vibration_toggle

        self.view_manager.log("Adding levels and player...")

        # add levels and player to the game
        level_online = Level("Online", self.draw.size, game)

        # we'll clear ourselves and swap afterwards too
        level_online.clear_allowed = False

        level_online.entity_add(self.player)

        # Town (level 2) - 4 houses spread across the open map
        house1 = Sprite(
            "House 1",
            Vector(14, 13),
            SPRITE_3D_HOUSE,
            10.0,
            10.0,
            0.0,
            Vector(-1, -1),
            0x03EF,
        )
        house2 = Sprite(
            "House 2",
            Vector(48, 13),
            SPRITE_3D_HOUSE,
            10.0,
            10.0,
            pi / 2,
            Vector(-1, -1),
            0x03EF,
        )
        house3 = Sprite(
            "House 3",
            Vector(14, 43),
            SPRITE_3D_HOUSE,
            10.0,
            10.0,
            pi,
            Vector(-1, -1),
            0x03EF,
        )
        house4 = Sprite(
            "House 4",
            Vector(48, 43),
            SPRITE_3D_HOUSE,
            10.0,
            10.0,
            pi * 1.5,
            Vector(-1, -1),
            0x03EF,
        )
        level_online.entity_add(house1)
        level_online.entity_add(house2)
        level_online.entity_add(house3)
        level_online.entity_add(house4)

        # Forest (level 3) - trees scattered throughout the open map
        tree_positions = [
            Vector(8, 5),
            Vector(20, 5),
            Vector(40, 5),
            Vector(55, 5),
            Vector(5, 15),
            Vector(25, 12),
            Vector(38, 12),
            Vector(58, 15),
            Vector(5, 28),
            Vector(58, 28),
            Vector(5, 42),
            Vector(25, 45),
            Vector(38, 45),
            Vector(58, 42),
            Vector(8, 51),
            Vector(55, 51),
        ]
        tree_names = [
            "OTree 1",
            "OTree 2",
            "OTree 3",
            "OTree 4",
            "OTree 5",
            "OTree 6",
            "OTree 7",
            "OTree 8",
            "OTree 9",
            "OTree 10",
            "OTree 11",
            "OTree 12",
            "OTree 13",
            "OTree 14",
            "OTree 15",
            "OTree 16",
        ]
        for i in range(16):
            level_online.entity_add(
                Sprite(
                    tree_names[i],
                    tree_positions[i],
                    SPRITE_3D_TREE,
                    3.0,
                    1.0,
                    0.0,
                    Vector(-1, -1),
                    0x07E0,
                )
            )

        game.level_add(level_online)

        self.view_manager.log("Levels and player added to game successfully")

        self.engine = GameEngine(game, 240)
        if not self.engine:
            # Failed to create GameEngine
            self.view_manager.log("Failed to create GameEngine", 2)
            return False

        self.view_manager.log("GameEngine created successfully")
        self.view_manager.log("Starting Free Roam Game...")
        self.is_game_running = True  # Set the flag to indicate game is running
        return True

    def switch_to_level(self, level_index: int):
        """switch to a specific level by index"""
        if not self.is_game_running or not self.engine or not self.engine.game:
            return

        # Ensure the level index is within bounds
        if level_index < 0 or level_index >= self.total_levels:
            return
        self.current_level_index = level_index

        # Switch to the specified level using the engine's game instance
        self.engine.game.level_switch(self.current_level_index)

        # Force the Player to update its currentDynamicMap on next render
        if self.player:
            self.player.force_map_reload()

    def switch_to_next_level(self):
        """switch to the next level in the game"""
        if not self.is_game_running or not self.engine or not self.engine.game:
            return

        # Cycle to next level
        self.current_level_index = (self.current_level_index + 1) % self.total_levels

        # Switch to the new level using the engine's game instance
        self.engine.game.level_switch(self.current_level_index)

        # Force the Player to update its currentDynamicMap on next render
        if self.player:
            self.player.force_map_reload()

    def update_draw(self):
        """update and draw the game"""
        # Initialize player if not already done
        if not self.player:
            from free_roam.player import Player
            from json import loads as json_loads

            data: str = self.view_manager.storage.read(
                "picoware/flip_social/username.json"
            )
            player = "Player"
            if data is not None:
                try:
                    obj: dict = json_loads(data)
                    if "username" in obj:
                        player = obj["username"]
                except Exception:
                    pass

            self.player = Player(player)
            if self.player:
                self.player.free_roam_game = self
                self.player.sound_toggle = self.sound_toggle
                self.player.vibration_toggle = self.vibration_toggle

        # Let the player handle all drawing
        if self.player:
            self.player.draw_current_view(self.draw)

    def update_input(self, key: int):
        """update input for the game"""
        self.last_input = key

        # Only run input_manager when not in an active game to avoid input conflicts
        if not (
            self.player
            and self.player.current_main_view
            in (GAME_VIEW_GAME_LOCAL, GAME_VIEW_GAME_ONLINE)
            and self.is_game_running
        ):
            self.input_manager()
