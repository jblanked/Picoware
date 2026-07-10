"""Simulator shim for the native websocket helper functions."""

_websocket = None


def http_websocket_start(url, port=0):
    global _websocket
    if _websocket is not None:
        return False
    try:
        from picoware.system.websocket import WebSocketAsync

        _websocket = WebSocketAsync(str(url))
        return bool(_websocket.connect())
    except Exception:
        _websocket = None
        return False


def http_websocket_stop():
    global _websocket
    if _websocket is None:
        return False
    try:
        _websocket.close()
        return True
    finally:
        _websocket = None


def http_websocket_send(message):
    if _websocket is None:
        return False
    try:
        return bool(_websocket.send(str(message)))
    except Exception:
        return False


def http_websocket_is_connected():
    if _websocket is None:
        return False
    try:
        return bool(_websocket.is_connected)
    except Exception:
        return False


def http_get_websocket_response(buffer=None, buffer_size=0):
    if _websocket is None:
        return False
    value = _websocket.last_received
    if value is None:
        return False
    text = str(value)
    if buffer is not None:
        data = text[: int(buffer_size or len(text))]
        try:
            buffer[: len(data)] = data
        except Exception:
            pass
    return text
