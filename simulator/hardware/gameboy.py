import sim_runtime
import os
import time


BUTTON_NONE = -1

GB_BUTTON_UP = 0
GB_BUTTON_DOWN = 1
GB_BUTTON_RIGHT = 2
GB_BUTTON_LEFT = 3
GB_BUTTON_A = 59
GB_BUTTON_B = 58
GB_BUTTON_START = 57
GB_BUTTON_SELECT = 54

PICOWARE_BUTTON_CENTER = 4
PICOWARE_BUTTON_X = 30
PICOWARE_BUTTON_Z = 32
PICOWARE_BUTTON_SPACE = 43
PICOWARE_BUTTON_ENTER = 74


class GameBoy:
    def __init__(self):
        """Initialize a simulator-backed GameBoy emulator."""
        self.rom_path = ""
        self.save_state_path = None
        self.running = False
        self.frame = 0
        self.last_button = -1
        self.rom_size = 0
        self.rom_title = ""
        self.buttons_seen = []
        self._helper = ""
        self._frame_path = ""
        self._control_path = ""
        self._status_path = ""
        self._native = False
        self._warned_fallback = False
        self._held_button = -1
        self._held_frames = 0

    def __str__(self):
        """Return a readable representation."""
        return "GameBoy(rom_path={!r}, running={})".format(self.rom_path, self.running)

    def start(self, rom_path, save_state_path=None):
        """Load a ROM and start the emulator."""
        host_rom = sim_runtime.host_path(rom_path)
        with open(host_rom, "rb") as handle:
            header = handle.read(0x150)
            handle.seek(0, 2)
            self.rom_size = handle.tell()
        self.rom_path = rom_path
        self.save_state_path = save_state_path
        self.rom_title = self._title_from_header(header)
        self.running = True
        self.frame = 0
        self.last_button = -1
        self.buttons_seen = []
        self._held_button = -1
        self._held_frames = 0
        self._native = False
        self._frame_path = sim_runtime.sd_root + "/sim_gameboy_frame.rgb565"
        self._control_path = sim_runtime.sd_root + "/sim_gameboy_control.txt"
        self._status_path = sim_runtime.sd_root + "/sim_gameboy_status.txt"
        self._cleanup_sidecars()
        self._helper = self._helper_path()
        if self._helper:
            self._write_control(-1, 0)
            audio_env = ""
            if sim_runtime.audio_mode != "real" or sim_runtime.headless:
                audio_env = "SDL_AUDIODRIVER=dummy "
            cmd = "{}{} {} {} {} {} >/tmp/picoware-sim-gameboy.log 2>&1 &".format(
                audio_env,
                self._quote(self._helper),
                self._quote(host_rom),
                self._quote(self._frame_path),
                self._quote(self._control_path),
                self._quote(self._status_path),
            )
            os.system(cmd)
            status = self._wait_status()
            if status.get("state") == "running":
                self._native = True
                self._draw("GameBoy Emulator", "Starting " + str(self.rom_title or rom_path))
                return True
            if status.get("state") == "error":
                self.running = False
                raise TypeError("Failed to initialize Game Boy emulator")
        if not self._warned_fallback:
            print("[sim:gameboy] native helper unavailable; using placeholder fallback")
            self._warned_fallback = True
        self._draw("GameBoy Emulator", "ROM: " + str(self.rom_title or rom_path))
        return True

    def stop(self):
        """Stop the emulator."""
        if self._native:
            self._write_control(self.last_button, 1)
        if self.save_state_path:
            self._write_save_state()
        self.running = False
        self._native = False
        return None

    def run(self, button=-1):
        """Run one frame with the given button input."""
        if not self.running:
            return False
        button = self._normalize_button(button)
        button = self._effective_button(button)
        self.frame += 1
        self.last_button = button
        if button != -1:
            self.buttons_seen.append(button)
        if self._native:
            self._write_control(button, 0)
            self._blit_native_frame()
            return True
        if self.frame % 6 == 0:
            self._draw("GameBoy Emulator", "Input: {}".format(button))
        return True

    def snapshot(self):
        return {
            "rom_path": self.rom_path,
            "rom_title": self.rom_title,
            "rom_size": self.rom_size,
            "running": self.running,
            "frame": self.frame,
            "last_button": self.last_button,
            "buttons_seen": tuple(self.buttons_seen),
            "save_state_path": self.save_state_path,
        }

    def _title_from_header(self, header):
        if len(header) >= 0x144:
            raw = header[0x134:0x144].split(b"\x00", 1)[0]
            try:
                return raw.decode("ascii").strip()
            except Exception:
                return ""
        return ""

    def _write_save_state(self):
        try:
            path = sim_runtime.host_path(self.save_state_path)
            parent = path.rsplit("/", 1)[0]
            sim_runtime.mkdir_p(parent)
            with open(path, "w") as handle:
                handle.write("rom={}\n".format(self.rom_path))
                handle.write("title={}\n".format(self.rom_title))
                handle.write("frame={}\n".format(self.frame))
                handle.write("last_button={}\n".format(self.last_button))
        except Exception:
            pass

    def _normalize_button(self, button):
        """Map simulator/Picoware input to canonical GameBoy runner button codes."""
        aliases = {
            PICOWARE_BUTTON_X: GB_BUTTON_A,
            ord("x"): GB_BUTTON_A,
            ord("X"): GB_BUTTON_A,
            ord("]"): GB_BUTTON_A,
            PICOWARE_BUTTON_Z: GB_BUTTON_B,
            ord("z"): GB_BUTTON_B,
            ord("Z"): GB_BUTTON_B,
            ord("["): GB_BUTTON_B,
            PICOWARE_BUTTON_SPACE: GB_BUTTON_SELECT,
            PICOWARE_BUTTON_CENTER: GB_BUTTON_START,
            PICOWARE_BUTTON_ENTER: GB_BUTTON_START,
            13: GB_BUTTON_START,
            ord("="): GB_BUTTON_START,
            ord("-"): GB_BUTTON_SELECT,
        }
        # The normal simulator path is raw key -> Input.button -> GameBoy.run().
        # Raw ASCII space is also 32, matching Picoware BUTTON_Z, so direct
        # GameBoy.run(32) remains B; real Space reaches here as BUTTON_SPACE.
        try:
            return aliases.get(int(button), int(button))
        except Exception:
            return BUTTON_NONE

    def _effective_button(self, button):
        if button != BUTTON_NONE:
            self._held_button = button
            self._held_frames = 6
            return button
        held = self._held_viewer_button()
        if held != BUTTON_NONE:
            self._held_button = held
            self._held_frames = 0
            return held
        if self._held_frames > 0:
            self._held_frames -= 1
            return self._held_button
        self._held_button = BUTTON_NONE
        return BUTTON_NONE

    def _held_viewer_button(self):
        try:
            held = sim_runtime.is_key_held
        except AttributeError:
            return BUTTON_NONE
        for raw, gb_button in (
            (0xB5, GB_BUTTON_UP),
            (0xB6, GB_BUTTON_DOWN),
            (0xB7, GB_BUTTON_RIGHT),
            (0xB4, GB_BUTTON_LEFT),
            (ord("]"), GB_BUTTON_A),
            (ord("["), GB_BUTTON_B),
            (ord("="), GB_BUTTON_START),
            (ord("-"), GB_BUTTON_SELECT),
        ):
            if held(raw):
                return gb_button
        return BUTTON_NONE

    def _helper_path(self):
        try:
            path = sim_runtime.native_helper_path("gameboy/sim_gameboy_runner", "gameboy")
            if self._exists(path):
                return path
        except Exception as e:
            print("[sim:gameboy] helper build failed:", e)
        return ""

    def _exists(self, path):
        try:
            os.stat(path)
            return True
        except OSError:
            return False

    def _quote(self, value):
        return "'" + str(value).replace("'", "'\"'\"'") + "'"

    def _cleanup_sidecars(self):
        for path in (
            self._frame_path,
            self._frame_path + ".tmp",
            self._control_path,
            self._status_path,
        ):
            try:
                os.remove(path)
            except OSError:
                pass

    def _write_control(self, button, stop):
        try:
            with open(self._control_path, "w") as handle:
                handle.write("button={}\n".format(int(button)))
                handle.write("stop={}\n".format(int(stop)))
        except Exception:
            pass

    def _read_status(self):
        status = {}
        try:
            with open(self._status_path, "r") as handle:
                for line in handle:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        status[key] = value
        except OSError:
            pass
        return status

    def _wait_status(self):
        for _ in range(20):
            status = self._read_status()
            if status.get("state"):
                return status
            time.sleep(0.025)
        return {}

    def _blit_native_frame(self):
        lcd = getattr(sim_runtime, "_lcd", None)
        if lcd is None:
            return
        try:
            with open(self._frame_path, "rb") as handle:
                data = handle.read()
        except OSError:
            return
        expected = lcd.width * lcd.height * 2
        if len(data) != expected:
            return
        lcd._buffer[:] = data
        lcd.swap()

    def _draw(self, title, subtitle):
        lcd = getattr(sim_runtime, "_lcd", None)
        if lcd is None:
            return
        lcd._clear(0)
        lcd._rectangle(24, 16, 272, 240, 0x07E0)
        lcd._text(42, 36, title, 0xFFFF, 1)
        lcd._text(42, 58, subtitle[:32], 0xFFFF, 1)
        lcd._text(42, 88, "Frame " + str(self.frame), 0xFFE0, 1)
        lcd._text(42, 108, "Use BACK to exit", 0xFFE0, 1)
        lcd.swap()
