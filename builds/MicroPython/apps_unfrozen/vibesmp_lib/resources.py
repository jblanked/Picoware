import json

# ---- theme resources ----

from micropython import const

# VibesMP Theme Presets (RGB565 via RGB888 conversion)
# Calculated using: ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

THEMES = {
    "dark": { # Classic Refined
        "bg_c": const(0x18E3),      # rgb(24, 28, 24)
        "well": const(0x0821),      # Black
        "text_c": const(0xDEFB),    # rgb(220, 220, 220)
        "accent_c": const(0xFC00),  # rgb(255, 128, 0)
        "highlight_c": const(0x07FF), # Cyan
        "panel_c": const(0x2965),   # rgb(40, 44, 40)
        "footer_bg": const(0xFC00), # Orange
        "footer_text": const(0x0821) # Black
    },
    "midnight": { # OLED Black + Neon Blue
        "bg_c": const(0x0821),      # Near Black
        "well": const(0x1082),      # rgb(20, 20, 20)
        "text_c": const(0xDEFB),    # Muted White
        "accent_c": const(0x05FF),  # rgb(0, 191, 255)
        "highlight_c": const(0xF81F), # Magenta
        "panel_c": const(0x0841),   # rgb(15, 15, 15)
        "footer_bg": const(0x05FF), # Neon Blue
        "footer_text": const(0x0821) # Black
    },
    "nord": { # Frosty Arctic
        "bg_c": const(0x2AD6),      # rgb(46, 52, 64)
        "well": const(0x3A32),      # rgb(59, 66, 82)
        "text_c": const(0xEF79),    # rgb(236, 239, 244)
        "accent_c": const(0x8E38),  # rgb(136, 192, 208)
        "highlight_c": const(0x8318), # rgb(129, 161, 193)
        "panel_c": const(0x426B),   # rgb(67, 76, 94)
        "footer_bg": const(0x8E38), # Frost Blue
        "footer_text": const(0x2AD6) # Darker Blue
    },
    "forest": { # Deep Moss + Brass
        "bg_c": const(0x10E2),      # rgb(20, 30, 20)
        "well": const(0x0841),      # rgb(10, 15, 10)
        "text_c": const(0xD75A),    # rgb(210, 230, 210)
        "accent_c": const(0xB50A),  # rgb(180, 160, 80)
        "highlight_c": const(0x07E0), # Green
        "panel_c": const(0x1B63),   # rgb(30, 45, 30)
        "footer_bg": const(0xB50A), # Brass
        "footer_text": const(0x10E2) # Deep Green
    },
    "solarized": { # Official Solarized Dark
        "bg_c": const(0x0166),      # base03
        "well": const(0x01AA),      # base02
        "text_c": const(0x84B2),    # base0
        "accent_c": const(0xB440),  # Yellow
        "highlight_c": const(0x245A), # Blue
        "panel_c": const(0x01AA),   # base02
        "footer_bg": const(0xB440), # Yellow
        "footer_text": const(0x0166) # base03
    },
    "apocalypse": { # Rust & Ash
        "bg_c": const(0x2104),      # Charcoal
        "well": const(0x1082),      # Deep Gray
        "text_c": const(0xBDD7),    # Ash Gray
        "accent_c": const(0xA145),  # Rust Red
        "highlight_c": const(0x8200), # Blood Red
        "panel_c": const(0x3186),   # Medium Gray
        "footer_bg": const(0xA145), # Rust
        "footer_text": const(0x2104) # Charcoal
    },
    "toxic_green": { # Matrix Glow
        "bg_c": const(0x0000),      # Pure Black
        "well": const(0x0040),      # Dark Emerald
        "text_c": const(0x07E0),    # Bright Green
        "accent_c": const(0xAD60),  # Acid Yellow-Green
        "highlight_c": const(0xFFFF), # White
        "panel_c": const(0x0821),   # Dark Gray
        "footer_bg": const(0xAD60), # Acid
        "footer_text": const(0x0000) # Black
    },
    "romance": { # Velvet & Wine
        "bg_c": const(0x4008),      # Deep Plum
        "well": const(0x600C),      # Muted Wine
        "text_c": const(0xFDB8),    # Rose Pink
        "accent_c": const(0xF80F),  # Hot Pink
        "highlight_c": const(0xFFFF), # White
        "panel_c": const(0x8010),   # Berry
        "footer_bg": const(0xF80F), # Rose
        "footer_text": const(0x4008) # Plum
    },
    "silent_forest": { # Misty Pine
        "bg_c": const(0x0104),      # Foggy Blue-Green
        "well": const(0x1106),      # Deep Moss
        "text_c": const(0xBDF7),    # Mist Gray
        "accent_c": const(0x4410),  # Dark Pine
        "highlight_c": const(0x07E0), # Vivid Green
        "panel_c": const(0x2208),   # Forest Floor
        "footer_bg": const(0x4410), # Pine
        "footer_text": const(0x0104) # Fog
    },
    "rainy_forest": { # Wet Slate & Teal
        "bg_c": const(0x0841),      # Wet Rock
        "well": const(0x0020),      # Deep Water
        "text_c": const(0x94B2),    # Rainy Sky
        "accent_c": const(0x2410),  # Wet Teal
        "highlight_c": const(0x041F), # Storm Blue
        "panel_c": const(0x10A2),   # Wet Pine
        "footer_bg": const(0x2410), # Teal
        "footer_text": const(0x0841) # Slate
    },
    "mellow_green": { # Sage & Cream
        "bg_c": const(0x6420),      # Sage Green
        "well": const(0x4380),      # Deep Sage
        "text_c": const(0xFFFF),    # Pure White
        "accent_c": const(0xB50A),  # Brass
        "highlight_c": const(0xE73F), # Rich Cream
        "panel_c": const(0x84E4),   # Soft Leaf
        "footer_bg": const(0xB50A), # Brass
        "footer_text": const(0x6420) # Sage
    },
    "orange_terminal": { # Retro CRT
        "bg_c": const(0x0000),      # Black
        "well": const(0x0821),      # Scanline Gray
        "text_c": const(0xFC00),    # Amber Orange
        "accent_c": const(0xFD40),  # Bright Amber
        "highlight_c": const(0xFFFF), # White Glow
        "panel_c": const(0x0821),   # Dark Gray
        "footer_bg": const(0xFC00), # Amber
        "footer_text": const(0x0000) # Black
    },
    "candy": { # Neon Pop
        "bg_c": const(0x4010),      # Deep Candy Blue
        "well": const(0x0210),      # Midnight Blue
        "text_c": const(0xFFFF),    # White
        "accent_c": const(0xF81F),  # Bubblegum
        "highlight_c": const(0x07FF), # Electric Cyan
        "panel_c": const(0x801F),   # Grape
        "footer_bg": const(0xF81F), # Bubblegum
        "footer_text": const(0xFFFF) # White
    },
    "psycho": { # Chaos Theory
        "bg_c": const(0x0000),      # Void
        "well": const(0x8000),      # Maroon
        "text_c": const(0x07E0),    # Toxic Green
        "accent_c": const(0xF81F),  # Hot Magenta
        "highlight_c": const(0xFFE0), # Acid Yellow
        "panel_c": const(0x001F),   # Electric Blue
        "footer_bg": const(0xF81F), # Magenta
        "footer_text": const(0x0000) # Void
    },
    "strawberry_cheesecake": { # Pastry Shop
        "bg_c": const(0xF79E),      # Biscuit
        "well": const(0xE71C),      # Dark Crust
        "text_c": const(0x4208),    # Cocoa Brown
        "accent_c": const(0xF800),  # Strawberry Red
        "highlight_c": const(0xFB24), # Whipped Pink
        "panel_c": const(0xFFF0),   # Cream Yellow
        "footer_bg": const(0xF800), # Strawberry
        "footer_text": const(0xFFFF) # White
    },
    "cannabis": { # High Grade
        "bg_c": const(0x0100),      # Skunk Black
        "well": const(0x0841),      # Pine Bark
        "text_c": const(0xBDD7),    # Silver Leaf
        "accent_c": const(0x07E0),  # Sticky Green
        "highlight_c": const(0x8010), # Purple Punch
        "panel_c": const(0x2304),   # Soil Brown
        "footer_bg": const(0x07E0), # Sticky Green
        "footer_text": const(0x0100) # Black
    }
}

# ---- theme_manager.py ----

from picoware.system.vector import Vector

def load_theme(settings):
    """Resolve and return the current theme dictionary."""
    # Handle case-insensitivity and provide a safe fallback
    theme_name = settings.config.get("theme", "dark").lower().replace(" ", "_")

    if theme_name in THEMES:
        return THEMES[theme_name]

    # Fallback to standard dark theme if key is missing
    return THEMES["dark"]

def draw_battery_icon(draw, pos, percent, color):
    """Draw a small battery icon with fill level."""
    w, h = 16, 8
    draw.rect(pos, Vector(w, h), color)
    draw.fill_rectangle(Vector(pos.x + w, pos.y + 2), Vector(2, 4), color)
    if percent > 0:
        fill_w = max(1, int((percent / 100) * (w - 4)))
        draw.fill_rectangle(Vector(pos.x + 2, pos.y + 2), Vector(fill_w, 4), color)

def draw_clock_icon(draw, pos, color):
    """Draw a small clock icon."""
    draw.rect(pos, Vector(8, 8), color)
    draw.fill_rectangle(Vector(pos.x + 3, pos.y + 1), Vector(1, 4), color)
    draw.fill_rectangle(Vector(pos.x + 3, pos.y + 4), Vector(4, 1), color)

_last_fetch_attempt = 0

def render_header_extras(ui, sw, bar_h):
    """Draw battery and time in the header area."""
    global _last_fetch_attempt
    curr_x = sw - 10

    # Battery
    if ui.view_manager and ui.view_manager.input_manager:
        try:
            bat = ui.view_manager.input_manager.battery
            bat_str = f"{bat}%"
            curr_x -= (len(bat_str) * 6 + 2)
            ui.draw.text(Vector(curr_x, (bar_h - 12) // 2 + 1), bat_str, ui.theme["footer_text"])
            curr_x -= 20
            draw_battery_icon(ui.draw, Vector(curr_x, (bar_h - 8) // 2), bat, ui.theme["footer_text"])
        except Exception as e:
            print(f"[DEBUG] Header Battery Error: {e}")

    # Time
    if ui.view_manager and ui.view_manager.time:
        t_obj = ui.view_manager.time

        # Auto-fetch if WiFi is connected but time has not been set yet
        if not t_obj.is_set and not t_obj.is_fetching:
            import time
            now = time.ticks_ms()
            if time.ticks_diff(now, _last_fetch_attempt) > 15000:
                _last_fetch_attempt = now
                try:
                    if ui.view_manager.wifi and ui.view_manager.wifi.is_connected():
                        t_obj.fetch(ui.view_manager.gmt_offset)
                except Exception:
                    pass

        if t_obj.is_set:
            try:
                date = t_obj.rtc.datetime()
                time_str = f"{date[4]:02d}:{date[5]:02d}"
                curr_x -= (len(time_str) * 6 + 15)
                ui.draw.text(Vector(curr_x + 12, (bar_h - 12) // 2 + 1), time_str, ui.theme["footer_text"])
                draw_clock_icon(ui.draw, Vector(curr_x, (bar_h - 8) // 2), ui.theme["footer_text"])
            except Exception as e:
                print(f"[DEBUG] Header Time Error: {e}")

LANG_DATA = {'en': {'app_name': 'VibesMP',
        'back': 'Back',
        'confirm': 'Confirm',
        'delete': 'Delete',
        'editor_bg': 'Background',
        'editor_color': 'Change Color',
        'editor_save': 'Save',
        'first_run_msg': 'Scan SD card for music now?',
        'first_run_title': 'VibesMP',
        'hint_confirm': 'LR:Choose ENT:Confirm',
        'hint_continue': 'ENT:Continue',
        'hint_library': 'UD:Scroll LR:Folder OK:Open/Action BACK:Back',
        'hint_np_controls': 'TAB:Lists P:Pause ESC:Stop [/:Seek <>:Trk L:Loop S:Shuf V:.,',
        'hint_np_lib': 'TAB:Player UD:Scroll LR:Panels OK:Add/Expand',
        'hint_np_pls': 'TAB:Player UD:Scroll LR:Panels OK:Load N:New DEL:Del',
        'hint_np_trk': 'TAB:Player UD:Scroll LR:Panels OK:Play DEL:Rem',
        'hint_playlist_ed': 'LR:Panel UD:Sel OK:Add/Rem BACK:Menu',
        'hint_playlist_sel': 'UD:Scroll OK:Load DEL:Delete BACK:Menu',
        'lib_action_add_current': 'Add to Current Playlist',
        'lib_action_add_favorite': 'Add Favorite',
        'lib_action_create_playlist': 'Create Playlist',
        'lib_action_play_next': 'Play Next',
        'lib_action_play_now': 'Play Now',
        'lib_action_remove_favorite': 'Remove Favorite',
        'lib_action_remove_library': 'Remove from Library',
        'lib_action_show_info': 'Show Info',
        'lib_actions': 'Actions',
        'lib_albums': 'Albums',
        'lib_all_songs': 'All Songs',
        'lib_artists': 'Artists',
        'lib_cleanup': 'Cleanup',
        'lib_favorites': 'Favorites',
        'lib_favorites_cleared': 'Favorites cleared',
        'lib_filters': 'Filters',
        'lib_folders': 'Folders',
        'lib_genres': 'Genres',
        'lib_info': 'Track Info',
        'lib_recently_added': 'Recently Added',
        'lib_removed': 'Removed',
        'lib_scan': 'Scan Library',
        'lib_scan_added': 'Added',
        'lib_scan_failed': 'Failed',
        'lib_scan_found': 'Found',
        'lib_scan_options': 'Scan Options',
        'lib_scan_removed': 'Removed',
        'lib_scan_total': 'Total',
        'lib_scan_unchanged': 'Unchanged',
        'lib_search': 'Search',
        'lib_sort': 'Sort',
        'lib_stats': 'Library Stats',
        'lib_tracks': 'Tracks',
        'library': 'Library',
        'loop_all': 'Loop: All',
        'loop_none': 'Loop: No',
        'loop_one': 'Loop: One',
        'menu_editor': 'Editor',
        'menu_help': 'Help',
        'menu_library': 'Library',
        'menu_play_file': 'Play File',
        'menu_player': 'Player',
        'menu_playlist': 'Playlist',
        'menu_playlist_editor': 'Playlist Editor',
        'menu_playlist_manager': 'Playlist Manager',
        'menu_playlists': 'Playlists',
        'menu_settings': 'Settings',
        'new_playlist': '+ New Playlist',
        'no_track': 'No Track',
        'now_playing': 'Now Playing',
        'off': 'OFF',
        'on': 'ON',
        'paused': 'Paused',
        'playing': 'Playing',
        'playlist': 'Tracks',
        'playlist_del': 'Delete Playlist',
        'playlist_editor': 'Playlist Editor',
        'playlist_new': 'New Playlist',
        'playlist_selector': 'Select Playlist',
        'playlists': 'Playlists',
        'refresh_library': 'Refresh Library',
        'scan_complete_msg': 'Found {} MP3 files.',
        'scan_complete_title': 'Scan Complete',
        'scanning_title': 'Scanning SD Card...',
        'set_auto_expand': 'Auto-Expand Lib',
        'set_autoplay': 'Auto-Play Next',
        'set_focus_timeout': 'Focus Timeout',
        'set_seek': 'Seek Step',
        'set_shuffle': 'Shuffle',
        'set_volume': 'Volume',
        'stopped': 'Stopped'}}

HELP_TEXT = {'en.txt': 'VibesMP is a dedicated MicroPython audio application engineered for RP2350 '
           'microcontrollers. It provides high-fidelity MP3 playback leveraging '
           'hardware-accelerated decoding capabilities while maintaining a low memory footprint '
           'and high responsiveness during concurrent SD card file operations and user interface '
           'rendering tasks on embedded hardware platforms.\n'
           '\n'
           'The application implements ID3v2 tag parsing for metadata extraction, real-time JPEG '
           'and BMP album art scaling and display, gapless playback transition logic, dynamic '
           'playlist management including creation and modification, and a three-column '
           'navigational system for efficient library browsing, track selection, and playlist '
           'switching across various storage directories.\n'
           '\n'
           'Available configuration parameters include auto-play toggle for sequential track '
           'advancement, shuffle and loop mode selection, visual theme presets using RGB565 '
           'palettes, adjustable seek intervals from one to fifteen seconds, focus timeout '
           'management, and persistent storage of all preferences.\n'
           '\n'
           'Navigational controls utilize the standard D-Pad mapping: Up and Down for vertical '
           'list scrolling, Left and Right for column switching and volume adjustment, Center '
           'button for selection confirmation and play and pause toggling, Back button for view '
           'regression or application termination, and specialized alphanumeric mapping for '
           'naming.\n'
           '\n'
           'Made by Slasher006 with the help of Gemini, 2026. This project showcases advanced '
           'MicroPython implementation techniques, efficient memory management strategies for '
           'resource-constrained embedded systems, and collaborative software development between '
           'human engineers and artificial intelligence to deliver a superior multimedia '
           'experience on the RP2350 microcontroller platform.\n',
 'first_start_en.txt': 'Welcome to VibesMP! To begin your musical journey, please perform an '
                       'initial scan of your SD card to index all available MP3 files. If you add '
                       'new tracks to your collection later, simply use the "Scan Library" option '
                       'in the main menu to refresh your database and ensure all new music is '
                       'correctly detected and displayed within the application.\n'}


_translations = {}
_fallback = LANG_DATA.get("en", {})
_current_lang = ""

def load_language():
    global _translations, _fallback, _current_lang
    _fallback = LANG_DATA.get("en", {})
    _translations = _fallback
    _current_lang = "en"

def t(key):
    res = _translations.get(key)
    if res is not None:
        return res
    return _fallback.get(key, key)

def get_help_text(first_start=False):
    prefix = "first_start_" if first_start else ""
    return HELP_TEXT.get(prefix + "en.txt") or ""

# ---- settings_view.py ----

from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER

def _move_menu_selection(menu, delta):
    count = len(menu.items) if menu and menu.items else 0
    if count <= 0:
        return
    if getattr(menu, "use_lvgl", False) and getattr(menu, "_lvgl_list", None) is not None:
        if delta < 0:
            menu.scroll_up(swap=False)
        else:
            menu.scroll_down(swap=False)
        return
    menu._selected_index = (menu._selected_index + delta) % count

def update_settings_menu(app):
    curr_idx = app.settings_menu.selected_index if app.settings_menu else 0
    app.settings_menu.clear()
    app.settings_menu.add_item(f"{t('set_autoplay')}: {t('on') if app.settings.config['auto_play_next'] else t('off')}")
    app.settings_menu.add_item(f"{t('set_shuffle')}: {t('on') if app.settings.config['shuffle'] else t('off')}")
    app.settings_menu.add_item(f"{t('set_auto_expand')}: {t('on') if app.settings.config.get('auto_expand_library', True) else t('off')}")
    # Format theme name for display: replace underscore with space and uppercase
    display_theme = app.settings.config['theme'].replace('_', ' ').upper()
    app.settings_menu.add_item(f"Theme: {display_theme}")
    app.settings_menu.add_item(f"Time Format: {'24H' if app.settings.config.get('time_24h', True) else '12H'}")
    app.settings_menu.add_item(f"{t('set_volume')}: {app.settings.config.get('volume', 100)}%")
    app.settings_menu.add_item(f"{t('set_seek')}: {app.settings.config.get('seek_length', 5)}s")
    app.settings_menu.add_item(f"{t('set_focus_timeout')}: {app.settings.config.get('focus_timeout', 10)}s")
    app.settings_menu.add_item(t("back"))
    if curr_idx < len(app.settings_menu.items): app.settings_menu.set_selected(curr_idx)

def handle_settings_input(app, button):
    from vibesmp_lib.ui_utils import VIEW_MENU
    from picoware.system.buttons import BUTTON_BACK
    if button == BUTTON_BACK:
        app._switch_view(VIEW_MENU)
        return
    if button == BUTTON_UP: _move_menu_selection(app.settings_menu, -1); app.needs_refresh = True
    elif button == BUTTON_DOWN: _move_menu_selection(app.settings_menu, 1); app.needs_refresh = True
    elif button == BUTTON_CENTER:
        sel = app.settings_menu.selected_index
        if sel == 0: app.settings.toggle("auto_play_next"); update_settings_menu(app)
        elif sel == 1: app.settings.toggle("shuffle"); update_settings_menu(app)
        elif sel == 2: app.settings.toggle("auto_expand_library"); update_settings_menu(app)
        elif sel == 3:
            app.settings.next_theme()
            # load_theme is provided by consolidated core
            app.ui.theme = load_theme(app.settings)
            update_settings_menu(app)
        elif sel == 4: app.settings.next_time_format(); update_settings_menu(app)
        elif sel == 5: app.settings.next_volume(); update_settings_menu(app)
        elif sel == 6: app.settings.next_seek_length(); update_settings_menu(app)
        elif sel == 7: app.settings.next_focus_timeout(); update_settings_menu(app)
        elif sel == 8: app._switch_view(VIEW_MENU)
        app.needs_refresh = True

def render_settings(app, ui, force_full=False):
    ui.render_menu(app.settings_menu, t("menu_settings"), force_full=force_full)

# ---- app_navigation.py ----


def _move_menu_selection(menu, delta):
    count = len(menu.items) if menu and menu.items else 0
    if count <= 0:
        return
    if getattr(menu, "use_lvgl", False) and getattr(menu, "_lvgl_list", None) is not None:
        if delta < 0:
            menu.scroll_up(swap=False)
        else:
            menu.scroll_down(swap=False)
        return
    menu._selected_index = (menu._selected_index + delta) % count

def switch_view(app, view_id):
    from vibesmp_lib.ui_utils import VIEW_MENU, VIEW_SETTINGS, VIEW_PLAYLIST_SELECTOR, VIEW_NOW_PLAYING
    """Unified view switcher for VibesApp."""
    app.ui.current_view = view_id
    app.needs_refresh = True
    # View-specific reset logic
    if view_id == VIEW_MENU:
        if hasattr(app, "main_menu") and app.main_menu:
            app.main_menu.set_selected(0)
    elif view_id == VIEW_SETTINGS:
        from vibesmp_lib.resources import update_settings_menu
        update_settings_menu(app)
    elif view_id == VIEW_PLAYLIST_SELECTOR:
        app.refresh_playlists()
    elif view_id == VIEW_NOW_PLAYING:
        if hasattr(app, "_prime_now_playing_lists"):
            app._prime_now_playing_lists()
    return True

def handle_main_menu_input(app, button):
    from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK
    from vibesmp_lib.ui_utils import VIEW_NOW_PLAYING, VIEW_LIBRARY, VIEW_SETTINGS
    if button == BUTTON_BACK:
        app.view_manager.back()
        return True
    if button == BUTTON_UP:
        _move_menu_selection(app.main_menu, -1); app.needs_refresh = True
    elif button == BUTTON_DOWN:
        _move_menu_selection(app.main_menu, 1); app.needs_refresh = True
    elif button == BUTTON_CENTER:
        sel = app.main_menu.selected_index
        if sel == 0: switch_view(app, VIEW_NOW_PLAYING)
        elif sel == 1: switch_view(app, VIEW_LIBRARY)
        elif sel == 2: switch_view(app, VIEW_SETTINGS)
        elif sel == 3:
            import vibesmp_lib.resources as d
            from vibesmp_lib.resources import get_help_text, t
            help_text = get_help_text()
            d.open_alert(app, t("menu_help"), help_text)
        app.needs_refresh = True
    return True

# ---- dialogs.py ----

from picoware.system.buttons import (
    BUTTON_CENTER, BUTTON_BACK, BUTTON_ENTER, BUTTON_LEFT, BUTTON_RIGHT,
    BUTTON_BACKSPACE, BUTTON_DELETE
)

def open_alert(app, title, message, callback=None):
    app.dialog_type = "alert"
    app.dialog_title = title
    app.dialog_message = message
    app.dialog_callback = callback
    app.dialog_scroll_idx = 0
    _show(app)

def open_confirm(app, title, message, callback, cancel_callback=None):
    app.dialog_type = "confirm"
    app.dialog_title = title
    app.dialog_message = message
    app.dialog_callback = callback
    app.dialog_cancel_callback = cancel_callback
    app.dialog_selected_idx = 0
    app.dialog_scroll_idx = 0
    _show(app)

def open_input(app, title, initial_text, callback, max_len=20):
    app.dialog_type = "input"
    app.dialog_title = title
    app.dialog_buffer = initial_text
    app.dialog_cursor_pos = len(initial_text)
    app.dialog_callback = callback
    app.dialog_max_len = max_len
    _show(app)

def _show(app):
    from vibesmp_lib.ui_utils import VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT
    # Only save last view if we are not already in a modal dialog
    # This ensures chained dialogs (Confirm -> Alert) return to the original view
    curr = app.ui.current_view
    if curr not in (VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT):
        app.dialog_last_view = curr

    view = VIEW_INPUT_MODAL if app.dialog_type == "input" else VIEW_CONFIRM if app.dialog_type == "confirm" else VIEW_ALERT
    app._switch_view(view)
    app.needs_refresh = True

def handle_dialog_input(app, button):
    from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN
    from vibesmp_lib.ui_utils import VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT
    if button == BUTTON_BACK:
        app._switch_view(app.dialog_last_view)
        app.needs_refresh = True
        return True

    if app.dialog_type in ("confirm", "alert"):
        if button == BUTTON_UP:
            if app.dialog_scroll_idx > 0:
                app.dialog_scroll_idx -= 1; app.needs_refresh = True
            return True
        elif button == BUTTON_DOWN:
            # We don't have total lines here easily, but we'll cap it in render
            app.dialog_scroll_idx += 1; app.needs_refresh = True
            return True

    if app.dialog_type == "confirm":
        if button == BUTTON_LEFT: app.dialog_selected_idx = 0; app.needs_refresh = True
        elif button == BUTTON_RIGHT: app.dialog_selected_idx = 1; app.needs_refresh = True
        elif button in (BUTTON_CENTER, BUTTON_ENTER):
            old = (app.dialog_type, app.dialog_title, app.dialog_callback)
            if app.dialog_selected_idx == 0 and app.dialog_callback: app.dialog_callback()
            elif app.dialog_selected_idx == 1 and hasattr(app, "dialog_cancel_callback") and app.dialog_cancel_callback:
                app.dialog_cancel_callback()
            new_dialog = app.ui.current_view in (VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT) and old != (app.dialog_type, app.dialog_title, app.dialog_callback)
            if not new_dialog:
                app._switch_view(app.dialog_last_view)
            app.needs_refresh = True
        return True

    elif app.dialog_type == "alert":
        if button in (BUTTON_CENTER, BUTTON_ENTER):
            old = (app.dialog_type, app.dialog_title, app.dialog_callback)
            if app.dialog_callback: app.dialog_callback()
            new_dialog = app.ui.current_view in (VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT) and old != (app.dialog_type, app.dialog_title, app.dialog_callback)
            if not new_dialog:
                app._switch_view(app.dialog_last_view)
            app.needs_refresh = True
        return True

    elif app.dialog_type == "input":
        if button in (BUTTON_CENTER, BUTTON_ENTER):
            old = (app.dialog_type, app.dialog_title, app.dialog_callback)
            if app.dialog_callback: app.dialog_callback(app.dialog_buffer)
            new_dialog = app.ui.current_view in (VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT) and old != (app.dialog_type, app.dialog_title, app.dialog_callback)
            if not new_dialog:
                app._switch_view(app.dialog_last_view)
            app.needs_refresh = True
        elif button == BUTTON_LEFT:
            if app.dialog_cursor_pos > 0: app.dialog_cursor_pos -= 1; app.needs_refresh = True
        elif button == BUTTON_RIGHT:
            if app.dialog_cursor_pos < len(app.dialog_buffer): app.dialog_cursor_pos += 1; app.needs_refresh = True
        elif button == BUTTON_BACKSPACE:
            if app.dialog_cursor_pos > 0:
                app.dialog_buffer = app.dialog_buffer[:app.dialog_cursor_pos-1] + app.dialog_buffer[app.dialog_cursor_pos:]
                app.dialog_cursor_pos -= 1; app.needs_refresh = True
        elif button == BUTTON_DELETE:
            if app.dialog_cursor_pos < len(app.dialog_buffer):
                app.dialog_buffer = app.dialog_buffer[:app.dialog_cursor_pos] + app.dialog_buffer[app.dialog_cursor_pos+1:]; app.needs_refresh = True
        elif button in app._char_map:
            max_len = getattr(app, "dialog_max_len", 20)
            if len(app.dialog_buffer) < max_len:
                char = app._char_map[button]
                if hasattr(app, "view_manager") and app.view_manager.input_manager.was_capitalized:
                    char = char.upper()
                app.dialog_buffer = app.dialog_buffer[:app.dialog_cursor_pos] + char + app.dialog_buffer[app.dialog_cursor_pos:]
                app.dialog_cursor_pos += 1; app.needs_refresh = True
        return True
    return False

def render_dialog(app, ui):
    if app.dialog_type == "confirm":
        ui.render_confirm(app.dialog_title, app.dialog_message, app.dialog_selected_idx, app.dialog_scroll_idx)
    elif app.dialog_type == "alert":
        ui.render_modal(app.dialog_title, app.dialog_message, "OK", app.dialog_scroll_idx)
    elif app.dialog_type == "input":
        ui.render_input_dialog(app.dialog_title, app.dialog_buffer, app.dialog_cursor_pos, False)
