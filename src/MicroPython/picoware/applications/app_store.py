from micropython import const

# Main menu states
STATE_MAIN_MENU = const(0)
STATE_LOADING_LIST = const(1)
STATE_APP_LIST = const(2)
STATE_LOADING_DETAILS = const(3)
STATE_APP_DETAILS = const(4)
STATE_DOWNLOADING = const(5)
STATE_DOWNLOADING_ALL = const(6)
STATE_LOADING_NEXT_APP = const(7)
# Current apps states
STATE_CURRENT_APPS_LIST = const(8)
STATE_CURRENT_APP_DETAILS = const(9)
STATE_CHECKING_APP_UPDATE = const(10)
# Update apps states
STATE_CHECKING_UPDATES = const(11)
STATE_UPDATES_LIST = const(12)
STATE_DOWNLOADING_UPDATES = const(13)
STATE_LOADING_UPDATE_DETAILS = const(14)

MAX_ITEMS = const(100)

_current_file_index: int = 0
_http = None
_loading = None
_files_to_download: list = []
_app_menu = None
_app_state: int = STATE_MAIN_MENU
_current_list_index: int = 0
_apps_data: dict = None
_selected_app_id: int = None
_selected_app_details = None
_download_all_mode: bool = False
_current_app_index: int = 0
_total_apps_to_download: int = 0
_installed_apps: list = []  # List of installed app info dicts
_updates_available: list = []  # List of apps that have updates
_main_menu = None  # Main menu reference
_update_check_data: dict = None  # Response from update check API


def __reset() -> None:
    """Reset the app store state"""
    global _http, _loading, _files_to_download, _current_file_index, _app_menu
    global _app_state, _current_list_index, _apps_data, _selected_app_id, _selected_app_details
    global _download_all_mode, _current_app_index, _total_apps_to_download
    global _installed_apps, _updates_available, _main_menu, _update_check_data
    if _http:
        del _http
        _http = None
    if _loading:
        del _loading
        _loading = None
    if _app_menu:
        del _app_menu
        _app_menu = None
    if _main_menu:
        del _main_menu
        _main_menu = None
    _files_to_download = []
    _current_file_index = 0
    _app_state = STATE_MAIN_MENU
    _current_list_index = 0
    _apps_data = None
    _selected_app_id = None
    if _selected_app_details is not None:
        del _selected_app_details
        _selected_app_details = None
    _download_all_mode = False
    _current_app_index = 0
    _total_apps_to_download = 0
    _installed_apps = []
    _updates_available = []
    _update_check_data = None


def __loading_start(view_manager, text: str = "Fetching...") -> None:
    """Start loading animation"""
    from picoware.gui.loading import Loading

    global _loading

    if not _loading:
        _loading = Loading(view_manager.draw)
    else:
        _loading.stop()
    _loading.set_text(text)


def __show_main_menu(view_manager) -> None:
    """Show the main App Store menu"""
    global _main_menu, _app_state

    from picoware.gui.menu import Menu

    draw = view_manager.draw
    draw.erase()

    if not _main_menu:
        _main_menu = Menu(
            draw,
            "App Store",
            0,
            draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
        )

    _main_menu.clear()
    _main_menu.add_item("Update Apps")
    _main_menu.add_item("Current App Info")
    _main_menu.add_item("View All Apps")
    _main_menu.draw()
    _app_state = STATE_MAIN_MENU


def __get_installed_apps(view_manager) -> list:
    """Scan cache folder for installed app JSON files and return list of app info"""
    storage = view_manager.storage
    installed = []

    try:
        # List files in cache directory
        cache_files = storage.listdir("picoware/cache")
        if not cache_files:
            return []

        from json import loads

        for filename in cache_files:
            # Look for app_<id>.json files (not app_list_*.json)
            if (
                filename.startswith("app_")
                and filename.endswith(".json")
                and "list" not in filename
            ):
                try:
                    file_path = f"picoware/cache/{filename}"
                    data = storage.read(file_path)
                    if data:
                        response = loads(data)
                        if response.get("success") and response.get("app"):
                            app_data = response["app"]
                            installed.append(
                                {
                                    "id": app_data.get("id"),
                                    "title": app_data.get("title", "Unknown"),
                                    "version": app_data.get("version", "1.0.0"),
                                    "description": app_data.get("description", ""),
                                    "authors": app_data.get("authors", []),
                                }
                            )
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
                    continue
    except Exception as e:
        print(f"Error listing cache files: {e}")

    return installed


def __check_updates_async(view_manager) -> bool:
    """Start async request to check for updates for all installed apps"""
    global _http, _installed_apps

    _installed_apps = __get_installed_apps(view_manager)

    if not _installed_apps:
        return False

    if not _http:
        from picoware.system.http import HTTP

        _http = HTTP(thread_manager=view_manager.thread_manager)

    # Build POST data for bulk update check
    from json import dumps

    apps_list = [
        {"app_id": app["id"], "current_version": app["version"]}
        for app in _installed_apps
    ]
    post_data = dumps({"apps": apps_list})

    storage = view_manager.storage
    storage.mkdir("picoware/cache")

    url = "https://www.jblanked.com/picoware/api/apps/check_updates/"

    return _http.post_async(
        url,
        payload=post_data,
        headers={
            "User-Agent": "Raspberry Pi Pico W",
            "Content-Type": "application/json",
        },
    )


def __parse_update_check(view_manager) -> bool:
    """Parse update check response and populate updates list"""
    global _updates_available, _app_menu

    # storage = view_manager.storage
    # file_path = "picoware/cache/update_check.json"

    try:
        response = _http.response.json()

        if not response.get("success") or not response.get("results"):
            return False

        # Filter apps that have updates available
        _updates_available = []
        for result in response["results"]:
            if result.get("is_update_available"):
                # Find the installed app info
                for app in _installed_apps:
                    if app["id"] == result.get("app_id"):
                        _updates_available.append(
                            {
                                "id": result.get("app_id"),
                                "title": app.get("title", "Unknown"),
                                "current_version": result.get("current_version"),
                                "latest_version": result.get("latest_version"),
                                "download_url": result.get("download_url"),
                            }
                        )
                        break

        # Create menu for updates
        if not _app_menu:
            from picoware.gui.menu import Menu

            draw = view_manager.draw
            _app_menu = Menu(
                draw,
                "Available Updates",
                0,
                draw.size.y,
                view_manager.foreground_color,
                view_manager.background_color,
            )

        _app_menu.clear()
        if _updates_available:
            _app_menu.add_item("[Update All]")
            for app in _updates_available:
                _app_menu.add_item(
                    f"{app['title']} ({app['current_version']} -> {app['latest_version']})"
                )
        else:
            _app_menu.add_item("All apps up to date!")

        return True
    except Exception as e:
        print(f"Error parsing update check: {e}")
        return False


def __check_single_app_update(view_manager, app_id: int, current_version: str) -> bool:
    """Check for update for a single app"""
    global _http

    if not _http:
        from picoware.system.http import HTTP

        _http = HTTP(thread_manager=view_manager.thread_manager)

    storage = view_manager.storage
    url = f"https://www.jblanked.com/picoware/api/app/{app_id}/check_update/{current_version}/"

    return _http.get_async(
        url,
        save_to_file=f"picoware/cache/update_check_{app_id}.json",
        storage=storage,
        headers={"User-Agent": "Raspberry Pi Pico W"},
    )


def __draw_current_app_details(
    view_manager, app_info: dict, update_info: dict = None
) -> None:
    """Draw current app details with optional update info"""
    from picoware.system.vector import Vector

    draw = view_manager.draw
    fg = view_manager.foreground_color

    draw.fill_screen(view_manager.background_color)

    # Title at top
    word_vec = Vector(10, 5)
    title = app_info.get("title", "Unknown")
    version = app_info.get("version", "1.0.0")
    draw.text(word_vec, f"{title[:35]} v{version}", fg)

    # Description section
    description = app_info.get("description", "No description available")
    y_pos = 30

    # Word wrap the description
    max_chars = 100
    words = description.split()
    current_line = ""

    word_vec.y = y_pos
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if len(test_line) <= max_chars:
            current_line = test_line
        else:
            if current_line:
                word_vec.y = y_pos
                draw.text(word_vec, current_line, fg)
                y_pos += 15
            current_line = word if len(word) <= max_chars else word[:max_chars]

    if current_line:
        word_vec.y = y_pos
        draw.text(word_vec, current_line, fg)
        y_pos += 15

    # Authors
    y_pos += 10
    authors = app_info.get("authors", [])
    if authors:
        word_vec.y = y_pos
        draw.text(word_vec, f"Authors: {', '.join(authors[:3])}", fg)
        y_pos += 15

    # Update status
    y_pos += 10
    word_vec.y = y_pos
    if update_info:
        if update_info.get("is_update_available"):
            latest = update_info.get("latest_version", "?")
            draw.text(word_vec, f"Update available: v{latest}", fg)
            word_vec.y += 15
            draw.text(word_vec, "CENTER = Download Update", fg)
        else:
            draw.text(word_vec, "App is up to date!", fg)
    else:
        draw.text(word_vec, "CENTER = Check for Update", fg)

    # Instructions at bottom
    y_pos = 285
    word_vec.y = y_pos
    draw.text(word_vec, "BACK = Return", fg)

    draw.swap()


def __fetch_app_list(view_manager) -> bool:
    """Fetch the list of apps from the API"""
    global _http

    if not _http:
        from picoware.system.http import HTTP

        _http = HTTP(thread_manager=view_manager.thread_manager)

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

        _http = HTTP(thread_manager=view_manager.thread_manager)

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
    word_vec = Vector(10, 5)
    title = _selected_app_details.title
    version = _selected_app_details.version
    draw.text(word_vec, f"{title[:35]} v{version}", fg)

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
                word_vec.y = y_pos
                draw.text(word_vec, current_line, fg)
                y_pos += 15
            current_line = word if len(word) <= max_chars else word[:max_chars]

    if current_line:
        word_vec.y = y_pos
        draw.text(word_vec, current_line, fg)
        y_pos += 15

    # File structure section
    y_pos += 10
    word_vec.y = y_pos
    draw.text(word_vec, "Files:", fg)
    y_pos += 15

    file_structure = _selected_app_details.file_structure
    file_count = len(file_structure)

    # Show first few files
    for file_path in file_structure[:5]:
        if y_pos > 250:
            break
        # Shorten path if too long
        display_path = file_path if len(file_path) <= 45 else "..." + file_path[-42:]
        word_vec.x, word_vec.y = 15, y_pos
        draw.text(word_vec, display_path, fg)
        y_pos += 12

    if file_count > 5:
        word_vec.x, word_vec.y = 15, y_pos
        draw.text(word_vec, f"...and {file_count - 5} more", fg)
        y_pos += 12

    # Instructions at bottom
    y_pos = 285
    word_vec.x, word_vec.y = 10, y_pos
    draw.text(word_vec, "CENTER = Install", fg)

    draw.swap()


def __download_next_file(view_manager) -> bool:
    """Download the next file in the queue"""
    if _current_file_index >= len(_files_to_download):
        return False

    file_info = _files_to_download[_current_file_index]
    file_url = file_info.get("download_url")
    file_path = file_info.get("path")

    if not file_url or not file_path:
        return False

    storage = view_manager.storage

    # Create necessary directories
    dir_path = "/".join(file_path.split("/")[:-1])
    storage.mkdir(dir_path)

    return _http.get_async(
        file_url,
        save_to_file=file_path,
        storage=storage,
        headers={
            "User-Agent": "Raspberry Pi Pico W",
            "Content-Type": "application/octet-stream",
        },
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

    # Show main menu instead of directly loading app list
    __show_main_menu(view_manager)

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

    global _app_state, _selected_app_id, _current_file_index, _files_to_download
    global _download_all_mode, _current_app_index, _total_apps_to_download
    global _installed_apps, _update_check_data, _app_menu

    inp = view_manager.input_manager
    button = inp.button

    # Handle BUTTON_BACK based on current state
    if button == BUTTON_BACK:
        inp.reset()
        if _app_state == STATE_MAIN_MENU:
            # Exit app from main menu
            view_manager.back()
            return
        if _app_state == STATE_APP_LIST:
            # Go back to main menu from app list
            __show_main_menu(view_manager)
            return
        if _app_state == STATE_APP_DETAILS:
            # Go back to app list from details
            _app_state = STATE_APP_LIST
            if _app_menu:
                view_manager.draw.erase()
                _app_menu.draw()
            return
        if _app_state == STATE_CURRENT_APPS_LIST:
            # Go back to main menu from current apps list
            __show_main_menu(view_manager)
            return
        if _app_state == STATE_CURRENT_APP_DETAILS:
            # Go back to current apps list
            _app_state = STATE_CURRENT_APPS_LIST
            if _app_menu:
                view_manager.draw.erase()
                _app_menu.draw()
            return
        if _app_state == STATE_UPDATES_LIST:
            # Go back to main menu from updates list
            __show_main_menu(view_manager)
            return

        # From loading states, go back to main menu
        __show_main_menu(view_manager)
        return

    # Main menu state
    if _app_state == STATE_MAIN_MENU:
        if button in (BUTTON_UP, BUTTON_LEFT):
            inp.reset()
            if _main_menu:
                _main_menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            inp.reset()
            if _main_menu:
                _main_menu.scroll_down()
        elif button == BUTTON_CENTER:
            inp.reset()
            if _main_menu:
                selected_index = _main_menu.selected_index
                if selected_index == 0:  # Update Apps
                    if __check_updates_async(view_manager):
                        _app_state = STATE_CHECKING_UPDATES
                        __loading_start(view_manager, "Checking for updates...")
                    else:
                        view_manager.alert("No installed apps found", False)
                elif selected_index == 1:  # Current App Info
                    _installed_apps = __get_installed_apps(view_manager)
                    if _installed_apps:
                        # Create menu for installed apps
                        if _app_menu:
                            del _app_menu
                        from picoware.gui.menu import Menu

                        draw = view_manager.draw
                        _app_menu = Menu(
                            draw,
                            "Installed Apps",
                            0,
                            draw.size.y,
                            view_manager.foreground_color,
                            view_manager.background_color,
                        )
                        _app_menu.clear()
                        for app in _installed_apps:
                            _app_menu.add_item(f"{app['title']} v{app['version']}")
                        _app_state = STATE_CURRENT_APPS_LIST
                        _app_menu.draw()
                    else:
                        view_manager.alert("No installed apps found", False)
                elif selected_index == 2:  # View All Apps
                    if __fetch_app_list(view_manager):
                        _app_state = STATE_LOADING_LIST
                        __loading_start(view_manager, "Loading apps...")
                    else:
                        view_manager.alert("Failed to fetch app list", False)

    elif _app_state == STATE_CHECKING_UPDATES:
        # Show loading animation while checking for updates
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()
            return

        if _loading:
            _loading.stop()

        # Parse update check response
        if __parse_update_check(view_manager):
            _app_state = STATE_UPDATES_LIST
            if _app_menu:
                _app_menu.draw()
        else:
            view_manager.alert("Failed to check updates", False)
            __show_main_menu(view_manager)

    elif _app_state == STATE_UPDATES_LIST:
        # Handle updates list navigation
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
            if _app_menu and _updates_available:
                selected_index = _app_menu.selected_index
                if selected_index == 0:  # Update All
                    # Start downloading all updates
                    _download_all_mode = True
                    _current_app_index = 0
                    _total_apps_to_download = len(_updates_available)
                    if _total_apps_to_download > 0:
                        _selected_app_id = _updates_available[0]["id"]
                        if __fetch_app_details(view_manager, _selected_app_id):
                            _app_state = STATE_LOADING_UPDATE_DETAILS
                            __loading_start(
                                view_manager,
                                f"Loading update 1/{_total_apps_to_download}...",
                            )
                        else:
                            view_manager.alert("Failed to fetch app details", False)
                            _download_all_mode = False
                elif 1 <= selected_index <= len(_updates_available):
                    # Download single update
                    _selected_app_id = _updates_available[selected_index - 1]["id"]
                    _download_all_mode = False
                    if __fetch_app_details(view_manager, _selected_app_id):
                        _app_state = STATE_LOADING_UPDATE_DETAILS
                        __loading_start(view_manager, "Loading update...")
                    else:
                        view_manager.alert("Failed to fetch app details", False)

    elif _app_state == STATE_LOADING_UPDATE_DETAILS:
        # Loading update details
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()
            return

        if _loading:
            _loading.stop()

        # Parse app details and start downloading
        if __parse_app_details(view_manager, _selected_app_id):
            if _selected_app_details and _selected_app_details.file_downloads:
                _files_to_download = _selected_app_details.file_downloads
                _current_file_index = 0

                if __download_next_file(view_manager):
                    _app_state = STATE_DOWNLOADING_UPDATES
                    __loading_start(
                        view_manager, f"Downloading 1/{len(_files_to_download)}..."
                    )
                else:
                    view_manager.alert("Failed to start download", False)
                    _app_state = STATE_UPDATES_LIST
                    if _app_menu:
                        _app_menu.draw()
            else:
                view_manager.alert("No files to download", False)
                _app_state = STATE_UPDATES_LIST
                if _app_menu:
                    _app_menu.draw()
        else:
            view_manager.alert("Failed to load update details", False)
            _app_state = STATE_UPDATES_LIST
            if _app_menu:
                _app_menu.draw()

    elif _app_state == STATE_DOWNLOADING_UPDATES:
        # Handle update file downloads
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
                # Move to next app in update all mode
                _current_app_index += 1
                if _current_app_index < _total_apps_to_download:
                    _selected_app_id = _updates_available[_current_app_index]["id"]
                    if __fetch_app_details(view_manager, _selected_app_id):
                        _app_state = STATE_LOADING_UPDATE_DETAILS
                        __loading_start(
                            view_manager,
                            f"Loading update {_current_app_index + 1}/{_total_apps_to_download}...",
                        )
                    else:
                        view_manager.alert(
                            f"Failed to fetch update {_current_app_index + 1}", False
                        )
                        _download_all_mode = False
                        _app_state = STATE_UPDATES_LIST
                        if _app_menu:
                            _app_menu.draw()
                else:
                    # All updates downloaded
                    _download_all_mode = False
                    view_manager.alert(
                        f"All {_total_apps_to_download} updates installed!", False
                    )
                    __show_main_menu(view_manager)
            else:
                # Single update complete
                view_manager.alert("Update installed successfully!", False)
                __show_main_menu(view_manager)

    elif _app_state == STATE_CURRENT_APPS_LIST:
        # Handle current apps list navigation
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
            if _app_menu and _installed_apps:
                selected_index = _app_menu.selected_index
                if 0 <= selected_index < len(_installed_apps):
                    app_info = _installed_apps[selected_index]
                    _selected_app_id = app_info["id"]
                    _update_check_data = None
                    __draw_current_app_details(view_manager, app_info)
                    _app_state = STATE_CURRENT_APP_DETAILS

    elif _app_state == STATE_CURRENT_APP_DETAILS:
        # Handle current app details screen
        if button == BUTTON_CENTER:
            inp.reset()
            # Check for update for this specific app
            app_info = None
            for app in _installed_apps:
                if app["id"] == _selected_app_id:
                    app_info = app
                    break

            if app_info:
                if _update_check_data and _update_check_data.get("is_update_available"):
                    # Download the update
                    if __fetch_app_details(view_manager, _selected_app_id):
                        _app_state = STATE_LOADING_UPDATE_DETAILS
                        _download_all_mode = False
                        __loading_start(view_manager, "Loading update...")
                    else:
                        view_manager.alert("Failed to fetch update", False)
                else:
                    # Check for update
                    if __check_single_app_update(
                        view_manager, _selected_app_id, app_info["version"]
                    ):
                        _app_state = STATE_CHECKING_APP_UPDATE
                        __loading_start(view_manager, "Checking for update...")
                    else:
                        view_manager.alert("Failed to check update", False)

    elif _app_state == STATE_CHECKING_APP_UPDATE:
        # Checking single app update
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()
            return

        if _loading:
            _loading.stop()

        # Parse single app update check
        storage = view_manager.storage
        file_path = f"picoware/cache/update_check_{_selected_app_id}.json"

        try:
            data = storage.read(file_path)
            if data:
                from json import loads

                _update_check_data = loads(data)

                # Find the app info
                app_info = None
                for app in _installed_apps:
                    if app["id"] == _selected_app_id:
                        app_info = app
                        break

                if app_info:
                    __draw_current_app_details(
                        view_manager, app_info, _update_check_data
                    )
                    _app_state = STATE_CURRENT_APP_DETAILS
                else:
                    view_manager.alert("App info not found", False)
                    _app_state = STATE_CURRENT_APPS_LIST
                    if _app_menu:
                        _app_menu.draw()
            else:
                view_manager.alert("Failed to check update", False)
                _app_state = STATE_CURRENT_APPS_LIST
                if _app_menu:
                    _app_menu.draw()
        except Exception as e:
            print(f"Error parsing update check: {e}")
            view_manager.alert("Failed to check update", False)
            _app_state = STATE_CURRENT_APPS_LIST
            if _app_menu:
                _app_menu.draw()

    elif _app_state == STATE_LOADING_LIST:
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
            _app_state = STATE_MAIN_MENU
            __show_main_menu(view_manager)

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
