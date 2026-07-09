# VibesMP now-playing renderer.

# ---- ui_player.py ----

from picoware.system.vector import Vector
from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_GREEN
from vibesmp_lib.utils import get_filename, format_time
from vibesmp_lib.resources import t
from vibesmp_lib.metadata_engine import draw_cover
from vibesmp_lib.ui_utils import draw_digit, draw_marquee, draw_player_button, draw_player_column, draw_progress_bar
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

