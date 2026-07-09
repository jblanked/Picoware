# VibesMP shared UI helpers.

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
from vibesmp_lib.utils import get_filename
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
