try:
    import ssl as _ssl
except ImportError:
    _ssl = None

try:
    PROTOCOL_TLS_CLIENT = _ssl.PROTOCOL_TLS_CLIENT
except Exception:
    PROTOCOL_TLS_CLIENT = 16

try:
    CERT_NONE = _ssl.CERT_NONE
except Exception:
    CERT_NONE = 0

try:
    CERT_REQUIRED = _ssl.CERT_REQUIRED
except Exception:
    CERT_REQUIRED = 2


class SSLContext:
    def __init__(self, protocol=PROTOCOL_TLS_CLIENT):
        """Wrap a CPython SSLContext for the simulator."""
        self.protocol = protocol
        self.verify_mode = CERT_REQUIRED
        self._context = None
        if _ssl is not None:
            try:
                self._context = _ssl.SSLContext(protocol)
            except Exception:
                self._context = None

    def wrap_socket(self, sock, server_hostname=None):
        """Wrap a socket with TLS using the underlying context."""
        if getattr(sock, "_sim_fixture", False):
            return sock
        if hasattr(sock, "_sim_real_socket"):
            sock = sock._sim_real_socket()
        if self._context is not None:
            try:
                if self.verify_mode == CERT_NONE and hasattr(self._context, "check_hostname"):
                    self._context.check_hostname = False
                self._context.verify_mode = self.verify_mode
            except Exception:
                pass
            return _wrap_compat(self._context.wrap_socket(sock, server_hostname=server_hostname))
        if _ssl is not None:
            try:
                return _wrap_compat(_ssl.wrap_socket(sock, server_hostname=server_hostname))
            except TypeError:
                return _wrap_compat(_ssl.wrap_socket(sock))
        return sock


class _CompatSocket:
    """Expose the small MicroPython stream API used by picoware.system.http."""

    def __init__(self, sock):
        self._sock = sock

    def write(self, data):
        if isinstance(data, str):
            data = data.encode()
        try:
            return self._sock.write(data)
        except AttributeError:
            return self._sock.send(data)

    def read(self, count=-1):
        if count is None or count < 0:
            chunks = []
            while True:
                data = self.recv(4096)
                if not data:
                    break
                chunks.append(data)
            return b"".join(chunks)
        try:
            return self._sock.read(count)
        except AttributeError:
            return self._sock.recv(count)

    def readline(self):
        chunks = []
        while True:
            data = self.read(1)
            if not data:
                break
            chunks.append(data)
            if data == b"\n":
                break
        return b"".join(chunks)

    def recv(self, count):
        try:
            return self._sock.recv(count)
        except AttributeError:
            return self._sock.read(count)

    def send(self, data):
        return self.write(data)

    def sendall(self, data):
        if isinstance(data, str):
            data = data.encode()
        try:
            return self._sock.sendall(data)
        except AttributeError:
            sent = 0
            while sent < len(data):
                n = self.write(data[sent:])
                if n <= 0:
                    raise OSError("socket send failed")
                sent += n
            return None

    def settimeout(self, value):
        return self._sock.settimeout(value)

    def close(self):
        return self._sock.close()

    def __getattr__(self, name):
        return getattr(self._sock, name)


def _wrap_compat(sock):
    if hasattr(sock, "readline") and hasattr(sock, "write"):
        return sock
    return _CompatSocket(sock)


def wrap_socket(sock, *args, **kwargs):
    """Wrap a socket with TLS; no-op for simulator fixtures."""
    if getattr(sock, "_sim_fixture", False):
        return sock
    if hasattr(sock, "_sim_real_socket"):
        sock = sock._sim_real_socket()
    if _ssl is None:
        return sock
    return _wrap_compat(_ssl.wrap_socket(sock, *args, **kwargs))
