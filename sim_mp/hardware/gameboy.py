import sim_runtime
import os


def _quote(path):
    return "'" + str(path).replace("'", "'\"'\"'") + "'"


class GameBoy:
    def __init__(self):
        self.rom_path = ""
        self.save_state_path = None
        self.running = False
        self.frame = 0
        self._frame_path = ""
        self._cmd_path = ""
        self._status_path = ""

    def __str__(self):
        return "GameBoy(rom_path={!r}, running={})".format(self.rom_path, self.running)

    def start(self, rom_path, save_state_path=None):
        self.rom_path = rom_path
        self.save_state_path = save_state_path
        self.running = True
        self.frame = 0
        self._start_sidecar()
        self._draw("GameBoy Sidecar", "ROM: " + str(rom_path))
        return True

    def stop(self):
        self._send("stop")
        self.running = False
        return None

    def run(self, button=-1):
        if not self.running:
            return False
        self.frame += 1
        if button is not None and int(button) >= 0:
            self._send("button " + str(int(button)))
        if not self._copy_frame():
            if self.frame % 6 == 0:
                self._draw("GameBoy Sidecar", "Input: {}".format(button))
        return True

    def _build_sidecar(self):
        binary = sim_runtime.root + "/sim_mp/native/sim_frame_sidecar"
        if not sim_runtime.build_native("frame-sidecar"):
            print("[sim:gameboy] could not build frame sidecar")
            return ""
        return binary if self._file_exists(binary) else ""

    def _file_exists(self, path):
        try:
            os.stat(path)
            return True
        except OSError:
            return False

    def _start_sidecar(self):
        binary = self._build_sidecar()
        if not binary:
            return False
        sim_runtime.mkdir_p(sim_runtime.sd_root + "/sim_sidecars")
        self._frame_path = sim_runtime.sd_root + "/sim_sidecars/gameboy.rgb565"
        self._cmd_path = sim_runtime.sd_root + "/sim_sidecars/gameboy.cmd"
        self._status_path = sim_runtime.sd_root + "/sim_sidecars/gameboy.status"
        for path in (self._cmd_path, self._status_path, self._frame_path):
            try:
                os.remove(path)
            except OSError:
                pass
        cmd = _quote(binary) + " gameboy " + _quote(self._frame_path) + " " + _quote(self._cmd_path) + " " + _quote(self._status_path) + " >/tmp/picoware-sim-gameboy.log 2>&1 &"
        os.system(cmd)
        return True

    def _send(self, text):
        if not self._cmd_path:
            return
        try:
            with open(self._cmd_path, "w") as handle:
                handle.write(text + "\n")
        except OSError:
            pass

    def _copy_frame(self):
        lcd = getattr(sim_runtime, "_lcd", None)
        if lcd is None or not self._frame_path:
            return False
        try:
            with open(self._frame_path, "rb") as handle:
                data = handle.read()
            if len(data) != len(lcd._buffer):
                return False
            lcd._buffer[:] = data
            lcd.swap()
            return True
        except OSError:
            return False

    def _draw(self, title, subtitle):
        lcd = getattr(sim_runtime, "_lcd", None)
        if lcd is None:
            return
        lcd._clear(0)
        lcd._rectangle(24, 16, 272, 240, 0x07E0)
        lcd._text(42, 36, title, 0xFFFF, 1)
        lcd._text(42, 58, subtitle[:32], 0xFFFF, 1)
        lcd._text(42, 88, "Native sidecar frame bridge", 0xFFE0, 1)
        lcd._text(42, 108, "Use BACK to exit", 0xFFE0, 1)
        lcd.swap()
