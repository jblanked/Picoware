from micropython import const
from picoware.system.response import Response

HTTP_IDLE = const(0)
HTTP_LOADING = const(1)
HTTP_ISSUE = const(2)


class HTTP:
    """HTTP class for making HTTP requests."""

    def __init__(self):
        """Initialize the HTTP class."""
        from _thread import allocate_lock

        self._async_request_complete = False
        self._async_request_in_progress = False
        self._async_thread = None
        self._state = HTTP_IDLE
        self._async_error = None
        self._async_callback: callable = None
        self._async_result = None
        self._lock = allocate_lock()
        self._running = False

    def __del__(self):
        """Destructor to clean up resources."""
        self.close()

    @property
    def callback(self) -> callable:
        """Get the async callback function."""
        return self._async_callback

    @callback.setter
    def callback(self, value: callable):
        """
        Set the async callback function.

        The callback function should accept three parameters:
            - response: The Response object or None if there was an error
            - state: The current HTTP state (HTTP_IDLE, HTTP_LOADING, HTTP_ISSUE)
            - error: The error message if any, otherwise None
        """
        self._async_callback = value

    @property
    def error(self):
        """Get the async error message, if any."""
        return self._async_error

    @property
    def in_progress(self) -> bool:
        """Check if the async request is in progress."""
        return self._async_request_in_progress

    @property
    def is_finished(self) -> bool:
        """Check if the async request is finished."""
        return self._async_request_complete

    @property
    def is_successful(self) -> bool:
        """Check if the async request was successful."""
        return self._async_request_complete and self._async_error is None

    @property
    def response(self):
        """Get the async Response object."""
        return self._async_result

    @property
    def state(self) -> int:
        """Get the current HTTP state."""
        return self._state

    def close(self):
        """Close the async thread, clear the async response, reset state."""
        self._async_thread = None
        with self._lock:
            self._running = False
            if self._async_result is not None:
                try:
                    self._async_result.close()
                except Exception:
                    pass
                finally:
                    del self._async_result
                    self._async_result = None
            self._async_request_complete = False
            self._async_request_in_progress = False
            self._async_error = None
            self._state = HTTP_IDLE

    def delete(
        self, url, headers=None, timeout: float = None, save_to_file=None, storage=None
    ) -> Response:
        """Sends a DELETE request and returns a Response object.

        Args:
            url: URL to request
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        if headers:
            return self.request(
                "DELETE",
                url,
                headers=headers,
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        return self.request(
            "DELETE", url, timeout=timeout, save_to_file=save_to_file, storage=storage
        )

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
        return self.request_async(
            "DELETE",
            url,
            headers=headers,
            timeout=timeout,
            save_to_file=save_to_file,
            storage=storage,
        )

    def get(
        self, url, headers=None, timeout: float = None, save_to_file=None, storage=None
    ) -> Response:
        """Sends a GET request and returns a Response object.

        Args:
            url: URL to request
            headers: HTTP headers dict
            timeout: Request timeout in seconds
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        if headers:
            return self.request(
                "GET",
                url=url,
                headers=headers,
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )

        return self.request(
            "GET", url=url, timeout=timeout, save_to_file=save_to_file, storage=storage
        )

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
        return self.request_async(
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
    ) -> Response:
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

        if payload is None:
            raise ValueError("HEAD request requires a payload.")

        if isinstance(payload, (str, bytes)):
            if headers:
                return self.request(
                    "HEAD",
                    url,
                    headers=headers,
                    data=payload,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            return self.request(
                "HEAD",
                url,
                data=payload,
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        if headers:
            return self.request(
                "HEAD",
                url,
                headers=headers,
                json_data=dumps(payload),
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        return self.request(
            "HEAD",
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
        return self.request_async(
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
    ) -> Response:
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

        if payload is None:
            raise ValueError("Payload cannot be None for PATCH request")

        if isinstance(payload, (str, bytes)):
            if headers:
                return self.request(
                    "PATCH",
                    url,
                    headers=headers,
                    data=payload,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            return self.request(
                "PATCH",
                url,
                data=payload,
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        if headers:
            return self.request(
                "PATCH",
                url,
                headers=headers,
                json_data=dumps(payload),
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        return self.request(
            "PATCH",
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
        return self.request_async(
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
    ) -> Response:
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

        if payload is None:
            raise ValueError("Payload cannot be None for POST request")

        if isinstance(payload, (str, bytes)):
            if headers:
                return self.request(
                    "POST",
                    url,
                    headers=headers,
                    data=payload,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            return self.request(
                "POST",
                url,
                data=payload,
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        if headers:
            return self.request(
                "POST",
                url,
                headers=headers,
                data=dumps(payload),
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        return self.request(
            "POST",
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
        return self.request_async(
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
    ) -> Response:
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

        if payload is None:
            raise ValueError("Payload cannot be None for PUT request")

        if isinstance(payload, (str, bytes)):
            if headers:
                return self.request(
                    "PUT",
                    url,
                    headers=headers,
                    data=payload,
                    timeout=timeout,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            return self.request(
                "PUT",
                url,
                data=payload,
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        if headers:
            return self.request(
                "PUT",
                url,
                headers=headers,
                json_data=dumps(payload),
                timeout=timeout,
                save_to_file=save_to_file,
                storage=storage,
            )
        return self.request(
            "PUT",
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
        return self.request_async(
            "PUT",
            url,
            payload=payload,
            headers=headers,
            timeout=timeout,
            save_to_file=save_to_file,
            storage=storage,
        )

    def read_chunked(self, s, uart=None, method="GET", save_to_file=None, storage=None):
        """Read chunked HTTP response.

        Args:
            s: Socket object
            uart: UART object for writing output
            method: HTTP method name
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        if uart:
            uart.write(f"[{method}/SUCCESS] {method} request successful.\n")

        body = b""
        file_handle = None

        # Open file for writing if save_to_file is specified
        if save_to_file and storage:
            storage.mount_vfs()
            file_handle = open(f"/sd/{save_to_file}", "wb")
            if file_handle is None:
                storage.unmount_vfs()
                raise RuntimeError(f"Failed to open file for writing: {save_to_file}")

        try:
            while True:
                if not self._running:
                    s.close()
                    if file_handle:
                        file_handle.close()
                        storage.unmount_vfs()
                    break
                # Read the chunk size line
                line = s.readline()
                if not line:
                    break
                # Remove any CRLF and convert from hex
                chunk_size_str = line.strip().split(b";")[0]  # Ignore chunk extensions
                try:
                    chunk_size = int(chunk_size_str, 16)
                except ValueError:
                    raise ValueError("Invalid chunk size: %s" % chunk_size_str)
                if chunk_size == 0:
                    # Read and discard trailer headers
                    while True:
                        trailer = s.readline()
                        if not trailer or trailer == b"\r\n":
                            break
                    break
                # Read the chunk data
                chunk = s.read(chunk_size)
                if uart:
                    uart.write(chunk)
                    uart.flush()
                elif file_handle:
                    # Write directly to file
                    file_handle.write(chunk)
                else:
                    body += chunk
                # Read the trailing CRLF after the chunk
                s.read(2)
            if uart:
                uart.flush()
                uart.write("\n")
                uart.write(f"[{method}/END]")
        finally:
            if file_handle:
                file_handle.close()
                storage.unmount_vfs()

        return body

    def request(
        self,
        method,
        url,
        data=None,
        json_data=None,
        headers={},
        stream=None,
        auth=None,
        timeout=None,
        parse_headers=True,
        uart=None,
        save_to_file=None,
        storage=None,
    ) -> Response:
        """Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            data: Request body data
            json_data: JSON data to send (will be serialized)
            headers: HTTP headers dict
            stream: Stream parameter (unused)
            auth: Authentication tuple (username, password)
            timeout: Request timeout in seconds
            parse_headers: Whether to parse response headers
            uart: UART object for streaming output
            save_to_file: File path to save response data to (requires storage)
            storage: Storage object for file operations
        """
        import ssl
        import usocket
        from ujson import dumps

        redirect = None  # redirection url, None means no redirection
        chunked_data = (
            data
            and getattr(data, "__next__", None)
            and not getattr(data, "__len__", None)
        )

        if auth is not None:
            import ubinascii

            username, password = auth
            formated = b"{}:{}".format(username, password)
            formated = str(ubinascii.b2a_base64(formated)[:-1], "ascii")
            headers["Authorization"] = "Basic {}".format(formated)

        try:
            proto, dummy, host, path = url.split("/", 3)
        except ValueError:
            proto, dummy, host = url.split("/", 2)
            path = ""
        if proto == "http:":
            port = 80
        elif proto == "https:":
            port = 443
        else:
            raise ValueError("Unsupported protocol: " + proto)

        if ":" in host:
            host, port = host.split(":", 1)
            port = int(port)

        ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)
        ai = ai[0]

        resp_d = {}
        if parse_headers is False:
            resp_d = None

        s = usocket.socket(ai[0], usocket.SOCK_STREAM, ai[2])

        if timeout is not None:
            # Note: settimeout is not supported on all platforms, will raise
            # an AttributeError if not available.
            try:
                s.settimeout(timeout)
            except AttributeError:
                pass

        try:
            self._running = True
            s.connect(ai[-1])
            if proto == "https:":
                s = ssl.wrap_socket(s, server_hostname=host)
            s.write(b"%s /%s HTTP/1.1\r\n" % (method, path))
            if "Host" not in headers:
                s.write(b"Host: %s\r\n" % host)
            # Iterate over keys to avoid tuple alloc
            for k in headers:
                s.write(k)
                s.write(b": ")
                s.write(headers[k])
                s.write(b"\r\n")
            if json_data is not None:
                assert data is None
                data = dumps(json_data)
                s.write(b"Content-Type: application/json\r\n")
            if data:
                if chunked_data:
                    s.write(b"Transfer-Encoding: chunked\r\n")
                else:
                    s.write(b"Content-Length: %d\r\n" % len(data))
            s.write(b"Connection: close\r\n\r\n")
            if data:
                if chunked_data:
                    for chunk in data:
                        s.write(b"%x\r\n" % len(chunk))
                        s.write(chunk)
                        s.write(b"\r\n")
                    s.write("0\r\n\r\n")
                else:
                    s.write(data)

            # Read the status line
            l = s.readline()
            # print(l)
            l = l.split(None, 2)
            if len(l) < 2:
                # Invalid response
                raise ValueError("HTTP error: BadStatusLine:\n%s" % l)
            status = int(l[1])
            reason = ""
            if len(l) > 2:
                reason = l[2].rstrip()
            transfer_encoding = None
            content_length = None
            while True:
                if not self._running:
                    s.close()
                    break
                l = s.readline()
                if not l or l == b"\r\n":
                    break
                # print(l)
                if l.startswith(b"Transfer-Encoding:"):
                    if b"chunked" in l:
                        transfer_encoding = "chunked"
                elif l.startswith(b"Content-Length:"):
                    content_length = int(l.split(b":", 1)[1].strip())
                elif l.startswith(b"Location:") and not 200 <= status <= 299:
                    if status in [301, 302, 303, 307, 308]:
                        redirect = str(l[10:-2], "utf-8")
                    else:
                        raise NotImplementedError(
                            "Redirect %d not yet supported" % status
                        )
                if parse_headers is False:
                    pass
                elif parse_headers is True:
                    l = str(l, "utf-8")
                    k, v = l.split(":", 1)
                    resp_d[k] = v.strip()
                else:
                    parse_headers(l, resp_d)

            # Read body
            if transfer_encoding == "chunked":
                body = self.read_chunked(s, uart, method, save_to_file, storage)
            elif content_length is not None:
                if not uart and not save_to_file:
                    body = s.read(content_length)
                elif save_to_file and storage:
                    # Save directly to file
                    storage.mount_vfs()
                    with open(f"/sd/{save_to_file}", "wb") as f:
                        try:
                            while content_length > 0:
                                chunk_size = min(2048, content_length)
                                chunk = s.read(chunk_size)
                                if not chunk:
                                    break
                                f.write(chunk)
                                content_length -= len(chunk)
                        finally:
                            f.close()
                    storage.unmount_vfs()
                    body = b""
                else:
                    # Read and write in fixed-size chunks to UART
                    uart.write(f"[{method}/SUCCESS] {method} request successful.\n")
                    while content_length > 0:
                        chunk_size = min(2048, content_length)
                        chunk = s.read(chunk_size)
                        if not chunk:
                            break
                        uart.write(chunk)
                        uart.flush()
                        content_length -= len(chunk)
                    uart.flush()
                    uart.write("\n")
                    uart.write(f"[{method}/END]")
            else:
                # Read until the socket is closed
                if not uart and not save_to_file:
                    body = s.read()
                elif save_to_file and storage:
                    # Save directly to file
                    storage.mount_vfs()
                    with open(f"/sd/{save_to_file}", "wb") as f:
                        try:
                            while True:
                                chunk = s.read(2048)
                                if not chunk:
                                    break
                                f.write(chunk)
                        finally:
                            f.close()
                    storage.unmount_vfs()
                    body = b""
                else:
                    uart.write(f"[{method}/SUCCESS] {method} request successful.\n")
                    while True:
                        chunk = s.read(2048)
                        if not chunk:
                            break
                        uart.write(chunk)
                        uart.flush()
                    uart.flush()
                    uart.write("\n")
                    uart.write(f"[{method}/END]")

            if redirect:
                s.close()
                if status in [301, 302, 303]:
                    return self.request(
                        "GET",
                        redirect,
                        None,
                        None,
                        headers,
                        stream,
                        save_to_file=save_to_file,
                        storage=storage,
                    )
                return self.request(
                    method,
                    redirect,
                    data,
                    json_data,
                    headers,
                    stream,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            resp = Response(body)
            resp.status_code = status
            resp.reason = reason
            if resp_d is not None:
                resp.headers = resp_d
            return resp

        except OSError:
            s.close()
            raise

    def request_async(
        self,
        method,
        url,
        payload=None,
        headers=None,
        timeout: float = None,
        save_to_file=None,
        storage=None,
    ) -> bool:
        """Method to handle async requests.

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
        self.close()
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
            self._async_thread = None
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
    ) -> None:
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
                self._async_result = result
                self._state = HTTP_IDLE
                del result
                result = None
            else:
                self._async_result = None
                self._state = HTTP_ISSUE
        except Exception as e:
            self._async_error = str(e)
            self._async_result = None
            self._state = HTTP_ISSUE
        finally:
            self._async_request_complete = True
            self._async_request_in_progress = False
            self._async_thread = None
            # Call the callback function if set
            if self._async_callback:
                self._async_callback(
                    response=self._async_result,
                    state=self._state,
                    error=self._async_error,
                )
            self._running = False
