# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: 2024 Justin Myers for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_connection_manager`
================================================================================

A urllib3.poolmanager/urllib3.connectionpool-like library for managing sockets and connections


* Author(s): Justin Myers

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_ConnectionManager.git"

import errno
import sys

WIZNET5K_SSL_SUPPORT_VERSION = (9, 1)

if not sys.implementation.name == "circuitpython":
    from typing import List, Optional, Tuple

    from circuitpython_typing.socket import (
        CircuitPythonSocketType,
        InterfaceType,
        SocketpoolModuleType,
        SocketType,
        SSLContextType,
    )


class _FakeSSLSocket:
    def __init__(self, socket: CircuitPythonSocketType, tls_mode: int) -> None:
        self._socket = socket
        self._mode = tls_mode
        self.settimeout = socket.settimeout
        self.send = socket.send
        self.recv = socket.recv
        self.close = socket.close
        self.recv_into = socket.recv_into
        # For sockets that come from software socketpools (like the esp32api), they track
        # the interface and socket pool. We need to make sure the clones do as well
        self._interface = getattr(socket, "_interface", None)
        self._socket_pool = getattr(socket, "_socket_pool", None)

    def connect(self, address: Tuple[str, int]) -> None:
        """Connect wrapper to add non-standard mode parameter"""
        try:
            return self._socket.connect(address, self._mode)
        except RuntimeError as error:
            raise OSError(errno.ENOMEM, str(error)) from error


class _FakeSSLContext:
    def __init__(self, iface: InterfaceType) -> None:
        self._iface = iface

    def wrap_socket(
        self, socket: CircuitPythonSocketType, server_hostname: Optional[str] = None
    ) -> _FakeSSLSocket:
        """Return the same socket"""
        if hasattr(self._iface, "TLS_MODE"):
            return _FakeSSLSocket(socket, self._iface.TLS_MODE)

        raise ValueError("This radio does not support TLS/HTTPS")


def create_fake_ssl_context(
    socket_pool: SocketpoolModuleType, iface: InterfaceType
) -> _FakeSSLContext:
    """Method to return a fake SSL context for when ssl isn't available to import

    For example when using a:

     * `Adafruit Ethernet FeatherWing <https://www.adafruit.com/product/3201>`_
     * `Adafruit AirLift – ESP32 WiFi Co-Processor Breakout Board
       <https://www.adafruit.com/product/4201>`_
     * `Adafruit AirLift FeatherWing – ESP32 WiFi Co-Processor
       <https://www.adafruit.com/product/4264>`_
    """
    if hasattr(socket_pool, "set_interface"):
        # this is to manually support legacy hardware like the fona
        socket_pool.set_interface(iface)

    return _FakeSSLContext(iface)


class CPythonNetwork:
    """Radio object to use when using ConnectionManager in CPython."""


_global_connection_managers = {}
_global_key_by_socketpool = {}
_global_socketpools = {}
_global_ssl_contexts = {}


def _get_radio_hash_key(radio):
    try:
        return hash(radio)
    except TypeError:
        return radio.__class__.__name__


def get_radio_socketpool(radio):
    """Helper to get a socket pool for common boards.

    Currently supported:

     * Boards with onboard WiFi (ESP32S2, ESP32S3, Pico W, etc)
     * Using the ESP32 WiFi Co-Processor (like the Adafruit AirLift)
     * Using a WIZ5500 (Like the Adafruit Ethernet FeatherWing)
    """
    key = _get_radio_hash_key(radio)
    if key not in _global_socketpools:
        class_name = radio.__class__.__name__
        if class_name == "Radio":
            import ssl

            import socketpool

            pool = socketpool.SocketPool(radio)
            ssl_context = ssl.create_default_context()

        elif class_name == "ESP_SPIcontrol":
            import adafruit_esp32spi.adafruit_esp32spi_socketpool as socketpool

            pool = socketpool.SocketPool(radio)
            ssl_context = create_fake_ssl_context(pool, radio)

        elif class_name == "WIZNET5K":
            import adafruit_wiznet5k.adafruit_wiznet5k_socketpool as socketpool

            pool = socketpool.SocketPool(radio)

            # Note: At this time, SSL/TLS connections are not supported by older
            # versions of the Wiznet5k library or on boards withouut the ssl module
            # see https://docs.circuitpython.org/en/latest/shared-bindings/support_matrix.html
            ssl_context = None
            implementation_name = sys.implementation.name
            implementation_version = sys.implementation.version
            if (
                pool.SOCK_STREAM == 1
                and implementation_name == "circuitpython"
                and implementation_version >= WIZNET5K_SSL_SUPPORT_VERSION
            ):
                try:
                    import ssl

                    ssl_context = ssl.create_default_context()
                except ImportError:
                    # if SSL not on board, default to fake_ssl_context
                    pass

            if ssl_context is None:
                ssl_context = create_fake_ssl_context(pool, radio)

        elif class_name == "CPythonNetwork":
            import socket as pool
            import ssl

            ssl_context = ssl.create_default_context()

        else:
            raise ValueError(f"Unsupported radio class: {class_name}")

        _global_key_by_socketpool[pool] = key
        _global_socketpools[key] = pool
        _global_ssl_contexts[key] = ssl_context

    return _global_socketpools[key]


def get_radio_ssl_context(radio):
    """Helper to get ssl_contexts for common boards.

    Currently supported:

     * Boards with onboard WiFi (ESP32S2, ESP32S3, Pico W, etc)
     * Using the ESP32 WiFi Co-Processor (like the Adafruit AirLift)
     * Using a WIZ5500 (Like the Adafruit Ethernet FeatherWing)
    """
    get_radio_socketpool(radio)
    return _global_ssl_contexts[_get_radio_hash_key(radio)]


class ConnectionManager:
    """A library for managing sockets across multiple hardware platforms and libraries."""

    def __init__(
        self,
        socket_pool: SocketpoolModuleType,
    ) -> None:
        self._socket_pool = socket_pool
        # Hang onto open sockets so that we can reuse them.
        self._available_sockets = set()
        self._key_by_managed_socket = {}
        self._managed_socket_by_key = {}

    def _free_sockets(self, force: bool = False) -> None:
        # cloning lists since items are being removed
        available_sockets = list(self._available_sockets)
        for socket in available_sockets:
            self.close_socket(socket)
        if force:
            open_sockets = list(self._managed_socket_by_key.values())
            for socket in open_sockets:
                self.close_socket(socket)

    def _register_connected_socket(self, key, socket):
        """Register a socket as managed."""
        self._key_by_managed_socket[socket] = key
        self._managed_socket_by_key[key] = socket

    def _get_connected_socket(
        self,
        addr_info: List[Tuple[int, int, int, str, Tuple[str, int]]],
        host: str,
        port: int,
        timeout: float,
        is_ssl: bool,
        ssl_context: Optional[SSLContextType] = None,
    ):
        socket = self._socket_pool.socket(addr_info[0], addr_info[1])

        if is_ssl:
            socket = ssl_context.wrap_socket(socket, server_hostname=host)
            connect_host = host
        else:
            connect_host = addr_info[-1][0]

        # Set socket read and connect timeout.
        socket.settimeout(timeout)

        try:
            socket.connect((connect_host, port))
        except (MemoryError, OSError):
            # If any connect problems, clean up and re-raise the problem exception.
            socket.close()
            raise

        return socket

    @property
    def available_socket_count(self) -> int:
        """Get the count of available (freed) managed sockets."""
        return len(self._available_sockets)

    @property
    def managed_socket_count(self) -> int:
        """Get the count of managed sockets."""
        return len(self._managed_socket_by_key)

    def close_socket(self, socket: SocketType) -> None:
        """
        Close a previously managed and connected socket.

        - **socket_pool** *(SocketType)* – The socket you want to close
        """
        if socket not in self._managed_socket_by_key.values():
            raise RuntimeError("Socket not managed")
        socket.close()
        key = self._key_by_managed_socket.pop(socket)
        del self._managed_socket_by_key[key]
        if socket in self._available_sockets:
            self._available_sockets.remove(socket)

    def free_socket(self, socket: SocketType) -> None:
        """Mark a managed socket as available so it can be reused. The socket is not closed."""
        if socket not in self._managed_socket_by_key.values():
            raise RuntimeError("Socket not managed")
        self._available_sockets.add(socket)

    def get_socket(
        self,
        host: str,
        port: int,
        proto: str,
        session_id: Optional[str] = None,
        *,
        timeout: float = 1.0,
        is_ssl: bool = False,
        ssl_context: Optional[SSLContextType] = None,
    ) -> CircuitPythonSocketType:
        """
        Get a new socket and connect to the given host.

        :param str host: host to connect to, such as ``"www.example.org"``
        :param int port: port to use for connection, such as ``80`` or ``443``
        :param str proto: connection protocol: ``"http:"``, ``"https:"``, etc.
        :param Optional[str]: unique session ID,
          used for multiple simultaneous connections to the same host
        :param float timeout: how long to wait to connect
        :param bool is_ssl: ``True`` If the connection is to be over SSL;
          automatically set when ``proto`` is ``"https:"``
        :param Optional[SSLContextType]: SSL context to use when making SSL requests
        """
        if session_id:
            session_id = str(session_id)
        key = (host, port, proto, session_id)

        # Do we have already have a socket available for the requested connection?
        if key in self._managed_socket_by_key:
            socket = self._managed_socket_by_key[key]
            if socket in self._available_sockets:
                self._available_sockets.remove(socket)
                return socket

            raise RuntimeError(f"An existing socket is already connected to {proto}//{host}:{port}")

        if proto == "https:":
            is_ssl = True
        if is_ssl and not ssl_context:
            raise ValueError("ssl_context must be provided if using ssl")

        addr_info = self._socket_pool.getaddrinfo(host, port, 0, self._socket_pool.SOCK_STREAM)[0]

        try:
            socket = self._get_connected_socket(addr_info, host, port, timeout, is_ssl, ssl_context)
            self._register_connected_socket(key, socket)
            return socket
        except (MemoryError, OSError, RuntimeError):
            # Could not get a new socket (or two, if SSL).
            # If there are any available sockets, free them all and try again.
            if self.available_socket_count:
                self._free_sockets()
                socket = self._get_connected_socket(
                    addr_info, host, port, timeout, is_ssl, ssl_context
                )
                self._register_connected_socket(key, socket)
                return socket
            # Re-raise exception if no sockets could be freed.
            raise


def connection_manager_close_all(
    socket_pool: Optional[SocketpoolModuleType] = None, release_references: bool = False
) -> None:
    """
    Close all open sockets for pool, optionally release references.

    :param Optional[SocketpoolModuleType] socket_pool:
      a specific socket pool whose sockets you want to close; ``None`` means all socket pools
    :param bool release_references: ``True`` if you also want the `ConnectionManager` to forget
      all the socket pools and SSL contexts it knows about
    """
    if socket_pool:
        socket_pools = [socket_pool]
    else:
        socket_pools = _global_connection_managers.keys()

    for pool in socket_pools:
        connection_manager = _global_connection_managers.get(pool, None)
        if connection_manager is None:
            raise RuntimeError("SocketPool not managed")

        connection_manager._free_sockets(force=True)

        if not release_references:
            continue

        key = _global_key_by_socketpool.pop(pool)
        if key:
            _global_socketpools.pop(key, None)
            _global_ssl_contexts.pop(key, None)

        _global_connection_managers.pop(pool, None)


def get_connection_manager(socket_pool: SocketpoolModuleType) -> ConnectionManager:
    """
    Get or create the ConnectionManager singleton for the given pool.
    """
    if socket_pool not in _global_connection_managers:
        _global_connection_managers[socket_pool] = ConnectionManager(socket_pool)
    return _global_connection_managers[socket_pool]
