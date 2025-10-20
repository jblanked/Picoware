# Workaround for the `urequests` module to support HTTP/1.1
# Based on https://github.com/micropython/micropython-lib/blob/e025c843b60e93689f0f991d753010bb5bd6a722/python-ecosys/requests/requests/__init__.py
# See https://github.com/micropython/micropython-lib/pull/861 and https://github.com/orgs/micropython/discussions/15112
# `1.0` replaced with `1.1, i.e.:
# `s.write(b"%s /%s HTTP/1.0\r\n" % (method, path))` changed to `s.write(b"%s /%s HTTP/1.1\r\n" % (method, path))`
# from https://github.com/AccelerationConsortium/ac-microcourses/blob/main/docs/courses/hello-world/urequests_2.py

RESPONSE_IS_BUSY = False


class Response:
    """Response object for HTTP requests."""

    def __init__(self, body):
        self.content = body
        self.encoding = "utf-8"
        self.text = str(self.content, self.encoding)
        self._json = None
        self.status_code = None
        self.reason = ""
        self.headers = {}

    def __del__(self):
        self.close()

    def close(self):
        self.content = None
        self.text = None
        self._json = None
        self.headers = None

    def json(self):
        from ujson import loads

        if self._json is None:
            self._json = loads(self.content)
        return self._json


def read_chunked(s, uart=None, method="GET", save_to_file=None, storage=None):
    """Read chunked HTTP response.

    Args:
        s: Socket object
        uart: UART object for writing output
        method: HTTP method name
        save_to_file: File path to save response data to (requires storage)
        storage: Storage object for file operations
    """
    global RESPONSE_IS_BUSY  # so we can modify the global variable
    if uart:
        uart.write(f"[{method}/SUCCESS] {method} request successful.\n")

    body = b""
    file_handle = None

    # Open file for writing if save_to_file is specified
    if save_to_file and storage:
        file_handle = storage.sd.open(save_to_file, "wb")
        if file_handle is None:
            raise RuntimeError(f"Failed to open file for writing: {save_to_file}")

    try:
        while True:
            RESPONSE_IS_BUSY = True
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
        RESPONSE_IS_BUSY = False

    return body


def request(
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
):
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

    global RESPONSE_IS_BUSY  # so we can modify the global variable
    redirect = None  # redirection url, None means no redirection
    chunked_data = (
        data and getattr(data, "__next__", None) and not getattr(data, "__len__", None)
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
                    raise NotImplementedError("Redirect %d not yet supported" % status)
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
            body = read_chunked(s, uart, method, save_to_file, storage)
        elif content_length is not None:
            if not uart and not save_to_file:
                body = s.read(content_length)
            elif save_to_file and storage:
                # Save directly to file
                file_handle = storage.sd.open(save_to_file, "wb")
                if file_handle is None:
                    raise RuntimeError(
                        f"Failed to open file for writing: {save_to_file}"
                    )
                try:
                    while content_length > 0:
                        RESPONSE_IS_BUSY = True
                        chunk_size = min(2048, content_length)
                        chunk = s.read(chunk_size)
                        if not chunk:
                            break
                        file_handle.write(chunk)
                        content_length -= len(chunk)
                finally:
                    file_handle.close()
                    RESPONSE_IS_BUSY = False
                body = b""
            else:
                # Read and write in fixed-size chunks to UART
                uart.write(f"[{method}/SUCCESS] {method} request successful.\n")
                while content_length > 0:
                    RESPONSE_IS_BUSY = True
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
                RESPONSE_IS_BUSY = False
        else:
            # Read until the socket is closed
            if not uart and not save_to_file:
                body = s.read()
            elif save_to_file and storage:
                # Save directly to file
                file_handle = storage.sd.open(save_to_file, "wb")
                if file_handle is None:
                    raise RuntimeError(
                        f"Failed to open file for writing: {save_to_file}"
                    )
                try:
                    while True:
                        RESPONSE_IS_BUSY = True
                        chunk = s.read(2048)
                        if not chunk:
                            break
                        file_handle.write(chunk)
                finally:
                    file_handle.close()
                    RESPONSE_IS_BUSY = False
                body = b""
            else:
                uart.write(f"[{method}/SUCCESS] {method} request successful.\n")
                while True:
                    RESPONSE_IS_BUSY = True
                    chunk = s.read(2048)
                    if not chunk:
                        break
                    uart.write(chunk)
                    uart.flush()
                uart.flush()
                uart.write("\n")
                uart.write(f"[{method}/END]")
                RESPONSE_IS_BUSY = False

        if redirect:
            s.close()
            if status in [301, 302, 303]:
                return request(
                    "GET",
                    redirect,
                    None,
                    None,
                    headers,
                    stream,
                    save_to_file=save_to_file,
                    storage=storage,
                )
            else:
                return request(
                    method,
                    redirect,
                    data,
                    json_data,
                    headers,
                    stream,
                    save_to_file=save_to_file,
                    storage=storage,
                )
        else:
            resp = Response(body)
            resp.status_code = status
            resp.reason = reason
            if resp_d is not None:
                resp.headers = resp_d
            return resp

    except OSError:
        s.close()
        raise


def head(url, **kw):
    """Send a HEAD request."""
    return request("HEAD", url, **kw)


def get(url, **kw):
    """Send a GET request."""
    return request("GET", url, **kw)


def post(url, **kw):
    """Send a POST request."""
    return request("POST", url, **kw)


def put(url, **kw):
    """Send a PUT request."""
    return request("PUT", url, **kw)


def patch(url, **kw):
    """Send a PATCH request."""
    return request("PATCH", url, **kw)


def delete(url, **kw):
    """Send a DELETE request."""
    return request("DELETE", url, **kw)
