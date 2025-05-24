from .wifi import WiFi
import adafruit_connection_manager  # https://circuitpython.org/libraries - add to the /lib folder
import adafruit_requests  # https://circuitpython.org/libraries - add to the /lib folder
from gc import collect as free


class HTTP:
    """HTTP client for making requests over WiFi."""

    def __init__(self, ssid: str, password: str, wifi_object: WiFi = None) -> None:
        self.ssid = ssid
        self.password = password
        self.wifi = wifi_object if wifi_object else WiFi()
        self.pool = None
        self.ssl_context = None
        self.requests = None
        self.is_ready = False

    def begin(self) -> bool:
        """Ensure WiFi is connected and initialize the HTTP session."""
        if not self.wifi.is_connected():
            if not self.wifi.connect(self.ssid, self.password):
                return False
        # Initalize Wifi, Socket Pool, Request Session
        self.pool = adafruit_connection_manager.get_radio_socketpool(self.wifi.network)
        self.ssl_context = adafruit_connection_manager.get_radio_ssl_context(
            self.wifi.network
        )
        self.requests = adafruit_requests.Session(self.pool, self.ssl_context)
        self.is_ready = True
        return True

    def delete(self, url: str, **kw) -> Response:
        """Make a DELETE request to the specified URL."""
        free()
        if not self.is_ready:
            raise RuntimeError("HTTP client is not initialized. Call begin() first.")
        return self.requests.delete(url, **kw)

    def get(self, url: str, **kw) -> Response:
        """Make a GET request to the specified URL."""
        free()
        if not self.is_ready:
            raise RuntimeError("HTTP client is not initialized. Call begin() first.")
        return self.requests.get(url, **kw)

    def patch(self, url: str, data: dict = None, json: dict = None, **kw) -> Response:
        """Make a PATCH request to the specified URL."""
        free()
        if not self.is_ready:
            raise RuntimeError("HTTP client is not initialized. Call begin() first.")
        return self.requests.patch(url, data=data, json=json, **kw)

    def post(self, url: str, data: dict = None, json: dict = None, **kw) -> Response:
        """Make a POST request to the specified URL."""
        free()
        if not self.is_ready:
            raise RuntimeError("HTTP client is not initialized. Call begin() first.")
        return self.requests.post(url, data=data, json=json, **kw)

    def put(self, url: str, data: dict = None, json: dict = None, **kw) -> Response:
        """Make a PUT request to the specified URL."""
        free()
        if not self.is_ready:
            raise RuntimeError("HTTP client is not initialized. Call begin() first.")
        return self.requests.put(url, data=data, json=json, **kw)
