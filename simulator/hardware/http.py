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
        _last_response = _client().request(
            str(method or "GET"),
            str(url),
            payload=payload,
            headers=_headers_from_text(headers),
        )
        _last_error = ""
        return True
    except Exception as exc:
        _last_response = None
        _last_error = str(exc)
        return False


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
