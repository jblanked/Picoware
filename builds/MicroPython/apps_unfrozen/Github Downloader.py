# picoware/apps/Github Downloader.py

from micropython import const
from json import loads
from picoware.system.buttons import BUTTON_BACK

STATE_KEYBOARD_AUTHOR = const(0)
STATE_KEYBOARD_REPO = const(1)
STATE_DOWNLOADING_INFO = const(2)
STATE_DOWNLOADING_REPO = const(3)


_app_state: int = STATE_KEYBOARD_AUTHOR
_github_author: str = ""
_github_repo: str = ""
_current_file_index: int = 0
_http = None
_loading = None
_total_files: int = 0
_github_alert = None
_download_queue: list = []


def __download_repo_info(view_manager) -> bool:
    """Create necessary directories and start downloading repo info"""
    storage = view_manager.storage
    if not storage.mkdir(f"picoware/github/{_github_author}"):
        return False
    if not storage.mkdir(f"picoware/github/{_github_author}/{_github_repo}"):
        return False

    global _http

    from picoware.system.http import HTTP

    if not _http:
        _http = HTTP(thread_manager=view_manager.thread_manager)

    url = f"https://api.github.com/repos/{_github_author}/{_github_repo}/git/trees/HEAD?recursive=1"

    return _http.get_async(
        url,
        save_to_file=f"picoware/github/{_github_author}-{_github_repo}-info.json",
        storage=storage,
        headers={
            "User-Agent": "Raspberry Pi Pico W",
            "Content-Type": "application/octet-stream",
        },
    )


def __parse_repo_info(view_manager) -> bool:
    """Parse the downloaded repo info and build download queue in memory"""
    global _github_author, _github_repo, _total_files, _download_queue
    storage = view_manager.storage

    file_path = f"picoware/github/{_github_author}-{_github_repo}-info.json"
    _total_files = 0
    _download_queue = []

    _http.close()

    # Read entire file at once
    file_content = storage.read(file_path)
    if not file_content:
        print("Failed to read repository info file")
        return False

    # Parse the JSON to get the tree array
    try:
        data = loads(file_content)
        tree = data.get("tree", [])

        for entry in tree:
            if entry.get("type") == "blob":
                path = entry.get("path")
                if path:
                    file_url = f"https://raw.githubusercontent.com/{_github_author}/{_github_repo}/HEAD/{path}"
                    save_path = (
                        f"picoware/github/{_github_author}/{_github_repo}/{path}"
                    )
                    _download_queue.append((file_url, save_path))
                    print(f"Queued: {path}")
                    _total_files += 1

    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return False

    if _total_files == 0:
        print("No files to download found in repository")
        return False

    return True


def __download_next_file(view_manager) -> bool:
    """Download the next file in the queue"""
    global _current_file_index, _total_files, _http, _download_queue

    if _current_file_index >= _total_files:
        print("All files downloaded")
        return False  # All files downloaded

    storage = view_manager.storage

    if _current_file_index >= len(_download_queue):
        print("Current index exceeds queue length")
        return False

    file_url, save_path = _download_queue[_current_file_index]

    # Create necessary directories
    dir_path = "/".join(save_path.split("/")[:-1])
    if not storage.mkdir(dir_path):
        print(f"Failed to create directory: {dir_path}")
        # Directory might already exist, continue anyway

    print(f"Downloading {file_url} to {save_path}")

    return _http.get_async(
        file_url,
        save_to_file=save_path,
        storage=storage,
        headers={
            "User-Agent": "Raspberry Pi Pico W",
            "Content-Type": "application/octet-stream",
        },
    )


def __loading_start(view_manager, text: str = "Fetching...") -> None:
    """Start loading animation"""
    from picoware.gui.loading import Loading

    global _loading

    if not _loading:
        _loading = Loading(view_manager.draw)
    _loading.set_text(text)


def __reset(view_manager) -> None:
    """Reset the app state"""
    global _app_state, _github_author, _github_repo, _http, _loading, _current_file_index, _total_files, _github_alert, _download_queue
    _app_state = STATE_KEYBOARD_AUTHOR
    _github_author = ""
    _github_repo = ""
    _current_file_index = 0
    _total_files = 0
    _download_queue = []
    if _http:
        del _http
        _http = None
    if _loading:
        del _loading
        _loading = None
    if _github_alert:
        del _github_alert
        _github_alert = None


def start(view_manager) -> bool:
    """Start the app"""
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

    if not view_manager.storage.mkdir("picoware/github"):
        view_manager.alert("Failed to create storage directory", False)
        return False

    view_manager.freq(True)  # set to lower frequency

    __reset(view_manager)
    keyboard = view_manager.keyboard
    keyboard.reset()
    keyboard.title = "Enter GitHub Author"
    keyboard.run(force=True)
    keyboard.run(force=True)
    return True


def run(view_manager) -> None:
    """Run the app"""
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    global _app_state, _github_author, _github_repo

    keyboard = view_manager.keyboard

    if _app_state == STATE_KEYBOARD_AUTHOR:
        if keyboard.is_finished:
            _github_author = keyboard.response
            keyboard.reset()
            _app_state = STATE_KEYBOARD_REPO
            keyboard.title = "Enter Repository Name"
            keyboard.run(force=True)
            keyboard.run(force=True)
            return
        if not keyboard.run():
            # back pressed, exit app
            view_manager.back()
            return
    elif _app_state == STATE_KEYBOARD_REPO:
        if keyboard.is_finished:
            _github_repo = keyboard.response
            keyboard.reset()
            _app_state = STATE_DOWNLOADING_INFO
            if not __download_repo_info(view_manager):
                view_manager.alert("Failed to start downloading repo info")
            else:
                __loading_start(view_manager, "Fetching...")
        if not keyboard.run():
            # back pressed, return to author input
            _app_state = STATE_KEYBOARD_AUTHOR
            keyboard.reset()
            keyboard.title = "Enter GitHub Author"
            keyboard.response = _github_author
            keyboard.run(force=True)
            keyboard.run(force=True)
            return
    elif _app_state == STATE_DOWNLOADING_INFO:
        global _http, _loading, _current_file_index
        if _http and not _http.is_request_complete():
            if _loading:
                _loading.animate()
            return
        if not __parse_repo_info(view_manager):
            view_manager.alert("Failed to parse repository info", True)
            return
        # Start downloading first file
        _current_file_index = 0
        if __download_next_file(view_manager):
            _app_state = STATE_DOWNLOADING_REPO
            __loading_start(view_manager, f"Downloading file 1/{_total_files}...")
        elif _total_files == 0:
            view_manager.alert("No files to download", True)
        else:
            view_manager.alert("Failed to start downloading files", True)
        return
    elif _app_state == STATE_DOWNLOADING_REPO:
        # Download files one-by-one
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()
            return

        # Move to next file
        _current_file_index += 1

        if _current_file_index < _total_files:
            if __download_next_file(view_manager):
                __loading_start(
                    view_manager,
                    f"Downloading file {_current_file_index + 1}/{_total_files}...",
                )
        else:
            # All files downloaded
            view_manager.alert("Repository downloaded successfully!", True)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    __reset(view_manager)
    view_manager.keyboard.reset()
    view_manager.freq()  # set to default frequency
    collect()
