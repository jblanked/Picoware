"""BLE UART Chat - Send and receive messages over BLE UART service"""

from micropython import const

_bluetooth = None
_menu = None
_loading = None
_messages = []  # List of (is_sent, text)
_scanned_devices = []
_addresses = []
_selected_device = None
_typing_needs_draw = False

# States
STATE_MODE_SELECT = const(0)
STATE_SCANNING = const(1)
STATE_DEVICE_LIST = const(2)
STATE_CONNECTING = const(3)
STATE_CHAT = const(4)
STATE_TYPING = const(5)
STATE_PERIPHERAL_WAIT = const(6)
STATE_CONNECTION_ERROR = const(7)
DISCOVERY_TIMEOUT_MS = const(15000)

_state = STATE_MODE_SELECT
_mode = None  # "central" or "peripheral"
_last_update = 0
_connection_error = ""
_service_discovery_pending = False
_service_done_pending = False
_service_done_status = 0
_characteristics_pending = None
_characteristics_done_pending = False
_characteristics_done_status = 0
_discovery_started = None
_connect_started = None
_subscribe_pending = False
_connect_stage = "Connecting..."


def _show_mode_select(view_manager) -> None:
    """Reset the screen and menu to BLE mode selection."""
    from picoware.gui.menu import Menu

    global _menu, _loading, _state, _mode, _connection_error, _typing_needs_draw
    global _subscribe_pending, _connect_stage

    if _loading is not None:
        _loading.stop()
        _loading = None
    if _menu is not None:
        del _menu

    _menu = Menu(
        view_manager.draw,
        "UART Chat",
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
        2,
    )
    _menu.add_item("Central (Connect)")
    _menu.add_item("Peripheral (Wait)")
    _menu.draw()

    _state = STATE_MODE_SELECT
    _mode = None
    _connection_error = ""
    _typing_needs_draw = False
    _subscribe_pending = False
    _connect_stage = "Connecting..."


def __addr_to_str(addr) -> str:
    """Convert address bytes to a colon-separated string.

    Args:
        addr (bytes): The device address bytes.

    Returns:
        str: The formatted address string.
    """
    return ":".join("{:02X}".format(b) for b in addr)


def on_data_received(data):
    """Store an incoming chat message.

    Args:
        data (bytes): Raw data received over BLE.
    """
    global _messages
    if isinstance(data, str):
        text = data.strip()
    else:
        payload = bytes(data)
        try:
            text = payload.decode("utf-8").strip()
        except UnicodeError:
            text = payload.hex()
    if text:
        _messages.append((False, text))
        # Keep last 20 messages
        if len(_messages) > 20:
            _messages = _messages[-20:]


def bluetooth_callback(event, data):
    """Handle Bluetooth connection and scan events.

    Args:
        event (int): Bluetooth event code.
        data (tuple): Event payload.
    """
    global _state, _addresses, _connection_error
    global _service_discovery_pending, _characteristics_pending, _discovery_started
    global _connect_started, _subscribe_pending, _connect_stage
    global _service_done_pending, _service_done_status
    global _characteristics_done_pending, _characteristics_done_status

    if event == 5:  # _IRQ_SCAN_RESULT
        addr_type, addr, adv_type, rssi, adv_data = data
        addr_str = __addr_to_str(addr)
        name = _bluetooth.decode_name(adv_data)

        if addr_str in _addresses:
            index = _addresses.index(addr_str)
            _, _, old_name, _ = _scanned_devices[index]
            _scanned_devices[index] = (
                addr_type,
                bytes(addr),
                name or old_name,
                rssi,
            )
            return

        _addresses.append(addr_str)
        _scanned_devices.append((addr_type, bytes(addr), name, rssi))

        if _menu is not None and _state == STATE_SCANNING:
            display = name if name else addr_str[:17]
            _menu.add_item(f"{display}")

    elif event == 6:  # _IRQ_SCAN_DONE
        _addresses.clear()
        if _menu is not None:
            _menu.clear()
            for addr_type, addr, name, rssi in _scanned_devices:
                display = name if name else __addr_to_str(addr)[:17]
                _menu.add_item(f"{display}")
        if _state == STATE_SCANNING:
            _state = STATE_DEVICE_LIST

    elif event == 7 and _mode == "central":  # _IRQ_PERIPHERAL_CONNECT
        _state = STATE_CONNECTING
        _service_discovery_pending = True
        _service_done_pending = False
        _characteristics_pending = None
        _characteristics_done_pending = False
        _subscribe_pending = False
        _discovery_started = None
        _connect_started = None
        _connect_stage = "Discovering services..."

    elif event == 8 and _mode == "central":  # _IRQ_PERIPHERAL_DISCONNECT
        _service_discovery_pending = False
        _service_done_pending = False
        _characteristics_pending = None
        _characteristics_done_pending = False
        _discovery_started = None
        _connect_started = None
        if _state in (
            STATE_CONNECTING,
            STATE_CHAT,
            STATE_TYPING,
        ):
            _connection_error = (
                "Connection failed"
                if _state == STATE_CONNECTING
                else "Connection lost"
            )
            _state = STATE_CONNECTION_ERROR

    elif event == 1 and _mode == "peripheral":  # _IRQ_CENTRAL_CONNECT (peripheral mode)
        _state = STATE_CHAT

    elif event == 2 and _mode == "peripheral":  # _IRQ_CENTRAL_DISCONNECT
        _state = STATE_PERIPHERAL_WAIT

    elif event == 28 and _mode == "peripheral":  # _IRQ_ENCRYPTION_UPDATE
        _state = STATE_CHAT

    elif event == 31:  # _IRQ_PASSKEY_ACTION
        pass

    elif event == 10 and _mode == "central":  # _IRQ_GATTC_SERVICE_DONE
        _, _service_done_status = data
        _service_done_pending = True
        _service_discovery_pending = False

    elif event == 12 and _mode == "central":  # _IRQ_GATTC_CHARACTERISTIC_DONE
        _, _characteristics_done_status = data
        _characteristics_done_pending = True
        _characteristics_pending = None
        _discovery_started = None


def start(view_manager) -> bool:
    """Start the UART Chat app and show the mode menu.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        bool: True if the app started, False on failure.
    """
    global _bluetooth, _menu, _state, _messages, _scanned_devices, _addresses, _mode
    global _connection_error, _service_discovery_pending
    global _characteristics_pending, _discovery_started, _connect_started
    global _typing_needs_draw, _subscribe_pending, _connect_stage
    global _service_done_pending, _service_done_status
    global _characteristics_done_pending, _characteristics_done_status
    global _last_update

    from picoware.system.bluetooth import get_persistent_connection

    persistent_connection = get_persistent_connection()

    # Cleanup
    if _bluetooth is not None and _bluetooth is not persistent_connection:
        if _bluetooth.is_connected or _bluetooth.is_peripheral_connected:
            _bluetooth.disconnect()
        del _bluetooth
        _bluetooth = None
    if _menu is not None:
        del _menu
        _menu = None

    _messages = []
    _scanned_devices = []
    _addresses = []
    _state = STATE_MODE_SELECT
    _mode = None
    _connection_error = ""
    _typing_needs_draw = False
    _last_update = 0
    _service_discovery_pending = False
    _service_done_pending = False
    _service_done_status = 0
    _characteristics_pending = None
    _characteristics_done_pending = False
    _characteristics_done_status = 0
    _discovery_started = None
    _connect_started = None
    _subscribe_pending = False
    _connect_stage = "Connecting..."

    _show_mode_select(view_manager)

    if persistent_connection is not None:
        _bluetooth = persistent_connection
        _bluetooth.callback = bluetooth_callback
        _bluetooth.on_notify(on_data_received)
        _mode = "central"

        uart_uuid = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
        uart_service = next(
            (
                service
                for service in _bluetooth.services
                if uart_uuid.lower() in str(service[2]).lower()
            ),
            None,
        )
        if _bluetooth.is_discovering_services:
            _connect_stage = "Discovering services..."
            _state = STATE_CONNECTING
        elif not _bluetooth.services:
            _service_discovery_pending = True
            _connect_stage = "Discovering services..."
            _state = STATE_CONNECTING
        elif uart_service is None:
            _connection_error = "Connected device has no UART service"
            _state = STATE_CONNECTION_ERROR
        elif _bluetooth.is_uart_ready():
            _connect_stage = "Subscribing..."
            _subscribe_pending = True
            _state = STATE_CONNECTING
        else:
            _characteristics_pending = (uart_service[0], uart_service[1])
            _connect_stage = "Discovering UART..."
            _state = STATE_CONNECTING

    return True


def run(view_manager) -> None:
    """Run the app and handle chat state input.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )
    from picoware.system.bluetooth import Bluetooth
    from utime import ticks_ms, ticks_diff

    global _state, _mode, _bluetooth, _menu, _loading, _connection_error
    global _selected_device, _scanned_devices, _addresses, _last_update
    global _typing_needs_draw
    global _service_discovery_pending, _characteristics_pending, _discovery_started
    global _connect_started, _subscribe_pending, _connect_stage
    global _service_done_pending, _service_done_status
    global _characteristics_done_pending, _characteristics_done_status

    button: int = view_manager.button
    if _bluetooth is not None:
        _bluetooth.flush_secrets()

    # Handle back button
    if button == BUTTON_BACK:
        if _state == STATE_TYPING:
            _state = STATE_CHAT
            view_manager.keyboard.reset()
            _typing_needs_draw = False
            return
        if _state == STATE_CHAT:
            if _bluetooth:
                if _mode == "peripheral":
                    for conn_handle in list(_bluetooth.central_connections):
                        _bluetooth.disconnect(conn_handle)
                    _bluetooth.stop_peripheral()
                else:
                    _bluetooth.disconnect()
            _show_mode_select(view_manager)
            return
        if _state == STATE_CONNECTION_ERROR:
            if _bluetooth and _mode == "peripheral":
                _bluetooth.stop_peripheral()
            elif _bluetooth and _bluetooth.is_connected:
                from picoware.system.bluetooth import get_persistent_connection

                if get_persistent_connection() is not _bluetooth:
                    _bluetooth.disconnect()
            _show_mode_select(view_manager)
            return
        if _state in (STATE_SCANNING, STATE_DEVICE_LIST, STATE_PERIPHERAL_WAIT):
            if _bluetooth:
                if _bluetooth.is_scanning:
                    _bluetooth.scan_stop()
                if _mode == "peripheral":
                    _bluetooth.stop_peripheral()
            _show_mode_select(view_manager)
            return
        view_manager.back()
        return

    # State: Mode Selection
    if _state == STATE_MODE_SELECT:
        if button in (BUTTON_UP, BUTTON_LEFT):
            _menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            _menu.scroll_down()
        elif button == BUTTON_CENTER:
            _bluetooth = Bluetooth(storage=view_manager.storage)
            _bluetooth.callback = bluetooth_callback

            if _menu.selected_index == 0:
                from picoware.gui.menu import Menu

                # Central mode - scan for devices
                _mode = "central"
                _bluetooth.on_notify(on_data_received)
                _scanned_devices = []
                _addresses = []

                # Create device list menu
                del _menu
                _menu = Menu(
                    view_manager.draw,
                    "Select Device",
                    0,
                    view_manager.draw.size.y,
                    view_manager.foreground_color,
                    view_manager.background_color,
                    view_manager.selected_color,
                    view_manager.foreground_color,
                    2,
                )

                if _loading is None:
                    from picoware.gui.loading import Loading

                    _loading = Loading(
                        view_manager.draw,
                        view_manager.foreground_color,
                        view_manager.background_color,
                    )
                else:
                    _loading.stop()
                _loading.text = "Scanning..."
                _state = STATE_SCANNING
                _bluetooth.scan()
            else:
                # Peripheral mode - wait for connection
                _mode = "peripheral"
                _bluetooth.on_write(on_data_received)
                _state = STATE_PERIPHERAL_WAIT
                if not _bluetooth.start_peripheral(name="Picoware-Chat"):
                    _state = STATE_CONNECTION_ERROR
                    _connection_error = "Could not start peripheral"
        return

    # State: Scanning
    if _state == STATE_SCANNING:
        if _loading:
            _loading.animate()
        return

    # State: Device List
    if _state == STATE_DEVICE_LIST:
        if _loading:
            del _loading
            _loading = None

        if _menu.item_count == 0:
            view_manager.alert("No devices found.", True)
            return

        _menu.draw()

        if button in (BUTTON_UP, BUTTON_LEFT):
            _menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            _menu.scroll_down()
        elif button == BUTTON_CENTER:
            idx = _menu.selected_index
            if 0 <= idx < len(_scanned_devices):
                _selected_device = _scanned_devices[idx]
                addr_type, addr, _, _ = _selected_device
                _service_discovery_pending = False
                _service_done_pending = False
                _characteristics_pending = None
                _characteristics_done_pending = False
                _subscribe_pending = False
                _discovery_started = None
                _connect_started = ticks_ms()
                _connect_stage = "Connecting..."
                _state = STATE_CONNECTING
                if not _bluetooth.connect(
                    addr_type, addr, auto_discover=False
                ):
                    _connect_started = None
                    _connection_error = "Could not start connection"
                    _state = STATE_CONNECTION_ERROR
        return

    # State: Connecting
    if _state == STATE_CONNECTING:
        if (
            _connect_started is not None
            and ticks_diff(ticks_ms(), _connect_started) >= 10000
        ):
            _connect_started = None
            _connection_error = "Connection timed out"
            _state = STATE_CONNECTION_ERROR
            return

        if _service_discovery_pending:
            _service_discovery_pending = False
            _discovery_started = ticks_ms()
            if not _bluetooth.discover_services():
                _discovery_started = None
                _connection_error = "Could not start service discovery"
                _state = STATE_CONNECTION_ERROR
                return
        elif _bluetooth.is_discovering_services and _discovery_started is None:
            _discovery_started = ticks_ms()

        if _service_done_pending:
            _service_done_pending = False
            _discovery_started = None
            print(
                f"[UART] Processing service results: status="
                f"{_service_done_status}, count={len(_bluetooth.services)}"
            )
            if _service_done_status != 0:
                _connection_error = "Service discovery failed"
                _state = STATE_CONNECTION_ERROR
                return
            uart_uuid = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
            uart_service = None
            for service in _bluetooth.services:
                if uart_uuid.lower() in str(service[2]).lower():
                    uart_service = service
                    break
            if uart_service is None:
                _connection_error = "UART service not found"
                _state = STATE_CONNECTION_ERROR
                return
            _characteristics_pending = (uart_service[0], uart_service[1])
            _connect_stage = "Discovering UART..."

        if _characteristics_pending is not None:
            start_handle, end_handle = _characteristics_pending
            _characteristics_pending = None
            _discovery_started = ticks_ms()
            print(
                f"[UART] Requesting characteristic discovery "
                f"{start_handle}-{end_handle}"
            )
            if not _bluetooth.discover_characteristics(
                start_handle, end_handle
            ):
                _discovery_started = None
                _connection_error = "Could not start UART characteristic discovery"
                _state = STATE_CONNECTION_ERROR
                return

        if _characteristics_done_pending:
            _characteristics_done_pending = False
            _discovery_started = None
            print(
                f"[UART] Processing characteristic results: "
                f"status={_characteristics_done_status}, "
                f"ready={_bluetooth.is_uart_ready()}"
            )
            if _characteristics_done_status != 0:
                _connection_error = "UART characteristic discovery failed"
                _state = STATE_CONNECTION_ERROR
                return
            if not _bluetooth.is_uart_ready():
                _connection_error = "UART characteristics not found"
                _state = STATE_CONNECTION_ERROR
                return
            _subscribe_pending = True
            _connect_stage = "Subscribing..."

        if _subscribe_pending:
            _subscribe_pending = False
            if _bluetooth.subscribe():
                _state = STATE_CHAT
                _connection_error = ""
                print("[UART] Chat ready")
            else:
                _connection_error = "Could not subscribe to UART notifications"
                _state = STATE_CONNECTION_ERROR
            return

        if _state != STATE_CONNECTING:
            return
        if (
            _discovery_started is not None
            and ticks_diff(ticks_ms(), _discovery_started)
            >= DISCOVERY_TIMEOUT_MS
        ):
            _discovery_started = None
            _connection_error = "UART discovery timed out"
            _state = STATE_CONNECTION_ERROR
            return

        if _loading is None:
            from picoware.gui.loading import Loading

            _loading = Loading(
                view_manager.draw,
                view_manager.foreground_color,
                view_manager.background_color,
            )
        _loading.text = _connect_stage
        _loading.animate()
        return

    if _state == STATE_CONNECTION_ERROR:
        draw = view_manager.draw
        draw.erase()
        fg = draw.foreground
        draw._text(5, 5, "UART connection failed", fg)
        draw._text(5, 5 + draw.font_size.y, _connection_error[:30], fg)
        draw._text(5, draw.size.y - draw.font_size.y, "BACK: Return", fg)
        draw.swap()
        return

    # State: Peripheral waiting
    if _state == STATE_PERIPHERAL_WAIT:
        now = ticks_ms()
        if ticks_diff(now, _last_update) < 500:
            return
        _last_update = now

        draw = view_manager.draw
        draw.erase()
        _font_size = draw.font_size.y
        fg = draw.foreground
        draw._text(5, 5, "UART Chat - Peripheral", fg)
        draw._text(5, 5 + _font_size, "Waiting for connection...", fg)
        draw._text(5, 5 + 2 * _font_size, "Name: Picoware-Chat", fg)
        draw._text(5, 5 + 3 * _font_size, f"MAC: {_bluetooth.mac_address}", fg)
        draw._text(5, draw.size.y - draw.font_size.y, "BACK: Cancel", fg)
        draw.swap()
        return

    # State: Chat
    if _state == STATE_CHAT:
        if _loading:
            del _loading
            _loading = None

        if button == BUTTON_CENTER:
            _keyboard = view_manager.keyboard
            _keyboard.reset()
            _typing_needs_draw = True
            _state = STATE_TYPING
            return

        now = ticks_ms()
        if ticks_diff(now, _last_update) < 100:
            return
        _last_update = now

        draw = view_manager.draw
        draw.clear()

        # Header
        mode_str = "Central" if _mode == "central" else "Peripheral"
        fg = draw.foreground
        draw._text(5, 5, f"Chat ({mode_str})", fg)

        # On short displays, show the newest messages that fit above the footer.
        font_height = draw.font_size.y
        line_height = max(font_height + 2, 1)
        messages_top = max(20, 5 + 2 * font_height)
        messages_bottom = draw.size.y - 2 * font_height - 2
        visible_count = max(0, (messages_bottom - messages_top) // line_height)
        if visible_count:
            visible_messages = _messages[-min(8, visible_count) :]
        else:
            visible_messages = []

        y = messages_top + max(
            0, (visible_count - len(visible_messages)) * line_height
        )
        max_text_width = max(draw.size.x - 10, 1)
        for is_sent, text in visible_messages:
            msg = ("> " if is_sent else "< ") + text
            while msg and draw.len(msg) > max_text_width:
                msg = msg[:-1]
            draw._text(5, y, msg, fg)
            y += line_height

        # Footer
        draw._text(5, draw.size.y - draw.font_size.y * 2, "CENTER: Type message", fg)
        draw._text(5, draw.size.y - draw.font_size.y, "BACK: Disconnect", fg)
        draw.swap()

        return

    # State: Typing
    if _state == STATE_TYPING:
        _keyboard = view_manager.keyboard
        force_draw = _typing_needs_draw
        _typing_needs_draw = False
        if not _keyboard.run(force=force_draw):
            _state = STATE_CHAT
            _keyboard.reset()
            return
        if _keyboard.is_finished:
            result = _keyboard.response
            # Message entered
            if result:
                _messages.append((True, result))
                if _mode == "central":
                    _bluetooth.write(result)
                else:
                    _bluetooth.send(result)

            _keyboard.reset()
            _typing_needs_draw = False
            _state = STATE_CHAT
            return


def stop(view_manager) -> None:
    """Stop the app and clean up the BLE connection.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from gc import collect

    global _bluetooth, _menu, _loading, _messages
    global _scanned_devices, _addresses, _selected_device, _state, _mode
    global _typing_needs_draw, _connection_error

    if _bluetooth is not None:
        if _bluetooth.is_connected or _bluetooth.is_peripheral_connected:
            _bluetooth.disconnect()
        _bluetooth.stop_peripheral()
        del _bluetooth
        _bluetooth = None

    if _menu is not None:
        del _menu
        _menu = None

    if _loading is not None:
        del _loading
        _loading = None

    view_manager.keyboard.reset()

    _messages = []
    _scanned_devices = []
    _addresses = []
    _selected_device = None
    _state = STATE_MODE_SELECT
    _mode = None
    _typing_needs_draw = False
    _connection_error = ""

    collect()
