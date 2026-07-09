from gc import collect
import time
from vibesmp_lib.id3 import parse_id3
from vibesmp_lib.utils import format_time


class Player:
    def _audio_has_method(self, name):
        if hasattr(self.audio, name):
            return True
        try:
            return hasattr(self.audio.__class__, name)
        except Exception:
            return False

    def _audio_call(self, name, *args):
        method = getattr(self.audio, name, None)
        if method:
            return method(*args)
        method = getattr(self.audio.__class__, name, None)
        if method:
            return method(self.audio, *args)
        raise AttributeError("Audio has no method " + name)

    def __init__(self, audio, storage=None):
        self.audio = audio
        self.storage = storage
        self.loop_mode = 0
        self.user_stopped = True
        self._paused_pos = 0
        self._paused = False
        self._seeking = False
        self._recovering = False
        self.current_track = ""
        self._volume = 100
        self._audio_call("set_volume", self._volume)
        self._last_dur = 0
        self._sr_ch = 88200
        self.current_id3 = {"title": "", "artist": ""}
        self.last_play_time = 0
        self._last_pos_check = 0
        self._last_hw_pos = -1
        self._stall_count = 0
        self._io_throttled_until = 0
        self._last_hw_info = None
        self._last_info_time = 0
        self._paused_pos_resume = 0
        self._play_busy_until = 0
        self._dur_str_cache = "--:--"
        self._meta_pending = False
        self.pre_play_callback = None
        self.perf_counters = None
        self._perf_enabled = False

    def set_perf_counters(self, counters):
        self.perf_counters = counters
        self._perf_enabled = counters is not None

    def _perf_inc(self, name):
        if not self._perf_enabled:
            return
        counters = self.perf_counters
        counters[name] = counters.get(name, 0) + 1

    def _fade(self, target, start_v=None, steps=2, step_ms=10):
        current = self._volume if start_v is None else start_v
        diff = target - current
        for i in range(1, steps + 1):
            v = int(current + (diff * i / steps))
            try:
                self._audio_call("set_volume", v)
            except (OSError, AttributeError):
                pass
            time.sleep_ms(step_ms)
        try:
            self._audio_call("set_volume", target)
        except (OSError, AttributeError):
            pass

    def play(self, file_path, start_pos=0):
        if not file_path:
            return False

        self._audio_call("stop")
        time.sleep_ms(10)
        collect()

        self.user_stopped = False
        self._paused_pos = 0
        self._paused = False
        self.current_track = file_path

        skip_meta = False
        if self.pre_play_callback:
            try:
                if self.pre_play_callback(file_path):
                    skip_meta = True
            except Exception as e:
                print("[ERROR] player.play pre_play_callback:", e)

        try:
            self._audio_call("set_volume", self._volume)
            res = self._execute_play(file_path, start_pos, skip_meta=skip_meta)
            if not res:
                time.sleep_ms(10)
                res = self._execute_play(file_path, start_pos, skip_meta=skip_meta)
            return res
        except MemoryError:
            from vibesmp_lib.id3 import clear_cache
            clear_cache()
            collect()
            try:
                self._audio_call("stop")
                time.sleep_ms(10)
                return self._execute_play(file_path, start_pos, skip_meta=skip_meta)
            except (OSError, AttributeError):
                return False
        except (OSError, ValueError) as e:
            import sys
            print("[ERROR] player.play:", e)
            sys.print_exception(e)
            return False

    def _execute_play(self, file_path, start_pos, skip_meta=False, is_seconds=False):
        sd_path = file_path
        if sd_path.startswith("/sd/"):
            sd_path = sd_path[4:]
        elif sd_path.startswith("sd/"):
            sd_path = sd_path[3:]
        if not sd_path.startswith("/"):
            sd_path = "/" + sd_path

        from vibesmp_lib.id3 import _id3_cache
        if file_path in _id3_cache:
            self.current_id3 = _id3_cache[file_path]
            self._meta_pending = False
        elif not skip_meta:
            self._meta_pending = True
            from vibesmp_lib.utils import get_filename
            self.current_id3 = {"title": get_filename(file_path), "artist": "Loading...", "cover": None}
            self._dur_str_cache = "--:--"

        try:
            res = self._audio_call("play_mp3", sd_path)
            self.last_play_time = time.ticks_ms()
            if res:
                self._play_busy_until = time.ticks_add(time.ticks_ms(), 300)

            if res and start_pos > 0:
                time.sleep_ms(10)
                target_sample = int(start_pos)
                if is_seconds:
                    info = self.audio.info
                    if info:
                        sr = info.sample_rate or 44100
                        ch = info.channels or 2
                        self._sr_ch = sr * ch
                        target_sample = int(start_pos * self._sr_ch)
                self._audio_call("seek", target_sample)
        except (OSError, ValueError) as e:
            import sys
            print(f"[ERROR] player: play_mp3: {e}")
            sys.print_exception(e)
            res = False

        if res:
            time.sleep_ms(20)
            if not self.audio.is_playing:
                self._audio_call("stop")
                time.sleep_ms(10)
                self._audio_call("play_mp3", sd_path)
                time.sleep_ms(5)
                if start_pos > 0:
                    self._audio_call("seek", int(start_pos * self._sr_ch if is_seconds else start_pos))

            info = self.audio.info
            if info:
                sr = info.sample_rate or 44100
                ch = info.channels or 2
                self._sr_ch = sr * ch
                if info.duration > 0:
                    self._last_dur = info.duration / self._sr_ch
                    self._dur_str_cache = format_time(int(self._last_dur))
        return res

    def restart_current(self):
        if not self.current_track:
            return False
        self.user_stopped = False
        self._paused = False
        self._paused_pos = 0
        self._paused_pos_resume = 0
        if self.is_playing:
            self._seeking = True
            try:
                self._audio_call("set_volume", 0)
                ok = self.seek_absolute(0)
            finally:
                self._audio_call("set_volume", self._volume)
                self._seeking = False
            if ok:
                self.last_play_time = time.ticks_ms()
                self._play_busy_until = time.ticks_add(time.ticks_ms(), 300)
                return True
        return self.play(self.current_track, 0)

    def get_info(self, force=False):
        now = time.ticks_ms()
        if force or not self._last_hw_info or time.ticks_diff(now, self._last_info_time) > 500:
            self._last_hw_info = self.audio.info
            self._last_info_time = now
        return self._last_hw_info

    def monitor_and_heal(self):
        if not self.is_playing or self.user_stopped or self._seeking or self._recovering:
            self._stall_count = 0
            return True

        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_pos_check) < 500:
            return True

        self._last_pos_check = now
        info = self.get_info(force=True)
        curr_pos = info.position if info else -1

        if curr_pos != -1:
            if curr_pos == self._last_hw_pos:
                self._stall_count += 1
                if self._stall_count >= 10:
                    print(f"[ERROR] Player: Stall healing at {curr_pos}")
                    self._stall_count = 0
                    self._recovering = True
                    self._io_throttled_until = time.ticks_add(now, 15000)
                    try:
                        self._audio_call("stop")
                        time.sleep_ms(20)
                        self._execute_play(self.current_track, start_pos=curr_pos, skip_meta=True)
                    finally:
                        self._recovering = False
                    return False
            else:
                self._stall_count = 0
                self._last_hw_pos = curr_pos
        return True

    def load_pending_meta(self):
        if not self._meta_pending or not self.current_track or not self.can_load_heavy_assets:
            return False

        collect()
        file_path = self.current_track
        try:
            from vibesmp_lib.metadata_engine import get_track_hash
            file_hash = get_track_hash(file_path)
            meta_path = "picoware/vibesmp/library/meta/" + file_hash + ".json"

            temp_meta = None
            if self.storage and self.storage.exists(meta_path):
                data = self.storage.read(meta_path)
                import json
                temp_meta = json.loads(data)
                del data
            else:
                temp_meta = parse_id3(self.storage, file_path)

            if temp_meta:
                self.current_id3 = temp_meta
                from vibesmp_lib.id3 import _id3_cache
                if len(_id3_cache) > 50:
                    _id3_cache.clear()
                _id3_cache[file_path] = temp_meta
        except (OSError, ValueError) as e:
            import sys
            print(f"[ERROR] Player: Meta load failed: {e}")
            sys.print_exception(e)

        self._meta_pending = False
        collect()
        return True

    def stop(self):
        self._paused_pos = 0
        self.user_stopped = True
        self._paused = False
        if self.is_playing:
            self._fade(0)
        self._audio_call("stop")
        collect()

    def pause(self):
        if self.is_playing:
            info = self.audio.info
            self._paused_pos = info.position if info else 0
            self._paused = True
            self._fade(0)
            self._audio_call("stop")
            collect()
            return True
        return False

    def resume(self):
        if self.current_track and not self.is_playing:
            pos = self._paused_pos
            is_sec = False
            if pos == 0 and self._paused_pos_resume > 0:
                pos = self._paused_pos_resume
                is_sec = True
                self._paused_pos_resume = 0

            meta = self.current_id3 if isinstance(self.current_id3, dict) else {}
            has_meta = bool(meta.get("title") or meta.get("artist") or meta.get("cover"))
            skip_meta = True

            if self.last_play_time <= 0 or not has_meta:
                skip_meta = False
                if self.pre_play_callback:
                    try:
                        if self.pre_play_callback(self.current_track):
                            skip_meta = True
                    except Exception as e:
                        print("[ERROR] player.resume pre_play_callback:", e)

            res = self._execute_play(self.current_track, pos, skip_meta=skip_meta, is_seconds=is_sec)
            if res:
                self._fade(self._volume, start_v=0)
                self._paused_pos = 0
                self._paused = False
            return res
        return False

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, val):
        self._volume = max(0, min(100, val))
        self._audio_call("set_volume", self._volume)

    def check_end(self, playlist, shuffle=False):
        if self.user_stopped or self.is_paused():
            return False
        if time.ticks_diff(time.ticks_ms(), self.last_play_time) < 2000:
            return False

        if not self.is_playing:
            curr = playlist.get_current()
            if curr:
                if self.current_track != curr:
                    return self.play(curr)
                next_t = playlist.next_track(self.loop_mode, shuffle, auto_advance=True)
                if next_t:
                    return self.play(next_t)
        return False

    def seek(self, seconds):
        if self._seeking:
            return False

        if self.is_paused():
            if self._sr_ch <= 0:
                self._sr_ch = 88200

            delta_samples = int(seconds * self._sr_ch)
            new_pos = self._paused_pos + delta_samples
            if new_pos < 0:
                new_pos = 0
            dur = self.get_duration_seconds()
            if dur > 0:
                max_samples = int(dur * self._sr_ch)
                if new_pos >= max_samples:
                    new_pos = int(max_samples - (self._sr_ch // 10))

            self._paused_pos = new_pos
            return True

        info = self.audio.info
        if not info:
            return False

        self._sr_ch = (info.sample_rate or 44100) * (info.channels or 1)
        current_sec = info.position / self._sr_ch
        self._seeking = True
        try:
            self._audio_call("set_volume", 0)
            res = self.seek_absolute(current_sec + seconds)
        finally:
            self._audio_call("set_volume", self._volume)
            self._seeking = False
        if res:
            self._play_busy_until = time.ticks_add(time.ticks_ms(), 300)
        return res

    def seek_absolute(self, seconds):
        info = self.audio.info
        if not info:
            return False

        self._sr_ch = (info.sample_rate or 44100) * (info.channels or 1)
        target_sample = int(seconds * self._sr_ch)
        dur_samples = info.duration

        if target_sample < 0:
            target_sample = 0
        if dur_samples > 0 and target_sample >= dur_samples:
            target_sample = int(dur_samples - (self._sr_ch // 10))

        try:
            return self._audio_call("seek", target_sample)
        except (OSError, ValueError) as e:
            import sys
            print(f"[ERROR] Player.seek_absolute: {e}")
            sys.print_exception(e)
            return False

    def get_pos_seconds(self):
        info = self.audio.info
        if not info:
            return self._paused_pos / self._sr_ch if self._sr_ch > 0 else 0
        if self._sr_ch <= 0:
            self._sr_ch = (info.sample_rate or 44100) * (info.channels or 2)
        return info.position / self._sr_ch

    def get_duration_seconds(self):
        info = self.audio.info
        if not info:
            return self._last_dur
        if self._sr_ch <= 0:
            self._sr_ch = (info.sample_rate or 44100) * (info.channels or 2)
        if info.duration > 0:
            self._last_dur = info.duration / self._sr_ch
        return self._last_dur

    def get_timing_seconds(self):
        info = self.audio.info
        if not info:
            pos = self._paused_pos / self._sr_ch if self._sr_ch > 0 else 0
            return pos, self._last_dur
        if self._sr_ch <= 0:
            self._sr_ch = (info.sample_rate or 44100) * (info.channels or 2)
        pos = info.position / self._sr_ch
        if info.duration > 0:
            self._last_dur = info.duration / self._sr_ch
        return pos, self._last_dur

    @property
    def can_load_heavy_assets(self):
        if not self.current_track:
            return False
        if self._seeking or self._recovering:
            return False
        if self.user_stopped:
            return True
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_play_time) < 1500:
            return False
        if self._io_throttled_until > 0:
            if time.ticks_diff(self._io_throttled_until, now) > 0:
                return False
            self._io_throttled_until = 0
        return not self.is_playing or time.ticks_diff(now, self.last_play_time) > 2000

    @property
    def is_busy(self):
        return time.ticks_diff(self._play_busy_until, time.ticks_ms()) > 0

    @property
    def is_playing(self):
        return self.audio.is_playing

    def is_paused(self, is_playing=None):
        if self._paused:
            return True
        if self._paused_pos_resume <= 0:
            return False
        if is_playing is None:
            is_playing = self.is_playing
        return not is_playing
