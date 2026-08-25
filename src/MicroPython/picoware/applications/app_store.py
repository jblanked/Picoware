"""App Store - Browse, install, and update Picoware apps."""

from micropython import const
from json import loads, dumps

from picoware.gui.menu import Menu
from picoware.system.http import HTTP
from picoware.system.decorator import storage_required, wifi_required

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
STATE_SETTINGS_MENU = const(15)
STATE_SETTINGS_INPUT = const(16)
STATE_SUBMIT_FORM = const(17)
STATE_SUBMIT_INPUT = const(18)
STATE_SUBMIT_BROWSE = const(19)
STATE_SUBMITTING = const(20)
STATE_SUBMISSIONS_LOADING = const(21)
STATE_SUBMISSIONS_LIST = const(22)
STATE_SUBMISSION_DETAILS = const(23)

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
_main_menu = None
_update_check_data: dict = None
_submitter_name: str = ""
_submitter_email: str = ""
_submit_app_name: str = ""
_submit_app_version: str = ""
_submit_app_path: str = ""
_submissions_data: list = []
_submission_details: dict = None
_input_mode: str = ""
_file_browser = None
_keyboard_just_started: bool = False


def __reset() -> None:
    """Reset the app store state"""
    global _http, _loading, _files_to_download, _current_file_index, _app_menu
    global _app_state, _current_list_index, _apps_data, _selected_app_id, _selected_app_details
    global _download_all_mode, _current_app_index, _total_apps_to_download
    global _installed_apps, _updates_available, _main_menu, _update_check_data
    global _submitter_name, _submitter_email
    global _submit_app_name, _submit_app_version, _submit_app_path
    global _submissions_data, _submission_details
    global _input_mode, _file_browser, _keyboard_just_started
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
    if _file_browser:
        del _file_browser
        _file_browser = None
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
    _submit_app_name = ""
    _submit_app_version = ""
    _submit_app_path = ""
    _submissions_data = []
    _submission_details = None
    _input_mode = ""
    _keyboard_just_started = False


def __loading_start(view_manager, text: str = "Fetching...") -> None:
    """Start loading animation.

    Args:
        view_manager (ViewManager): The view manager context.
        text (str): The loading message. Defaults to "Fetching...".
    """

    global _loading

    if not _loading:
        from picoware.gui.loading import Loading
        _loading = Loading(
            view_manager.draw,
            view_manager.foreground_color,
            view_manager.background_color,
        )
    else:
        _loading.stop()
    _loading.set_text(text)


def __show_main_menu(view_manager) -> None:
    """Show the main App Store menu.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global _main_menu, _app_state

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
            view_manager.selected_color,
            view_manager.foreground_color,
        )

    _main_menu.clear()
    _main_menu.add_item("Update Apps")
    _main_menu.add_item("Downloaded Apps")
    _main_menu.add_item("View All Apps")
    _main_menu.add_item("Submit App")
    _main_menu.add_item("App Submissions")
    _main_menu.add_item("Settings")
    _main_menu.draw()
    _app_state = STATE_MAIN_MENU


def __get_installed_apps(view_manager) -> list:
    """Scan cache folder for installed app JSON files.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        list: App info dicts.
    """
    storage = view_manager.storage
    installed = []

    try:
        # List files in cache directory
        cache_files = storage.listdir("picoware/cache")
        if not cache_files:
            return []

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
                    view_manager.log(f"Error reading {filename}: {e}", 2)
                    continue
    except Exception as e:
        view_manager.log(f"Error listing cache files: {e}", 2)

    return installed


def __check_updates_async(view_manager) -> bool:
    """Start async request to check for updates for all installed apps.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True if the request was started.
    """
    global _http, _installed_apps

    _installed_apps = __get_installed_apps(view_manager)

    if not _installed_apps:
        return False

    if not _http:
        _http = HTTP(thread_manager=view_manager.thread_manager)

    # Build POST data for bulk update check
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
    """Parse update check response and populate updates list.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
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
            draw = view_manager.draw
            _app_menu = Menu(
                draw,
                "Available",
                0,
                draw.size.y,
                view_manager.foreground_color,
                view_manager.background_color,
                view_manager.selected_color,
                view_manager.foreground_color,
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
        view_manager.log(f"Error parsing update check: {e}", 2)
        return False


def __check_single_app_update(view_manager, app_id: int, current_version: str) -> bool:
    """Check for update for a single app.

    Args:
        view_manager (ViewManager): The view manager context.
        app_id (int): The app ID.
        current_version (str): The installed version.

    Returns:
        bool: True if the request was started.
    """
    global _http

    if not _http:
        _http = HTTP(thread_manager=view_manager.thread_manager)

    storage = view_manager.storage
    url = f"https://www.jblanked.com/picoware/api/app/{app_id}/check_update/{current_version}/"

    return _http.get_async(
        url,
        save_to_file=f"picoware/cache/update_check_{app_id}.json",
        storage=storage,
        headers={"User-Agent": "Raspberry Pi Pico W"},
    )


def __delete_app(view_manager, app_id: int) -> bool:
    """Delete an installed app's files and cached data.

    Args:
        view_manager (ViewManager): The view manager context.
        app_id (int): The app ID.

    Returns:
        bool: True on success.
    """
    storage = view_manager.storage
    file_path = f"picoware/cache/app_{app_id}.json"

    try:
        data = storage.read(file_path)
        if data:
            response = loads(data)
            if response.get("success") and response.get("app"):
                app_data = response["app"]
                for f in app_data.get("file_structure", []):
                    if not storage.remove(f):
                        view_manager.log(f"Error deleting {f}", 2)
        if not storage.remove(file_path):
            view_manager.log(f"Error deleting cache: {file_path}", 2)
        return True
    except Exception as e:
        view_manager.log(f"Error deleting app: {e}", 2)
        return False


def __draw_current_app_details(
    view_manager, app_info: dict, update_info: dict = None
) -> None:
    """Draw current app details with optional update info.

    Args:
        view_manager (ViewManager): The view manager context.
        app_info (dict): The installed app info.
        update_info (dict): The update check info. Defaults to None.
    """
    draw = view_manager.draw
    fg = view_manager.foreground_color

    draw.fill_screen(view_manager.background_color)

    # Title at top
    word_vec_x, word_vec_y = draw.scale(10, 5)
    title = app_info.get("title", "Unknown")
    version = app_info.get("version", "1.0.0")
    draw._text(word_vec_x, word_vec_y, f"{title[:draw.scale_x(35)]} v{version}", fg)

    # Description section
    description = app_info.get("description", "No description available")
    y_pos = draw.scale_y(30)

    # Word wrap the description
    max_chars = (draw.size.x // draw.font_size.x) - word_vec_x - 1
    words = description.split()
    current_line = ""

    word_vec_y = y_pos
    distance = draw.scale_y(15)
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if len(test_line) <= max_chars:
            current_line = test_line
        else:
            if current_line:
                word_vec_y = y_pos
                draw._text(word_vec_x, word_vec_y, current_line, fg)
                y_pos += distance
            current_line = word if len(word) <= max_chars else word[:max_chars]

    if current_line:
        word_vec_y = y_pos
        draw._text(word_vec_x, word_vec_y, current_line, fg)
        y_pos += distance

    # Authors
    y_pos += draw.scale_y(10)
    authors = app_info.get("authors", [])
    if authors:
        word_vec_y = y_pos
        draw._text(word_vec_x, word_vec_y, f"Authors: {', '.join(authors[:3])}", fg)
        y_pos += distance

    # Update status
    y_pos += draw.scale_y(10)
    word_vec_y = y_pos
    if update_info:
        if update_info.get("is_update_available"):
            latest = update_info.get("latest_version", "?")
            draw._text(word_vec_x, word_vec_y, f"Update available: v{latest}", fg)
            word_vec_y += distance
            draw._text(word_vec_x, word_vec_y, "CENTER = Download Update", fg)
        else:
            draw._text(word_vec_x, word_vec_y, "App is up to date!", fg)
    else:
        draw._text(word_vec_x, word_vec_y, "CENTER = Check for Update", fg)

    # Instructions at bottom
    word_vec_y = draw.scale_y(278)
    draw._text(word_vec_x, word_vec_y, "LEFT = Delete", fg)
    word_vec_y = draw.scale_y(293)
    draw._text(word_vec_x, word_vec_y, "BACK = Return", fg)

    draw.swap()


def __fetch_app_list(view_manager) -> bool:
    """Fetch the list of apps from the API.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True if the request was started.
    """
    global _http

    if not _http:
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
    """Parse the app list JSON and populate the menu.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    global _apps_data, _app_menu

    storage = view_manager.storage
    file_path = f"picoware/cache/app_list_{_current_list_index}.json"

    if not storage.exists(file_path):
        view_manager.log(f"App list file not found: {file_path}", 2)
        return False

    try:
        data = storage.read(file_path)
        if not data:
            return False

        _apps_data = loads(data)

        if not _apps_data.get("success") or not _apps_data.get("apps"):
            return False

        # Create menu if it doesn't exist
        if not _app_menu:
            draw = view_manager.draw
            _app_menu = Menu(
                draw,
                "App Store",
                0,
                draw.size.y,
                view_manager.foreground_color,
                view_manager.background_color,
                view_manager.selected_color,
                view_manager.foreground_color,
            )

        # Clear and populate menu
        _app_menu.clear()
        # Add "Download All" option at the top
        _app_menu.add_item("[Download All]")
        for app in _apps_data["apps"]:
            title = app.get("title", "Unknown App")
            _app_menu.add_item(title)

        return True
    except Exception as e:
        view_manager.log(f"Error parsing app list: {e}", 2)
        return False


def __fetch_app_details(view_manager, app_id: int) -> bool:
    """Fetch details for a specific app.

    Args:
        view_manager (ViewManager): The view manager context.
        app_id (int): The app ID.

    Returns:
        bool: True if the request was started.
    """
    global _http

    if not _http:
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
    """Parse app details from JSON.

    Args:
        view_manager (ViewManager): The view manager context.
        app_id (int): The app ID.

    Returns:
        bool: True on success.
    """
    global _selected_app_details

    storage = view_manager.storage
    file_path = f"picoware/cache/app_{app_id}.json"

    try:
        data = storage.read(file_path)
        if not data:
            return False

        from picoware.system.app import App

        response = loads(data)

        if not response.get("success") or not response.get("app"):
            return False

        _selected_app_details = App(response["app"])
        return True
    except Exception as e:
        view_manager.log(f"Error parsing app details: {e}", 2)
        return False


def __draw_app_details(view_manager) -> None:
    """Draw the app details screen with professional layout.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    if not _selected_app_details:
        return
    
    draw = view_manager.draw
    fg = view_manager.foreground_color

    draw.erase()

    # Title at top
    word_vec_x, word_vec_y = draw.scale(10, 5)
    title = _selected_app_details.title
    version = _selected_app_details.version
    draw._text(word_vec_x, word_vec_y, f"{title[:draw.scale_x(35)]} v{version}", fg)

    # Description section
    description = _selected_app_details.description
    y_pos = draw.scale_y(30)

    # Word wrap the description
    max_chars = (draw.size.x // draw.font_size.x) - word_vec_x - 1
    words = description.split()
    current_line = ""

    distance = draw.scale_y(15)
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if len(test_line) <= max_chars:
            current_line = test_line
        else:
            if current_line:
                word_vec_y = y_pos
                draw._text(word_vec_x, word_vec_y, current_line, fg)
                y_pos += distance
            current_line = word if len(word) <= max_chars else word[:max_chars]

    if current_line:
        word_vec_y = y_pos
        draw._text(word_vec_x, word_vec_y, current_line, fg)
        y_pos += distance

    # File structure section
    y_pos += draw.scale_y(10)
    word_vec_y = y_pos
    draw._text(word_vec_x, word_vec_y, "Files:", fg)
    y_pos += draw.scale_y(15)

    file_structure = _selected_app_details.file_structure
    file_count = len(file_structure)

    # Show first few files
    for file_path in file_structure[:5]:
        if y_pos > draw.scale_y(250):
            break
        # Shorten path if too long
        display_path = file_path if len(file_path) <= draw.scale_x(45) else "..." + file_path[-draw.scale_x(42):]
        word_vec_x, word_vec_y = draw.scale_x(15), y_pos
        draw._text(word_vec_x, word_vec_y, display_path, fg)
        y_pos += draw.scale_y(12)

    if file_count > 5:
        word_vec_x, word_vec_y = draw.scale_x(15), y_pos
        draw._text(word_vec_x, word_vec_y, f"...and {file_count - 5} more", fg)
        y_pos += draw.scale_y(12)

    # Instructions at bottom
    y_pos = draw.scale_y(285)
    word_vec_x, word_vec_y = draw.scale_x(10), y_pos
    draw._text(word_vec_x, word_vec_y, "CENTER = Install", fg)

    draw.swap()


def __download_next_file(view_manager) -> bool:
    """Download the next file in the queue.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True if the request was started.
    """
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
    if not storage.exists(dir_path):
        storage.mkdir(dir_path)

    if storage.exists(file_path):
        storage.remove(file_path)

    return _http.get_async(
        file_url,
        save_to_file=file_path,
        storage=storage,
        headers={
            "User-Agent": "Raspberry Pi Pico W",
            "Content-Type": "application/octet-stream",
        },
    )


def __load_settings(view_manager) -> None:
    """Load submitter name/email from persistent settings.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global _submitter_name, _submitter_email

    storage = view_manager.storage if view_manager else None
    if storage is None:
        return

    _path = "picoware/settings/app_store.json"

    try:
        if storage.exists(_path):
            data = storage.read(_path)
            if data:
                obj = loads(data)
                _submitter_name = obj.get("submitter_name", "")
                _submitter_email = obj.get("submitter_email", "")
    except Exception:
        pass


def __save_settings(view_manager) -> None:
    """Persist submitter name/email.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global _submitter_name, _submitter_email

    storage = view_manager.storage
    storage.mkdir("picoware/settings")

    data = dumps(
        {
            "submitter_name": _submitter_name,
            "submitter_email": _submitter_email,
        }
    )
    storage.write("picoware/settings/app_store.json", data)


def __draw_settings_menu(view_manager) -> None:
    """Draw the settings sub-menu showing current name and email.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    draw = view_manager.draw
    fg = view_manager.foreground_color
    draw.fill_screen(view_manager.background_color)

    vec_x, vec_y = draw.scale(10, 5)
    draw._text(vec_x, vec_y, "App Store Settings", fg)

    vec_y = draw.scale_y(30)
    name_display = _submitter_name if _submitter_name else "(not set)"
    draw._text(vec_x, vec_y, f"Name:  {name_display[:30]}", fg)

    vec_y = draw.scale_y(50)
    email_display = _submitter_email if _submitter_email else "(not set)"
    draw._text(vec_x, vec_y, f"Email: {email_display[:30]}", fg)

    vec_y = draw.scale_y(80)
    draw._text(vec_x, vec_y, "CENTER = Edit Name", fg)
    vec_y = draw.scale_y(95)
    draw._text(vec_x, vec_y, "RIGHT  = Edit Email", fg)
    vec_y = draw.scale_y(110)
    draw._text(vec_x, vec_y, "LEFT/DOWN = Clear All", fg)
    vec_y = draw.scale_y(130)
    draw._text(vec_x, vec_y, "BACK = Return", fg)

    draw.swap()


def __keyboard_save_callback(result: str) -> None:
    """Called when the keyboard 'Save' is pressed.

    Args:
        result (str): The typed text.
    """
    global _submitter_name, _submitter_email, _submit_app_name, _submit_app_version
    global _input_mode

    if _input_mode == "name":
        _submitter_name = result.strip()
    elif _input_mode == "email":
        _submitter_email = result.strip()
    elif _input_mode == "app_name":
        _submit_app_name = result.strip()
    elif _input_mode == "app_version":
        _submit_app_version = result.strip()


def __start_keyboard(view_manager, mode: str, title: str, initial: str) -> None:
    """Activate the on-screen keyboard for text input.

    Args:
        view_manager (ViewManager): The view manager context.
        mode (str): The input mode key.
        title (str): The keyboard title.
        initial (str): The initial response text.
    """
    global _input_mode, _keyboard_just_started

    _input_mode = mode
    kb = view_manager.keyboard
    kb.set_save_callback(__keyboard_save_callback)
    kb.title = title
    kb.response = initial
    view_manager.input_manager.reset()
    view_manager.draw.clear(color=view_manager.background_color)
    kb.run(force=True)
    _keyboard_just_started = True


def __draw_submit_form(view_manager) -> None:
    """Draw the submit app form screen.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    draw = view_manager.draw
    fg = view_manager.foreground_color
    draw.erase()

    vec_x, vec_y = draw.scale(10, 5)
    draw._text(vec_x, vec_y, "Submit an App", fg)

    vec_y = draw.scale_y(30)
    name_disp = _submit_app_name if _submit_app_name else "(not set)"
    draw._text(vec_x, vec_y, f"Name:    {name_disp[:draw.scale_x(27)]}", fg)

    vec_y = draw.scale_y(50)
    ver_disp = _submit_app_version if _submit_app_version else "(not set)"
    draw._text(vec_x, vec_y, f"Version: {ver_disp[:draw.scale_x(27)]}", fg)

    vec_y = draw.scale_y(70)
    path_disp = _submit_app_path if _submit_app_path else "(not set)"
    # Truncate long paths for display
    if draw.len(path_disp) > draw.scale_x(35):
        path_disp = "..." + path_disp[-draw.scale_x(32):]
    draw._text(vec_x, vec_y, f"File:    {path_disp}", fg)

    vec_y = draw.scale_y(100)
    draw._text(vec_x, vec_y, "CENTER = Edit Name", fg)
    vec_y = draw.scale_y(115)
    draw._text(vec_x, vec_y, "RIGHT  = Edit Version", fg)
    vec_y = draw.scale_y(130)
    draw._text(vec_x, vec_y, "DOWN   = Browse File", fg)
    vec_y = draw.scale_y(150)
    draw._text(vec_x, vec_y, "LEFT   = Submit", fg)

    # Require name/email to be set
    vec_y = draw.scale_y(180)
    if not _submitter_name or not _submitter_email:
        draw._text(vec_x, vec_y, "Set name & email in Settings first!", fg)

    vec_y = draw.scale_y(200)
    draw._text(vec_x, vec_y, "BACK = Return", fg)

    draw.swap()

def __base64_encode(view_managerr) -> bytes:
    """Base64 encode the contents of the given file.

    Args:
        view_managerr (ViewManager): The view manager context.

    Returns:
        bytes: The base64-encoded file contents.
    """
    import ubinascii
    return ubinascii.b2a_base64(view_managerr.storage.read(_submit_app_path))

def __submit_app(view_manager) -> bool:
    """POST the app submission to the API.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True if the request was started.
    """
    global _http

    if not _http:
        _http = HTTP(thread_manager=view_manager.thread_manager)

    payload = dumps(
        {
            "app_name": _submit_app_name,
            "app_version": _submit_app_version,
            "app_content": [
                {
                    "path": _submit_app_path,
                    "content": __base64_encode(view_manager),
                }
            ],
            "submitter_name": _submitter_name,
            "submitter_email": _submitter_email,
        }
    )

    return _http.post_async(
        "https://www.jblanked.com/picoware/api/submit_app/",
        payload=payload,
        headers={
            "Content-Type": "application/json",
            "HTTP_USER_AGENT": "Pico",
            "Setting": "X-Flipper-Redirect",
            "User-Agent": "Raspberry Pi Pico W",
        },
    )


def __fetch_submissions(view_manager) -> bool:
    """GET all submissions for the current submitter's email.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True if the request was started.
    """
    global _http

    if not _http:
        _http = HTTP(thread_manager=view_manager.thread_manager)

    storage = view_manager.storage
    storage.mkdir("picoware/cache")

    # URL-encode the email
    email_safe = _submitter_email.replace("@", "%40").replace(".", "%2E")
    url = f"https://www.jblanked.com/picoware/api/submissions/{email_safe}/"

    return _http.get_async(
        url,
        save_to_file="picoware/cache/submissions.json",
        storage=storage,
        headers={"User-Agent": "Raspberry Pi Pico W"},
    )


def __parse_submissions(view_manager) -> bool:
    """Parse the submissions list JSON and populate the menu.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    global _submissions_data, _app_menu

    storage = view_manager.storage
    file_path = "picoware/cache/submissions.json"

    if not storage.exists(file_path):
        return False

    try:
        data = storage.read(file_path)
        if not data:
            return False

        response = loads(data)

        if not response.get("success") or not response.get("submissions"):
            return False

        _submissions_data = response["submissions"]

        if not _app_menu:
            draw = view_manager.draw
            _app_menu = Menu(
                draw,
                "My Submissions",
                0,
                draw.size.y,
                view_manager.foreground_color,
                view_manager.background_color,
                view_manager.selected_color,
                view_manager.foreground_color,
            )

        _app_menu.clear()
        for sub in _submissions_data:
            status = sub.get("status", "?")
            name = sub.get("app_name", "Unknown")
            _app_menu.add_item(f"[{status}] {name}")

        return True
    except Exception as e:
        view_manager.log(f"Error parsing submissions: {e}", 2)
        return False


def __fetch_submission_details(view_manager, submission_id: int) -> bool:
    """GET a single submission's details.

    Args:
        view_manager (ViewManager): The view manager context.
        submission_id (int): The submission ID.

    Returns:
        bool: True if the request was started.
    """
    global _http

    if not _http:
        _http = HTTP(thread_manager=view_manager.thread_manager)

    storage = view_manager.storage
    storage.mkdir("picoware/cache")

    url = f"https://www.jblanked.com/picoware/api/submission/{submission_id}/"

    return _http.get_async(
        url,
        save_to_file=f"picoware/cache/submission_{submission_id}.json",
        storage=storage,
        headers={"User-Agent": "Raspberry Pi Pico W"},
    )


def __parse_submission_details(view_manager, submission_id: int) -> bool:
    """Parse single submission details from JSON.

    Args:
        view_manager (ViewManager): The view manager context.
        submission_id (int): The submission ID.

    Returns:
        bool: True on success.
    """
    global _submission_details

    storage = view_manager.storage
    file_path = f"picoware/cache/submission_{submission_id}.json"

    try:
        data = storage.read(file_path)
        if not data:
            return False

        response = loads(data)

        if not response.get("success") or not response.get("submission"):
            return False

        _submission_details = response["submission"]
        return True
    except Exception as e:
        view_manager.log(f"Error parsing submission details: {e}", 2)
        return False


def __draw_submission_details(view_manager) -> None:
    """Draw the submission detail screen.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    if not _submission_details:
        return
    
    draw = view_manager.draw
    fg = view_manager.foreground_color

    draw.erase()

    vec_x, vec_y = draw.scale(10, 5)
    name = _submission_details.get("app_name", "Unknown")
    version = _submission_details.get("app_version", "?")
    draw._text(vec_x, vec_y, f"{name[:draw.scale_x(30)]} v{version}", fg)

    vec_y = draw.scale_y(25)
    status = _submission_details.get("status", "?")
    draw._text(vec_x, vec_y, f"Status: {status}", fg)

    vec_y = draw.scale_y(40)
    sub_name = _submission_details.get("submitter_name", "")
    draw._text(vec_x, vec_y, f"Submitter: {sub_name[:draw.scale_x(30)]}", fg)

    vec_y = draw.scale_y(55)
    sub_email = _submission_details.get("submitter_email", "")
    draw._text(vec_x, vec_y, f"Email: {sub_email[:draw.scale_x(30)]}", fg)

    vec_y = draw.scale_y(70)
    submitted_at = _submission_details.get("submitted_at", "")
    draw._text(vec_x, vec_y, f"Submitted: {submitted_at[:draw.scale_x(25)]}", fg)

    # App content / file structure
    content = _submission_details.get("app_content", [])
    if content and isinstance(content, list) and len(content) > 0:
        vec_y = draw.scale_y(95)
        draw._text(vec_x, vec_y, "Files:", fg)
        y_pos = draw.scale_y(110)
        for fp in content[:8]:
            if y_pos > draw.scale_y(260):
                break
            disp = fp.get("path", "") if draw.len(fp.get("path", "")) <= draw.scale_x(45) else "..." + fp.get("path", "")[-(draw.scale_x(42)):]
            vec_x, vec_y = draw.scale_x(15), y_pos
            draw._text(vec_x, vec_y, disp, fg)
            y_pos += draw.scale_y(12)

    vec_x, vec_y = draw.scale(10, 290)
    draw._text(vec_x, vec_y, "BACK = Return", fg)

    draw.swap()

@storage_required
@wifi_required
def start(view_manager) -> bool:
    """Start the app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    __reset()

    # Load persisted submitter name/email
    __load_settings(view_manager)

    # Show main menu instead of directly loading app list
    __show_main_menu(view_manager)

    return True


def run(view_manager) -> None:
    """Run the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
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
    global _submitter_name, _submitter_email
    global _submit_app_name, _submit_app_version, _submit_app_path
    global _submission_details
    global  _file_browser, _keyboard_just_started

    button = view_manager.button

    # Handle BUTTON_BACK based on current state
    if button == BUTTON_BACK:
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
        if _app_state == STATE_SETTINGS_MENU:
            __show_main_menu(view_manager)
            return
        if _app_state == STATE_SETTINGS_INPUT:
            # Abort keyboard, return to settings
            _app_state = STATE_SETTINGS_MENU
            __draw_settings_menu(view_manager)
            return
        if _app_state == STATE_SUBMIT_FORM:
            __show_main_menu(view_manager)
            return
        if _app_state == STATE_SUBMIT_INPUT:
            # Abort keyboard, return to submit form
            _app_state = STATE_SUBMIT_FORM
            __draw_submit_form(view_manager)
            return
        if _app_state == STATE_SUBMIT_BROWSE:
            # Abort file browser, return to submit form
            if _file_browser:
                del _file_browser
                _file_browser = None
            _app_state = STATE_SUBMIT_FORM
            __draw_submit_form(view_manager)
            return
        if _app_state == STATE_SUBMISSIONS_LIST:
            __show_main_menu(view_manager)
            return
        if _app_state == STATE_SUBMISSION_DETAILS:
            _submission_details = None
            _app_state = STATE_SUBMISSIONS_LIST
            if _app_menu:
                view_manager.draw.erase()
                _app_menu.draw()
            return

        # From loading states, go back to main menu
        __show_main_menu(view_manager)
        return

    # Main menu state
    if _app_state == STATE_MAIN_MENU:
        if button in (BUTTON_UP, BUTTON_LEFT):
            if _main_menu:
                _main_menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            if _main_menu:
                _main_menu.scroll_down()
        elif button == BUTTON_CENTER:
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

                        draw = view_manager.draw
                        _app_menu = Menu(
                            draw,
                            "Installed Apps",
                            0,
                            draw.size.y,
                            view_manager.foreground_color,
                            view_manager.background_color,
                            view_manager.selected_color,
                            view_manager.foreground_color,
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
                elif selected_index == 3:  # Submit App
                    _submit_app_name = ""
                    _submit_app_version = ""
                    _submit_app_path = ""
                    _app_state = STATE_SUBMIT_FORM
                    __draw_submit_form(view_manager)
                elif selected_index == 4:  # App Submissions
                    if not _submitter_email:
                        view_manager.alert(
                            "Set your email in Settings first", False
                        )
                    elif __fetch_submissions(view_manager):
                        _app_state = STATE_SUBMISSIONS_LOADING
                        __loading_start(view_manager, "Loading submissions...")
                    else:
                        view_manager.alert("Failed to fetch submissions", False)
                elif selected_index == 5:  # Settings
                    _app_state = STATE_SETTINGS_MENU
                    __draw_settings_menu(view_manager)

    elif _app_state == STATE_CHECKING_UPDATES:
        # Show loading animation while checking for updates
        if not _http.is_request_complete():
            if _loading:
                _loading.animate(http=_http)
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
            if _app_menu:
                _app_menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            if _app_menu:
                _app_menu.scroll_down()
        elif button == BUTTON_CENTER:
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
                _loading.animate(http=_http)
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
                _loading.animate(http=_http)
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
            if _app_menu:
                _app_menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            if _app_menu:
                _app_menu.scroll_down()
        elif button == BUTTON_CENTER:
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
        if button == BUTTON_LEFT:
            # Delete the selected app
            if __delete_app(view_manager, _selected_app_id):
                view_manager.alert("App deleted!", False)
                _installed_apps = __get_installed_apps(view_manager)
                if _installed_apps:
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
                        view_manager.selected_color,
                        view_manager.foreground_color,
                    )
                    _app_menu.clear()
                    for app in _installed_apps:
                        _app_menu.add_item(f"{app['title']} v{app['version']}")
                    _app_state = STATE_CURRENT_APPS_LIST
                    _app_menu.draw()
                else:
                    __show_main_menu(view_manager)
            else:
                view_manager.alert("Failed to delete app", False)
        elif button == BUTTON_CENTER:
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
                _loading.animate(http=_http)
            return

        if _loading:
            _loading.stop()

        # Parse single app update check
        storage = view_manager.storage
        file_path = f"picoware/cache/update_check_{_selected_app_id}.json"

        try:
            data = storage.read(file_path)
            if data:
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
            view_manager.log(f"Error parsing update check: {e}", 2)
            view_manager.alert("Failed to check update", False)
            _app_state = STATE_CURRENT_APPS_LIST
            if _app_menu:
                _app_menu.draw()

    elif _app_state == STATE_LOADING_LIST:
        # Show loading animation while fetching app list
        if not _http.is_request_complete():
            if _loading:
                _loading.animate(http=_http)
            return

        del _http
        _http = None

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
            if _app_menu:
                _app_menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            if _app_menu:
                _app_menu.scroll_down()
        elif button == BUTTON_CENTER:
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
                _loading.animate(http=_http)
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
            # Go back to app list
            _app_state = STATE_APP_LIST
            if _app_menu:
                _app_menu.draw()
        elif button == BUTTON_CENTER:
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
                _loading.animate(http=_http)
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
                _loading.animate(http=_http)
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

    elif _app_state == STATE_SETTINGS_MENU:
        if button == BUTTON_CENTER:
            __start_keyboard(
                view_manager,
                "name",
                "Enter your name:",
                _submitter_name,
            )
            _app_state = STATE_SETTINGS_INPUT
        elif button == BUTTON_RIGHT:
            __start_keyboard(
                view_manager,
                "email",
                "Enter your email:",
                _submitter_email,
            )
            _app_state = STATE_SETTINGS_INPUT
        elif button in (BUTTON_LEFT, BUTTON_DOWN):
            _submitter_name = ""
            _submitter_email = ""
            __save_settings(view_manager)
            __draw_settings_menu(view_manager)

    elif _app_state == STATE_SETTINGS_INPUT:
        kb = view_manager.keyboard
        if kb is None:
            return

        if not _keyboard_just_started:
            kb.run(force=True)
            _keyboard_just_started = True
        else:
            result = kb.run()
            if not result:
                kb.reset()
                view_manager.input_manager.reset()
                __save_settings(view_manager)
                _app_state = STATE_SETTINGS_MENU
                __draw_settings_menu(view_manager)
                return

        if kb.is_save_pressed:
            kb.reset()
            _keyboard_just_started = False
            __save_settings(view_manager)
            _app_state = STATE_SETTINGS_MENU
            __draw_settings_menu(view_manager)

    elif _app_state == STATE_SUBMIT_FORM:
        if button == BUTTON_CENTER:
            __start_keyboard(
                view_manager,
                "app_name",
                "App name:",
                _submit_app_name,
            )
            _app_state = STATE_SUBMIT_INPUT
        elif button == BUTTON_RIGHT:
            __start_keyboard(
                view_manager,
                "app_version",
                "App version:",
                _submit_app_version,
            )
            _app_state = STATE_SUBMIT_INPUT
        elif button == BUTTON_DOWN:
            from picoware.gui.file_browser import FileBrowser, FILE_BROWSER_SELECTOR

            _file_browser = FileBrowser(
                view_manager,
                mode=FILE_BROWSER_SELECTOR,
                start_directory="/",
                allowed_extensions=["py"],
            )
            _app_state = STATE_SUBMIT_BROWSE
        elif button == BUTTON_LEFT:
            # Submit
            if not _submit_app_name or not _submit_app_version:
                view_manager.alert(
                    "App name and version are required", False
                )
                __draw_submit_form(view_manager)
            elif not _submitter_name or not _submitter_email:
                view_manager.alert(
                    "Set your name & email in Settings first", False
                )
                __draw_submit_form(view_manager)
            elif not _submit_app_path:
                view_manager.alert("Select a file first (DOWN)", False)
                __draw_submit_form(view_manager)
            elif __submit_app(view_manager):
                _app_state = STATE_SUBMITTING
                __loading_start(view_manager, "Submitting app...")
            else:
                view_manager.alert("Failed to submit app", False)
                __draw_submit_form(view_manager)

    elif _app_state == STATE_SUBMIT_INPUT:
        kb = view_manager.keyboard
        if kb is None:
            return

        if not _keyboard_just_started:
            kb.run(force=True)
            _keyboard_just_started = True
        else:
            result = kb.run()
            if not result:
                kb.reset()
                view_manager.input_manager.reset()
                _app_state = STATE_SUBMIT_FORM
                __draw_submit_form(view_manager)
                return

        if kb.is_save_pressed:
            kb.reset()
            _keyboard_just_started = False
            _app_state = STATE_SUBMIT_FORM
            __draw_submit_form(view_manager)

    elif _app_state == STATE_SUBMIT_BROWSE:
        if _file_browser is None:
            _app_state = STATE_SUBMIT_FORM
            __draw_submit_form(view_manager)
            return

        continue_browsing = _file_browser.run()

        if not continue_browsing:
            selected_path = _file_browser.path
            is_exit = _file_browser.mode == _file_browser.MODE_EXIT

            del _file_browser
            _file_browser = None

            if selected_path and not is_exit:
                _submit_app_path = selected_path

            _app_state = STATE_SUBMIT_FORM
            __draw_submit_form(view_manager)

    elif _app_state == STATE_SUBMITTING:
        if not _http.is_request_complete():
            if _loading:
                _loading.animate(http=_http)
            return

        if _loading:
            _loading.stop()

        try:
            response = _http.response.json()
        except Exception:
            response = {}

        if response.get("success"):
            sub_id = response.get("submission_id", "?")
            view_manager.alert(
                f"App submitted! (ID: {sub_id})", False
            )
            # return to main menu
            _app_state = STATE_MAIN_MENU
            __show_main_menu(view_manager)
            return

        error = response.get("error", "Unknown error")
        view_manager.alert(f"Submission failed: {error}", False)

        _app_state = STATE_SUBMIT_FORM
        __draw_submit_form(view_manager)

    elif _app_state == STATE_SUBMISSIONS_LOADING:
        if not _http.is_request_complete():
            if _loading:
                _loading.animate(http=_http)
            return

        if _loading:
            _loading.stop()

        if __parse_submissions(view_manager):
            _app_state = STATE_SUBMISSIONS_LIST
            if _app_menu:
                _app_menu.draw()
        else:
            view_manager.alert("No submissions found", False)
            __show_main_menu(view_manager)

    elif _app_state == STATE_SUBMISSIONS_LIST:
        if button in (BUTTON_UP, BUTTON_LEFT):
            if _app_menu:
                _app_menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            if _app_menu:
                _app_menu.scroll_down()
        elif button == BUTTON_CENTER:
            if _app_menu and _submissions_data:
                selected_index = _app_menu.selected_index
                if 0 <= selected_index < len(_submissions_data):
                    sub_id = _submissions_data[selected_index]["id"]
                    _submission_details = None  # Reset for new fetch
                    if __fetch_submission_details(view_manager, sub_id):
                        _app_state = STATE_SUBMISSION_DETAILS
                        __loading_start(view_manager, "Loading details...")
                    else:
                        view_manager.alert(
                            "Failed to fetch submission details", False
                        )

    elif _app_state == STATE_SUBMISSION_DETAILS:
        # Still loading submission details
        if _http and not _http.is_request_complete():
            if _loading:
                _loading.animate(http=_http)
            return

        # Parse and draw once
        if _loading and _http and _submission_details is None:
            _loading.stop()

            idx = _app_menu.selected_index if _app_menu else 0
            if _submissions_data and 0 <= idx < len(_submissions_data):
                sub_id = _submissions_data[idx]["id"]
                if __parse_submission_details(view_manager, sub_id):
                    __draw_submission_details(view_manager)
                else:
                    view_manager.alert("Failed to parse details", False)
                    _app_state = STATE_SUBMISSIONS_LIST
                    if _app_menu:
                        _app_menu.draw()
            else:
                view_manager.alert("Submission not found", False)
                _app_state = STATE_SUBMISSIONS_LIST
                if _app_menu:
                    _app_menu.draw()


def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from gc import collect

    __reset()

    collect()
