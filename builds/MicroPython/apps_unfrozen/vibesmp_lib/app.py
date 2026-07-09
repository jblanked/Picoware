from picoware.system.buttons import (
    BUTTON_CENTER, BUTTON_BACK, BUTTON_UP, BUTTON_DOWN,
    BUTTON_LEFT, BUTTON_RIGHT, BUTTON_ENTER,
    BUTTON_L, BUTTON_P, BUTTON_SPACE, BUTTON_DELETE, BUTTON_BACKSPACE,
    BUTTON_S, BUTTON_V, BUTTON_PERIOD, BUTTON_COMMA, BUTTON_N,
    BUTTON_LEFT_BRACKET, BUTTON_RIGHT_BRACKET, BUTTON_TAB, BUTTON_ESCAPE,
    BUTTON_LESS_THAN, BUTTON_GREATER_THAN, BUTTON_SLASH, BUTTON_COLON
)

import time
import json
from picoware.gui.list import List
from picoware.gui.file_browser import FileBrowser, FILE_BROWSER_SELECTOR
from picoware.gui.loading import Loading
from vibesmp_lib.utils import get_filename, get_parent_path
from vibesmp_lib.player import Player
from vibesmp_lib.playlist import Playlist
from vibesmp_lib.ui_utils import (
    UI, VIEW_MENU, VIEW_NOW_PLAYING,
    VIEW_SETTINGS, VIEW_LIBRARY, VIEW_MODAL, VIEW_KEYBOARD,
    VIEW_PLAYLIST_SELECTOR, VIEW_PLAYLIST_EDITOR, VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT
)
from vibesmp_lib.ui_utils import IconList
from vibesmp_lib.settings import Settings
from vibesmp_lib.resources import load_language, t, set_storage
from vibesmp_lib.utils import mkdir_p
from vibesmp_lib.resources import THEMES
from vibesmp_lib.resources import switch_view, handle_main_menu_input
import vibesmp_lib.resources as d

DEBUG_PERF = False

class VibesApp:
    def __init__(self, view_manager, loading_screen=None):
        self.view_manager = view_manager
        self.loading_screen = loading_screen
        from vibesmp_lib.settings import StorageManager
        self.storage_manager = StorageManager()
        self.storage_manager.set_storage(view_manager.storage)
        self.storage_manager.set_audio(view_manager.audio)
        set_storage(view_manager.storage)

        # Deferred loading
        self.settings = None; self.player = None; self.playlist = None
        self.ui = None; self.library = None
        self.dialog_type = None
        self.dialog_title = ""
        self.dialog_message = ""
        self.dialog_buffer = ""
        self.dialog_cursor_pos = 0
        self.dialog_selected_idx = 0
        self.dialog_scroll_idx = 0
        self.dialog_callback = None
        self.dialog_last_view = 1

        self._playlist_loaded = False; self._library_loaded = False; self._menus_initialized = False
        self.library_stack = []
        self.library_action_tracks = []
        self.library_action_item = None
        self.library_sort_mode = "title"
        self.library_last_search = ""

        self._char_map = {}
        for b in range(7, 33):  # BUTTON_A to BUTTON_Z
            self._char_map[b] = chr(97 + (b - 7))
        for b in range(33, 43):  # BUTTON_0 to BUTTON_9
            self._char_map[b] = chr(48 + (b - 33))
        from picoware.system.buttons import (
            BUTTON_SPACE, BUTTON_MINUS, BUTTON_UNDERSCORE, BUTTON_PERIOD, BUTTON_COMMA,
            BUTTON_SLASH, BUTTON_COLON
        )
        self._char_map[BUTTON_SPACE] = " "
        self._char_map[BUTTON_MINUS] = "-"
        self._char_map[BUTTON_UNDERSCORE] = "_"
        self._char_map[BUTTON_PERIOD] = "."
        self._char_map[BUTTON_COMMA] = ","
        self._char_map[BUTTON_SLASH] = "/"
        self._char_map[BUTTON_COLON] = ":"

        self.save_timer = 0; self._last_marquee_time = 0
        self._last_input_time = time.ticks_ms()
        self.seek_msg = ""; self.seek_timer = 0; self._last_seek_time = 0
        self.playlist_sel_idx = 0  # Cursor for VIEW_PLAYLIST_SELECTOR
        self._playback_state_pending = False
        self.needs_refresh = True
        self._list_marquee_tick = False
        self._marquee_idle_ms = 1500
        self._nav_fast_frame = False
        self._nav_button = -1
        self.debug_perf = DEBUG_PERF
        self.perf_counters = {
            "render_requests": 0,
            "render_executions": 0,
            "swaps": 0,
            "full_player_repaints": 0,
            "metadata_repaints": 0,
            "control_repaints": 0,
            "button_repaints": 0,
            "footer_repaints": 0,
            "list_repaints": 0,
            "cover_decodes": 0,
            "audio_info_reads": 0,
            "cover_extract_attempts": 0,
            "cover_extract_success": 0,
            "cover_extract_fail": 0,
            "cover_draw_attempts": 0,
            "cover_draw_success": 0,
            "cover_draw_fail": 0,
            "cover_decoder_fallbacks": 0,
        }
        self._last_progress_render = 0
        self._last_pause_blink_render = 0
        self._last_header_render = 0
        self._last_player_busy = False
        self._last_np_snapshot = None
        self._header_render_pending = False
        self._np_timed_render_pending = False
        self._last_storage_tick = 0
        self._last_player_monitor_tick = 0
        self._last_player_meta_tick = 0
        self._last_player_end_tick = 0
        self._last_meta_prefetch_tick = 0
        self._last_metadata_extract_tick = 0
        self._meta_prefetch_idx = 0
        self._library_meta_prefetch_idx = 0
        self._last_settings_save_request = 0
        self._last_playlist_save_request = 0
        self._last_playback_state_save_request = 0
        self._settings_save_idle_ms = 1500
        self._playlist_save_idle_ms = 1500
        self._playback_state_save_idle_ms = 2500
        self._loop_is_playing = False
        self._loop_is_busy = False
        self._loop_is_paused = False
        self._perf_input_start_ms = 0
        self._perf_render_start_ms = 0
        self._scan_progress_last_tick = 0
        self._scan_progress_last_count = -1
        self._scan_progress_updates = 0
        self._np_library_tree_cache = None
        self._np_library_tree_key = None
        self._handled_no_render = False

    def _perf_inc(self, name):
        if self.debug_perf:
            self.perf_counters[name] = self.perf_counters.get(name, 0) + 1

    def _perf_timing(self, prefix, elapsed):
        if not self.debug_perf:
            return
        count_key = prefix + "_count"
        total_key = prefix + "_total_ms"
        max_key = prefix + "_max_ms"
        min_key = prefix + "_min_ms"
        self.perf_counters[count_key] = self.perf_counters.get(count_key, 0) + 1
        self.perf_counters[total_key] = self.perf_counters.get(total_key, 0) + elapsed
        if elapsed > self.perf_counters.get(max_key, 0):
            self.perf_counters[max_key] = elapsed
        current_min = self.perf_counters.get(min_key, None)
        if current_min is None or elapsed < current_min:
            self.perf_counters[min_key] = elapsed

    def _perf_finish_render(self):
        if not self.debug_perf:
            return
        now = time.ticks_ms()
        if self._perf_render_start_ms:
            self._perf_timing("render", time.ticks_diff(now, self._perf_render_start_ms))
            self._perf_render_start_ms = 0
        if self._perf_input_start_ms:
            self._perf_timing("key_to_render", time.ticks_diff(now, self._perf_input_start_ms))
            self._perf_input_start_ms = 0

    def _perf_play_result(self, prefix, start_ms, ok):
        if not self.debug_perf or not start_ms:
            return
        elapsed = time.ticks_diff(time.ticks_ms(), start_ms)
        self._perf_timing(prefix, elapsed)
        self._perf_inc(prefix + "_ok" if ok else prefix + "_fail")

    def _player_play(self, track):
        start = time.ticks_ms() if self.debug_perf else 0
        ok = self.player.play(track)
        self._perf_play_result("play_press_to_return", start, ok)
        return ok

    def _player_resume(self):
        start = time.ticks_ms() if self.debug_perf else 0
        ok = self.player.resume()
        self._perf_play_result("resume_press_to_return", start, ok)
        return ok

    def _player_seek_delta(self, seconds, label):
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_seek_time) <= 300:
            return False
        self._last_seek_time = now
        if not self.player:
            return False
        if not self.player.seek(seconds):
            self.seek_msg = "Seek N/A"
            self.seek_timer = now
            return False
        if self.player.is_playing or self.player.is_paused():
            self.seek_msg = "{} {}s".format(label, abs(seconds))
            self.seek_timer = now
        return True

    def _player_previous(self):
        if not self.playlist:
            return False
        old_index = self.playlist.current_index
        t_path = self.playlist.prev_track()
        if not t_path:
            return False
        same_track = self.player and self.player.current_track == t_path
        same_index = self.playlist.current_index == old_index
        if same_track or same_index:
            if self.player and self.player.current_track == t_path and self.player.restart_current():
                return True
        return self._player_play(t_path)

    def _player_next(self):
        if not self.playlist:
            return False
        old_index = self.playlist.current_index
        shuffle = self.settings.config.get("shuffle", False) if self.settings else False
        t_path = self.playlist.next_track(self.player.loop_mode, shuffle, auto_advance=False)
        if not t_path:
            if (
                len(self.playlist.tracks) == 1
                and self.player
                and self.player.current_track == self.playlist.tracks[0]
                and self.player.restart_current()
            ):
                return True
            return False
        same_track = self.player and self.player.current_track == t_path
        same_index = self.playlist.current_index == old_index
        if same_track or same_index:
            if self.player and self.player.current_track == t_path and self.player.restart_current():
                return True
        return self._player_play(t_path)

    def _now_playing_tree_key(self):
        if not self.library or not self.settings:
            return None
        return (
            self.library.display_cache_version,
            len(self.library.tracks),
            bool(self.settings.config.get("auto_expand_library", True)),
        )

    def _prime_now_playing_lists(self):
        key = self._now_playing_tree_key()
        if key is None:
            self._np_library_tree_cache = []
            self._np_library_tree_key = None
            return []
        if self._np_library_tree_key == key and self._np_library_tree_cache is not None:
            self._perf_inc("np_library_tree_cache_hit")
            return self._np_library_tree_cache
        auto_expand = key[2]
        tree = self.library.get_tree_view(auto_expand)
        self._np_library_tree_cache = tree
        self._np_library_tree_key = key
        self._perf_inc("np_library_tree_cache_miss")
        return tree

    def _idle_for(self, now, delay_ms):
        return time.ticks_diff(now, self._last_input_time) >= delay_ms

    def _deferred_saves(self, now, player_busy, is_playing):
        if player_busy or is_playing:
            return

        if (
            self.playlist
            and self.playlist._is_dirty
            and not getattr(self.playlist, "_save_pending", False)
            and self._idle_for(now, self._playlist_save_idle_ms)
            and time.ticks_diff(now, self._last_playlist_save_request) >= self._playlist_save_idle_ms
        ):
            self.playlist.save(storage_manager=self.storage_manager)
            self._last_playlist_save_request = now
            self._perf_inc("playlist_save_requests")

        if (
            self.playlist
            and self.playlist._index_dirty
            and not getattr(self, "_playback_state_pending", False)
            and self._idle_for(now, self._playback_state_save_idle_ms)
            and time.ticks_diff(now, self._last_playback_state_save_request) >= self._playback_state_save_idle_ms
        ):
            self._save_playback_state()
            self._last_playback_state_save_request = now
            self._perf_inc("playback_state_save_requests")

        if (
            self.settings
            and self.settings._is_dirty
            and not getattr(self.settings, "_save_pending", False)
            and self._idle_for(now, self._settings_save_idle_ms)
            and time.ticks_diff(now, self._last_settings_save_request) >= self._settings_save_idle_ms
        ):
            self.settings.save(storage_manager=self.storage_manager)
            self._last_settings_save_request = now
            self._perf_inc("settings_save_requests")

    def _perf_finalize_summary(self):
        if not self.debug_perf:
            return
        for prefix in (
            "key_to_render",
            "render",
            "play_press_to_return",
            "resume_press_to_return",
        ):
            count = self.perf_counters.get(prefix + "_count", 0)
            total = self.perf_counters.get(prefix + "_total_ms", 0)
            if count:
                self.perf_counters[prefix + "_avg_ms"] = total // count

    def _now_playing_snapshot(self, is_playing, is_paused):
        if not self.ui:
            return None
        player = self.player
        playlist = self.playlist
        settings = self.settings
        return (
            self.ui.current_view,
            self.ui.focus,
            self.ui.active_col,
            self.ui.btn_idx,
            self.ui.l_idx,
            self.ui.playlist_idx,
            playlist.current_index if playlist else -1,
            playlist.editor_playlist_idx if playlist else -1,
            len(playlist.tracks) if playlist and playlist.tracks else 0,
            player.current_track if player else "",
            is_playing,
            is_paused,
            settings.config.get("shuffle", False) if settings else False,
            player.loop_mode if player else 0,
            player.volume if player else 0,
            self.seek_msg,
        )

    def _timed_render_due(self, now, is_playing, is_busy, is_paused):
        due = False
        np_due = False
        header_due = False
        if not self.ui:
            return due

        if self.ui.current_view == VIEW_NOW_PLAYING:
            snapshot = self._now_playing_snapshot(is_playing, is_paused)
            if snapshot != self._last_np_snapshot:
                self._last_np_snapshot = snapshot
                np_due = True

            if is_playing and time.ticks_diff(now, self._last_progress_render) >= 1000:
                self._last_progress_render = now
                np_due = True

            last_np = self.ui.last_np_state if self.ui.last_np_state else {}
            if is_playing and last_np.get("marquee"):
                if time.ticks_diff(now, self.ui.last_scroll_time) >= 200:
                    np_due = True

            if is_paused and time.ticks_diff(now, self._last_pause_blink_render) >= 500:
                self._last_pause_blink_render = now
                np_due = True

            if is_busy != self._last_player_busy:
                self._last_player_busy = is_busy
                np_due = True

        if self.ui.current_view not in (VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT):
            if time.ticks_diff(now, self._last_header_render) >= 1000:
                self._last_header_render = now
                header_due = True

        if np_due:
            self._np_timed_render_pending = True
            due = True
        if header_due:
            self._header_render_pending = True
            due = True
        return due

    def _lazy_init(self, loading=None):
        if self._menus_initialized: return
        try:
            if loading: loading.set_text("Creating directories..."); loading.animate()
            from vibesmp_lib.utils import mkdir_p
            mkdir_p(self.view_manager.storage, "picoware/vibesmp/playlists/")
            mkdir_p(self.view_manager.storage, "picoware/vibesmp/lang/")
            mkdir_p(self.view_manager.storage, "picoware/vibesmp/library/meta/")
            mkdir_p(self.view_manager.storage, "picoware/vibesmp/library/covers/")

            if loading: loading.set_text("Starting systems..."); loading.animate()
            self._init_core_systems()

            if loading: loading.set_text("Loading UI menus..."); loading.animate()
            menu_h = self.view_manager.draw.size.y - 60
            theme = self.ui.theme
            tc, bg, ac, pc = theme["text_c"], theme["bg_c"], theme["accent_c"], theme["panel_c"]
            from vibesmp_lib.ui_utils import IconList
            self.main_menu = IconList(self.view_manager.draw, 30, menu_h, tc, bg, ac, pc)
            self.settings_menu = IconList(self.view_manager.draw, 30, menu_h, tc, bg, ac, pc)
            self.library_menu = IconList(self.view_manager.draw, 30, menu_h, tc, bg, ac, pc)
            self.refresh_playlists(); self.update_menus()

            if loading: loading.set_text("Loading library..."); loading.animate()
            self._handle_first_run_flow()
            self._reset_library_browser()
            self._menus_initialized = True
        except (OSError, ValueError, KeyError) as e:
            import sys
            print(f"[ERROR] VibesApp init failed: {e}")
            sys.print_exception(e)
            self._menus_initialized = True # Prevent hot-looping even on failure
            self.view_manager.alert(f"Init Error:\n{e}")

    def _init_core_systems(self):
        if not self.settings:
            self.settings = Settings(self.view_manager.storage)
            if not self.view_manager.storage.exists("picoware/vibesmp/settings.json"): self.settings.save()
            self.debug_perf = DEBUG_PERF or bool(self.settings.config.get("debug_perf", False))
            set_storage(self.view_manager.storage)
            load_language(self.settings.config["language"])

        if not self.player:
            self.player = Player(self.view_manager.audio, self.view_manager.storage)
            self.player.volume = self.settings.config.get("volume", 100)
            self.player.loop_mode = self.settings.config.get("loop_mode", 0)
        if self.player:
            self.player.set_perf_counters(self.perf_counters if self.debug_perf else None)

        if not self.playlist:
            self.playlist = Playlist(self.view_manager.storage)
            if not self.view_manager.storage.exists("picoware/vibesmp/playlists/default.json"): self.playlist.save(force=True)

        if not self.ui:
            from vibesmp_lib.resources import load_theme
            self.ui = UI(self.view_manager.draw, load_theme(self.settings), self.view_manager, self.settings)
            from vibesmp_lib.metadata_engine import set_perf_counters as set_cover_perf_counters
            from vibesmp_lib.id3 import set_perf_counters as set_id3_perf_counters
            if self.debug_perf:
                self.ui.perf_counters = self.perf_counters
                set_cover_perf_counters(self.perf_counters)
                set_id3_perf_counters(self.perf_counters)
            else:
                set_cover_perf_counters(None)
                set_id3_perf_counters(None)
            if self.player:
                self.player.pre_play_callback = self._pre_play_render

        if not self._playlist_loaded:
            # Decoupled playback state loading
            state_path = "picoware/vibesmp/playback_state.json"
            try:
                if self.view_manager.storage.exists(state_path):
                    import json
                    data = self.view_manager.storage.read(state_path)
                    state = json.loads(data)
                    last_pl = state.get("playlist", "default.json")
                    self.playlist.load(last_pl, storage_manager=self.storage_manager)
                    idx = state.get("index", 0)
                    pos = state.get("pos", 0)
                    self.playlist.current_index = idx
                    self.playlist.editor_playlist_idx = idx
                    self.playlist._index_dirty = False

                    # Restore track and position to player
                    if 0 <= idx < len(self.playlist.tracks):
                        self.player.current_track = self.playlist.tracks[idx]
                        if pos > 0:
                            # We don't start playing, but we set the paused position
                            # so that hitting play/resume starts from here.
                            # We need to convert seconds to samples.
                            # Player._lazy_init hasn't happened yet, but we can set a flag.
                            self.player._paused_pos_resume = pos
                else:
                    self.playlist.load(storage_manager=self.storage_manager)
            except (OSError, ValueError) as e:
                import sys
                print(f"[ERROR] load_state: {e}")
                sys.print_exception(e)
                self.playlist.load(storage_manager=self.storage_manager)
            self._playlist_loaded = True
        if not self._library_loaded:
            from vibesmp_lib.vibes_library import Library
            self.library = Library(self.view_manager.storage)
            self._library_loaded = True
        if self.library and hasattr(self.library, "set_perf_counters"):
            self.library.set_perf_counters(self.perf_counters if self.debug_perf else None)

    def _pre_play_render(self, file_path):
        """Prime cheap track state before playback; defer metadata and cover IO."""
        try:
            if not self.ui or self.ui.current_view != VIEW_NOW_PLAYING:
                return False

            from vibesmp_lib.id3 import _id3_cache
            metadata = _id3_cache.get(file_path)
            if metadata:
                self.player.current_id3 = metadata
                self.player._meta_pending = False
            else:
                name = file_path.rsplit("/", 1)[-1]
                if name.lower().endswith(".mp3"):
                    name = name[:-4]
                self.player.current_id3 = {"title": name, "artist": "Loading...", "cover": None}
                self.player._meta_pending = True
            self.player.current_track = file_path
            self.needs_refresh = True
            return True
        except Exception as e:
            print("[ERROR] App: _pre_play_render failed:", e)
            return False

    def _handle_first_run_flow(self):
        if self.settings.config.get("first_run", True):
            import vibesmp_lib.resources as d
            from vibesmp_lib.resources import t
            d.open_confirm(self, t("first_run_title"), t("first_run_msg"), self._on_first_run_confirm, self._on_first_run_cancel)
            return # Wait for user response
        switch_view(self, VIEW_MENU)

    def _on_first_run_confirm(self):
        from vibesmp_lib.resources import t
        import vibesmp_lib.resources as d
        # Perform scan
        self._begin_scan_progress()
        count = self.library.scan(progress_callback=self._scan_progress)
        # Update settings
        self.settings.set("first_run", False)
        self.settings.save(storage_manager=getattr(self, "storage_manager", None))

        def on_alert_close():
            # Force transition to menu and refresh
            self._switch_view(VIEW_MENU)
            self.needs_refresh = True

        d.open_alert(self, t("scan_complete_title"), t("scan_complete_msg").format(count), on_alert_close)

    def _begin_scan_progress(self):
        self._scan_progress_last_tick = 0
        self._scan_progress_last_count = -1
        self._scan_progress_updates = 0
        if self.debug_perf:
            self.perf_counters["scan_progress_updates"] = 0
            self.perf_counters["scan_progress_skipped"] = 0

    def _scan_progress(self, path, count):
        import time
        from vibesmp_lib.resources import t
        now = time.ticks_ms()
        force = bool(self.library and getattr(self.library, "_scan_progress_force", False))
        if not force and self._scan_progress_last_count >= 0:
            elapsed = time.ticks_diff(now, self._scan_progress_last_tick)
            count_changed = count != self._scan_progress_last_count
            if count_changed:
                if count % 10 != 0 and elapsed < 200:
                    self._perf_inc("scan_progress_skipped")
                    return
            elif elapsed < 250:
                self._perf_inc("scan_progress_skipped")
                return
        self._scan_progress_last_tick = now
        self._scan_progress_last_count = count
        self._scan_progress_updates += 1
        if self.debug_perf:
            self.perf_counters["scan_progress_updates"] = self._scan_progress_updates
        self.ui.render_progress_modal(t("scanning_title"), path, count)

    def _on_first_run_cancel(self):
        self.settings.set("first_run", False)
        self.settings.save(storage_manager=getattr(self, "storage_manager", None))
        switch_view(self, VIEW_MENU)

    def _switch_view(self, view_id):
        switch_view(self, view_id)

    def is_running(self):
        return True

    def _is_fast_nav_button(self, view_id, button):
        if button not in (BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT):
            return False
        if view_id in (VIEW_MENU, VIEW_SETTINGS, VIEW_LIBRARY):
            return button in (BUTTON_UP, BUTTON_DOWN)
        if view_id == VIEW_PLAYLIST_SELECTOR:
            return button in (BUTTON_UP, BUTTON_DOWN)
        if view_id == VIEW_PLAYLIST_EDITOR:
            return True
        if view_id == VIEW_NOW_PLAYING and self.ui and self.ui.focus == 1:
            return True
        return False

    def run(self, view_manager):
        render_due = False
        if not self._menus_initialized:
            self._lazy_init(self.loading_screen)
            if self.loading_screen:
                self.loading_screen.stop(swap=False)
                self.loading_screen = None
            render_due = True
        if not self.settings or not self.ui:
            return render_due
        now = time.ticks_ms()
        _player_busy = bool(self.player and self.player.is_busy)
        _is_playing = bool(self.player and self.player.is_playing)
        _is_paused = bool(self.player and self.player.is_paused(_is_playing))
        self._loop_is_busy = _player_busy
        self._loop_is_playing = _is_playing
        self._loop_is_paused = _is_paused
        inp = view_manager.input_manager
        btn = inp.button if inp else -1
        v = self.ui.current_view
        self._nav_fast_frame = btn >= 0 and self._is_fast_nav_button(v, btn)
        self._nav_button = btn if self._nav_fast_frame else -1

        if btn >= 0:
            self._last_input_time = now
            if self.debug_perf:
                self._perf_input_start_ms = now
                self._perf_inc("input_events")

        # Focus Timeout Logic
        if self.ui and self.ui.current_view == VIEW_NOW_PLAYING and self.ui.focus == 1:
            timeout_s = self.settings.config.get("focus_timeout", 10)
            if timeout_s > 0 and time.ticks_diff(now, self._last_input_time) > timeout_s * 1000:
                self.ui.focus = 0
                self.needs_refresh = True
            # Keep focused-row marquee animation alive only when needed.
            if getattr(self.ui, "active_list_overflow", False):
                idle_ms = time.ticks_diff(now, self._last_input_time)
                allow_marquee = (not _is_playing) or (idle_ms >= self._marquee_idle_ms)
                if allow_marquee and time.ticks_diff(now, getattr(self, "_last_list_marquee", 0)) > 500:
                    self._list_marquee_tick = True
                    self._last_list_marquee = now

        if self.seek_msg and time.ticks_diff(now, self.seek_timer) > 1000:
            self.seek_msg = ""
            self.needs_refresh = True
            render_due = True

        handled = False
        self._handled_no_render = False
        try:
            if btn >= 0:
                # Priority 1: Modal Dialogs
                if v in (VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT):
                    import vibesmp_lib.resources as d
                    handled = d.handle_input(self, btn)

                # Priority 2: Views
                elif v == VIEW_MENU:
                    handled = handle_main_menu_input(self, btn)

                elif v == VIEW_NOW_PLAYING:
                    # Handle DELETE key globally in NP screen
                    if btn in (BUTTON_DELETE, BUTTON_BACKSPACE):
                        if self.ui.active_col == 1: # Tracks
                            self.playlist.remove_track(self.playlist.editor_playlist_idx)
                            self.needs_refresh = True
                            handled = True
                        elif self.ui.active_col == 2: # Playlists
                            p_idx = self.ui.playlist_idx
                            if 0 < p_idx < len(self.ui_playlists):
                                p_name = self.ui_playlists[p_idx]
                                self._confirm_playlist_delete_action(p_name)
                            self.needs_refresh = True
                            handled = True

                    if not handled:
                        handled = self._handle_now_playing_input(btn, inp)

                elif v == VIEW_SETTINGS:
                    from vibesmp_lib.resources import handle_settings_input as handle_input
                    handle_input(self, btn)
                    handled = True # Settings handles its own refresh/state

                elif v == VIEW_LIBRARY:
                    handled = self._handle_library_input(btn, inp)

                elif v == VIEW_PLAYLIST_SELECTOR:
                    handled = self._handle_playlist_selector_input(btn, inp)

                elif v == VIEW_PLAYLIST_EDITOR:
                    handled = self._handle_playlist_editor_input(btn, inp)

                # Global fallback for BUTTON_BACK if not handled by view
                if not handled and btn == BUTTON_BACK:
                    if v != VIEW_MENU:
                        switch_view(self, VIEW_MENU)
                    else:
                        self.view_manager.back()
                    handled = True
        except OSError as e:
            import sys
            print(f"[ERROR] run input handling OSError: {e}")
            sys.print_exception(e)
            self.needs_refresh = True

        if not self._nav_fast_frame:
            # Storage Background Writer Tick — deferred during playback, SD bus belongs to Core 1
            if (
                hasattr(self, "storage_manager")
                and not _player_busy
                and not _is_playing
                and time.ticks_diff(now, self._last_storage_tick) >= 250
            ):
                self.storage_manager.tick()
                self._last_storage_tick = now

            # Background tasks
            if self.player:
                # Detect heavy asset loading transition to trigger automatic UI refresh (Cover Art)
                if self.ui and self.ui.current_view == VIEW_NOW_PLAYING and self.ui.last_np_state:
                    can_load = self.player.can_load_heavy_assets
                    if can_load and not self.ui.last_np_state.get("can_load", False):
                        self.needs_refresh = True

                if time.ticks_diff(now, self._last_player_monitor_tick) >= 250:
                    self.player.monitor_and_heal()
                    self._last_player_monitor_tick = now

                if _player_busy:
                    self.needs_refresh = True
                elif (
                    time.ticks_diff(now, self._last_player_meta_tick) >= 500
                    and self.player.load_pending_meta()
                ):
                    self._last_player_meta_tick = now
                    self.needs_refresh = True
                elif time.ticks_diff(now, self._last_player_meta_tick) >= 500:
                    self._last_player_meta_tick = now

                if (
                    self.settings.config.get("auto_play_next", True)
                    and time.ticks_diff(now, self._last_player_end_tick) >= 500
                ):
                    self._last_player_end_tick = now
                    if self.player.check_end(self.playlist, self.settings.config.get("shuffle", False)):
                        self.needs_refresh = True

            # Background metadata pre-fetcher
            if (
                self.library
                and self.playlist
                and not _player_busy
                and not _is_playing
                and time.ticks_diff(now, self._last_meta_prefetch_tick) >= 750
            ):
                if not self._prefetch_library_visible_metadata() and self.playlist.tracks:
                    tracks = self.playlist.tracks
                    total = len(tracks)
                    start = self._meta_prefetch_idx % total
                    for step in range(total):
                        idx = (start + step) % total
                        track = tracks[idx]
                        if not self.library.has_track_metadata(track):
                            self.library.load_track_metadata(track)
                            self._meta_prefetch_idx = idx + 1
                            break
                self._last_meta_prefetch_tick = now

            if (
                self.library
                and self.ui.current_view == VIEW_MENU
                and not _player_busy
                and not _is_playing
                and self._idle_for(now, 500)
                and self._np_library_tree_key != self._now_playing_tree_key()
            ):
                self._prime_now_playing_lists()

            if (
                self.library
                and not _player_busy
                and not _is_playing
                and self._idle_for(now, 2000)
                and time.ticks_diff(now, self._last_metadata_extract_tick) >= 2500
                and hasattr(self.library, "metadata_queue_pending")
                and self.library.metadata_queue_pending()
            ):
                before = self.library.display_cache_version
                if self.library.extract_next_metadata():
                    if (
                        self.ui
                        and self.ui.current_view == VIEW_LIBRARY
                        and self.library.display_cache_version != before
                    ):
                        self._library_refresh_current()
                self._last_metadata_extract_tick = now

            # Periodic memory pressure relief (Every 10 seconds)
            if not _player_busy and time.ticks_diff(now, getattr(self, "_last_gc", 0)) > 10000:
                from gc import collect
                collect()
                self._last_gc = now

            self._deferred_saves(now, _player_busy, _is_playing)

        if handled and self._handled_no_render and not self.needs_refresh and not self._list_marquee_tick:
            if inp:
                inp.reset()
            self._perf_inc("handled_no_render")
            handled = False

        if handled or self.needs_refresh or self._list_marquee_tick:
            if inp:
                inp.reset()
            render_due = True

        if self._timed_render_due(now, _is_playing, _player_busy, _is_paused):
            render_due = True

        if render_due:
            self._perf_inc("render_requests")
        return render_due

    def _handle_now_playing_input(self, button, inp):
        def no_render():
            self._handled_no_render = True
            self._perf_inc("np_input_noop")
            return True

        # Anti-bounce for heavy play actions
        if button in (BUTTON_CENTER, BUTTON_ENTER):
            now = time.ticks_ms()
            if self.player and self.player.last_play_time > 0 and time.ticks_diff(now, self.player.last_play_time) < 500:
                if not (self.ui.focus == 0 and self.ui.btn_idx in (1, 2, 5, 6)):
                    return no_render()

        # Priority: Global Play/Pause & Stop
        if button in (BUTTON_P, BUTTON_SPACE):
            if self.player.is_playing:
                self.player.pause()
            elif not self._player_resume():
                track = self.player.current_track or self.playlist.get_current()
                if track:
                    self._player_play(track)
            self.needs_refresh = True
            return True

        if button == BUTTON_ESCAPE:
            if self.player and (self.player.is_playing or self.player.current_track):
                self.player.stop()
                self.needs_refresh = True
                return True
            return no_render()

        # Seeking or Reordering ([ / ])
        if button == BUTTON_LEFT_BRACKET:
            if self.ui.focus == 1 and self.ui.active_col == 1:
                idx = self.playlist.editor_playlist_idx
                if idx > 0:
                    if self.playlist.move_track(idx, idx - 1):
                        self.playlist.editor_playlist_idx = idx - 1
                        self.needs_refresh = True
            else:
                seek_len = self.settings.config.get("seek_length", 5)
                self._player_seek_delta(-seek_len, "FB <<")
                self.needs_refresh = True
            return True
        if button == BUTTON_RIGHT_BRACKET:
            if self.ui.focus == 1 and self.ui.active_col == 1:
                idx = self.playlist.editor_playlist_idx
                if idx < len(self.playlist.tracks) - 1:
                    if self.playlist.move_track(idx, idx + 1):
                        self.playlist.editor_playlist_idx = idx + 1
                        self.needs_refresh = True
            else:
                seek_len = self.settings.config.get("seek_length", 5)
                self._player_seek_delta(seek_len, "FF >>")
                self.needs_refresh = True
            return True

        # Track Switch (< / >)
        if button == BUTTON_LESS_THAN:
            if self._player_previous():
                self.needs_refresh = True
                return True
            return no_render()
        if button == BUTTON_GREATER_THAN:
            if self._player_next():
                self.needs_refresh = True
                return True
            return no_render()

        # Shuffle Toggle (S)
        if button == BUTTON_S:
            self.settings.set("shuffle", not self.settings.config.get("shuffle", False))
            self.needs_refresh = True
            return True

        # New Playlist (N)
        if button == BUTTON_N:
            import vibesmp_lib.resources as d
            d.open_input(self, "New Playlist", "my_playlist", self._create_playlist)
            return True

        # Volume (V/./,)
        if button == BUTTON_V or button == BUTTON_PERIOD:
            new_volume = min(100, self.player.volume + 5)
            if new_volume == self.player.volume:
                return no_render()
            self.player.volume = new_volume
            self.settings.set("volume", self.player.volume)
            self.needs_refresh = True
            return True
        if button == BUTTON_COMMA:
            new_volume = max(0, self.player.volume - 5)
            if new_volume == self.player.volume:
                return no_render()
            self.player.volume = new_volume
            self.settings.set("volume", self.player.volume)
            self.needs_refresh = True
            return True


        # Loop Toggle (L)
        if button == BUTTON_L:
            self.player.loop_mode = (self.player.loop_mode + 1) % 3
            self.settings.set("loop_mode", self.player.loop_mode)
            self.needs_refresh = True
            return True

        if button == BUTTON_BACK:
            if self.ui.focus == 1:
                self.ui.focus = 0
                self.needs_refresh = True
            else:
                switch_view(self, VIEW_MENU)
            return True

        # Focus toggle
        if button == BUTTON_TAB:
            self.ui.focus = 1 if self.ui.focus == 0 else 0
            self.needs_refresh = True
            return True

        if self.ui.focus == 0:
            # Controls Logic
            if button == BUTTON_LEFT:
                self.ui.btn_idx = (self.ui.btn_idx - 1) % 8
                self.needs_refresh = True
                return True
            elif button == BUTTON_RIGHT:
                self.ui.btn_idx = (self.ui.btn_idx + 1) % 8
                self.needs_refresh = True
                return True
            elif button in (BUTTON_CENTER, BUTTON_ENTER):
                idx = self.ui.btn_idx
                if idx == 0: # Shuffle
                    s = not self.settings.config.get("shuffle", False)
                    self.settings.set("shuffle", s)
                elif idx == 1: # Prev
                    self._player_previous()
                elif idx == 2: # FB
                    seek_len = self.settings.config.get("seek_length", 5)
                    self._player_seek_delta(-seek_len, "FB <<")
                elif idx == 3: # Play/Pause
                    if self.player.is_playing: self.player.pause()
                    else:
                        if not self._player_resume():
                            # Fallback: Start fresh if resume not possible
                            track = self.player.current_track or self.playlist.get_current()
                            if track: self._player_play(track)
                elif idx == 4: # Stop
                    if self.player: self.player.stop()
                elif idx == 5: # FF
                    seek_len = self.settings.config.get("seek_length", 5)
                    self._player_seek_delta(seek_len, "FF >>")
                elif idx == 6: # Next
                    self._player_next()
                elif idx == 7: # Loop Mode
                    self.player.loop_mode = (self.player.loop_mode + 1) % 3
                    self.settings.set("loop_mode", self.player.loop_mode)
                self.needs_refresh = True
                return True
        else:
            # List Logic
            if button == BUTTON_LEFT:
                self.ui.active_col = (self.ui.active_col - 1) % 3
                self.needs_refresh = True
                return True
            elif button == BUTTON_RIGHT:
                self.ui.active_col = (self.ui.active_col + 1) % 3
                self.needs_refresh = True
                return True
            elif button == BUTTON_UP:
                changed = False
                if self.ui.active_col == 0:
                    old_idx = self.ui.l_idx
                    self.ui.l_idx = max(0, self.ui.l_idx - 1)
                    changed = self.ui.l_idx != old_idx
                elif self.ui.active_col == 1:
                    old_idx = self.playlist.editor_playlist_idx
                    self.playlist.editor_playlist_idx = max(0, self.playlist.editor_playlist_idx - 1)
                    changed = self.playlist.editor_playlist_idx != old_idx
                elif self.ui.active_col == 2:
                    old_idx = self.ui.playlist_idx
                    self.ui.playlist_idx = max(0, self.ui.playlist_idx - 1)
                    changed = self.ui.playlist_idx != old_idx
                if changed:
                    self.needs_refresh = True
                    return True
                return no_render()
            elif button == BUTTON_DOWN:
                changed = False
                if self.ui.active_col == 0: # Library
                    items = self._prime_now_playing_lists()
                    if self.ui.l_idx < len(items) - 1:
                        self.ui.l_idx += 1
                        changed = True
                elif self.ui.active_col == 1: # Tracks
                    if self.playlist.editor_playlist_idx < len(self.playlist.tracks) - 1:
                        self.playlist.editor_playlist_idx += 1
                        changed = True
                elif self.ui.active_col == 2: # Playlists
                    if self.ui.playlist_idx < len(self.ui_playlists) - 1:
                        self.ui.playlist_idx += 1
                        changed = True
                if changed:
                    self.needs_refresh = True
                    return True
                return no_render()
            elif button in (BUTTON_CENTER, BUTTON_ENTER):
                if self.ui.active_col == 0: # Library Add
                    items = self._prime_now_playing_lists()
                    if self.ui.l_idx < len(items):
                        path, depth, is_dir, is_exp, name = items[self.ui.l_idx]
                        if is_dir:
                            self.library.toggle_expanded(path)
                            self._np_library_tree_key = None
                        else: self.playlist.add_track(path)
                elif self.ui.active_col == 1: # Play Track
                    if self.playlist.tracks:
                        self.playlist.current_index = self.playlist.editor_playlist_idx
                        self._player_play(self.playlist.get_current())
                elif self.ui.active_col == 2: # Playlist Actions
                    if self.ui.playlist_idx == 0: # New Playlist
                        import vibesmp_lib.resources as d
                        d.open_input(self, "New Playlist", "my_playlist", self._create_playlist)
                    elif 0 < self.ui.playlist_idx < len(self.ui_playlists):
                        self.playlist.load(self.ui_playlists[self.ui.playlist_idx], storage_manager=self.storage_manager)
                self.needs_refresh = True
                return True

        return False

    def _create_playlist(self, name):
        if not name: return
        if not name.endswith(".json"): name += ".json"
        self.playlist.save_as(name, storage_manager=self.storage_manager)
        self.refresh_playlists()
        self.needs_refresh = True

    def _confirm_playlist_delete_action(self, name):
        import vibesmp_lib.resources as d
        from vibesmp_lib.resources import t

        if name == "default.json":
            d.open_confirm(
                self,
                t("confirm"),
                "Clear default playlist?",
                lambda: self._clear_playlist(name),
            )
            return

        d.open_confirm(
            self,
            t("confirm"),
            "Delete {}?".format(name),
            lambda: self._delete_playlist(name),
        )

    def _clear_playlist(self, name):
        if not name:
            return

        curr = self.playlist.filename
        if curr.startswith(self.playlist.base_dir):
            curr = curr[len(self.playlist.base_dir):]

        if name == curr:
            if self.player:
                self.player.stop()
                self.player.current_track = ""
                self.player.current_id3 = {"title": "", "artist": "", "cover": None}
                self.player._meta_pending = False
                self.player._paused_pos_resume = 0
            self.playlist.clear()
            self._save_playback_state()
        else:
            try:
                data = json.dumps({"tracks": [], "current_index": 0})
                full_path = f"picoware/vibesmp/playlists/{name}"
                if hasattr(self, "storage_manager"):
                    self.storage_manager.request_write(full_path, data)
                else:
                    self.view_manager.storage.write(full_path, data, "w")
            except (OSError, ValueError) as e:
                import sys
                print(f"[ERROR] _clear_playlist: {e}")
                sys.print_exception(e)

        self.needs_refresh = True

    def _delete_playlist(self, name):
        p = f"picoware/vibesmp/playlists/{name}"
        pending_entry = None
        if hasattr(self, "storage_manager"):
            pending_entry = self.storage_manager.cancel_write(p)
        try:
            deleted = self.view_manager.storage.remove(p)
        except OSError as e:
            import sys
            print(f"[ERROR] delete_playlist: {e}")
            sys.print_exception(e)
            deleted = False

        if deleted is False:
            if pending_entry and hasattr(self, "storage_manager"):
                self.storage_manager.pending_writes[p] = pending_entry
            self.needs_refresh = True
            return

        # If the deleted playlist is the currently active one, reload default.json
        curr = self.playlist.filename
        if curr.startswith(self.playlist.base_dir):
            curr = curr[len(self.playlist.base_dir):]
        if name == curr:
            self.playlist._is_dirty = False
            self.playlist._index_dirty = False
            self.playlist.load("default.json", storage_manager=self.storage_manager)
            self._save_playback_state()

        self.refresh_playlists()
        self.needs_refresh = True

    def _library_category_label(self, category):
        key = "lib_" + category
        val = t(key)
        if val != key:
            return val
        labels = {
            "all_songs": "All Songs",
            "artists": "Artists",
            "albums": "Albums",
            "folders": "Folders",
            "genres": "Genres",
            "recently_added": "Recently Added",
            "favorites": "Favorites",
            "search": "Search",
            "scan_options": "Scan Options",
            "sort": "Sort",
            "filters": "Filters",
            "stats": "Library Stats",
            "cleanup": "Cleanup",
            "scan": "Scan Library",
        }
        return labels.get(category, category)

    def _library_build_items(self, level):
        if not self.library:
            return []
        l_type = level.get("type")
        if l_type == "root":
            items = []
            for category, _label in self.library.get_categories():
                items.append({
                    "kind": "category",
                    "category": category,
                    "label": self._library_category_label(category),
                })
            return items
        if l_type == "category":
            return self.library.get_category_items(
                level.get("category"),
                query=level.get("query"),
                sort_mode=level.get("sort_mode") or self.library_sort_mode,
            )
        if l_type == "filter":
            return self.library.get_filtered_items(
                level.get("filter"),
                sort_mode=level.get("sort_mode") or self.library_sort_mode,
            )
        if l_type == "child":
            return self.library.get_child_items(level.get("category"), level.get("parent"))
        if l_type == "actions":
            return level.get("items", [])
        return []

    def _reset_library_browser(self):
        self.library_stack = [{
            "type": "root",
            "title": t("menu_library"),
            "items": [],
            "idx": 0,
        }]
        self.library_stack[0]["items"] = self._library_build_items(self.library_stack[0])
        self.library_action_tracks = []
        self.library_action_item = None

    def _library_current_level(self):
        if not self.library_stack:
            self._reset_library_browser()
        return self.library_stack[-1]

    def _library_push(self, level):
        level["items"] = self._library_build_items(level)
        level["idx"] = 0
        self.library_stack.append(level)
        self.needs_refresh = True

    def _library_refresh_current(self):
        level = self._library_current_level()
        level["items"] = self._library_build_items(level)
        if level["idx"] >= len(level["items"]):
            level["idx"] = max(0, len(level["items"]) - 1)
        self.needs_refresh = True

    def _library_tracks_from_item(self, item):
        if not item:
            return []
        kind = item.get("kind")
        if kind == "track":
            return [item.get("path")]
        if kind == "folder":
            return self.library.tracks_under_folder(item.get("path"))
        if kind in ("bucket", "collection", "cleanup_action"):
            return item.get("tracks", [])
        return []

    def _library_visible_tracks(self):
        if not self.library_stack:
            return []
        level = self._library_current_level()
        items = level.get("items", [])
        tracks = []
        if level.get("type") == "category":
            category = level.get("category")
            if category == "favorites":
                for path in self.library.tracks:
                    if self.library.is_favorite(path):
                        tracks.append(path)
            elif category in ("all_songs", "artists", "albums", "genres", "recently_added", "search"):
                tracks.extend(self.library.tracks)
        elif level.get("type") == "filter":
            for entry in self.library.get_filtered_items(level.get("filter"), sort_mode=self.library_sort_mode):
                if isinstance(entry, dict) and entry.get("path"):
                    tracks.append(entry.get("path"))
        for item in items:
            if isinstance(item, dict):
                kind = item.get("kind")
                if kind == "track":
                    path = item.get("path")
                    if path:
                        tracks.append(path)
                elif kind in ("bucket", "collection"):
                    for path in item.get("tracks", []):
                        if path:
                            tracks.append(path)
        return tracks

    def _prefetch_library_visible_metadata(self):
        if not self.library or self.ui.current_view != VIEW_LIBRARY:
            return False
        tracks = self._library_visible_tracks()
        total = len(tracks)
        if total <= 0:
            return False
        start = self._library_meta_prefetch_idx % total
        for step in range(total):
            idx = (start + step) % total
            track = tracks[idx]
            if not self.library.has_track_metadata(track):
                before = self.library.display_cache_version
                self.library.load_track_metadata(track)
                self._library_meta_prefetch_idx = idx + 1
                if self.library.display_cache_version != before:
                    self._library_refresh_current()
                return True
        return False

    def _library_open_actions(self, item):
        tracks = [p for p in self._library_tracks_from_item(item) if p]
        if not tracks:
            return
        self.library_action_tracks = tracks
        self.library_action_item = item
        labels = [
            ("play_now", t("lib_action_play_now")),
            ("play_next", t("lib_action_play_next")),
            ("add_current", t("lib_action_add_current")),
            ("create_playlist", t("lib_action_create_playlist")),
            ("remove_library", t("lib_action_remove_library")),
            ("show_info", t("lib_action_show_info")),
        ]
        if len(tracks) == 1:
            label = t("lib_action_remove_favorite") if self.library.is_favorite(tracks[0]) else t("lib_action_add_favorite")
            labels.insert(3, ("favorite", label))
        items = [{"kind": "action", "action": action, "label": label} for action, label in labels]
        self._library_push({
            "type": "actions",
            "title": t("lib_actions"),
            "items": items,
        })

    def _library_search(self, query):
        query = query or ""
        self.library_last_search = query
        if self.library:
            self.library.last_search = query
        self._library_push({
            "type": "category",
            "category": "search",
            "query": query,
            "title": "{}: {}".format(t("lib_search"), query),
        })

    def _library_create_playlist_from_tracks(self, name):
        if not name or not self.library_action_tracks:
            return
        if not name.endswith(".json"):
            name += ".json"
        try:
            data = json.dumps({"tracks": self.library_action_tracks, "current_index": 0})
            full_path = self.playlist.base_dir + name
            if hasattr(self, "storage_manager"):
                self.storage_manager.request_write(full_path, data)
            else:
                self.view_manager.storage.write(full_path, data, "w")
            self.refresh_playlists()
            self.needs_refresh = True
        except (OSError, ValueError, TypeError) as e:
            import sys
            print("[ERROR] _library_create_playlist_from_tracks:", e)
            sys.print_exception(e)

    def _library_scan_message(self, summary):
        return (
            "{}: {}\n{}: {}\n{}: {}\n{}: {}\n{}: {}\n{}: {}".format(
                t("lib_scan_total"),
                summary.get("total", 0),
                t("lib_scan_added"),
                summary.get("added", 0),
                t("lib_scan_removed"),
                summary.get("removed", 0),
                t("lib_scan_unchanged"),
                summary.get("unchanged", 0),
                t("lib_scan_found"),
                summary.get("found", 0),
                t("lib_scan_failed"),
                summary.get("failed", 0),
            )
        )

    def _library_run_scan(self, mode="full"):
        self._begin_scan_progress()
        quick = mode == "quick"
        remove_missing = mode in ("missing", "full")
        summary = self.library.scan(
            progress_callback=self._scan_progress,
            quick=quick,
            remove_missing=remove_missing,
            summary=True,
        )
        import vibesmp_lib.resources as d
        d.open_alert(self, t("scan_complete_title"), self._library_scan_message(summary))
        self._library_refresh_current()

    def _library_clear_favorites(self):
        count = self.library.clear_favorites()
        import vibesmp_lib.resources as d
        d.open_alert(self, t("lib_cleanup"), "{}: {}".format(t("lib_favorites_cleared"), count))
        self._library_refresh_current()

    def _library_remove_tracks(self, tracks):
        removed = self.library.remove_tracks(tracks)
        import vibesmp_lib.resources as d
        d.open_alert(self, t("lib_cleanup"), "{}: {}".format(t("lib_removed"), removed))
        if self.library_stack and self.library_stack[-1].get("type") == "actions":
            self.library_stack.pop()
        self._library_refresh_current()

    def _library_show_info(self):
        tracks = self.library_action_tracks
        item = self.library_action_item or {}
        if not tracks:
            return
        if len(tracks) == 1:
            info = self.library.get_track_info(tracks[0])
            msg = "{}\n{}\n{}\n{}\n{}".format(
                info.get("title", ""),
                info.get("artist", ""),
                info.get("album", ""),
                info.get("genre", ""),
                info.get("path", tracks[0]),
            )
        else:
            msg = "{}\n{}: {}".format(item.get("label", t("menu_library")), t("lib_tracks"), len(tracks))
        import vibesmp_lib.resources as d
        d.open_alert(self, t("lib_info"), msg)

    def _library_perform_action(self, action):
        tracks = [p for p in self.library_action_tracks if p]
        if not tracks:
            return
        if action == "play_now":
            if len(tracks) == 1:
                self._player_play(tracks[0])
            else:
                self.playlist.tracks = list(tracks)
                self.playlist.current_index = 0
                self.playlist.editor_playlist_idx = 0
                self.playlist._is_dirty = True
                self._player_play(tracks[0])
            self.needs_refresh = True
            return
        if action == "play_next":
            insert_at = self.playlist.current_index + 1 if self.playlist.tracks else 0
            for path in tracks:
                self.playlist.tracks.insert(insert_at, path)
                insert_at += 1
            self.playlist._is_dirty = True
            self.needs_refresh = True
            return
        if action == "add_current":
            for path in tracks:
                self.playlist.add_track(path)
            self.needs_refresh = True
            return
        if action == "remove_library":
            self._library_remove_tracks(tracks)
            return
        if action == "create_playlist":
            import vibesmp_lib.resources as d
            d.open_input(self, t("playlist_new"), "library_playlist", self._library_create_playlist_from_tracks)
            return
        if action == "favorite":
            if len(tracks) == 1:
                self.library.toggle_favorite(tracks[0])
                if self.library_stack and self.library_stack[-1].get("type") == "actions":
                    self.library_stack.pop()
                self._library_refresh_current()
            return
        if action == "show_info":
            self._library_show_info()
            return

    def _library_open_filter(self, item):
        label = item.get("label", t("lib_filters"))
        self._library_push({
            "type": "filter",
            "filter": item.get("filter"),
            "title": label,
        })

    def _library_apply_sort(self, item):
        self.library_sort_mode = item.get("sort_mode", "title")
        if len(self.library_stack) > 1:
            self.library_stack.pop()
        self._library_refresh_current()

    def _library_cleanup(self, item):
        action = item.get("cleanup")
        if action == "remove_missing":
            self._library_remove_tracks(item.get("tracks", []))
            return
        if action == "clear_favorites":
            self._library_clear_favorites()
            return

    def _handle_library_input(self, button, inp):
        if not self.library_stack:
            self._reset_library_browser()
        level = self._library_current_level()
        items = level.get("items", [])

        if button == BUTTON_BACK:
            if len(self.library_stack) > 1:
                self.library_stack.pop()
                self.needs_refresh = True
            else:
                switch_view(self, VIEW_MENU)
            return True
        if button == BUTTON_UP:
            if items:
                level["idx"] = (level.get("idx", 0) - 1) % len(items)
            else:
                level["idx"] = 0
            self.needs_refresh = True
            return True
        if button == BUTTON_DOWN:
            if items:
                level["idx"] = (level.get("idx", 0) + 1) % len(items)
            else:
                level["idx"] = 0
            self.needs_refresh = True
            return True
        if button in (BUTTON_LEFT, BUTTON_RIGHT):
            if not items:
                return True
            item = items[max(0, min(level.get("idx", 0), len(items) - 1))]
            if isinstance(item, dict) and item.get("kind") == "folder":
                expanded = bool(item.get("expanded", False))
                if (button == BUTTON_RIGHT and not expanded) or (button == BUTTON_LEFT and expanded):
                    self.library.toggle_expanded(item.get("path"))
                    self._library_refresh_current()
                return True
            if button == BUTTON_LEFT and len(self.library_stack) > 1:
                self.library_stack.pop()
                self.needs_refresh = True
                return True
            return False
        if button not in (BUTTON_CENTER, BUTTON_ENTER):
            return False

        if not items:
            return True
        item = items[max(0, min(level.get("idx", 0), len(items) - 1))]
        kind = item.get("kind") if isinstance(item, dict) else ""

        if kind == "category":
            category = item.get("category")
            if category == "scan":
                self._library_run_scan("full")
            elif category == "search":
                import vibesmp_lib.resources as d
                d.open_input(self, t("lib_search"), self.library_last_search, self._library_search)
            else:
                self._library_push({
                    "type": "category",
                    "category": category,
                    "title": item.get("label", self._library_category_label(category)),
                })
            self.needs_refresh = True
            return True

        if kind == "folder":
            self._library_open_actions(item)
            return True
        if kind == "category_filter":
            self._library_open_filter(item)
            return True
        if kind == "sort_mode":
            self._library_apply_sort(item)
            return True
        if kind == "scan_action":
            self._library_run_scan(item.get("scan_mode", "full"))
            return True
        if kind == "cleanup_action":
            self._library_cleanup(item)
            return True
        if kind == "info":
            return True
        if kind == "bucket":
            self._library_push({
                "type": "child",
                "category": item.get("category"),
                "parent": item,
                "title": item.get("label", ""),
            })
            return True
        if kind == "collection":
            self._library_open_actions(item)
            return True
        if kind == "track":
            if level.get("type") == "actions":
                return True
            self._library_open_actions(item)
            return True
        if kind == "action":
            self._library_perform_action(item.get("action"))
            return True
        return True

    def _handle_playlist_selector_input(self, button, inp):
        playlists = self.ui_playlists[1:] if self.ui_playlists else []  # Skip the '+ New' entry
        max_idx = len(playlists) - 1
        if button == BUTTON_BACK:
            switch_view(self, VIEW_MENU)
            return True
        if button == BUTTON_UP:
            self.playlist_sel_idx = max(0, self.playlist_sel_idx - 1)
            self.needs_refresh = True
            return True
        if button == BUTTON_DOWN:
            if self.playlist_sel_idx < max_idx:
                self.playlist_sel_idx += 1
            self.needs_refresh = True
            return True
        if button in (BUTTON_CENTER, BUTTON_ENTER):
            if playlists and self.playlist_sel_idx <= max_idx:
                self.playlist.load(playlists[self.playlist_sel_idx], storage_manager=self.storage_manager)
                self.needs_refresh = True
            return True
        if button in (BUTTON_DELETE, BUTTON_BACKSPACE):
            if playlists and self.playlist_sel_idx <= max_idx:
                p_name = playlists[self.playlist_sel_idx]
                self._confirm_playlist_delete_action(p_name)
                return True
        return False

    def _handle_playlist_editor_input(self, button, inp):
        if button == BUTTON_BACK:
            switch_view(self, VIEW_MENU)
            return True
        if button == BUTTON_LEFT:
            self.playlist.active_pane = 0
            self.needs_refresh = True
            return True
        if button == BUTTON_RIGHT:
            self.playlist.active_pane = 1
            self.needs_refresh = True
            return True
        if button == BUTTON_UP:
            if self.playlist.active_pane == 0:
                self.playlist.editor_library_idx = max(0, self.playlist.editor_library_idx - 1)
            else:
                self.playlist.editor_playlist_idx = max(0, self.playlist.editor_playlist_idx - 1)
            self.needs_refresh = True
            return True
        if button == BUTTON_DOWN:
            if self.playlist.active_pane == 0:
                items = self.library.tracks if self.library else []
                if self.playlist.editor_library_idx < len(items) - 1:
                    self.playlist.editor_library_idx += 1
            else:
                if self.playlist.editor_playlist_idx < len(self.playlist.tracks) - 1:
                    self.playlist.editor_playlist_idx += 1
            self.needs_refresh = True
            return True
        if button in (BUTTON_CENTER, BUTTON_ENTER):
            if self.playlist.active_pane == 0:
                items = self.library.tracks if self.library else []
                if items and self.playlist.editor_library_idx < len(items):
                    self.playlist.add_track(items[self.playlist.editor_library_idx])
            else:
                self.playlist.remove_track(self.playlist.editor_playlist_idx)
            self.needs_refresh = True
            return True
        return False

    def refresh_playlists(self):
        try:
            vpath = self.playlist.base_dir
            if not vpath.startswith("/"): vpath = "/" + vpath
            mkdir_p(self.view_manager.storage, vpath)
            items = self.view_manager.storage.read_directory(vpath)
            self.playlists = [i["filename"] for i in items if not i["is_directory"] and i["filename"].endswith(".json")]
        except OSError as e:
            import sys
            print(f"[ERROR] refresh_playlists: {e}")
            sys.print_exception(e)
            self.playlists = []

        # Unified list for UI (Action first, then data)
        from vibesmp_lib.resources import t
        self.ui_playlists = [t("new_playlist")] + self.playlists

    def update_menus(self):
        self.main_menu.clear()
        self.main_menu.add_item(t("menu_player"), "player")
        self.main_menu.add_item(t("menu_library"), "library")
        self.main_menu.add_item(t("menu_settings"), "settings")
        self.main_menu.add_item(t("menu_help"))

        self.library_menu.clear()
        self.library_menu.add_item(t("refresh_library"))

    def _save_playback_state(self, storage_manager=None, force_direct=False):
        if not self.playlist: return
        try:
            state = {
                "playlist": self.playlist.filename,
                "index": self.playlist.current_index,
                "pos": int(self.player.get_pos_seconds()) if self.player else 0
            }
            data = json.dumps(state)
            manager = None if force_direct else storage_manager
            if manager is None and not force_direct:
                manager = getattr(self, "storage_manager", None)

            if manager:
                def _mark_saved():
                    self._playback_state_pending = False

                def _mark_failed():
                    self._playback_state_pending = False
                    if self.playlist:
                        self.playlist._index_dirty = True

                manager.request_write(
                    "picoware/vibesmp/playback_state.json",
                    data,
                    on_success=_mark_saved,
                    on_error=_mark_failed,
                )
                self._playback_state_pending = True
                self.playlist._index_dirty = False
            else:
                if self.view_manager.storage.write("picoware/vibesmp/playback_state.json", data, "w"):
                    self._playback_state_pending = False
                    self.playlist._index_dirty = False
                else:
                    self._playback_state_pending = False
                    self.playlist._index_dirty = True
        except (OSError, ValueError) as e:
            import sys
            print(f"[ERROR] _save_playback_state: {e}")
            sys.print_exception(e)
            self._playback_state_pending = False
            if self.playlist:
                self.playlist._index_dirty = True

    def stop(self, view_manager):
        from vibesmp_lib.metadata_engine import cleanup_engine, set_perf_counters as set_cover_perf_counters
        from vibesmp_lib.id3 import set_perf_counters as set_id3_perf_counters
        set_cover_perf_counters(None)
        set_id3_perf_counters(None)
        cleanup_engine()
        if self.debug_perf:
            self._perf_finalize_summary()
            print("[PERF] VibesMP:", self.perf_counters)
        sm = getattr(self, "storage_manager", None)
        playlist_path = None
        if self.playlist:
            fname = self.playlist.filename
            if fname.startswith(self.playlist.base_dir):
                fname = fname[len(self.playlist.base_dir):]
            playlist_path = self.playlist.base_dir + fname

        if sm:
            if playlist_path:
                sm.cancel_write(playlist_path)
            sm.cancel_write("picoware/vibesmp/playback_state.json")
            sm.cancel_write("picoware/vibesmp/settings.json")

        if self.playlist:
            self.playlist.save(force=True, storage_manager=None)
            self._save_playback_state(force_direct=True)
        if self.player:
            self.player.stop()

        if self.settings:
            self.settings.save(force=True, storage_manager=None)

        # Flush all pending storage operations
        if sm:
            sm.close()

        # Explicit cleanup
        if hasattr(self, "main_menu"): del self.main_menu
        if hasattr(self, "settings_menu"): del self.settings_menu
        if hasattr(self, "library_menu"): del self.library_menu
        if hasattr(self, "_char_map"): del self._char_map
        self.settings = None; self.player = None; self.playlist = None
        self.ui = None; self.library = None
        from gc import collect; collect()

    def render(self, view_manager):
        if not self.ui: return
        if self.debug_perf:
            self._perf_render_start_ms = time.ticks_ms()
        self._perf_inc("render_executions")
        v = self.ui.current_view
        nav_fast = self._nav_fast_frame
        header_only = (
            self._header_render_pending and
            not self._np_timed_render_pending and
            not self.needs_refresh and
            not self._list_marquee_tick
        )
        if header_only:
            title = t("app_name") if t("app_name") != "app_name" else "VibesMP"
            if v == VIEW_SETTINGS:
                title = t("menu_settings")
            if self.ui.check_header_update(title):
                if self.ui.perf_counters is not None:
                    self.ui.perf_counters["swaps"] = self.ui.perf_counters.get("swaps", 0) + 1
                self.ui.draw.swap()
            self.ui.last_view = v
            self._header_render_pending = False
            self._np_timed_render_pending = False
            self._nav_fast_frame = False
            self._nav_button = -1
            self._perf_finish_render()
            return

        # Pre-importing for performance (cached in sys.modules anyway)
        if v in (VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT):
            import vibesmp_lib.resources as d
            d.render(self, self.ui)
            self.ui.last_view = v
            self.needs_refresh = False
            self._list_marquee_tick = False
            self._header_render_pending = False
            self._np_timed_render_pending = False
            self._nav_fast_frame = False
            self._nav_button = -1
            self._perf_finish_render()
            return

        if v == VIEW_MENU:
            self.ui.render_menu(self.main_menu, force_full=self.needs_refresh)
        elif v == VIEW_NOW_PLAYING:
            track = self.player.current_track if self.player else None
            is_playing = self._loop_is_playing if self.player else False
            library_tree = self._prime_now_playing_lists()
            np_force_full = (
                self.needs_refresh
                and not nav_fast
                and (self.ui.last_view != VIEW_NOW_PLAYING or not self.ui.last_np_state)
            )
            if self.needs_refresh and not np_force_full:
                self._perf_inc("np_partial_refreshes")
            self.ui.render_now_playing(track, is_playing, self.player.loop_mode if self.player else 0, self.playlist, self.player, self.settings.config.get("shuffle", False), force_full=np_force_full, seek_msg=self.seek_msg, playlists=self.ui_playlists, playlist_idx=self.ui.playlist_idx, library_items=library_tree, l_idx=self.ui.l_idx, active_col=self.ui.active_col, library=self.library, focus=self.ui.focus, btn_idx=self.ui.btn_idx, list_tick=self._list_marquee_tick, nav_fast=nav_fast)
        elif v == VIEW_SETTINGS:
            from vibesmp_lib.resources import render_settings
            render_settings(self, self.ui, force_full=self.needs_refresh)
        elif v == VIEW_LIBRARY:
            from vibesmp_lib.ui_utils import render_library_browser
            level = self._library_current_level()
            render_library_browser(
                self.ui,
                level.get("title", t("menu_library")),
                level.get("items", []),
                level.get("idx", 0),
                force_full=(self.needs_refresh and not nav_fast),
                nav_fast=nav_fast,
            )
        elif v == VIEW_PLAYLIST_SELECTOR:
            from vibesmp_lib.ui_playlist import render_playlist_selector
            playlists = self.ui_playlists[1:] if self.ui_playlists else []  # Skip '+ New' entry
            render_playlist_selector(self.ui, playlists, self.playlist_sel_idx, force_full=(self.needs_refresh and not nav_fast), nav_fast=nav_fast)
        elif v == VIEW_PLAYLIST_EDITOR:
            from vibesmp_lib.ui_playlist import render_playlist_editor
            items = self.library.tracks if self.library else []
            render_playlist_editor(self.ui, items, self.playlist, force_full=(self.needs_refresh and not nav_fast), nav_fast=nav_fast)

        self.ui.last_view = v
        self.needs_refresh = False
        self._list_marquee_tick = False
        self._header_render_pending = False
        self._np_timed_render_pending = False
        self._nav_fast_frame = False
        self._nav_button = -1
        self._perf_finish_render()
