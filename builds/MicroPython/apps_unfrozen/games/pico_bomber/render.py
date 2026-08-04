"""Low-allocation renderer for Pico Bomber."""

from utime import ticks_diff

from picoware.system.colors import (
    TFT_BLACK,
    TFT_CYAN,
    TFT_DARKGREY,
    TFT_GREEN,
    TFT_LIGHTGREY,
    TFT_MAGENTA,
    TFT_ORANGE,
    TFT_RED,
    TFT_WHITE,
    TFT_YELLOW,
)
from picoware.system.vector import Vector

from .model import (
    DECAL_BLOB,
    DECAL_BOMBER,
    DECAL_CHASER,
    DECAL_DEBRIS,
    DECAL_ELITE,
    DECAL_SCORCH,
    DEATH_ANIMATION_MS,
    DEATH_ENEMY_BLOB,
    DEATH_ENEMY_BOMBER,
    DEATH_ENEMY_CHASER,
    DEATH_ENEMY_ELITE,
    DEATH_PLAYER,
    ENEMY_BOMBER,
    ENEMY_KAMIKAZE,
    ENEMY_SLIME,
    ENEMY_SMALL_SLIME,
    ENEMY_TURRET,
    GRID_HEIGHT,
    GRID_WIDTH,
    MODE_BOMB_COURIER,
    MODE_HOT_POTATO,
    MODE_NAMES,
    MODE_TREASURE_HUNT,
    POSITION_SCALE,
    POWER_BOMB,
    POWER_FLAME_SUIT,
    POWER_LIFE,
    POWER_MAGNET,
    POWER_SHIELD,
    POWER_SPEED,
    SPIKE_ACTIVE_MS,
    SPIKE_CYCLE_MS,
    STATE_GAME_OVER,
    STATE_LEADERBOARD,
    STATE_MODE_SELECT,
    STATE_NAME_ENTRY,
    STATE_PAUSED,
    STATE_PLAYER_DYING,
    STATE_STAGE_CLEAR,
    STATE_STAGE_INTRO,
    STATE_TITLE,
    THEME_BEACH,
    THEME_CANYON,
    THEME_CLOUD,
    THEME_FOREST,
    THEME_HELL,
    THEME_INDUSTRIAL,
    THEME_NAMES,
    THEME_NATURE,
    THEME_WATER,
    TILE_BRICK,
    TILE_SOLID,
)


COLOR_ARENA = 0x0861
COLOR_SOLID_LIGHT = 0x6B4D
COLOR_PLAYER = 0x05FF
COLOR_PLAYER_DARK = 0x0372
COLOR_POWER = 0x7FE0
COLOR_VISOR = 0x867D

COLOR_GRASS = 0x1C84
COLOR_GRASS_LIGHT = 0x2E66
COLOR_MOSS = 0x3D86
COLOR_NATURE_STONE = 0x52AA
COLOR_WOOD = 0xA285
COLOR_WOOD_DARK = 0x6183

COLOR_FACTORY_FLOOR = 0x18C3
COLOR_FACTORY_SEAM = 0x2945
COLOR_STEEL = 0x630C
COLOR_STEEL_LIGHT = 0x8C51
COLOR_HAZARD = 0xD5A0

COLOR_WATER = 0x0452
COLOR_WATER_DARK = 0x02AB
COLOR_WAVE = 0x4E7F
COLOR_REEF = 0x39AA
COLOR_CORAL = 0xF3E0
COLOR_PURPLE = 0xA15C
COLOR_INK = 0x30A7
COLOR_COOLANT = 0x36DF
COLOR_RUST = 0xA2C2
COLOR_FOAM = 0xBFFF
COLOR_GOLD = 0xF5E0
COLOR_ENEMY_BLOB = 0xD81F
COLOR_ENEMY_CHASER = 0xFFE0
COLOR_DESTRUCTIBLE_EDGE = 0xFFE0
SPLASH_IMAGE_PATH = "picoware/apps/games/pico_bomber/picobomber.rgb332"
SPLASH_IMAGE_BYTES = 320 * 320
LEADERBOARD_MODE_LABELS = (
    "GHOST",
    "RIVALS",
    "TREASURE",
    "COURIER",
    "POTATO",
)

COLOR_SAND = 0xE6A4
COLOR_SAND_LIGHT = 0xFF0B
COLOR_SHELL = 0xFCD3
COLOR_BEACH_ROCK = 0x8C10
COLOR_PALM = 0x64A2

COLOR_BASALT = 0x20C2
COLOR_OBSIDIAN = 0x1822
COLOR_LAVA = 0xF940
COLOR_LAVA_LIGHT = 0xFDE0
COLOR_BRIMSTONE = 0xD4A0

COLOR_SKY = 0x65DF
COLOR_SKY_LIGHT = 0xA69F
COLOR_CLOUD = 0xEF7D
COLOR_CLOUD_SHADE = 0xBDF7
COLOR_STORM = 0x5AEB

COLOR_FOREST_FLOOR = 0x0B62
COLOR_FOREST_LIGHT = 0x25C4
COLOR_LEAF = 0x3545
COLOR_BARK = 0x71E3
COLOR_BARK_DARK = 0x38E1

COLOR_CANYON = 0xB282
COLOR_CANYON_LIGHT = 0xE3C7
COLOR_CANYON_DARK = 0x7902
COLOR_SANDSTONE = 0xD4A5
COLOR_DUST = 0xF5EA

PARTICLE_DIRECTIONS = (
    (-1, -1),
    (0, -1),
    (1, -1),
    (-1, 0),
    (1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
)


class Renderer:
    """Draw a complete Pico Bomber frame using the native LCD primitives."""

    def __init__(self, draw, storage=None):
        self.draw = draw
        self.storage = storage
        self.width = draw.size.x
        self.height = draw.size.y
        self.hud_height = 28 if self.height >= 160 else 14
        available_w = max(1, self.width - 4)
        available_h = max(1, self.height - self.hud_height - 4)
        self.cell = max(
            2,
            min(available_w // GRID_WIDTH, available_h // GRID_HEIGHT),
        )
        self.board_w = self.cell * GRID_WIDTH
        self.board_h = self.cell * GRID_HEIGHT
        self.origin_x = (self.width - self.board_w) // 2
        self.origin_y = self.hud_height + (
            self.height - self.hud_height - self.board_h
        ) // 2
        self.phase = 0
        self.tile_x = -1
        self.tile_y = -1
        self.item_index = -1

    def _center_text(self, text, y, color, font_size=1):
        width = self.draw.len(text, font_size)
        self.draw._text(max(0, (self.width - width) // 2), y, text, color, font_size)

    def _tile_box(self, x, y):
        return (
            self.origin_x + x * self.cell,
            self.origin_y + y * self.cell,
        )

    def _fixed_box(self, draw_x, draw_y):
        return (
            self.origin_x + draw_x * self.cell // POSITION_SCALE,
            self.origin_y + draw_y * self.cell // POSITION_SCALE,
        )

    def _draw_title(self):
        draw = self.draw
        draw.fill_screen(TFT_BLACK)
        if (
            self.storage
            and self.storage.exists(SPLASH_IMAGE_PATH)
            and self.storage.size(SPLASH_IMAGE_PATH) == SPLASH_IMAGE_BYTES
        ):
            # This is preconverted to the LCD's native RGB332 framebuffer
            # format. Avoid the multicore JPEG decoder here: it takes over
            # RP2350 core 1 outside MicroPython's thread/GC ownership and can
            # corrupt live bytecode long after the splash has finished.
            draw.image_bytearray_path(
                Vector(0, 0),
                Vector(320, 320),
                SPLASH_IMAGE_PATH,
                self.storage,
                chunk_size=SPLASH_IMAGE_BYTES,
            )
            return

        # Keep startup usable if the SD asset is missing or incomplete.
        draw.fill_screen(COLOR_ARENA)
        title_y = max(8, self.height // 7)
        self._center_text("PICO BOMBER", title_y, TFT_YELLOW, 3)

        cx = self.width // 2
        cy = self.height // 2
        radius = max(8, min(30, self.width // 12))
        draw._fill_circle(cx, cy, radius, TFT_BLACK)
        draw._circle(cx, cy, radius, TFT_LIGHTGREY)
        draw._fill_circle(cx - radius // 3, cy - radius // 3, max(2, radius // 5), TFT_WHITE)
        draw._line(cx + radius // 2, cy - radius // 2, cx + radius, cy - radius, TFT_ORANGE)
        draw._fill_circle(cx + radius, cy - radius, max(2, radius // 7), TFT_YELLOW)

        controls_y = min(self.height - 52, cy + radius + 24)
        self._center_text("ARROWS  MOVE", controls_y, TFT_CYAN)
        self._center_text("CENTER/SPACE  BOMB", controls_y + 16, TFT_WHITE)
        self._center_text("PRESS CENTER", min(self.height - 16, controls_y + 38), TFT_GREEN)

    def _draw_mode_menu(self, game):
        draw = self.draw
        draw.fill_screen(COLOR_ARENA)
        title_y = 10 if self.height >= 160 else 4
        self._center_text("CHOOSE MODE", title_y, TFT_YELLOW, 2)
        self._center_text(
            "UP/DOWN MODE  LEFT/RIGHT MUSIC",
            title_y + (26 if self.height >= 160 else 18),
            TFT_CYAN,
            0,
        )

        compact = self.height < 200
        gap = 2 if compact else 3
        top = title_y + (38 if compact else 50)
        box_w = min(self.width - 24, 270)
        x = (self.width - box_w) // 2
        items = MODE_NAMES + ("LEADERBOARD",)
        descriptions = (
            "DEFEAT EVERY CREATURE",
            "ENEMY BOMBERS PLACE BOMBS TOO",
            "BREAK BLOCKS, COLLECT ALL TREASURE",
            "DELIVER THE BOMB BEFORE IT BLOWS",
            "TOUCH ENEMIES TO PASS THE LIVE BOMB",
            "VIEW THE FIVE BEST LOCAL SCORES",
        )
        colors = (
            COLOR_PURPLE,
            TFT_RED,
            COLOR_GOLD,
            TFT_ORANGE,
            TFT_MAGENTA,
            TFT_GREEN,
        )
        bottom_reserved = 18 if compact else 74
        card_h = max(
            10 if compact else 17,
            (
                self.height
                - top
                - bottom_reserved
                - gap * (len(items) - 1)
            )
            // len(items),
        )
        for index in range(len(items)):
            y = top + index * (card_h + gap)
            selected = index == game.menu_selection
            border = TFT_YELLOW if selected else TFT_DARKGREY
            draw._fill_rectangle(
                x,
                y,
                box_w,
                card_h,
                TFT_BLACK if selected else COLOR_FACTORY_FLOOR,
            )
            draw._rectangle(x, y, box_w, card_h, border)
            marker = ">" if selected else " "
            draw._text(
                x + 10,
                y + max(2, (card_h - 8) // 2),
                marker + " " + items[index],
                colors[index],
                0 if card_h < 28 else 1,
            )
        selected_description = descriptions[game.menu_selection]
        if compact:
            self._center_text(
                selected_description,
                self.height - 12,
                TFT_WHITE,
                0,
            )
        else:
            self._center_text(
                selected_description,
                self.height - 62,
                TFT_WHITE,
                0,
            )
            self._center_text(
                "<  MUSIC %d/5: %s  >"
                % (
                    getattr(game, "music_selection", 0) + 1,
                    getattr(game, "music_name", "NEON FUSE"),
                ),
                self.height - 46,
                TFT_CYAN,
                0,
            )
            self._center_text(
                "DEMO IN %02d" % game.demo_countdown,
                self.height - 30,
                TFT_MAGENTA,
                0,
            )
            self._center_text("BACK  EXIT", self.height - 16, TFT_LIGHTGREY, 0)

    def _draw_leaderboard(self, game):
        draw = self.draw
        draw.fill_screen(COLOR_ARENA)
        compact = self.height < 240
        self._center_text(
            "LEADERBOARD",
            4 if compact else 10,
            TFT_YELLOW,
            1 if compact else 2,
        )
        self._center_text("LOCAL TOP 5", 20 if compact else 37, TFT_CYAN, 0)
        box_w = min(self.width - (12 if compact else 24), 286)
        x = (self.width - box_w) // 2
        top = 34 if compact else 58
        gap = 2 if compact else 4
        row_h = (
            max(12, (self.height - top - 20 - gap * 4) // 5)
            if compact
            else 36
        )
        entries = game.leaderboard
        if not entries:
            self._center_text(
                "NO SCORES YET",
                self.height // 2 - 8,
                TFT_WHITE,
                0 if compact else 1,
            )
            self._center_text("FINISH A RUN TO SAVE", self.height // 2 + 14, TFT_LIGHTGREY, 0)
        else:
            for index in range(min(5, len(entries))):
                entry = entries[index]
                y = top + index * (row_h + gap)
                draw._fill_rectangle(x, y, box_w, row_h, TFT_BLACK)
                draw._rectangle(
                    x,
                    y,
                    box_w,
                    row_h,
                    TFT_YELLOW if index == 0 else TFT_DARKGREY,
                )
                mode = (
                    LEADERBOARD_MODE_LABELS[entry[2]]
                    if 0 <= entry[2] < len(LEADERBOARD_MODE_LABELS)
                    else "MODE"
                )
                name = entry[3] if len(entry) >= 4 else "PLAYER"
                if compact:
                    text_y = y + max(2, (row_h - 8) // 2)
                    left = "#%d %s" % (index + 1, name[:5])
                    draw._text(x + 5, text_y, left, TFT_YELLOW, 0)
                    score = str(entry[0])
                    draw._text(
                        x + box_w - draw.len(score, 0) - 5,
                        text_y,
                        score,
                        TFT_WHITE,
                        0,
                    )
                else:
                    draw._text(x + 8, y + 8, "#%d" % (index + 1), TFT_YELLOW, 1)
                    draw._text(x + 42, y + 4, name, TFT_CYAN, 0)
                    draw._text(
                        x + 42,
                        y + 17,
                        "%06d" % entry[0],
                        TFT_WHITE,
                        0,
                    )
                    draw._text(x + 150, y + 5, mode, TFT_CYAN, 0)
                    draw._text(
                        x + 150,
                        y + 19,
                        "STAGE %d" % entry[1],
                        TFT_GREEN,
                        0,
                    )
        self._center_text(
            "CENTER/BACK  MODES",
            self.height - 16,
            TFT_LIGHTGREY,
            0,
        )

    def _draw_name_entry(self, game):
        draw = self.draw
        draw.fill_screen(COLOR_ARENA)
        compact = self.height < 200
        self._center_text(
            "NEW HIGH SCORE",
            8 if compact else 22,
            TFT_YELLOW,
            1 if compact else 2,
        )
        self._center_text(
            "%06d  STAGE %d" % (game.score, game.stage),
            30 if compact else 62,
            TFT_CYAN,
            0 if compact else 1,
        )
        self._center_text(
            "ENTER YOUR NAME",
            48 if compact else 96,
            TFT_WHITE,
            0 if compact else 1,
        )

        box_w = min(self.width - 24, 260)
        box_h = 32 if compact else 54
        x = (self.width - box_w) // 2
        y = 65 if compact else 128
        draw._fill_rectangle(x, y, box_w, box_h, TFT_BLACK)
        draw._rectangle(x, y, box_w, box_h, TFT_YELLOW)
        name = game.player_name
        display_name = name + ("_" if len(name) < 10 else "")
        if not display_name:
            display_name = "_"
        text_size = 1 if compact else 2
        text_x = max(x + 6, x + (box_w - draw.len(display_name, text_size)) // 2)
        text_y = y + (8 if compact else 14)
        draw._text(text_x, text_y, display_name, TFT_GREEN, text_size)

        self._center_text(
            "TYPE A-Z / 0-9  BACK ERASE",
            min(self.height - 34, y + box_h + 18),
            TFT_LIGHTGREY,
            0,
        )
        self._center_text(
            "ENTER SAVE  EMPTY = PLAYER",
            min(self.height - 16, y + box_h + 36),
            TFT_CYAN,
            0,
        )

    @staticmethod
    def _theme_color(theme):
        if theme in (THEME_NATURE, THEME_FOREST):
            return TFT_GREEN
        if theme in (THEME_INDUSTRIAL, THEME_CLOUD):
            return TFT_YELLOW
        if theme == THEME_WATER:
            return TFT_CYAN
        if theme == THEME_BEACH:
            return COLOR_SAND_LIGHT
        if theme == THEME_HELL:
            return COLOR_LAVA_LIGHT
        return COLOR_DUST

    @staticmethod
    def _theme_background(theme):
        if theme == THEME_NATURE:
            return COLOR_GRASS
        if theme == THEME_INDUSTRIAL:
            return COLOR_FACTORY_FLOOR
        if theme == THEME_WATER:
            return COLOR_WATER_DARK
        if theme == THEME_BEACH:
            return COLOR_SAND
        if theme == THEME_HELL:
            return COLOR_BASALT
        if theme == THEME_CLOUD:
            return COLOR_SKY
        if theme == THEME_FOREST:
            return COLOR_FOREST_FLOOR
        return COLOR_CANYON

    def _draw_hud(self, game):
        draw = self.draw
        draw._fill_rectangle(0, 0, self.width, self.hud_height, TFT_BLACK)
        if self.height < 160:
            text = "%sS%d L%d B%d F%d %d" % (
                "D " if game.demo_mode else "",
                game.stage,
                game.lives,
                game.bombs_available(),
                game.flame_range,
                game.score,
            )
            draw._text(2, 2, text, TFT_WHITE, 0)
            return

        draw._text(4, 4, "PICO BOMBER", TFT_YELLOW, 1)
        if game.demo_mode:
            demo_text = "DEMO"
            demo_x = (self.width - draw.len(demo_text, 1)) // 2
            draw._text(demo_x, 4, demo_text, TFT_MAGENTA, 1)
        status = "S:%d L:%d B:%d F:%d" % (
            game.stage,
            game.lives,
            game.bombs_available(),
            game.flame_range,
        )
        status_x = max(4, self.width - draw.len(status, 0) - 4)
        draw._text(status_x, 3, status, TFT_CYAN, 0)
        score_text = "%06d" % game.score
        score_x = max(4, self.width - draw.len(score_text, 0) - 4)
        draw._text(score_x, 15, score_text, TFT_WHITE, 0)
        draw._text(
            4,
            15,
            THEME_NAMES[game.theme],
            self._theme_color(game.theme),
            0,
        )
        effect_x = 112
        objective = None
        if game.mode == MODE_TREASURE_HUNT:
            remaining = max(
                0,
                (ticks_diff(game.objective_until, game.animation_time) + 999)
                // 1000,
            )
            objective = "T:%d/%d %d" % (
                game.treasure_collected,
                game.treasure_target,
                remaining,
            )
        elif game.mode == MODE_BOMB_COURIER:
            if game.courier_carrying:
                remaining = max(
                    0,
                    (
                        ticks_diff(
                            game.courier_fuse_until,
                            game.animation_time,
                        )
                        + 999
                    )
                    // 1000,
                )
                objective = "DELIVER %d" % remaining
            else:
                objective = "GET BOMB"
        elif game.mode == MODE_HOT_POTATO:
            remaining = max(
                0,
                (ticks_diff(game.hot_potato_until, game.animation_time) + 999)
                // 1000,
            )
            objective = "PASS %d" % remaining
        if objective is not None:
            draw._text(effect_x, 15, objective, TFT_YELLOW, 0)
            effect_x += draw.len(objective, 0) + 6
        if ticks_diff(game.magnet_until, game.animation_time) > 0:
            draw._text(effect_x, 15, "M", TFT_MAGENTA, 0)
            effect_x += 10
        if ticks_diff(game.flame_suit_until, game.animation_time) > 0:
            draw._text(effect_x, 15, "F", TFT_ORANGE, 0)
            effect_x += 10
        if ticks_diff(game.speed_until, game.animation_time) > 0:
            draw._text(effect_x, 15, ">", TFT_GREEN, 0)
            effect_x += 10
        if game.shield_hits > 0:
            draw._text(effect_x, 15, "S", TFT_CYAN, 0)
        if game.demo_mode:
            exit_text = "ANY KEY EXITS"
            exit_x = (self.width - draw.len(exit_text, 0)) // 2
            draw._text(exit_x, 15, exit_text, TFT_LIGHTGREY, 0)

    def _draw_floor(self, px, py, x, y, theme, animation_time):
        inset = 1 if self.cell >= 5 else 0
        # Most floors match the full-frame background. Water uses a lighter
        # inner tile so the moving ripples remain readable.
        if theme == THEME_WATER:
            self.draw._fill_rectangle(
                px + inset,
                py + inset,
                self.cell - inset,
                self.cell - inset,
                COLOR_WATER,
            )

        if self.cell < 8:
            return
        if theme == THEME_NATURE:
            seed = (x * 7 + y * 11) % max(2, self.cell - 4)
            sway = (animation_time // 260 + x + y) % 3 - 1
            self.draw._fill_rectangle(
                px + 2 + seed + sway,
                py + 3 + (seed % 3),
                2,
                2,
                COLOR_GRASS_LIGHT,
            )
            if (x * 5 + y * 3) % 17 == 0:
                flower_x = px + self.cell - 5
                flower_y = py + self.cell - 5
                self.draw._fill_rectangle(
                    flower_x,
                    flower_y,
                    2,
                    2,
                    TFT_YELLOW if (x + y) % 2 else TFT_WHITE,
                )
                self.draw._fill_rectangle(
                    flower_x,
                    flower_y + 2,
                    1,
                    2,
                    COLOR_MOSS,
                )
        elif theme == THEME_INDUSTRIAL:
            self.draw._rectangle(
                px + 2,
                py + 2,
                self.cell - 5,
                self.cell - 5,
                COLOR_FACTORY_SEAM,
            )
            self.draw._fill_rectangle(px + 3, py + 3, 1, 1, TFT_LIGHTGREY)
            if (x * 3 + y * 7) % 19 == 0:
                pipe_y = py + self.cell - 5
                self.draw._line(
                    px + 3,
                    pipe_y,
                    px + self.cell - 4,
                    pipe_y,
                    COLOR_STEEL_LIGHT,
                )
                self.draw._fill_rectangle(
                    px + self.cell - 5,
                    pipe_y - 2,
                    2,
                    2,
                    TFT_RED
                    if (animation_time // 240 + x + y) % 2
                    else TFT_YELLOW,
                )
            belt_x = px + 3 + (
                animation_time // 170 + x * 2 + y
            ) % max(2, self.cell - 7)
            self.draw._fill_rectangle(
                belt_x,
                py + self.cell // 2,
                2,
                2,
                COLOR_STEEL_LIGHT,
            )
        elif theme == THEME_WATER:
            wave_y = py + 4 + (
                animation_time // 180 + x * 2 + y
            ) % max(2, self.cell - 8)
            self.draw._line(
                px + 2,
                wave_y,
                px + max(3, self.cell // 2),
                wave_y,
                COLOR_WAVE,
            )
            self.draw._line(
                px + self.cell // 2,
                wave_y + 3,
                px + self.cell - 3,
                wave_y + 3,
                COLOR_WATER_DARK,
            )
            if (x * 11 + y * 5) % 23 == 0:
                bubble_x = px + self.cell - 5
                bubble_y = py + 3
                self.draw._circle(bubble_x, bubble_y, 2, COLOR_FOAM)
        elif theme == THEME_BEACH:
            grain = (x * 5 + y * 9) % max(2, self.cell - 5)
            self.draw._fill_rectangle(
                px + 2 + grain,
                py + 3 + (grain % 4),
                2,
                1,
                COLOR_SAND_LIGHT,
            )
            if (x * 7 + y * 13) % 19 == 0:
                shell_x = px + self.cell - 6
                shell_y = py + self.cell - 5
                self.draw._circle(shell_x, shell_y, 2, COLOR_SHELL)
                self.draw._line(
                    shell_x - 1,
                    shell_y,
                    shell_x + 1,
                    shell_y,
                    COLOR_CORAL,
                )
        elif theme == THEME_HELL:
            pulse = (animation_time // 190 + x + y) % 3
            crack = (
                x * 7 + y * 5 + pulse
            ) % max(3, self.cell - 6)
            self.draw._line(
                px + 2,
                py + 3 + crack,
                px + self.cell // 2,
                py + 2 + crack,
                COLOR_LAVA_LIGHT if pulse == 2 else COLOR_LAVA,
            )
            if (x * 11 + y * 3) % 17 == 0:
                self.draw._fill_rectangle(
                    px + self.cell - 5,
                    py + 3,
                    2,
                    2,
                    COLOR_LAVA_LIGHT,
                )
        elif theme == THEME_CLOUD:
            drift = (
                animation_time // 240 + x * 3 + y * 2
            ) % max(2, self.cell - 7)
            self.draw._line(
                px + 2 + drift,
                py + 4,
                px + min(self.cell - 3, 6 + drift),
                py + 4,
                COLOR_SKY_LIGHT,
            )
            if (x * 13 + y * 5) % 23 == 0:
                self.draw._fill_circle(
                    px + self.cell - 5,
                    py + self.cell - 5,
                    2,
                    COLOR_CLOUD,
                )
        elif theme == THEME_FOREST:
            leaf_x = px + 2 + (x * 7 + y * 3) % max(2, self.cell - 5)
            leaf_y = py + 2 + (x * 3 + y * 5) % max(2, self.cell - 5)
            self.draw._fill_rectangle(
                leaf_x,
                leaf_y,
                2,
                2,
                COLOR_FOREST_LIGHT if (x + y) % 2 else COLOR_LEAF,
            )
            if (x * 5 + y * 11) % 29 == 0:
                self.draw._line(
                    px + 3,
                    py + self.cell - 4,
                    px + self.cell - 4,
                    py + 3,
                    COLOR_BARK_DARK,
                )
        else:
            stratum = py + 3 + (x * 3 + y * 7) % max(2, self.cell - 7)
            self.draw._line(
                px + 2,
                stratum,
                px + self.cell - 3,
                stratum,
                COLOR_CANYON_LIGHT,
            )
            if (x * 11 + y * 7) % 19 == 0:
                self.draw._fill_rectangle(
                    px + self.cell - 5,
                    py + self.cell - 5,
                    2,
                    2,
                    COLOR_DUST,
                )

    def _draw_solid(self, px, py, x, y, theme):
        if theme == THEME_NATURE:
            self.draw._fill_rectangle(
                px,
                py,
                self.cell,
                self.cell,
                COLOR_NATURE_STONE,
            )
            if self.cell >= 7:
                self.draw._rectangle(
                    px + 2,
                    py + 2,
                    self.cell - 5,
                    self.cell - 5,
                    COLOR_SOLID_LIGHT,
                )
                self.draw._fill_rectangle(
                    px + 1,
                    py + 1,
                    max(2, self.cell // 2),
                    2,
                    COLOR_MOSS,
                )
        elif theme == THEME_INDUSTRIAL:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_STEEL)
            if self.cell >= 7:
                self.draw._rectangle(
                    px + 2,
                    py + 2,
                    self.cell - 5,
                    self.cell - 5,
                    COLOR_STEEL_LIGHT,
                )
                rivet = max(1, self.cell // 10)
                self.draw._fill_rectangle(px + 3, py + 3, rivet, rivet, TFT_WHITE)
                self.draw._fill_rectangle(
                    px + self.cell - 4 - rivet,
                    py + self.cell - 4 - rivet,
                    rivet,
                    rivet,
                    TFT_DARKGREY,
                )
        elif theme == THEME_WATER:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_WATER_DARK)
            if self.cell >= 7:
                self.draw._fill_rectangle(
                    px + 2,
                    py + 3,
                    self.cell - 4,
                    self.cell - 6,
                    COLOR_REEF,
                )
                self.draw._line(
                    px + 3,
                    py + 4,
                    px + self.cell - 4,
                    py + 4,
                    COLOR_WAVE,
                )
                if (x + y) % 3 == 0:
                    self.draw._circle(
                        px + self.cell - 5,
                        py + self.cell // 2,
                        2,
                        TFT_CYAN,
                    )
        elif theme == THEME_BEACH:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_BEACH_ROCK)
            if self.cell >= 7:
                self.draw._fill_rectangle(
                    px + 2,
                    py + 3,
                    self.cell - 4,
                    self.cell - 6,
                    COLOR_SANDSTONE,
                )
                self.draw._line(
                    px + 2,
                    py + 3,
                    px + self.cell - 3,
                    py + 3,
                    COLOR_FOAM,
                )
                self.draw._fill_rectangle(
                    px + 3,
                    py + self.cell - 5,
                    3,
                    2,
                    COLOR_SHELL,
                )
        elif theme == THEME_HELL:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_OBSIDIAN)
            if self.cell >= 7:
                self.draw._rectangle(
                    px + 2,
                    py + 2,
                    self.cell - 5,
                    self.cell - 5,
                    COLOR_BASALT,
                )
                self.draw._line(
                    px + 3,
                    py + self.cell - 4,
                    px + self.cell // 2,
                    py + self.cell // 2,
                    COLOR_LAVA,
                )
                self.draw._line(
                    px + self.cell // 2,
                    py + self.cell // 2,
                    px + self.cell - 4,
                    py + 3,
                    COLOR_LAVA_LIGHT,
                )
        elif theme == THEME_CLOUD:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_CLOUD_SHADE)
            if self.cell >= 7:
                radius = max(2, self.cell // 4)
                self.draw._fill_circle(
                    px + self.cell // 3,
                    py + self.cell // 2,
                    radius,
                    COLOR_CLOUD,
                )
                self.draw._fill_circle(
                    px + self.cell * 2 // 3,
                    py + self.cell // 2,
                    radius,
                    TFT_WHITE,
                )
                self.draw._line(
                    px + 3,
                    py + self.cell - 4,
                    px + self.cell - 4,
                    py + self.cell - 4,
                    COLOR_SKY_LIGHT,
                )
        elif theme == THEME_FOREST:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_BARK_DARK)
            if self.cell >= 7:
                self.draw._fill_rectangle(
                    px + 2,
                    py + 2,
                    self.cell - 4,
                    self.cell - 4,
                    COLOR_LEAF,
                )
                self.draw._rectangle(
                    px + 3,
                    py + 3,
                    self.cell - 7,
                    self.cell - 7,
                    COLOR_FOREST_LIGHT,
                )
                self.draw._fill_rectangle(
                    px + 2,
                    py + 2,
                    max(2, self.cell // 2),
                    2,
                    COLOR_MOSS,
                )
        else:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_CANYON_DARK)
            if self.cell >= 7:
                self.draw._fill_rectangle(
                    px + 2,
                    py + 2,
                    self.cell - 4,
                    self.cell - 4,
                    COLOR_SANDSTONE,
                )
                self.draw._line(
                    px + 2,
                    py + self.cell // 3,
                    px + self.cell - 3,
                    py + self.cell // 3,
                    COLOR_CANYON_LIGHT,
                )
                self.draw._line(
                    px + 3,
                    py + self.cell * 2 // 3,
                    px + self.cell - 4,
                    py + self.cell * 2 // 3,
                    COLOR_CANYON,
                )
        # Permanent walls always have a dark, unbroken boundary. This semantic
        # edge stays recognizable even when a themed fill is close in value to
        # the floor or to a destructible block.
        self.draw._rectangle(
            px,
            py,
            self.cell,
            self.cell,
            TFT_BLACK,
        )

    def _draw_brick(self, px, py, x, y, theme):
        if theme == THEME_NATURE:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_WOOD)
            if self.cell >= 6:
                self.draw._rectangle(
                    px + 2,
                    py + 2,
                    self.cell - 5,
                    self.cell - 5,
                    COLOR_WOOD_DARK,
                )
                self.draw._line(
                    px + 3,
                    py + 3,
                    px + self.cell - 4,
                    py + self.cell - 4,
                    COLOR_WOOD_DARK,
                )
                self.draw._line(
                    px + self.cell - 4,
                    py + 3,
                    px + 3,
                    py + self.cell - 4,
                    COLOR_WOOD_DARK,
                )
        elif theme == THEME_INDUSTRIAL:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_STEEL)
            if self.cell >= 6:
                band = max(2, self.cell // 7)
                self.draw._fill_rectangle(
                    px + 2,
                    py + band + 1,
                    self.cell - 4,
                    self.cell - band * 2 - 2,
                    COLOR_FACTORY_SEAM,
                )
                self.draw._fill_rectangle(px, py, self.cell, band, COLOR_HAZARD)
                self.draw._fill_rectangle(
                    px,
                    py + self.cell - band,
                    self.cell,
                    band,
                    COLOR_HAZARD,
                )
                stripe = max(2, self.cell // 5)
                self.draw._fill_rectangle(
                    px + 3,
                    py,
                    stripe,
                    band,
                    TFT_BLACK,
                )
                self.draw._fill_rectangle(
                    px + self.cell - stripe - 3,
                    py + self.cell - band,
                    stripe,
                    band,
                    TFT_BLACK,
                )
                self.draw._rectangle(
                    px + 1,
                    py + 1,
                    self.cell - 3,
                    self.cell - 3,
                    TFT_DARKGREY,
                )
        elif theme == THEME_WATER:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_WATER)
            if self.cell >= 6:
                center = px + self.cell // 2
                base = py + self.cell - 3
                self.draw._fill_rectangle(
                    center - 2,
                    py + 4,
                    4,
                    self.cell - 7,
                    COLOR_CORAL,
                )
                self.draw._fill_rectangle(
                    px + 4,
                    py + self.cell // 2,
                    self.cell - 8,
                    4,
                    COLOR_CORAL,
                )
                branch = 2 if (x + y) % 2 else -2
                self.draw._line(
                    center,
                    py + self.cell // 2,
                    center + branch,
                    py + 3,
                    TFT_ORANGE,
                )
                self.draw._line(
                    px + 3,
                    base,
                    px + self.cell - 4,
                    base,
                    COLOR_REEF,
                )
        elif theme == THEME_BEACH:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_PALM)
            if self.cell >= 6:
                self.draw._rectangle(
                    px + 2,
                    py + 2,
                    self.cell - 5,
                    self.cell - 5,
                    COLOR_BARK_DARK,
                )
                self.draw._line(
                    px + 3,
                    py + 3,
                    px + self.cell - 4,
                    py + self.cell - 4,
                    COLOR_SAND_LIGHT,
                )
                self.draw._fill_rectangle(
                    px + self.cell // 2 - 1,
                    py + 2,
                    2,
                    self.cell - 4,
                    COLOR_BARK,
                )
        elif theme == THEME_HELL:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_BRIMSTONE)
            if self.cell >= 6:
                self.draw._fill_rectangle(
                    px + 2,
                    py + 2,
                    self.cell - 4,
                    self.cell - 4,
                    COLOR_BASALT,
                )
                self.draw._line(
                    px + 3,
                    py + 3,
                    px + self.cell - 4,
                    py + self.cell - 4,
                    COLOR_LAVA,
                )
                self.draw._line(
                    px + self.cell - 4,
                    py + 3,
                    px + 3,
                    py + self.cell - 4,
                    COLOR_LAVA_LIGHT,
                )
        elif theme == THEME_CLOUD:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_STORM)
            if self.cell >= 6:
                self.draw._fill_circle(
                    px + self.cell // 3,
                    py + self.cell // 3,
                    max(2, self.cell // 4),
                    COLOR_CLOUD_SHADE,
                )
                self.draw._fill_circle(
                    px + self.cell * 2 // 3,
                    py + self.cell // 3,
                    max(2, self.cell // 4),
                    COLOR_CLOUD,
                )
                bolt_x = px + self.cell // 2
                self.draw._line(
                    bolt_x,
                    py + self.cell // 2,
                    bolt_x - 2,
                    py + self.cell - 4,
                    TFT_YELLOW,
                )
                self.draw._line(
                    bolt_x - 2,
                    py + self.cell - 4,
                    bolt_x + 3,
                    py + self.cell - 6,
                    TFT_YELLOW,
                )
        elif theme == THEME_FOREST:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_BARK)
            if self.cell >= 6:
                self.draw._rectangle(
                    px + 2,
                    py + 2,
                    self.cell - 5,
                    self.cell - 5,
                    COLOR_BARK_DARK,
                )
                self.draw._line(
                    px + self.cell // 3,
                    py + 2,
                    px + self.cell // 3,
                    py + self.cell - 3,
                    COLOR_FOREST_LIGHT,
                )
                self.draw._line(
                    px + self.cell * 2 // 3,
                    py + 2,
                    px + self.cell * 2 // 3,
                    py + self.cell - 3,
                    COLOR_BARK_DARK,
                )
        else:
            self.draw._fill_rectangle(px, py, self.cell, self.cell, COLOR_CANYON_LIGHT)
            if self.cell >= 6:
                self.draw._fill_rectangle(
                    px + 2,
                    py + 2,
                    self.cell - 4,
                    self.cell - 4,
                    COLOR_CANYON,
                )
                self.draw._line(
                    px + 2,
                    py + self.cell // 3,
                    px + self.cell - 3,
                    py + self.cell // 3,
                    COLOR_DUST,
                )
                self.draw._line(
                    px + self.cell // 2,
                    py + self.cell // 3,
                    px + self.cell - 4,
                    py + self.cell - 4,
                    COLOR_CANYON_DARK,
                )
        # Destructible blocks use one bright boundary in every theme. Keeping
        # this gameplay cue stable prevents Hell, Cloud, and future palettes
        # from making breakable blocks look like permanent walls.
        self.draw._rectangle(
            px,
            py,
            self.cell,
            self.cell,
            COLOR_DESTRUCTIBLE_EDGE,
        )

    def _draw_powerup(self, powerup):
        px, py = self._tile_box(powerup[0], powerup[1])
        pad = max(2, self.cell // 5)
        kind = powerup[2]
        is_life = kind == POWER_LIFE
        background = (
            TFT_WHITE
            if is_life
            else TFT_RED
            if kind == POWER_MAGNET
            else TFT_ORANGE
            if kind == POWER_FLAME_SUIT
            else TFT_GREEN
            if kind == POWER_SPEED
            else TFT_CYAN
            if kind == POWER_SHIELD
            else COLOR_POWER
        )
        self.draw._fill_rectangle(
            px + pad,
            py + pad,
            self.cell - pad * 2,
            self.cell - pad * 2,
            background,
        )
        if is_life:
            cx = px + self.cell // 2
            top = py + pad + max(1, self.cell // 8)
            radius = max(1, (self.cell - pad * 2) // 5)
            self.draw._fill_circle(cx - radius, top + radius, radius, TFT_RED)
            self.draw._fill_circle(cx + radius, top + radius, radius, TFT_RED)
            point_y = min(py + self.cell - pad - 1, top + radius * 4)
            body_top = top + radius
            body_height = max(1, point_y - body_top)
            for row in range(body_height + 1):
                half_width = radius * 2 * (body_height - row) // body_height
                self.draw._line(
                    cx - half_width,
                    body_top + row,
                    cx + half_width,
                    body_top + row,
                    TFT_RED,
                )
            return
        cx = px + self.cell // 2
        cy = py + self.cell // 2
        radius = max(2, (self.cell - pad * 2) // 3)
        if kind == POWER_MAGNET:
            self.draw._line(cx - radius, cy - radius, cx - radius, cy + radius, TFT_WHITE)
            self.draw._line(cx + radius, cy - radius, cx + radius, cy + radius, TFT_WHITE)
            self.draw._line(cx - radius, cy + radius, cx + radius, cy + radius, TFT_WHITE)
            self.draw._fill_rectangle(cx - radius - 1, cy - radius, 3, 3, TFT_CYAN)
            self.draw._fill_rectangle(cx + radius - 1, cy - radius, 3, 3, TFT_CYAN)
            return
        if kind == POWER_FLAME_SUIT:
            self.draw._fill_circle(cx, cy + 2, radius, TFT_YELLOW)
            self.draw._line(cx, cy - radius - 2, cx - radius, cy + 2, TFT_WHITE)
            self.draw._line(cx, cy - radius - 2, cx + radius, cy + 2, TFT_WHITE)
            return
        if kind == POWER_SPEED:
            self.draw._line(cx - radius, cy - radius, cx + radius, cy, TFT_WHITE)
            self.draw._line(cx + radius, cy, cx - radius, cy + radius, TFT_WHITE)
            self.draw._line(cx - radius - 2, cy, cx + radius - 2, cy, TFT_WHITE)
            return
        if kind == POWER_SHIELD:
            self.draw._circle(cx, cy, radius + 1, TFT_WHITE)
            self.draw._line(cx - radius, cy - 1, cx, cy + radius + 1, TFT_WHITE)
            self.draw._line(cx + radius, cy - 1, cx, cy + radius + 1, TFT_WHITE)
            return
        if self.cell >= 12:
            label = "B" if kind == POWER_BOMB else "F"
            tx = px + (self.cell - self.draw.len(label, 0)) // 2
            ty = py + (self.cell - 8) // 2
            self.draw._text(tx, ty, label, TFT_BLACK, 0)

    def _draw_bomb(self, bomb, animation_time, theme):
        px, py = self._tile_box(bomb[0], bomb[1])
        cx = px + self.cell // 2
        cy = py + self.cell // 2 + 1
        frame = (animation_time // 120) % 4
        radius = max(1, self.cell // 3 + (1 if frame in (1, 2) else 0))
        enemy_bomb = len(bomb) >= 5 and bomb[4] == 1
        bomb_kind = bomb[5] if len(bomb) >= 6 else 0
        if bomb_kind:
            body_color = COLOR_RUST
            accent = TFT_YELLOW
        elif enemy_bomb:
            body_color = TFT_BLACK
            accent = TFT_RED
        elif theme == THEME_NATURE:
            body_color, accent = COLOR_WOOD_DARK, COLOR_MOSS
        elif theme == THEME_INDUSTRIAL:
            body_color, accent = COLOR_STEEL, COLOR_HAZARD
        elif theme == THEME_WATER:
            body_color, accent = COLOR_PURPLE, COLOR_FOAM
        elif theme == THEME_BEACH:
            body_color, accent = COLOR_CORAL, COLOR_SAND_LIGHT
        elif theme == THEME_HELL:
            body_color, accent = COLOR_OBSIDIAN, COLOR_LAVA_LIGHT
        elif theme == THEME_CLOUD:
            body_color, accent = COLOR_STORM, TFT_YELLOW
        elif theme == THEME_FOREST:
            body_color, accent = COLOR_BARK_DARK, COLOR_LEAF
        else:
            body_color, accent = COLOR_RUST, COLOR_DUST
        self.draw._fill_circle(cx, cy, radius, body_color)
        if self.cell >= 8:
            self.draw._circle(
                cx,
                cy,
                radius,
                accent,
            )
            self.draw._fill_circle(
                cx - max(1, radius // 3),
                cy - max(1, radius // 3),
                max(1, radius // 4),
                TFT_WHITE,
            )
            self.draw._line(cx + radius // 2, cy - radius, cx + radius, cy - radius - 3, TFT_ORANGE)
            spark_x = cx + radius + (frame % 2)
            spark_y = cy - radius - 3 - (frame // 2)
            self.draw._fill_rectangle(
                spark_x,
                spark_y,
                2,
                2,
                TFT_RED if enemy_bomb else accent,
            )

    def _draw_barrel(self, barrel):
        px, py = self._tile_box(barrel[0], barrel[1])
        pad = max(2, self.cell // 6)
        self.draw._fill_rectangle(
            px + pad,
            py + 2,
            self.cell - pad * 2,
            self.cell - 4,
            COLOR_RUST,
        )
        self.draw._rectangle(
            px + pad,
            py + 2,
            self.cell - pad * 2,
            self.cell - 4,
            TFT_BLACK,
        )
        self.draw._line(px + pad, py + 6, px + self.cell - pad, py + 6, TFT_YELLOW)
        self.draw._line(
            px + pad,
            py + self.cell - 6,
            px + self.cell - pad,
            py + self.cell - 6,
            TFT_YELLOW,
        )
        if self.cell >= 12:
            self.draw._text(px + self.cell // 2 - 3, py + self.cell // 2 - 4, "!", TFT_WHITE, 0)

    def _draw_teleporter(self, pad, animation_time):
        px, py = self._tile_box(pad[0], pad[1])
        cx = px + self.cell // 2
        cy = py + self.cell // 2
        pulse = (animation_time // 140) % 3
        radius = max(2, self.cell // 3 - pulse)
        self.draw._circle(cx, cy, radius + 2, TFT_MAGENTA)
        self.draw._circle(cx, cy, radius, TFT_CYAN)
        self.draw._fill_circle(cx, cy, max(1, radius // 3), TFT_WHITE)

    def _draw_spike_trap(self, trap, animation_time):
        px, py = self._tile_box(trap[0], trap[1])
        active = (
            (animation_time + trap[2]) % SPIKE_CYCLE_MS
            >= SPIKE_CYCLE_MS - SPIKE_ACTIVE_MS
        )
        color = TFT_WHITE if active else TFT_DARKGREY
        base_y = py + self.cell - 4
        for offset in (3, self.cell // 2, self.cell - 4):
            height = self.cell // 2 if active else 3
            self.draw._line(px + offset, base_y, px + offset, base_y - height, color)
            self.draw._line(px + offset - 2, base_y - height + 2, px + offset, base_y - height, color)
            self.draw._line(px + offset + 2, base_y - height + 2, px + offset, base_y - height, color)

    def _draw_mine(self, mine, animation_time):
        px, py = self._tile_box(mine[0], mine[1])
        cx = px + self.cell // 2
        cy = py + self.cell // 2
        blink = (animation_time // 180) % 2
        radius = max(2, self.cell // 4)
        self.draw._fill_circle(cx, cy, radius, TFT_BLACK)
        self.draw._circle(cx, cy, radius, COLOR_STEEL_LIGHT)
        self.draw._fill_circle(cx, cy, 2, TFT_RED if blink else TFT_YELLOW)

    def _draw_emitter(self, emitter, animation_time):
        px, py = self._tile_box(emitter[0], emitter[1])
        cx = px + self.cell // 2
        cy = py + self.cell // 2
        dx, dy = ((0, -1), (0, 1), (-1, 0), (1, 0))[emitter[2]]
        self.draw._fill_circle(cx, cy, max(2, self.cell // 4), COLOR_STEEL)
        self.draw._line(cx, cy, cx + dx * self.cell // 3, cy + dy * self.cell // 3, TFT_ORANGE)
        if emitter[4] and ticks_diff(emitter[4], animation_time) > 0:
            self.draw._circle(cx, cy, max(3, self.cell // 3), TFT_YELLOW)

    def _draw_cannon(self, cannon, animation_time):
        px, py = self._tile_box(cannon[0], cannon[1])
        cx = px + self.cell // 2
        cy = py + self.cell // 2
        self.draw._fill_circle(cx, cy, max(2, self.cell // 3), COLOR_STEEL)
        self.draw._line(
            cx,
            cy,
            cx + cannon[2] * self.cell // 2,
            cy + cannon[3] * self.cell // 2,
            TFT_BLACK,
        )
        if cannon[5] and ticks_diff(cannon[5], animation_time) > 0:
            self.draw._circle(cx, cy, max(3, self.cell // 3), TFT_RED)

    def _draw_projectile(self, projectile):
        px, py = self._tile_box(projectile[0], projectile[1])
        cx = px + self.cell // 2
        cy = py + self.cell // 2
        color = TFT_RED if projectile[5] == 0 else TFT_YELLOW
        self.draw._fill_circle(cx, cy, max(2, self.cell // 6), color)
        self.draw._line(
            cx - projectile[2] * self.cell // 3,
            cy - projectile[3] * self.cell // 3,
            cx,
            cy,
            TFT_WHITE,
        )

    def _draw_background_creature(self, creature, animation_time, theme):
        px, py = self._tile_box(creature[0], creature[1])
        panicked = ticks_diff(creature[3], animation_time) > 0
        bob = (animation_time // (80 if panicked else 260)) % 2
        color = COLOR_FOAM if theme in (THEME_WATER, THEME_CLOUD) else COLOR_LEAF
        cx = px + self.cell // 2 + (creature[4] * 2 if panicked else 0)
        cy = py + self.cell - 4 - bob
        if creature[2] == 0:
            self.draw._fill_circle(cx, cy, max(1, self.cell // 8), color)
            self.draw._fill_rectangle(cx - 1, cy - 1, 1, 1, TFT_BLACK)
        else:
            wing = 3 if panicked else 2
            self.draw._line(cx - wing, cy - bob, cx, cy, color)
            self.draw._line(cx, cy, cx + wing, cy - bob, color)
            self.draw._fill_rectangle(cx, cy, 1, 2, TFT_BLACK)

    def _draw_treasure(self, treasure, animation_time):
        px, py = self._tile_box(treasure[0], treasure[1])
        pad = max(2, self.cell // 6)
        pulse = (animation_time // 180) % 2
        self.draw._fill_rectangle(
            px + pad,
            py + self.cell // 3,
            self.cell - pad * 2,
            self.cell // 2,
            COLOR_WOOD,
        )
        self.draw._rectangle(
            px + pad,
            py + self.cell // 3,
            self.cell - pad * 2,
            self.cell // 2,
            COLOR_GOLD,
        )
        self.draw._fill_rectangle(
            px + self.cell // 2 - 2,
            py + self.cell // 2,
            4,
            4,
            TFT_YELLOW if pulse else COLOR_GOLD,
        )

    def _draw_courier_exit(self, game):
        if game.courier_exit_x < 0:
            return
        px, py = self._tile_box(game.courier_exit_x, game.courier_exit_y)
        inset = 2 + (game.animation_time // 180) % 2
        self.draw._rectangle(
            px + inset,
            py + inset,
            self.cell - inset * 2,
            self.cell - inset * 2,
            TFT_GREEN,
        )
        self.draw._line(
            px + self.cell // 3,
            py + self.cell // 2,
            px + self.cell * 2 // 3,
            py + self.cell // 2,
            TFT_WHITE,
        )

    def _draw_objective_bomb(self, draw_x, draw_y, deadline, animation_time):
        px, py = self._fixed_box(draw_x, draw_y)
        remaining = (
            ticks_diff(deadline, animation_time)
            if deadline
            else 9999
        )
        pulse = (animation_time // (80 if remaining < 1600 else 170)) % 2
        cx = px + self.cell // 2
        cy = py + self.cell // 3
        radius = max(2, self.cell // 5 + pulse)
        self.draw._fill_circle(cx, cy, radius, TFT_BLACK)
        self.draw._circle(
            cx,
            cy,
            radius,
            TFT_RED if remaining < 1600 else COLOR_GOLD,
        )
        self.draw._line(
            cx + radius // 2,
            cy - radius,
            cx + radius + 2,
            cy - radius - 2,
            TFT_ORANGE,
        )
        self.draw._fill_rectangle(
            cx + radius + 1,
            cy - radius - 3,
            2,
            2,
            TFT_WHITE if pulse else TFT_YELLOW,
        )

    def _draw_flame(self, flame):
        px, py = self._tile_box(flame[0], flame[1])
        center = self.cell // 2
        arm = max(1, self.cell // 4)
        self.draw._fill_rectangle(px, py + center - arm, self.cell, arm * 2, TFT_ORANGE)
        self.draw._fill_rectangle(px + center - arm, py, arm * 2, self.cell, TFT_ORANGE)
        inner = max(1, arm // 2)
        self.draw._fill_rectangle(
            px + inner,
            py + center - inner,
            self.cell - inner * 2,
            inner * 2,
            TFT_YELLOW,
        )
        self.draw._fill_rectangle(
            px + center - inner,
            py + inner,
            inner * 2,
            self.cell - inner * 2,
            TFT_YELLOW,
        )

    def _draw_player(self, game):
        px, py = self._fixed_box(game.player_draw_x, game.player_draw_y)
        frame = (game.animation_time // 110 + game.player_frame) % 4
        color = COLOR_PLAYER
        if (
            ticks_diff(game.invulnerable_until, game.animation_time) > 0
            and frame % 2
        ):
            color = TFT_WHITE

        cx = px + self.cell // 2
        cy = py + self.cell // 2
        if ticks_diff(game.speed_until, game.animation_time) > 0:
            self.draw._line(px, cy - 3, px + self.cell // 3, cy - 3, TFT_GREEN)
            self.draw._line(px - 2, cy + 2, px + self.cell // 4, cy + 2, TFT_GREEN)
        if ticks_diff(game.magnet_until, game.animation_time) > 0:
            self.draw._circle(cx, cy, max(3, self.cell // 2 - 2), TFT_MAGENTA)
        if ticks_diff(game.flame_suit_until, game.animation_time) > 0:
            self.draw._rectangle(px + 1, py + 1, self.cell - 2, self.cell - 2, TFT_ORANGE)
        if game.shield_hits > 0 or ticks_diff(
            game.shield_flash_until,
            game.animation_time,
        ) > 0:
            self.draw._circle(
                cx,
                cy,
                max(3, self.cell // 2 - 1),
                TFT_WHITE
                if ticks_diff(game.shield_flash_until, game.animation_time) > 0
                else TFT_CYAN,
            )

        if self.cell < 12:
            pad = max(1, self.cell // 6)
            self.draw._fill_rectangle(
                px + pad,
                py + pad,
                self.cell - pad * 2,
                self.cell - pad * 2,
                color,
            )
            return

        bob = 1 if frame in (1, 3) else 0
        pad = max(2, self.cell // 5)
        body_w = self.cell - pad * 2
        helmet_y = py + 2 + bob
        helmet_h = max(7, self.cell // 2)

        # Helmet and visor.
        self.draw._fill_rectangle(
            px + pad + 2,
            helmet_y,
            body_w - 4,
            2,
            color,
        )
        self.draw._fill_rectangle(
            px + pad,
            helmet_y + 2,
            body_w,
            helmet_h - 2,
            color,
        )
        visor_x = px + pad + 2
        visor_y = helmet_y + 4
        visor_w = max(4, body_w - 4)
        self.draw._fill_rectangle(visor_x, visor_y, visor_w, 4, COLOR_VISOR)

        # Directional visor detail makes facing readable.
        if game.player_facing == 1:
            self.draw._fill_rectangle(visor_x + 1, visor_y + 1, 2, 2, TFT_WHITE)
        elif game.player_facing == 2:
            self.draw._fill_rectangle(
                visor_x + visor_w - 3,
                visor_y + 1,
                2,
                2,
                TFT_WHITE,
            )
        elif game.player_facing == 3:
            self.draw._line(
                visor_x + 2,
                visor_y + 1,
                visor_x + visor_w - 3,
                visor_y + 1,
                TFT_WHITE,
            )
        else:
            self.draw._fill_rectangle(visor_x + 2, visor_y + 1, 2, 2, TFT_WHITE)
            self.draw._fill_rectangle(
                visor_x + visor_w - 4,
                visor_y + 1,
                2,
                2,
                TFT_WHITE,
            )

        # Suit, arms, and alternating legs provide the four-step cycle.
        torso_y = helmet_y + helmet_h
        torso_w = max(4, body_w - 4)
        self.draw._fill_rectangle(
            px + pad + 2,
            torso_y,
            torso_w,
            max(3, self.cell // 5),
            COLOR_PLAYER_DARK,
        )
        self.draw._fill_rectangle(px + pad, torso_y + 1, 2, 4, color)
        self.draw._fill_rectangle(px + self.cell - pad - 2, torso_y + 1, 2, 4, color)

        leg_y = min(py + self.cell - 5, torso_y + max(3, self.cell // 5))
        leg_w = max(2, torso_w // 3)
        left_step = 2 if frame == 1 else 0
        right_step = 2 if frame == 3 else 0
        self.draw._fill_rectangle(
            px + pad + 2,
            leg_y + left_step,
            leg_w,
            max(2, 4 - left_step),
            color,
        )
        self.draw._fill_rectangle(
            px + self.cell - pad - 2 - leg_w,
            leg_y + right_step,
            leg_w,
            max(2, 4 - right_step),
            color,
        )

    def _enemy_colors(self, kind, theme, elite):
        if elite:
            return COLOR_GOLD, TFT_WHITE
        if kind == ENEMY_BOMBER:
            return TFT_RED, TFT_CYAN
        if kind in (ENEMY_SLIME, ENEMY_SMALL_SLIME):
            return TFT_GREEN, TFT_MAGENTA
        if kind == ENEMY_KAMIKAZE:
            return TFT_ORANGE, TFT_RED
        if kind == ENEMY_TURRET:
            return COLOR_STEEL_LIGHT, TFT_RED
        if kind == 0:
            return COLOR_ENEMY_BLOB, TFT_WHITE
        return COLOR_ENEMY_CHASER, TFT_BLACK

    def _draw_slime_enemy(self, px, py, frame, small, elite):
        color, accent = self._enemy_colors(ENEMY_SLIME, 0, elite)
        radius = max(2, self.cell // (5 if small else 3))
        cx = px + self.cell // 2
        cy = py + self.cell // 2 + (1 if frame in (1, 3) else 0)
        self.draw._fill_circle(cx, cy, radius, color)
        self.draw._fill_rectangle(cx - radius, cy, radius * 2 + 1, radius, color)
        self.draw._fill_rectangle(cx - radius // 2, cy - 1, 2, 2, TFT_WHITE)
        self.draw._fill_rectangle(cx + radius // 2, cy - 1, 2, 2, TFT_WHITE)
        self.draw._line(cx - radius, cy + radius, cx + radius, cy + radius, accent)
        if elite:
            self._draw_elite_mark(px, py)

    def _draw_kamikaze_enemy(self, px, py, frame, facing, elite):
        color, accent = self._enemy_colors(ENEMY_KAMIKAZE, 0, elite)
        cx = px + self.cell // 2
        cy = py + self.cell // 2
        radius = max(3, self.cell // 3)
        self.draw._fill_circle(cx, cy, radius, color)
        self.draw._circle(cx, cy, radius, TFT_BLACK)
        eye_dx, eye_dy = self._direction_for_facing(facing)
        self.draw._fill_circle(cx + eye_dx * 2, cy + eye_dy * 2, 2, TFT_WHITE)
        # The live bomb is visibly strapped to its back at all times.
        self.draw._fill_circle(cx - eye_dx * radius, cy - eye_dy * radius, max(2, radius // 2), TFT_BLACK)
        spark = 1 + frame % 2
        self.draw._fill_rectangle(cx - eye_dx * radius + spark, cy - eye_dy * radius - spark, 2, 2, accent)
        if elite:
            self._draw_elite_mark(px, py)

    @staticmethod
    def _direction_for_facing(facing):
        if facing == 1:
            return -1, 0
        if facing == 2:
            return 1, 0
        if facing == 3:
            return 0, -1
        return 0, 1

    def _draw_turret_enemy(self, px, py, facing):
        cx = px + self.cell // 2
        cy = py + self.cell // 2
        pad = max(2, self.cell // 5)
        dx, dy = self._direction_for_facing(facing)
        self.draw._fill_rectangle(
            px + pad,
            py + pad,
            self.cell - pad * 2,
            self.cell - pad * 2,
            COLOR_STEEL,
        )
        self.draw._rectangle(
            px + pad,
            py + pad,
            self.cell - pad * 2,
            self.cell - pad * 2,
            COLOR_STEEL_LIGHT,
        )
        self.draw._fill_circle(cx, cy, max(2, self.cell // 6), TFT_RED)
        self.draw._line(cx, cy, cx + dx * self.cell // 2, cy + dy * self.cell // 2, TFT_BLACK)

    def _draw_blob_enemy(self, px, py, frame, theme, elite):
        color, accent = self._enemy_colors(0, theme, elite)
        pad = max(2, self.cell // 6)
        squat = 2 if frame in (1, 3) else 0
        side = 0 if squat == 0 else 1
        x = px + pad - side
        y = py + pad + squat
        width = self.cell - pad * 2 + side * 2
        height = self.cell - pad * 2 - squat
        self.draw._fill_rectangle(x + 2, y, width - 4, 2, color)
        self.draw._fill_rectangle(x, y + 2, width, height - 4, color)
        self.draw._fill_rectangle(x + 2, y + height - 2, width - 4, 2, color)
        if self.cell >= 12:
            eye_y = y + 4
            blink = frame == 2
            eye_h = 1 if blink else 3
            self.draw._fill_rectangle(x + 3, eye_y, 3, eye_h, TFT_WHITE)
            self.draw._fill_rectangle(x + width - 6, eye_y, 3, eye_h, TFT_WHITE)
            if theme == THEME_INDUSTRIAL and not elite:
                self.draw._line(
                    x + 2,
                    y + height // 2,
                    x + width - 3,
                    y + height // 2,
                    accent,
                )
            elif theme == THEME_WATER and not elite:
                self.draw._circle(x + width // 2, y + height - 5, 2, accent)
            foot_y = y + height - 2
            if frame in (0, 2):
                self.draw._fill_rectangle(x, foot_y, 4, 2, color)
                self.draw._fill_rectangle(x + width - 4, foot_y, 4, 2, color)
            else:
                self.draw._fill_rectangle(x + 3, foot_y, 4, 2, color)
                self.draw._fill_rectangle(x + width - 7, foot_y, 4, 2, color)
            if elite:
                self._draw_elite_mark(px, py)

    def _draw_chaser_enemy(self, px, py, frame, facing, theme, elite):
        color, accent = self._enemy_colors(1, theme, elite)
        bob = (0, 1, 0, -1)[frame]
        cx = px + self.cell // 2
        cy = py + self.cell // 2 - 1 + bob
        radius = max(3, self.cell // 3)
        self.draw._fill_circle(cx, cy, radius, color)
        self.draw._fill_rectangle(
            cx - radius,
            cy,
            radius * 2 + 1,
            radius,
            color,
        )
        eye_y = cy - 2
        eye_x = cx
        if facing == 1:
            eye_x -= 2
        elif facing == 2:
            eye_x += 2
        elif facing == 3:
            eye_y -= 1
        self.draw._fill_rectangle(eye_x - 2, eye_y - 1, 4, 4, TFT_WHITE)
        self.draw._fill_rectangle(eye_x, eye_y, 2, 2, TFT_BLACK)
        if theme == THEME_INDUSTRIAL and not elite:
            self.draw._line(
                cx - radius + 2,
                cy + 2,
                cx + radius - 2,
                cy + 2,
                accent,
            )
        elif theme == THEME_WATER and not elite:
            self.draw._fill_rectangle(
                cx - radius - 2,
                cy - 1,
                2,
                2,
                accent,
            )
            self.draw._fill_rectangle(
                cx + radius + 1,
                cy - 1,
                2,
                2,
                accent,
            )

        foot_y = cy + radius - 1
        shift = 2 if frame in (1, 3) else 0
        self.draw._fill_rectangle(cx - radius, foot_y, 4 + shift, 3, color)
        self.draw._fill_rectangle(
            cx + radius - 4 - shift,
            foot_y,
            4 + shift,
            3,
            color,
        )
        if elite:
            self._draw_elite_mark(px, py)

    def _draw_rival_enemy(self, px, py, frame, facing, theme, elite):
        color, accent = self._enemy_colors(ENEMY_BOMBER, theme, elite)
        bob = 1 if frame in (1, 3) else 0
        pad = max(2, self.cell // 5)
        helmet_y = py + 3 + bob
        width = self.cell - pad * 2
        helmet_h = max(7, self.cell // 2)
        self.draw._fill_rectangle(
            px + pad + 2,
            helmet_y,
            width - 4,
            2,
            color,
        )
        self.draw._fill_rectangle(
            px + pad,
            helmet_y + 2,
            width,
            helmet_h - 2,
            color,
        )
        visor_x = px + pad + 2
        visor_y = helmet_y + 4
        visor_w = max(4, width - 4)
        self.draw._fill_rectangle(visor_x, visor_y, visor_w, 4, TFT_BLACK)
        glint_x = (
            visor_x + 1
            if facing == 1
            else visor_x + visor_w - 3
            if facing == 2
            else visor_x + visor_w // 2 - 1
        )
        self.draw._fill_rectangle(glint_x, visor_y + 1, 2, 2, TFT_CYAN)

        torso_y = helmet_y + helmet_h
        self.draw._fill_rectangle(
            px + pad + 2,
            torso_y,
            max(4, width - 4),
            4,
            COLOR_RUST if not elite else COLOR_GOLD,
        )
        self.draw._fill_rectangle(px + pad - 1, torso_y, 3, 5, color)
        self.draw._fill_rectangle(px + self.cell - pad - 2, torso_y, 3, 5, color)
        self.draw._fill_rectangle(
            px + self.cell - pad - 1,
            helmet_y + helmet_h - 3,
            3,
            5,
            TFT_BLACK,
        )
        self.draw._fill_rectangle(
            px + self.cell - pad,
            helmet_y + helmet_h - 2,
            1,
            1,
            accent,
        )

        leg_y = min(py + self.cell - 4, torso_y + 4)
        left_step = 2 if frame == 1 else 0
        right_step = 2 if frame == 3 else 0
        self.draw._fill_rectangle(
            px + pad + 2,
            leg_y + left_step,
            3,
            max(2, 4 - left_step),
            color,
        )
        self.draw._fill_rectangle(
            px + self.cell - pad - 5,
            leg_y + right_step,
            3,
            max(2, 4 - right_step),
            color,
        )
        if elite:
            self._draw_elite_mark(px, py)

    def _draw_elite_mark(self, px, py):
        cx = px + self.cell // 2
        top = py + 1
        self.draw._line(cx - 4, top + 3, cx - 2, top, COLOR_GOLD)
        self.draw._line(cx - 2, top, cx, top + 3, COLOR_GOLD)
        self.draw._line(cx, top + 3, cx + 2, top, COLOR_GOLD)
        self.draw._line(cx + 2, top, cx + 4, top + 3, COLOR_GOLD)
        self.draw._line(cx - 4, top + 3, cx + 4, top + 3, TFT_WHITE)

    def _draw_enemy(self, enemy, animation_time, theme):
        px, py = self._fixed_box(enemy[6], enemy[7])
        frame = (animation_time // 120 + enemy[4] + enemy[0] + enemy[1]) % 4
        elite = enemy[8]
        if self.cell < 12:
            pad = max(1, self.cell // 6)
            color, accent = self._enemy_colors(enemy[3], theme, elite)
            self.draw._fill_rectangle(
                px + pad,
                py + pad,
                self.cell - pad * 2,
                self.cell - pad * 2,
                color,
            )
            self.draw._rectangle(
                px + pad,
                py + pad,
                self.cell - pad * 2,
                self.cell - pad * 2,
                accent,
            )
        elif enemy[3] == ENEMY_TURRET:
            self._draw_turret_enemy(px, py, enemy[5])
        elif enemy[3] == ENEMY_KAMIKAZE:
            self._draw_kamikaze_enemy(px, py, frame, enemy[5], elite)
        elif enemy[3] in (ENEMY_SLIME, ENEMY_SMALL_SLIME):
            self._draw_slime_enemy(
                px,
                py,
                frame,
                enemy[3] == ENEMY_SMALL_SLIME,
                elite,
            )
        elif enemy[3] == ENEMY_BOMBER:
            self._draw_rival_enemy(
                px,
                py,
                frame,
                enemy[5],
                theme,
                elite,
            )
        elif enemy[3] == 0:
            self._draw_blob_enemy(px, py, frame, theme, elite)
        else:
            self._draw_chaser_enemy(px, py, frame, enemy[5], theme, elite)
        if len(enemy) >= 12 and enemy[11] and ticks_diff(
            enemy[11],
            animation_time,
        ) > 0:
            icon_x = px + self.cell - 6
            icon_y = py + 1
            self.draw._fill_circle(icon_x, icon_y + 3, 4, TFT_YELLOW)
            self.draw._text(icon_x - 2, icon_y - 1, "!", TFT_BLACK, 0)

    def _draw_decal(self, decal):
        px, py = self._fixed_box(decal[0], decal[1])
        kind = decal[2]
        theme = decal[3]
        variant = decal[4]
        cx = px + self.cell // 2
        cy = py + self.cell // 2
        radius = max(2, self.cell // 4)

        if kind == DECAL_SCORCH:
            if theme in (THEME_NATURE, THEME_FOREST):
                color = COLOR_WOOD_DARK
            elif theme in (THEME_INDUSTRIAL, THEME_HELL):
                color = TFT_BLACK
            elif theme == THEME_WATER:
                color = COLOR_WATER_DARK
            elif theme == THEME_BEACH:
                color = COLOR_BEACH_ROCK
            elif theme == THEME_CLOUD:
                color = COLOR_STORM
            else:
                color = COLOR_CANYON_DARK
            accent = (
                COLOR_WAVE
                if theme == THEME_WATER
                else COLOR_LAVA
                if theme == THEME_HELL
                else COLOR_CLOUD_SHADE
                if theme == THEME_CLOUD
                else TFT_DARKGREY
            )
            self.draw._fill_circle(cx, cy, radius + variant % 2, color)
            self.draw._line(
                cx - radius,
                cy + variant % 3 - 1,
                cx + radius,
                cy - variant % 2,
                accent,
            )
            return

        if kind == DECAL_DEBRIS:
            if theme == THEME_NATURE:
                color, accent = COLOR_WOOD, COLOR_WOOD_DARK
            elif theme == THEME_INDUSTRIAL:
                color, accent = COLOR_STEEL_LIGHT, COLOR_RUST
            elif theme == THEME_WATER:
                color, accent = COLOR_CORAL, COLOR_REEF
            elif theme == THEME_BEACH:
                color, accent = COLOR_PALM, COLOR_SHELL
            elif theme == THEME_HELL:
                color, accent = COLOR_BRIMSTONE, COLOR_LAVA
            elif theme == THEME_CLOUD:
                color, accent = COLOR_CLOUD, COLOR_STORM
            elif theme == THEME_FOREST:
                color, accent = COLOR_BARK, COLOR_LEAF
            else:
                color, accent = COLOR_SANDSTONE, COLOR_CANYON_DARK
            self.draw._fill_rectangle(px + 3, cy - 1, 4, 2, color)
            self.draw._fill_rectangle(cx + 2, py + 4, 3, 3, accent)
            self.draw._line(
                cx - 2,
                cy + 2,
                cx + 4,
                cy + 4,
                color,
            )
            return

        if kind == DECAL_ELITE:
            self.draw._fill_circle(cx, cy, radius + 2, COLOR_GOLD)
            self.draw._fill_circle(cx, cy, max(1, radius - 1), TFT_BLACK)
            self.draw._line(cx - radius, cy, cx + radius, cy, TFT_WHITE)
            self.draw._line(cx, cy - radius, cx, cy + radius, TFT_WHITE)
            return

        if kind == DECAL_BLOB:
            color, accent = self._enemy_colors(0, theme, False)
            self.draw._fill_circle(cx, cy, radius + variant % 2, color)
            self.draw._fill_circle(cx - radius, cy + 2, max(1, radius // 2), color)
            self.draw._fill_circle(cx + radius, cy - 1, max(1, radius // 2), color)
            self.draw._fill_rectangle(cx - 1, cy - 1, 2, 2, accent)
            return

        if kind == DECAL_BOMBER:
            self.draw._fill_circle(cx, cy, radius + 1, COLOR_RUST)
            self.draw._fill_circle(cx, cy, max(1, radius - 2), TFT_BLACK)
            self.draw._line(
                cx - radius - 1,
                cy - radius,
                cx + radius + 1,
                cy + radius,
                TFT_RED,
            )
            self.draw._line(
                cx + radius + 1,
                cy - radius,
                cx - radius - 1,
                cy + radius,
                TFT_RED,
            )
            return

        color, accent = self._enemy_colors(1, theme, False)
        self.draw._circle(cx, cy, radius + 1, color)
        self.draw._circle(cx, cy, max(1, radius - 2), accent)
        self.draw._fill_rectangle(cx - radius - 2, cy - 1, 3, 2, color)
        self.draw._fill_rectangle(cx + radius, cy + 1, 3, 2, color)

    def _draw_death(self, effect, animation_time, theme):
        px, py = self._fixed_box(effect[0], effect[1])
        elapsed = max(0, ticks_diff(animation_time, effect[3]))
        frame = min(4, elapsed * 5 // DEATH_ANIMATION_MS)
        cx = px + self.cell // 2
        cy = py + self.cell // 2

        if effect[2] == DEATH_PLAYER:
            color = COLOR_PLAYER
        elif effect[2] == DEATH_ENEMY_BLOB:
            color = self._enemy_colors(0, theme, False)[0]
        elif effect[2] == DEATH_ENEMY_ELITE:
            color = COLOR_GOLD
        elif effect[2] == DEATH_ENEMY_BOMBER:
            color = TFT_RED
        else:
            color = self._enemy_colors(1, theme, False)[0]

        radius = max(2, self.cell // 3)
        if frame == 0:
            self.draw._fill_circle(cx, cy, radius, TFT_WHITE)
        else:
            core_radius = max(1, radius - frame * 2)
            self.draw._fill_circle(cx, cy, core_radius, color)

        step = max(2, self.cell // 6)
        distance = step * (frame + 1)
        particle_size = 4 if frame == 0 else 3 if frame <= 3 else 2
        seed = (
            effect[0] // POSITION_SCALE * 3
            + effect[1] // POSITION_SCALE * 5
            + effect[2]
        )
        for index in range(len(PARTICLE_DIRECTIONS)):
            dx, dy = PARTICLE_DIRECTIONS[index]
            jitter = (seed + index * 7) % 3 - 1
            particle_x = cx + dx * distance
            particle_y = cy + dy * distance
            if dx == 0:
                particle_x += jitter
            if dy == 0:
                particle_y += jitter
            particle_color = (
                TFT_WHITE
                if frame <= 1 and index % 3 == 0
                else TFT_YELLOW
                if index % 2
                else color
            )
            if 0 < frame < 4 and index % 2 == 0:
                self.draw._line(
                    cx + dx * max(1, distance - step),
                    cy + dy * max(1, distance - step),
                    particle_x,
                    particle_y,
                    particle_color,
                )
            self.draw._fill_rectangle(
                particle_x - particle_size // 2,
                particle_y - particle_size // 2,
                particle_size,
                particle_size,
                particle_color,
            )

    def _draw_overlay(self, title, subtitle, title_color):
        box_w = min(self.width - 16, 250)
        box_h = 70
        x = (self.width - box_w) // 2
        y = (self.height - box_h) // 2
        self.draw._fill_rectangle(x, y, box_w, box_h, TFT_BLACK)
        self.draw._rectangle(x, y, box_w, box_h, title_color)
        self._center_text(title, y + 12, title_color, 2)
        self._center_text(subtitle, y + 44, TFT_WHITE, 0)

    def draw_frame(self, game):
        """Render the current model state and present the framebuffer."""
        self.tile_x = -1
        self.tile_y = -1
        self.item_index = -1
        if game.state == STATE_TITLE:
            self.phase = 1
            self._draw_title()
            self.phase = 2
            self.draw.swap()
            return
        if game.state == STATE_MODE_SELECT:
            self.phase = 3
            self._draw_mode_menu(game)
            self.phase = 4
            self.draw.swap()
            return
        if game.state == STATE_LEADERBOARD:
            self.phase = 5
            self._draw_leaderboard(game)
            self.phase = 6
            self.draw.swap()
            return
        if game.state == STATE_NAME_ENTRY:
            self.phase = 7
            self._draw_name_entry(game)
            self.phase = 8
            self.draw.swap()
            return

        self.phase = 10
        self.draw.fill_screen(self._theme_background(game.theme))
        self.phase = 11
        self._draw_hud(game)

        base_origin_x = self.origin_x
        base_origin_y = self.origin_y
        if ticks_diff(game.shake_until, game.animation_time) > 0:
            shake = max(1, min(3, game.chain_strength))
            shake_frame = (game.animation_time // 45) % 4
            self.origin_x += (-shake, shake, 0, -shake)[shake_frame]
            self.origin_y += (0, -shake, shake, shake)[shake_frame]

        self.phase = 12
        py = self.origin_y
        for y in range(GRID_HEIGHT):
            self.tile_y = y
            px = self.origin_x
            for x in range(GRID_WIDTH):
                self.tile_x = x
                tile = game.grid[y][x]
                if tile == TILE_SOLID:
                    self._draw_solid(px, py, x, y, game.theme)
                elif tile == TILE_BRICK:
                    self._draw_brick(px, py, x, y, game.theme)
                else:
                    self._draw_floor(
                        px,
                        py,
                        x,
                        y,
                        game.theme,
                        game.animation_time,
                    )
                px += self.cell
            py += self.cell

        self.phase = 13
        self.item_index = 0
        if game.mode == MODE_BOMB_COURIER:
            self._draw_courier_exit(game)
        for creature in game.background_creatures:
            self._draw_background_creature(
                creature,
                game.animation_time,
                game.theme,
            )
            self.item_index += 1
        for pad in game.teleporters:
            self._draw_teleporter(pad, game.animation_time)
            self.item_index += 1
        for trap in game.spike_traps:
            self._draw_spike_trap(trap, game.animation_time)
            self.item_index += 1
        for mine in game.mines:
            self._draw_mine(mine, game.animation_time)
            self.item_index += 1
        for emitter in game.flame_emitters:
            self._draw_emitter(emitter, game.animation_time)
            self.item_index += 1
        for cannon in game.cannons:
            self._draw_cannon(cannon, game.animation_time)
            self.item_index += 1
        for decal in game.decals:
            self._draw_decal(decal)
            self.item_index += 1
        self.phase = 14
        self.item_index = 0
        for treasure in game.treasures:
            self._draw_treasure(treasure, game.animation_time)
            self.item_index += 1
        if (
            game.mode == MODE_BOMB_COURIER
            and not game.courier_carrying
            and game.courier_bomb_x >= 0
        ):
            self._draw_objective_bomb(
                game.courier_bomb_x * POSITION_SCALE,
                game.courier_bomb_y * POSITION_SCALE,
                0,
                game.animation_time,
            )
        for powerup in game.powerups:
            self._draw_powerup(powerup)
            self.item_index += 1
        for barrel in game.barrels:
            self._draw_barrel(barrel)
            self.item_index += 1
        self.phase = 15
        self.item_index = 0
        for bomb in game.bombs:
            self._draw_bomb(bomb, game.animation_time, game.theme)
            self.item_index += 1
        for projectile in game.projectiles:
            self._draw_projectile(projectile)
            self.item_index += 1
        self.phase = 16
        self.item_index = 0
        for enemy in game.enemies:
            self._draw_enemy(enemy, game.animation_time, game.theme)
            self.item_index += 1
        self.phase = 17
        if game.state not in (STATE_PLAYER_DYING, STATE_GAME_OVER):
            self._draw_player(game)
        if game.mode == MODE_BOMB_COURIER and game.courier_carrying:
            self._draw_objective_bomb(
                game.player_draw_x,
                game.player_draw_y,
                game.courier_fuse_until,
                game.animation_time,
            )
        elif game.mode == MODE_HOT_POTATO:
            if game.hot_potato_player:
                self._draw_objective_bomb(
                    game.player_draw_x,
                    game.player_draw_y,
                    game.hot_potato_until,
                    game.animation_time,
                )
            elif game.hot_potato_enemy is not None:
                self._draw_objective_bomb(
                    game.hot_potato_enemy[6],
                    game.hot_potato_enemy[7],
                    game.hot_potato_until,
                    game.animation_time,
                )
        self.phase = 18
        self.item_index = 0
        for flame in game.explosions:
            self._draw_flame(flame)
            self.item_index += 1
        self.phase = 19
        self.item_index = 0
        for effect in game.death_effects:
            self._draw_death(effect, game.animation_time, game.theme)
            self.item_index += 1

        self.origin_x = base_origin_x
        self.origin_y = base_origin_y
        if ticks_diff(game.flash_until, game.animation_time) > 0:
            flash_color = TFT_WHITE if game.chain_strength >= 3 else TFT_YELLOW
            border = max(1, game.chain_strength)
            for inset in range(border):
                self.draw._rectangle(
                    inset,
                    self.hud_height + inset,
                    self.width - inset * 2,
                    self.height - self.hud_height - inset * 2,
                    flash_color,
                )

        self.phase = 20
        if game.state == STATE_STAGE_INTRO:
            self._draw_overlay(
                THEME_NAMES[game.theme],
                "STAGE %d - %s" % (game.stage, MODE_NAMES[game.mode]),
                self._theme_color(game.theme),
            )
        elif game.state == STATE_STAGE_CLEAR:
            if game.mode == MODE_TREASURE_HUNT:
                title = "TREASURE FOUND"
            elif game.mode == MODE_BOMB_COURIER:
                title = "DELIVERED"
            elif game.mode == MODE_HOT_POTATO:
                title = "POTATO CLEARED"
            else:
                title = "STAGE CLEAR"
            self._draw_overlay(title, "+250 BONUS", TFT_GREEN)
        elif game.state == STATE_GAME_OVER:
            self._draw_overlay("GAME OVER", "CENTER FOR MODES", TFT_RED)
        elif game.state == STATE_PAUSED:
            self._draw_overlay("PAUSED", "P RESUME - BACK MODES", TFT_YELLOW)

        self.phase = 21
        self.draw.swap()
        self.phase = 0
