from picoware.system.vector import Vector
import time
from picoware.system.colors import TFT_WHITE
from vibesmp_lib.utils import get_filename
from vibesmp_lib.ui_utils import draw_scrollable_list
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
