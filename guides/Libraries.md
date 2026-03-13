# Libraries
This section provides documentation for the libraries available in Picoware.

## Table of Contents
- [MicroPython](#micropython)
- [SDK](#sdk)

## MicroPython

### Table of Contents
- [System](#system)
  - [picoware.system.app](#picoware-system-app)
  - [picoware.system.app_loader](#picoware-system-app_loader)
  - [picoware.system.auto_complete](#picoware-system-auto_complete)
  - [picoware.system.bluetooth](#picoware-system-bluetooth)
  - [picoware.system.boards](#picoware-system-boards)
  - [picoware.system.buttons](#picoware-system-buttons)
  - [picoware.system.colors](#picoware-system-colors)
  - [picoware.system.font](#picoware-system-font)
  - [picoware.system.http](#picoware-system-http)
  - [picoware.system.input](#picoware-system-input)
  - [picoware.system.LED](#picoware-system-led)
  - [picoware.system.log](#picoware-system-log)
  - [picoware.system.psram](#picoware-system-psram)
  - [picoware.system.response](#picoware-system-response)
  - [picoware.system.storage](#picoware-system-storage)
  - [picoware.system.system](#picoware-system-system)
  - [picoware.system.thread](#picoware-system-thread)
  - [picoware.system.time](#picoware-system-time)
  - [picoware.system.uart](#picoware-system-uart)
  - [picoware.system.vector](#picoware-system-vector)
  - [picoware.system.view](#picoware-system-view)
  - [picoware.system.view_manager](#picoware-system-view_manager)
  - [picoware.system.websocket](#picoware-system-websocket)
  - [picoware.system.wifi](#picoware-system-wifi)
- [GUI](#gui)
  - [picoware.gui.alert](#picoware-gui-alert)
  - [picoware.gui.choice](#picoware-gui-choice)
  - [picoware.gui.date_picker](#picoware-gui-date_picker)
  - [picoware.gui.desktop](#picoware-gui-desktop)
  - [picoware.gui.draw](#picoware-gui-draw)
  - [picoware.gui.file_browser](#picoware-gui-file_browser)
  - [picoware.gui.image](#picoware-gui-image)
  - [picoware.gui.jpeg](#picoware-gui-jpeg)
  - [picoware.gui.keyboard](#picoware-gui-keyboard)
  - [picoware.gui.list](#picoware-gui-list)
  - [picoware.gui.loading](#picoware-gui-loading)
  - [picoware.gui.menu](#picoware-gui-menu)
  - [picoware.gui.scrollbar](#picoware-gui-scrollbar)
  - [picoware.gui.textbox](#picoware-gui-textbox)
  - [picoware.gui.toggle](#picoware-gui-toggle)
  - [picoware.gui.toggle_list](#picoware-gui-toggle_list)
- [Engine](#engine)
  - [picoware.engine.camera](#picoware-engine-camera)
  - [picoware.engine.engine](#picoware-engine-engine)
  - [picoware.engine.entity](#picoware-engine-entity)
  - [picoware.engine.game](#picoware-engine-game)
  - [picoware.engine.image](#picoware-engine-image)
  - [picoware.engine.level](#picoware-engine-level)
  - [picoware.engine.sprite3d](#picoware-engine-sprite3d)
  - [picoware.engine.triangle3d](#picoware-engine-triangle3d)

### System

#### picoware-system-app
- `App` class: An object wrapping an app manifest dictionary.
    - `__init__(manifest)`: Initializes the App with a manifest dict. Reads keys: authors, description, download_url, file_downloads, file_structure, github_url, icon_url, id, title, version.
    - `__str__()`: Returns `"App(id=..., title='...', version='...')"`.
    - `authors`: Property — list of author strings.
    - `description`: Property — app description string.
    - `download_url`: Property — download URL string.
    - `file_downloads`: Property — list of file download dicts.
    - `file_structure`: Property — list of file path strings.
    - `github_url`: Property — GitHub URL string.
    - `icon_url`: Property — icon URL string.
    - `id`: Property — app ID integer.
    - `json`: Property — the original manifest dict.
    - `title`: Property — app title string.
    - `version`: Property — version string.

#### picoware-system-app_loader
- `AppLoader` class: Dynamically loads and manages apps from the SD card.
    - `__init__(view_manager)`: Initializes the loader, mounts `/sd` VFS.
    - `cleanup_modules()`: Removes loaded app modules from `sys.modules` and forces garbage collection.
    - `list_available_apps(subdirectory="")`: Lists `.py`/`.mpy` files in `/picoware/apps`. Returns a list of filename strings.
    - `list_loaded_apps()`: Returns a list of currently loaded app keys.
    - `load_app(app_name, subdirectory="")`: Dynamically imports an app module; validates that it has `start`, `run`, and `stop` functions.
    - `run()`: Calls `current_app.run(view_manager)`.
    - `start(app_name)`: Stops the current app, loads and starts a new one. Returns True on success.
    - `stop()`: Calls `current_app.stop(view_manager)`.
    - `switch_app(app_name)`: Alias for `start(app_name)`.

#### picoware-system-auto_complete
- `AutoComplete` class: Wraps the C `auto_complete` module to provide word completion.
    - `__init__()`: Initializes the AutoComplete object.
    - `suggestion_count`: Property — number of current suggestions (int).
    - `suggestions`: Property — tuple of current suggestion strings.
    - `add_words(words)`: Add a list of strings to the word database. Returns the count of words added.

#### picoware-system-bluetooth
- `_IRQ_CENTRAL_CONNECT`: Constant for central connect event (1)
- `_IRQ_CENTRAL_DISCONNECT`: Constant for central disconnect event (2)
- `_IRQ_GATTS_WRITE`: Constant for GATT server write event (3)
- `_IRQ_SCAN_RESULT`: Constant for scan result event (5)
- `_IRQ_SCAN_DONE`: Constant for scan done event (6)
- `_IRQ_PERIPHERAL_CONNECT`: Constant for peripheral connect event (7)
- `_IRQ_PERIPHERAL_DISCONNECT`: Constant for peripheral disconnect event (8)
- `_IRQ_GATTC_SERVICE_RESULT`: Constant for GATT client service result event (9)
- `_IRQ_GATTC_SERVICE_DONE`: Constant for GATT client service done event (10)
- `_IRQ_GATTC_CHARACTERISTIC_RESULT`: Constant for GATT client characteristic result event (11)
- `_IRQ_GATTC_CHARACTERISTIC_DONE`: Constant for GATT client characteristic done event (12)
- `_IRQ_GATTC_DESCRIPTOR_RESULT`: Constant for GATT client descriptor result event (13)
- `_IRQ_GATTC_DESCRIPTOR_DONE`: Constant for GATT client descriptor done event (14)
- `_IRQ_GATTC_READ_RESULT`: Constant for GATT client read result event (15)
- `_IRQ_GATTC_READ_DONE`: Constant for GATT client read done event (16)
- `_IRQ_GATTC_WRITE_DONE`: Constant for GATT client write done event (17)
- `_IRQ_GATTC_NOTIFY`: Constant for GATT client notify event (18)
- `_IRQ_GATTC_INDICATE`: Constant for GATT client indicate event (19)
- `_IRQ_GATTS_INDICATE_DONE`: Constant for GATT server indicate done event (20)
- `_IRQ_MTU_EXCHANGED`: Constant for MTU exchanged event (21)
- `_IRQ_ENCRYPTION_UPDATE`: Constant for encryption update event (28)
- `_IRQ_PASSKEY_ACTION`: Constant for passkey action event (31)
- `_PASSKEY_ACTION_NONE`: Constant for no passkey action (0)
- `_PASSKEY_ACTION_INPUT`: Constant for input passkey action (2)
- `_PASSKEY_ACTION_DISPLAY`: Constant for display passkey action (3)
- `_PASSKEY_ACTION_NUMERIC_COMPARISON`: Constant for numeric comparison passkey action (4)
- `_UART_SERVICE_UUID`: Nordic UART Service UUID (`"6E400001-B5A3-F393-E0A9-E50E24DCCA9E"`)
- `_UART_RX_CHAR_UUID`: UART RX characteristic UUID (`"6E400002-B5A3-F393-E0A9-E50E24DCCA9E"`)
- `_UART_TX_CHAR_UUID`: UART TX characteristic UUID (`"6E400003-B5A3-F393-E0A9-E50E24DCCA9E"`)
- `Bluetooth` class: Manages BLE central and peripheral (Nordic UART Service) functionality.
    - `__init__(storage=None)`: Initializes BLE, registers IRQ handler, sets up central and peripheral state. Optional `storage` parameter enables saving paired devices.
    - `callback`: Property to get/set the Bluetooth event callback. Receives `(event, data)`.
    - `central_connections`: Property — set of active central connection handles (peripheral mode).
    - `characteristics`: Property — list of discovered GATT characteristics.
    - `connected_address`: Property — address string of the connected peripheral.
    - `is_connected`: Property — True if connected to a peripheral (central mode).
    - `is_pairing`: Property — True if a pairing/bonding is in progress.
    - `is_peripheral_connected`: Property — True if at least one central is connected to this device (peripheral mode).
    - `is_scanning`: Property — True if a scan is currently running.
    - `mac_address`: Property — MAC address string of this device.
    - `passkey`: Property — current passkey integer during pairing.
    - `services`: Property — list of discovered GATT services.
    - `advertise(interval_us=None, name="Picoware")`: Start or stop BLE advertising. Pass `interval_us=None` to stop.
    - `connect(addr_type, addr, timeout_ms=10000, auto_discover=True)`: Connect to a BLE peripheral. Returns True on success.
    - `decode_name(adv_data)`: Decode a device name from raw advertising data bytes.
    - `disconnect(conn_handle=None)`: Disconnect from a central or peripheral device.
    - `discover_characteristics(start_handle, end_handle)`: Discover characteristics for a service range. Returns True if started.
    - `discover_services()`: Discover services on the connected peripheral. Returns True if started.
    - `is_device_paired(addr)`: Returns True if the address is in the saved paired devices list.
    - `load_paired_devices()`: Load paired device dict from storage. Returns the dict.
    - `on_notify(callback)`: Set a callback for incoming GATTC notifications (central mode).
    - `on_write(callback)`: Set a callback for incoming GATTS writes (peripheral mode).
    - `pair()`: Initiate bonding/pairing with the connected peripheral. Returns True if started.
    - `passkey_reply(accept=True, passkey=None)`: Reply to a passkey action request during pairing.
    - `read(handle)`: Read a GATTC characteristic value. Returns True if started.
    - `register()`: Register this device as a GATT server with a Nordic UART Service. Returns True on success.
    - `remove_paired_device(addr)`: Remove a paired device from storage. Returns True on success.
    - `save_paired_device(addr, name="")`: Save a paired device address and optional name to storage. Returns True on success.
    - `scan(duration_ms=5000, interval_us=30000, window_us=30000, active=True, callback=None)`: Scan for BLE devices. Returns True if started.
    - `scan_stop()`: Stop an ongoing BLE scan.
    - `send(data)`: Send data to all connected centrals (peripheral mode).
    - `start_peripheral(name="Picoware", interval_us=500000)`: Start advertising as a peripheral with the UART service. Returns True on success.
    - `stop_peripheral()`: Stop peripheral advertising and disconnect centrals. Returns True on success.
    - `write(data)`: Write data to the connected peripheral (central mode).

#### picoware-system-boards
- `BOARD_PICOCALC_PICO`: Board ID for PicoCalc with Pico.
- `BOARD_PICOCALC_PICOW`: Board ID for PicoCalc with Pico W.
- `BOARD_PICOCALC_PICO_2`: Board ID for PicoCalc with Pico 2.
- `BOARD_PICOCALC_PICO_2W`: Board ID for PicoCalc with Pico 2W.
- `BOARD_WAVESHARE_1_28_RP2350`: Board ID for Waveshare 1.28" RP2350.
- `BOARD_WAVESHARE_1_43_RP2350`: Board ID for Waveshare 1.43" RP2350.
- `BOARD_WAVESHARE_3_49_RP2350`: Board ID for Waveshare 3.49" RP2350.
- `BOARD_PICOCALC_PIMORONI_2W`: Board ID for PicoCalc with Pimoroni Pico Plus 2W.
- `BOARD_ID`: The current board ID integer (read from C module at import time).
- `BOARD_HAS_PSRAM`: True if the current board has PSRAM.
- `BOARD_HAS_SD`: True if the current board has an SD card slot.
- `BOARD_HAS_TOUCH`: True if the current board has a touch screen.
- `BOARD_HAS_WIFI`: True if the current board has WiFi.

#### picoware-system-buttons
- `BUTTON_NONE`: No button pressed (-1)
- `BUTTON_UART`: UART input source (-2)
- `BUTTON_PICO_CALC`: PicoCalc keyboard source (-3)
- `BUTTON_UP`: Up button (0)
- `BUTTON_DOWN`: Down button (1)
- `BUTTON_LEFT`: Left button (2)
- `BUTTON_RIGHT`: Right button (3)
- `BUTTON_CENTER`: Center/OK button (4)
- `BUTTON_OK`: Alias for `BUTTON_CENTER` (4)
- `BUTTON_BACK`: Back button (5)
- `BUTTON_START`: Start button (6)
- `BUTTON_A` through `BUTTON_Z`: Alphabet buttons (7–32)
- `BUTTON_0` through `BUTTON_9`: Number buttons (33–42)
- `BUTTON_SPACE` (43), `BUTTON_EXCLAMATION` (44), `BUTTON_AT` (45), `BUTTON_HASH` (46), `BUTTON_DOLLAR` (47), `BUTTON_PERCENT` (48), `BUTTON_CARET` (49), `BUTTON_AMPERSAND` (50), `BUTTON_ASTERISK` (51), `BUTTON_LEFT_PARENTHESIS` (52), `BUTTON_RIGHT_PARENTHESIS` (53), `BUTTON_MINUS` (54), `BUTTON_UNDERSCORE` (55), `BUTTON_PLUS` (56), `BUTTON_EQUAL` (57), `BUTTON_LEFT_BRACKET` (58), `BUTTON_RIGHT_BRACKET` (59), `BUTTON_LEFT_BRACE` (60), `BUTTON_RIGHT_BRACE` (61), `BUTTON_SEMICOLON` (62), `BUTTON_COLON` (63), `BUTTON_SINGLE_QUOTE` (64), `BUTTON_DOUBLE_QUOTE` (65), `BUTTON_COMMA` (66), `BUTTON_PERIOD` (67), `BUTTON_SLASH` (68), `BUTTON_BACKSLASH` (69), `BUTTON_LESS_THAN` (70), `BUTTON_GREATER_THAN` (71), `BUTTON_QUESTION` (72): Special character buttons.
- `BUTTON_BACKSPACE` (73), `BUTTON_ENTER` (74), `BUTTON_SHIFT` (75), `BUTTON_CAPS_LOCK` (76), `BUTTON_ESCAPE` (77), `BUTTON_CONTROL` (78), `BUTTON_ALT` (79), `BUTTON_HOME` (80), `BUTTON_DELETE` (81), `BUTTON_TAB` (82), `BUTTON_TILDE` (83), `BUTTON_PIPE` (84), `BUTTON_BACK_TICK` (85): Control and editing buttons.
- `KEY_MOD_ALT` (0xA1), `KEY_MOD_SHL` (0xA2), `KEY_MOD_SHR` (0xA3), `KEY_MOD_SYM` (0xA4), `KEY_MOD_CTRL` (0xA5): Key modifier constants.
- `KEY_ESC` (0xB1), `KEY_UP` (0xB5), `KEY_DOWN` (0xB6), `KEY_LEFT` (0xB4), `KEY_RIGHT` (0xB7): Cursor key constants.
- `KEY_BREAK` (0xD0), `KEY_INSERT` (0xD1), `KEY_HOME` (0xD2), `KEY_DEL` (0xD4), `KEY_END` (0xD5), `KEY_PAGE_UP` (0xD6), `KEY_PAGE_DOWN` (0xD7): Navigation key constants.
- `KEY_CAPS_LOCK` (0xC1): Caps lock key constant.
- `KEY_F1` (0x81) through `KEY_F10` (0x90): Function key constants.

#### picoware-system-colors
- `TFT_WHITE`: White (0xFFFF)
- `TFT_BLACK`: Black (0x0000)
- `TFT_BLUE`: Blue (0x001F)
- `TFT_CYAN`: Cyan (0x07FF)
- `TFT_RED`: Red (0xF800)
- `TFT_LIGHTGREY`: Light grey (0xD69A)
- `TFT_DARKGREY`: Dark grey (0x7BEF)
- `TFT_GREEN`: Green (0x07E0)
- `TFT_DARKCYAN`: Dark cyan (0x03EF)
- `TFT_DARKGREEN`: Dark green (0x03E0)
- `TFT_SKYBLUE`: Sky blue (0x867D)
- `TFT_VIOLET`: Violet (0x915C)
- `TFT_BROWN`: Brown (0x9A60)
- `TFT_TRANSPARENT`: Transparent sentinel (0x0120)
- `TFT_YELLOW`: Yellow (0xFFE0)
- `TFT_ORANGE`: Orange (0xFDA0)
- `TFT_PINK`: Pink (0xFE19)

All color constants are RGB565 format and defined as `micropython.const` integers.

#### picoware-system-font
- `FONT_XTRA_SMALL`: Extra-small font size index (0)
- `FONT_SMALL`: Small font size index (1)
- `FONT_MEDIUM`: Medium font size index (2)
- `FONT_LARGE`: Large font size index (3)
- `FONT_XTRA_LARGE`: Extra-large font size index (4)
- `Font` class: Wraps the C `font.Font` module.
    - `get_character(font_size, char)`: Returns the byte data for a specific character. Returns `bytes`.
    - `get_data(font_size)`: Returns the full byte data for a font size. Returns `bytes`.
    - `get_height(font_size)`: Returns the pixel height of the font. Returns `int`.
    - `get_spacing(font_size)`: Returns the pixel spacing of the font. Returns `int`.
    - `get_width(font_size)`: Returns the pixel width of the font. Returns `int`.
- `FontSize` class: Wraps the C `font.FontSize` object.
    - `height`: Property — pixel height of this font size (int).
    - `size`: Property — font size index (int).
    - `spacing`: Property — pixel spacing (int).
    - `width`: Property — pixel character width (int).

#### picoware-system-http
- `HTTP_IDLE`: Idle state constant (0)
- `HTTP_LOADING`: Loading/in-progress state constant (1)
- `HTTP_ISSUE`: Error state constant (2)
- `HTTP` class: Synchronous and asynchronous HTTP client supporting all major verbs.
    - `__init__(chunk_size=4096, thread_manager=None)`: Initializes the HTTP object. `chunk_size` controls the read buffer size for chunked responses.
    - `callback`: Property to get/set the async completion callback. Receives `(response, state, error)`.
    - `error`: Property — last async error string, if any.
    - `in_progress`: Property — True if an async request is currently running.
    - `is_finished`: Property — True if the last async request has completed.
    - `is_successful`: Property — True if the last async request completed without error.
    - `response`: Property — the `Response` object from the last async request.
    - `state`: Property — current state integer (`HTTP_IDLE`, `HTTP_LOADING`, or `HTTP_ISSUE`).
    - `close()`: Stop any running async thread, clear the response, and reset state.
    - `delete(url, headers=None, timeout=None, save_to_file=None, storage=None)`: Synchronous HTTP DELETE. Returns `Response`.
    - `delete_async(url, headers=None, timeout=None, save_to_file=None, storage=None)`: Asynchronous HTTP DELETE. Returns True if started.
    - `get(url, headers=None, timeout=None, save_to_file=None, storage=None)`: Synchronous HTTP GET. Returns `Response`.
    - `get_async(url, headers=None, timeout=None, save_to_file=None, storage=None)`: Asynchronous HTTP GET. Returns True if started.
    - `head(url, payload, headers=None, timeout=None, save_to_file=None, storage=None)`: Synchronous HTTP HEAD. Returns `Response`.
    - `head_async(url, payload, headers=None, timeout=None, save_to_file=None, storage=None)`: Asynchronous HTTP HEAD. Returns True if started.
    - `is_request_complete()`: Returns True if the async request is complete.
    - `patch(url, payload, headers=None, timeout=None, save_to_file=None, storage=None)`: Synchronous HTTP PATCH. Returns `Response`.
    - `patch_async(url, payload, headers=None, timeout=None, save_to_file=None, storage=None)`: Asynchronous HTTP PATCH. Returns True if started.
    - `post(url, payload, headers=None, timeout=None, save_to_file=None, storage=None)`: Synchronous HTTP POST. Returns `Response`.
    - `post_async(url, payload, headers=None, timeout=None, save_to_file=None, storage=None)`: Asynchronous HTTP POST. Returns True if started.
    - `put(url, payload, headers=None, timeout=None, save_to_file=None, storage=None)`: Synchronous HTTP PUT. Returns `Response`.
    - `put_async(url, payload, headers=None, timeout=None, save_to_file=None, storage=None)`: Asynchronous HTTP PUT. Returns True if started.
    - `read_chunked(s, uart=None, method="GET", save_to_file=None, storage=None)`: Read a chunked Transfer-Encoding body from an open socket. Returns `bytes`.
    - `request(method, url, data=None, json_data=None, headers=None, stream=None, auth=None, timeout=None, parse_headers=True, uart=None, save_to_file=None, storage=None)`: Low-level synchronous HTTP request. Returns `Response`.
    - `request_async(method, url, ...)`: Runs `request()` in a background thread via `ThreadManager`. Returns True if started.

#### picoware-system-input
- `Input` class: Handles keyboard input (PicoCalc) and touch input (Waveshare boards).
    - `__init__()`: Initializes the input system for the current board.
    - `battery`: Property — current battery level as a percentage (0–100). Returns 0 on boards without battery reporting.
    - `button`: Property — last button pressed as a `BUTTON_*` constant integer. Polls the keyboard if needed.
    - `gesture`: Property — last touch gesture (Waveshare boards only).
    - `has_touch_support`: Property — True if the current board supports touch input.
    - `point`: Property — last touch point as an `(x, y)` tuple (Waveshare boards only).
    - `was_capitalized`: Property — True if the last key pressed was a capital letter.
    - `button_to_char(button)`: Convert a `BUTTON_*` constant to its character string representation.
    - `is_held(duration=3)`: Returns True if the last button has been held for at least `duration` frames.
    - `is_pressed()`: Returns True if any key is currently pressed.
    - `on_key_callback(_=None)`: Callback invoked when a new key becomes available.
    - `read()`: Blocking read — waits until a key is pressed and returns the raw key code integer.
    - `read_non_blocking()`: Non-blocking read — returns the raw key code, or -1 if no key is available.
    - `reset()`: Resets all input state (clears the last button, gesture, and touch point).

#### picoware-system-LED
- `LED` class: Controls the onboard LED.
    - `__init__(pin=-1)`: Initializes the LED. If `pin` is -1 (default), uses the standard `"LED"` pin. Otherwise uses the specified GPIO pin number.
    - `blink(duration=0.5)`: Turns the LED on, sleeps for `duration` seconds, then turns it off and sleeps again.
    - `off()`: Turns the LED off.
    - `on()`: Turns the LED on.
    - `toggle()`: Toggles the LED state.

#### picoware-system-log
- `LOG_MODE_REPL`: Log to REPL only (0)
- `LOG_MODE_STORAGE`: Log to file only (1)
- `LOG_MODE_ALL`: Log to both REPL and file (2)
- `LOG_TYPE_NONE`: No log type (-1)
- `LOG_TYPE_INFO`: Info log type (0)
- `LOG_TYPE_WARN`: Warning log type (1)
- `LOG_TYPE_ERROR`: Error log type (2)
- `LOG_TYPE_DEBUG`: Debug log type (3)
- `Log` class: Wraps the C `log.Log` module.
    - `__init__(mode=LOG_MODE_REPL, file_path="picoware/log.txt", reset=False)`: Initializes the logger. If `reset=True`, clears the log file on init.
    - `mode`: Property (r/w) — current log mode integer.
    - `logs`: Property (read-only) — list of all log entries.
    - `log(message, log_type=LOG_TYPE_NONE)`: Append a log entry.
    - `reset()`: Clear all log entries and the log file.

#### picoware-system-psram
- `PSRAMObject` class: Wraps a C `picoware_psram.Object` — a reference to an allocated PSRAM block.
    - `__str__()`: Returns a string description of the object.
    - `__del__()`: Frees the object when garbage collected.
    - `value()`: Returns the stored data.
    - `length()`: Returns the size in bytes.
    - `addr()`: Returns the PSRAM address.
- `PSRAM` class: Wraps the C `picoware_psram.PSRAM` module.
    - `free_heap_size`: Property — free bytes remaining in PSRAM heap.
    - `is_ready`: Property — True if PSRAM hardware is initialized and working.
    - `next_free_addr`: Property — address of the next free PSRAM location.
    - `total_heap_size`: Property — total PSRAM heap size in bytes.
    - `used_heap_size`: Property — bytes currently allocated from PSRAM heap.
    - `from_file(storage, addr, file_path, chunk_size=2048)`: Load a file from SD into PSRAM at `addr`. Returns number of bytes loaded.
    - `malloc(data)`: Alias for `alloc_object(data)` — allocate and store data. Returns a `PSRAMObject`.
    - `memcpy(dest_addr, src_addr, length)`: Alias for `copy()` — copy bytes within PSRAM.
    - `memset(addr, value, length)`: Alias for `fill()` — fill a region with a byte value.

#### picoware-system-response
- `Response` class: Wraps an HTTP response.
    - `__init__(body)`: Initializes with raw body bytes. Sets `content` (bytes) and `text` (str).
    - `close()`: Resets all fields.
    - `json()`: Parses `content` as JSON and returns a dict.
    - `content`: Attribute — raw response body bytes.
    - `text`: Attribute — response body decoded as UTF-8 string.
    - `status_code`: Attribute — HTTP status code integer.
    - `headers`: Attribute — dict of response headers.

#### picoware-system-storage
- `FAT32File` class: Wraps a C `sd_mp.fat32_file` handle (available when `sd_mp` module is present).
    - Properties (from C): `is_open`, `last_entry_read`, `attributes`, `start_cluster`, `current_cluster`, `file_size`, `position`, `dir_entry_sector`, `dir_entry_offset`.
- `Storage` class: SD card file storage using the `sd_mp` / `vfs_mp` C modules.
    - `__init__()`: Initializes the storage and calls `sd_mp.init()`.
    - `active`: Property — True if the SD card is mounted and accessible.
    - `vfs_mounted`: Property — True if the VFS is mounted (enables Python `open()`, `__import__`, etc.).
    - `copy(source_path, destination_path, bytes_per_chunk=2048)`: Copy a file. Returns True on success.
    - `deserialize(json_dict, file_path)`: Write a Python dict as JSON to a file.
    - `execute_script(file_path="/")`: Compile and execute a Python script from the SD card.
    - `exists(path)`: Returns True if the file or directory exists.
    - `file_close(file_obj)`: Close an open `FAT32File`.
    - `file_copy(source_file, destination_path, bytes_per_chunk=2048)`: Copy an open file to a new path. Returns True on success.
    - `file_move(source_file, destination_path, bytes_per_chunk=2048)`: Move an open file to a new path. Returns True on success.
    - `file_open(file_path)`: Open a file and return a `FAT32File` handle.
    - `file_read(file_obj, index=0, count=0, decode=True)`: Read from an open file. Returns str or bytes.
    - `file_readinto(file_obj, buffer)`: Read from an open file into a `bytearray`. Returns bytes read.
    - `file_seek(file_obj, position)`: Seek to a byte position in an open file. Returns True on success.
    - `file_write(file_obj, data, mode="w")`: Write data to an open file. Returns True on success.
    - `is_directory(path)`: Returns True if the path is a directory.
    - `listdir(path="")`: Returns a list of filename strings in the directory.
    - `mkdir(path)`: Creates a directory. Returns True on success.
    - `mount()`: Mount the SD card. Returns True on success.
    - `mount_vfs(mount_point="/sd")`: Mount the SD card as a VFS at `mount_point`. Returns True on success.
    - `move(source_path, destination_path)`: Move/rename a file or directory. Returns True on success.
    - `read(file_path, mode="r", index=0, count=0)`: Read a file and return its contents as str or bytes.
    - `read_chunked(file_path, start=0, chunk_size=1024)`: Read a portion of a file without loading all of it. Returns bytes.
    - `read_directory(path="")`: Returns a list of dicts, each with keys: `filename`, `size`, `date`, `time`, `attributes`, `is_directory`.
    - `readinto(file_path, buffer)`: Read a file into a `bytearray`. Returns bytes read.
    - `remove(file_path)`: Delete a file. Returns True on success.
    - `rename(old_path, new_path)`: Rename a file or directory. Returns True on success.
    - `rmdir(path)`: Remove a directory. Returns True on success.
    - `serialize(file_path)`: Read a file and parse its contents as JSON. Returns a dict.
    - `size(file_path)`: Returns the file size in bytes.
    - `unmount()`: Unmount the SD card. Returns True on success.
    - `unmount_vfs(mount_point="/sd")`: Unmount the VFS. Returns True on success.
    - `write(file_path, data, mode="w")`: Write data to a file, creating or overwriting as needed. Returns True on success.

#### picoware-system-system
- `System` class: Provides device information and system control operations.
    - `__init__()`: No-op initializer.
    - `board_id`: Property — current board ID integer (matches a `BOARD_*` constant).
    - `board_name`: Property — board name string (e.g. `"Pico W"`).
    - `device_name`: Property — device name string (e.g. `"PicoCalc"`).
    - `free_flash`: Property — free flash memory in bytes.
    - `free_heap`: Property — free heap RAM in bytes.
    - `free_psram`: Property — free PSRAM in bytes (0 if no PSRAM).
    - `has_psram`: Property — True if the board has PSRAM.
    - `has_sd_card`: Property — True if the board has an SD card slot.
    - `has_touch`: Property — True if the board has a touch screen.
    - `has_wifi`: Property — True if the board has WiFi.
    - `is_circular`: Property — True if the display is circular.
    - `total_flash`: Property — total flash memory in bytes.
    - `total_heap`: Property — total heap RAM in bytes.
    - `total_psram`: Property — total PSRAM in bytes.
    - `used_flash`: Property — used flash memory in bytes.
    - `used_heap`: Property — used heap RAM in bytes.
    - `used_psram`: Property — used PSRAM in bytes.
    - `version`: Property — Picoware firmware version string (e.g. `"1.7.2"`).
    - `bootloader_mode()`: Reboots the device into the UF2 bootloader.
    - `hard_reset()`: Performs a hard reset (`machine.reset()`).
    - `shutdown_device(view_manager=None)`: Powers off the device (requires southbridge support).
    - `soft_reset()`: Performs a soft reset (`machine.soft_reset()`).

#### picoware-system-thread
- `Thread` class: Wraps a single background thread using `_thread`.
    - `__init__(function, args=())`: Stores the function and arguments.
    - `error`: Property — error string from the last run, if any.
    - `is_running`: Property — True if the thread is currently active.
    - `should_stop`: Property — True if `stop()` has been called.
    - `run()`: Starts the function in a new background thread. Returns True if started.
    - `stop()`: Requests the thread to stop by setting the stop flag.
- `ThreadTask` class: A named task for use with `ThreadManager`.
    - `__init__(name, function, args=(), timeout=0)`: Defines a task with optional timeout in milliseconds.
    - `id`: Property (r/w) — unique integer task ID.
    - `stop()`: Sets the `should_stop` flag for this task.
    - Slots: `args`, `error`, `function`, `_id`, `name`, `result`, `should_stop`, `start_time`, `timeout`.
- `ThreadManager` class: Manages a queue of `ThreadTask` objects, running them sequentially.
    - `__init__()`: Initializes the task queue.
    - `task`: Property — the currently active `ThreadTask`.
    - `thread`: Property — the underlying `Thread` object.
    - `add_task(task)`: Add a `ThreadTask` to the queue.
    - `remove_task(task_id)`: Remove a task from the queue by ID.
    - `run()`: Process the task queue — starts the next queued task if no task is running. Returns a log string.

#### picoware-system-time
- `Time` class: Manages the device RTC and optional NTP time synchronization.
    - `__init__(thread_manager=None)`: Creates a `machine.RTC()` instance. Accepts an optional `ThreadManager` for async NTP fetch.
    - `date`: Property — current date as a `"M/D/Y"` formatted string.
    - `is_fetching`: Property — True if an NTP sync is currently in progress.
    - `is_set`: Property — True if the time has been set (manually or via NTP).
    - `rtc`: Property — the underlying `machine.RTC` object.
    - `time`: Property — current time as an `"H:MM:SS"` formatted string.
    - `fetch(offset=0)`: Synchronize the RTC with NTP (`pool.ntp.org`). `offset` is the UTC offset in hours. Uses `ThreadManager` if available. Returns True if started/successful.
    - `set(year, month, day, hour, minute, second)`: Manually set the RTC time.

#### picoware-system-uart
- `UART` class: Wraps `machine.UART` for serial communication.
    - `__init__(uart_id=0, tx_pin=0, rx_pin=1, baud_rate=115200, timeout=2000)`: Initializes UART with specified parameters.
    - `baud_rate`: Property — configured baud rate.
    - `has_data`: Property — True if data is available to read.
    - `is_sending`: Property — True if a send is in progress.
    - `rx_pin`: Property — RX GPIO pin number.
    - `timeout`: Property (r/w) — read timeout in milliseconds.
    - `tx_pin`: Property — TX GPIO pin number.
    - `uart`: Property — the underlying `machine.UART` object.
    - `clear()`: Flush the read buffer.
    - `flush()`: Flush the UART output.
    - `println(message)`: Write a string followed by a newline.
    - `read_into(buffer)`: Read available data into a `bytearray`. Returns bytes read.
    - `read_line()`: Blocking read with timeout — returns a line string.
    - `read_serial_line()`: Non-blocking read — returns available data as a string.
    - `set_callback(callback)`: Set a UART IRQ callback function.
    - `write(message)`: Write raw bytes to the UART.

#### picoware-system-vector
- `Vector` class: A 3D vector wrapping the C `vector.Vector` module.
    - `__init__(x=0, y=0, z=0)`: Initializes the vector. Accepts individual coordinates or, if `x` is a tuple, unpacks it.
    - `from_val(value)`: Class method — ensures a value is a `Vector`, converting from a tuple if needed.
    - `__add__(other)`: Returns the sum of two vectors as a new `Vector`.
    - `__mul__(scalar)`: Returns this vector scaled by a scalar as a new `Vector`.
    - `__rmul__(scalar)`: Right scalar multiplication (same as `__mul__`).
    - `__eq__(other)`: Returns True if both vectors have equal x, y, z components.
    - `x`: Property — x component (from C base).
    - `y`: Property — y component (from C base).
    - `z`: Property — z component (from C base).

#### picoware-system-wifi
- `WIFI_STATE_INACTIVE`: WiFi inactive / not initialized (-1)
- `WIFI_STATE_IDLE`: WiFi idle, not connecting (0)
- `WIFI_STATE_CONNECTING`: WiFi actively connecting (1)
- `WIFI_STATE_CONNECTED`: WiFi connected (2)
- `WIFI_STATE_ISSUE`: WiFi connection error (3)
- `WIFI_STATE_TIMEOUT`: WiFi connection timed out (4)
- `WiFi` class: Manages WiFi connections in STA (station) or AP (access point) mode.
    - `__init__(thread_manager=None, timeout=10)`: Creates a `network.WLAN(STA_IF)` instance. Accepts optional `ThreadManager` for async connect.
    - `callback_connect`: Property (r/w) — callable invoked when async connection state changes. Receives `(state, error)`.
    - `device_ip`: Property — current device IP address string.
    - `last_error`: Property — last connection error message string.
    - `mac_address`: Property — MAC address string.
    - `state`: Property — current WiFi state integer (`WIFI_STATE_*`).
    - `timeout`: Property (r/w) — connection timeout in seconds.
    - `connect(ssid, password, sta_mode=True)`: Synchronous connect to a WiFi network (STA or AP). Returns True on success.
    - `connect_async(ssid, password, sta_mode=True)`: Start an async WiFi connection via `ThreadManager` or `_thread`. Returns True if started.
    - `disconnect()`: Disconnect from the network.
    - `is_connected()`: Returns True if currently connected.
    - `reset()`: Deactivate WLAN and reset all state.
    - `scan()`: Scan for available networks. Returns a list of scan result tuples.
    - `status()`: Returns the current WiFi state as a `WIFI_STATE_*` constant.

#### picoware-system-view
- `View` class: Represents a named view with start/run/stop lifecycle callbacks.
    - `__init__(name, run, start, stop)`: Stores the name and three callables. Sets `active=False` and `should_stop=False`.
    - `active`: Attribute — True while the view is active.
    - `should_stop`: Attribute — set to True when `stop()` is called.
    - `start(view_manager)`: Calls the `start` callback and sets `active=True`. Returns True.
    - `stop(view_manager)`: Calls the `stop` callback, sets `active=False` and `should_stop=True`.
    - `run(view_manager)`: Calls the `run` callback if active. If `should_stop` is set, calls `stop()`. Shows a traceback alert on unhandled exceptions.

#### picoware-system-view_manager
- `MAX_VIEWS`: Maximum number of registered views (10).
- `MAX_STACK_SIZE`: Maximum navigation stack depth (10).
- `FREQ_DEFAULT` / `FREQ_RP2040`: Default CPU frequency for RP2040 boards (200 MHz).
- `FREQ_RP2350`: Default CPU frequency for RP2350 boards (230 MHz).
- `FREQ_PIMORONI`: Default CPU frequency for Pimoroni boards (210 MHz).
- `ViewManager` class: Central orchestrator that manages views, hardware subsystems, navigation, and settings.
    - `__init__()`: Initializes `Draw`, `Input`, `Keyboard`, `Storage`, `WiFi`, `Time`, `ThreadManager`, and `Log`. Loads settings from SD card (dark_mode, onscreen_keyboard, lvgl_mode, theme_color, debug, gmt_offset).
    - `background_color`: Property (r/w) — background color; also propagates to `draw.background` and `keyboard.background_color`.
    - `board_id`: Property (r/o) — current board ID integer.
    - `board_name`: Property (r/o) — board name string.
    - `current_view`: Property (r/o) — the active `View` object.
    - `draw`: Property (r/o) — the `Draw` instance.
    - `foreground_color`: Property (r/w) — foreground color; also propagates to draw and keyboard.
    - `gmt_offset`: Property (r/o) — configured GMT offset in hours.
    - `has_psram`: Property (r/o) — True if the board has PSRAM.
    - `has_sd_card`: Property (r/o) — True if the board has an SD card.
    - `has_touch`: Property (r/o) — True if the board has touch support.
    - `has_wifi`: Property (r/o) — True if the board has WiFi.
    - `input_manager`: Property (r/o) — the `Input` instance.
    - `keyboard`: Property (r/o) — the `Keyboard` instance.
    - `logs`: Property (r/o) — list of log entries.
    - `screen_size`: Property (r/o) — screen dimensions as a `Vector` (from `draw.size`).
    - `selected_color`: Property (r/w) — selection/highlight color; also propagates to keyboard.
    - `storage`: Property (r/o) — the `Storage` instance.
    - `thread_manager`: Property (r/o) — the `ThreadManager` instance.
    - `time`: Property (r/o) — the `Time` instance.
    - `view_count`: Property (r/o) — number of registered views.
    - `wifi`: Property (r/o) — the `WiFi` instance.
    - `add(view)`: Register a `View`. Returns True if successful (max `MAX_VIEWS`).
    - `alert(message, back=False)`: Display an `Alert` widget and block until `BUTTON_BACK` is pressed.
    - `back(remove_current_view=True, should_clear=True, should_start=True)`: Navigate to the previous view in the stack.
    - `clear()`: Fill the screen with the background color and swap.
    - `clear_stack()`: Empty the navigation stack.
    - `freq(use_default=False, frequency=None)`: Set the CPU clock frequency. Uses board-appropriate defaults if no value is given. Returns the set frequency.
    - `get_view(view_name)`: Returns the `View` with the given name, or None.
    - `log(message, log_type=3)`: Append a message to the log. Returns True on success.
    - `push_view(view_name)`: Push the named view onto the navigation stack.
    - `remove(view_name)`: Remove a view by name and clean it from the stack.
    - `run()`: Main loop tick — handle HOME button, run `ThreadManager`, run the current view.
    - `set(view_name)`: Set the active view by name and clear the navigation stack.
    - `switch_to(view_name, clear_stack=False, push_view=True)`: Switch to a view with optional stack management.

#### picoware-system-websocket
- `WS_OP_CONT` (0x0), `WS_OP_TEXT` (0x1), `WS_OP_BYTES` (0x2), `WS_OP_CLOSE` (0x8), `WS_OP_PING` (0x9), `WS_OP_PONG` (0xA): WebSocket opcode constants.
- `WS_CLOSE_OK` (1000), `WS_CLOSE_GOING_AWAY` (1001), `WS_CLOSE_PROTOCOL_ERROR` (1002), `WS_CLOSE_DATA_NOT_SUPPORTED` (1003), `WS_CLOSE_BAD_DATA` (1007), `WS_CLOSE_POLICY_VIOLATION` (1008), `WS_CLOSE_TOO_BIG` (1009), `WS_CLOSE_MISSING_EXTN` (1010), `WS_CLOSE_BAD_CONDITION` (1011): WebSocket close code constants.
- `WebSocketError`: Exception class for WebSocket-specific errors.
- `NoDataException`: Exception raised when a non-blocking read returns no data.
- `ConnectionClosed`: Exception raised when the connection has been closed.
- `WebSocket` class: RFC 6455 WebSocket client supporting `ws://` and `wss://` (TLS) connections.
    - `__init__(sock, underlying_sock=None)`: Low-level constructor. Use `WebSocket.connect()` instead.
    - `connect(uri, headers=None, timeout=10.0)`: Class method — connect to a WebSocket server. Returns a `WebSocket` instance. Handles `ws://` and `wss://` with SSL.
    - `error`: Property — last error string.
    - `is_blocking`: Property (r/w) — whether socket reads block. Setting this calls `setblocking()`.
    - `is_connected`: Property — True if the socket is open and connected.
    - `is_open`: Property — True if the connection is open.
    - `close(code=WS_CLOSE_OK, reason="")`: Send a close frame and shut down the connection.
    - `ping(data=b"")`: Send a WebSocket ping frame. Returns True on success.
    - `pong(data=b"")`: Send a WebSocket pong frame. Returns True on success.
    - `recv()`: Receive a message. Returns `str` (text), `bytes` (binary), `""` (no data available), or `None` (connection closed).
    - `send(data)`: Send a text or binary message. Returns True on success.

### GUI

#### picoware-gui-alert
- `Alert` class: A modal alert dialog for displaying a message to the user.
    - `__init__(draw, text, text_color=0xFFFF, background_color=0x0000)`: Initialize with drawing context and text. Supports both native and LVGL rendering.
    - `clear()`: Fill the display with the background color.
    - `draw(title)`: Render the alert with `title` as the header and the constructor `text` as body (word-wrapped). Handles circular displays and LVGL.

#### picoware-gui-choice
- `Choice` class: A labeled choice/dropdown selector widget.
    - `__init__(draw, position, size, title, options, initial_state=0, foreground_color=0xFFFF, background_color=0x0000)`: Initialize with position, size, title, a list of option strings, and optional styling.
    - `state`: Property (r/w) — current selected index integer.
    - `clear()`: Clear the widget area.
    - `close()`: Close the dropdown (LVGL mode only).
    - `draw()`: Render the options with a selection highlight.

#### picoware-gui-date_picker
- `DatePicker` class: A 6-field date and time picker using a drum-roll style interface.
    - `__init__(view_manager, position, size, time=None)`: Initialize. `time` is an optional initial RTC tuple `(year, month, dom, weekday, hour, min, sec, sub)`.
    - `time`: Property (read-only) — current selected tuple `(year, month, dom, weekday, hour, min, sec, sub)`.
    - `run()`: Handle one frame of input. Returns True to keep running, False when the user confirms or cancels (CENTER or BACK).

#### picoware-gui-desktop
- `Desktop` class: Manages the desktop environment header bar (WiFi icon, battery, time).
    - `__init__(draw, text_color, background_color)`: Initializes with drawing context and colors.
    - `clear()`: Clear the display with the background color.
    - `draw(animation_frame, animation_size, position)`: Draw the desktop background with a BMP image from disk.
    - `draw_header()`: Draw the header bar with the board name and WiFi status icon.
    - `set_battery(battery_level)`: Update the battery level shown in the header.
    - `set_time(time_str)`: Update the time string shown in the header.

#### picoware-gui-draw
- `Draw` class: Main graphics drawing class, inherits from the C `lcd.LCD` module.
    - `__init__(foreground=0xFFFF, background=0x0000, scale_x=1.0, scale_y=1.0, scale_position=False)`: Initialize with colors and optional display scaling.
    - `background`: Property (r/w) — background color integer.
    - `font`: Property (r/w) — current font size index.
    - `font_size`: Property (r/o) — current font dimensions as a `Vector`.
    - `foreground`: Property (r/w) — foreground color integer.
    - `size`: Property (r/o) — display dimensions as a `Vector`.
    - `use_lvgl`: Property (r/w) — whether LVGL rendering is enabled.
    - `char(position, char, color=None, font_size=-1)`: Draw a single character.
    - `circle(position, radius, color=None)`: Draw a circle outline.
    - `clear(position=Vector(0,0), size=Vector(320,320), color=None)`: Fill a rectangular area with a color (or the background color).
    - `erase()`: Fill the entire screen with the background color.
    - `fill_circle(position, radius, color=None)`: Draw a filled circle.
    - `fill_rectangle(position, size, color=None)`: Draw a filled rectangle.
    - `fill_round_rectangle(position, size, radius, color=None)`: Draw a filled rounded rectangle.
    - `fill_screen(color=None)`: Fill the entire screen.
    - `fill_triangle(point1, point2, point3, color=None)`: Draw a filled triangle.
    - `get_font(font_size=0)`: Returns a `FontSize` object for the given font size index.
    - `image(position, img)`: Draw an `Image` object pixel by pixel onto the back buffer.
    - `image_bmp(position, path, storage=None)`: Draw a 24-bit BMP file. Accepts a `Storage` object or a plain file path.
    - `image_bytearray(position, size, byte_data, invert=False)`: Draw from 8-bit pixel data (one byte per pixel).
    - `image_bytearray_1bit(position, size, byte_data)`: Draw from 1-bit packed bitmap data.
    - `image_bytearray_path(position, size, path, storage=None, seek=0, chunk_size=0)`: Draw pixel data loaded from a file.
    - `image_jpeg(position, path, storage=None)`: Decode and draw a Baseline JPEG file. Returns True on success.
    - `image_jpeg_buffer(position, buf)`: Decode and draw a JPEG from a bytes buffer. Returns True on success.
    - `len(text, font_size=0)`: Returns the pixel width of a text string at the given font size.
    - `line(position, size, color=None)`: Draw a horizontal line.
    - `line_custom(point_1, point_2, color=None)`: Draw a line between two arbitrary points.
    - `pixel(position, color=None)`: Draw a single pixel.
    - `psram(position, size, addr)`: Draw pixel data directly from a PSRAM address.
    - `rect(position, size, color=None)`: Draw a rectangle outline.
    - `set_mode(mode)`: Set the LCD rendering mode (inherited from C).
    - `set_scaling(scale_x, scale_y, scale_position=False)`: Set the display scaling factors (inherited from C).
    - `swap()`: Push the back buffer to the display (inherited from C).
    - `text(position, text, color=None, font_size=-1)`: Draw a text string.
    - `triangle(point1, point2, point3, color=None)`: Draw a triangle outline.

#### picoware-gui-file_browser
- `FILE_BROWSER_VIEWER`: Mode constant — view files only (0)
- `FILE_BROWSER_MANAGER`: Mode constant — full file manager (1)
- `FILE_BROWSER_SELECTOR`: Mode constant — file picker (returns selected path) (2)
- `FileBrowser` class: A dual-pane file browser/manager/selector with image viewer and text editor.
    - `__init__(view_manager, mode=FILE_BROWSER_SELECTOR, start_directory="")`: Initialize the browser. `mode` controls available operations.
    - `directory`: Property — active pane's current directory path (SD-prefix stripped).
    - `path`: Property — full path to the currently selected item.
    - `stats`: Property — dict with keys: `directory`, `path`, `size`, `type`.
    - `run()`: Main event loop. In `FILE_BROWSER_SELECTOR` mode, returns the selected path string when done. Returns None otherwise.

#### picoware-gui-image
- `Image` class: Holds RGB565 pixel data for a small image.
    - `__init__()`: Initializes an empty Image (`size=Vector(0,0)`, `_raw=None`).
    - `size`: Attribute — image dimensions as a `Vector`.
    - `is_8bit`: Attribute — True if the data is 8-bit (one byte per pixel).
    - `from_path(path)`: Load a 16-bit BMP from disk into the `_raw` attribute. Returns True on success.
    - `from_byte_array(data, size, is_8bit=True)`: Create an image from raw bytes/bytearray/memoryview. Returns True on success.
    - `from_string(image_str)`: Create an image from an ASCII art string (`.`=black, `1`=white, color codes `2`–`9`, `a`–`e`).
    - `get_pixel(x, y)`: Returns the RGB565 color value at `(x, y)`.

#### picoware-gui-jpeg
- `JPEG` class: Decodes JPEG images to the display. Wraps the C `jpegdec.JPEGDecoder` module.
    - `__init__(screen_width=320, screen_height=320, buffer_size=8192, buffer_num=2)`: Initialize the decoder.
    - `draw(x, y, file_path, storage=None)`: Decode a JPEG file and render it at `(x, y)`. Returns True on success.
    - `draw_buffer(x, y, buf)`: Decode a JPEG from a `bytes` buffer and render at `(x, y)`. Returns True on success.

#### picoware-gui-keyboard
- `KeyLayout` class: Defines the layout for one key on the on-screen keyboard.
    - `__init__(normal, shifted, width=1)`: Stores the normal character, shifted character, and key width multiplier.
- `Keyboard` class: On-screen keyboard with auto-complete support.
    - Class variables: `ROW1`–`ROW5` — lists of `KeyLayout` objects defining each row. `ROWS` — list of all rows. `ROW_SIZES` — row widths. `NUM_ROWS=5`. `KEY_WIDTH=22`, `KEY_HEIGHT=35`, `KEY_SPACING=1`, `TEXTBOX_HEIGHT=45`.
    - `__init__(draw, input_manager, text_color=0xFFFF, background_color=0x0000, selected_color=0x001F, on_save_callback=None)`: Initialize the keyboard.
    - `auto_complete_words`: Property (r/w) — list of strings to use for auto-complete suggestions.
    - `callback`: Property (r/w) — callable invoked when the user saves/submits text.
    - `is_finished`: Property (r/o) — True if the user has finished input (saved or cancelled).
    - `keyboard_width`: Property (r/o) — total pixel width of the keyboard.
    - `response`: Property (r/w) — the current input text string.
    - `show_keyboard`: Property (r/w) — whether the keyboard is visible.
    - `title`: Property (r/w) — label shown above the text input field.
    - `reset()`: Reset all keyboard state.
    - `run(swap=True, force=False)`: Process one input frame and redraw if needed. Returns False when input is complete.
    - `set_save_callback(callback)`: Set the function to call when text is submitted.

#### picoware-gui-list
- `List` class: A scrollable list widget with optional LVGL rendering.
    - `__init__(draw, y, height, text_color=0xFFFF, background_color=0x0000, selected_color=0x001F, border_color=0xFFFF, border_width=2)`: Initialize the list with position, size, and styling.
    - `current_item`: Property — the currently selected item string.
    - `item_count`: Property — number of items in the list.
    - `list_height`: Property — pixel height of the visible list area.
    - `selected_index`: Property — index of the currently selected item.
    - `add_item(item)`: Add a string item to the list.
    - `clear()`: Clear all items and the display.
    - `draw()`: Render the list with navigation arrows and dot position indicators.
    - `get_item(index)`: Returns the item string at the given index.
    - `item_exists(item)`: Returns True if the string exists in the list.
    - `remove_item(index)`: Remove the item at the given index.
    - `scroll_down()`: Scroll down one item.
    - `scroll_up()`: Scroll up one item.
    - `set_selected(index)`: Set the selected item by index.

#### picoware-gui-loading
- `Loading` class: A spinner loading animation widget with optional LVGL rendering.
    - `__init__(draw, spinner_color=0xFFFF, background_color=0x0000)`: Initialize the spinner.
    - `text`: Property (r/w) — text displayed below the spinner. Setting this updates the centered position.
    - `animate(swap=True)`: Draw one frame of the spinner arc with fading colors and an elapsed-time counter.
    - `fade_color(color, opacity)`: Fast RGB565 color fading utility. Returns faded color integer.
    - `set_text(text)`: Set the loading message.
    - `stop()`: Stop the animation and clean up.

#### picoware-gui-menu
- `Menu` class: A titled list widget for menus.
    - `__init__(draw, title, y, height, text_color=0xFFFF, background_color=0x0000, selected_color=0x001F, border_color=0xFFFF, border_width=2)`: Initialize with a title and layout. Reserves space for the title in native mode.
    - `current_item`: Property — the currently selected item string.
    - `item_count`: Property — number of items.
    - `list_height`: Property — pixel height of the list area.
    - `selected_index`: Property — index of the selected item.
    - `title`: Property (r/w) — menu title string.
    - `add_item(item)`: Add an item string.
    - `clear()`: Clear all items and the display.
    - `draw()`: Draw the title then the list.
    - `draw_title()`: Draw the title text and underline (native mode only).
    - `get_item(index)`: Returns the item at the given index.
    - `item_exists(item)`: Returns True if the item exists.
    - `refresh()`: Redraw the title and re-render the list selection.
    - `remove_item(index)`: Remove the item at the given index.
    - `scroll_down()`: Scroll down one item.
    - `scroll_up()`: Scroll up one item.
    - `set_selected(index)`: Set the selected item.

#### picoware-gui-scrollbar
- `ScrollBar` class: A simple scrollbar indicator widget.
    - `__init__(draw, position, size, outline_color=0x0000, fill_color=0xFFFFFF, is_horizontal=False)`: Initialize with position, size, colors, and orientation.
    - `clear()`: Fill the scrollbar area with the fill color.
    - `draw()`: Draw the scrollbar outline and the filled inner indicator.
    - `set_all(position, size, outline_color, fill_color, is_horizontal=False, should_draw=True, should_clear=True)`: Update all scrollbar properties and optionally redraw.

#### picoware-gui-textbox
- `TextBox` class: A multi-line scrollable text display. Wraps the C `textbox.TextBox` module with optional LVGL rendering.
    - `__init__(draw, y, height, foreground_color=0xFFFF, background_color=0x0000, show_scrollbar=True)`: Initialize the text box.
    - `current_text`: Property (r/w) — the displayed text string.
    - `text_height`: Property (r/o) — height of the text content in pixels.
    - `clear()`: Clear all text and the display area.
    - `refresh()`: Re-render the current text and scrollbar.
    - `scroll_down()`: Scroll down one line.
    - `scroll_up()`: Scroll up one line.
    - `set_current_line(line)`: Scroll the view to the specified line number.
    - `set_text(text)`: Set the text content and refresh the display.

#### picoware-gui-toggle
- `Toggle` class: A labeled toggle switch widget with optional LVGL rendering.
    - `__init__(draw, position, size, text, initial_state=False, foreground_color=0xFFFF, background_color=0x0000, on_color=0x001F, border_color=0xFFFF, border_width=1, should_clear=True, use_lvgl=True)`: Initialize the toggle.
    - `state`: Property (r/w) — current boolean state. Setting this redraws the widget.
    - `text`: Property (r/w) — label string. Setting this redraws the widget.
    - `clear()`: Fill the toggle area with the background color.
    - `draw(swap=True, clear=True, selected=False)`: Render the toggle switch with its label.

#### picoware-gui-toggle_list
- `ToggleList` class: A vertical list of `Toggle` switches with keyboard navigation.
    - `__init__(view_manager, foreground_color=0xFFFF, background_color=0x0000, on_color=0x001F, border_color=0xFFFF, border_width=1, callback=None)`: Initialize. `callback` is called with `(index, state)` when a toggle is changed.
    - `current_item`: Property — the currently focused `Toggle` object.
    - `current_state`: Property — boolean state of the currently focused toggle.
    - `current_text`: Property — label string of the currently focused toggle.
    - `item_count`: Property — number of toggles in the list.
    - `list_height`: Property — total pixel height of all toggles.
    - `selected_index`: Property — index of the currently focused item.
    - `add_toggle(text, initial_state=False)`: Add a new `Toggle` to the list.
    - `clear()`: Reset the list and clear the display.
    - `remove_toggle(index)`: Remove the toggle at the given index. Returns True on success.
    - `run()`: Handle one frame of input (UP/DOWN/CENTER/BACK). Returns False to signal exit.
    - `update_toggle(index, text, state)`: Update the text and state of a toggle. Returns True on success.

### Engine

#### picoware-engine-camera
- `CAMERA_FIRST_PERSON`: First-person camera mode constant (0)
- `CAMERA_THIRD_PERSON`: Third-person camera mode constant (1)
- `CameraParams` class: Wraps the C `engine.Camera` object. Stores camera parameters used by the 3D renderer (position, direction, plane vectors). Passed as `camera_context` to `Game`.

#### picoware-engine-engine
- `GameEngine` class: Represents a game engine:
    - `__init__(game, fps)`: Initialize the game engine.
    - `run()`: Run the game engine.
    - `run_async(should_delay)`: Run the game engine asynchronously.
    - `stop()`: Stop the game engine.
    - `update_game_input(game_input)`: Update the game input.

#### picoware-engine-entity
- `ENTITY_STATE_IDLE` (0), `ENTITY_STATE_MOVING` (1), `ENTITY_STATE_MOVING_TO_START` (2), `ENTITY_STATE_MOVING_TO_END` (3), `ENTITY_STATE_ATTACKING` (4), `ENTITY_STATE_ATTACKED` (5), `ENTITY_STATE_DEAD` (6): Constants for entity states.
- `ENTITY_TYPE_PLAYER`, `ENTITY_TYPE_ENEMY`, `ENTITY_TYPE_ICON`, `ENTITY_TYPE_NPC`, `ENTITY_TYPE_3D_SPRITE`: Constants for entity types.
- `SPRITE_3D_NONE`, `SPRITE_3D_HUMANOID`, `SPRITE_3D_TREE`, `SPRITE_3D_HOUSE`, `SPRITE_3D_PILLAR`, `SPRITE_3D_CUSTOM`: Constants for 3D sprite types.
- `Entity` class: Represents an entity in the game:
    - `__init__(name, entity_type, position, size, sprite_data, sprite_data_left, sprite_data_right, start, stop, update, render, collision, sprite_3d_type, is_8bit, sprite_3d_color)`: Initializes the entity.
    - `has_3d_sprite`: Property that returns True if the entity has a 3D sprite.
    - `position`: Property for getting and setting the position.
    - `is_active`: Attribute indicating if the entity is active.
    - `is_visible`: Attribute indicating if the entity is visible.
    - `is_player`: Attribute indicating if the entity is the player.
    - `direction`: Attribute for the entity's direction vector.
    - `state`: Attribute for the entity's current state.
    - `speed`: Attribute for the entity's movement speed.
    - `health`: Attribute for the entity's current health.
    - `max_health`: Attribute for the entity's maximum health.
    - `create_3d_sprite(sprite_3d_type, height, width, rotation, color)`: Creates a 3D sprite for the entity.
    - `collision(other, game)`: Called when the entity collides with another entity.
    - `render(draw, game)`: Called every frame to render the entity.
    - `start(game)`: Called when the entity is created.
    - `stop(game)`: Called when the entity is destroyed.
    - `update(game)`: Called every frame.

#### picoware-engine-game
- `Game` class: Represents a game:
    - `__init__(name, size, draw, input_manager, foreground_color, background_color, camera_context=None, start=None, stop=None)`: Initializes the game. `camera_context` is an optional `CameraParams` instance for 3D rendering.
    - `camera_context`: Property to get/set the `CameraParams` instance.
    - `is_active`: Attribute indicating if the game is active.
    - `input`: Attribute containing the last button pressed.
    - `camera`: Attribute containing the camera position as a Vector.
    - `current_level`: Attribute containing the current level.
    - `clamp(value, lower, upper)`: Clamp a value between a lower and upper bound.
    - `level_add(level)`: Add a level to the game.
    - `level_remove(level)`: Remove a level from the game.
    - `level_switch(level)`: Switch to a new level (by index or name).
    - `render()`: Render the current level.
    - `start()`: Start the game. Returns True on success.
    - `stop()`: Stop the game.
    - `update()`: Update the game input and entity positions.

#### picoware-engine-level
- `CAMERA_FIRST_PERSON`, `CAMERA_THIRD_PERSON`: Constants for camera perspectives.
- `Level` class: Represents a level in the game:
    - `__init__(name, size, game, start, stop)`: Initializes the level.
    - `clear_allowed`: Property to get/set if the level is allowed to clear the screen.
    - `entities`: Attribute containing the list of entities in the level.
    - `clear()`: Clear the level and stop all entities.
    - `collision_list(entity)`: Return a list of entities that the entity collided with.
    - `entity_add(entity)`: Add an entity to the level.
    - `entity_remove(entity)`: Remove an entity from the level.
    - `has_collided(entity)`: Check for collisions with other entities.
    - `is_collision(entity, other)`: Check if two entities collided using AABB logic.
    - `render(perspective, camera_params)`: Render the level with optional camera perspective.
    - `start()`: Start the level.
    - `stop()`: Stop the level.
    - `update()`: Update the level and check for collisions.

#### picoware-engine-image
- `Image` class: Wraps the C `engine.Image` structure. Represents a sprite or texture image used by the 3D engine. Typically constructed with image byte data and dimensions.

#### picoware-engine-sprite3d
- `SPRITE_HUMANOID` (0), `SPRITE_TREE` (1), `SPRITE_HOUSE` (2), `SPRITE_PILLAR` (3), `SPRITE_CUSTOM` (4): Constants for 3D sprite template types.
- `Sprite3D` class: Wraps the C `engine.Sprite3D` object. Represents a billboard sprite rendered in 3D space.
    - `__init__(sprite_type, position, height, width, rotation, color, image)`: Initializes the sprite. `sprite_type` is a `SPRITE_*` constant. `position` is a `Vector`, `image` is an optional `Image`.
    - `position`: Property to get/set the sprite's `Vector` position in world space.
    - `rotation`: Property to get/set the rotation angle (float, radians).
    - `color`: Property to get/set the tint color (RGB565 int).
    - `is_visible`: Property to get/set visibility (bool).

#### picoware-engine-triangle3d
- `Triangle3D` class: Wraps the C `engine.Triangle3D` structure. Represents a single 3D triangle (face) for use in polygon-based mesh rendering.
    - `__init__(v0, v1, v2, color)`: Initializes the triangle. `v0`, `v1`, `v2` are `Vector` vertices; `color` is an RGB565 int.
    - `color`: Property to get/set the fill color.

## SDK

### Table of Contents
- [System](#system-1)
  - [buttons](#buttons)
  - [colors](#colors)
  - [http](#http)
  - [input](#input)
  - [LED](#led)
  - [storage](#storage)
  - [system](#system-2)
  - [view](#view)
  - [view_manager](#view_manager)
  - [wifi](#wifi)
  - [helpers](#helpers)
  - [psram](#psram)
- [GUI](#gui-1)
  - [alert](#alert)
  - [desktop](#desktop)
  - [draw](#draw)
  - [image](#image)
  - [keyboard](#keyboard)
  - [list](#list)
  - [loading](#loading)
  - [menu](#menu)
  - [scrollbar](#scrollbar)
  - [textbox](#textbox)
  - [toggle](#toggle)
  - [vector](#vector)
- [Engine](#engine-1)
  - [engine](#engine-2)
  - [entity](#entity)
  - [game](#game)
  - [level](#level)
  - [sprite3d](#sprite3d)

### System

#### buttons
- `BUTTON_NONE`: No button pressed (-1)
- `BUTTON_UART`: UART button (-2)
- `BUTTON_PICO_CALC`: PicoCalc button (-3)
- `BUTTON_UP`: Up button (0)
- `BUTTON_DOWN`: Down button (1)
- `BUTTON_LEFT`: Left button (2)
- `BUTTON_RIGHT`: Right button (3)
- `BUTTON_CENTER`: Center/Enter button (4)
- `BUTTON_OK`: Center/Enter button (4)
- `BUTTON_BACK`: Back button (5)
- `BUTTON_START`: Start button (6)
- `BUTTON_A` through `BUTTON_Z`: Alphabet buttons (7-32)
- `BUTTON_0` through `BUTTON_9`: Number buttons (33-42)
- `BUTTON_SPACE`: Space button (43)
- `BUTTON_EXCLAMATION` through `BUTTON_BACKSPACE`: Special character buttons (44-73)
- `BUTTON_SHIFT`: Shift button (75)
- `BUTTON_CAPS_LOCK`: Caps lock button (76)

#### colors
- `TFT_WHITE`: White color (0xFFFF)
- `TFT_BLACK`: Black color (0x0000)
- `TFT_BLUE`: Blue color (0x001F)
- `TFT_CYAN`: Cyan color (0x07FF)
- `TFT_RED`: Red color (0xF800)
- `TFT_LIGHTGREY`: Light grey color (0xD69A)
- `TFT_DARKGREY`: Dark grey color (0x7BEF)
- `TFT_GREEN`: Green color (0x07E0)
- `TFT_DARKCYAN`: Dark cyan color (0x03EF)
- `TFT_DARKGREEN`: Dark green color (0x03E0)
- `TFT_SKYBLUE`: Sky blue color (0x867D)
- `TFT_VIOLET`: Violet color (0x915C)
- `TFT_BROWN`: Brown color (0x9A60)
- `TFT_TRANSPARENT`: Transparent color (0x0120)
- `TFT_YELLOW`: Yellow color (0xFFE0)
- `TFT_ORANGE`: Orange color (0xFDA0)
- `TFT_PINK`: Pink color (0xFE19)

#### http
- `HTTP` class: HTTP client for making requests
  - `HTTP()`: Constructor
  - `~HTTP()`: Destructor
  - `clearAsyncResponse()`: Clear async response data
  - `getAsyncResponse()`: Get async response string
  - `getState()`: Get current HTTP state (IDLE, LOADING, ISSUE)
  - `getStateString()`: Get state as string
  - `isRequestComplete()`: Check if async request is complete
  - `isRequestInProgress()`: Check if request is in progress
  - `update()`: Poll async requests
  - `request(method, url, headers, data)`: Make synchronous HTTP request
  - `requestAsync(method, url, headers, data)`: Start async HTTP request
  - `del(url, headers)`: Quick synchronous DELETE request
  - `get(url, headers)`: Quick synchronous GET request
  - `post(url, headers, data)`: Quick synchronous POST request
  - `put(url, headers, data)`: Quick synchronous PUT request
  - `delAsync(url, headers)`: Quick async DELETE request
  - `getAsync(url, headers)`: Quick async GET request
  - `postAsync(url, headers, data)`: Quick async POST request
  - `putAsync(url, headers, data)`: Quick async PUT request

#### input
- `Input` class: Input management system
  - `Input()`: Constructor initializes input system
  - `getLastButton()`: Get last button pressed
  - `isHeld(duration)`: Check if button held for duration
  - `isPressed()`: Check if button currently pressed
  - `reset()`: Reset input state
  - `run()`: Update input state
  - `read()`: Read key (blocking)
  - `readNonBlocking()`: Read key (non-blocking)

#### LED
- `LED` class: Built-in LED control
  - `LED()`: Constructor
  - `~LED()`: Destructor
  - `blink(period)`: Blink LED with given period in ms
  - `off()`: Turn LED off
  - `on()`: Turn LED on

#### storage
- `Storage` class: File storage management
  - `Storage()`: Constructor
  - `~Storage()`: Destructor
  - `createDirectory(dirPath)`: Create directory
  - `createFile(filePath)`: Create file
  - `read(filePath, buffer, size, bytes_read)`: Read file data
  - `remove(filePath)`: Remove file/directory
  - `rename(oldPath, newPath)`: Rename file/directory
  - `write(filePath, data, size, overwrite)`: Write data to file
  - `getFileSize(filePath)`: Get file size

#### system
- `System` class: System operations
  - `bootloaderMode()`: Reboot into bootloader
  - `getBoardName()`: Get board name (Pico/Pico W/Pico 2/Pico 2W)
  - `getDeviceName()`: Get device name (PicoCalc variants)
  - `freeHeap()`: Get free heap size
  - `freeHeapPSRAM()`: Get free PSRAM size
  - `isPicoW()`: Check if board has WiFi
  - `reboot()`: Reboot device
  - `sleep(ms)`: Sleep for milliseconds
  - `totalHeap()`: Get total heap size
  - `totalHeapPSRAM()`: Get total PSRAM size
  - `usedHeap()`: Get used heap size
  - `usedHeapPSRAM()`: Get used PSRAM size

#### view
- `View` class: View lifecycle management
  - `View(name, run, start, stop)`: Constructor with callbacks
  - `start(viewManager)`: Called when view starts
  - `stop(viewManager)`: Called when view stops
  - `run(viewManager)`: Called every frame

#### view_manager
- `ViewManager` class: Multi-view management system
  - `ViewManager()`: Constructor
  - `~ViewManager()`: Destructor
  - `add(view)`: Add view to manager
  - `back(removeCurrentView)`: Navigate back
  - `clearStack()`: Clear navigation stack
  - `pushView(viewName)`: Push view to stack
  - `remove(viewName)`: Remove view
  - `run()`: Run current view
  - `set(viewName)`: Set current view
  - `switchTo(viewName, clearStack, push)`: Switch to view
  - `getBackgroundColor()`: Get background color
  - `getCurrentView()`: Get current view
  - `getDraw()`: Get Draw object
  - `getForegroundColor()`: Get foreground color
  - `getInputManager()`: Get Input manager
  - `getKeyboard()`: Get Keyboard object
  - `getLED()`: Get LED object
  - `getSelectedColor()`: Get selected color
  - `getSize()`: Get display size
  - `getStackDepth()`: Get stack depth
  - `getStorage()`: Get Storage object
  - `getView(viewName)`: Get view by name
  - `getWiFi()`: Get WiFi object
  - `getTime()`: Get current time string
  - `setBackgroundColor(color)`: Set background color
  - `setForegroundColor(color)`: Set foreground color
  - `setSelectedColor(color)`: Set selected color

#### wifi
- `WiFiConnectionState` enum: Connection states (IDLE, CONNECTING, CONNECTED, FAILED, TIMEOUT)
- `WiFiScanResult` struct: WiFi scan result data
- `WiFi` class: WiFi management
  - `WiFi()`: Constructor
  - `~WiFi()`: Destructor
  - `configureTime()`: Configure NTP time sync
  - `connect(ssid, password, async)`: Connect to WiFi
  - `connectAsync(ssid, password)`: Start async connection
  - `connectAP(ssid)`: Connect in AP mode
  - `deviceIP()`: Get device IP address
  - `disconnect()`: Disconnect from WiFi
  - `getConnectedSSID()`: Get connected SSID
  - `getConnectedPassword()`: Get connected password
  - `getConnectionState()`: Get connection state
  - `isConnected()`: Check connection status
  - `resetConnection()`: Reset connection state
  - `scan()`: Scan for networks
  - `setTime(timeinfo, timeoutMs)`: Set time via NTP
  - `updateConnection()`: Update async connection

#### helpers
- `getJsonValue(json, key)`: Get JSON value by key
- `getJsonArrayValue(json, key)`: Get JSON array value by key
- `mapValue(value, fromLow, fromHigh, toLow, toHigh)`: Map value from one range to another
- `randomMax(max)`: Generate random number from 0 to max-1
- `randomRange(min, max)`: Generate random number in range
- `trim(str)`: Trim whitespace from string
- `getJsonStringValue(json, key)`: Get JSON string value by key
- `getJsonBoolValue(json, key)`: Get JSON boolean value by key
- `getJsonIntValue(json, key)`: Get JSON integer value by key
- `getJsonFloatValue(json, key)`: Get JSON float value by key
- `getJsonObjectValue(json, key)`: Get JSON object value by key
- `getJsonStringArrayValue(json, key)`: Get JSON string array value by key
- `getJsonIntArrayValue(json, key)`: Get JSON integer array value by key
- `getJsonFloatArrayValue(json, key)`: Get JSON float array value by key
- `getJsonBoolArrayValue(json, key)`: Get JSON boolean array value by key

#### psram
- `PSRAM` class: PSRAM memory management
  - `PSRAM()`: Constructor - initializes PSRAM hardware
  - `~PSRAM()`: Destructor
  - `isReady()`: Check if PSRAM is ready for use
  - `malloc(size)`: Allocate memory from PSRAM heap
  - `free(addr)`: Free previously allocated PSRAM memory
  - `realloc(addr, new_size)`: Reallocate PSRAM memory
  - `getTotalSize()`: Get total PSRAM size
  - `getTotalHeapSize()`: Get total heap size available for allocation
  - `getUsedHeapSize()`: Get used heap size
  - `getFreeHeapSize()`: Get free heap size
  - `getBlockCount()`: Get number of allocated blocks
  - `read(addr, data, length)`: Read data from PSRAM
  - `write(addr, data, length)`: Write data to PSRAM
  - `read8(addr)`: Read 8-bit value from PSRAM
  - `write8(addr, value)`: Write 8-bit value to PSRAM
  - `read16(addr)`: Read 16-bit value from PSRAM
  - `write16(addr, value)`: Write 16-bit value to PSRAM
  - `read32(addr)`: Read 32-bit value from PSRAM
  - `write32(addr, value)`: Write 32-bit value to PSRAM
  - `memset(addr, value, length)`: Set memory region to a specific value
  - `memcpy(dest, src, length)`: Copy memory from one PSRAM location to another
  - `copyToRAM(psram_addr, ram_ptr, length)`: Copy memory from regular RAM to PSRAM
  - `copyFromRAM(ram_ptr, psram_addr, length)`: Copy memory from PSRAM to regular RAM
  - `writeUint32Array(addr, values, count)`: Write array of uint32_t values to PSRAM
  - `readUint32Array(addr, values, count)`: Read array of uint32_t values from PSRAM
  - `writeUint16Array(addr, values, count)`: Write array of uint16_t values to PSRAM
  - `readUint16Array(addr, values, count)`: Read array of uint16_t values from PSRAM
  - `writeUint8Array(addr, values, count)`: Write array of uint8_t values to PSRAM
  - `readUint8Array(addr, values, count)`: Read array of uint8_t values from PSRAM
- `PSRAMPtr<T>` template class: RAII wrapper for PSRAM allocations
  - `PSRAMPtr(count)`: Constructor - allocates memory for count elements of type T
  - `~PSRAMPtr()`: Destructor - automatically frees memory
  - `address()`: Get PSRAM address
  - `isValid()`: Check if allocation is valid
  - `count()`: Get number of elements
  - `get(index)`: Read element at index
  - `set(index, value)`: Write element at index
  - `fill(value)`: Fill all elements with a value

### GUI

#### alert
- `Alert` class: Alert dialog management
  - `Alert(draw, text, text_color, background_color)`: Constructor
  - `clear()`: Clear display
  - `draw(title)`: Render alert message

#### desktop
- `Desktop` class: Desktop UI management
  - `Desktop(draw, text_color, background_color)`: Constructor
  - `clear()`: Clear display
  - `draw(animation_frame, animation_size, position)`: Draw desktop with BMP
  - `draw_header()`: Draw header with board name and WiFi status
  - `set_battery(battery_level)`: Set battery level display
  - `set_time(time_str)`: Set time display

#### draw
- `Draw` class: Graphics drawing and rendering
  - `Draw(foregroundColor, backgroundColor)`: Constructor
  - `~Draw()`: Destructor
  - `background(color)`: Set background color
  - `clear(position, size, color)`: Clear rectangular area
  - `clearBuffer(colorIndex)`: Clear back buffer
  - `clearBothBuffers(colorIndex)`: Clear both buffers
  - `color(color)`: Set drawing color
  - `color332(color)`: Convert RGB565 to RGB332
  - `color565(r, g, b)`: Convert RGB888 to RGB565
  - `drawCircle(position, r, color)`: Draw circle outline
  - `drawLine(position, size, color)`: Draw line
  - `drawLineCustom(point1, point2, color)`: Draw custom line
  - `drawPixel(position, color)`: Draw single pixel
  - `drawRect(position, size, color)`: Draw rectangle outline
  - `fillCircle(position, r, color)`: Fill circle
  - `fillRect(position, size, color)`: Fill rectangle
  - `fillRoundRect(position, size, color, radius)`: Fill rounded rectangle
  - `fillScreen(color)`: Fill entire screen
  - `getCursor()`: Get cursor position
  - `getFontSize()`: Get font size
  - `getPaletteColor(index)`: Get palette color
  - `getSize()`: Get display size
  - `getBackgroundTextColor()`: Get text background color
  - `getBackgroundTextStatus()`: Get text background status
  - `getForegroundTextColor()`: Get text foreground color
  - `image(position, bitmap, size, palette, imageCheck, invert)`: Draw bitmap image
  - `image(position, image, imageCheck)`: Draw Image object
  - `imageBitmap(position, bitmap, size, color, invert)`: Draw 1-bit bitmap
  - `imageColor(position, bitmap, size, color, invert, transparentColor)`: Draw color bitmap
  - `setBackgroundTextColor(color)`: Set text background color
  - `setBackgroundTextStatus(status)`: Set text background status
  - `setForegroundTextColor(color)`: Set text foreground color
  - `setCursor(position)`: Set cursor position
  - `setFont(font)`: Set font
  - `setPaletteColor(index, color)`: Set palette color
  - `swap(copyFrameBuffer, copyPalette)`: Swap display buffers
  - `swapRegion(position, size)`: Swap specific region
  - `text(position, text)`: Draw single character
  - `text(position, text, color)`: Draw character with color
  - `text(position, text)`: Draw text string
  - `text(position, text, color, font)`: Draw text with font and color

#### image
- `Image` class: Image data management
  - `Image()`: Constructor
  - `from_path(path)`: Load BMP from file
  - `from_byte_array(data, size, is_8bit)`: Create from byte array
  - `from_string(image_str)`: Create from ASCII art
  - `get_pixel(x, y)`: Get pixel value

#### keyboard
- `KeyLayout` class: Keyboard layout definition
  - `KeyLayout(normal, shifted, width)`: Constructor
- `Keyboard` class: Virtual keyboard
  - `ROW1`, `ROW2`, `ROW3`, `ROW4`, `ROW5`: Row constants
  - `ROWS`, `ROW_SIZES`, `NUM_ROWS`: Configuration constants
  - `KEY_WIDTH`, `KEY_HEIGHT`, `KEY_SPACING`, `TEXTBOX_HEIGHT`: Dimension constants
  - `Keyboard(draw, input_manager, text_color, background_color, ...)`: Constructor
  - `is_finished()`: Check if input finished
  - `keyboard_width()`: Get keyboard width
  - `get_response()`: Get entered text
  - `set_save_callback(callback)`: Set save callback
  - `set_response(text)`: Set initial text
  - `reset()`: Reset keyboard state
  - `run(swap, force)`: Run keyboard loop

#### list
- `List` class: Scrollable list component
  - `List(draw, y, height, text_color, background_color, selected_color, border_color, border_width)`: Constructor
  - `add_item(item, update_view)`: Add item to list
  - `clear()`: Clear list
  - `draw()`: Draw list
  - `draw_item(index, selected)`: Draw individual item
  - `current_item`: Get current item
  - `get_item(index)`: Get item by index
  - `item_count`: Get item count
  - `list_height`: Get list height
  - `remove_item(index)`: Remove item
  - `scroll_down()`: Scroll down
  - `scroll_up()`: Scroll up
  - `set_selected(index)`: Set selected item
  - `set_scrollbar_position()`: Set scrollbar position
  - `set_scrollbar_size()`: Set scrollbar size
  - `update_visibility()`: Update item visibility

#### loading
- `Loading` class: Loading spinner animation
  - `Loading(draw, spinner_color, background_color)`: Constructor
  - `animate(swap)`: Animate spinner
  - `fade_color(color, opacity)`: Color fading utility
  - `stop()`: Stop animation

#### menu
- `Menu` class: Menu component
  - `Menu(draw, title, y, height, text_color, background_color, selected_color, border_color, border_width)`: Constructor
  - `add_item(item)`: Add menu item
  - `clear()`: Clear menu
  - `draw()`: Draw menu
  - `draw_title()`: Draw menu title
  - `current_item`: Get current item
  - `get_item(index)`: Get item by index
  - `item_count`: Get item count
  - `list_height`: Get list height
  - `selected_index`: Get selected index
  - `remove_item(index)`: Remove item
  - `scroll_down()`: Scroll down
  - `scroll_up()`: Scroll up
  - `set_selected(index)`: Set selected item

#### scrollbar
- `ScrollBar` class: Scrollbar component
  - `ScrollBar(draw, position, size, outline_color, fill_color)`: Constructor
  - `clear()`: Clear scrollbar
  - `draw()`: Draw scrollbar
  - `set_all(position, size, outline_color, fill_color, should_draw, should_clear)`: Set all properties

#### textbox
- `TextBox` class: Multi-line text display
  - `TextBox(draw, y, height, foreground_color, background_color, show_scrollbar)`: Constructor
  - `get_text_height()`: Get text height
  - `set_scrollbar_position()`: Set scrollbar position
  - `set_scrollbar_size()`: Set scrollbar size
  - `display_visible_lines()`: Display visible lines
  - `clear()`: Clear textbox
  - `scroll_down()`: Scroll down
  - `scroll_up()`: Scroll up
  - `set_current_line(line)`: Set current line
  - `set_text(text)`: Set text content

#### toggle
- `Toggle` class: Toggle switch component
  - `Toggle(draw, position, size, text, initial_state, foreground_color, background_color, on_color, border_color, border_width)`: Constructor
  - `clear()`: Clear toggle area
  - `draw()`: Draw toggle
  - `set_state(new_state)`: Set toggle state
  - `toggle()`: Toggle state
  - `get_state()`: Get current state

#### vector
- `Vector` class: 2D vector mathematics
  - `Vector(x, y)`: Constructor
  - `from_val(value)`: Create from value
  - `__add__(other)`: Vector addition
  - `__mul__(scalar)`: Scalar multiplication
  - `__rmul__(scalar)`: Right scalar multiplication
  - `__str__()`: String representation

### Engine

#### engine
- `GameEngine` class: Game engine management and execution
  - `GameEngine()`: Constructor
  - `run()`: Run the game engine synchronously
  - `runAsync()`: Run the game engine asynchronously
  - `stop()`: Stop the game engine
  - `updateGameInput()`: Update game input state
  - `getGame()`: Get the current game instance

#### entity
- `EntityState` enum: Entity states (IDLE, MOVING, MOVING_TO_START, MOVING_TO_END, ATTACKING, ATTACKED, DEAD)
- `EntityType` enum: Entity types (PLAYER, ENEMY, ICON, NPC, 3D_SPRITE)
- `Sprite3DType` enum: 3D sprite types (NONE, HUMANOID, TREE, HOUSE, PILLAR, CUSTOM)
- `Entity` class: Game entity representation
  - `Entity(name, type, position, sprite, sprite_left, sprite_right, start, stop, update, render, collision, sprite_3d_type)`: Constructor with Image sprites
  - `Entity(name, type, position, size, sprite_data, sprite_left_data, sprite_right_data, start, stop, update, render, collision, is_8bit, is_progmem, sprite_3d_type)`: Constructor with raw sprite data
  - `~Entity()`: Virtual destructor
  - `collision(other, game)`: Handle collision with another entity
  - `position_get()`: Get entity position
  - `position_set(value)`: Set entity position
  - `render(draw, game)`: Render entity
  - `start(game)`: Initialize entity
  - `stop(game)`: Cleanup entity
  - `update(game)`: Update entity logic
  - `has3DSprite()`: Check if entity has 3D sprite
  - `set3DSpriteRotation(rotation)`: Set 3D sprite rotation
  - `set3DSpriteScale(scale)`: Set 3D sprite scale
  - `render3DSprite(draw, player_pos, player_dir, player_plane, view_height, screen_size)`: Render 3D sprite
  - `update3DSpritePosition()`: Update 3D sprite position
  - Entity properties: name, position, old_position, direction, plane, size, sprite, sprite_left, sprite_right, is_active, is_visible, type, sprite_3d, sprite_3d_type, sprite_rotation, sprite_scale, state, start_position, end_position, move_timer, elapsed_move_timer, radius, speed, attack_timer, elapsed_attack_timer, strength, health, max_health, level, xp, health_regen, elapsed_health_regen, is_8bit, is_progmem

#### game
- `CameraPerspective` enum: Camera perspectives (FIRST_PERSON, THIRD_PERSON)
- `Game` class: Main game class
  - `Game(name, size, draw, input_manager, fg_color, bg_color, perspective, start, stop)`: Constructor
  - `~Game()`: Destructor
  - `clamp(value, min, max)`: Clamp value between bounds
  - `level_add(level)`: Add level to game
  - `level_remove(level)`: Remove level from game
  - `level_switch(name)`: Switch to level by name
  - `level_switch(index)`: Switch to level by index
  - `render()`: Render current level
  - `setPerspective(perspective)`: Set camera perspective
  - `getPerspective()`: Get current camera perspective
  - `start()`: Start game
  - `stop()`: Stop game
  - `update()`: Update game logic
  - Game properties: name, levels, current_level, input_manager, draw, input, camera, pos, old_pos, size, is_active, bg_color, fg_color, camera_perspective

#### level
- `CameraPerspective` enum: Camera perspectives (FIRST_PERSON, THIRD_PERSON)
- `CameraParams` struct: Camera parameters (position, direction, plane, height)
- `Level` class: Game level management
  - `Level()`: Default constructor
  - `Level(name, size, game, start, stop)`: Constructor with callbacks
  - `~Level()`: Destructor
  - `clear()`: Clear level
  - `collision_list(entity, count)`: Get entities colliding with given entity
  - `entity_add(entity)`: Add entity to level
  - `entity_remove(entity)`: Remove entity from level
  - `has_collided(entity)`: Check if entity has collided
  - `is_collision(a, b)`: Check collision between two entities
  - `render(game, perspective, camera_params)`: Render level
  - `setClearAllowed(status)`: Set clear allowed flag
  - `start()`: Start level
  - `stop()`: Stop level
  - `update(game)`: Update level logic
  - `getEntityCount()`: Get entity count
  - `getEntity(index)`: Get entity by index
  - `isClearAllowed()`: Check if clear is allowed
  - Level properties: name, size

#### sprite3d
- `Vertex3D` struct: 3D vertex with x, y, z coordinates
  - `Vertex3D()`: Default constructor
  - `Vertex3D(x, y, z)`: Constructor with coordinates
  - `rotateY(angle)`: Rotate vertex around Y axis
  - `translate(dx, dy, dz)`: Translate vertex
  - `scale(sx, sy, sz)`: Scale vertex
  - `operator-(other)`: Vector subtraction
- `Triangle3D` struct: 3D triangle with 3 vertices
  - Properties: vertices[3], visible, distance
- `Sprite3D` class: 3D sprite management
  - `Sprite3D()`: Constructor
  - `setPosition(pos)`: Set sprite position
  - `getPosition()`: Get sprite position
  - `setRotation(rot)`: Set sprite rotation
  - `getRotation()`: Get sprite rotation
  - `setScale(scale)`: Set sprite scale
  - `getScale()`: Get sprite scale
  - `setActive(state)`: Set active state
  - `isActive()`: Check if active
  - `getType()`: Get sprite type
  - `addTriangle(triangle)`: Add triangle to sprite
  - `clearTriangles()`: Clear all triangles
  - `initializeAsHumanoid(pos, height, rot)`: Initialize as humanoid
  - `initializeAsTree(pos, height)`: Initialize as tree
  - `initializeAsHouse(pos, width, height, rot)`: Initialize as house
  - `initializeAsPillar(pos, height, radius)`: Initialize as pillar
  - `getTransformedTriangles(output_triangles, count, camera_pos)`: Get transformed triangles 