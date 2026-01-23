from micropython import const
from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_CENTER,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
)

# App states
STATE_DISCONNECTED = const(0)
STATE_CONNECTING = const(1)
STATE_CONNECTED = const(2)
STATE_ERROR = const(3)

# Globals
_ws = None
_textbox = None
_current_state = STATE_DISCONNECTED
_messages = []
_message_count = 0
_should_update = False


def _add_message(msg: str) -> None:
    """Add a message to the display buffer."""
    global _messages, _should_update
    _messages.append(msg)
    # Keep only last 10 messages to save memory
    if len(_messages) > 10:
        _messages = _messages[-10:]
    _should_update = True


def _update_display() -> None:
    """Update the textbox display with current state and messages."""
    global _textbox, _current_state, _ws, _messages

    status = "Unknown"
    if _current_state == STATE_CONNECTING:
        status = "Connecting..."
    elif _current_state == STATE_CONNECTED:
        status = "Connected"
    elif _current_state == STATE_ERROR:
        error_msg = _ws.error if _ws else "Unknown error"
        status = f"Error: {error_msg}"
    elif _current_state == STATE_DISCONNECTED:
        status = "Disconnected"

    text = "WebSocket Echo Test\n"
    text += f"Status: {status}\n"
    text += "─-------------------\n"
    text += "Controls:\n"
    text += "CENTER - Send message\n"
    text += "UP - Send ping\n"
    text += "BACK - Exit\n"
    text += "─-------------------\n"
    text += "Messages:\n"

    for msg in _messages:
        text += f"{msg}\n"

    if _textbox:
        _textbox.set_text(text)


def _connect_websocket(view_manager) -> bool:
    """Establish WebSocket connection."""
    global _ws, _current_state, _should_update

    from picoware.system.websocket import WebSocketAsync

    _current_state = STATE_CONNECTING
    _should_update = True

    url = "wss://echo.websocket.org"
    _add_message(f"Connecting to {url}...")

    try:
        _ws = WebSocketAsync(
            url, callback=callback, thread_manager=view_manager.thread_manager
        )
        if not _ws.connect():
            _current_state = STATE_ERROR
            _add_message(f"Failed to connect: {_ws.error}")
            return False
        _current_state = STATE_CONNECTED
        return True
    except Exception as e:
        _current_state = STATE_ERROR
        _add_message(f"Failed: {e}")
        return False


def _send_message() -> None:
    """Send a test message to the WebSocket server."""
    global _ws, _message_count

    if not _ws or not _ws.is_connected:
        _add_message("Not connected!")
        return

    _message_count += 1
    message = f"Hello from Picoware! #{_message_count}"
    _add_message(f">>> {message}")

    if _ws.send(message):
        pass  # Message sent, will receive echo
    else:
        _add_message(f"Send failed: {_ws.error}")


def _send_ping() -> None:
    """Send a ping to the server."""
    global _ws

    if not _ws or not _ws.is_connected:
        _add_message("Not connected!")
        return

    _add_message(">>> PING")
    if _ws.ping(b"PING"):
        pass  # Ping sent
    else:
        _add_message(f"Ping failed: {_ws.error}")


def callback(data) -> None:
    """Check for and process incoming WebSocket messages."""
    global _ws, _current_state, _should_update

    if not _ws or not _ws.is_connected:
        return

    from picoware.system.websocket import ConnectionClosed, NoDataException

    try:
        if data is not None and data != "":
            _add_message(f"<<< {data}")
        elif data is None:
            # Connection closed by server
            _add_message("<<< Server closed connection")
            _current_state = STATE_DISCONNECTED
    except ConnectionClosed:
        _add_message("<<< Connection closed")
        _current_state = STATE_DISCONNECTED
    except NoDataException:
        pass
    except OSError:
        pass

    _should_update = True


def start(view_manager) -> bool:
    """Start the WebSocket test app."""
    global _textbox, _messages, _message_count, _current_state, _ws, _should_update

    # Check WiFi
    wifi = view_manager.wifi
    if not wifi:
        view_manager.alert("WiFi not available...", False)
        return False

    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        view_manager.alert("WiFi not connected yet.")
        connect_to_saved_wifi(view_manager)
        return False

    # Initialize UI
    from picoware.gui.textbox import TextBox

    if _textbox:
        del _textbox
        _textbox = None

    _messages = []
    _message_count = 0
    _current_state = STATE_DISCONNECTED
    _ws = None
    _should_update = False

    _textbox = TextBox(
        view_manager.draw,
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
    )

    _update_display()

    # Connect to WebSocket
    return _connect_websocket(view_manager)


def run(view_manager) -> None:
    """Main run loop for the app."""
    global _current_state, _should_update

    if not _textbox:
        return

    input_manager = view_manager.input_manager
    button = input_manager.button

    # Handle input
    if button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()
        return

    if button == BUTTON_CENTER:
        input_manager.reset()
        _send_message()
    elif button == BUTTON_UP:
        input_manager.reset()
        _send_ping()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        input_manager.reset()
        _textbox.scroll_down()
    elif button == BUTTON_LEFT:
        input_manager.reset()
        _textbox.scroll_up()

    if _should_update:
        _update_display()
        _update_display()  # second time for callback
        _should_update = False


def stop(view_manager) -> None:
    """Stop the app and clean up resources."""
    from gc import collect

    global _ws, _textbox, _messages, _current_state, _should_update
    if _ws is not None:
        _ws.close()
        del _ws
        _ws = None

    if _textbox is not None:
        del _textbox
        _textbox = None

    _messages = []
    _current_state = STATE_DISCONNECTED
    _should_update = False

    collect()
