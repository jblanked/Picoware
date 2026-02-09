# translated from https://github.com/danni/uwebsockets/blob/esp8266/uwebsockets/protocol.py
from micropython import const
import ure as re
import ustruct as struct
import urandom as random
import usocket as socket
import ubinascii as binascii

# WebSocket opcodes
WS_OP_CONT = const(0x0)
WS_OP_TEXT = const(0x1)
WS_OP_BYTES = const(0x2)
WS_OP_CLOSE = const(0x8)
WS_OP_PING = const(0x9)
WS_OP_PONG = const(0xA)

# Close codes
WS_CLOSE_OK = const(1000)
WS_CLOSE_GOING_AWAY = const(1001)
WS_CLOSE_PROTOCOL_ERROR = const(1002)
WS_CLOSE_DATA_NOT_SUPPORTED = const(1003)
WS_CLOSE_BAD_DATA = const(1007)
WS_CLOSE_POLICY_VIOLATION = const(1008)
WS_CLOSE_TOO_BIG = const(1009)
WS_CLOSE_MISSING_EXTN = const(1010)
WS_CLOSE_BAD_CONDITION = const(1011)

# URL parsing
_URL_RE = re.compile(r"(wss|ws)://([A-Za-z0-9\-\.]+)(?:\:([0-9]+))?(/.+)?")


class WebSocketError(Exception):
    """Base exception for WebSocket errors."""

    pass


class NoDataException(Exception):
    """Raised when no data is available."""

    pass


class ConnectionClosed(Exception):
    """Raised when the connection is closed."""

    pass


def _urlparse(uri: str) -> tuple:
    """
    Parse a WebSocket URL.

    Args:
        uri: WebSocket URL (ws:// or wss://)

    Returns:
        Tuple of (protocol, hostname, port, path) or None if invalid
    """
    match = _URL_RE.match(uri)
    if match:
        protocol = match.group(1)
        host = match.group(2)
        port = match.group(3)
        path = match.group(4)

        if protocol == "wss":
            if port is None:
                port = 443
        elif protocol == "ws":
            if port is None:
                port = 80
        else:
            raise ValueError(f"Scheme {protocol} is invalid")

        return (protocol, host, int(port), path or "/")
    return None


class WebSocket:
    """
    Synchronous WebSocket client for MicroPython.

    Usage:
        ws = WebSocket.connect("wss://echo.websocket.org")
        ws.send("Hello!")
        response = ws.recv()
        ws.close()
    """

    is_client = True

    def __init__(self, sock, underlying_sock=None):
        """
        Initialize the WebSocket.

        Args:
            sock: Connected socket (possibly SSL-wrapped)
            underlying_sock: Underlying raw socket (for timeout control)
        """
        self._sock = sock
        self._underlying_sock = underlying_sock or sock
        self._open = True
        self._error = None
        self._blocking = True

    def __del__(self):
        """Destructor to clean up resources."""
        if self._open:
            self._close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    @property
    def error(self) -> str:
        """Get the last error message, if any."""
        return self._error

    @property
    def is_blocking(self) -> bool:
        """Check if the socket is in blocking mode."""
        return self._blocking

    @is_blocking.setter
    def is_blocking(self, flag: bool):
        """Set the socket to blocking or non-blocking mode."""
        try:
            self._underlying_sock.setblocking(flag)
            self._blocking = flag
        except Exception as e:
            print("Failed to set blocking:", e)

    @property
    def is_open(self) -> bool:
        """Check if the WebSocket is open."""
        return self._open

    @property
    def is_connected(self) -> bool:
        """Check if the WebSocket is connected."""
        return self._open

    def close(self, code: int = WS_CLOSE_OK, reason: str = ""):
        """
        Close the websocket gracefully.

        Args:
            code: Close status code
            reason: Optional close reason
        """
        if not self._open:
            return

        try:
            buf = struct.pack("!H", code) + reason.encode("utf-8")
            self._write_frame(WS_OP_CLOSE, buf)
        except Exception:
            pass

        self._close()

    @classmethod
    def connect(cls, uri: str, headers: dict = None, timeout: float = 10.0):
        """
        Connect to a WebSocket server.

        Args:
            uri: WebSocket URL (ws:// or wss://)
            headers: Optional additional headers for the handshake
            timeout: Connection timeout in seconds

        Returns:
            WebSocket instance
        """
        parsed = _urlparse(uri)
        if not parsed:
            raise ValueError(f"Invalid WebSocket URL: {uri}")

        protocol, hostname, port, path = parsed

        # Create socket and connect
        sock = socket.socket()
        addr = socket.getaddrinfo(hostname, port)
        sock.connect(addr[0][4])

        # Set timeout
        try:
            sock.settimeout(timeout)
        except Exception:
            pass

        # Store reference to underlying socket
        underlying_sock = sock

        # Wrap with SSL if secure
        if protocol == "wss":
            import tls

            _context = tls.SSLContext(tls.PROTOCOL_TLS_CLIENT)
            _context.verify_mode = tls.CERT_NONE
            sock = _context.wrap_socket(sock, server_hostname=hostname)

        # Helper to send headers
        def send_header(header, *args):
            if args:
                line = header % args + b"\r\n"
            else:
                line = header + b"\r\n"
            sock.write(line)

        # Generate WebSocket key (16 random bytes, base64 encoded)
        key = binascii.b2a_base64(bytes(random.getrandbits(8) for _ in range(16)))[:-1]

        # Send handshake headers
        send_header(
            b"GET %s HTTP/1.1", path.encode() if isinstance(path, str) else path
        )
        send_header(b"Host: %s:%d", hostname.encode(), port)
        send_header(b"Connection: Upgrade")
        send_header(b"Upgrade: websocket")
        send_header(b"Sec-WebSocket-Key: %s", key)
        send_header(b"Sec-WebSocket-Version: 13")
        send_header(b"Origin: http://%s:%d", hostname.encode(), port)

        # Add custom headers
        if headers:
            for k, v in headers.items():
                send_header(
                    b"%s: %s",
                    k.encode() if isinstance(k, str) else k,
                    v.encode() if isinstance(v, str) else v,
                )

        send_header(b"")

        # Read response
        header = sock.readline()[:-2]
        if not header.startswith(b"HTTP/1.1 101"):
            raise WebSocketError(f"Handshake failed: {header}")

        # Read remaining headers (we don't need them)
        while header:
            header = sock.readline()[:-2]

        return cls(sock, underlying_sock)

    def ping(self, data: bytes = b"") -> bool:
        """
        Send a ping frame.

        Args:
            data: Optional ping payload (max 125 bytes)

        Returns:
            True if sent successfully
        """
        if not self._open:
            self._error = "Connection closed"
            return False

        try:
            if len(data) > 125:
                data = data[:125]
            self._write_frame(WS_OP_PING, data)
            return True
        except Exception as e:
            self._error = str(e)
            return False

    def pong(self, data: bytes = b"") -> bool:
        """
        Send a pong frame.

        Args:
            data: Pong payload

        Returns:
            True if sent successfully
        """
        if not self._open:
            self._error = "Connection closed"
            return False

        try:
            if len(data) > 125:
                data = data[:125]
            self._write_frame(WS_OP_PONG, data)
            return True
        except Exception as e:
            self._error = str(e)
            return False

    def recv(self):
        """
        Receive data from the websocket.

        Returns:
            Received data as string (for text) or bytes (for binary),
            empty string if no data, or None if connection closed.
        """
        if not self._open:
            return None

        # ensure socket is non-blocking for reads
        try:
            self._underlying_sock.setblocking(False)
            self._blocking = False
        except Exception:
            pass

        try:
            while self._open:
                try:
                    fin, opcode, data = self._read_frame()
                except NoDataException:
                    return ""
                except ValueError as e:
                    self._close()
                    raise ConnectionClosed() from e

                if not fin:
                    raise NotImplementedError("Fragmented frames not supported")

                if opcode == WS_OP_TEXT:
                    return data.decode("utf-8")
                if opcode == WS_OP_BYTES:
                    return data
                if opcode == WS_OP_CLOSE:
                    self._close()
                    return None
                if opcode == WS_OP_PONG:
                    # Return PONG data so caller can see it
                    return "PONG"
                if opcode == WS_OP_PING:
                    # Send pong and continue waiting
                    self._write_frame(WS_OP_PONG, data)
                    continue
                if opcode == WS_OP_CONT:
                    raise NotImplementedError("Continuation frames not supported")
                raise ValueError(f"Unknown opcode: {opcode}")
        finally:
            # Restore blocking mode for writes
            try:
                self._underlying_sock.setblocking(True)
                self._blocking = True
            except Exception:
                pass

    def send(self, data) -> bool:
        """
        Send data to the websocket.

        Args:
            data: Data to send (str or bytes)

        Returns:
            True if sent successfully
        """
        if not self._open:
            self._error = "Connection closed"
            return False

        try:
            if isinstance(data, str):
                opcode = WS_OP_TEXT
                data = data.encode("utf-8")
            elif isinstance(data, bytes):
                opcode = WS_OP_BYTES
            else:
                raise TypeError("Data must be str or bytes")

            self._write_frame(opcode, data)
            return True

        except OSError as e:
            self._error = f"OSError {e.args[0]}: {e}"
            self._close()
            return False
        except Exception as e:
            self._error = str(e)
            return False

    def _close(self):
        """Internal close - cleanup resources."""
        self._open = False
        try:
            self._sock.close()
        except Exception:
            pass

    def _read_frame(self, max_size=None):
        """
        Read a frame from the socket.
        See https://tools.ietf.org/html/rfc6455#section-5.2 for details.
        """
        # Frame header (2 bytes)
        try:
            two_bytes = self._sock.read(2)
        except OSError as e:
            # Timeout or connection error: ETIMEDOUT(110), EAGAIN(11), EWOULDBLOCK(11), etc
            errno = e.args[0] if e.args else None
            if errno in (-110, 110, 11, -11, 35, -35, 116, -116):
                raise NoDataException() from e
            # Other errors - connection might be closed
            print(f"Socket error during read_frame: errno={errno}")
            raise
        except Exception as e:
            print(f"Unexpected error during read_frame: {type(e).__name__}: {e}")
            raise

        if not two_bytes:
            raise NoDataException()

        byte1, byte2 = struct.unpack("!BB", two_bytes)

        # Byte 1: FIN(1) _(1) _(1) _(1) OPCODE(4)
        fin = bool(byte1 & 0x80)
        opcode = byte1 & 0x0F

        # Byte 2: MASK(1) LENGTH(7)
        mask = bool(byte2 & (1 << 7))
        length = byte2 & 0x7F

        if length == 126:  # 2-byte length header
            (length,) = struct.unpack("!H", self._sock.read(2))
        elif length == 127:  # 8-byte length header
            (length,) = struct.unpack("!Q", self._sock.read(8))

        mask_bits = None
        if mask:  # Mask is 4 bytes
            mask_bits = self._sock.read(4)

        try:
            data = self._sock.read(length)
        except MemoryError:
            # Frame too big, close the socket
            self.close(code=WS_CLOSE_TOO_BIG)
            return True, WS_OP_CLOSE, None

        if mask and mask_bits:
            data = bytes(b ^ mask_bits[i % 4] for i, b in enumerate(data))

        return fin, opcode, data

    def _write_frame(self, opcode: int, data: bytes = b""):
        """
        Write a frame to the socket.
        Args:
            opcode: Frame opcode
            data: Frame payload
        """
        fin = True
        mask = self.is_client  # Client messages are masked

        length = len(data)

        # Frame header
        # Byte 1: FIN(1) _(1) _(1) _(1) OPCODE(4)
        byte1 = 0x80 if fin else 0
        byte1 |= opcode

        # Byte 2: MASK(1) LENGTH(7)
        byte2 = 0x80 if mask else 0

        if length < 126:
            byte2 |= length
            self._sock.write(struct.pack("!BB", byte1, byte2))
        elif length < (1 << 16):
            byte2 |= 126
            self._sock.write(struct.pack("!BBH", byte1, byte2, length))
        elif length < (1 << 64):
            byte2 |= 127
            self._sock.write(struct.pack("!BBQ", byte1, byte2, length))
        else:
            raise ValueError("Data too large")

        if mask:
            mask_bits = struct.pack("!I", random.getrandbits(32))
            self._sock.write(mask_bits)
            data = bytes(b ^ mask_bits[i % 4] for i, b in enumerate(data))

        self._sock.write(data)


class WebSocketAsync:
    """WebSocket implementation that runs in a separate thread."""

    def __init__(
        self,
        uri: str,
        headers: dict = None,
        timeout: float = 10.0,
        callback: callable = None,  # one-argument function (data: Any)
        thread_manager=None,
    ):
        import _thread

        self._uri: str = uri
        self._headers: dict = headers
        self._timeout: float = timeout
        self._callback: callable = callback
        self._running: bool = False
        self._ws: WebSocket = None
        self._thread = None
        self._lock = _thread.allocate_lock()
        self._thread_manager = thread_manager
        self._current_task = None

    def __del__(self):
        """Destructor to clean up resources."""
        self.close()

    def __close_thread(self):
        """Internal method to close the thread."""
        if self._current_task:
            self._current_task.stop()
            self._current_task = None
        if self._thread is not None:
            self._thread = None

    def _should_continue(self) -> bool:
        """Check if the operation should continue running."""
        with self._lock:
            if self._thread_manager is not None and self._current_task is not None:
                return self._running and not self._current_task.should_stop
            return self._running

    @property
    def error(self) -> str:
        """Get the last error message, if any."""
        if self._ws:
            return self._ws.error
        return ""

    @property
    def is_connected(self) -> bool:
        """Check if the WebSocket is connected."""
        return self._ws.is_connected if self._ws else False

    @property
    def is_running(self) -> bool:
        """Check if the WebSocket thread is running."""
        return self._running

    def close(self):
        """Close the WebSocket connection."""
        self._running = False

        with self._lock:
            if self._ws is not None:
                try:
                    self._ws.close()
                except Exception:
                    pass
                self._ws = None
            self.__close_thread()

    def connect(self) -> bool:
        """Start the WebSocket connection in a separate thread."""
        if self._running:
            return True  # Already running

        self.__close_thread()

        def _thread_func():
            try:
                self._ws = WebSocket.connect(
                    self._uri, headers=self._headers, timeout=self._timeout
                )
                self._running = True
                while self._should_continue():
                    try:
                        data = self._ws.recv()
                        if data is not None and data != "":
                            if self._callback:
                                self._callback(data)
                    except ConnectionClosed:
                        if self._callback:
                            self._callback(None)
                        self.close()
                        break
                    except NoDataException:
                        pass
                    except OSError:
                        pass
            except Exception as e:
                if self._callback:
                    self._callback(e)
            finally:
                self._running = False
                if self._ws:
                    self._ws.close()
                    del self._ws
                    self._ws = None

        try:
            if self._thread_manager:
                # Use ThreadManager
                from picoware.system.thread import ThreadTask

                task = ThreadTask(
                    "WebSocket",
                    function=_thread_func,
                    args=(),
                )
                self._current_task = task
                self._thread_manager.add_task(task)
            else:
                import _thread

                self._thread = _thread.start_new_thread(_thread_func, ())
        except Exception as e:
            self._running = False
            if self._callback:
                self._callback(e)
            return False

        return True

    def ping(self, data: bytes = b"") -> bool:
        """Send a ping to the WebSocket server."""
        with self._lock:
            if self._ws and self._running:
                return self._ws.ping(data)
        return False

    def pong(self, data: bytes = b"") -> bool:
        """Send a pong to the WebSocket server."""
        with self._lock:
            if self._ws and self._running:
                return self._ws.pong(data)
        return False

    def send(self, data) -> bool:
        """Send data to the WebSocket server."""
        with self._lock:
            if self._ws and self._running:
                return self._ws.send(data)
        return False
