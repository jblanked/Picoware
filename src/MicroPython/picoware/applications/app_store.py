from micropython import const

STATE_LOADING_LIST = const(0)
STATE_APP_LIST = const(1)
STATE_LOADING_DETAILS = const(2)
STATE_APP_DETAILS = const(3)
STATE_DOWNLOADING = const(4)

_app_store_alert = None
_current_file_index: int = 0
_http = None
_loading = None
_files_to_download: list = []
_app_menu = None
_app_state: int = STATE_LOADING_LIST
_current_list_index: int = 0
_max_items: int = 20
_apps_data: dict = None
_selected_app_id: int = None
_selected_app_details: dict = None


def __reset() -> None:
    """Reset the app store state"""
    global _app_store_alert, _http, _loading, _files_to_download, _current_file_index, _app_menu
    global _app_state, _current_list_index, _apps_data, _selected_app_id, _selected_app_details

    if _app_store_alert:
        del _app_store_alert
        _app_store_alert = None
    if _http:
        del _http
        _http = None
    if _loading:
        del _loading
        _loading = None
    if _app_menu:
        del _app_menu
        _app_menu = None
    _files_to_download = []
    _current_file_index = 0
    _app_state = STATE_LOADING_LIST
    _current_list_index = 0
    _apps_data = None
    _selected_app_id = None
    _selected_app_details = None


def __app_store_alert(view_manager, message: str, back: bool = True) -> None:
    """Show an alert"""
    global _app_store_alert

    if _app_store_alert:
        del _app_store_alert
        _app_store_alert = None

    from picoware.gui.alert import Alert
    from picoware.system.buttons import BUTTON_BACK

    draw = view_manager.get_draw()
    draw.fill_screen(view_manager.get_background_color())
    _app_store_alert = Alert(
        draw,
        message,
        view_manager.get_foreground_color(),
        view_manager.get_background_color(),
    )
    _app_store_alert.draw("Alert")

    # Wait for user to acknowledge
    inp = view_manager.get_input_manager()
    while True:
        button = inp.button
        if button == BUTTON_BACK:
            inp.reset()
            break

    del _app_store_alert
    _app_store_alert = None

    if back:
        view_manager.back()


def __loading_start(view_manager, text: str = "Fetching...") -> None:
    """Start loading animation"""
    from picoware.gui.loading import Loading

    global _loading

    if not _loading:
        _loading = Loading(view_manager.get_draw())
    _loading.set_text(text)


def __fetch_app_list(view_manager) -> bool:
    """Fetch the list of apps from the API"""
    global _http, _current_list_index, _max_items

    if not _http:
        from picoware.system.http import HTTP

        _http = HTTP()

    storage = view_manager.get_storage()
    storage.mkdir("picoware/cache")

    url = f"https://www.jblanked.com/picoware/api/apps/{_max_items}/{_current_list_index}/"

    return _http.get_async(
        url,
        save_to_file=f"picoware/cache/app_list_{_current_list_index}.json",
        storage=storage,
        headers={"User-Agent": "Raspberry Pi Pico W"},
    )


def __parse_app_list(view_manager) -> bool:
    """Parse the app list JSON and populate the menu"""
    global _apps_data, _app_menu, _current_list_index

    storage = view_manager.get_storage()
    file_path = f"picoware/cache/app_list_{_current_list_index}.json"

    try:
        data = storage.read(file_path)
        if not data:
            return False

        from json import loads

        _apps_data = loads(data)

        if not _apps_data.get("success") or not _apps_data.get("apps"):
            return False

        # Create menu if it doesn't exist
        if not _app_menu:
            from picoware.gui.menu import Menu

            draw = view_manager.get_draw()
            _app_menu = Menu(
                draw,
                "App Store",
                0,
                draw.size.y,
                view_manager.get_foreground_color(),
                view_manager.get_background_color(),
            )

        # Clear and populate menu
        _app_menu.clear()
        for app in _apps_data["apps"]:
            title = app.get("title", "Unknown App")
            _app_menu.add_item(title)

        return True
    except Exception as e:
        print(f"Error parsing app list: {e}")
        return False


def __fetch_app_details(view_manager, app_id: int) -> bool:
    """Fetch details for a specific app"""
    global _http

    if not _http:
        from picoware.system.http import HTTP

        _http = HTTP()

    storage = view_manager.get_storage()
    url = f"https://www.jblanked.com/picoware/api/app/{app_id}/"

    return _http.get_async(
        url,
        save_to_file=f"picoware/cache/app_{app_id}.json",
        storage=storage,
        headers={"User-Agent": "Raspberry Pi Pico W"},
    )


def __parse_app_details(view_manager, app_id: int) -> bool:
    """Parse app details from JSON"""
    global _selected_app_details

    storage = view_manager.get_storage()
    file_path = f"picoware/cache/app_{app_id}.json"

    try:
        data = storage.read(file_path)
        if not data:
            return False

        from json import loads

        response = loads(data)

        if not response.get("success") or not response.get("app"):
            return False

        _selected_app_details = response["app"]
        return True
    except Exception as e:
        print(f"Error parsing app details: {e}")
        return False


def __draw_app_details(view_manager) -> None:
    """Draw the app details screen with professional layout"""
    from picoware.system.vector import Vector

    draw = view_manager.get_draw()
    fg = view_manager.get_foreground_color()

    draw.fill_screen(view_manager.get_background_color())

    if not _selected_app_details:
        return

    # Title at top
    title = _selected_app_details.get("title", "Unknown App")
    draw.text(Vector(10, 5), f"App: {title[:35]}", fg)

    # Description section
    description = _selected_app_details.get("description", "No description available")
    y_pos = 30

    # Word wrap the description
    max_chars = 45
    words = description.split()
    current_line = ""

    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if len(test_line) <= max_chars:
            current_line = test_line
        else:
            if current_line:
                draw.text(Vector(10, y_pos), current_line, fg)
                y_pos += 15
            current_line = word if len(word) <= max_chars else word[:max_chars]

    if current_line:
        draw.text(Vector(10, y_pos), current_line, fg)
        y_pos += 15

    # File structure section
    y_pos += 10
    draw.text(Vector(10, y_pos), "Files:", fg)
    y_pos += 15

    file_structure = _selected_app_details.get("file_structure", [])
    file_count = len(file_structure)

    # Show first few files
    for i, file_path in enumerate(file_structure[:5]):
        if y_pos > 250:
            break
        # Shorten path if too long
        display_path = file_path if len(file_path) <= 45 else "..." + file_path[-42:]
        draw.text(Vector(15, y_pos), display_path, fg)
        y_pos += 12

    if file_count > 5:
        draw.text(Vector(15, y_pos), f"...and {file_count - 5} more", fg)
        y_pos += 12

    # Instructions at bottom
    y_pos = 285
    draw.text(Vector(10, y_pos), "CENTER=Install  LEFT=Back", fg)

    draw.swap()


def __download_next_file(view_manager) -> bool:
    """Download the next file in the queue"""
    global _current_file_index, _files_to_download, _http

    if _current_file_index >= len(_files_to_download):
        return False

    file_info = _files_to_download[_current_file_index]
    file_url = file_info.get("download_url")
    file_path = file_info.get("path")

    if not file_url or not file_path:
        print(f"DEBUG: Missing download_url or path in file_info: {file_info}")
        return False

    storage = view_manager.get_storage()

    # Create necessary directories
    dir_path = "/".join(file_path.split("/")[:-1])
    storage.mkdir(dir_path)

    print(f"Downloading {file_url} to {file_path}")

    return _http.get_async(
        file_url,
        save_to_file=file_path,
        storage=storage,
        headers={"User-Agent": "Raspberry Pi Pico W"},
    )


def start(view_manager) -> bool:
    """Start the app"""
    if not view_manager.has_sd_card:
        __app_store_alert(view_manager, "App Store app requires an SD card", False)
        return False

    wifi = view_manager.get_wifi()

    # if not a wifi device, return
    if not wifi:
        __app_store_alert(view_manager, "WiFi not available...", False)
        return False

    # if wifi isn't connected, return
    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        __app_store_alert(view_manager, "WiFi not connected", False)
        connect_to_saved_wifi(view_manager)
        return False

    __reset()

    # Start fetching app list
    if __fetch_app_list(view_manager):
        __loading_start(view_manager, "Loading apps...")
    else:
        __app_store_alert(view_manager, "Failed to fetch app list")
        return False

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_CENTER,
        BUTTON_LEFT,
        BUTTON_RIGHT,
    )

    global _app_state, _app_menu, _selected_app_id, _http, _loading, _current_file_index, _files_to_download, _apps_data, _selected_app_details

    inp = view_manager.get_input_manager()
    button = inp.button

    # Handle BUTTON_BACK based on current state
    if button == BUTTON_BACK:
        inp.reset()
        if _app_state == STATE_APP_LIST:
            # Exit app only from main menu
            view_manager.back()
            return
        if _app_state == STATE_APP_DETAILS:
            # Go back to app list from details
            _app_state = STATE_APP_LIST
            if _app_menu:
                _app_menu.draw()
            return

        # From loading states, go back to app list or exit
        view_manager.back()
        return

    if _app_state == STATE_LOADING_LIST:
        # Show loading animation while fetching app list
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()
            return

        # Parse the app list
        if __parse_app_list(view_manager):
            _app_state = STATE_APP_LIST
            if _app_menu:
                _app_menu.draw()
        else:
            __app_store_alert(view_manager, "Failed to load apps")

    elif _app_state == STATE_APP_LIST:
        # Handle menu navigation
        if button in (BUTTON_UP, BUTTON_LEFT):
            inp.reset()
            if _app_menu:
                _app_menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            inp.reset()
            if _app_menu:
                _app_menu.scroll_down()
        elif button == BUTTON_CENTER:
            inp.reset()
            # Get selected app ID
            if _app_menu and _apps_data:
                selected_index = _app_menu.get_selected_index()
                if 0 <= selected_index < len(_apps_data["apps"]):
                    _selected_app_id = _apps_data["apps"][selected_index]["id"]
                    # Fetch app details
                    if __fetch_app_details(view_manager, _selected_app_id):
                        _app_state = STATE_LOADING_DETAILS
                        __loading_start(view_manager, "Loading details...")
                    else:
                        __app_store_alert(
                            view_manager, "Failed to fetch app details", False
                        )

    elif _app_state == STATE_LOADING_DETAILS:
        # Show loading animation while fetching app details
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()
            return

        # Parse app details
        if __parse_app_details(view_manager, _selected_app_id):
            _app_state = STATE_APP_DETAILS
            __draw_app_details(view_manager)
        else:
            __app_store_alert(view_manager, "Failed to load app details", False)
            _app_state = STATE_APP_LIST
            if _app_menu:
                _app_menu.draw()

    elif _app_state == STATE_APP_DETAILS:
        # Handle app details screen
        if button == BUTTON_LEFT:
            inp.reset()
            # Go back to app list
            _app_state = STATE_APP_LIST
            if _app_menu:
                _app_menu.draw()
        elif button == BUTTON_CENTER:
            inp.reset()
            # Start downloading
            if _selected_app_details and _selected_app_details.get("file_downloads"):
                _files_to_download = _selected_app_details["file_downloads"]
                _current_file_index = 0

                if __download_next_file(view_manager):
                    _app_state = STATE_DOWNLOADING
                    __loading_start(
                        view_manager, f"Downloading 1/{len(_files_to_download)}..."
                    )
                else:
                    __app_store_alert(view_manager, "Failed to start download", False)
            else:
                __app_store_alert(view_manager, "No files to download", False)

    elif _app_state == STATE_DOWNLOADING:
        # Handle file downloads
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()
            return

        # Move to next file
        _current_file_index += 1

        if _current_file_index < len(_files_to_download):
            # Download next file
            if __download_next_file(view_manager):
                __loading_start(
                    view_manager,
                    f"Downloading {_current_file_index + 1}/{len(_files_to_download)}...",
                )
        else:
            # All files downloaded
            __app_store_alert(view_manager, "App installed successfully!", False)
            _app_state = STATE_APP_LIST
            if _app_menu:
                _app_menu.draw()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    __reset()

    collect()
