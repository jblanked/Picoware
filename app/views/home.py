"""Home view — USB Video Stream Viewer.

Receives raw RGB332/RGB565 framebuffer data over USB CDC serial and
renders it in a customtkinter label via PIL.
"""

import struct
import threading
import time

from PIL import Image
import customtkinter as ctk
import serial
import serial.tools.list_ports

USB_VIDEO_MAGIC = 0x50494356  # "PICV" little-endian
USB_VIDEO_MAGIC_BYTES = struct.pack("<I", USB_VIDEO_MAGIC)
USB_VIDEO_HDR_SIZE = 10  # magic+w+h+fmt+rsvd
USB_VIDEO_FORMAT_RGB332 = 0
USB_VIDEO_FORMAT_RGB565 = 1

_RGB332_TO_RGB888 = bytes(
    v
    for r3 in range(8)
    for g3 in range(8)
    for b2 in range(4)
    for v in (
        ((r3 << 5) | (r3 << 2) | (r3 >> 1)),       # R
        ((g3 << 5) | (g3 << 2) | (g3 >> 1)),       # G
        ((b2 << 6) | (b2 << 4) | (b2 << 2) | b2),  # B
    )
)


def decode_frame(data: bytes, width: int, height: int, fmt: int) -> bytes | None:
    """Decode raw pixel data into RGB888 bytes (width * height * 3).

    Returns ``None`` if *data* is too short for the declared dimensions.
    """
    expected = width * height

    if fmt == USB_VIDEO_FORMAT_RGB332:
        if len(data) < expected:
            return None
        out = bytearray(expected * 3)
        for i in range(expected):
            p = data[i]
            off = p * 3
            out[i * 3] = _RGB332_TO_RGB888[off]
            out[i * 3 + 1] = _RGB332_TO_RGB888[off + 1]
            out[i * 3 + 2] = _RGB332_TO_RGB888[off + 2]
        return bytes(out)

    if fmt == USB_VIDEO_FORMAT_RGB565:
        if len(data) < expected * 2:
            return None
        out = bytearray(expected * 3)
        for i in range(expected):
            p = data[i * 2] | (data[i * 2 + 1] << 8)
            r = ((p >> 11) & 0x1F) * 255 // 31
            g = ((p >> 5) & 0x3F) * 255 // 63
            b = (p & 0x1F) * 255 // 31
            out[i * 3] = r
            out[i * 3 + 1] = g
            out[i * 3 + 2] = b
        return bytes(out)

    return None


def find_picoware_port() -> str | None:
    """Auto-detect a Picoware / RP2040 device by USB VID/PID."""
    for p in serial.tools.list_ports.comports():
        # RP2040 / RP2350 CDC
        if p.vid == 0x2E8A and p.pid in (0x0005, 0x000A, 0x000C):
            return p.device
        # Fallbacks
        if p.vid == 0x2E8A:
            return p.device
        desc = p.description or ""
        if "MicroPython" in desc:
            return p.device
        if "Board in FS mode" in desc:
            return p.device
        product = p.product or ""
        if "Pico" in product:
            return p.device
    return None


class HomeView(ctk.CTkFrame):
    """Home screen that displays a live USB video stream from a Picoware device."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self._serial: serial.Serial | None = None
        self._running = False
        self._lock = threading.Lock()
        self._latest_frame: Image.Image | None = None
        self._display_w = 320
        self._display_h = 320
        self._buf = bytearray()
        self._frame_count = 0
        self._ctk_img_ref = None  # keep CTkImage alive

        self._build_ui()
        self._display_loop()

    def _build_ui(self) -> None:
        """Create the header bar and video display area."""

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))

        header.grid_columnconfigure(0, weight=1, uniform="side")
        header.grid_columnconfigure(1, weight=0)
        header.grid_columnconfigure(2, weight=1, uniform="side")

        self.status_label = ctk.CTkLabel(
            header,
            text="Not Connected",
            fg_color="transparent",
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.title_label = ctk.CTkLabel(
            header,
            text="Home",
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="transparent",
        )
        self.title_label.grid(row=0, column=1)

        self.connect_btn = ctk.CTkButton(
            header,
            text="Connect",
            command=self._toggle_connection,
            width=110,
        )
        self.connect_btn.grid(row=0, column=2, sticky="e", padx=(10, 0))

        self.video_frame = ctk.CTkFrame(self, fg_color="black")
        self.video_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.video_label = ctk.CTkLabel(self.video_frame, text="", fg_color="black")
        self.video_label.pack(fill="both", expand=True)

    def _display_loop(self) -> None:
        """Poll for new frames and push them to the CTkImage label."""
        with self._lock:
            frame = self._latest_frame
            self._latest_frame = None

        if frame is not None:
            lbl_w = self.video_label.winfo_width() or self._display_w
            lbl_h = self.video_label.winfo_height() or self._display_h
            if lbl_w > 1 and lbl_h > 1:
                ctk_img = ctk.CTkImage(light_image=frame, size=(lbl_w, lbl_h))
                self.video_label.configure(image=ctk_img)
                self._ctk_img_ref = ctk_img  # prevent GC

        self.after(33, self._display_loop)  # ~30 fps

    def _toggle_connection(self) -> None:
        """Button handler: connect or disconnect."""
        if self._running:
            self._disconnect()
        else:
            self._connect()

    def _connect(self) -> None:
        """Start connection attempt in a background thread."""
        self.status_label.configure(text="Connecting…")
        self.connect_btn.configure(text="Disconnect", state="disabled")
        threading.Thread(target=self._connect_thread, daemon=True).start()

    def _connect_thread(self) -> None:
        """Background: find device, open serial port, then read frames."""
        port = find_picoware_port()
        if not port:
            self.after(0, lambda: self._on_connect_fail("No device found"))
            return

        try:
            ser = serial.Serial(port, 2000000, timeout=0)
            ser.reset_input_buffer()
        except Exception as exc:
            self.after(0, lambda e=exc: self._on_connect_fail(str(e)))
            return

        self._serial = ser
        self._running = True
        self._buf = bytearray()
        self.after(0, lambda p=port: self._on_connected(p))

        try:
            while self._running:
                chunk = ser.read(65536)
                if chunk:
                    self._buf.extend(chunk)
                else:
                    time.sleep(0.001)
                self._process_buffer()
        except Exception:
            pass
        finally:
            self.after(0, self._on_disconnected)

    def _process_buffer(self) -> None:
        """Parse framed video data from the internal buffer (called from bg thread)."""
        while True:
            if len(self._buf) < USB_VIDEO_HDR_SIZE:
                break

            start = self._buf.find(USB_VIDEO_MAGIC_BYTES)
            if start < 0:
                # keep tail for split magic
                keep = len(USB_VIDEO_MAGIC_BYTES) - 1
                if len(self._buf) > keep:
                    del self._buf[:-keep]
                break
            if start > 0:
                del self._buf[:start]

            if len(self._buf) < USB_VIDEO_HDR_SIZE:
                break

            w = struct.unpack_from("<H", self._buf, 4)[0]
            h = struct.unpack_from("<H", self._buf, 6)[0]
            fmt = self._buf[8]

            if w == 0 or h == 0 or w > 1024 or h > 1024:
                del self._buf[0]
                continue

            pixel_size = w * h if fmt == USB_VIDEO_FORMAT_RGB332 else w * h * 2
            frame_size = USB_VIDEO_HDR_SIZE + pixel_size
            if len(self._buf) < frame_size:
                break

            frame_data = decode_frame(
                memoryview(self._buf)[USB_VIDEO_HDR_SIZE:frame_size], w, h, fmt
            )
            if frame_data is not None:
                try:
                    img = Image.frombytes("RGB", (w, h), frame_data)
                    with self._lock:
                        self._latest_frame = img
                        self._display_w = w
                        self._display_h = h
                    self._frame_count += 1
                except Exception:
                    pass

            del self._buf[:frame_size]

    def _on_connected(self, port: str) -> None:
        """Update UI after a successful connection."""
        self.status_label.configure(text=f"Connected — {port}")
        self.connect_btn.configure(text="Disconnect", state="normal")

    def _on_connect_fail(self, reason: str) -> None:
        """Reset UI after a failed connection attempt."""
        self.status_label.configure(text="Not Connected")
        self.connect_btn.configure(text="Connect", state="normal")

    def _on_disconnected(self) -> None:
        """Reset UI and close serial port after disconnection."""
        self._running = False
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        self.status_label.configure(text="Not Connected")
        self.connect_btn.configure(text="Connect", state="normal")

    def _disconnect(self) -> None:
        """Request disconnection (called on main thread)."""
        self.status_label.configure(text="Disconnecting…")
        self.connect_btn.configure(state="disabled")
        self._running = False

    def destroy(self) -> None:
        """Stop the read loop and close the serial port."""
        self._running = False
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        super().destroy()
