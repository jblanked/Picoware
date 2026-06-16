import sim_runtime
import os


def _quote(path):
    return "'" + str(path).replace("'", "'\"'\"'") + "'"


class Ghouls:
    def __init__(self, username="", password="", sound_enabled=True):
        self.username = username
        self.password = password
        self.sound_enabled = sound_enabled
        self.is_active = True
        self.frame = 0
        self.last_input = -1
        self._frame_path = ""
        self._cmd_path = ""
        self._status_path = ""
        self._start_sidecar()
        self._draw("Ghouls Simulator")

    def start(self, *args, **kwargs):
        self.is_active = True
        self._start_sidecar()
        self._draw("Ghouls Simulator")
        return True

    def stop(self):
        self._send("stop")
        self.is_active = False
        return True

    def update_input(self, button):
        self.last_input = button
        if button is not None and int(button) >= 0:
            self._send("button " + str(int(button)))
        if button in (0xB1, 8, 27):
            self.is_active = False
        return True

    def update_draw(self):
        if not self.is_active:
            return False
        self.frame += 1
        if not self._copy_frame() and (self.frame == 1 or self.frame % 12 == 0):
            self._draw("Ghouls Simulator")
        return True

    def _build_sidecar(self):
        binary = sim_runtime.root + "/sim_mp/native/sim_frame_sidecar"
        if not sim_runtime.build_native("frame-sidecar"):
            print("[sim:ghouls] could not build frame sidecar")
            return ""
        return binary if self._file_exists(binary) else ""

    def _file_exists(self, path):
        try:
            os.stat(path)
            return True
        except OSError:
            return False

    def _start_sidecar(self):
        if self._frame_path:
            return True
        binary = self._build_sidecar()
        if not binary:
            return False
        sim_runtime.mkdir_p(sim_runtime.sd_root + "/sim_sidecars")
        self._frame_path = sim_runtime.sd_root + "/sim_sidecars/ghouls.rgb565"
        self._cmd_path = sim_runtime.sd_root + "/sim_sidecars/ghouls.cmd"
        self._status_path = sim_runtime.sd_root + "/sim_sidecars/ghouls.status"
        for path in (self._cmd_path, self._status_path, self._frame_path):
            try:
                os.remove(path)
            except OSError:
                pass
        cmd = _quote(binary) + " ghouls " + _quote(self._frame_path) + " " + _quote(self._cmd_path) + " " + _quote(self._status_path) + " >/tmp/picoware-sim-ghouls.log 2>&1 &"
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

    def _draw(self, title):
        lcd = sim_runtime._lcd
        if lcd is None:
            return
        width = getattr(lcd, "width", 320)
        height = getattr(lcd, "height", 320)
        bg = 0x0841
        fg = 0xFFFF
        accent = 0xF800
        try:
            lcd._clear(bg)
            lcd._rectangle(12, 12, width - 24, height - 24, fg)
            lcd._text(24, 28, title, fg)
            lcd._text(24, 52, "Native sidecar frame bridge", fg)
            lcd._text(24, 76, "User: " + str(self.username or "guest"), fg)
            lcd._text(24, 100, "Frame: " + str(self.frame), fg)
            lcd._text(24, height - 36, "Back exits", accent)
            lcd.swap()
        except Exception:
            pass
