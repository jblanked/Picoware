from .wifi import WiFi
from gc import collect as free
from micropython import const

HTTP_IDLE = const(0)
HTTP_LOADING = const(1)
HTTP_ISSUE = const(2)


class HTTP:
    """HTTP client for making requests over WiFi."""

    def __init__(self, wifi_object: WiFi) -> None:
        self.wifi = wifi_object
        self.pool = None
        self.ssl_context = None
        self._error = None
        self._state = HTTP_IDLE
        self.requests = None
        self._response = None
        self.is_ready = False
        self._callback: callable = None

    @property
    def callback(self) -> callable:
        """Get the current callback function."""
        return self._callback

    @callback.setter
    def callback(self, func: callable) -> None:
        """Set a callback function to be called after each request."""
        self._callback = func

    @property
    def error(self):
        """Get the last error encountered."""
        return self._error if self._error else ""

    @property
    def in_progress(self) -> bool:
        """Return True if a request is in progress, False otherwise."""
        return self._state == HTTP_LOADING

    @property
    def is_finished(self) -> bool:
        """Return True if the last request has finished, False otherwise."""
        return self._state == HTTP_IDLE

    @property
    def is_successful(self) -> bool:
        """Return True if the last request was successful, False otherwise."""
        return self._state == HTTP_IDLE and self._error is None

    @property
    def response(self) -> Response:
        """Get the last HTTP response."""
        return self._response

    @property
    def state(self) -> int:
        """Get the current state of the HTTP client."""
        return self._state

    def begin(self) -> bool:
        """Ensure WiFi is connected and initialize the HTTP session."""
        if not self.wifi.is_connected():
            return False
        try:
            import adafruit_connection_manager
            import adafruit_requests

            # Initalize Wifi, Socket Pool, Request Session
            self.pool = adafruit_connection_manager.get_radio_socketpool(
                self.wifi.radio
            )
            self.ssl_context = adafruit_connection_manager.get_radio_ssl_context(
                self.wifi.radio
            )
            self.requests = adafruit_requests.Session(self.pool, self.ssl_context)
            self.is_ready = True
            self._error = None
            return True
        except Exception as e:
            print("HTTP initialization error:", e)
            self._error = e
            self.is_ready = False
            del self.pool
            self.pool = None
            del self.ssl_context
            self.ssl_context = None
            del self.requests
            self.requests = None
            return False

    def close(self) -> None:
        """Close the HTTP session and free resources."""
        free()
        if self.is_ready:
            del self.pool
            self.pool = None
            del self.ssl_context
            self.ssl_context = None
            del self.requests
            self.requests = None
            self.is_ready = False

    def __async(self, url: str, method: str, **kw) -> bool:
        """Make an asynchronous HTTP request to the specified URL."""
        free()
        try:
            if not self.is_ready:
                if not self.begin():
                    raise RuntimeError(
                        "HTTP client is not initialized and failed to begin.."
                    )

            self._response = self.__request(url, method, **kw)
            self._state = HTTP_LOADING
            if self._callback:
                self._callback(response=self._response, error=None, state=HTTP_IDLE)
            self._state = HTTP_IDLE
            return True
        except Exception as e:
            self._state = HTTP_ISSUE
            self._error = e
            if self._callback:
                self._callback(response=None, error=e, state=HTTP_ISSUE)
            del self._response
            self._response = None
            del self.pool
            self.pool = None
            del self.ssl_context
            self.ssl_context = None
            del self.requests
            self.requests = None
            self.is_ready = False
            return False

    def delete(self, url: str, **kw) -> Response:
        """Make a DELETE request to the specified URL."""
        return self.__request(url, "delete", **kw)

    def delete_async(self, url: str, **kw) -> bool:
        """Make an asynchronous DELETE request to the specified URL."""
        return self.__async(url, "delete", **kw)

    def get(self, url: str, **kw) -> Response:
        """Make a GET request to the specified URL."""
        return self.__request(url, "get", **kw)

    def get_async(self, url: str, **kw) -> bool:
        """Make an asynchronous GET request to the specified URL."""
        return self.__async(url, "get", **kw)

    def patch(self, url: str, data: dict = None, json: dict = None, **kw) -> Response:
        """Make a PATCH request to the specified URL."""
        return self.__request(url, "patch", data=data, json=json, **kw)

    def patch_async(self, url: str, data: dict = None, json: dict = None, **kw) -> bool:
        """Make an asynchronous PATCH request to the specified URL."""
        return self.__async(url, "patch", data=data, json=json, **kw)

    def post(self, url: str, data: dict = None, json: dict = None, **kw) -> Response:
        """Make a POST request to the specified URL."""
        return self.__request(url, "post", data=data, json=json, **kw)

    def post_async(self, url: str, data: dict = None, json: dict = None, **kw) -> bool:
        """Make an asynchronous POST request to the specified URL."""
        return self.__async(url, "post", data=data, json=json, **kw)

    def put(self, url: str, data: dict = None, json: dict = None, **kw) -> Response:
        """Make a PUT request to the specified URL."""
        return self.__request(url, "put", data=data, json=json, **kw)

    def put_async(self, url: str, data: dict = None, json: dict = None, **kw) -> bool:
        """Make an asynchronous PUT request to the specified URL."""
        return self.__async(url, "put", data=data, json=json, **kw)

    def __request(
        self, url: str, method: str, save_to_file=None, storage=None, **kw
    ) -> Response:
        """Make a synchronous HTTP request to the specified URL."""
        free()
        if not self.is_ready:
            if not self.begin():
                raise RuntimeError(
                    "HTTP client is not initialized. Call begin() first."
                )
        return getattr(self.requests, method)(url, **kw)
