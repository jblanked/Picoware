import time


def _ticks_ms():
    """Return monotonic milliseconds, falling back to time.time."""
    try:
        return time.ticks_ms()
    except AttributeError:
        return int(time.time() * 1000)


def _ticks_diff(a, b):
    """Return the difference between two tick values in ms."""
    try:
        return time.ticks_diff(a, b)
    except AttributeError:
        return a - b


def _quote(path):
    """Shell-quote a path string for use in os.system calls."""
    return "'" + str(path).replace("'", "'\"'\"'") + "'"


class AudioInfo:
    def __init__(self, sample_rate=44100, channels=2, duration_seconds=180):
        self.sample_rate = sample_rate
        self.channels = channels
        self.duration = int(sample_rate * channels * duration_seconds)
        self.position = 0
        self.bitrate = 128000
        self.path = ""


class Audio:
    HIGH_BEEP = 880
    LOW_BEEP = 220
    SILENCE = 0

    NOTE_WHOLE = 2000
    NOTE_HALF = 1000
    NOTE_QUARTER = 500
    NOTE_EIGHTH = 250
    NOTE_SIXTEENTH = 125
    NOTE_THIRTYSECOND = 63
    NOTE_DOTTED_HALF = 1500
    NOTE_DOTTED_QUARTER = 750
    NOTE_DOTTED_EIGHTH = 375

    PITCH_C3 = 131
    PITCH_CS3 = 139
    PITCH_D3 = 147
    PITCH_DS3 = 156
    PITCH_E3 = 165
    PITCH_F3 = 175
    PITCH_FS3 = 185
    PITCH_G3 = 196
    PITCH_GS3 = 208
    PITCH_A3 = 220
    PITCH_AS3 = 233
    PITCH_B3 = 247
    PITCH_C4 = 262
    PITCH_CS4 = 277
    PITCH_D4 = 294
    PITCH_DS4 = 311
    PITCH_E4 = 330
    PITCH_F4 = 349
    PITCH_FS4 = 370
    PITCH_G4 = 392
    PITCH_GS4 = 415
    PITCH_A4 = 440
    PITCH_AS4 = 466
    PITCH_B4 = 494
    PITCH_C5 = 523
    PITCH_CS5 = 554
    PITCH_D5 = 587
    PITCH_DS5 = 622
    PITCH_E5 = 659
    PITCH_F5 = 698
    PITCH_FS5 = 740
    PITCH_G5 = 784
    PITCH_GS5 = 831
    PITCH_A5 = 880
    PITCH_AS5 = 932
    PITCH_B5 = 988
    PITCH_C6 = 1047
    PITCH_CS6 = 1109
    PITCH_D6 = 1175
    PITCH_DS6 = 1245
    PITCH_E6 = 1319
    PITCH_F6 = 1397
    PITCH_FS6 = 1480
    PITCH_G6 = 1568
    PITCH_GS6 = 1661
    PITCH_A6 = 1760
    PITCH_AS6 = 1865
    PITCH_B6 = 1976

    def __init__(self):
        object.__setattr__(self, "volume", 50)
        self._playing = False
        self._released = False
        self._info = None
        self._start_ms = 0
        self._start_position = 0
        self._mode = "stopped"
        self._current_source = ""
        self._radio_state = "stopped"
        self._radio_diag = tuple(0 for _ in range(18))
        self._player_cmd_file = ""
        self._player_status_file = ""
        self._player_status = {}
        self._player_active = False
        self._paused = False
        self._radio_temp_path = ""

    def _file_exists(self, path):
        try:
            import os

            os.stat(path)
            return True
        except OSError:
            return False

    def _build_player(self):
        try:
            import sim_runtime

            player_dir = sim_runtime.root + "/sim_mp/audio"
            binary = player_dir + "/sdl_audio_player"
            if not sim_runtime.build_native("audio-player"):
                print("[sim:audio] could not build SDL audio player")
                return ""
            return binary if self._file_exists(binary) else ""
        except Exception as e:
            print("[sim:audio] build failed:", e)
            return ""

    def _build_radio_player(self):
        try:
            import sim_runtime

            player_dir = sim_runtime.root + "/sim_mp/audio"
            binary = player_dir + "/sdl_radio_player"
            if not sim_runtime.build_native("radio-player"):
                print("[sim:audio] could not build SDL radio player")
                return ""
            return binary if self._file_exists(binary) else ""
        except Exception as e:
            print("[sim:audio] radio build failed:", e)
            return ""

    def _send_player_command(self, command):
        if not self._player_cmd_file:
            return
        try:
            with open(self._player_cmd_file, "w") as handle:
                handle.write(str(command) + "\n")
        except OSError:
            pass

    def _stop_player(self):
        self._send_player_command("stop")
        self._player_active = False

    def _read_player_status(self):
        if not self._player_status_file:
            return None
        try:
            with open(self._player_status_file, "r") as handle:
                text = handle.read()
        except OSError:
            return None
        out = {}
        for line in text.split("\n"):
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            try:
                if key in ("state", "error"):
                    out[key] = value
                else:
                    out[key] = int(value)
            except ValueError:
                out[key] = value
        self._player_status = out
        return out

    def _sync_player_status(self):
        status = self._read_player_status()
        if not status or not self._info:
            return False
        self._info.sample_rate = int(status.get("sample_rate", self._info.sample_rate))
        self._info.channels = int(status.get("channels", self._info.channels))
        duration = int(status.get("duration", self._info.duration))
        if duration > 0:
            self._info.duration = duration
        self._info.position = int(status.get("position", self._info.position))
        sidecar_playing = bool(int(status.get("playing", 0)))
        at_end = self._info.duration > 0 and self._info.position >= self._info.duration
        self._playing = sidecar_playing and not at_end
        if at_end and not self._paused:
            self._mode = "stopped" if self._mode != "radio" else self._mode
            if self._mode == "radio":
                self._radio_state = "stopped"
        elif self._mode == "radio":
            state = status.get("state", "")
            self._radio_state = state if isinstance(state, str) and state else ("playing" if self._playing else self._radio_state)
        return True

    def _start_player(self, source):
        try:
            import sim_runtime
            import os

            if sim_runtime.audio_mode != "real" or sim_runtime.headless:
                return False
            if source.startswith("http://") or source.startswith("https://"):
                return False
            host_path = sim_runtime.host_path(source)
            if not self._file_exists(host_path):
                host_path = source
            if not self._file_exists(host_path):
                return False
            binary = self._build_player()
            if not binary:
                return False
            self._stop_player()
            cmd_file = sim_runtime.sd_root + "/sim_audio.cmd"
            status_file = sim_runtime.sd_root + "/sim_audio.status"
            for path in (cmd_file, status_file):
                try:
                    os.remove(path)
                except OSError:
                    pass
            self._player_cmd_file = cmd_file
            self._player_status_file = status_file
            cmd = _quote(binary) + " " + _quote(host_path) + " " + _quote(cmd_file) + " " + _quote(status_file) + " >/tmp/picoware-sim-audio.log 2>&1 &"
            os.system(cmd)
            self._player_active = True
            for _ in range(8):
                time.sleep(0.05)
                if self._read_player_status():
                    return True
            return True
        except Exception as e:
            print("[sim:audio] player failed:", e)
            return False

    def _start_radio_player(self, url):
        try:
            import sim_runtime
            import os

            if sim_runtime.audio_mode != "real" or sim_runtime.headless:
                return False
            binary = self._build_radio_player()
            if not binary:
                return False
            self._stop_player()
            cmd_file = sim_runtime.sd_root + "/sim_audio.cmd"
            status_file = sim_runtime.sd_root + "/sim_audio.status"
            for path in (cmd_file, status_file):
                try:
                    os.remove(path)
                except OSError:
                    pass
            self._player_cmd_file = cmd_file
            self._player_status_file = status_file
            cmd = _quote(binary) + " " + _quote(url) + " " + _quote(cmd_file) + " " + _quote(status_file) + " >/tmp/picoware-sim-radio.log 2>&1 &"
            os.system(cmd)
            self._player_active = True
            self._radio_state = "startup_buffering"
            for _ in range(12):
                time.sleep(0.05)
                if self._read_player_status():
                    self._sync_player_status()
                    return True
            return True
        except Exception as e:
            print("[sim:audio] radio player failed:", e)
            return False

    def _download_radio_preview(self, url):
        try:
            import sim_runtime
            import os

            if sim_runtime.audio_mode != "real" or sim_runtime.headless:
                return ""
            temp = sim_runtime.sd_root + "/sim_radio_stream.mp3"
            try:
                os.remove(temp)
            except OSError:
                pass
            # Host downloader bridges network/audio for MicroPython.
            cmd = (
                "curl -L --silent --show-error --max-time 12 --output "
                + _quote(temp)
                + " "
                + _quote(url)
                + " >/tmp/picoware-sim-radio.log 2>&1"
            )
            if os.system(cmd) != 0:
                return ""
            try:
                if os.stat(temp)[6] <= 0:
                    return ""
            except OSError:
                return ""
            self._radio_temp_path = temp
            return temp
        except Exception as e:
            print("[sim:audio] radio download failed:", e)
            return ""

    def _source_exists(self, path):
        if not path:
            return False
        if path.startswith("http://") or path.startswith("https://"):
            return True
        try:
            import sim_runtime

            host_path = sim_runtime.host_path(path)
        except Exception:
            host_path = path
        try:
            import os

            os.stat(host_path)
            return True
        except OSError:
            return False

    def _duration_for_source(self, path):
        try:
            import sim_runtime
            import os

            host_path = sim_runtime.host_path(path)
            size = os.stat(host_path)[6]
            if size > 0:
                # Rough 128 kbit/s estimate, clamped.
                seconds = size * 8 // 128000
                if seconds < 5:
                    seconds = 5
                if seconds > 7200:
                    seconds = 7200
                return seconds
        except Exception:
            pass
        return 180

    def _update_position(self):
        if not self._info:
            return
        if self._player_active and self._sync_player_status():
            return
        if not self._playing:
            return
        elapsed_ms = _ticks_diff(_ticks_ms(), self._start_ms)
        samples_per_ms = self._info.sample_rate * self._info.channels / 1000
        position = self._start_position + int(elapsed_ms * samples_per_ms)
        if position >= self._info.duration:
            self._info.position = self._info.duration
            self._playing = False
            if self._mode == "radio":
                self._radio_state = "stopped"
            else:
                self._mode = "stopped"
            return
        self._info.position = position

    def _begin(self, source, mode="mp3"):
        if mode != "radio" and not self._source_exists(source):
            self.stop()
            return False
        self._current_source = source
        self._mode = mode
        self._playing = True
        self._released = False
        self._start_ms = _ticks_ms()
        self._start_position = 0
        self._paused = False
        duration = 86400 if mode == "radio" else self._duration_for_source(source)
        self._info = AudioInfo(duration_seconds=duration)
        self._info.path = source
        self._radio_state = "playing" if mode == "radio" else "stopped"
        return True

    def set_volume(self, value):
        value = int(value)
        if value < 0:
            value = 0
        if value > 100:
            value = 100
        object.__setattr__(self, "volume", value)
        self._send_player_command("volume " + str(value))

    def stop(self):
        self._update_position()
        self._stop_player()
        self._playing = False
        self._paused = False
        self._mode = "stopped"
        self._radio_state = "stopped"

    def release(self):
        self.stop()
        self._released = True

    def play(self, *args, **kwargs):
        self._playing = True
        self._mode = "tone"
        self._info = AudioInfo(duration_seconds=1)
        self._start_ms = _ticks_ms()
        self._start_position = 0
        self._paused = False
        return True

    def play_note(self, note):
        return self.play(note)

    def play_song(self, song):
        return self.play(song)

    def play_wav(self, path):
        ok = self._begin(path, "wav")
        if ok:
            self._start_player(path)
        return ok

    def play_mp3(self, path):
        ok = self._begin(path, "mp3")
        if ok:
            self._start_player(path)
        return ok

    def play_mp3_url(self, url, profile=None):
        if not (isinstance(url, str) and (url.startswith("http://") or url.startswith("https://"))):
            return False
        ok = self._begin(url, "radio")
        if ok:
            if not self._start_radio_player(url):
                preview = self._download_radio_preview(url)
                if preview and self._start_player(preview):
                    self._radio_state = "playing"
                else:
                    self._radio_state = "startup_buffering"
        return ok

    def radio_probe(self, url, profile=None):
        if isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
            return {"ok": True, "status": 200, "final_url": url, "headers": {}, "error": ""}
        return {"ok": False, "status": 0, "final_url": url, "headers": {}, "error": "invalid url"}

    def seek(self, position):
        if not self._info:
            return False
        self._update_position()
        position = int(position)
        if position < 0:
            position = 0
        if position > self._info.duration:
            position = self._info.duration
        self._info.position = position
        self._start_position = position
        self._start_ms = _ticks_ms()
        self._send_player_command("seek " + str(position))
        return True

    def pause(self):
        if not self._info:
            return False
        self._update_position()
        self._send_player_command("pause")
        self._playing = False
        self._paused = True
        self._start_position = self._info.position
        return True

    def resume(self):
        if not self._info:
            return False
        self._send_player_command("resume")
        self._playing = True
        self._paused = False
        self._start_ms = _ticks_ms()
        self._start_position = self._info.position
        if self._mode == "radio":
            self._radio_state = "playing"
        return True

    @property
    def initialized(self):
        return not self._released

    @property
    def is_playing(self):
        self._update_position()
        return self._playing

    @property
    def is_paused(self):
        return self._paused

    @property
    def is_sd_busy(self):
        return False

    @property
    def info(self):
        self._update_position()
        return self._info

    @property
    def radio_state(self):
        self._update_position()
        return self._radio_state

    @property
    def radio_diag(self):
        return self._radio_diag


class AudioNote:
    def __init__(self, left_frequency=0, right_frequency=0, duration_ms=0):
        self.left_frequency = left_frequency
        self.right_frequency = right_frequency
        self.duration_ms = duration_ms

    def set_left_frequency(self, value):
        self.left_frequency = value

    def set_right_frequency(self, value):
        self.right_frequency = value

    def set_duration_ms(self, value):
        self.duration_ms = value


class AudioSong:
    def __init__(self, name="", notes=(), description=""):
        self.name = name
        self.notes = notes
        self.description = description
