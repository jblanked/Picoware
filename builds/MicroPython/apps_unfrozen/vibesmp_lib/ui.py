# Consolidated VibesMP rendering modules.


# ---- ui_utils.py ----

from picoware.system.vector import Vector
from picoware.gui.list import List
from picoware.system.colors import TFT_DARKGREY, TFT_WHITE, TFT_BLACK, TFT_DARKCYAN, TFT_LIGHTGREY, TFT_ORANGE

# Pre-built digit segment table for performance
_SEGMENTS = {
    '0': (1,1,1,0,1,1,1), '1': (0,0,1,0,0,1,0), '2': (1,0,1,1,1,0,1),
    '3': (1,0,1,1,0,1,1), '4': (0,1,1,1,0,1,0), '5': (1,1,0,1,0,1,1),
    '6': (1,1,0,1,1,1,1), '7': (1,0,1,0,0,1,0), '8': (1,1,1,1,1,1,1),
    '9': (1,1,1,1,0,1,1)
}

def draw_progress_bar(draw, pos, size, theme, pulse=True, progress=0):
    """Draw a progress bar with a distinct border."""
    # Draw border (1px outside)
    border_c = theme.get("highlight_c", theme["accent_c"])
    draw.rect(Vector(pos.x - 1, pos.y - 1), Vector(size.x + 2, size.y + 2), border_c)

    # Draw background (empty well)
    draw.fill_rectangle(pos, size, theme["well"])

    if pulse:
        import time
        p_w = size.x // 4
        p_x = pos.x + int((time.ticks_ms() // 5) % (size.x - p_w))
        draw.fill_rectangle(Vector(p_x, pos.y), Vector(p_w, size.y), theme["accent_c"])
    else:
        if progress > 0:
            fill_w = int(size.x * (progress / 100))
            draw.fill_rectangle(pos, Vector(fill_w, size.y), theme["accent_c"])

def draw_scrollbar(draw, pos, size, total, visible, current, theme):
    """Draw a vertical scrollbar."""
    if total <= visible or total <= 0: return
    sb_h = max(10, int(size.y * (visible / total)))
    divisor = max(1, total - visible)
    sb_y = pos.y + int((size.y - sb_h) * (current / divisor))
    draw.fill_rectangle(pos, size, theme["well"])
    draw.fill_rectangle(Vector(pos.x, sb_y), Vector(size.x, sb_h), theme["accent_c"])

def draw_digit(draw, pos, digit, color):
    """Draw a single digit in VibesMP-style 7-segment look."""
    w, h = 10, 17
    if digit == ':':
        draw.fill_rectangle(Vector(pos.x + 4, pos.y + 4), Vector(2, 2), color)
        draw.fill_rectangle(Vector(pos.x + 4, pos.y + 11), Vector(2, 2), color)
        return
    if digit == '/':
        for i in range(h - 4):
            px = pos.x + 2 + (w - 4) * (h - 4 - i) // (h - 4)
            draw.fill_rectangle(Vector(px, pos.y + 2 + i), Vector(2, 2), color)
        return
    s = _SEGMENTS.get(str(digit), (0,0,0,0,0,0,0))
    if s[0]: draw.fill_rectangle(Vector(pos.x + 2, pos.y), Vector(w - 4, 2), color)
    if s[1]: draw.fill_rectangle(Vector(pos.x, pos.y + 2), Vector(2, (h // 2) - 2), color)
    if s[2]: draw.fill_rectangle(Vector(pos.x + w - 2, pos.y + 2), Vector(2, (h // 2) - 2), color)
    if s[3]: draw.fill_rectangle(Vector(pos.x + 2, pos.y + (h // 2)), Vector(w - 4, 2), color)
    if s[4]: draw.fill_rectangle(Vector(pos.x, pos.y + (h // 2) + 2), Vector(2, (h // 2) - 2), color)
    if s[5]: draw.fill_rectangle(Vector(pos.x + w - 2, pos.y + (h // 2) + 2), Vector(2, (h // 2) - 2), color)
    if s[6]: draw.fill_rectangle(Vector(pos.x + 2, pos.y + h - 2), Vector(w - 4, 2), color)

def draw_player_button(draw, pos, size, type, active=False, highlighted=False, colors=None, radius=3):
    """Draw a high-contrast button with rounded corners."""
    # colors can be a dict with "accent", "highlight", "well", "text"
    c_accent = colors["accent_c"] if colors else TFT_ORANGE
    c_highlight = colors["highlight_c"] if colors else TFT_ORANGE
    c_well = colors["well"] if colors else TFT_DARKGREY
    c_text = colors["text_c"] if colors else TFT_WHITE

    border = c_highlight if highlighted else TFT_BLACK
    face_c = c_accent if active else c_well

    # Outer border (rounded)
    btn_radius = max(0, min(radius, size.y // 2, size.x // 2))
    draw.fill_round_rectangle(pos, size, btn_radius, border)
    # Inner face (rounded)
    draw.fill_round_rectangle(Vector(pos.x + 1, pos.y + 1), Vector(size.x - 2, size.y - 2), btn_radius, face_c)

    fg = c_text if (highlighted or active) else TFT_LIGHTGREY
    if highlighted and not active: fg = c_highlight
    icon_size = Vector(size.x - 10, size.y - 8); icon_pos = Vector(pos.x + 5, pos.y + 4)
    if type == "play":
        draw.fill_triangle(icon_pos, Vector(icon_pos.x, icon_pos.y + icon_size.y), Vector(icon_pos.x + icon_size.x, icon_pos.y + icon_size.y // 2), fg)
    elif type == "pause":
        w2 = icon_size.x // 3
        draw.fill_rectangle(icon_pos, Vector(w2, icon_size.y), fg)
        draw.fill_rectangle(Vector(icon_pos.x + icon_size.x - w2, icon_pos.y), Vector(w2, icon_size.y), fg)
    elif type == "prev":
        draw.fill_rectangle(icon_pos, Vector(2, icon_size.y), fg)
        draw.fill_triangle(Vector(icon_pos.x + 2, icon_pos.y + icon_size.y // 2), Vector(icon_pos.x + icon_size.x, icon_pos.y), Vector(icon_pos.x + icon_size.x, icon_pos.y + icon_size.y), fg)
    elif type == "stop": draw.fill_rectangle(icon_pos, icon_size, fg)
    elif type == "next":
        draw.fill_rectangle(Vector(icon_pos.x + icon_size.x - 2, icon_pos.y), Vector(2, icon_size.y), fg)
        draw.fill_triangle(Vector(icon_pos.x, icon_pos.y), Vector(icon_pos.x, icon_pos.y + icon_size.y), Vector(icon_pos.x + icon_size.x - 2, icon_pos.y + icon_size.y // 2), fg)
    elif type == "fb":
        w2 = icon_size.x // 2
        draw.fill_triangle(Vector(icon_pos.x, icon_pos.y + icon_size.y // 2), Vector(icon_pos.x + w2, icon_pos.y), Vector(icon_pos.x + w2, icon_pos.y + icon_size.y), fg)
        draw.fill_triangle(Vector(icon_pos.x + w2, icon_pos.y + icon_size.y // 2), Vector(icon_pos.x + icon_size.x, icon_pos.y), Vector(icon_pos.x + icon_size.x, icon_pos.y + icon_size.y), fg)
    elif type == "ff":
        w2 = icon_size.x // 2
        draw.fill_triangle(Vector(icon_pos.x, icon_pos.y), Vector(icon_pos.x, icon_pos.y + icon_size.y), Vector(icon_pos.x + w2, icon_pos.y + icon_size.y // 2), fg)
        draw.fill_triangle(Vector(icon_pos.x + w2, icon_pos.y), Vector(icon_pos.x + w2, icon_pos.y + icon_size.y), Vector(icon_pos.x + icon_size.x, icon_pos.y + icon_size.y // 2), fg)
    elif type == "shuffle":
        # Classic crossing arrows shuffle icon
        x, y = icon_pos.x, icon_pos.y
        # Left horizontal bars
        draw.fill_rectangle(Vector(x + 2, y + 3), Vector(4, 2), fg)
        draw.fill_rectangle(Vector(x + 2, y + 11), Vector(4, 2), fg)
        # Crossing diagonals
        draw.fill_rectangle(Vector(x + 6, y + 4), Vector(2, 2), fg)
        draw.fill_rectangle(Vector(x + 8, y + 6), Vector(2, 2), fg)
        draw.fill_rectangle(Vector(x + 10, y + 7), Vector(2, 2), fg)
        draw.fill_rectangle(Vector(x + 12, y + 8), Vector(2, 2), fg)
        draw.fill_rectangle(Vector(x + 14, y + 10), Vector(2, 2), fg)

        draw.fill_rectangle(Vector(x + 6, y + 10), Vector(2, 2), fg)
        draw.fill_rectangle(Vector(x + 8, y + 8), Vector(2, 2), fg)
        draw.fill_rectangle(Vector(x + 12, y + 6), Vector(2, 2), fg)
        draw.fill_rectangle(Vector(x + 14, y + 4), Vector(2, 2), fg)
        # Right horizontal bars
        draw.fill_rectangle(Vector(x + 14, y + 3), Vector(4, 2), fg)
        draw.fill_rectangle(Vector(x + 14, y + 11), Vector(4, 2), fg)
        # Arrow heads
        draw.fill_triangle(Vector(x + 16, y + 1), Vector(x + 16, y + 7), Vector(x + 19, y + 4), fg)
        draw.fill_triangle(Vector(x + 16, y + 9), Vector(x + 16, y + 15), Vector(x + 19, y + 12), fg)
    elif type.startswith("loop"):
        draw.rect(icon_pos, Vector(icon_size.x, icon_size.y - 4), fg)
        draw.fill_rectangle(Vector(icon_pos.x + 2, icon_pos.y + 2), Vector(icon_size.x - 4, icon_size.y - 8), face_c)
        draw.fill_triangle(Vector(icon_pos.x + icon_size.x - 4, icon_pos.y - 2), Vector(icon_pos.x + icon_size.x, icon_pos.y + 2), Vector(icon_pos.x + icon_size.x - 4, icon_pos.y + 4), fg)
        mode = type[4:]
        if mode: draw.text(Vector(icon_pos.x + 6, icon_pos.y + 2), mode, fg)

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

def draw_panel(draw, pos, size, title, panel_c, accent_c, title_c):
    """Draw a themed rounded panel with a title bar."""
    draw.fill_round_rectangle(pos, size, 4, accent_c)
    draw.fill_round_rectangle(Vector(pos.x + 1, pos.y + 1), Vector(size.x - 2, size.y - 2), 3, panel_c)
    draw.fill_rectangle(Vector(pos.x + 2, pos.y + 2), Vector(size.x - 4, 15), accent_c)
    draw.text(Vector(pos.x + 5, pos.y + 4), title, title_c)

def draw_metadata_well(draw, pos, size, theme):
    """Draw metadata container with rounded corners."""
    draw.fill_round_rectangle(pos, size, 3, theme["well"])

def draw_marquee(draw, pos, text, color, max_chars, scroll_pos):
    if len(text) <= max_chars: draw.text(pos, text, color)
    else:
        disp = text + "   "; off = scroll_pos % len(disp)
        draw.text(pos, (disp + disp)[off:off+max_chars], color)

def draw_scrollable_list(draw, pos, size, items, sel_idx, focused, theme, format_fn, item_h=15, active_idx=-1, row_cache=None, cache_token=None, marquee_delay_ms=2000, row_only_tick=False, redraw_indices=None, marquee_start_ms=0, repaint_mode="full", view_state=None):
    effective_row_only = repaint_mode == "row_only" or row_only_tick

    count = len(items)
    x, y, w, h = pos.x, pos.y, size.x, size.y
    bg_col = theme.get("panel_c", theme["well"])

    if repaint_mode in ("full", "viewport_only"):
        draw.fill_rectangle(Vector(x, y), Vector(w, h), bg_col)

    if not items:
        draw.text(Vector(pos.x + 5, pos.y + 5), "Empty", theme["text_c"])
        return

    # Defensive clamping
    sel_idx = max(0, min(sel_idx, count - 1))
    if view_state:
        max_items = max(1, int(view_state.get("max_items", h // item_h if item_h > 0 else 1)))
        start_idx = max(0, min(int(view_state.get("start_idx", 0)), count))
        end_idx = max(start_idx, min(count, int(view_state.get("end_idx", count))))
    else:
        max_items = max(1, h // item_h)
        max_start = max(0, count - max_items)
        start_idx = min(max(0, sel_idx - (max_items // 2)), max_start)
        end_idx = min(len(items), start_idx + max_items)

    if not effective_row_only and len(items) > max_items:
        sb_w = 4
        sb_h = max(6, int(h * (max_items / len(items))))
        divisor = max(1, len(items) - 1)
        sb_y = y + int((h - sb_h) * (sel_idx / divisor))
        draw.fill_rectangle(Vector(x + w - sb_w, y), Vector(sb_w, h), theme["well"])
        draw.fill_rectangle(Vector(x + w - sb_w, sb_y), Vector(sb_w, sb_h), theme["accent_c"])
        w -= (sb_w + 2)

    p_y = y
    import time
    if row_cache is not None and len(row_cache) > 512:
        row_cache.clear()

    for i in range(start_idx, end_idx):
        is_sel = (i == sel_idx)
        is_active = (i == active_idx)
        if effective_row_only:
            if redraw_indices is None:
                if not is_sel:
                    p_y += item_h
                    continue
            elif i not in redraw_indices:
                p_y += item_h
                continue

        if is_sel:
            # High-contrast if focused, subtle if background
            sel_bg = theme["accent_c"] if focused else theme.get("panel_c", theme["well"])
            # Small rounding for individual list items
            draw.fill_round_rectangle(Vector(x, p_y), Vector(w, item_h), 4, sel_bg)
        else:
            # Clear background of unselected item to avoid ghosting/text overlap
            draw.fill_rectangle(Vector(x, p_y), Vector(w, item_h), bg_col)

        txt_c = theme["text_c"]
        if is_sel:
            # Use background-appropriate text color
            txt_c = theme["footer_text"] if focused else theme["text_c"]
        elif is_active:
            txt_c = theme["highlight_c"]

        if row_cache is not None and cache_token is not None:
            item = items[i]
            try:
                hash(item)
                item_key = item
            except TypeError:
                if isinstance(item, dict):
                    item_key = (
                        item.get("kind", ""),
                        item.get("label", ""),
                        item.get("title", ""),
                        item.get("name", ""),
                        item.get("path", ""),
                        item.get("url", ""),
                        item.get("expanded", False),
                        item.get("favorite", False),
                        item.get("count", 0),
                        item.get("depth", 0),
                    )
                elif isinstance(item, list):
                    item_key = tuple(item)
                else:
                    item_key = repr(item)
            ck = (cache_token, i, item_key)
            text = row_cache.get(ck)
            if text is None:
                text = format_fn(i, items[i])
                row_cache[ck] = text
        else:
            text = format_fn(i, items[i])
        max_chars = max(1, (w - 8) // 6)
        if is_sel and focused and len(text) > max_chars:
            # Focused-row ping-pong marquee with start delay.
            period = 320
            over = len(text) - max_chars
            now = time.ticks_ms()
            start_ms = marquee_start_ms if marquee_start_ms else now
            elapsed = time.ticks_diff(now, start_ms)
            if elapsed > marquee_delay_ms:
                prog = int((elapsed - marquee_delay_ms) // period)
                bounce = over * 2
                m = prog % (bounce if bounce > 0 else 1)
                off = m if m <= over else (bounce - m)
            else:
                off = 0
            draw.text(Vector(x + 6, p_y + 1), text[off:off + max_chars], txt_c)
        else:
            if len(text) > max_chars:
                text = text[:max_chars]
            draw.text(Vector(x + 6, p_y + 1), text, txt_c)
        p_y += item_h

class IconList(List):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.icons = []
    def add_item(self, text, icon_type=None):
        super().add_item(text); self.icons.append(icon_type)
    def clear(self, swap: bool = True):
        super().clear(swap); self.icons = []
    def scroll_up(self, swap: bool = True):
        if self.use_lvgl and self._lvgl_list is not None:
            super().scroll_up(swap)
            return
        _len = len(self.items)
        if _len > 0:
            self._selected_index = (self._selected_index - 1) % _len
        self.draw(swap)
    def scroll_down(self, swap: bool = True):
        if self.use_lvgl and self._lvgl_list is not None:
            super().scroll_down(swap)
            return
        _len = len(self.items)
        if _len > 0:
            self._selected_index = (self._selected_index + 1) % _len
        self.draw(swap)
    def draw(self, swap: bool = True):
        if self.use_lvgl and self._lvgl_list is not None:
            super().draw(swap)
            return
        self.display.fill_rectangle(self.position, self.size, self.background_color)
        _len = len(self.items)
        if _len == 0:
            if swap:
                self.display.swap()
            return
        item_h = 30; max_v = (self.height - 20) // item_h
        sel_idx = self._selected_index
        if _len > 0 and sel_idx >= _len: sel_idx = _len - 1
        if sel_idx < 0: sel_idx = 0
        off = 0
        if _len > max_v and sel_idx >= max_v: off = sel_idx - max_v + 1
        for i in range(off, min(_len, off + max_v)):
            idx = i - off; iy = self.position.y + 10 + (idx * item_h)
            if i == sel_idx: self.display.fill_round_rectangle(Vector(5, iy - 2), Vector(self.size.x - 10, item_h - 4), 5, self.selected_color)
            it = self.icons[i] if i < len(self.icons) else None; tx = 10
            if it:
                # Triangle for player, Cog for settings, Folder for library
                if it == "player": self.display.fill_triangle(Vector(10, iy + 4), Vector(10, iy + 20), Vector(25, iy + 12), self.text_color)
                elif it == "settings":
                    for j in range(4):
                        w, h = (16, 4) if j % 2 == 0 else (4, 16)
                        ox = 10 if j % 2 == 0 else 16
                        oy = iy + 8 if j % 2 == 0 else iy + 2
                        self.display.fill_rectangle(Vector(ox, oy), Vector(w, h), self.text_color)
                elif it == "library": self.display.rect(Vector(10, iy + 4), Vector(18, 12), self.text_color)
                tx = 35
            self.display.text(Vector(tx, iy + 4), self.items[i], self.text_color)
        if swap:
            self.display.swap()

def draw_musical_note(draw, center, angle, color, accent_color):
    """Draw a rotating slanted double eighth note."""
    import math
    rad = (angle * 3.14159) / 180.0
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    # Stems and Beam relative to 0,0
    lines = [
        ((-6, 10), (-6, -10)),   # Left stem
        ((14, 5), (14, -15)),    # Right stem
        ((-6, -10), (14, -15)),  # Beam top
        ((-6, -8), (14, -13)),   # Beam bottom
    ]

    for p1, p2 in lines:
        x1 = int(p1[0] * cos_a - p1[1] * sin_a)
        y1 = int(p1[0] * sin_a + p1[1] * cos_a)
        x2 = int(p2[0] * cos_a - p2[1] * sin_a)
        y2 = int(p2[0] * sin_a + p2[1] * cos_a)
        draw.line(center + Vector(x1, y1), center + Vector(x2, y2), color)

    heads = [(-10, 10), (10, 5)]
    for hx, hy in heads:
        rx = int(hx * cos_a - hy * sin_a)
        ry = int(hx * sin_a + hy * cos_a)
        draw.fill_circle(center + Vector(rx, ry), 5, accent_color)


# ---- ui_elements.py ----

from picoware.system.vector import Vector
import time
from picoware.system.colors import TFT_WHITE
from vibesmp_lib.core import get_filename
def format_lib_item(i, x, max_chars):
    if isinstance(x, tuple):
        path, depth, is_dir, is_exp, name = x
        prefix = "  " * depth
        if is_dir: prefix += "-" if is_exp else "+"
        else: prefix += " "
        res = prefix + name
    else:
        res = x if x == ".." else get_filename(x)
    return res

def format_track_item(i, x, pl_idx, max_chars, library=None):
    prefix = "> " if i == pl_idx else "  "
    name = get_filename(x)
    if name.lower().endswith(".mp3"): name = name[:-4]
    if library is not None:
        title, artist = library.get_track_display(x, allow_io=False)
        name = title if not artist else (title + " - " + artist)
    res = prefix + name
    return res

def format_playlist_item(i, x, active_pl_name, max_chars):
    fname = x if x == ".." else get_filename(x)
    is_active = (fname == active_pl_name)
    if fname.endswith(".json"): fname = fname[:-5]
    prefix = "> " if is_active else "  "
    res = prefix + fname
    return res

def draw_player_column(ui, col_idx, title, items, sel_idx, focus, active_col, list_y, list_h, col_w, max_chars, type="lib", repaint_mode="full_column", **kwargs):
    cx = 5 + col_idx * col_w
    redraw_indices = kwargs.get("redraw_indices", None)
    viewport_pos = Vector(cx + 2, list_y + 17)
    viewport_size = Vector(col_w - 4, list_h - 19)
    view_state = kwargs.get("view_state")

    # Clear column background with rounded corners
    box_bg = ui.theme.get("panel_c", ui.theme["well"])
    if repaint_mode == "full_column":
        ui.draw.fill_round_rectangle(Vector(cx, list_y), Vector(col_w, list_h), 6, box_bg)

    is_active = (focus == 1 and active_col == col_idx)
    # Column border
    border_c = ui.theme["accent_c"] if is_active else ui.theme["well"]
    if repaint_mode == "full_column":
        ui.draw.rect(Vector(cx, list_y), Vector(col_w, list_h), border_c)

    # Title drawing
    if repaint_mode == "full_column":
        t_title = title if len(title) <= max_chars else title[:max_chars-1] + "~"
        ui.draw.text(Vector(cx + 4, list_y + 3), t_title, ui.theme["accent_c"])
        # Separator line under title
        ui.draw.fill_rectangle(Vector(cx + 2, list_y + 15), Vector(col_w - 4, 1), ui.theme["well"])

    # On-demand formatter — reserve 1 char for scrollbar (4px + 2px gap = 6px = 1 char width)
    sc = max_chars - 1
    def formatter(i, x):
        if type == "lib": return format_lib_item(i, x, sc)
        if type == "track": return format_track_item(i, x, kwargs.get("pl_idx", -1), sc, library=kwargs.get("library"))
        if type == "plist": return format_playlist_item(i, x, kwargs.get("active_pl", ""), sc)
        return str(x)

    a_idx = -1
    if col_idx == 2: a_idx = 0

    # Build a compact cache token based on visible window and list state.
    item_h = 16
    vis_h = list_h - 19
    count = len(items)
    clamped_sel = max(0, min(sel_idx, count - 1)) if count else 0
    if view_state:
        max_items = view_state.get("max_items", max(1, vis_h // item_h) if item_h > 0 else 1)
    else:
        max_items = max(1, vis_h // item_h) if item_h > 0 else 1
    cache_token = (
        type, col_idx, is_active, a_idx,
        kwargs.get("pl_idx", -1), kwargs.get("active_pl", ""), count,
        getattr(kwargs.get("library"), "display_cache_version", 0)
    )

    # Track overflow state for active column only (used by app loop for timed marquee refresh).
    row_redraw_indices = redraw_indices
    if is_active:
        ui.active_list_overflow = False
        if count > 0 and 0 <= clamped_sel < count:
            sel_text = formatter(clamped_sel, items[clamped_sel])
            ui.active_list_overflow = len(sel_text) > sc
            marker = ("marquee_sel", type, col_idx, clamped_sel, sel_text, sc)
            if getattr(ui, "_marquee_marker", None) != marker:
                ui._marquee_marker = marker
                ui._marquee_start_ms = time.ticks_ms()
        prev_sel = ui._last_sel_by_col.get(col_idx, -1)
        if repaint_mode == "row_only":
            row_redraw_indices = (clamped_sel, prev_sel)
        ui._last_sel_by_col[col_idx] = clamped_sel

    list_repaint_mode = "full"
    if repaint_mode == "viewport_only":
        list_repaint_mode = "viewport_only"
    elif repaint_mode == "row_only":
        list_repaint_mode = "row_only"

    draw_scrollable_list(
        ui.draw,
        viewport_pos,
        viewport_size,
        items,
        sel_idx,
        is_active,
        ui.theme,
        formatter,
        item_h=item_h,
        active_idx=a_idx,
        row_cache=getattr(ui, "list_row_cache", None),
        cache_token=cache_token,
        marquee_delay_ms=2000,
        row_only_tick=(repaint_mode == "row_only"),
        redraw_indices=row_redraw_indices,
        marquee_start_ms=getattr(ui, "_marquee_start_ms", 0),
        repaint_mode=list_repaint_mode,
        view_state=view_state,
    )


# ---- ui_dialogs.py ----

from picoware.system.vector import Vector
from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_GREEN
from vibesmp_lib.core import t

def _wrap_text(text, limit):
    res = []
    # Handle both actual newlines and escaped newlines
    lines = text.replace("\\n", "\n").split("\n")
    for l in lines:
        if not l:
            res.append("")
            continue
        for i in range(0, len(l), limit):
            res.append(l[i:i+limit])
    return res

def _dialog_text_limit(width_px, inner_padding=20, scrollbar_w=8, char_w=6):
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

from picoware.system.vector import Vector
from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_GREEN
from vibesmp_lib.core import t
from vibesmp_lib.core import get_filename

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


# ---- ui_player.py ----

from picoware.system.vector import Vector
from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_GREEN
from vibesmp_lib.core import get_filename, format_time
from vibesmp_lib.core import t
from vibesmp_lib.core import draw_cover
import time

_inf_cache = {"str": "", "v_str": "", "info_track": "", "info_tuple": None, "info_retry_after": 0}
def _perf_inc(ui, name):
    counters = getattr(ui, "perf_counters", None)
    if counters is not None:
        counters[name] = counters.get(name, 0) + 1

def _cached_audio_info(ui, player, track_key):
    if not player:
        return None
    now = time.ticks_ms()
    cached = _inf_cache.get("info_tuple")
    if _inf_cache.get("info_track") == track_key and cached:
        _perf_inc(ui, "audio_info_cache_hits")
        return cached
    if _inf_cache.get("info_track") == track_key:
        retry_after = _inf_cache.get("info_retry_after", 0)
        if retry_after and time.ticks_diff(now, retry_after) < 0:
            _perf_inc(ui, "audio_info_negative_cache_hits")
            return None

    _perf_inc(ui, "audio_info_reads")
    info = player.get_info()
    if not info:
        _inf_cache["info_retry_after"] = time.ticks_add(now, 1000)
        _perf_inc(ui, "audio_info_negative_cache_misses")
        return None

    try:
        if isinstance(info, tuple):
            b_rate = info[0] if len(info) > 0 else 0
            s_rate = info[1] if len(info) > 1 else 0
        else:
            b_rate = getattr(info, "bitrate", 0)
            s_rate = getattr(info, "sample_rate", 0)
    except (AttributeError, TypeError, IndexError):
        _inf_cache["info_retry_after"] = time.ticks_add(now, 1000)
        _perf_inc(ui, "audio_info_negative_cache_misses")
        return None

    if b_rate and s_rate:
        cached = (b_rate, s_rate)
        _inf_cache["info_track"] = track_key
        _inf_cache["info_tuple"] = cached
        _inf_cache["info_retry_after"] = 0
        _perf_inc(ui, "audio_info_cache_misses")
        return cached
    _inf_cache["info_retry_after"] = time.ticks_add(now, 1000)
    _perf_inc(ui, "audio_info_negative_cache_misses")
    return None

def _list_policy(settings):
    if not settings:
        return ("offset", 2)
    policy = settings.config.get("list_view_policy", "offset")
    if policy not in ("centered", "offset"):
        policy = "offset"
    try:
        offset = int(settings.config.get("list_scroll_offset", 2))
    except (TypeError, ValueError):
        offset = 2
    return (policy, max(0, offset))

def _compute_viewport(sel_idx, total, view_h, item_h, policy="offset", scroll_offset=2, prev_window=None):
    if total <= 0:
        return {
            "start_idx": 0,
            "end_idx": 0,
            "max_items": max(1, view_h // item_h) if item_h > 0 else 1,
            "has_scrollbar": False,
        }

    max_items = max(1, view_h // item_h) if item_h > 0 else 1
    max_start = max(0, total - max_items)
    sel_idx = max(0, min(sel_idx, total - 1))

    if policy == "centered":
        start_idx = min(max(0, sel_idx - (max_items // 2)), max_start)
    else:
        offset = min(max(0, scroll_offset), max(0, max_items - 1))
        if prev_window is None:
            start_idx = min(max(0, sel_idx - offset), max_start)
        else:
            prev_start, prev_end = prev_window
            prev_start = max(0, min(prev_start, max_start))
            prev_end = max(prev_start, min(total, prev_end))
            upper_threshold = prev_start + offset
            lower_threshold = prev_end - offset - 1
            start_idx = prev_start
            if sel_idx < upper_threshold:
                start_idx = max(0, sel_idx - offset)
            elif sel_idx > lower_threshold:
                start_idx = min(max_start, sel_idx - (max_items - offset - 1))
            start_idx = min(max(0, start_idx), max_start)

    end_idx = min(total, start_idx + max_items)
    return {
        "start_idx": start_idx,
        "end_idx": end_idx,
        "max_items": max_items,
        "has_scrollbar": total > max_items,
    }

def _column_state(prefix, sel_idx, total, view_h, item_h, is_active, prev_state, policy, scroll_offset):
    prev_window = prev_state.get(prefix + "_window")
    viewport = _compute_viewport(sel_idx, total, view_h, item_h, policy=policy, scroll_offset=scroll_offset, prev_window=prev_window)
    return {
        "selected_idx": sel_idx,
        "count": total,
        "window": (viewport["start_idx"], viewport["end_idx"]),
        "active": is_active,
        "scroll": viewport["has_scrollbar"],
        "max_items": viewport["max_items"],
        "viewport": viewport,
        "policy": policy,
    }

def _choose_repaint_mode(prev_state, prefix, current_state, force_full=False, list_tick=False):
    if force_full:
        return "full_column"

    prev_window = prev_state.get(prefix + "_window")
    prev_count = prev_state.get(prefix + "_count", -1)
    prev_active = prev_state.get(prefix + "_active")
    prev_scroll = prev_state.get(prefix + "_scroll")
    prev_policy = prev_state.get(prefix + "_policy")

    if prev_window is None:
        return "full_column"
    if prev_active != current_state["active"]:
        return "full_column"
    if prev_count != current_state["count"]:
        return "full_column"
    if prev_scroll != current_state["scroll"]:
        return "full_column"
    if prev_policy != current_state["policy"]:
        return "full_column"
    if current_state["count"] == 0:
        return "viewport_only"
    if list_tick:
        return "row_only" if prev_window == current_state["window"] else "viewport_only"
    if prev_window == current_state["window"]:
        return "row_only"
    return "viewport_only"

def _draw_player_metadata(ui, player, cover_path, norm_track, is_playing, blink_state, curr_sec, total_sec, sw, last_cover, force_full, time_changed, play_changed, blink_changed, scroll_changed, track_changed, text_changed):
    well_pos = Vector(5, 20)
    well_size = Vector(sw - 10, 78)

    has_played = player and (player.last_play_time > 0 or player.current_track)
    has_valid_cover = isinstance(cover_path, str) and len(cover_path) > 0
    can_load = (player.can_load_heavy_assets if player else False) or (ui.cover_draw_count > 0)
    bg_col = ui.theme.get("panel_c", ui.theme["well"])

    # Background drawing
    if force_full:
        if has_played and has_valid_cover and ui.cover_drawn_path == cover_path:
            # Keep the already drawn cover. Only clear the text area to the right of the cover.
            # Cover is at x=10..78. Text area starts at x=78.
            text_area_pos = Vector(78, well_pos.y)
            text_area_size = Vector(well_size.x - 73, well_size.y)
            ui.draw.fill_rectangle(text_area_pos, text_area_size, bg_col)
            # Redraw the well border outline (does not erase the inside)
            ui.draw.rect(well_pos, well_size, ui.theme["well"])
        else:
            # Clear the entire well
            ui.draw.fill_round_rectangle(well_pos, well_size, 5, bg_col)
            ui.draw.rect(well_pos, well_size, ui.theme["well"])
            ui.cover_drawn_path = None
        # DO NOT clear ui.cover_attempted_path here!
    else:
        # Partial clears for performance during playback
        # Use bg_col (panel_c/well) instead of clearing to pure bg_c to keep the "box" look
        box_bg = ui.theme.get("panel_c", ui.theme["well"])
        if time_changed:
            ui.draw.fill_rectangle(Vector(85, 22), Vector(140, 25), box_bg)
        if play_changed or blink_changed:
            ui.draw.fill_rectangle(Vector(sw - 60, 22), Vector(55, 14), box_bg)
        if scroll_changed or track_changed or text_changed:
            ui.draw.fill_rectangle(Vector(90, 48), Vector(sw - 100, 20), box_bg)
            ui.draw.fill_rectangle(Vector(90, 68), Vector(sw - 100, 16), box_bg)

    # Cover art handling
    if has_played and has_valid_cover:
        if can_load:
            if ui.cover_drawn_path != cover_path or ui.cover_draw_count > 0:
                ui.draw.fill_rectangle(Vector(10, 25), Vector(68, 68), bg_col)
                _perf_inc(ui, "cover_decodes")
                drawn = draw_cover(ui.draw, cover_path, 10, 25, size=68)
                if drawn:
                    ui.cover_drawn_path = cover_path
                else:
                    ui.draw.rect(Vector(10, 25), Vector(68, 68), ui.theme["accent_c"])
        else:
            if ui.cover_drawn_path != cover_path:
                ui.draw.fill_rectangle(Vector(10, 25), Vector(68, 68), bg_col)
                ui.draw.rect(Vector(10, 25), Vector(68, 68), ui.theme["well"])
    else:
        # No cover or stopped
        if force_full or ui.cover_drawn_path is not None:
            ui.draw.fill_rectangle(Vector(10, 25), Vector(68, 68), bg_col)
            ui.draw.rect(Vector(10, 25), Vector(68, 68), ui.theme["accent_c"])
            ui.cover_drawn_path = None

    if time_changed or force_full:
        _perf_inc(ui, "metadata_time_repaints")
        curr_ts = format_time(curr_sec)
        total_str = player._dur_str_cache if player else "--:--"
        ts = f"{curr_ts} / {total_str}" if total_sec > 0 else curr_ts
        time_pos = Vector(85, 22)
        for i, char in enumerate(ts):
            char_pos = Vector(time_pos.x + 5 + i*10, time_pos.y + 5)
            draw_digit(ui.draw, char_pos, char, ui.theme["accent_c"])

    if play_changed or blink_changed or force_full:
        status_y = 25
        if is_playing:
            ui.draw.text(Vector(sw - 55, status_y), t("playing").upper(), ui.theme["accent_c"])
        else:
            p_state = player.is_paused() if player else False
            if p_state:
                if blink_state: ui.draw.text(Vector(sw - 50, status_y), t("paused").upper(), ui.theme["highlight_c"])
            else:
                ui.draw.text(Vector(sw - 55, status_y), t("stopped").upper(), ui.theme["text_c"])

    if force_full or scroll_changed or track_changed or text_changed:
        _perf_inc(ui, "metadata_text_repaints")
        text_x = 90
        max_c = (sw - text_x - 10) // 6
        name = t("no_track"); info_str = ""
        if norm_track:
            name = norm_track.rsplit("/", 1)[-1]
            if name.lower().endswith(".mp3"): name = name[:-4]
            if player and hasattr(player, "current_id3") and player.current_id3:
                id3 = player.current_id3
                if id3.get("title"): name = id3["title"]
                if id3.get("artist"):
                    info_str = id3["artist"]
                    if id3.get("album"): info_str += f" - {id3['album']}"

        draw_marquee(ui.draw, Vector(text_x, 52), name, ui.theme["accent_c"], max_c, ui.scroll_pos)
        if info_str: draw_marquee(ui.draw, Vector(text_x, 68), info_str, ui.theme["text_c"], max_c, ui.scroll_pos2)

def _draw_player_controls(ui, player, is_playing, loop_mode, shuffle, focus, btn_idx, active_col, curr_sec, total_sec, sw, sh, vol, force_full, progress_dirty=True, buttons_dirty=True, footer_dirty=True, info_dirty=True, status_dirty=True, info_track="", button_indices=None):
    global _inf_cache
    if force_full:
        _inf_cache["str"] = ""
        _inf_cache["v_str"] = ""
    if _inf_cache.get("info_track") != info_track:
        _inf_cache["str"] = ""
        _inf_cache["info_track"] = info_track
        _inf_cache["info_tuple"] = None
        _inf_cache["info_retry_after"] = 0

    # Control Panel Background
    ctrl_pos = Vector(5, 100)
    ctrl_size = Vector(sw - 10, 42)
    bg_col = ui.theme.get("panel_c", ui.theme["well"])

    if force_full:
        ui.draw.fill_round_rectangle(ctrl_pos, ctrl_size, 6, bg_col)
        # Subtle border for visibility
        border_c = ui.theme["accent_c"] if focus == 0 else ui.theme["well"]
        ui.draw.rect(ctrl_pos, ctrl_size, border_c)

    tx = 85
    l_v = "Off"
    if loop_mode == 1: l_v = "1"
    elif loop_mode == 2: l_v = "A"

    # Bitrate/Sample Rate (drawn INSIDE metadata well, Y=84)
    well_bg = ui.theme.get("panel_c", ui.theme["well"])
    if force_full or info_dirty:
        info = _cached_audio_info(ui, player, info_track)
        if info:
            b_rate, s_rate = info
            inf_str = f"{b_rate}k {s_rate//1000}k"
            if force_full or inf_str != _inf_cache["str"]:
                ui.draw.fill_rectangle(Vector(tx, 84), Vector(80, 12), well_bg)
                ui.draw.text(Vector(tx, 84), inf_str, ui.theme["accent_c"])
                _inf_cache["str"] = inf_str

    # Volume/Shuffle/Loop status line (drawn INSIDE metadata well, Y=84)
    r_str = f"V:{vol} S:{'On' if shuffle else 'Off'} L:{l_v}"
    if force_full or status_dirty or r_str != _inf_cache["v_str"]:
        ui.draw.fill_rectangle(Vector(sw - 120, 84), Vector(110, 12), well_bg)
        ui.draw.text(Vector(sw - len(r_str)*6 - 15, 84), r_str, ui.theme["text_c"])
        _inf_cache["v_str"] = r_str

    # Progress Bar (Y=106, H=6)
    if force_full or progress_dirty:
        _perf_inc(ui, "control_repaints")
        prog_pos = Vector(10, 106); prog_size = Vector(sw - 20, 6)
        progress_perc = (curr_sec * 100 // total_sec) if total_sec > 0 else 0
        draw_progress_bar(ui.draw, prog_pos, prog_size, ui.theme, pulse=False, progress=progress_perc)

    # Buttons (Y=116)
    if force_full or buttons_dirty:
        _perf_inc(ui, "button_repaints")
        btn_w, btn_spacing = 26, 2; num_btns = 8
        total_w = (btn_w * num_btns) + (btn_spacing * (num_btns - 1))
        start_x = (sw - total_w) // 2

        indices = button_indices if button_indices is not None else range(num_btns)
        if button_indices is not None:
            _perf_inc(ui, "button_partial_repaints")

        for i in indices:
            if i < 0 or i >= num_btns:
                continue
            bx = start_x + i * (btn_w + btn_spacing)
            is_sel = (focus == 0 and btn_idx == i)

            icon = "play"
            if i == 0: icon = "shuffle"; is_active = shuffle
            elif i == 1: icon = "prev"; is_active = False
            elif i == 2: icon = "fb"; is_active = False
            elif i == 3: icon = "pause" if is_playing else "play"; is_active = is_playing
            elif i == 4: icon = "stop"; is_active = False
            elif i == 5: icon = "ff"; is_active = False
            elif i == 6: icon = "next"; is_active = False
            elif i == 7: icon = "loop" if loop_mode == 0 else (f"loop{l_v}"); is_active = loop_mode > 0

            draw_player_button(ui.draw, Vector(bx, 114), Vector(btn_w, 24), icon, active=is_active, highlighted=is_sel, colors=ui.theme)

    # Hints and Seek Message
    if force_full or footer_dirty:
        _perf_inc(ui, "footer_repaints")
        hints = ""
        if focus == 0: hints = t("hint_np_controls")
        elif active_col == 0: hints = t("hint_np_lib")
        elif active_col == 1: hints = t("hint_np_trk")
        elif active_col == 2: hints = t("hint_np_pls")

        # Always clear footer area to avoid ghost hints
        bar_h = 20
        ui.draw.fill_round_rectangle(Vector(0, sh - bar_h), Vector(sw, bar_h), 5, ui.theme["footer_bg"])
        if hints:
            ui.draw.text(Vector(10, sh - 16), hints, ui.theme["footer_text"])
        else:
            # Restore footer separator if no hint
            ui.draw.fill_rectangle(Vector(0, sh - bar_h), Vector(sw, 1), TFT_BLACK)

def _draw_player_lists(ui, library_tree, l_idx, playlist, pl_idx, e_idx, playlists, playlist_idx, focus, active_col, sw, sh, lib_state, trk_state, pls_state, library=None, list_tick=False, nav_fast=False, force_full=False):
    col_w = (sw - 10) // 3
    max_chars = col_w // 6
    list_y = 142
    list_h = sh - 162
    track_list = playlist.tracks if playlist else []

    if lib_state.get("changed") or force_full:
        repaint_mode = lib_state["repaint_mode"]
        if not (list_tick or nav_fast) and repaint_mode != "full_column":
            repaint_mode = "viewport_only"
        draw_player_column(
            ui, 0, t("menu_library").upper(), library_tree, lib_state["selected_idx"], focus, active_col, list_y, list_h, col_w, max_chars,
            type="lib",
            repaint_mode=repaint_mode,
            redraw_indices=(lib_state["selected_idx"],),
            view_state=lib_state["viewport"],
        )
    if trk_state.get("changed") or force_full:
        repaint_mode = trk_state["repaint_mode"]
        if not (list_tick or nav_fast) and repaint_mode != "full_column":
            repaint_mode = "viewport_only"
        draw_player_column(
            ui, 1, t("menu_playlist").upper(), track_list, trk_state["selected_idx"], focus, active_col, list_y, list_h, col_w, max_chars,
            type="track", pl_idx=pl_idx, library=library,
            repaint_mode=repaint_mode,
            redraw_indices=(trk_state["selected_idx"],),
            view_state=trk_state["viewport"],
        )
    if pls_state.get("changed") or force_full:
        repaint_mode = pls_state["repaint_mode"]
        if not (list_tick or nav_fast) and repaint_mode != "full_column":
            repaint_mode = "viewport_only"
        draw_player_column(
            ui, 2, t("menu_playlist_manager").upper() if t("menu_playlist_manager") != "menu_playlist_manager" else "LISTS", playlists, pls_state["selected_idx"], focus, active_col, list_y, list_h, col_w, max_chars,
            type="plist", active_pl=playlist.filename if playlist else "",
            repaint_mode=repaint_mode,
            redraw_indices=(pls_state["selected_idx"],),
            view_state=pls_state["viewport"],
        )

def render_now_playing(ui, track_name, is_playing, loop_mode, playlist=None, player=None, shuffle=False, force_full=False, seek_msg="", focus=0, btn_idx=3, playlists=None, playlist_idx=0, library_items=None, l_idx=0, active_col=1, swap=True, settings=None, library=None, list_tick=False, nav_fast=False):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    now = time.ticks_ms()
    last_state = ui.last_np_state if ui.last_np_state else {}
    use_cached_timing = nav_fast and focus == 1 and last_state and not force_full
    auto_expand = settings.config.get("auto_expand_library", True) if settings else True
    library_tree = library_items if library_items is not None else (library.get_tree_view(auto_expand) if library else [])

    if use_cached_timing:
        curr_sec = last_state.get("sec", 0)
        total_sec = last_state.get("tot", 0)
    elif player and hasattr(player, "get_timing_seconds"):
        curr_sec, total_sec = player.get_timing_seconds()
        curr_sec = int(curr_sec)
        total_sec = int(total_sec)
    else:
        curr_sec = int(player.get_pos_seconds()) if player else 0
        total_sec = int(player.get_duration_seconds()) if player else 0
    vol = settings.config.get("volume", 50) if settings else 50

    track_count = len(playlist.tracks) if playlist and playlist.tracks else 0
    pl_idx = playlist.current_index if playlist else -1
    e_idx = playlist.editor_playlist_idx if playlist else 0
    if library_tree:
        l_idx = max(0, min(l_idx, len(library_tree) - 1))
    else:
        l_idx = 0
    if playlist and playlist.tracks:
        e_idx = max(0, min(e_idx, len(playlist.tracks) - 1))
    else:
        e_idx = 0
    if playlists:
        playlist_idx = max(0, min(playlist_idx, len(playlists) - 1))
    else:
        playlist_idx = 0

    norm_track = track_name.lstrip("/") if track_name else ""

    scroll_changed = False
    text_x = 90; max_c = (sw - text_x - 10) // 6
    name = track_name.rsplit("/", 1)[-1] if track_name else ""
    meta_title = ""
    meta_artist = ""
    meta_album = ""
    if player and hasattr(player, "current_id3") and player.current_id3 and player.current_id3.get("title"):
        meta_title = player.current_id3["title"]
        name = meta_title

    info_str = ""
    if norm_track:
        if player and hasattr(player, "current_id3") and player.current_id3:
            id3 = player.current_id3
            if id3.get("artist"):
                meta_artist = id3["artist"]
                info_str = meta_artist
                if id3.get("album"):
                    meta_album = id3["album"]
                    info_str += f" - {meta_album}"
    meta_sig = (meta_title, meta_artist, meta_album)
    text_changed = last_state.get("meta_sig") != meta_sig

    needs_scroll = len(name) > max_c
    needs_scroll2 = len(info_str) > max_c
    if (not nav_fast) and is_playing and time.ticks_diff(now, ui.last_scroll_time) > 200:
        if needs_scroll:
            ui.scroll_pos += 1
        if needs_scroll2:
            ui.scroll_pos2 += 1
        ui.last_scroll_time = now
        if needs_scroll or needs_scroll2:
            scroll_changed = True

    blink_state = last_state.get("blink", 0) if use_cached_timing else ((now // 500) % 2)
    is_paused = player.is_paused(is_playing) if player else False
    blink_changed = (not use_cached_timing) and is_paused and blink_state != last_state.get("blink")

    time_changed = force_full or last_state.get("sec") != curr_sec or last_state.get("tot") != total_sec
    track_changed = last_state.get("track") != norm_track
    if track_changed or text_changed:
        ui.scroll_pos = 0
        ui.scroll_pos2 = 0

    cover_path = None
    if player and hasattr(player, "current_id3") and player.current_id3:
        cover_path = player.current_id3.get("cover")
    if cover_path: cover_path = cover_path.lstrip("/")

    last_cover = last_state.get("last_cover") if last_state else None
    cover_changed = cover_path != last_cover

    can_load = player.can_load_heavy_assets if player else False
    last_can_load = last_state.get("can_load", False)
    load_triggered = can_load and not last_can_load and ui.cover_drawn_path != cover_path

    if track_changed or not last_state:
        force_full = True
        ui.cover_draw_count = 2
    elif cover_changed or load_triggered:
        ui.cover_draw_count = 2

    playback_changed = force_full or last_state.get("playing") != is_playing
    buttons_changed = force_full or last_state.get("playing") != is_playing or last_state.get("focus") != focus or last_state.get("btn") != btn_idx or last_state.get("shuf") != shuffle or last_state.get("loop") != loop_mode
    button_indices = None
    if buttons_changed and not force_full:
        button_state_changed = (
            last_state.get("playing") != is_playing or
            last_state.get("shuf") != shuffle or
            last_state.get("loop") != loop_mode
        )
        if not button_state_changed:
            prev_btn = last_state.get("btn", btn_idx)
            if prev_btn == btn_idx:
                button_indices = (btn_idx,)
            else:
                button_indices = (prev_btn, btn_idx)
    footer_changed = force_full or last_state.get("focus") != focus or last_state.get("active_col") != active_col
    status_changed = force_full or last_state.get("vol") != vol or last_state.get("shuf") != shuffle or last_state.get("loop") != loop_mode
    controls_changed = time_changed or buttons_changed or footer_changed or status_changed or track_changed
    seek_changed = force_full or last_state.get("seek") != seek_msg

    last_focus = last_state.get("focus")
    last_col = last_state.get("active_col")
    nav_changed = (focus != last_focus or active_col != last_col)
    list_h = sh - 162
    list_view_h = list_h - 19
    item_h = 16
    view_policy, scroll_offset = _list_policy(settings)
    lib_state = _column_state("lib", l_idx, len(library_tree), list_view_h, item_h, focus == 1 and active_col == 0, last_state, view_policy, scroll_offset)
    trk_state = _column_state("trk", e_idx, track_count, list_view_h, item_h, focus == 1 and active_col == 1, last_state, view_policy, scroll_offset)
    pls_state = _column_state("pls", playlist_idx, len(playlists) if playlists else 0, list_view_h, item_h, focus == 1 and active_col == 2, last_state, view_policy, scroll_offset)
    lib_changed = force_full or last_state.get("l_idx") != l_idx or (nav_changed and (active_col == 0 or last_col == 0))
    trk_changed = force_full or e_idx != last_state.get("e_idx") or pl_idx != last_state.get("pl_idx") or track_count != last_state.get("trk_count") or (nav_changed and (active_col == 1 or last_col == 1))
    pls_changed = force_full or last_state.get("plist_idx") != playlist_idx or (nav_changed and (active_col == 2 or last_col == 2))
    lib_state["changed"] = lib_changed
    trk_state["changed"] = trk_changed
    pls_state["changed"] = pls_changed
    lib_state["repaint_mode"] = _choose_repaint_mode(last_state, "lib", lib_state, force_full=force_full, list_tick=(list_tick and focus == 1 and active_col == 0))
    trk_state["repaint_mode"] = _choose_repaint_mode(last_state, "trk", trk_state, force_full=force_full, list_tick=(list_tick and focus == 1 and active_col == 1))
    pls_state["repaint_mode"] = _choose_repaint_mode(last_state, "pls", pls_state, force_full=force_full, list_tick=(list_tick and focus == 1 and active_col == 2))
    nav_chrome_fast = False
    if nav_changed and not force_full:
        # Fast path for section switch: only active/inactive columns' chrome + selected rows.
        same_rows = (
            last_state.get("l_idx") == l_idx and
            last_state.get("e_idx") == e_idx and
            last_state.get("plist_idx") == playlist_idx
        )
        nav_chrome_fast = same_rows
    if list_tick and focus == 1:
        if active_col == 0:
            lib_changed = True
        elif active_col == 1:
            trk_changed = True
        elif active_col == 2:
            pls_changed = True
    pl_changed = lib_changed or trk_changed or pls_changed or (nav_changed)

    header_title = t("app_name") if t("app_name") != "app_name" else "VibesMP"
    header_updated = False
    view_changed = (ui.current_view != ui.last_view)
    if force_full and (view_changed or not last_state):
        ui.check_header_update(header_title)
    else:
        header_updated = ui.check_header_update(header_title)

    if not (time_changed or track_changed or text_changed or controls_changed or pl_changed or seek_changed or scroll_changed or blink_changed or cover_changed or load_triggered or header_updated) and not force_full:
        return False

    state = {
        "track": norm_track, "playing": is_playing, "sec": curr_sec, "tot": total_sec,
        "pl_idx": pl_idx, "seek": seek_msg, "focus": focus, "btn": btn_idx, "vol": vol, "shuf": shuffle,
        "plist_idx": playlist_idx, "e_idx": e_idx, "l_idx": l_idx, "active_col": active_col,
        "blink": blink_state, "loop": loop_mode, "last_cover": cover_path, "can_load": can_load,
        "marquee": needs_scroll or needs_scroll2, "meta_sig": meta_sig,
        "trk_count": track_count, "lib_count": len(library_tree), "plist_count": len(playlists) if playlists else 0,
        "lib_window": lib_state["window"], "trk_window": trk_state["window"], "pls_window": pls_state["window"],
        "lib_active": lib_state["active"], "trk_active": trk_state["active"], "pls_active": pls_state["active"],
        "lib_scroll": lib_state["scroll"], "trk_scroll": trk_state["scroll"], "pls_scroll": pls_state["scroll"],
        "lib_policy": view_policy, "trk_policy": view_policy, "pls_policy": view_policy
    }

    if force_full and (view_changed or not last_state):
        _perf_inc(ui, "full_player_repaints")
        ui.draw_background()
        ui.render_header_footer(header_title)
        ui.cover_drawn_path = None
    elif header_updated and not force_full:
        ui.render_header_footer(header_title)

    ui.last_view = ui.current_view

    metadata_changed = force_full or time_changed or track_changed or text_changed or playback_changed or seek_changed or scroll_changed or blink_changed or cover_changed or load_triggered
    if force_full or (not list_tick and metadata_changed):
        _perf_inc(ui, "metadata_repaints")
        _draw_player_metadata(ui, player, cover_path, norm_track, is_playing, blink_state, curr_sec, total_sec, sw, last_cover, force_full, time_changed, playback_changed, blink_changed, scroll_changed, track_changed, text_changed)

        # Draw Seek Message overlay if active
        if seek_msg:
            well_bg = ui.theme.get("panel_c", ui.theme["well"])
            ui.draw.fill_rectangle(Vector(sw - 60, 38), Vector(55, 14), well_bg)
            ui.draw.text(Vector(sw - 55, 38), seek_msg, ui.theme["highlight_c"])
        elif seek_changed and not force_full:
            well_bg = ui.theme.get("panel_c", ui.theme["well"])
            ui.draw.fill_rectangle(Vector(sw - 60, 38), Vector(55, 14), well_bg)

    if force_full or (not list_tick and controls_changed):
        _draw_player_controls(
            ui, player, is_playing, loop_mode, shuffle, focus, btn_idx, active_col,
            curr_sec, total_sec, sw, sh, vol, force_full,
            progress_dirty=time_changed,
            buttons_dirty=buttons_changed,
            footer_dirty=footer_changed,
            info_dirty=track_changed or load_triggered,
            status_dirty=status_changed,
            info_track=norm_track,
            button_indices=button_indices,
        )

    if pl_changed or force_full:
        _perf_inc(ui, "list_repaints")
        _draw_player_lists(ui, library_tree, l_idx, playlist, pl_idx, e_idx, playlists, playlist_idx, focus, active_col, sw, sh, lib_state, trk_state, pls_state, library=library, list_tick=list_tick, nav_fast=(nav_fast or nav_chrome_fast), force_full=force_full)

    if ui.cover_draw_count > 0:
        ui.cover_draw_count -= 1

    ui.last_np_state = state
    if swap:
        _perf_inc(ui, "swaps")
        ui.draw.swap()
    return True


# ---- ui_library.py ----

from picoware.system.vector import Vector
from vibesmp_lib.core import t


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
from vibesmp_lib.core import t

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
        from vibesmp_lib.core import render_header_extras
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
        from vibesmp_lib.ui_dialogs import render_confirm
        render_confirm(self, title, message, selected_idx, scroll_idx)

    def render_modal(self, title, message, button_text="OK", scroll_idx=0):
        from vibesmp_lib.ui_dialogs import render_modal
        render_modal(self, title, message, button_text, scroll_idx)

    def render_progress_modal(self, title, current_item, count):
        from vibesmp_lib.ui_dialogs import render_progress_modal
        render_progress_modal(self, title, current_item, count)

    def render_input_dialog(self, title, text, cursor_pos=0, force_full=False):
        from vibesmp_lib.ui_dialogs import render_input_dialog
        render_input_dialog(self, title, text, cursor_pos, force_full)
