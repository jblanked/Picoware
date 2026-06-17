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
                self._context.verify_mode = self.verify_mode
            except Exception:
                pass
            return self._context.wrap_socket(sock, server_hostname=server_hostname)
        if _ssl is not None:
            try:
                return _ssl.wrap_socket(sock, server_hostname=server_hostname)
            except TypeError:
                return _ssl.wrap_socket(sock)
        return sock


def wrap_socket(sock, *args, **kwargs):
    """Wrap a socket with TLS; no-op for simulator fixtures."""
    if getattr(sock, "_sim_fixture", False):
        return sock
    if hasattr(sock, "_sim_real_socket"):
        sock = sock._sim_real_socket()
    if _ssl is None:
        return sock
    return _ssl.wrap_socket(sock, *args, **kwargs)
