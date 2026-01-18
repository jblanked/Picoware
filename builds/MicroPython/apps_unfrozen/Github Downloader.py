# picoware/apps/Github Downloader.py

from micropython import const

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
_files_to_download: list = []
_github_alert = None


def __download_repo_info(view_manager) -> bool:
    """Create necessary directories and start downloading repo info"""
    storage = view_manager.storage
    storage.mkdir("picoware/github")
    storage.mkdir(f"picoware/github/{_github_author}")
    storage.mkdir(f"picoware/github/{_github_author}/{_github_repo}")
    global _http
    from picoware.system.http import HTTP

    if not _http:
        _http = HTTP()

    url = f"https://api.github.com/repos/{_github_author}/{_github_repo}/git/trees/HEAD?recursive=1"

    return _http.get_async(
        url,
        save_to_file=f"picoware/github/{_github_author}-{_github_repo}-info.json",
        storage=storage,
        headers={"User-Agent": "Raspberry Pi Pico W"},
    )


def __parse_repo_info(view_manager) -> bool:
    """Parse the downloaded repo info and build list of files to download using chunked reading"""
    global _github_author, _github_repo, _files_to_download
    storage = view_manager.storage

    file_path = f"picoware/github/{_github_author}-{_github_repo}-info.json"
    _files_to_download = []

    # Read file in chunks to avoid memory issues
    chunk_size = 4096  # 4KB chunks
    offset = 0
    buffer = b""
    in_tree_array = False
    brace_count = 0
    current_entry = b""

    while True:
        chunk = storage.read_chunked(file_path, start=offset, chunk_size=chunk_size)
        if not chunk:
            break

        buffer += chunk
        offset += len(chunk)

        # Process the buffer
        while buffer:
            if not in_tree_array:
                # Look for the "tree" array start
                tree_start = buffer.find(b'"tree"')
                if tree_start != -1:
                    # Find the opening bracket after "tree":
                    bracket_pos = buffer.find(b"[", tree_start)
                    if bracket_pos != -1:
                        in_tree_array = True
                        buffer = buffer[bracket_pos + 1 :]
                        continue
                # If not found, keep last 20 bytes in case "tree" is split
                if len(buffer) > 20:
                    buffer = buffer[-20:]
                break
            else:
                # We're inside the tree array, parse entries
                if not current_entry:
                    # Skip whitespace
                    buffer = buffer.lstrip()
                    if not buffer:
                        break
                    # Check if we've reached the end of the array
                    if buffer[0:1] == b"]":
                        return True  # Successfully parsed all entries
                    # Start of new entry
                    if buffer[0:1] == b"{":
                        current_entry = b"{"
                        brace_count = 1
                        buffer = buffer[1:]

                # Build up the current entry
                while buffer and brace_count > 0:
                    char = buffer[0:1]
                    current_entry += char
                    buffer = buffer[1:]

                    if char == b"{":
                        brace_count += 1
                    elif char == b"}":
                        brace_count -= 1

                    if brace_count == 0:
                        # Complete entry found, parse it
                        try:
                            from json import loads

                            entry_str = current_entry.decode("utf-8")
                            tree = loads(entry_str)

                            if tree.get("type") == "blob":
                                path = tree.get("path")
                                if path:
                                    file_url = f"https://raw.githubusercontent.com/{_github_author}/{_github_repo}/HEAD/{path}"
                                    save_path = f"picoware/github/{_github_author}/{_github_repo}/{path}"
                                    _files_to_download.append((file_url, save_path))
                        except Exception as e:
                            print(f"Error parsing entry: {e}")

                        current_entry = b""
                        # Skip comma and whitespace
                        buffer = buffer.lstrip()
                        if buffer and buffer[0:1] == b",":
                            buffer = buffer[1:]
                        break

                # If buffer is empty but we haven't completed the entry, get more data
                if not buffer and current_entry and brace_count > 0:
                    break

        # If we've processed everything in the buffer and need more data
        if not buffer or (in_tree_array and current_entry and brace_count > 0):
            continue

        # If chunk was smaller than chunk_size, we've reached EOF
        if len(chunk) < chunk_size:
            break

    return len(_files_to_download) > 0


def __download_next_file(view_manager) -> bool:
    """Download the next file in the queue"""
    global _current_file_index, _files_to_download, _http

    if _current_file_index >= len(_files_to_download):
        return False  # All files downloaded

    file_url, save_path = _files_to_download[_current_file_index]
    storage = view_manager.storage

    # Create necessary directories
    dir_path = "/".join(save_path.split("/")[:-1])
    storage.mkdir(dir_path)

    print(f"Downloading {file_url} to {save_path}")

    return _http.get_async(
        file_url,
        save_to_file=save_path,
        storage=storage,
        headers={
            "User-Agent": "Raspberry Pi Pico W",
            "Content-Type": "application/json",
        },
    )


def __loading_start(view_manager, text: str = "Fetching...") -> None:
    """Start loading animation"""
    from picoware.gui.loading import Loading

    global _loading

    if not _loading:
        _loading = Loading(view_manager.draw)
    _loading.set_text(text)


def __reset() -> None:
    """Reset the app state"""
    global _app_state, _github_author, _github_repo, _http, _loading, _current_file_index, _files_to_download, _github_alert
    _app_state = STATE_KEYBOARD_AUTHOR
    _github_author = ""
    _github_repo = ""
    _current_file_index = 0
    _files_to_download = []
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

    __reset()
    keyboard = view_manager.keyboard
    keyboard.reset()
    keyboard.title = "Enter GitHub Author"
    keyboard.run(force=True)
    keyboard.run(force=True)
    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

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
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()
            return
        if not __parse_repo_info(view_manager):
            return
        # Start downloading first file
        _current_file_index = 0
        if __download_next_file(view_manager):
            _app_state = STATE_DOWNLOADING_REPO
            __loading_start(
                view_manager, f"Downloading file 1/{len(_files_to_download)}..."
            )
        else:
            print("No files to download")
    elif _app_state == STATE_DOWNLOADING_REPO:
        # Download files one-by-one
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()
            return

        # Move to next file
        _current_file_index += 1

        if _current_file_index < len(_files_to_download):
            if __download_next_file(view_manager):
                __loading_start(
                    view_manager,
                    f"Downloading file {_current_file_index + 1}/{len(_files_to_download)}...",
                )
        else:
            # All files downloaded
            view_manager.alert("Repository downloaded successfully!", True)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    __reset()
    view_manager.keyboard.reset()
    collect()
