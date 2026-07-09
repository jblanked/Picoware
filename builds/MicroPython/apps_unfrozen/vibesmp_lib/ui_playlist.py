# VibesMP dialog renderers.

# ---- dialog renderers ----

from picoware.system.vector import Vector
from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_GREEN
from vibesmp_lib.resources import t
from vibesmp_lib.utils import get_filename
from vibesmp_lib.ui_utils import (
    draw_metadata_well,
    draw_panel,
    draw_player_button,
    draw_progress_bar,
    draw_scrollbar,
    draw_scrollable_list,
)

def _wrap_text(text, limit):
    res = []
    lines = text.replace("\\n", "\n").split("\n")
    for raw in lines:
        words = raw.split(" ")
        if not words:
            res.append("")
            continue
        line = ""
        for word in words:
            if not word:
                continue
            while len(word) > limit:
                if line:
                    res.append(line)
                    line = ""
                res.append(word[:limit])
                word = word[limit:]
            if not line:
                line = word
            elif len(line) + 1 + len(word) <= limit:
                line += " " + word
            else:
                res.append(line)
                line = word
        if line:
            res.append(line)
    return res

def _dialog_text_limit(width_px, inner_padding=24, scrollbar_w=12, char_w=8):
    usable_w = max(0, width_px - inner_padding - scrollbar_w)
    return max(1, usable_w // char_w)

def render_progress_modal(ui, title, current_item, count):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    ui.draw_background()

    m_h, m_w = 120, sw - 40
    m_x, m_y = 20, (sh - m_h) // 2

    draw_panel(ui.draw, Vector(m_x, m_y), Vector(m_w, m_h), title, ui.theme["panel_c"], ui.theme["accent_c"], ui.theme["footer_text"])

    # Track Count
    ui.draw.text(Vector(m_x + 10, m_y + 30), f"Found: {count} tracks", ui.theme["text_c"])

    # Current Folder (Truncated)
    folder_text = current_item if len(current_item) < 25 else "..." + current_item[-22:]
    ui.draw.text(Vector(m_x + 10, m_y + 50), folder_text, ui.theme["footer_text"])

    # Pulsing Bar
    draw_progress_bar(ui.draw, Vector(m_x + 10, m_y + 75), Vector(m_w - 20, 10), ui.theme, pulse=True)

    ui.draw.swap()

def render_modal(ui, title, message, button_text="OK", scroll_idx=0):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    ui.draw_background()
    m_w = sw - 40
    limit = _dialog_text_limit(m_w)
    wrapped = _wrap_text(message, limit)

    # Header(20) + Text Area + Button Area(35) + Footer(20)
    content_h = len(wrapped) * 15
    m_h = max(85, min(sh - 20, 85 + content_h))
    m_x, m_y = 20, (sh - m_h) // 2

    draw_panel(ui.draw, Vector(m_x, m_y), Vector(m_w, m_h), title, ui.theme["panel_c"], ui.theme["accent_c"], ui.theme["footer_text"])

    text_viewport_h = max(0, m_h - 85)
    max_v_lines = text_viewport_h // 15

    # Clamp scroll_idx
    if scroll_idx > len(wrapped) - max_v_lines: scroll_idx = max(0, len(wrapped) - max_v_lines)

    y_offset = 30
    visible_lines = wrapped[scroll_idx : scroll_idx + max_v_lines]

    for line in visible_lines:
        ui.draw.text(Vector(m_x + 10, m_y + y_offset), line, ui.theme["text_c"])
        y_offset += 15

    # Scrollbar
    draw_scrollbar(ui.draw, Vector(m_x + m_w - 5, m_y + 30), Vector(3, text_viewport_h), len(wrapped), max_v_lines, scroll_idx, ui.theme)

    char_w = 6
    padding = 20
    btn_w = (len(button_text) * char_w) + padding
    btn_h = 20
    btn_x = m_x + (m_w - btn_w) // 2
    btn_y = m_y + m_h - 45
    draw_player_button(ui.draw, Vector(btn_x, btn_y), Vector(btn_w, btn_h), "ok", active=True, highlighted=True, colors=ui.theme, radius=btn_h // 2)
    ui.draw.text(Vector(btn_x + (btn_w - len(button_text)*char_w)//2, btn_y + 4), button_text, ui.theme["footer_text"])

    # Footer Bar
    ui.draw.fill_rectangle(Vector(m_x + 2, m_y + m_h - 18), Vector(m_w - 4, 15), ui.theme["accent_c"])
    ui.draw.text(Vector(m_x + 10, m_y + m_h - 15), t("hint_continue"), ui.theme["footer_text"])
    ui.draw.swap()


def render_input_dialog(ui, title, text, cursor_pos=0, force_full=False):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    if force_full:
        ui.draw_background()

    # Input dialog has mostly fixed vertical structure
    m_w, m_h = 200, 100
    m_x, m_y = (sw - m_w) // 2, (sh - m_h) // 2

    shadow_offset = 4
    ui.draw.fill_round_rectangle(Vector(m_x + shadow_offset, m_y + shadow_offset), Vector(m_w, m_h), 5, TFT_BLACK)
    draw_panel(ui.draw, Vector(m_x, m_y), Vector(m_w, m_h), title, ui.theme["panel_c"], ui.theme["accent_c"], ui.theme["footer_text"])

    well_w, well_h = m_w - 20, 24
    well_x, well_y = m_x + 10, m_y + 35
    draw_metadata_well(ui.draw, Vector(well_x, well_y), Vector(well_w, well_h), ui.theme)

    char_w = 6
    visible_chars = max(1, (well_w - 10) // char_w)
    start = 0
    if cursor_pos >= visible_chars:
        start = cursor_pos - visible_chars + 1
    shown = text[start:start + visible_chars]
    ui.draw.text(Vector(well_x + 5, well_y + 6), shown, ui.theme["accent_c"])

    import time
    if (time.ticks_ms() // 500) % 2:
        cursor_x = well_x + 5 + ((cursor_pos - start) * char_w)
        if cursor_x < well_x + well_w - 5:
            ui.draw.text(Vector(cursor_x, well_y + 6), "_", ui.theme["accent_c"])

    hint = "DEL:Rem LR:Move ENT:Save"
    ui.draw.fill_rectangle(Vector(m_x + 2, m_y + m_h - 18), Vector(m_w - 4, 15), ui.theme["accent_c"])
    ui.draw.text(Vector(m_x + 10, m_y + m_h - 15), hint, ui.theme["footer_text"])
    ui.draw.swap()


def render_confirm(ui, title, message, sel_idx=0, scroll_idx=0):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    m_w = 180
    limit = _dialog_text_limit(m_w)
    wrapped = _wrap_text(message, limit)

    # Calculate height: Title(20) + Text(lines*15) + Buttons(35) + Footer(20) + Padding(10)
    m_h = max(85, min(sh - 20, 85 + (len(wrapped) * 15)))
    m_x, m_y = (sw - m_w) // 2, (sh - m_h) // 2

    ui.draw.fill_round_rectangle(Vector(m_x + 4, m_y + 4), Vector(m_w, m_h), 5, TFT_BLACK)
    draw_panel(ui.draw, Vector(m_x, m_y), Vector(m_w, m_h), title, ui.theme["panel_c"], ui.theme["accent_c"], ui.theme["footer_text"])

    y_offset = 30
    for line in wrapped:
        ui.draw.text(Vector(m_x + 10, m_y + y_offset), line, ui.theme["text_c"])
        y_offset += 15

    yes_txt, no_txt = "YES", "NO"
    char_w = 6
    padding = 20
    btn_h = 20
    yes_btn_w = (len(yes_txt) * char_w) + padding
    no_btn_w = (len(no_txt) * char_w) + padding

    spacing = (m_w - yes_btn_w - no_btn_w) // 3
    yes_x = m_x + spacing
    no_x = m_x + spacing * 2 + yes_btn_w
    btn_y = m_y + m_h - 42 # Positioned relative to bottom

    draw_player_button(ui.draw, Vector(yes_x, btn_y), Vector(yes_btn_w, btn_h), "ok", active=True, highlighted=(sel_idx == 0), colors=ui.theme, radius=btn_h // 2)
    ui.draw.text(Vector(yes_x + (yes_btn_w - len(yes_txt)*char_w)//2, btn_y + 4), yes_txt, ui.theme["footer_text"])

    draw_player_button(ui.draw, Vector(no_x, btn_y), Vector(no_btn_w, btn_h), "ok", active=True, highlighted=(sel_idx == 1), colors=ui.theme, radius=btn_h // 2)
    ui.draw.text(Vector(no_x + (no_btn_w - len(no_txt)*char_w)//2, btn_y + 4), no_txt, ui.theme["footer_text"])

    ui.draw.fill_rectangle(Vector(m_x + 2, m_y + m_h - 18), Vector(m_w - 4, 15), ui.theme["accent_c"])
    ui.draw.text(Vector(m_x + 10, m_y + m_h - 15), t("hint_confirm"), ui.theme["footer_text"])
    ui.draw.swap()

# ---- ui_playlist.py ----

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
