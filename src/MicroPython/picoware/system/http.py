class HTTP:
    """HTTP class for making HTTP requests."""

    def __init__(self):
        """Initialize the HTTP class."""
        pass

    def get(self, url, headers=None, timeout: float = None):
        """Sends a GET request and returns a Response object."""
        from picoware.system.drivers.urequests_2 import get

        if headers:
            return get(url=url, headers=headers, timeout=timeout)

        return get(url=url, timeout=timeout)

    def post(self, url, payload, headers=None, timeout: float = None):
        """Send a POST request and returns a Response object."""
        from ujson import dumps
        from picoware.system.drivers.urequests_2 import post

        if payload is None:
            return None
        if isinstance(payload, (str, bytes)):
            if headers:
                return post(url, headers=headers, data=payload, timeout=timeout)
            return post(url, data=payload, timeout=timeout)
        if headers:
            return post(url, headers=headers, data=dumps(payload), timeout=timeout)
        return post(url, json_data=dumps(payload), timeout=timeout)

    def put(self, url, payload, headers=None, timeout: float = None):
        """Send a PUT request and returns a Response object."""
        from ujson import dumps
        from picoware.system.drivers.urequests_2 import put

        if payload is None:
            return None
        if isinstance(payload, (str, bytes)):
            if headers:
                return put(url, headers=headers, data=payload, timeout=timeout)
            return put(url, data=payload, timeout=timeout)
        if headers:
            return put(url, headers=headers, json_data=dumps(payload), timeout=timeout)
        return put(url, json_data=dumps(payload), timeout=timeout)

    def delete(self, url, headers=None, timeout: float = None):
        """Send a DELETE request and returns a Response object."""
        from picoware.system.drivers.urequests_2 import delete

        if headers:
            return delete(url, headers=headers, timeout=timeout)
        return delete(url, timeout=timeout)

    def head(self, url, payload, headers=None, timeout: float = None):
        """Send a HEAD request and returns a Response object."""
        from ujson import dumps
        from picoware.system.drivers.urequests_2 import head

        if payload is None:
            return None
        if isinstance(payload, (str, bytes)):
            if headers:
                return head(url, headers=headers, data=payload, timeout=timeout)
            return head(url, data=payload, timeout=timeout)
        if headers:
            return head(url, headers=headers, json_data=dumps(payload), timeout=timeout)
        return head(url, json_data=dumps(payload), timeout=timeout)

    def patch(self, url, payload, headers=None, timeout: float = None):
        """Send a PATCH request."""
        from ujson import dumps
        from picoware.system.drivers.urequests_2 import patch

        if payload is None:
            return None
        if isinstance(payload, (str, bytes)):
            if headers:
                return patch(url, headers=headers, data=payload, timeout=timeout)
            return patch(url, data=payload, timeout=timeout)
        if headers:
            return patch(
                url, headers=headers, json_data=dumps(payload), timeout=timeout
            )
        return patch(url, json_data=dumps(payload), timeout=timeout)
