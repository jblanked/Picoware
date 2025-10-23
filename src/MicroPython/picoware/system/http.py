from micropython import const

HTTP_IDLE = const(0)
HTTP_LOADING = const(1)
HTTP_ISSUE = const(2)


class HTTP:
    """HTTP class for making HTTP requests."""

    def __init__(self):
        """Initialize the HTTP class."""
        self._async_response = ""
        self._async_request_complete = False
        self._async_request_in_progress = False
        self._async_thread = None
        self._state = HTTP_IDLE
        self._async_error = None

    def __del__(self):
        """Destructor to clean up resources."""
        self.clear_async_response()

    @property
    def response(self):
        """Get the async response data."""
        return self._async_response

    @property
    def state(self) -> int:
        """Get the current HTTP state."""
        return self._state

    def clear_async_response(self):
        """Clear the async response and reset state."""
        self._async_response = ""
        self._async_request_complete = False
        self._async_request_in_progress = False
        self._async_error = None
        self._state = HTTP_IDLE
        if self._async_thread:
            try:
                # Clean up thread if it exists
                self._async_thread = None
                import _thread

                _thread.exit()
            except AttributeError:
                pass

    def delete(
        self, url, headers=None, timeout: float = None, save_to_file=None, storage=None
    ):
        """Sends a DELETE request and returns a Response object.

        Args:
            url: URL to request
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        from picoware.system.drivers.urequests_2 import delete

        if headers:
            return delete(
                url,
                headers=headers,
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        return delete(url, timeout=timeout, save_to_file=save_to_file, storage=storage)

    def delete_async(
        self, url, headers=None, timeout: float = None, save_to_file=None, storage=None
    ) -> bool:
        """Sends an async DELETE request.

        Args:
            url: URL to request
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        return self.__request_async(
            "DELETE",
            url,
            headers=headers,
            timeout=timeout,
            save_to_file=save_to_file,
            storage=storage,
        )

    def get(
        self, url, headers=None, timeout: float = None, save_to_file=None, storage=None
    ):
        """Sends a GET request and returns a Response object.

        Args:
            url: URL to request
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        from picoware.system.drivers.urequests_2 import get

        if headers:
            return get(
                url=url,
                headers=headers,
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )

        return get(url=url, timeout=timeout, save_to_file=save_to_file, storage=storage)

    def get_async(
        self, url, headers=None, timeout: float = None, save_to_file=None, storage=None
    ) -> bool:
        """Send an async GET request.

        Args:
            url: URL to request
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        return self.__request_async(
            "GET",
            url,
            headers=headers,
            timeout=timeout,
            save_to_file=save_to_file,
            storage=storage,
        )

    def head(
        self,
        url,
        payload,
        headers=None,
        timeout: float = None,
        save_to_file=None,
        storage=None,
    ):
        """Sends a HEAD request and returns a Response object.

        Args:
            url: URL to request
            payload: Request payload (can be str, bytes, or dict)
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        from ujson import dumps
        from picoware.system.drivers.urequests_2 import head

        if payload is None:
            return None
        if isinstance(payload, (str, bytes)):
            if headers:
                return head(
                    url,
                    headers=headers,
                    data=payload,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            return head(
                url,
                data=payload,
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        if headers:
            return head(
                url,
                headers=headers,
                json_data=dumps(payload),
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        return head(
            url,
            json_data=dumps(payload),
            timeout=timeout,
            save_to_file=save_to_file,
            storage=storage,
        )

    def head_async(
        self,
        url,
        payload,
        headers=None,
        timeout: float = None,
        save_to_file=None,
        storage=None,
    ) -> bool:
        """Send an async HEAD request.

        Args:
            url: URL to request
            payload: Request payload (can be str, bytes, or dict)
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        return self.__request_async(
            "HEAD",
            url,
            payload=payload,
            headers=headers,
            timeout=timeout,
            save_to_file=save_to_file,
            storage=storage,
        )

    def is_request_complete(self) -> bool:
        """Check if the async request is complete."""
        return self._async_request_complete

    def patch(
        self,
        url,
        payload,
        headers=None,
        timeout: float = None,
        save_to_file=None,
        storage=None,
    ):
        """Sends a PATCH request and returns a Response object.

        Args:
            url: URL to request
            payload: Request payload (can be str, bytes, or dict)
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        from ujson import dumps
        from picoware.system.drivers.urequests_2 import patch

        if payload is None:
            return None
        if isinstance(payload, (str, bytes)):
            if headers:
                return patch(
                    url,
                    headers=headers,
                    data=payload,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            return patch(
                url,
                data=payload,
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        if headers:
            return patch(
                url,
                headers=headers,
                json_data=dumps(payload),
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        return patch(
            url,
            json_data=dumps(payload),
            timeout=timeout,
            save_to_file=save_to_file,
            storage=storage,
        )

    def patch_async(
        self,
        url,
        payload,
        headers=None,
        timeout: float = None,
        save_to_file=None,
        storage=None,
    ) -> bool:
        """Send an async PATCH request.

        Args:
            url: URL to request
            payload: Request payload (can be str, bytes, or dict)
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        return self.__request_async(
            "PATCH",
            url,
            payload=payload,
            headers=headers,
            timeout=timeout,
            save_to_file=save_to_file,
            storage=storage,
        )

    def post(
        self,
        url,
        payload,
        headers=None,
        timeout: float = None,
        save_to_file=None,
        storage=None,
    ):
        """Sends a POST request and returns a Response object.

        Args:
            url: URL to request
            payload: Request payload (can be str, bytes, or dict)
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        from ujson import dumps
        from picoware.system.drivers.urequests_2 import post

        if payload is None:
            return None
        if isinstance(payload, (str, bytes)):
            if headers:
                return post(
                    url,
                    headers=headers,
                    data=payload,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            return post(
                url,
                data=payload,
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        if headers:
            return post(
                url,
                headers=headers,
                data=dumps(payload),
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        return post(
            url,
            json_data=dumps(payload),
            timeout=timeout,
            save_to_file=save_to_file,
            storage=storage,
        )

    def post_async(
        self,
        url,
        payload,
        headers=None,
        timeout: float = None,
        save_to_file=None,
        storage=None,
    ) -> bool:
        """Send an async POST request.

        Args:
            url: URL to request
            payload: Request payload (can be str, bytes, or dict)
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        return self.__request_async(
            "POST",
            url,
            payload=payload,
            headers=headers,
            timeout=timeout,
            save_to_file=save_to_file,
            storage=storage,
        )

    def put(
        self,
        url,
        payload,
        headers=None,
        timeout: float = None,
        save_to_file=None,
        storage=None,
    ):
        """Sends a PUT request and returns a Response object.

        Args:
            url: URL to request
            payload: Request payload (can be str, bytes, or dict)
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        from ujson import dumps
        from picoware.system.drivers.urequests_2 import put

        if payload is None:
            return None
        if isinstance(payload, (str, bytes)):
            if headers:
                return put(
                    url,
                    headers=headers,
                    data=payload,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            return put(
                url,
                data=payload,
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        if headers:
            return put(
                url,
                headers=headers,
                json_data=dumps(payload),
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        return put(
            url,
            json_data=dumps(payload),
            timeout=timeout,
            save_to_file=save_to_file,
            storage=storage,
        )

    def put_async(
        self,
        url,
        payload,
        headers=None,
        timeout: float = None,
        save_to_file=None,
        storage=None,
    ) -> bool:
        """Send an async PUT request.

        Args:
            url: URL to request
            payload: Request payload (can be str, bytes, or dict)
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        return self.__request_async(
            "PUT",
            url,
            payload=payload,
            headers=headers,
            timeout=timeout,
            save_to_file=save_to_file,
            storage=storage,
        )

    def __request_async(
        self,
        method,
        url,
        payload=None,
        headers=None,
        timeout: float = None,
        save_to_file=None,
        storage=None,
    ) -> bool:
        """Internal method to handle async requests.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            payload: Request payload
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        if self._async_request_in_progress:
            return False  # Request already in progress

        # Reset state
        self.clear_async_response()
        self._async_request_in_progress = True
        self._state = HTTP_LOADING

        try:
            import _thread

            # Start the request in a separate thread
            self._async_thread = _thread.start_new_thread(
                self.__execute_request,
                (method, url, payload, headers, timeout, save_to_file, storage),
            )
            return True
        except Exception as e:
            self._async_error = f"Thread creation failed: {e}"
            print(self._async_error)
            self._async_request_complete = True
            self._async_request_in_progress = False
            self._state = HTTP_ISSUE
            if self._async_thread:
                try:
                    # Clean up thread if it exists
                    self._async_thread = None
                    import _thread

                    _thread.exit()
                except AttributeError:
                    pass
            return False

    def __execute_request(
        self,
        method: str,
        url: str,
        payload,
        headers=None,
        timeout: float = None,
        save_to_file=None,
        storage=None,
    ):
        """Execute the actual HTTP request in a separate thread.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            payload: Request payload
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        try:
            result = None
            method = method.upper()

            if method == "GET":
                result = self.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            elif method == "POST":
                result = self.post(
                    url,
                    payload,
                    headers=headers,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            elif method == "PUT":
                result = self.put(
                    url,
                    payload,
                    headers=headers,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            elif method == "DELETE":
                result = self.delete(
                    url,
                    headers=headers,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            elif method == "HEAD":
                result = self.head(
                    url,
                    payload,
                    headers=headers,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            elif method == "PATCH":
                result = self.patch(
                    url,
                    payload,
                    headers=headers,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )

            if result:
                self._async_response = result.text
                self._state = HTTP_IDLE
                del result
                result = None
            else:
                self._async_response = ""
                self._state = HTTP_ISSUE
        except Exception as e:
            self._async_error = str(e)
            self._async_response = ""
            self._state = HTTP_ISSUE
        finally:
            self._async_request_complete = True
            self._async_request_in_progress = False
            if self._async_thread:
                try:
                    # Clean up thread if it exists
                    self._async_thread = None
                    import _thread

                    _thread.exit()
                except AttributeError:
                    pass
