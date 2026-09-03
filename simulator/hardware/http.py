"""Simulator shim for the native HTTP helper module."""

_http = None
_last_response = None
_last_error = ""


def _client():
    global _http
    if _http is None:
        from picoware.system.http import HTTP

        _http = HTTP()
    return _http


def _headers_from_text(headers):
    if not headers:
        return None
    if isinstance(headers, dict):
        return headers
    out = {}
    for line in str(headers).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip()
    return out or None


def http_send_request(url, method="GET", headers=None, payload=None):
    """Start a request and cache the response for http_get_http_response()."""
    global _last_response, _last_error
    try:
        import sim_runtime

        if getattr(sim_runtime, "network_mode", "real") in ("offline", "fixture"):
            _last_response = _fixture_response(str(url), str(method or "GET"))
        else:
            _last_response = _client().request(
                str(method or "GET"),
                str(url),
                data=payload,
                headers=_headers_from_text(headers),
            )
        _last_error = ""
        return True
    except Exception as exc:
        _last_response = None
        _last_error = str(exc)
        return False


def _fixture_response(url, method):
    """Build a Response from the simulator's offline socket fixture."""
    import sim_usocket
    from response import Response

    parts = str(url).split("/", 3)
    if len(parts) < 3:
        raise ValueError("invalid fixture URL: " + str(url))
    proto = parts[0].lower()
    host = parts[2]
    path = "/" + parts[3] if len(parts) > 3 else "/"
    port = 443 if proto == "https:" else 80
    request = (str(method) + " " + path + " HTTP/1.1\r\n\r\n").encode()
    raw = sim_usocket._build_response((host, port), request)
    header, body = raw.split(b"\r\n\r\n", 1)
    lines = header.split(b"\r\n")
    status_line = lines[0].decode().split(" ", 2)
    response = Response()
    response.set_status_code(int(status_line[1]))
    response.set_reason(status_line[2] if len(status_line) > 2 else "")
    response.set_headers(
        {
            line.split(b":", 1)[0].decode(): line.split(b":", 1)[1].strip().decode()
            for line in lines[1:]
            if b":" in line
        }
    )
    response.set_content(body)
    response.set_text(body.decode())
    return response


def http_file_download(url, destination_path):
    """Download a URL to the simulated SD card."""
    global _last_response, _last_error
    try:
        from picoware.system.storage import Storage

        _last_response = _client().get(
            str(url),
            save_to_file=str(destination_path),
            storage=Storage(),
        )
        _last_error = ""
        return True
    except Exception as exc:
        _last_response = None
        _last_error = str(exc)
        return False


def http_get_http_response(buffer=None, buffer_size=0):
    """Return the cached response text.

    The native helper copies into a caller-provided buffer. Python callers in
    the simulator can use the returned string directly.
    """
    if _last_response is None:
        return ""
    text = getattr(_last_response, "text", "")
    if buffer is not None:
        data = str(text)[: int(buffer_size or len(str(text)))]
        try:
            buffer[: len(data)] = data
        except Exception:
            pass
    return text


def http_is_finished():
    return True


def http_last_error():
    return _last_error
