# Libraries
This section provides documentation for the libraries available in Picoware.

## Table of Contents
- [MicroPython](#micropython)
- [SDK](#sdk)

## MicroPython

### Table of Contents
- [System](#system)
  - [picoware.system.bluetooth](#picoware-system-bluetooth)
  - [picoware.system.buttons](#picoware-system-buttons)
  - [picoware.system.colors](#picoware-system-colors)
  - [picoware.system.http](#picoware-system-http)
  - [picoware.system.input](#picoware-system-input)
  - [picoware.system.LED](#picoware-system-led)
  - [picoware.system.storage](#picoware-system-storage)
  - [picoware.system.system](#picoware-system-system)
  - [picoware.system.time](#picoware-system-time)
  - [picoware.system.vector](#picoware-system-vector)
  - [picoware.system.wifi](#picoware-system-wifi)
  - [picoware.system.view](#picoware-system-view)
  - [picoware.system.view_manager](#picoware-system-view_manager)
- [GUI](#gui)
  - [picoware.gui.alert](#picoware-gui-alert)
  - [picoware.gui.choice](#picoware-gui-choice)
  - [picoware.gui.desktop](#picoware-gui-desktop)
  - [picoware.gui.draw](#picoware-gui-draw)
  - [picoware.gui.image](#picoware-gui-image)
  - [picoware.gui.keyboard](#picoware-gui-keyboard)
  - [picoware.gui.list](#picoware-gui-list)
  - [picoware.gui.loading](#picoware-gui-loading)
  - [picoware.gui.menu](#picoware-gui-menu)
  - [picoware.gui.scrollbar](#picoware-gui-scrollbar)
  - [picoware.gui.textbox](#picoware-gui-textbox)
  - [picoware.gui.toggle](#picoware-gui-toggle)
- [Engine](#engine)
  - [picoware.engine.engine](#picoware-engine-engine)
  - [picoware.engine.entity](#picoware-engine-entity)
  - [picoware.engine.game](#picoware-engine-game)
  - [picoware.engine.level](#picoware-engine-level)

### System

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
- `Bluetooth` class: A class to manage Bluetooth functionality as a central device
    - `__init__(storage=None)`: Initializes the Bluetooth class with optional storage for paired devices.
    - `callback`: Property to get/set the Bluetooth event callback function. The callback accepts two parameters: event and data.
    - `characteristics`: Property that returns a list of discovered characteristics.
    - `connected_address`: Property that returns the address of the connected device.
    - `is_pairing`: Property that returns True if currently in pairing process.
    - `is_scanning`: Property that returns True if Bluetooth is currently scanning.
    - `is_connected`: Property that returns True if connected to a peripheral.
    - `mac_address`: Property that returns the MAC address of this Bluetooth device.
    - `passkey`: Property that returns the current passkey during pairing (if any).
    - `services`: Property that returns a list of discovered services.
    - `advertise(interval_us=None, name="Picoware")`: Start or stop BLE advertising to make this device discoverable.
    - `connect(addr_type, addr, timeout_ms=10000)`: Connect to a BLE peripheral device.
    - `decode_name(adv_data)`: Decode device name from advertising data.
    - `disconnect(conn_handle=None)`: Disconnect from a device.
    - `discover_characteristics(start_handle, end_handle)`: Discover characteristics for a service.
    - `discover_services()`: Discover services on the connected peripheral.
    - `is_device_paired(addr)`: Check if a device address is in the paired devices list.
    - `load_paired_devices()`: Load paired devices from storage.
    - `pair()`: Initiate pairing/bonding with the connected device.
    - `passkey_reply(accept=True, passkey=None)`: Reply to a passkey request during pairing.
    - `read(handle)`: Read data from a characteristic.
    - `remove_paired_device(addr)`: Remove a paired device from storage.
    - `save_paired_device(addr, name="")`: Save a paired device to storage.
    - `scan(duration_ms=5000, interval_us=30000, window_us=30000, active=True)`: Start scanning for BLE devices.
    - `scan_stop()`: Stop an ongoing scan.
    - `register()`: Register the device as a GATT server.
    - `subscribe(handle, notify=True)`: Subscribe to notifications from a characteristic.
    - `write(data, handle=None, response=False)`: Write data to the connected peripheral.

#### picoware-system-buttons
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
- `BUTTON_EXCLAMATION` through `BUTTON_BACK_TICK`: Special character buttons (44-85)
- `KEY_MOD_ALT`, `KEY_MOD_SHL`, `KEY_MOD_SHR`, `KEY_MOD_SYM`, `KEY_MOD_CTRL`: Key modifier constants
- `KEY_ESC`, `KEY_UP`, `KEY_DOWN`, `KEY_LEFT`, `KEY_RIGHT`: Arrow and escape key constants
- `KEY_BREAK`, `KEY_INSERT`, `KEY_HOME`, `KEY_DEL`, `KEY_END`, `KEY_PAGE_UP`, `KEY_PAGE_DOWN`: Navigation key constants
- `KEY_CAPS_LOCK`: Caps lock key constant
- `KEY_F1` through `KEY_F10`: Function key constants

Check the source code for all available button and key constants.

#### picoware-system-colors
- `TFT_WHITE`: A constant representing the color white (0xFFFF)
- `TFT_BLACK`: A constant representing the color black (0x0000)
- `TFT_BLUE`: A constant representing the color blue (0x001F)
- `TFT_CYAN`: A constant representing the color cyan (0x07FF)
- `TFT_RED`: A constant representing the color red (0xF800)
- `TFT_LIGHTGREY`: A constant representing the color light grey (0xD69A)
- `TFT_DARKGREY`: A constant representing the color dark grey (0x7BEF)
- `TFT_GREEN`: A constant representing the color green (0x07E0)
- `TFT_DARKCYAN`: A constant representing the color dark cyan (0x03EF)
- `TFT_DARKGREEN`: A constant representing the color dark green (0x03E0)
- `TFT_SKYBLUE`: A constant representing the color sky blue (0x867D)
- `TFT_VIOLET`: A constant representing the color violet (0x915C)
- `TFT_BROWN`: A constant representing the color brown (0x9A60)
- `TFT_TRANSPARENT`: A constant representing the color transparent (0x0120)
- `TFT_YELLOW`: A constant representing the color yellow (0xFFE0)
- `TFT_ORANGE`: A constant representing the color orange (0xFDA0)
- `TFT_PINK`: A constant representing the color pink (0xFE19)


#### picoware-system-http
- `HTTP_IDLE`: A constant representing the idle state (0)
- `HTTP_LOADING`: A constant representing the loading state (1)
- `HTTP_ISSUE`: A constant representing the issue state (2)
- `HTTP` class: A class for handling HTTP requests:
    - `__init__()`: Initializes the HTTP object.
    - `callback`: Property to get/set the async callback function. The callback accepts three parameters: response, state, and error.
    - `error`: Property that returns the async error message, if any.
    - `in_progress`: Property that checks if the async request is in progress.
    - `is_finished`: Property that checks if the async request is finished.
    - `is_successful`: Property that checks if the async request was successful (complete and no error).
    - `response`: Property that returns the async Response object.
    - `state`: Property that returns the current HTTP state.
    - `close()`: Close the async thread, clear the async response, and reset state.
    - `delete(url, headers, timeout, save_to_file, storage)`: Performs a synchronous HTTP DELETE request with optional headers, timeout, and file saving.
    - `delete_async(url, headers, timeout, save_to_file, storage)`: Starts an asynchronous HTTP DELETE request.
    - `get(url, headers, timeout, save_to_file, storage)`: Performs a synchronous HTTP GET request with optional headers, timeout, and file saving.
    - `get_async(url, headers, timeout, save_to_file, storage)`: Starts an asynchronous HTTP GET request.
    - `head(url, payload, headers, timeout, save_to_file, storage)`: Performs a synchronous HTTP HEAD request with payload.
    - `head_async(url, payload, headers, timeout, save_to_file, storage)`: Starts an asynchronous HTTP HEAD request.
    - `is_request_complete()`: Checks if the asynchronous request is complete.
    - `patch(url, payload, headers, timeout, save_to_file, storage)`: Performs a synchronous HTTP PATCH request with payload.
    - `patch_async(url, payload, headers, timeout, save_to_file, storage)`: Starts an asynchronous HTTP PATCH request.
    - `post(url, payload, headers, timeout, save_to_file, storage)`: Performs a synchronous HTTP POST request with payload.
    - `post_async(url, payload, headers, timeout, save_to_file, storage)`: Starts an asynchronous HTTP POST request.
    - `put(url, payload, headers, timeout, save_to_file, storage)`: Performs a synchronous HTTP PUT request with payload.
    - `put_async(url, payload, headers, timeout, save_to_file, storage)`: Starts an asynchronous HTTP PUT request.

#### picoware-system-input
- `Input` class: A class for handling user input:
    - `__init__()`: Initializes the Input object.
    - `battery`: Property that returns the current battery level as a percentage (0-100).
    - `button`: Property that returns the last button pressed.
    - `gesture`: Property that returns the last touch gesture.
    - `has_touch_support`: Property that returns True if touch input is supported on the current board.
    - `point`: Property that returns the last touch point as (x, y) tuple.
    - `was_capitalized`: Property that returns True if the last key pressed was a capital letter.
    - `is_pressed()`: Returns True if any key is currently pressed.
    - `is_held(duration)`: Returns True if the last button was held for the specified duration (in frames).
    - `on_key_callback(_)`: Callback invoked when a key becomes available.
    - `read()`: Returns the key code as an integer (blocking call).
    - `read_non_blocking()`: Returns the key code as integer, or -1 if no key is pressed.
    - `reset()`: Resets the input state.

#### picoware-system-LED
- `LED` class: A class for controlling the built-in LED:
    - `__init__(pin)`: Initializes the LED object with the specified pin (default is the onboard LED pin).
    - `blink(duration)`: A function that blinks the LED for a specified duration (in seconds).
    - `off()`: A function that turns the LED off.
    - `on()`: A function that turns the LED on.
    - `toggle()`: A function that toggles the LED state.

#### picoware-system-storage
- `Storage` class: A class for handling file storage:
    - `__init__()`: Initializes the Storage object.
    - `active`: Property that returns True if the storage is active (mounted).
    - `vfs_mounted`: Property that returns True if the VFS is mounted (allows use of open(), __import__, etc.).
    - `close(file_obj)`: Closes an open file and releases resources.
    - `deserialize(json_dict, file_path)`: Deserializes a JSON object and writes it to a file.
    - `execute_script(file_path)`: Runs a Python file from the storage.
    - `exists(path)`: Checks if a file or directory exists.
    - `file_read(file_obj)`: Reads from an open file.
    - `file_seek(file_obj, position)`: Seeks to a specific position in an open file.
    - `file_write(file_obj, data, mode)`: Writes data to an open file.
    - `is_directory(path)`: Checks if a path is a directory.
    - `listdir(path)`: Lists files in a directory.
    - `mkdir(path)`: Creates a new directory at the specified path.
    - `mount()`: Mounts the SD card.
    - `mount_vfs(mount_point)`: Mounts the SD card as a VFS filesystem for use with Python's built-in open(), __import__, etc.
    - `open(file_path, mode)`: Opens a file and returns the file handle.
    - `read(file_path, mode)`: Reads and returns the contents of a file.
    - `read_chunked(file_path, start, chunk_size)`: Reads a chunk of data from a file without loading the entire file.
    - `remove(file_path)`: Removes a file at the specified path.
    - `rename(old_path, new_path)`: Renames a file or directory from old_path to new_path.
    - `rmdir(path)`: Removes a directory at the specified path.
    - `serialize(file_path)`: Reads a file and returns its contents as a JSON object.
    - `size(file_path)`: Gets the size of a file in bytes.
    - `write(file_path, data, mode)`: Writes data to a file, creating or overwriting as needed.
    - `unmount()`: Unmounts the SD card (including VFS if mounted).
    - `unmount_vfs(mount_point)`: Unmounts the VFS filesystem.

#### picoware-system-system
- `System` class: Handle basic system operations:
    - `__init__()`: Initializes the System object.
    - `board_id`: Property that returns the board ID.
    - `board_name`: Property that returns the name of the board.
    - `device_name`: Property that returns the name of the device.
    - `free_flash`: Property that returns the free flash memory size.
    - `free_heap`: Property that returns the amount of free heap memory.
    - `free_psram`: Property that returns the amount of free PSRAM memory.
    - `has_psram`: Property that returns True if the device has PSRAM capabilities.
    - `has_sd_card`: Property that returns True if the device has an SD card slot.
    - `has_touch`: Property that returns True if the device has touch capabilities.
    - `has_wifi`: Property that returns True if the device has WiFi capabilities.
    - `is_circular`: Property that returns True if the device has a circular display.
    - `total_flash`: Property that returns the total flash memory size.
    - `total_heap`: Property that returns the total heap memory size.
    - `total_psram`: Property that returns the total PSRAM memory size.
    - `used_flash`: Property that returns the used flash memory size.
    - `used_heap`: Property that returns the used heap memory.
    - `used_psram`: Property that returns the used PSRAM memory.
    - `bootloader_mode()`: Enters the bootloader mode.
    - `hard_reset()`: Reboots the system.
    - `shutdown_device(view_manager)`: Shuts down the device (if supported).

#### picoware-system-time
- `Time` class: A class for handling time-related functions:
    - `__init__()`: Initializes the Time object.
    - `date`: A property that returns the current date as a string
    - `is_set`: A property that indicates if the time is set.
    - `time`: A property that returns the current time as a string.
    - `set(year, month, day, hour, minute, second)`: A function that sets the current date and time.

#### picoware-system-vector
- `Vector` class: A simple 2D vector class for handling coordinates and basic vector operations:
    - `__init__(x=0, y=0)`: Initializes the Vector with x and y coordinates. If x is a tuple, it unpacks it.
    - `from_val(value)`: Class method to ensure the value is a Vector. Converts tuples to Vector instances.
    - `__add__(other)`: Adds two vectors together.
    - `__mul__(scalar)`: Multiplies the vector by a scalar.
    - `__rmul__(scalar)`: Right multiplication by a scalar (same as __mul__).
    - `__str__()`: Returns a string representation of the vector as "(x, y)".

#### picoware-system-wifi
- `WIFI_STATE_INACTIVE`: WiFi inactive state (-1)
- `WIFI_STATE_IDLE`: WiFi idle state (0)
- `WIFI_STATE_CONNECTING`: WiFi connecting state (1)
- `WIFI_STATE_CONNECTED`: WiFi connected state (2)
- `WIFI_STATE_ISSUE`: WiFi issue state (3)
- `WIFI_STATE_TIMEOUT`: WiFi timeout state (4)
- `WiFi` class: A class to manage WiFi functionality on a MicroPython device:
    - `__init__()`: Initializes the WiFi class.
    - `device_ip`: Property that gets the current device IP address.
    - `last_error`: Property that gets the last connection error message.
    - `connect(ssid, password, sta_mode=True, is_async=False)`: Connects to a Wi-Fi network. Returns True on success.
    - `disconnect()`: Disconnects from the Wi-Fi network.
    - `is_connected()`: Checks if the device is connected to a Wi-Fi network.
    - `scan()`: Scans for available Wi-Fi networks and returns a list.
    - `status()`: Gets the current Wi-Fi connection status as a WiFi state value.
    - `reset()`: Resets the Wi-Fi configuration.
    - `update()`: Updates the Wi-Fi connection state (for async connections). Returns True when connected.

#### picoware-system-view
- `View` class: A class representing a view in the system with lifecycle methods:
    - `__init__(name, run, start, stop)`: Initializes the View with a name and callable functions for run, start, and stop.
    - `active`: Attribute indicating if the view is currently active.
    - `should_stop`: Attribute indicating if the view should stop.
    - `start(view_manager)`: Called when the view is created. Returns True on success.
    - `stop(view_manager)`: Called when the view is destroyed.
    - `run(view_manager)`: Called every frame while the view is active.

#### picoware-system-view_manager
- `ViewManager` class: A class that manages multiple views and provides navigation capabilities:
    - `MAX_VIEWS`: Maximum number of views (10).
    - `MAX_STACK_SIZE`: Maximum stack size for navigation (10).
    - `__init__()`: Initializes the ViewManager with default settings and subsystems.
    - `background_color`: Property to get/set the background color.
    - `board_id`: Property that returns the current board ID.
    - `board_name`: Property that returns the current device name.
    - `current_view`: Property that returns the current view.
    - `draw`: Property that returns the Draw instance.
    - `foreground_color`: Property to get/set the foreground color.
    - `has_psram`: Property that returns whether the current board has PSRAM.
    - `has_sd_card`: Property that returns whether the current board has an SD card.
    - `has_wifi`: Property that returns whether the current board has WiFi capability.
    - `input_manager`: Property that returns the Input manager instance.
    - `keyboard`: Property that returns the Keyboard instance.
    - `led`: Property that returns the LED instance.
    - `selected_color`: Property to get/set the selected color.
    - `screen_size`: Property that returns the screen size as a Vector.
    - `storage`: Property that returns the Storage instance.
    - `time`: Property that returns the Time instance.
    - `view_count`: Property that returns the number of views managed.
    - `wifi`: Property that returns the WiFi instance.
    - `add(view)`: Adds a view to the manager. Returns True if successful.
    - `alert(message, back)`: Shows an alert message.
    - `back(remove_current_view, should_clear, should_start)`: Navigates back to the previous view in the stack.
    - `clear()`: Clears the screen with the background color.
    - `clear_stack()`: Clears the navigation stack.
    - `get_view(view_name)`: Gets a view by name.
    - `remove(view_name)`: Removes a view by name.
    - `run()`: Runs the current view and handles input.
    - `set(view_name)`: Sets the current view by name, clearing the stack.
    - `switch_to(view_name, clear_stack, push_view)`: Switches to a view by name with stack management options.
    - `push_view(view_name)`: Pushes a view to the stack by name.

### GUI

#### picoware-gui-alert
- `Alert` class: A simple alert dialog class for displaying messages to the user:
    - `__init__(draw, text, text_color, background_color)`: Initialize the Alert with drawing context and styling.
    - `clear()`: Clear the display with the background color.
    - `draw(title)`: Render the alert message on the display.

#### picoware-gui-choice
- `Choice` class: A simple choice switch for the GUI:
    - `__init__(draw, position, size, title, options, initial_state, foreground_color, background_color)`: Initialize the Choice with drawing context, position, size, title, options, and styling.
    - `state`: Property to get/set the current state of the choice.
    - `clear()`: Clear the choice area with the background color.
    - `draw()`: Render the choices on the display.

#### picoware-gui-desktop
- `Desktop` class: A class to manage the desktop environment for the display:
    - `__init__(draw, text_color, background_color)`: Initializes the Desktop with drawing context and colors.
    - `clear()`: Clear the display with the background color.
    - `draw(animiation_frame, animation_size, position)`: Draw the desktop environment with a BMP image from disk.
    - `draw_header()`: Draw the header with the board name and Wi-Fi status.
    - `set_battery(battery_level)`: Set the battery level on the header.
    - `set_time(time_str)`: Set the time on the header.

#### picoware-gui-draw
- `Draw` class: Class for drawing shapes and text on the display:
    - `__init__(foreground, background)`: Initializes the Draw object with colors.
    - `background`: Property to get/set the current background color.
    - `board_id`: Property that gets the current board ID.
    - `font_size`: Property that gets the font size as a Vector.
    - `foreground`: Property to get/set the current foreground color.
    - `size`: Property that gets the size of the display as a Vector.
    - `circle(position, radius, color)`: Draw a circle outline.
    - `clear(position, size, color)`: Fill a rectangular area with a color.
    - `cleanup()`: Cleanup all allocated buffers and free memory.
    - `color332(color)`: Convert RGB565 to RGB332 color format.
    - `color565(r, g, b)`: Convert RGB888 to RGB565 color format.
    - `erase()`: Erase the display by filling with background color.
    - `fill_circle(position, radius, color)`: Draw a filled circle.
    - `fill_rectangle(position, size, color)`: Draw a filled rectangle.
    - `fill_round_rectangle(position, size, radius, color)`: Draw a filled rounded rectangle on the display.
    - `fill_screen(color)`: Fill the entire screen with a color.
    - `fill_triangle(point1, point2, point3, color)`: Draw a filled triangle.
    - `image(position, img)`: Draw an image object to the back buffer.
    - `image_bmp(position, path)`: Draw a 24-bit BMP image from file.
    - `image_bytearray(position, size, byte_data, invert)`: Draw an image from 8-bit byte data with optional inversion.
    - `image_bytearray_1bit(position, size, byte_data)`: Draw a 1-bit bitmap from packed byte_data.
    - `line(position, size, color)`: Draw horizontal line.
    - `line_custom(point_1, point_2, color)`: Draw line between two points.
    - `pixel(position, color)`: Draw a pixel.
    - `rect(position, size, color)`: Draw a rectangle outline.
    - `reset()`: Reset the display by clearing the framebuffer.
    - `swap()`: Swap the front and back buffers.
    - `text(position, text, color)`: Draw text on the display.
    - `text_char(position, char, color)`: Draw a single character on the display.
    - `triangle(point1, point2, point3, color)`: Draw a triangle outline.

#### picoware-gui-image
- `Image` class: Represents an image with RGB565 pixel data for MicroPython:
    - `__init__()`: Initializes an empty Image object.
    - `size`: Attribute containing the image dimensions as a Vector.
    - `is_8bit`: Attribute indicating if the image is in 8-bit format.
    - `from_path(path)`: Load a 16-bit BMP from disk into raw RGB565 data. Returns True on success.
    - `from_byte_array(data, size, is_8bit)`: Create an image from raw byte array. Returns True on success.
    - `from_string(image_str)`: Create a tiny monochrome-style RGB565 image from ASCII art.
    - `get_pixel(x, y)`: Get RGB565 pixel value at coordinates (x, y).

#### picoware-gui-keyboard
- `KeyLayout` class: Defines the keyboard layout structure:
    - `__init__(normal, shifted, width)`: Initializes with normal, shifted characters and width.
- `Keyboard` class: A simple on-screen keyboard class for a GUI:
    - `ROW1`, `ROW2`, `ROW3`, `ROW4`, `ROW5`: Constants defining keyboard rows.
    - `ROWS`, `ROW_SIZES`, `NUM_ROWS`: Constants for row configuration.
    - `KEY_WIDTH`, `KEY_HEIGHT`, `KEY_SPACING`, `TEXTBOX_HEIGHT`: Constants for key dimensions.
    - `__init__(draw, input_manager, text_color, background_color, selected_color, on_save_callback)`: Initializes the Keyboard with drawing and input contexts.
    - `callback`: Property to get/set the save callback function.
    - `is_finished`: Property that returns whether the keyboard is finished.
    - `keyboard_width`: Property that returns the keyboard width.
    - `title`: Property to get/set the current title of the keyboard.
    - `response`: Property to get/set the response string.
    - `set_save_callback(callback)`: Sets the save callback function.
    - `reset()`: Resets the keyboard state.
    - `run(swap, force)`: Run the keyboard input loop.

#### picoware-gui-list
- `List` class: A simple list class for a GUI:
    - `__init__(draw, y, height, text_color, background_color, selected_color, border_color, border_width)`: Initializes the List with drawing context and styling.
    - `item_count`: Property that returns the number of items in the list.
    - `add_item(item)`: Add an item to the list.
    - `clear()`: Clear the list.
    - `draw()`: Draw the list.
    - `current_item`: Get the currently selected item.
    - `get_item(index)`: Get an item from the list at the specified index.
    - `item_count`: Get the number of items in the list.
    - `list_height`: Get the height of the list.
    - `item_exists(item)`: Check if an item exists in the list.
    - `remove_item(index)`: Remove an item from the list.
    - `scroll_down()`: Scroll the list down by one item.
    - `scroll_up()`: Scroll the list up by one item.
    - `set_selected(index)`: Set the selected item in the list.

#### picoware-gui-loading
- `Loading` class: A loading class with spinner animation:
    - `__init__(draw, spinner_color, background_color)`: Initializes the Loading with drawing context and colors.
    - `text`: Property to get/set the current loading text.
    - `animate(swap)`: Animate the loading spinner.
    - `fade_color(color, opacity)`: Fast color fading.
    - `set_text(text)`: Set the loading text.
    - `stop()`: Stop the loading animation.

#### picoware-gui-menu
- `Menu` class: A simple menu class for a GUI:
    - `__init__(draw, title, y, height, text_color, background_color, selected_color, border_color, border_width)`: Initializes the Menu with drawing context and styling.
    - `current_item`: Property that gets the current item.
    - `item_count`: Property that gets the number of items.
    - `list_height`: Property that gets the height of the list.
    - `selected_index`: Property that gets the selected index.
    - `title`: Property that gets the menu title.
    - `add_item(item)`: Add an item to the menu.
    - `clear()`: Clear the menu.
    - `draw()`: Draw the menu.
    - `draw_title()`: Draw the title.
    - `current_item`: Get the current item in the menu.
    - `get_item(index)`: Get the item at the specified index.
    - `item_count`: Get the number of items in the menu.
    - `list_height`: Get the height of the list.
    - `selected_index`: Get the index of the selected item.
    - `item_exists(item)`: Check if an item exists in the menu.
    - `refresh()`: Refresh the menu display.
    - `remove_item(index)`: Remove an item from the menu.
    - `scroll_down()`: Scroll down the menu.
    - `scroll_up()`: Scroll up the menu.
    - `set_selected(index)`: Set the selected item.

#### picoware-gui-scrollbar
- `ScrollBar` class: A simple scrollbar class for a GUI:
    - `__init__(draw, position, size, outline_color, fill_color, is_horizontal)`: Initializes the ScrollBar with drawing context, colors, and orientation.
    - `clear()`: Clear the scrollbar.
    - `draw()`: Draw the scrollbar.
    - `set_all(position, size, outline_color, fill_color, is_horizontal, should_draw, should_clear)`: Set the properties of the scrollbar.

#### picoware-gui-textbox
- `TextBox` class: Class for a text box with scrolling functionality:
    - `__init__(draw, y, height, foreground_color, background_color, show_scrollbar)`: Initializes the TextBox with drawing context and styling.
    - `text`: Property that gets the current text in the text box.
    - `text_height`: Property that gets the height of the text box based on the number of lines and font size.
    - `set_scrollbar_position()`: Set the position of the scrollbar based on the current line.
    - `set_scrollbar_size()`: Set the size of the scrollbar based on the number of lines.
    - `display_visible_lines()`: Display only the lines that are currently visible.
    - `clear()`: Clear the text box and reset the scrollbar.
    - `refresh()`: Refresh the display to show current text and scrollbar.
    - `scroll_down()`: Scroll down by one line.
    - `scroll_up()`: Scroll up by one line.
    - `set_current_line(line)`: Scroll the text box to the specified line.
    - `set_text(text)`: Set the text in the text box, wrap lines, and scroll to bottom.

#### picoware-gui-toggle
- `Toggle` class: A simple toggle switch for the GUI:
    - `__init__(draw, position, size, text, initial_state, foreground_color, background_color, on_color, border_color, border_width)`: Initialize the Toggle switch with drawing context and styling.
    - `state`: Attribute indicating the current toggle state.
    - `clear()`: Clear the toggle area with the background color.
    - `draw()`: Render the toggle switch on the display.

### Engine

#### picoware-engine-engine
- `GameEngine` class: Represents a game engine:
    - `__init__(game, fps)`: Initialize the game engine.
    - `run()`: Run the game engine.
    - `run_async(should_delay)`: Run the game engine asynchronously.
    - `stop()`: Stop the game engine.
    - `update_game_input(game_input)`: Update the game input.

#### picoware-engine-entity
- `ENTITY_STATE_IDLE`, `ENTITY_STATE_MOVING`, `ENTITY_STATE_MOVING_TO_START`, `ENTITY_STATE_MOVING_TO_END`, `ENTITY_STATE_ATTACKING`, `ENTITY_STATE_DEAD`: Constants for entity states.
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
    - `__init__(name, size, draw, input_manager, foreground_color, background_color, perspective, start, stop)`: Initializes the game.
    - `perspective`: Property to get/set the camera perspective.
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