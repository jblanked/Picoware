import jpegdec


class JPEG(jpegdec.JPEGDecoder):
    """JPEG decoder for Picoware."""

    def __init__(
        self,
        screen_width: int = 320,
        screen_height: int = 320,
        buffer_size: int = 1024 * 8,
        buffer_num: int = 2,
    ):
        super().__init__()
        self._max_width = screen_width
        self._max_height = screen_height
        self._buffer_size = buffer_size
        self._buffer_num = buffer_num
        self._filebuffer = None
        self._buffers = [None] * self._buffer_num
        self._buffers_pos = [-1] * self._buffer_num
        self._buffers_len = [self._buffer_size] * self._buffer_num
        self._decoder_running = False

    def draw(self, x: int, y: int, file_path, storage=None) -> bool:
        """Draw a JPEG file at position (x, y) on the display.

        Args:
            x: Horizontal draw position in pixels.
            y: Vertical draw position in pixels.
            file_path: Path to the .jpg / .jpeg file.
            storage: Storage class instance
        """
        if not file_path.endswith((".jpg", ".jpeg")):
            print("Bad file", file_path)
            return False
        if not file_path.startswith("sd") and not file_path.startswith("/sd"):
            file_path = "sd/" + file_path.lstrip("/")
        rc = True
        try:
            self._init_buffers()
            if storage:
                storage.mount_vfs()
            with open(file_path, mode="rb") as fi:
                fsize = fi.seek(0, 2)  # os.SEEK_END
                fi.seek(0, 0)  # os.SEEK_SET
                rc = self._decode_split(fi, fsize, x, y)
            if storage:
                storage.unmount_vfs()
        except OSError as e:
            print(e, "file open error")
            rc = False
        finally:
            self._cleanup()
        return rc

    def draw_buffer(self, x: int, y: int, buf) -> bool:
        """Draw a JPEG image from bytes data into a BytesIO buffer."""
        from io import BytesIO

        self._init_buffers()
        bio = BytesIO(buf)
        rc = False
        try:
            rc = self._decode_split(bio, len(buf), x, y)
        except OSError as e:
            print(e, "buffer decode error")
        return rc

    def __del__(self) -> None:
        self._cleanup()
        del self._filebuffer
        del self._buffers
        del self._buffers_pos
        del self._buffers_len

    def _init_buffers(self) -> None:
        if self._filebuffer is None:
            self._filebuffer = bytearray(self._buffer_size * self._buffer_num)
            mv = memoryview(self._filebuffer)
            for i in range(self._buffer_num):
                self._buffers[i] = mv[
                    i * self._buffer_size : (i + 1) * self._buffer_size
                ]

    def _cleanup(self) -> None:
        if self._decoder_running:
            self.decode_core_wait(1)
            self.decode_core_wait(1)
            self._decoder_running = False

    def _get_option(self, scale) -> int:
        if scale == 1:
            return 0
        if scale >= 0.5:
            return 2
        if scale >= 0.25:
            return 4
        if scale >= 0.125:
            return 8
        return 0

    def _get_scale(self, w, h) -> tuple[float, tuple[int, int]]:
        """Return (scale, (auto_x, auto_y)) so the image fits the display."""
        scale = 1.0
        for fact in (4, 2, 1):
            if w > self._max_width * fact or h > self._max_height * fact:
                fact = fact * 2
                scale = 1 / fact
                break
        sw = int(w * scale)
        sh = int(h * scale)
        off_x = (self._max_width - sw) // 2
        off_y = (self._max_height - sh) // 2
        return scale, (off_x, off_y)

    def _test_buffer(self, ipos, ilen) -> tuple[int, int]:
        idx = -1
        freeidx = 0
        for i in range(self._buffer_num):
            bufpos = self._buffers_pos[i]
            buflen = self._buffers_len[i]
            if bufpos < 0:
                freeidx = freeidx | (1 << i)
                continue
            if bufpos <= ipos and ipos + ilen <= bufpos + buflen:
                idx = i
            if bufpos + buflen <= ipos:
                freeidx = freeidx | (1 << i)
        return idx, freeidx

    def _read_into_buf(self, fi, buf):
        fi.readinto(buf)

    def _start_split(self, fsize, buf, x, y) -> bool:
        jpginfo = self.getinfo(buf)
        iw = jpginfo[1]
        ih = jpginfo[2]
        scale, auto_offset = self._get_scale(iw, ih)
        ioption = self._get_option(scale)
        offset = (x, y)
        jpginfo = self.decode_split(fsize, buf, offset, None, ioption)
        return jpginfo[0]

    def _decode_split(self, fi, fsize, x, y) -> bool:
        buf_idx = 0
        buf = self._buffers[buf_idx]
        self._buffers_pos[buf_idx] = 0
        fi.readinto(buf)
        self._decoder_running = True
        rc = self._start_split(fsize, buf, x, y)

        buf2 = self._buffers[1]
        pos2 = self._buffer_size
        self._buffers_pos[1] = pos2
        fi.seek(pos2)
        fi.readinto(buf2)
        _ = self.decode_split_buffer(1, pos2, buf2)

        newpos = -1
        newsize = -1
        while True:
            while True:
                retc = self.decode_split_wait()
                if retc[0] == 0:  # running
                    if retc[1] < 0:  # fpos not set yet
                        continue
                    newpos = retc[1]
                    newsize = retc[2]
                break
            if retc[0] != 0:  # done
                break

            idx, freeidx = self._test_buffer(newpos, newsize)
            if freeidx != 0:
                for i in range(self._buffer_num):
                    if freeidx & (1 << i) != 0:
                        buf2 = self._buffers[i]
                        for j in range(self._buffer_num):
                            if newpos < self._buffers_pos[j] + self._buffer_size:
                                newpos = self._buffers_pos[j] + self._buffer_size
                        pos2 = newpos
                        self._buffers_pos[i] = pos2
                        fi.seek(pos2)
                        fi.readinto(buf2)
                        self.decode_split_buffer(i, pos2, buf2)
                continue

            if idx != -1:  # requested data already buffered
                continue
            else:
                buf_idx = 0
            buf = self._buffers[buf_idx]
            self._buffers_pos[buf_idx] = newpos
            fi.seek(newpos)
            fi.readinto(buf)
            _ = self.decode_split_buffer(buf_idx, newpos, buf)

            buf_idx += 1
            if buf_idx >= self._buffer_num:
                buf_idx = 0
            buf = self._buffers[buf_idx]
            newpos += self._buffer_size
            self._buffers_pos[buf_idx] = newpos
            fi.seek(newpos)
            fi.readinto(buf)
            _ = self.decode_split_buffer(buf_idx, newpos, buf)

        self._decoder_running = False
        return rc
