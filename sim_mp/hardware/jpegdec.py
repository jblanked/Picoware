import sim_runtime
import os


class JPEGDecoder:
    def __init__(self):
        self._opened = False
        self._data = b""
        self._info = (True, 160, 120)
        self._split_running = False
        self._split_offset = (0, 0)
        self._split_data = None
        self._split_next = 0
        self._split_pending = None
        self._split_buffer_size = 0
        self._split_option = 0

    def _read_path(self, path):
        """Read raw bytes from a VFS path or host path."""
        try:
            import sd_mp

            return sd_mp.read(path)
        except Exception:
            try:
                with open(path, "rb") as handle:
                    return handle.read()
            except Exception:
                return b""

    def _detect_size(self, data):
        """Parse JPEG header for width and height."""
        i = 0
        size = len(data)
        while i + 9 < size:
            if data[i] == 0xFF and data[i + 1] in (0xC0, 0xC1, 0xC2):
                h = (data[i + 5] << 8) | data[i + 6]
                w = (data[i + 7] << 8) | data[i + 8]
                return (True, w, h)
            i += 1
        return (True, 160, 120)

    def open_file(self, path):
        """Load a JPEG from the given path."""
        data = self._read_path(path)
        if not data:
            return False
        self._data = data
        self._info = self._detect_size(data)
        self._opened = True
        return True

    def open_RAM(self, data):
        """Load JPEG data from a bytes buffer."""
        self._data = bytes(data)
        self._info = self._detect_size(self._data)
        self._opened = True
        return True

    def getinfo(self, data=None):
        """Return (ok, width, height) for the loaded or given JPEG."""
        if data is not None:
            return self._detect_size(bytes(data))
        return self._info

    def _draw_placeholder(self, x, y, w=None, h=None):
        """Draw a checkerboard placeholder when JPEG decode fails."""
        lcd = getattr(sim_runtime, "_lcd", None)
        if lcd is None:
            return True
        if w is None:
            w = min(120, self._info[1])
        if h is None:
            h = min(90, self._info[2])
        x = int(x)
        y = int(y)
        w = max(16, min(220, int(w)))
        h = max(16, min(180, int(h)))
        for yy in range(h):
            for xx in range(w):
                c = 0x7BEF if ((xx // 8) + (yy // 8)) & 1 else 0x39E7
                lcd._set_pixel(x + xx, y + yy, c)
        lcd._rectangle(x, y, w - 1, h - 1, 0xFFFF)
        lcd._text(x + 4, y + 4, "JPEG", 0xFFFF, 1)
        lcd.swap()
        return True

    def _quote(self, value):
        """Shell-quote a value for os.system."""
        return "'" + str(value).replace("'", "'\"'\"'") + "'"

    def _draw_jpeg_bytes(self, data, x, y, option=0):
        """Decode JPEG bytes via djpeg and blit to LCD."""
        lcd = getattr(sim_runtime, "_lcd", None)
        if lcd is None:
            return True
        if not data:
            return self._draw_placeholder(x, y)
        token = str(id(data))
        in_path = "/tmp/picoware-jpegdec-" + token + ".jpg"
        out_path = "/tmp/picoware-jpegdec-" + token + ".bmp"
        try:
            with open(in_path, "wb") as handle:
                handle.write(data)
            scale = int(option) if option else 1
            if scale not in (1, 2, 4, 8):
                scale = 1
            cmd = "djpeg -bmp -scale 1/{} -outfile {} {}".format(
                scale, self._quote(out_path), self._quote(in_path)
            )
            rc = os.system(cmd)
            if rc != 0:
                return self._draw_placeholder(x, y)
            ok = lcd._bmp(int(x), int(y), out_path)
            lcd.swap()
            return ok
        except Exception as e:
            print("[sim:jpeg] decode failed:", e)
            return self._draw_placeholder(x, y)
        finally:
            try:
                os.remove(in_path)
            except OSError:
                pass
            try:
                os.remove(out_path)
            except OSError:
                pass

    def decode(self, x, y, flags=0):
        """Decode the loaded JPEG at screen position (x, y)."""
        return self._draw_jpeg_bytes(self._data, x, y, flags)

    def decode_split(self, fsize, buf, offset, callback=None, option=0):
        """Begin progressive JPEG decode from a partial buffer."""
        self._opened = True
        self._split_running = True
        self._split_offset = offset or (0, 0)
        self._split_buffer_size = len(buf)
        self._split_next = min(int(fsize), len(buf))
        self._split_pending = None
        self._split_option = option
        self._split_data = bytearray(int(fsize))
        self._split_data[: len(buf)] = buf
        self._info = self._detect_size(bytes(buf))
        return (True, self._info[1], self._info[2])

    def decode_split_buffer(self, index, position, buf):
        """Feed a chunk into the progressive JPEG decoder."""
        if self._split_data is not None:
            start = int(position)
            end = min(len(self._split_data), start + len(buf))
            if start < end:
                self._split_data[start:end] = buf[: end - start]
                self._split_next = max(self._split_next, end)
            if self._split_pending == start:
                self._split_pending = None
        return True

    def decode_split_wait(self):
        """Poll the progressive decoder; returns (state, offset, size)."""
        if self._split_running:
            if self._split_data is not None and self._split_next < len(self._split_data):
                if self._split_pending is None:
                    self._split_pending = self._split_next
                return (
                    0,
                    self._split_pending,
                    min(self._split_buffer_size, len(self._split_data) - self._split_pending),
                )
            self._draw_jpeg_bytes(
                bytes(self._split_data) if self._split_data is not None else self._data,
                self._split_offset[0],
                self._split_offset[1],
                self._split_option,
            )
            self._split_running = False
            self._split_data = None
            return (1, -1, 0)
        return (1, -1, 0)

    def decode_core_wait(self, timeout=0):
        """Finalize progressive decode (no-op in simulator)."""
        self._split_running = False
        self._split_data = None
        return True
