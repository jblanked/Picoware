# VibesMP UI shell.

# ---- ui_library.py ----

from picoware.system.vector import Vector
from vibesmp_lib.resources import t
from vibesmp_lib.ui_utils import draw_scrollable_list


def format_library_item(i, item):
    if isinstance(item, tuple):
        label = item[1] if len(item) > 1 else str(item)
        return label
    if not isinstance(item, dict):
        return str(item)

    kind = item.get("kind", "")
    label = item.get("label", "") or item.get("title", "") or item.get("path", "")

    if kind == "category":
        return label
    if kind == "bucket":
        return "{} ({})".format(label, item.get("count", 0))
    if kind == "collection":
        return "{} ({})".format(label, item.get("count", len(item.get("tracks", []))))
    if kind == "folder":
        depth = int(item.get("depth", 0))
        prefix = "  " * depth
        prefix += "- " if item.get("expanded", False) else "+ "
        return prefix + label
    if kind == "track":
        depth = int(item.get("depth", 0))
        prefix = "  " * depth
        fav = "* " if item.get("favorite", False) else ""
        title = item.get("title", label)
        artist = item.get("artist", "")
        if artist and artist != "Unknown Artist":
            return prefix + fav + title + " - " + artist
        return prefix + fav + title
    return label


def render_library_browser(ui, title, items, selected_idx, force_full=False, swap=True, nav_fast=False):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    header_updated = False
    item_h = 18
    list_pos = Vector(8, 26)
    list_size = Vector(sw - 16, sh - 68)

    if force_full:
        ui.draw_background()
        ui.render_header_footer(title)
    else:
        header_updated = ui.check_header_update(title)

    drew = force_full or header_updated
    cache_token = ("library_browser", title, len(items))
    draw_scrollable_list(
        ui.draw,
        list_pos,
        list_size,
        items,
        selected_idx,
        True,
        ui.theme,
        lambda i, x: format_library_item(i, x),
        item_h=item_h,
        row_cache=getattr(ui, "list_row_cache", None),
        cache_token=cache_token,
    )
    drew = True

    if force_full or header_updated:
        footer_y = sh - 16
        ui.draw.text(Vector(10, footer_y + 2), t("hint_library"), ui.theme["footer_text"])

    ui._library_browser_state = {"selected_idx": selected_idx, "count": len(items)}
    if swap and drew:
        ui.draw.swap()

# ---- ui.py ----

from picoware.system.vector import Vector
from picoware.system.colors import TFT_BLACK, TFT_WHITE
from vibesmp_lib.resources import t

# View Constants
VIEW_MENU = 1
VIEW_NOW_PLAYING = 2
VIEW_SETTINGS = 4
VIEW_LIBRARY = 5
VIEW_PLAYLIST_SELECTOR = 7
VIEW_PLAYLIST_EDITOR = 8
VIEW_MODAL = 9
VIEW_KEYBOARD = 10
VIEW_INPUT_MODAL = 11
VIEW_CONFIRM = 12
VIEW_ALERT = 13

class UI:
    def __init__(self, draw, theme, view_manager=None, settings=None):
        self.draw = draw
        self.theme = theme
        self.view_manager = view_manager
        self.settings = settings
        self.last_np_state = {}
        self.playlist_idx = 0
        self.l_idx = 0
        self.active_col = 1
        self.focus = 0
        self.btn_idx = 3
        self._v_zero = Vector(0, 0)
        self._v_bar = Vector(self.draw.size.x, 20)
        self._menus_initialized = False
        self.current_view = 1 # VIEW_MENU
        self.last_view = 1
        self.scroll_pos = 0
        self.scroll_pos2 = 0  # Independent scroll for artist/album line
        self.last_scroll_time = 0
        self.cover_drawn_path = None
        self.cover_buffer = None
        self.cover_buffer_path = None
        self.list_row_cache = {}
        self.active_list_overflow = False
        self._marquee_marker = None
        self._marquee_start_ms = 0
        self._last_sel_by_col = {0: -1, 1: -1, 2: -1}
        self.cover_draw_count = 0
        self._playlist_selector_state = {}
        self._playlist_editor_state = {}
        self.perf_counters = None

    def check_header_update(self, title):
        time_sec = 0
        bat_val = -1
        if self.view_manager:
            if self.view_manager.time and self.view_manager.time.is_set:
                try:
                    date = self.view_manager.time.rtc.datetime()
                    time_sec = date[4] * 60 + date[5]
                except Exception:
                    pass
            if self.view_manager.input_manager:
                try:
                    bat_val = self.view_manager.input_manager.battery
                except Exception:
                    pass
        if not hasattr(self, "_last_header_time_sec") or self._last_header_time_sec != time_sec or self._last_header_bat != bat_val:
            self._last_header_time_sec = time_sec
            self._last_header_bat = bat_val
            self.render_header_footer(title)
            return True
        return False

    def set_view(self, view):
        self.current_view = view

    def draw_background(self):
        self.draw.clear(color=self.theme["bg_c"])

    def render_header_footer(self, title):
        from vibesmp_lib.themes import render_header_extras
        sw, sh = self.draw.size.x, self.draw.size.y
        bar_h = 20
        # Header
        self.draw.fill_round_rectangle(self._v_zero, Vector(sw, bar_h), 5, self.theme["accent_c"])
        self.draw.text(Vector(10, (bar_h - 12) // 2), title, self.theme["footer_text"])

        render_header_extras(self, sw, bar_h)

        # Footer
        self.draw.fill_round_rectangle(Vector(0, sh - bar_h), Vector(sw, bar_h), 5, self.theme["footer_bg"])
        self.draw.fill_rectangle(Vector(0, sh - bar_h), Vector(sw, 1), TFT_BLACK)

    def render_menu(self, menu_list, title="VibesMP", force_full=False, swap=True):
        header_title = title
        if header_title == "VibesMP":
            header_title = t("app_name") if t("app_name") != "app_name" else "VibesMP"
        header_updated = False
        if force_full:
            self.draw_background()
            self.render_header_footer(header_title)
        else:
            header_updated = self.check_header_update(header_title)
        if menu_list and force_full:
            menu_list.background_color = self.theme["bg_c"]
            menu_list.text_color = self.theme["text_c"]
            menu_list.accent_color = self.theme["accent_c"]
            menu_list.panel_color = self.theme["panel_c"]
            menu_list.draw(swap=False)
        if swap and (force_full or header_updated): self.draw.swap()

    def render_library_view(self, menu_list, track_count, title="VibesMP", force_full=False, swap=True):
        self.render_menu(menu_list, title, force_full, swap)

    def render_now_playing(self, track_name, is_playing, loop_mode, playlist=None, player=None, shuffle=False, force_full=False, seek_msg="", focus=0, btn_idx=3, playlists=None, playlist_idx=0, library_items=None, l_idx=0, active_col=1, swap=True, library=None, list_tick=False, nav_fast=False):
        from vibesmp_lib.ui_player import render_now_playing
        render_now_playing(self, track_name, is_playing, loop_mode, playlist, player, shuffle, force_full, seek_msg, focus, btn_idx, playlists, playlist_idx, library_items, l_idx, active_col, swap, self.settings, library, list_tick, nav_fast)

    def render_confirm(self, title, message, selected_idx, scroll_idx=0):
        from vibesmp_lib.ui_playlist import render_confirm
        render_confirm(self, title, message, selected_idx, scroll_idx)

    def render_modal(self, title, message, button_text="OK", scroll_idx=0):
        from vibesmp_lib.ui_playlist import render_modal
        render_modal(self, title, message, button_text, scroll_idx)

    def render_progress_modal(self, title, current_item, count):
        from vibesmp_lib.ui_playlist import render_progress_modal
        render_progress_modal(self, title, current_item, count)

    def render_input_dialog(self, title, text, cursor_pos=0, force_full=False):
        from vibesmp_lib.ui_playlist import render_input_dialog
        render_input_dialog(self, title, text, cursor_pos, force_full)
