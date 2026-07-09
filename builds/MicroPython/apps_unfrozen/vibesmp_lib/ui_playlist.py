# VibesMP playlist renderers.

# ---- ui_playlist.py ----

from picoware.system.vector import Vector
from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_GREEN
from vibesmp_lib.resources import t
from vibesmp_lib.utils import get_filename
from vibesmp_lib.ui_utils import draw_panel, draw_scrollable_list

def _visible_window(sel_idx, total, view_h, item_h):
    if total <= 0:
        return (0, 0)
    max_items = max(1, view_h // item_h) if item_h > 0 else 1
    max_start = max(0, total - max_items)
    start_idx = min(max(0, sel_idx - (max_items // 2)), max_start)
    end_idx = min(total, start_idx + max_items)
    return (start_idx, end_idx)

def render_playlist_selector(ui, playlists, selected_idx, force_full=False, swap=True, nav_fast=False):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    header_title = t("playlist_selector")
    header_updated = False
    item_h = 20
    list_pos = Vector(10, 25)
    list_size = Vector(sw - 20, sh - 70)
    state = getattr(ui, "_playlist_selector_state", {})
    can_partial = False

    if force_full:
        ui.draw_background()
        ui.render_header_footer(header_title)
    else:
        header_updated = ui.check_header_update(header_title)

    def _format_pl(i, p):
        if p == "..": return ".."
        name = get_filename(p)
        if name.lower().endswith(".json"): name = name[:-5]
        return f"{i+1}. {name}"

    if nav_fast and playlists:
        prev_idx = state.get("selected_idx", selected_idx)
        prev_count = state.get("count", len(playlists))
        prev_window = _visible_window(prev_idx, prev_count, list_size.y, item_h)
        curr_window = _visible_window(selected_idx, len(playlists), list_size.y, item_h)
        can_partial = prev_count == len(playlists) and prev_window == curr_window

    drew = force_full or header_updated
    if force_full or not can_partial:
        draw_scrollable_list(ui.draw, list_pos, list_size, playlists, selected_idx, True, ui.theme, _format_pl, item_h=item_h, row_cache=getattr(ui, "list_row_cache", None), cache_token=("playlist_selector", len(playlists)))
        drew = True
    elif playlists:
        prev_idx = state.get("selected_idx", selected_idx)
        draw_scrollable_list(
            ui.draw,
            list_pos,
            list_size,
            playlists,
            selected_idx,
            True,
            ui.theme,
            _format_pl,
            item_h=item_h,
            row_cache=getattr(ui, "list_row_cache", None),
            cache_token=("playlist_selector", len(playlists)),
            row_only_tick=True,
            redraw_indices=(prev_idx, selected_idx),
        )
        drew = True

    # Help Footer Text (Overlay on the orange footer)
    footer_y = sh - 14 # (16 - 12) // 2 = 2px offset. sh - 16 + 2 = sh - 14
    if force_full or header_updated:
        ui.draw.text(Vector(10, footer_y), t("hint_playlist_sel"), ui.theme["footer_text"])
    ui._playlist_selector_state = {"selected_idx": selected_idx, "count": len(playlists)}
    if swap and drew: ui.draw.swap()


def render_playlist_editor(ui, library_items, playlist, force_full=False, swap=True, nav_fast=False):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    header_title = t("playlist_editor")
    header_updated = False
    item_h = 15
    state = getattr(ui, "_playlist_editor_state", {})
    if force_full:
        ui.draw_background()
        ui.render_header_footer(header_title)
    else:
        header_updated = ui.check_header_update(header_title)

    col_w = sw // 2
    list_h = sh - 65
    lib_list_pos = Vector(0, 36)
    lib_list_size = Vector(col_w, list_h - 16)
    pl_list_pos = Vector(col_w, 36)
    pl_list_size = Vector(sw - col_w, list_h - 16)
    same_pane = state.get("active_pane", playlist.active_pane) == playlist.active_pane
    can_partial = False
    partial_target = None
    if nav_fast and same_pane:
        if playlist.active_pane == 0:
            prev_idx = state.get("lib_idx", playlist.editor_library_idx)
            prev_count = state.get("lib_count", len(library_items))
            prev_window = _visible_window(prev_idx, prev_count, lib_list_size.y, item_h)
            curr_window = _visible_window(playlist.editor_library_idx, len(library_items), lib_list_size.y, item_h)
            can_partial = prev_count == len(library_items) and prev_window == curr_window
            partial_target = "lib"
        else:
            prev_idx = state.get("pl_idx", playlist.editor_playlist_idx)
            prev_count = state.get("pl_count", len(playlist.tracks))
            prev_window = _visible_window(prev_idx, prev_count, pl_list_size.y, item_h)
            curr_window = _visible_window(playlist.editor_playlist_idx, len(playlist.tracks), pl_list_size.y, item_h)
            can_partial = prev_count == len(playlist.tracks) and prev_window == curr_window
            partial_target = "pl"
    drew = force_full or header_updated

    # Library Pane
    l_h_c = ui.theme["accent_c"] if playlist.active_pane == 0 else ui.theme["panel_c"]
    if force_full or not can_partial:
        draw_panel(ui.draw, Vector(0, 20), Vector(col_w, list_h), t("library"), ui.theme["panel_c"], l_h_c, TFT_WHITE)
        draw_scrollable_list(ui.draw, lib_list_pos, lib_list_size, library_items, playlist.editor_library_idx, playlist.active_pane == 0, ui.theme, lambda i, x: get_filename(x), row_cache=getattr(ui, "list_row_cache", None), cache_token=("playlist_editor_lib", len(library_items)))

    # Playlist Pane
    p_h_c = ui.theme["accent_c"] if playlist.active_pane == 1 else ui.theme["panel_c"]
    if force_full or not can_partial:
        draw_panel(ui.draw, Vector(col_w, 20), Vector(sw - col_w, list_h), t("playlist"), ui.theme["panel_c"], p_h_c, TFT_WHITE)
        draw_scrollable_list(ui.draw, pl_list_pos, pl_list_size, playlist.tracks, playlist.editor_playlist_idx, playlist.active_pane == 1, ui.theme, lambda i, x: get_filename(x), row_cache=getattr(ui, "list_row_cache", None), cache_token=("playlist_editor_pl", len(playlist.tracks)))

    if can_partial and partial_target == "lib":
        prev_idx = state.get("lib_idx", playlist.editor_library_idx)
        draw_scrollable_list(
            ui.draw,
            lib_list_pos,
            lib_list_size,
            library_items,
            playlist.editor_library_idx,
            True,
            ui.theme,
            lambda i, x: get_filename(x),
            row_cache=getattr(ui, "list_row_cache", None),
            cache_token=("playlist_editor_lib", len(library_items)),
            row_only_tick=True,
            redraw_indices=(prev_idx, playlist.editor_library_idx),
        )
        drew = True
    elif can_partial and partial_target == "pl":
        prev_idx = state.get("pl_idx", playlist.editor_playlist_idx)
        draw_scrollable_list(
            ui.draw,
            pl_list_pos,
            pl_list_size,
            playlist.tracks,
            playlist.editor_playlist_idx,
            True,
            ui.theme,
            lambda i, x: get_filename(x),
            row_cache=getattr(ui, "list_row_cache", None),
            cache_token=("playlist_editor_pl", len(playlist.tracks)),
            row_only_tick=True,
            redraw_indices=(prev_idx, playlist.editor_playlist_idx),
        )
        drew = True

    # Help Footer Text (Overlay on the orange footer)
    footer_y = sh - 14 # (16 - 12) // 2 = 2px offset. sh - 16 + 2 = sh - 14
    if force_full or header_updated:
        ui.draw.text(Vector(10, footer_y), t("hint_playlist_ed"), ui.theme["footer_text"])
    ui._playlist_editor_state = {
        "active_pane": playlist.active_pane,
        "lib_idx": playlist.editor_library_idx,
        "pl_idx": playlist.editor_playlist_idx,
        "lib_count": len(library_items),
        "pl_count": len(playlist.tracks),
    }
    if swap and drew: ui.draw.swap()
