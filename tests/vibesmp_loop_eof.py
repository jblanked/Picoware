"""Regression coverage for VibesMP loop transitions at MP3 EOF.

Run from the repository root with:

    micropython tests/vibesmp_loop_eof.py

The simulator audio backend does not model SD-bus contention, so this test
uses the real VibesApp.run(), Player, and Playlist code with a small audio
fake.  The fake marks the SD decoder busy as soon as loop playback restarts.
No storage or metadata work may then run later in the same app frame.
"""

import sys
import time


# Keep simulator hardware shims ahead of the MicroPython package modules.
sys.path.insert(0, "src/MicroPython")
sys.path.insert(0, "simulator/hardware")
sys.path.insert(0, "builds/MicroPython/apps_unfrozen")

from vibesmp_lib.app import Playlist, VibesApp
from vibesmp_lib.player import Player
from vibesmp_lib.ui_utils import VIEW_MENU


class FakeInput:
    button = -1

    def reset(self):
        pass


class FakeViewManager:
    input_manager = FakeInput()


class FakeUI:
    current_view = VIEW_MENU
    focus = 0
    last_np_state = None
    active_list_overflow = False


class FakeSettings:
    config = {
        "auto_play_next": True,
        "shuffle": False,
        "focus_timeout": 10,
    }


class FakeAudio:
    def __init__(self, events):
        self.events = events
        self.is_playing = False
        self.is_sd_busy = False
        self.info = None
        self.played_paths = []
        self.decoder_release_at = None

    def set_volume(self, value):
        pass

    def stop(self):
        if (
            self.decoder_release_at is not None
            and time.ticks_diff(time.ticks_ms(), self.decoder_release_at) < 0
        ):
            raise AssertionError("audio stopped before Core 1 EOF teardown")
        self.events.append("audio:stop")
        self.is_playing = False
        self.is_sd_busy = False

    def play_mp3(self, path):
        self.events.append("loop:restart")
        self.played_paths.append(path)
        self.is_playing = True
        self.is_sd_busy = True
        return True


class FakeStorageManager:
    def __init__(self, events):
        self.events = events

    def tick(self):
        self.events.append("sd:storage")


class FakeLibrary:
    def __init__(self, events):
        self.events = events
        self.display_cache_version = 0

    def has_track_metadata(self, track):
        return False

    def load_track_metadata(self, track):
        self.events.append("sd:library-load")

    def metadata_queue_pending(self):
        return True

    def extract_next_metadata(self):
        self.events.append("sd:metadata-extract")
        return False


class LoopFrameHarness(VibesApp):
    def __init__(self, loop_mode, events):
        now = time.ticks_ms()

        self.events = events
        self.audio = FakeAudio(events)
        self.player = Player(self.audio)
        self.player.loop_mode = loop_mode
        self.player.user_stopped = False
        self.player.last_play_time = time.ticks_add(now, -3000)

        self.playlist = Playlist()
        if loop_mode == 1:
            self.playlist.tracks = ["/sd/Music/one.mp3"]
            self.playlist.current_index = 0
        else:
            self.playlist.tracks = [
                "/sd/Music/one.mp3",
                "/sd/Music/two.mp3",
            ]
            self.playlist.current_index = 1
        self.player.current_track = self.playlist.get_current()

        # Ignore Player construction's initial volume call.
        self.events[:] = []

        self._menus_initialized = True
        self.loading_screen = None
        self.settings = FakeSettings()
        self.ui = FakeUI()
        self.library = FakeLibrary(events)
        self.storage_manager = FakeStorageManager(events)

        self._nav_fast_frame = False
        self._nav_button = -1
        self._last_input_time = time.ticks_add(now, -5000)
        self.seek_msg = ""
        self.needs_refresh = False
        self._list_marquee_tick = False
        self._marquee_idle_ms = 1500

        # Make every SD/background path due during this frame.
        self._last_storage_tick = time.ticks_add(now, -1000)
        self._last_player_monitor_tick = now
        self._last_player_meta_tick = now
        self._last_player_end_tick = time.ticks_add(now, -1000)
        self._last_meta_prefetch_tick = time.ticks_add(now, -1000)
        self._last_metadata_extract_tick = time.ticks_add(now, -3000)
        self._meta_prefetch_idx = 0
        self._last_gc = now
        self._np_library_tree_key = None

        self._handled_no_render = False
        self.debug_perf = False
        self._loop_is_busy = False
        self._loop_is_playing = False
        self._loop_is_paused = False

        self.deferred_state = None
        self.timed_render_state = None

    def _prefetch_library_visible_metadata(self):
        self.events.append("sd:visible-prefetch")
        return False

    def _now_playing_tree_key(self):
        return ("changed",)

    def _prime_now_playing_lists(self):
        self.events.append("sd:prime-now-playing")
        return []

    def _deferred_saves(self, now, player_busy, is_playing):
        self.deferred_state = (player_busy, is_playing)

    def _timed_render_due(self, now, is_playing, is_busy, is_paused):
        self.timed_render_state = (is_playing, is_busy, is_paused)
        return False


def run_loop_case(loop_mode, name):
    events = []
    app = LoopFrameHarness(loop_mode, events)

    render_due = app.run(FakeViewManager())

    assert render_due, name + ": successful loop restart must request a render"
    assert events.count("loop:restart") == 1, name + ": expected one restart"
    restart_index = events.index("loop:restart")
    unsafe = [
        event
        for event in events[restart_index + 1 :]
        if event.startswith("sd:")
    ]
    assert not unsafe, name + ": SD work after restart: " + repr(unsafe)

    # A fix may skip deferred saves for this frame or call the helper with
    # refreshed state.  Calling it with the stale stopped state is unsafe.
    assert app.deferred_state in (None, (True, True)), (
        name + ": stale deferred-save state: " + repr(app.deferred_state)
    )
    assert app._loop_is_playing is True, name + ": loop playing cache is stale"
    assert app._loop_is_busy is True, name + ": loop busy cache is stale"
    assert app._loop_is_paused is False, name + ": loop pause cache is stale"
    assert app.timed_render_state == (True, True, False), (
        name + ": timed-render state is stale: " + repr(app.timed_render_state)
    )

    assert app.playlist.current_index == 0, name + ": playlist did not wrap"
    assert app.player.current_track == "/sd/Music/one.mp3", (
        name + ": wrong current track after restart"
    )
    assert app.audio.played_paths == ["/Music/one.mp3"], (
        name + ": wrong SD path passed to audio: " + repr(app.audio.played_paths)
    )


def run_decoder_release_case():
    events = []
    now = time.ticks_ms()
    audio = FakeAudio(events)
    player = Player(audio)
    playlist = Playlist()
    playlist.tracks = ["/sd/Music/one.mp3"]
    player.current_track = playlist.get_current()
    player.loop_mode = 1
    player.user_stopped = False
    player.last_play_time = time.ticks_add(now, -3000)
    events[:] = []

    audio.is_sd_busy = True
    assert player.check_end(playlist) is False, (
        "loop restart must wait until the decoder releases SD state"
    )
    assert events == [], "busy decoder was stopped or restarted: " + repr(events)

    audio.is_sd_busy = False
    assert player.check_end(playlist) is True, (
        "loop restart did not resume after decoder release"
    )
    assert events == ["audio:stop", "loop:restart"], (
        "unexpected decoder-release restart sequence: " + repr(events)
    )


def run_native_eof_tail_case():
    events = []
    now = time.ticks_ms()
    audio = FakeAudio(events)
    player = Player(audio)
    playlist = Playlist()
    playlist.tracks = ["/sd/Music/one.mp3"]
    player.current_track = playlist.get_current()
    player.loop_mode = 1
    player.user_stopped = False
    player.last_play_time = time.ticks_add(now, -3000)
    audio.decoder_release_at = time.ticks_add(time.ticks_ms(), 5)
    events[:] = []

    assert player.check_end(playlist) is True, (
        "loop restart did not wait for the native EOF teardown tail"
    )
    assert events == ["audio:stop", "loop:restart"], (
        "unexpected native EOF restart sequence: " + repr(events)
    )


run_loop_case(1, "loop-one")
run_loop_case(2, "loop-all")
run_decoder_release_case()
run_native_eof_tail_case()
print("VibesMP loop EOF regression: PASS")
