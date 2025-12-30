from micropython import const

STATE_LOADING_LIST = const(0)
STATE_APP_LIST = const(1)
STATE_LOADING_DETAILS = const(2)
STATE_APP_DETAILS = const(3)
STATE_DOWNLOADING = const(4)
STATE_DOWNLOADING_ALL = const(5)
STATE_LOADING_NEXT_APP = const(6)

MAX_ITEMS = const(100)

_current_file_index: int = 0
_http = None
_loading = None
_files_to_download: list = []
_app_menu = None
_app_state: int = STATE_LOADING_LIST
_current_list_index: int = 0
_apps_data: dict = None
_selected_app_id: int = None
_selected_app_details = None
_download_all_mode: bool = False
_current_app_index: int = 0
_total_apps_to_download: int = 0


def __reset() -> None:
    """Reset the app store state"""
    global _http, _loading, _files_to_download, _current_file_index, _app_menu
    global _app_state, _current_list_index, _apps_data, _selected_app_id, _selected_app_details
    global _download_all_mode, _current_app_index, _total_apps_to_download
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
    if _selected_app_details is not None:
        del _selected_app_details
        _selected_app_details = None
    _download_all_mode = False
    _current_app_index = 0
    _total_apps_to_download = 0


def __loading_start(view_manager, text: str = "Fetching...") -> None:
    """Start loading animation"""
    from picoware.gui.loading import Loading

    global _loading

    if not _loading:
        _loading = Loading(view_manager.draw)
    else:
        _loading.stop()
    _loading.set_text(text)


def __fetch_app_list(view_manager) -> bool:
    """Fetch the list of apps from the API"""
    global _http

    if not _http:
        from picoware.system.http import HTTP

        _http = HTTP()

    storage = view_manager.storage
    storage.mkdir("picoware/cache")

    url = (
        f"https://www.jblanked.com/picoware/api/apps/{MAX_ITEMS}/{_current_list_index}/"
    )

    return _http.get_async(
        url,
        save_to_file=f"picoware/cache/app_list_{_current_list_index}.json",
        storage=storage,
        headers={"User-Agent": "Raspberry Pi Pico W"},
    )


def __parse_app_list(view_manager) -> bool:
    """Parse the app list JSON and populate the menu"""
    global _apps_data, _app_menu

    storage = view_manager.storage
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

            draw = view_manager.draw
            _app_menu = Menu(
                draw,
                "App Store",
                0,
                draw.size.y,
                view_manager.foreground_color,
                view_manager.background_color,
            )

        # Clear and populate menu
        _app_menu.clear()
        # Add "Download All Apps" option at the top
        _app_menu.add_item("[Download All Apps]")
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

    storage = view_manager.storage
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

    storage = view_manager.storage
    file_path = f"picoware/cache/app_{app_id}.json"

    try:
        data = storage.read(file_path)
        if not data:
            return False

        from json import loads
        from picoware.system.app import App

        response = loads(data)

        if not response.get("success") or not response.get("app"):
            return False

        _selected_app_details = App(response["app"])
        return True
    except Exception as e:
        print(f"Error parsing app details: {e}")
        return False


def __draw_app_details(view_manager) -> None:
    """Draw the app details screen with professional layout"""
    from picoware.system.vector import Vector

    draw = view_manager.draw
    fg = view_manager.foreground_color

    draw.fill_screen(view_manager.background_color)

    if not _selected_app_details:
        return

    # Title at top
    title = _selected_app_details.title
    version = _selected_app_details.version
    draw.text(Vector(10, 5), f"{title[:35]} v{version}", fg)

    # Description section
    description = _selected_app_details.description
    y_pos = 30

    # Word wrap the description
    max_chars = 100
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

    file_structure = _selected_app_details.file_structure
    file_count = len(file_structure)

    # Show first few files
    for file_path in file_structure[:5]:
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
    draw.text(Vector(10, y_pos), "CENTER = Install", fg)

    draw.swap()


def __download_next_file(view_manager) -> bool:
    """Download the next file in the queue"""
    if _current_file_index >= len(_files_to_download):
        return False

    file_info = _files_to_download[_current_file_index]
    file_url = file_info.get("download_url")
    file_path = file_info.get("path")

    if not file_url or not file_path:
        print(f"DEBUG: Missing download_url or path in file_info: {file_info}")
        return False

    storage = view_manager.storage

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
        view_manager.alert("App Store app requires an SD card", False)
        return False

    wifi = view_manager.wifi

    # if not a wifi device, return
    if not wifi:
        view_manager.alert("WiFi not available...", False)
        return False

    # if wifi isn't connected, return
    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        view_manager.alert("WiFi not connected", False)
        connect_to_saved_wifi(view_manager)
        return False

    __reset()

    # Start fetching app list
    if __fetch_app_list(view_manager):
        __loading_start(view_manager, "Loading apps...")
    else:
        view_manager.alert("Failed to fetch app list")
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
    global _download_all_mode, _current_app_index, _total_apps_to_download

    inp = view_manager.input_manager
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
                view_manager.draw.erase()
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

        if _loading:
            _loading.stop()

        # Parse the app list
        if __parse_app_list(view_manager):
            _app_state = STATE_APP_LIST
            if _app_menu:
                _app_menu.draw()
        else:
            view_manager.alert("Failed to load apps")

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
                selected_index = _app_menu.selected_index
                # Check if "Download All Apps" is selected (index 0)
                if selected_index == 0:
                    # Start downloading all apps
                    _download_all_mode = True
                    _current_app_index = 0
                    _total_apps_to_download = len(_apps_data["apps"])
                    if _total_apps_to_download > 0:
                        _selected_app_id = _apps_data["apps"][0]["id"]
                        if __fetch_app_details(view_manager, _selected_app_id):
                            _app_state = STATE_LOADING_NEXT_APP
                            __loading_start(
                                view_manager,
                                f"Loading app 1/{_total_apps_to_download}...",
                            )
                        else:
                            view_manager.alert("Failed to fetch app details", False)
                            _download_all_mode = False
                    else:
                        view_manager.alert("No apps to download", False)
                # Adjust index by 1 to account for "Download All Apps" option
                elif 1 <= selected_index <= len(_apps_data["apps"]):
                    _selected_app_id = _apps_data["apps"][selected_index - 1]["id"]
                    # Fetch app details
                    if __fetch_app_details(view_manager, _selected_app_id):
                        _app_state = STATE_LOADING_DETAILS
                        __loading_start(view_manager, "Loading details...")
                    else:
                        view_manager.alert("Failed to fetch app details", False)

    elif _app_state == STATE_LOADING_DETAILS:
        # Show loading animation while fetching app details
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()
            return

        if _loading:
            _loading.stop()

        # Parse app details
        if __parse_app_details(view_manager, _selected_app_id):
            _app_state = STATE_APP_DETAILS
            __draw_app_details(view_manager)
        else:
            view_manager.alert("Failed to load app details", False)
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
            if _selected_app_details and _selected_app_details.file_downloads:
                _files_to_download = _selected_app_details.file_downloads
                _current_file_index = 0

                if __download_next_file(view_manager):
                    _app_state = STATE_DOWNLOADING
                    __loading_start(
                        view_manager, f"Downloading 1/{len(_files_to_download)}..."
                    )
                else:
                    view_manager.alert("Failed to start download", False)
            else:
                view_manager.alert("No files to download", False)

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
            # All files downloaded for this app
            if _download_all_mode:
                # Move to next app in download all mode
                _current_app_index += 1
                if _current_app_index < _total_apps_to_download:
                    # Fetch next app details
                    _selected_app_id = _apps_data["apps"][_current_app_index]["id"]
                    if __fetch_app_details(view_manager, _selected_app_id):
                        _app_state = STATE_LOADING_NEXT_APP
                        __loading_start(
                            view_manager,
                            f"Loading app {_current_app_index + 1}/{_total_apps_to_download}...",
                        )
                    else:
                        view_manager.alert(
                            f"Failed to fetch app {_current_app_index + 1}", False
                        )
                        _download_all_mode = False
                        _app_state = STATE_APP_LIST
                        if _app_menu:
                            _app_menu.draw()
                else:
                    # All apps downloaded
                    _download_all_mode = False
                    view_manager.alert(
                        f"All {_total_apps_to_download} apps installed!", False
                    )
                    _app_state = STATE_APP_LIST
                    if _app_menu:
                        _app_menu.draw()
            else:
                # Single app download complete
                view_manager.alert("App installed successfully!", False)
                _app_state = STATE_APP_LIST
                if _app_menu:
                    _app_menu.draw()

    elif _app_state == STATE_LOADING_NEXT_APP:
        # Loading next app details in download all mode
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()
            return

        # Parse app details and start downloading
        if __parse_app_details(view_manager, _selected_app_id):
            if _selected_app_details and _selected_app_details.file_downloads:
                _files_to_download = _selected_app_details.file_downloads
                _current_file_index = 0

                if __download_next_file(view_manager):
                    _app_state = STATE_DOWNLOADING
                    __loading_start(
                        view_manager,
                        f"App {_current_app_index + 1}/{_total_apps_to_download}: 1/{len(_files_to_download)}...",
                    )
                else:
                    # Skip this app if download fails, move to next
                    _current_app_index += 1
                    if _current_app_index < _total_apps_to_download:
                        _selected_app_id = _apps_data["apps"][_current_app_index]["id"]
                        if __fetch_app_details(view_manager, _selected_app_id):
                            __loading_start(
                                view_manager,
                                f"Loading app {_current_app_index + 1}/{_total_apps_to_download}...",
                            )
                        else:
                            view_manager.alert("Failed during download all", False)
                            _download_all_mode = False
                            _app_state = STATE_APP_LIST
                            if _app_menu:
                                _app_menu.draw()
                    else:
                        _download_all_mode = False
                        view_manager.alert(
                            f"All {_total_apps_to_download} apps installed!", False
                        )
                        _app_state = STATE_APP_LIST
                        if _app_menu:
                            _app_menu.draw()
            else:
                # No files to download for this app, skip to next
                _current_app_index += 1
                if _current_app_index < _total_apps_to_download:
                    _selected_app_id = _apps_data["apps"][_current_app_index]["id"]
                    if __fetch_app_details(view_manager, _selected_app_id):
                        __loading_start(
                            view_manager,
                            f"Loading app {_current_app_index + 1}/{_total_apps_to_download}...",
                        )
                    else:
                        view_manager.alert("Failed during download all", False)
                        _download_all_mode = False
                        _app_state = STATE_APP_LIST
                        if _app_menu:
                            _app_menu.draw()
                else:
                    _download_all_mode = False
                    view_manager.alert(
                        f"All {_total_apps_to_download} apps installed!",
                        False,
                    )
                    _app_state = STATE_APP_LIST
                    if _app_menu:
                        _app_menu.draw()
        else:
            # Failed to parse, skip to next app
            _current_app_index += 1
            if _current_app_index < _total_apps_to_download:
                _selected_app_id = _apps_data["apps"][_current_app_index]["id"]
                if __fetch_app_details(view_manager, _selected_app_id):
                    __loading_start(
                        view_manager,
                        f"Loading app {_current_app_index + 1}/{_total_apps_to_download}...",
                    )
                else:
                    view_manager.alert("Failed during download all", False)
                    _download_all_mode = False
                    _app_state = STATE_APP_LIST
                    if _app_menu:
                        _app_menu.draw()
            else:
                _download_all_mode = False
                view_manager.alert(
                    f"All {_total_apps_to_download} apps installed!",
                    False,
                )
                _app_state = STATE_APP_LIST
                if _app_menu:
                    _app_menu.draw()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    __reset()

    collect()
