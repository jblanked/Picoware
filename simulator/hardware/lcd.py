import sim_runtime
import sim_font
import ustruct


def _rgb565_to_rgb(color):
    color = int(color) & 0xFFFF
    r = ((color >> 11) & 31) * 255 // 31
    g = ((color >> 5) & 63) * 255 // 63
    b = (color & 31) * 255 // 31
    return r, g, b


class LCD:
    width = 320
    height = 320

    FONT_DEFAULT = 1
    FONT_XTRA_SMALL = 0
    FONT_SMALL = 1
    FONT_MEDIUM = 2
    FONT_LARGE = 3
    FONT_XTRA_LARGE = 4

    MODE_HEAP = 0
    MODE_PSRAM = 1

    def __init__(self, scale_x=1.0, scale_y=1.0, scale_position=False):
        self._scale_x_factor = scale_x
        self._scale_y_factor = scale_y
        self.scale_position = scale_position
        self._mode = self.MODE_HEAP
        self._buffer = bytearray(self.width * self.height * 2)
        self._sdl = None
        self._window = 0
        self._renderer = 0
        self._texture = 0
        self._event = bytearray(64)
        self._use_sdl = False
        if not sim_runtime.headless:
            self._init_sdl()
        sim_runtime.set_lcd(self)

    def _init_sdl(self):
        try:
            import ffi

            lib = ffi.open("libSDL2-2.0.so.0")
            self._sdl = lib
            self._SDL_Init = lib.func("i", "SDL_Init", "i")
            self._SDL_CreateWindow = lib.func("p", "SDL_CreateWindow", "siiiii")
            self._SDL_CreateRenderer = lib.func("p", "SDL_CreateRenderer", "pii")
            self._SDL_CreateTexture = lib.func("p", "SDL_CreateTexture", "piiii")
            self._SDL_UpdateTexture = lib.func("i", "SDL_UpdateTexture", "pppi")
            self._SDL_RenderClear = lib.func("i", "SDL_RenderClear", "p")
            self._SDL_RenderCopy = lib.func("i", "SDL_RenderCopy", "pppp")
            self._SDL_RenderPresent = lib.func("v", "SDL_RenderPresent", "p")
            self._SDL_SetRenderDrawColor = lib.func("i", "SDL_SetRenderDrawColor", "piiii")
            self._SDL_PollEvent = lib.func("i", "SDL_PollEvent", "p")
            self._SDL_Quit = lib.func("v", "SDL_Quit", "")
            if self._SDL_Init(32) != 0:
                print("SDL unavailable, using headless LCD")
                return
            s = sim_runtime.scale
            self._window = self._SDL_CreateWindow("Picoware MicroPython Simulator", 100, 100, self.width * s, self.height * s, 0)
            if not self._window:
                print("SDL window unavailable, using headless LCD")
                return
            self._renderer = self._SDL_CreateRenderer(self._window, -1, 0)
            if not self._renderer:
                print("SDL renderer unavailable, using headless LCD")
                return
            # SDL_PIXELFORMAT_RGB565 = 0x15151002, SDL_TEXTUREACCESS_STREAMING = 1
            self._texture = self._SDL_CreateTexture(self._renderer, 0x15151002, 1, self.width, self.height)
            if not self._texture:
                print("SDL texture unavailable, using headless LCD")
                return
            self._use_sdl = True
        except Exception as e:
            print("SDL unavailable, using headless LCD:", e)

    def _offset(self, x, y):
        return (int(y) * self.width + int(x)) * 2

    def _set_pixel(self, x, y, color):
        x = int(x)
        y = int(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            off = self._offset(x, y)
            color = int(color) & 0xFFFF
            self._buffer[off] = color & 0xFF
            self._buffer[off + 1] = (color >> 8) & 0xFF

    def _clear(self, color=0):
        color = int(color) & 0xFFFF
        lo = color & 0xFF
        hi = (color >> 8) & 0xFF
        self._buffer[:] = bytes((lo, hi)) * (self.width * self.height)

    def _pixel(self, x, y, color):
        self._set_pixel(x, y, color)

    def _line(self, x1, y1, x2, y2, color):
        x1 = int(x1)
        y1 = int(y1)
        x2 = int(x2)
        y2 = int(y2)
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        x = x1
        y = y1
        while True:
            self._set_pixel(x, y, color)
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def _rectangle(self, x, y, w, h, color):
        self._line(x, y, x + w, y, color)
        self._line(x, y, x, y + h, color)
        self._line(x + w, y, x + w, y + h, color)
        self._line(x, y + h, x + w, y + h, color)

    def _fill_rectangle(self, x, y, w, h, color):
        x = int(x)
        y = int(y)
        w = int(w)
        h = int(h)
        if w <= 0 or h <= 0:
            return
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        if x0 >= x1 or y0 >= y1:
            return
        color = int(color) & 0xFFFF
        lo = color & 0xFF
        hi = (color >> 8) & 0xFF
        row = bytes((lo, hi)) * (x1 - x0)
        row_bytes = len(row)
        for yy in range(y0, y1):
            off = self._offset(x0, yy)
            self._buffer[off : off + row_bytes] = row

    def _circle(self, x, y, radius, color):
        x = int(x)
        y = int(y)
        radius = int(radius)
        xx = radius
        yy = 0
        err = 0
        while xx >= yy:
            pts = ((x + xx, y + yy), (x + yy, y + xx), (x - yy, y + xx), (x - xx, y + yy), (x - xx, y - yy), (x - yy, y - xx), (x + yy, y - xx), (x + xx, y - yy))
            for p in pts:
                self._set_pixel(p[0], p[1], color)
            yy += 1
            if err <= 0:
                err += 2 * yy + 1
            if err > 0:
                xx -= 1
                err -= 2 * xx + 1

    def _fill_circle(self, x, y, radius, color):
        x = int(x)
        y = int(y)
        radius = int(radius)
        for yy in range(y - radius, y + radius + 1):
            for xx in range(x - radius, x + radius + 1):
                if (xx - x) * (xx - x) + (yy - y) * (yy - y) <= radius * radius:
                    self._set_pixel(xx, yy, color)

    def _triangle(self, x1, y1, x2, y2, x3, y3, color):
        self._line(x1, y1, x2, y2, color)
        self._line(x2, y2, x3, y3, color)
        self._line(x3, y3, x1, y1, color)

    def _fill_triangle(self, x1, y1, x2, y2, x3, y3, color):
        self._triangle(x1, y1, x2, y2, x3, y3, color)

    def _fill_round_rectangle(self, x, y, w, h, radius, color):
        self._fill_rectangle(x, y, w, h, color)

    def _font_metrics(self, font_size):
        if font_size == 0:
            return 5, 8, 1
        if font_size == 2:
            return 11, 16, 0
        if font_size == 3:
            return 14, 20, 0
        if font_size == 4:
            return 17, 24, 0
        return 7, 12, 0

    def _draw_glyph(self, x, y, ch, color, width, height):
        rows = sim_font.glyph_rows(ch)
        for dst_y in range(height):
            src_y = dst_y * sim_font.HEIGHT // height
            row = rows[src_y]
            for dst_x in range(width):
                src_x = dst_x * sim_font.WIDTH // width
                if row & (0x80 >> src_x):
                    self._set_pixel(x + dst_x, y + dst_y, color)

    def _text(self, x, y, text, color, font_size=None):
        try:
            sim_runtime.note_text(text)
        except Exception:
            pass
        w, h, spacing = self._font_metrics(font_size)
        xx = int(x)
        yy = int(y)
        for ch in str(text):
            if ch == "\n":
                xx = int(x)
                yy += h
                continue
            if ch != " ":
                self._draw_glyph(xx, yy, ch, color, w, h)
            xx += w + spacing

    def _char(self, x, y, char, color, font_size=None):
        self._text(x, y, char, color, font_size)

    def _bytearray(self, x, y, w, h, data):
        idx = 0
        for yy in range(int(h)):
            for xx in range(int(w)):
                if idx >= len(data):
                    return
                value = data[idx]
                if value:
                    self._set_pixel(int(x) + xx, int(y) + yy, self._rgb332_to_565(value))
                idx += 1

    def _rgb332_to_565(self, value):
        value = int(value) & 0xFF
        r3 = (value >> 5) & 0x07
        g3 = (value >> 2) & 0x07
        b2 = value & 0x03
        r8 = (r3 * 255) // 7
        g8 = (g3 * 255) // 7
        b8 = (b2 * 255) // 3
        return self._rgb_to_565(r8, g8, b8)

    def _bmp(self, x, y, path):
        try:
            data = self._read_file(path)
            if len(data) < 54 or data[0:2] != b"BM":
                return False
            off = self._u32(data, 10)
            dib = self._u32(data, 14)
            if dib < 40:
                return False
            width = self._i32(data, 18)
            height_raw = self._i32(data, 22)
            planes = self._u16(data, 26)
            bpp = self._u16(data, 28)
            compression = self._u32(data, 30)
            colors_used = self._u32(data, 46) if len(data) >= 50 else 0
            if planes != 1 or compression not in (0, 3):
                return False
            if width <= 0 or height_raw == 0:
                return False
            top_down = height_raw < 0
            height = -height_raw if top_down else height_raw
            palette = []
            if bpp <= 8:
                count = colors_used if colors_used else (1 << bpp)
                pos = 14 + dib
                for _ in range(count):
                    if pos + 4 > len(data):
                        break
                    b = data[pos]
                    g = data[pos + 1]
                    r = data[pos + 2]
                    palette.append(self._rgb_to_565(r, g, b))
                    pos += 4
            row_bits = width * bpp
            row_bytes = ((row_bits + 31) // 32) * 4
            x = int(x)
            y = int(y)
            for row in range(height):
                src_y = row if top_down else height - 1 - row
                row_start = off + src_y * row_bytes
                if row_start >= len(data):
                    break
                for col in range(width):
                    color = self._bmp_pixel(data, row_start, col, bpp, palette)
                    if color is not None:
                        self._set_pixel(x + col, y + row, color)
            return True
        except Exception as e:
            print("[sim:lcd] BMP decode failed:", e)
            return False

    def _psram(self, x, y, w, h, addr):
        try:
            import picoware_psram

            data = picoware_psram.read(addr, int(w) * int(h) * 2)
            idx = 0
            for yy in range(int(h)):
                dst = self._offset(int(x), int(y) + yy)
                row_len = int(w) * 2
                self._buffer[dst : dst + row_len] = data[idx : idx + row_len]
                idx += row_len
            return True
        except Exception as e:
            print("[sim:lcd] PSRAM render failed:", e)
            return False

    def _read_file(self, path):
        try:
            import sim_runtime

            host = sim_runtime.host_path(path)
            try:
                with open(host, "rb") as handle:
                    return handle.read()
            except OSError:
                pass
        except Exception:
            pass
        with open(path, "rb") as handle:
            return handle.read()

    def _u16(self, data, offset):
        return int(data[offset]) | (int(data[offset + 1]) << 8)

    def _u32(self, data, offset):
        return self._u16(data, offset) | (self._u16(data, offset + 2) << 16)

    def _i32(self, data, offset):
        value = self._u32(data, offset)
        if value & 0x80000000:
            value -= 0x100000000
        return value

    def _rgb_to_565(self, r, g, b):
        return ((int(r) & 0xF8) << 8) | ((int(g) & 0xFC) << 3) | (int(b) >> 3)

    def _bmp_pixel(self, data, row_start, col, bpp, palette):
        if bpp == 24:
            pos = row_start + col * 3
            if pos + 2 >= len(data):
                return None
            return self._rgb_to_565(data[pos + 2], data[pos + 1], data[pos])
        if bpp == 32:
            pos = row_start + col * 4
            if pos + 2 >= len(data):
                return None
            return self._rgb_to_565(data[pos + 2], data[pos + 1], data[pos])
        if bpp == 16:
            pos = row_start + col * 2
            if pos + 1 >= len(data):
                return None
            return self._u16(data, pos)
        if bpp == 8:
            pos = row_start + col
            if pos >= len(data):
                return None
            idx = data[pos]
            return palette[idx] if idx < len(palette) else 0
        if bpp == 4:
            pos = row_start + col // 2
            if pos >= len(data):
                return None
            value = data[pos]
            idx = (value >> 4) if col % 2 == 0 else (value & 0x0F)
            return palette[idx] if idx < len(palette) else 0
        if bpp == 1:
            pos = row_start + col // 8
            if pos >= len(data):
                return None
            idx = (data[pos] >> (7 - (col % 8))) & 1
            return palette[idx] if idx < len(palette) else (0xFFFF if idx else 0)
        return None

    def set_mode(self, mode):
        self._mode = mode

    def set_scaling(self, scale_x, scale_y, scale_position=False):
        self._scale_x_factor = scale_x
        self._scale_y_factor = scale_y
        self.scale_position = scale_position

    def scale_x(self, value):
        return int(value * self._scale_x_factor)

    def scale_y(self, value):
        return int(value * self._scale_y_factor)

    def scale(self, x, y):
        return self.scale_x(x), self.scale_y(y)

    def scale_vector(self, position):
        from picoware.system.vector import Vector

        return Vector(self.scale_x(position.x), self.scale_y(position.y), self.scale_y(position.z))

    def swap(self):
        self.poll_events()
        if sim_runtime.viewer and sim_runtime.viewer_frame_path:
            self._write_raw_frame(sim_runtime.viewer_frame_path)
        if self._use_sdl:
            self._SDL_UpdateTexture(self._texture, 0, self._buffer, self.width * 2)
            self._SDL_RenderClear(self._renderer)
            self._SDL_RenderCopy(self._renderer, self._texture, 0, 0)
            self._SDL_RenderPresent(self._renderer)
        sim_runtime.frame_swapped()

    def _write_raw_frame(self, file_path):
        tmp_path = file_path + ".tmp"
        with open(tmp_path, "wb") as handle:
            handle.write(self._buffer)
        try:
            import os

            os.rename(tmp_path, file_path)
        except Exception:
            pass

    def poll_events(self):
        if not self._use_sdl:
            return
        import ustruct
        while self._SDL_PollEvent(self._event):
            event_type = ustruct.unpack_from("I", self._event, 0)[0]
            if event_type == 0x100:
                raise SystemExit
            if event_type == 0x300:
                sym = ustruct.unpack_from("i", self._event, 20)[0]
                key = self._map_sdl_key(sym)
                if key is not None:
                    sim_runtime.push_key(key)

    def _map_sdl_key(self, sym):
        if sym == 1073741906:
            return 0xB5
        if sym == 1073741905:
            return 0xB6
        if sym == 1073741904:
            return 0xB4
        if sym == 1073741903:
            return 0xB7
        if sym == 27:
            return 0xB1
        if sym == 8:
            return 8
        if sym in (13, 10):
            return 13
        if sym == 9:
            return 9
        if sym == 1073741898:
            return 0xD2
        if sym == 127:
            return 0xD4
        if sym == 1073741901:
            return 0xD5
        if 1073741882 <= sym <= 1073741891:
            return 0x81 + (sym - 1073741882)
        if 0 <= sym < 128:
            return sym
        return None

    def screenshot(self, file_path):
        row_bytes = self.width * 3
        padding = (4 - row_bytes % 4) % 4
        pixel_size = (row_bytes + padding) * self.height
        file_size = 54 + pixel_size
        with open(file_path, "wb") as handle:
            handle.write(b"BM")
            handle.write(ustruct.pack("<IHHI", file_size, 0, 0, 54))
            handle.write(ustruct.pack("<IIIHHIIIIII", 40, self.width, self.height, 1, 24, 0, pixel_size, 2835, 2835, 0, 0))
            for y in range(self.height - 1, -1, -1):
                for x in range(self.width):
                    off = self._offset(x, y)
                    color = self._buffer[off] | (self._buffer[off + 1] << 8)
                    r, g, b = _rgb565_to_rgb(color)
                    handle.write(bytes((b, g, r)))
                if padding:
                    handle.write(b"\x00" * padding)
        return True
