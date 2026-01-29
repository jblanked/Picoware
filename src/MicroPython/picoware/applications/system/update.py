from micropython import const

STATE_CHECKING = const(0)
STATE_UPDATE_AVAILABLE = const(1)
STATE_NO_UPDATE = const(2)
STATE_DOWNLOADING = const(3)
STATE_COMPLETE = const(4)

_http = None
_loading = None
_app_state: int = STATE_CHECKING
_update_info: dict = {}
_current_version: str = None
_board_id: int = None
_download_started: bool = False
_download_complete: bool = False
_download_error: str = None
_download_filename: str = None


def __reset() -> None:
    """Reset the update state"""
    global _http, _loading, _app_state, _update_info, _current_version, _board_id, _download_started, _download_complete, _download_error, _download_filename
    if _http:
        _http.close()
        del _http
        _http = None
    if _loading:
        del _loading
        _loading = None
    _app_state = STATE_CHECKING
    _update_info = None
    _current_version = None
    _board_id = None
    _download_started = False
    _download_complete = False
    _download_error = None
    _download_filename = None


def __loading_start(view_manager, text: str = "Checking...") -> None:
    """Start loading animation"""
    from picoware.gui.loading import Loading

    global _loading

    if not _loading:
        _loading = Loading(view_manager.draw)
    else:
        _loading.stop()
    _loading.set_text(text)


def __draw_update_available(view_manager) -> None:
    """Draw the update available screen"""
    from picoware.system.vector import Vector

    draw = view_manager.draw
    fg = view_manager.foreground_color

    draw.fill_screen(view_manager.background_color)

    if not _update_info:
        return

    text_vec = Vector(10, 10)

    # Title
    draw.text(text_vec, "Firmware Update Available!", fg)

    text_vec.y = 40

    # Current version
    current = _update_info.get("current_version", _current_version)
    draw.text(text_vec, f"Current Version: {current}", fg)
    text_vec.y += 20

    # Latest version
    latest = _update_info.get("latest_version", "Unknown")
    draw.text(text_vec, f"Latest Version:  {latest}", fg)
    text_vec.y += 30

    # Last updated
    last_updated = _update_info.get("last_updated", "")
    if last_updated:
        # Format: 2024-06-01T12:00:00Z -> 2024-06-01
        date_only = last_updated.split("T")[0] if "T" in last_updated else last_updated
        draw.text(text_vec, f"Released: {date_only}", fg)
        text_vec.y += 30

    # Download info
    text_vec.y += 10
    draw.text(text_vec, "The firmware will be saved to", fg)
    text_vec.y += 15
    draw.text(text_vec, "your SD card as a .uf2 file.", fg)

    # Instructions at bottom
    text_vec.y = 270
    draw.text(text_vec, "CENTER = Download Update", fg)
    text_vec.y += 15
    draw.text(text_vec, "BACK = Cancel", fg)

    draw.swap()


def __draw_no_update(view_manager) -> None:
    """Draw the no update available screen"""
    from picoware.system.vector import Vector

    draw = view_manager.draw
    fg = view_manager.foreground_color

    draw.fill_screen(view_manager.background_color)

    text_vec = Vector(10, 10)

    # Title
    draw.text(text_vec, "Firmware Up to Date!", fg)

    text_vec.y = 50

    # Current version
    draw.text(text_vec, f"Current Version: {_current_version}", fg)
    text_vec.y += 30

    draw.text(text_vec, "You are running the latest", fg)
    text_vec.y += 15
    draw.text(text_vec, "version of Picoware.", fg)

    # Instructions at bottom
    text_vec.y = 285
    draw.text(text_vec, "BACK = Return", fg)

    draw.swap()


def __draw_download_complete(view_manager, filename: str) -> None:
    """Draw the download complete screen"""
    from picoware.system.vector import Vector

    draw = view_manager.draw
    fg = view_manager.foreground_color

    draw.fill_screen(view_manager.background_color)

    text_vec = Vector(10, 10)

    # Title
    draw.text(text_vec, "Download Complete!", fg)

    text_vec.y = 50

    draw.text(text_vec, "Firmware saved to SD card:", fg)
    text_vec.y += 20
    draw.text(text_vec, f"  {filename}", fg)

    # Instructions at bottom
    text_vec.y = 285
    draw.text(text_vec, "BACK = Return", fg)

    draw.swap()


def __draw_error(view_manager, message: str) -> None:
    """Draw an error screen"""
    view_manager.alert(f"Update Error:\n{message}", True)


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.http import HTTP
    from picoware.system.system import System

    global _http, _app_state, _current_version, _board_id

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

    __reset()

    system = System()
    _current_version = system.version
    _board_id = system.board_id

    url = (
        "https://www.jblanked.com/picoware/api/firmware/check/micropython/"
        + str(_current_version)
        + "/"
        + str(_board_id)
        + "/"
    )

    _http = HTTP(thread_manager=view_manager.thread_manager)
    if not _http.get_async(
        url,
        headers={
            "User-Agent": "Raspberry Pi Pico W",
            "Content-Type": "application/json",
        },
    ):
        view_manager.alert("Failed to check for updates", False)
        return False

    _app_state = STATE_CHECKING
    __loading_start(view_manager, "Checking for updates...")
    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER

    global _app_state, _update_info, _loading

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    if _app_state == STATE_CHECKING:
        # Show loading animation while checking for updates
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()

            return

        if _loading:
            _loading.stop()
            del _loading
            _loading = None

        # Parse the response
        response = _http.response
        if response and response.status_code == 200:
            try:
                from json import loads

                _update_info = loads(response.text)

                if _update_info.get("success"):
                    if _update_info.get("is_update_available"):
                        _app_state = STATE_UPDATE_AVAILABLE
                        __draw_update_available(view_manager)
                    else:
                        _app_state = STATE_NO_UPDATE
                        __draw_no_update(view_manager)
                else:
                    __draw_error(view_manager, "Server returned an error")
            except Exception as e:
                __draw_error(view_manager, f"Failed to parse response: {e}")
        else:
            __draw_error(view_manager, "Failed to check for updates")

        if _http:
            _http.close()

    elif _app_state == STATE_UPDATE_AVAILABLE:
        if button == BUTTON_CENTER:
            inp.reset()
            # Start downloading the firmware
            if _update_info and _update_info.get("download_url"):
                download_url = _update_info["download_url"]
                filename = download_url.split("/")[-1]

                storage = view_manager.storage

                # save to uf2loader folder
                # this allow users to download Picoware
                # then use uf2loader to flash it easily
                file_path = ""
                if "Pico2" in download_url:
                    storage.mkdir("pico2-apps")
                    file_path = f"pico2-apps/{filename}"
                else:
                    storage.mkdir("pico1-apps")
                    file_path = f"pico1-apps/{filename}"

                if _http:
                    _http.close()

                    if _http.get_async(
                        download_url,
                        headers={
                            "User-Agent": "Raspberry Pi Pico W",
                            "Content-Type": "application/octet-stream",
                        },
                        storage=storage,
                        save_to_file=file_path,
                    ):
                        _app_state = STATE_DOWNLOADING
                        __loading_start(view_manager, "Downloading firmware...")
                    else:
                        __draw_error(view_manager, "Failed to start download")
            else:
                __draw_error(view_manager, "No download URL available")

    elif _app_state == STATE_DOWNLOADING:
        # Check if download is complete
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()
            return

        if _loading:
            _loading.stop()
            del _loading
            _loading = None

        # Check the download result
        response = _http.response
        if response and response.status_code == 200:
            # Download successful
            download_url = _update_info.get("download_url", "")
            filename = download_url.split("/")[-1]
            _app_state = STATE_COMPLETE
            __draw_download_complete(view_manager, filename)
        else:
            # Download failed
            error_msg = "Download failed"
            if _http and _http.error:
                error_msg = f"Download failed: HTTP {_http.error}"
            __draw_error(view_manager, error_msg)

        if _http:
            _http.close()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    __reset()

    collect()
