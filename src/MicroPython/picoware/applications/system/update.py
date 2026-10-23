"""Update - Check for and install updates."""

from micropython import const

STATE_CHECKING = const(0)
STATE_UPDATE_AVAILABLE = const(1)
STATE_NO_UPDATE = const(2)
STATE_DOWNLOADING = const(3)
STATE_COMPLETE = const(4)
STATE_CHECK_FAILED = const(5)

_http = None
_loading = None
_app_state: int = STATE_CHECKING
_update_info: dict = {}
_current_version: str = None
_download_file_path: str = None
_view_manager = None
_check_error = None
_check_attempts = 0


def __reset() -> None:
    """Reset the update state"""
    global _http, _loading, _app_state, _update_info, _current_version
    global _download_file_path, _view_manager, _check_error, _check_attempts
    if _http is not None:
        _http.close()
    _http = None
    _loading = None
    _app_state = STATE_CHECKING
    _update_info = None
    _current_version = None
    _download_file_path = None
    _view_manager = None
    _check_error = None
    _check_attempts = 0


def __check_for_update_start(http_context, view_manager, retry=False) -> bool:
    """Start the check for update request.

    Args:
        http_context (HTTP): The HTTP context for the request.
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        bool: True if the request started, False otherwise.
    """
    from picoware.system.system import System
    from picoware_boards import BOARD_HAS_ESP32

    system = System()

    url = (
        "https://www.jblanked.com/picoware/api/firmware/check/micropython/"
        + str(system.version)
        + "/"
        + str(system.board_id)
        + "/"
    )

    # Parse once on the UI thread after completion. A worker callback can race
    # with close(), and malformed JSON must not escape into the desktop loop.
    http_context.callback = None
    global _update_info, _check_error, _check_attempts
    _update_info = None
    _check_error = None
    _check_attempts = _check_attempts + 1 if retry else 1

    del system

    global _view_manager
    _view_manager = view_manager
    return http_context.get_async(
        url,
        headers={
            "User-Agent": "Raspberry Pi Pico W" if BOARD_HAS_ESP32 == 0 else "ESP32HTTPClient",
            "Content-Type": "application/json",
        },
    )


def __update_filename(url):
    """Validate a firmware URL and return its safe local basename."""
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        return None
    if any(char.isspace() for char in url):
        return None
    parts = url.split("/", 3)
    if len(parts) != 4 or not parts[2]:
        return None
    path = parts[3].split("?", 1)[0].split("#", 1)[0]
    filename = path.rsplit("/", 1)[-1]
    if filename in ("", ".", "..") or "\\" in filename:
        return None
    return filename


def __check_for_update_is_available(http_context):
    """Return True/False for success, None for failure, or -1 while retrying."""
    global _update_info, _check_error
    _update_info = None
    _check_error = None
    if not http_context.is_request_complete():
        return None
    response = http_context.response
    # A single fresh connection recovers transient DNS/socket/TLS failures.
    # Never retry HTTP responses (including an unregistered board's 404).
    if response is None and _check_attempts == 1:
        _view_manager.log("Retrying update check after: " + (http_context.error or "No response"))
        if __check_for_update_start(http_context, _view_manager, retry=True):
            return -1
    data = None
    if response is not None:
        try:
            data = response.json()
        except (ValueError, TypeError, OSError):
            pass
    if (response is not None and response.status_code == 404
            and isinstance(data, dict)
            and isinstance(data.get("error"), str)
            and data["error"].startswith("No device found for board_id ")):
        _check_error = "Updates unavailable for this board"
    elif response is None:
        _check_error = "Update check failed: " + (http_context.error or "No response")
    elif response.status_code != 200:
        _check_error = "Update check failed: HTTP " + str(response.status_code)
    elif (not isinstance(data, dict) or data.get("success") is not True
            or not isinstance(data.get("is_update_available"), bool)):
        _check_error = "Update check failed: invalid response"
    elif data["is_update_available"] and __update_filename(data.get("download_url")) is None:
        _check_error = "Update check failed: invalid download URL"
    else:
        _update_info = data
        return data["is_update_available"]
    _view_manager.log(_check_error)
    return None


def __check_for_update_download_start(http_context, storage) -> bool:
    """Start the download of the update.

    Args:
        http_context (HTTP): The HTTP context for the request.
        storage (Storage): The storage to save the firmware to.

    Returns:
        bool: True if the download started, False otherwise.
    """
    from picoware_boards import BOARD_HAS_ESP32
    global _view_manager, _update_info, _download_file_path
    if http_context is None:
        _view_manager.log("Error downloading update: http context is None")
        return False
    if _update_info and _update_info.get("download_url"):
        download_url = _update_info["download_url"]
        filename = __update_filename(download_url)
        if filename is None:
            _view_manager.log("Update download failed: invalid download URL")
            return False

        file_path = ""
        if BOARD_HAS_ESP32 == 0:
            # save to uf2loader folder
            # this allow users to download Picoware
            # then use uf2loader to flash it easily
            if "Pico2" in download_url:
                storage.mkdir("pico2-apps")
                file_path = f"pico2-apps/{filename}"
            else:
                storage.mkdir("pico1-apps")
                file_path = f"pico1-apps/{filename}"
        else:
            file_path = filename # save on root

        _download_file_path = file_path

        http_context.close()
        # Completion is handled by the UI; no worker retains update state.
        http_context.callback = None

        return http_context.get_async(
            download_url,
            headers={
                "User-Agent": "Raspberry Pi Pico W" if BOARD_HAS_ESP32 == 0 else "ESP32HTTPClient",
                "Content-Type": "application/octet-stream",
            },
            storage=storage,
            save_to_file=file_path,
        )
    return False


def __loading_start(view_manager, text: str = "Checking...") -> None:
    """Start the loading animation.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
        text (str): The loading text. Defaults to "Checking...".
    """
    from picoware.gui.loading import Loading

    global _loading

    if not _loading:
        _loading = Loading(view_manager.draw)
    else:
        _loading.stop()
    _loading.set_text(text)


def __draw_update_available(view_manager) -> None:
    """Draw the update available screen.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    if not _update_info:
        return
    
    draw = view_manager.draw
    fg = view_manager.foreground_color

    draw.erase()

    text_vec_x, text_vec_y = draw.scale(10, 10)

    # Title
    draw._text(text_vec_x, text_vec_y, "Firmware Update Available!", fg)

    text_vec_y = draw.scale_y(40)

    # Current version
    current = _update_info.get("current_version", _current_version)
    draw._text(text_vec_x, text_vec_y, f"Current Version: {current}", fg)
    text_vec_y += draw.scale_y(20)

    # Latest version
    latest = _update_info.get("latest_version", "Unknown")
    draw._text(text_vec_x, text_vec_y, f"Latest Version:  {latest}", fg)
    text_vec_y += draw.scale_y(30)

    # Last updated
    last_updated = _update_info.get("last_updated", "")
    if last_updated:
        # Format: 2024-06-01T12:00:00Z -> 2024-06-01
        date_only = last_updated.split("T")[0] if "T" in last_updated else last_updated
        draw._text(text_vec_x, text_vec_y, f"Released: {date_only}", fg)
        text_vec_y += draw.scale_y(30)

    # Download info
    text_vec_y += draw.scale_y(10)
    draw._text(text_vec_x, text_vec_y, "The firmware will be saved to", fg)
    text_vec_y += draw.scale_y(15)
    draw._text(text_vec_x, text_vec_y, f"your SD card at {_download_file_path}", fg)

    # Instructions at bottom
    text_vec_y = draw.scale_y(270)
    draw._text(text_vec_x, text_vec_y, "CENTER = Download and install update", fg)
    text_vec_y += draw.scale_y(15)
    draw._text(text_vec_x, text_vec_y, "BACK = Cancel", fg)

    draw.swap()


def __draw_no_update(view_manager) -> None:
    """Draw the no update available screen.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    draw = view_manager.draw
    fg = view_manager.foreground_color

    draw.fill_screen(view_manager.background_color)

    text_vec_x, text_vec_y = draw.scale(10, 10)

    # Title
    draw._text(text_vec_x, text_vec_y, "Firmware Up to Date!", fg)

    text_vec_y = draw.scale_y(50)

    # Current version
    draw._text(text_vec_x, text_vec_y, f"Current Version: {_current_version}", fg)
    text_vec_y += draw.scale_y(30)

    draw._text(text_vec_x, text_vec_y, "You are running the latest", fg)
    text_vec_y += draw.scale_y(15)
    draw._text(text_vec_x, text_vec_y, "version of Picoware.", fg)

    # Instructions at bottom
    text_vec_y = draw.scale_y(285)
    draw._text(text_vec_x, text_vec_y, "BACK = Return", fg)

    draw.swap()


def __draw_download_complete(view_manager) -> None:
    """Draw the download complete screen.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """

    draw = view_manager.draw
    fg = view_manager.foreground_color

    draw.fill_screen(view_manager.background_color)

    text_vec_x, text_vec_y = draw.scale(10, 10)

    # Title
    draw._text(text_vec_x, text_vec_y, "Download Complete!", fg)

    draw._text(text_vec_x, text_vec_y + draw.scale_y(40), "Firmware saved to SD card:", fg)
    draw._text(text_vec_x, text_vec_y + draw.scale_y(60), f"  {_download_file_path}", fg)

    # Instructions at bottom
    draw._text(text_vec_x, draw.scale_y(285), "CENTER = Install, BACK = Return", fg)

    draw.swap()

    inp = view_manager.input_manager
    inp.reset()
    while True:
        but = inp.button
        if but != -1:
            inp.reset()
            if but == 5:  # back
                view_manager.back(True)
                return
            break

    from picoware.system.uf2loader import UF2Loader

    uf2 = UF2Loader()
    uf2.flash(_download_file_path)


def __draw_error(view_manager, message: str) -> None:
    """Draw an error screen.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
        message (str): The error message to show.
    """
    view_manager.alert(f"Update Error:\n{message}", True)


def start(view_manager) -> bool:
    """Start the app and check for updates.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        bool: True if the update check started, False on failure.
    """
    global _http, _app_state, _current_version

    # Check for SD card (needed to save firmware)
    if not view_manager.has_sd_card:
        view_manager.alert("Update requires an SD card", False)
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
    
    from picoware.system.http import HTTP
    from picoware.system.system import System

    __reset()

    system = System()
    _current_version = system.version
    _http = HTTP(view_manager=view_manager)

    if not __check_for_update_start(_http, view_manager):
        view_manager.alert("Failed to check for updates", False)
        return False

    _app_state = STATE_CHECKING
    __loading_start(view_manager, "Checking for updates...")
    return True


def run(view_manager) -> None:
    """Run the app and handle the update state machine.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER

    global _app_state, _update_info, _loading

    button = view_manager.button

    if button == BUTTON_BACK:
        view_manager.back()
        return

    if _app_state == STATE_CHECKING:
        # Show loading animation while checking for updates
        if not _http.is_request_complete():
            if _loading:
                _loading.animate(http=_http)
            return

        available = __check_for_update_is_available(_http)
        if available == -1:
            return  # A bounded transport retry is now in progress.

        if _loading:
            _loading.stop()
            del _loading
            _loading = None

        # Parse the response
        if available is True:
            _app_state = STATE_UPDATE_AVAILABLE
            __draw_update_available(view_manager)
        elif available is False:
            _app_state = STATE_NO_UPDATE
            __draw_no_update(view_manager)
        else:
            _app_state = STATE_CHECK_FAILED
            __draw_error(view_manager, _check_error or "Update check failed")

        if _http:
            _http.close()

    elif _app_state == STATE_UPDATE_AVAILABLE:
        if button == BUTTON_CENTER:

            # Start downloading the firmware
            if __check_for_update_download_start(_http, view_manager.storage):
                _app_state = STATE_DOWNLOADING
                __loading_start(view_manager, "Downloading firmware...")
            else:
                __draw_error(view_manager, "Failed to start download")

    elif _app_state == STATE_DOWNLOADING:
        # Check if download is complete
        if not _http.is_request_complete():
            if _loading:
                _loading.animate(http=_http)
            return

        if _loading:
            _loading.stop()
            del _loading
            _loading = None

        # Check the download result
        response = _http.response
        if response and response.status_code == 200:
            # Download successful
            _app_state = STATE_COMPLETE
            __draw_download_complete(view_manager)
        else:
            # Download failed
            error_msg = "Download failed"
            if _http and _http.error:
                error_msg = f"Download failed: HTTP {_http.error}"
            __draw_error(view_manager, error_msg)

        if _http:
            _http.close()


def stop(view_manager) -> None:
    """Stop the app and reset the update state.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from gc import collect

    __reset()

    collect()
