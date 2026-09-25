"""Picoware launcher for Gorillas.

Draw the small loading logo before importing the larger game module.
"""

from time import ticks_ms
from picoware.system.vector import Vector


INK = 0x1085
PANEL = 0x18C7
SLATE = 0x52F0
CREAM = 0xFF35
GOLD = 0xFDEA
TEAL = 0x5E79
CORAL = 0xFBAE
LOGO_FULL = ("gorillas_game/loading-logo.bin", 78, 72)
LOGO_COMPACT = ("gorillas_game/loading-logo-compact.bin", 52, 48)
SCENE_ASSET = "picoware/apps/games/gorillas_game/loading-scene.bin"
SEASONAL_SCENES = {
    "spring": "picoware/apps/games/gorillas_game/loading-scene-spring.bin",
    "summer": "picoware/apps/games/gorillas_game/loading-scene-summer.bin",
    "fall": "picoware/apps/games/gorillas_game/loading-scene-fall.bin",
    "winter": "picoware/apps/games/gorillas_game/loading-scene-winter.bin",
}
SCENE_SIZE = 320
SCENE_BYTES = SCENE_SIZE * SCENE_SIZE


def __scene_asset_for_date(view_manager):
    """Choose seasonal art only when Picoware has a valid set RTC date."""
    clock = view_manager.time
    if not clock.is_set:
        return SCENE_ASSET

    try:
        date = clock.rtc.datetime()
        year, month = int(date[0]), int(date[1])
    except Exception:
        return SCENE_ASSET

    if year < 2024 or month < 1 or month > 12:
        return SCENE_ASSET

    # Use Northern Hemisphere meteorological seasons.
    if month in (3, 4, 5):
        season = "spring"
    elif month in (6, 7, 8):
        season = "summer"
    elif month in (9, 10, 11):
        season = "fall"
    else:
        season = "winter"
    return SEASONAL_SCENES[season]

_game_module = None


def __draw_loading_screen(view_manager):
    """Show the full-screen art on PicoCalc-sized displays, else the logo."""
    draw = view_manager.draw
    width, height = int(draw.size.x), int(draw.size.y)
    if width >= SCENE_SIZE and height >= SCENE_SIZE:
        storage = view_manager.storage
        scene_asset = __scene_asset_for_date(view_manager)
        if storage.exists(scene_asset) and storage.size(scene_asset) == SCENE_BYTES:
            draw.fill_screen(INK)
            chunk_height = 8
            buffer = bytearray(SCENE_SIZE * chunk_height)
            draw.image_bytearray_path(
                Vector((width - SCENE_SIZE) // 2, (height - SCENE_SIZE) // 2),
                Vector(SCENE_SIZE, SCENE_SIZE),
                scene_asset,
                storage=storage,
                chunk_size=SCENE_SIZE * chunk_height,
                buffer=buffer,
                loop=True,
            )
            draw.swap()
            return

    font_height = int(draw.font_size.y)
    compact = width < 180 or height < 180
    filename, logo_width, logo_height = LOGO_COMPACT if compact else LOGO_FULL
    logo = bytearray(logo_width * logo_height)
    path = __file__.rsplit("/", 1)[0] + "/" + filename
    with open(path, "rb") as source:
        if source.readinto(logo) != len(logo):
            raise ValueError("Truncated Gorillas loading logo")

    panel_width, panel_height = logo_width + 10, logo_height + 10
    panel_x = max(0, (width - panel_width) // 2)
    panel_y = max(4, (height - panel_height - (2 if compact else 4) * font_height - 28) // 2)
    logo_x, logo_y = (width - logo_width) // 2, panel_y + 5

    draw.fill_screen(INK)
    draw._fill_rectangle(0, 0, width, 3, TEAL)
    draw.fill_round_rectangle(
        Vector(panel_x, panel_y), Vector(panel_width, panel_height), 5, PANEL,
    )
    draw.rect(Vector(panel_x, panel_y), Vector(panel_width, panel_height), TEAL)
    draw.image_bytearray(Vector(logo_x, logo_y), Vector(logo_width, logo_height), logo)

    title = "GORILLAS"
    title_y = panel_y + panel_height + font_height
    draw.text(Vector(max(0, (width - draw.len(title)) // 2), title_y), title, CREAM)
    if compact:
        status = "LOADING CITY..."
        status_y = max(title_y + font_height + 3, height - font_height - 8)
    else:
        subtitle = "ROOFTOP DUEL"
        subtitle_y = title_y + font_height + 3
        draw.text(Vector(max(0, (width - draw.len(subtitle)) // 2), subtitle_y), subtitle, GOLD)
        status = "LOADING CITY..."
        status_y = max(subtitle_y + font_height + 7, height - 2 * font_height - 14)
        footer = "FIRST TO 3 WINS"
        footer_y = min(height - font_height, status_y + font_height + 2)
        if footer_y >= status_y + font_height + 2 and footer_y + font_height <= height:
            draw.text(Vector(max(0, (width - draw.len(footer)) // 2), footer_y), footer, SLATE)
    draw.text(Vector(max(0, (width - draw.len(status)) // 2), status_y), status, TEAL)
    draw._fill_rectangle(0, height - 3, width, 3, CORAL)
    draw.swap()


def start(view_manager):
    """Show the logo, then import and start the heavier game module."""
    global _game_module

    splash_started = ticks_ms()
    __draw_loading_screen(view_manager)

    import gorillas_game.game as game_module
    _game_module = game_module
    return game_module.start(view_manager, splash_started)


def run(view_manager):
    """Run one game frame after startup."""
    if _game_module is not None:
        _game_module.run(view_manager)


def stop(view_manager):
    """Release the game scene when leaving the app."""
    global _game_module
    if _game_module is not None:
        _game_module.stop(view_manager)
        _game_module = None


__all__ = ("start", "run", "stop")
