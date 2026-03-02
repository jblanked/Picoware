"""
CCTV/MJPEG App for Picoware
Copyright (c) 2026 JBlanked
GPL-3.0 License
https://www.github.com/jblanked/Picoware
Last Updated: 2026-03-01

Users need a word list of CCTV stream URLs in "picoware/cctv/list.txt" on the device's storage, with one URL per line.
The app connects to each URL in turn and displays the MJPEG stream.
Use the UP/DOWN or LEFT/RIGHT buttons to switch between cameras, and BACK to exit.

In my testing I saw 113kb frames so its possible on the Pico2W and Pimoroni 2W only... although so endpoints may have smaller frames
"""

from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
)
from picoware.system.vector import Vector
from gc import mem_alloc, mem_free

tv_list = []

_tv_index = 0
_streaming = False
_cctv = None
_psram = None
_frame_addr = 0
MAX_FRAME_SIZE = 320000


class PSRAMReader:
    """File-like reader backed by a PSRAM region.

    Provides readinto() and seek() so the JPEG split-decoder can stream
    directly from PSRAM without copying the full frame to heap.
    """

    def __init__(self, psram, addr: int, size: int):
        self._psram = psram
        self._addr = addr
        self._size = size
        self._pos = 0

    def seek(self, pos: int, whence: int = 0) -> int:
        if whence == 0:
            self._pos = pos
        elif whence == 1:
            self._pos += pos
        elif whence == 2:
            self._pos = self._size + pos
        return self._pos

    def readinto(self, buf) -> int:
        avail = self._size - self._pos
        if avail <= 0:
            return 0
        n = min(len(buf), avail)
        data = self._psram.read(self._addr + self._pos, n)
        buf[:n] = data
        self._pos += n
        return n

    def read(self, n: int = -1) -> bytes:
        avail = self._size - self._pos
        if avail <= 0:
            return b""
        if n < 0:
            n = avail
        n = min(n, avail)
        data = self._psram.read(self._addr + self._pos, n)
        self._pos += n
        return data


class CCTV:
    """Class to manage MJPEG socket connection and frame retrieval from a CCTV stream."""

    def __init__(self):
        self._sock = None
        self._boundary = b"--frame"
        self._error_msg = ""
        self._is_running = False

    def __del__(self):
        self.close_socket()
        self._sock = None

    @property
    def boundary(self) -> bytes:
        """Boundary string used to separate MJPEG frames. Default is b"--frame"."""
        return self._boundary

    @property
    def is_connected(self) -> bool:
        """True if the socket is currently connected."""
        return self._sock is not None and self._is_running

    @property
    def is_running(self) -> bool:
        """True if the background thread is running."""
        return self._is_running

    @is_running.setter
    def is_running(self, value: bool):
        """Set the running state of the background thread."""
        self._is_running = value

    @property
    def error_msg(self) -> str:
        """Error message from the last operation, if any."""
        return self._error_msg

    @property
    def socket(self):
        """The underlying socket object, or None if not connected."""
        return self._sock

    def close_socket(self):
        """Close the socket if it's open"""
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def connect(self, url: str) -> bool:
        """Open the MJPEG socket and consume HTTP response headers."""
        import usocket as socket

        try:
            self._is_running = True
            host, port, path = self._decode_url(url)
            path += "?width=320&height=240"
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(10)
            addr = socket.getaddrinfo(host, port)[0][-1]
            self._sock.connect(addr)

            request = (
                "GET {} HTTP/1.0\r\n" "Host: {}:{}\r\n" "Accept: */*\r\n\r\n"
            ).format(path, host, port)
            self._sock.send(request.encode())

            # Read HTTP response headers; extract boundary if present
            found_boundary = b""
            while True:
                if not self._is_running:
                    self.close_socket()
                    return False
                line = self._readline()
                if line is None or line == b"":
                    break  # None = error, b"" = blank line (end of headers)
                lower = line.lower()
                if b"boundary=" in lower:
                    idx = lower.find(b"boundary=") + 9
                    val = line[idx:].strip().strip(b'"').strip(b"'")
                    if val:
                        found_boundary = val

            if found_boundary:
                if not found_boundary.startswith(b"--"):
                    found_boundary = b"--" + found_boundary
                self._boundary = found_boundary
            return True

        except Exception as e:
            self._is_running = False
            self._error_msg = str(e)
            self.close_socket()
            return False

    def next_frame(self):
        """
        Read the next JPEG frame from the open MJPEG socket.

        Server format (per frame):
            --frame\\r\\n
            Content-Type: image/jpeg\\r\\n
            Content-Length: <n>\\r\\n
            \\r\\n
            <JPEG bytes>\\r\\n
        """

        if self._sock is None:
            return None

        try:
            # Consume lines until a boundary marker
            for _ in range(64):  # safety cap to avoid infinite loop
                if not self._is_running:
                    return None
                line = self._readline()
                if line is None:
                    return None  # connection closed / error
                if line.startswith(b"--"):
                    break
            else:
                return None  # never found boundary

            # Read part headers
            content_length = 0
            for _ in range(16):
                if not self._is_running:
                    return None
                line = self._readline()
                if line is None:
                    return None
                if line == b"":
                    break  # blank line = body follows
                if line.lower().startswith(b"content-length:"):
                    try:
                        content_length = int(line.split(b":", 1)[1].strip())
                    except ValueError:
                        pass

            # Read JPEG payload
            if content_length > 0:
                data = self._read_exactly_to_psram(
                    content_length, _psram, _frame_addr, MAX_FRAME_SIZE
                )
            else:
                # Fallback: accumulate until JPEG EOI marker FF D9
                buf = bytearray()
                while len(buf) < 65536:  # 64 KB safety cap
                    if not self._is_running:
                        return None
                    b = self._sock.read(1)
                    if not b:
                        break
                    buf += b
                    if len(buf) >= 2 and buf[-2] == 0xFF and buf[-1] == 0xD9:
                        break
                data = bytes(buf) if buf else None

            return data if data and len(data) > 4 else None

        except OSError:
            return None

    def _decode_url(self, url) -> (str, int, str):
        """Parse a URL into (host, port, path). Port defaults to 80 if not specified."""
        import ure

        pattern = ure.compile(r"^https?://([^:/]+)(?::(\d+))?(.*)$")
        match = pattern.match(url)
        if match:
            host = match.group(1)
            port = int(match.group(2)) if match.group(2) else 80
            path = match.group(3) if match.group(3) else "/"
            return host, port, path
        raise ValueError("Invalid URL format: {}".format(url))

    def _readline(self):
        """Read one CRLF-terminated line (byte-at-a-time). Returns bytes or None on error."""
        line = bytearray()
        try:
            while True:
                if not self._is_running:
                    return None
                ch = self._sock.read(1)
                if not ch:
                    return None  # EOF / connection closed
                if ch == b"\n":
                    break
                if ch != b"\r":
                    line += ch
        except OSError:
            return None
        return bytes(line)

    def _read_exactly(self, n):
        """Read exactly *n* bytes. Returns bytes or None on error."""
        buf = bytearray(n)
        view = memoryview(buf)
        received = 0
        try:
            while received < n:
                if not self._is_running:
                    return None
                chunk = self._sock.readinto(view[received:], n - received)
                if not chunk:
                    return None
                received += chunk
        except OSError:
            return None
        return bytes(buf)

    def _read_exactly_to_psram(
        self, n: int, psram, addr: int, chunk_size: int = 2048
    ) -> int:
        """Stream exactly *n* bytes directly into PSRAM. Returns bytes written or -1 on error."""
        chunk_buf = bytearray(chunk_size)
        view = memoryview(chunk_buf)
        received = 0
        try:
            while received < n:
                if not self._is_running:
                    return -1
                to_read = min(chunk_size, n - received)
                got = self._sock.readinto(view[:to_read])
                if not got:
                    return -1
                psram.write(addr + received, view[:got])
                received += got
        except OSError:
            return -1
        return received

    def next_frame_to_psram(
        self, psram, addr: int, max_size: int = MAX_FRAME_SIZE
    ) -> int:
        """Read the next JPEG frame directly into PSRAM.

        Streams the payload chunk-by-chunk so the full frame is never on heap.
        Returns the number of bytes written, or -1 on failure.
        """
        if self._sock is None:
            return -1

        try:
            # Find boundary marker
            for _ in range(64):
                if not self._is_running:
                    return -1
                line = self._readline()
                if line is None:
                    return -1
                if line.startswith(b"--"):
                    break
            else:
                return -1

            # Read part headers
            content_length = 0
            for _ in range(16):
                if not self._is_running:
                    return -1
                line = self._readline()
                if line is None:
                    return -1
                if line == b"":
                    break
                if line.lower().startswith(b"content-length:"):
                    try:
                        content_length = int(line.split(b":", 1)[1].strip())
                    except ValueError:
                        pass

            if content_length > 0 and content_length <= max_size:
                return self._read_exactly_to_psram(content_length, psram, addr)

            # Fallback: stream byte-by-byte watching for JPEG EOI (FF D9)
            chunk = bytearray(256)
            cpos = 0
            written = 0
            prev_byte = 0
            try:
                while written + cpos < max_size:
                    if not self._is_running:
                        return -1
                    b = self._sock.read(1)
                    if not b:
                        break
                    byte_val = b[0]
                    found_eoi = prev_byte == 0xFF and byte_val == 0xD9
                    chunk[cpos] = byte_val
                    cpos += 1
                    if cpos >= 256 or found_eoi:
                        psram.write(addr + written, memoryview(chunk)[:cpos])
                        written += cpos
                        cpos = 0
                        if found_eoi:
                            break
                    prev_byte = byte_val
                if cpos > 0:
                    psram.write(addr + written, memoryview(chunk)[:cpos])
                    written += cpos
            except OSError:
                return -1
            return written if written > 4 else -1

        except OSError:
            return -1


class CCTVAsync:
    """Async CCTV: connects in a background thread, reads frames from the main thread."""

    def __init__(self, thread_manager=None):
        self._cctv = CCTV()
        self._thread_manager = thread_manager
        self._running = False
        self._connected = False
        self._connect_error = ""
        self._frame_count = 0

    @property
    def boundary(self) -> bytes:
        """Boundary string used to separate MJPEG frames. Default is b"--frame"."""
        return self._cctv.boundary

    @property
    def error_msg(self) -> str:
        """Error message from the last operation, if any."""
        return self._connect_error if self._connect_error else self._cctv.error_msg

    @property
    def is_connected(self) -> bool:
        """True if the socket is currently connected."""
        return self._connected

    @property
    def frame_count(self) -> int:
        """Number of frames successfully read so far."""
        return self._frame_count

    def close(self):
        """Close connection and reset state."""
        self._running = False
        self._connected = False
        self._cctv.is_running = False
        self._cctv.close_socket()
        self._frame_count = 0
        self._connect_error = ""

    def connect(self, url):
        """Connect to the MJPEG stream in a background thread.

        The thread performs only the blocking connection handshake.
        Once connected, call next_frame() from the main loop to read frames.
        """
        self._running = True
        self._connected = False
        self._connect_error = ""
        self._frame_count = 0

        def _connect_task():
            self._cctv.is_running = True
            if not self._running:
                return
            if self._cctv.connect(url):
                if self._running:
                    try:
                        self._cctv._sock.settimeout(10)
                    except Exception:
                        pass
                    self._connected = True
                else:
                    self._cctv.close_socket()
            else:
                self._connect_error = self._cctv.error_msg

        if self._thread_manager:
            from picoware.system.thread import ThreadTask

            task = ThreadTask(
                "CCTV",
                function=_connect_task,
                args=(),
            )
            self._thread_manager.add_task(task)
        else:
            import _thread

            _thread.start_new_thread(_connect_task, ())

    def next_frame(self):
        """Read the next JPEG frame (called from the main thread).

        Returns frame bytes, or None if not connected / no data yet.
        """
        if not self._connected or not self._running:
            return None
        frame = self._cctv.next_frame()
        if frame:
            self._frame_count += 1
        return frame

    def next_frame_to_psram(
        self, psram, addr: int, max_size: int = MAX_FRAME_SIZE
    ) -> int:
        """Stream the next JPEG frame directly into PSRAM.

        Returns the number of bytes written, or -1 if not connected / error.
        """
        if not self._connected or not self._running:
            return -1
        size = self._cctv.next_frame_to_psram(psram, addr, max_size)
        if size > 0:
            self._frame_count += 1
        return size


def load_tv_list(storage):
    """Load the list of CCTV URLs from storage."""
    global tv_list

    _textlist = storage.read("picoware/cctv/list.txt")
    if not _textlist:
        return False
    tv_list = _textlist.splitlines()
    return True


def _status(draw, fg, bg, title, *lines):
    """Clear screen and show a status message with optional sub-lines."""
    draw._fill_rectangle(0, 0, draw.width, 80, bg)
    draw._text(5, 5, title, fg)
    for i, line in enumerate(lines):
        draw._text(5, 25 + i * 20, str(line), fg)
    draw.swap()


def start(view_manager):
    """Start the CCTV viewer app."""
    global _streaming, _cctv, _tv_index

    wifi = view_manager.wifi
    if not wifi:
        view_manager.alert("WiFi not available", False)
        return False

    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        view_manager.alert("WiFi not connected...", False)
        connect_to_saved_wifi(view_manager)
        return False

    storage = view_manager.storage
    storage.mkdir("picoware/cctv")

    if not storage.exists("picoware/cctv/list.txt"):
        view_manager.alert(
            "CCTV list not found! Create one in picoware/cctv/list.txt with the URLs of your CCTV cameras separated by newlines.",
            False,
        )
        return False

    if not load_tv_list(storage):
        view_manager.alert(
            "Failed to load CCTV list! Make sure picoware/cctv/list.txt exists and each line contains a valid URL.",
            False,
        )
        return False

    _cctv = CCTVAsync(view_manager.thread_manager)

    _streaming = False
    _tv_index = 0

    # Reserve a PSRAM address region for the frame buffer if the board supports it
    global _psram, _frame_addr
    _psram = None
    _frame_addr = 0
    if view_manager.has_psram:
        try:
            from picoware.system.psram import PSRAM

            _psram = PSRAM()
            _frame_addr = _psram.get_next_free()
        except Exception as e:
            _psram = None
            _frame_addr = 0

    draw = view_manager.draw
    fg = view_manager.foreground_color
    bg = view_manager.background_color

    _status(draw, fg, bg, "CCTV Viewer", "Starting...")

    return True


def run(view_manager):
    """Run the CCTV viewer — called repeatedly by the ViewManager loop."""
    global _streaming, _tv_index

    draw = view_manager.draw
    fg = view_manager.foreground_color
    bg = view_manager.background_color
    inp = view_manager.input_manager

    if inp.button == BUTTON_BACK or not _cctv:
        inp.reset()
        view_manager.back()
        return

    if inp.button in (BUTTON_UP, BUTTON_LEFT):
        inp.reset()
        _tv_index = (_tv_index - 1) % len(tv_list)
        _cctv.close()
        _streaming = False
        draw.erase()
    elif inp.button in (BUTTON_DOWN, BUTTON_RIGHT):
        inp.reset()
        _tv_index = (_tv_index + 1) % len(tv_list)
        _cctv.close()
        _streaming = False
        draw.erase()

    if not _streaming:
        _status(
            draw,
            fg,
            bg,
            "CCTV Viewer",
            "Connecting...",
            tv_list[_tv_index],
        )
        _cctv.connect(tv_list[_tv_index])
        _streaming = True
        return

    if not _cctv.is_connected:
        if _cctv.error_msg:
            err = _cctv.error_msg
            _status(
                draw,
                fg,
                bg,
                "CCTV Viewer",
                "Connection failed:",
                err[:36],
                err[36:72] if len(err) > 36 else "",
                "Retrying...",
                "BACK to exit",
            )
            _cctv.close()
            _streaming = False
        else:
            _status(
                draw,
                fg,
                bg,
                "CCTV Viewer",
                "Connecting...",
                tv_list[_tv_index],
                "BACK to exit",
            )
        return

    if _psram and _frame_addr:
        frame_size = _cctv.next_frame_to_psram(_psram, _frame_addr, MAX_FRAME_SIZE)

        if frame_size <= 0:
            if _cctv.error_msg:
                err = _cctv.error_msg
                _status(
                    draw,
                    fg,
                    bg,
                    "CCTV Viewer",
                    "Stream lost:",
                    err[:36],
                    "BACK to exit",
                )
                _cctv.close()
                _streaming = False
            else:
                _status(
                    draw,
                    fg,
                    bg,
                    "CCTV Viewer",
                    "Waiting for frame...",
                    "Frame #{}".format(_cctv.frame_count + 1),
                    "BACK to exit",
                )
            return

        _status(
            draw,
            fg,
            bg,
            f"CCTV Viewer {mem_alloc() // 1024} KB used",
            "Decoding... (PSRAM)",
            "Frame #{} ({} B)".format(_cctv.frame_count, frame_size),
        )
        try:
            from picoware.gui.jpeg import JPEG

            jpeg = JPEG(screen_width=draw.width, screen_height=draw.height)
            jpeg._init_buffers()
            reader = PSRAMReader(_psram, _frame_addr, frame_size)
            jpeg._decode_split(reader, frame_size, 40, 120)
        except Exception as e:
            _status(
                draw,
                fg,
                bg,
                "CCTV Viewer",
                "Decode failed...{}".format(e),
                "Frame #{}".format(_cctv.frame_count),
                "Size: {} B".format(frame_size),
                tv_list[_tv_index],
                "BACK to exit",
            )
            return
    else:
        # Heap fallback for boards without PSRAM
        frame = _cctv.next_frame()

        if frame is None:
            if _cctv.error_msg:
                err = _cctv.error_msg
                _status(
                    draw,
                    fg,
                    bg,
                    "CCTV Viewer",
                    "Stream lost:",
                    err[:36],
                    "BACK to exit",
                )
                _cctv.close()
                _streaming = False
            else:
                _status(
                    draw,
                    fg,
                    bg,
                    "CCTV Viewer",
                    "Waiting for frame...",
                    "Frame #{}".format(_cctv.frame_count + 1),
                    "BACK to exit",
                )
            return
        _status(
            draw,
            fg,
            bg,
            "CCTV Viewer",
            "Decoding...",
            "Frame #{} ({} B)".format(_cctv.frame_count, len(frame)),
            "Heap free: {} B".format(mem_free()),
        )
        try:
            draw.image_jpeg_buffer(Vector(40, 120), frame)
        except Exception:
            _status(
                draw,
                fg,
                bg,
                "CCTV Viewer",
                "Decode failed...",
                "Frame #{}".format(_cctv.frame_count),
                "Size: {} B".format(len(frame)),
                tv_list[_tv_index],
                "BACK to exit",
            )
            return
    _status(
        draw,
        fg,
        bg,
        f"CCTV Viewer {mem_alloc() // 1024} KB used",
        "Displaying...",
        "Frame #{}".format(_cctv.frame_count),
    )
    draw.swap()


def stop(view_manager):
    """Stop the CCTV viewer and release resources."""
    from gc import collect

    global _cctv, _streaming, _tv_index, tv_list, _psram, _frame_addr

    if _cctv:
        _cctv.close()
        del _cctv
        _cctv = None

    if _psram:
        _psram.collect()
        del _psram
        _psram = None

    _frame_addr = 0

    _streaming = False
    _tv_index = 0
    tv_list = []

    collect()
