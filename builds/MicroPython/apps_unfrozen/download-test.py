# picoware/apps/download-test.py
from picoware.system.buttons import (
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_BACK,
    BUTTON_CENTER,
)

_http = None
_menu = None
_loading = None
_request_started = False
_download_complete = False
_download_error = None


def __http_callback(response, state, error) -> None:
    """HTTP callback function - runs in background thread, only sets flags."""
    global _request_started, _download_complete, _download_error

    if any([response is None, error, state == 2]):  # HTTP_ERROR
        _download_error = error if error is not None else "Unknown error"
    else:
        _download_error = None

    _download_complete = True
    _request_started = False


def start(view_manager) -> bool:
    """Start the app."""
    from picoware.gui.menu import Menu
    from picoware.gui.loading import Loading
    from picoware.system.colors import TFT_BLUE

    draw = view_manager.draw
    wifi = view_manager.wifi
    if not wifi:
        view_manager.alert("WiFi not available...")
        return False
    if not wifi.is_connected():
        view_manager.alert("WiFi not connected yet...")
        return False

    global _menu, _loading, _request_started

    _request_started = False

    if not _menu:
        # set menu
        _menu = Menu(
            draw,  # draw instance
            "Click an option to download",  # title
            0,  # y position
            draw.size.y,  # height
            view_manager.foreground_color,  # text color
            view_manager.background_color,  # background color
            TFT_BLUE,  # selected item color
            view_manager.foreground_color,  # border color
        )

        # add items
        _menu.add_item("1 KB from httpbin.org")
        _menu.add_item("1 MB from proof.ovh.net")
        _menu.add_item("10 MB from proof.ovh.net")
        _menu.set_selected(0)

    if not _loading:
        _loading = Loading(
            draw,
            view_manager.foreground_color,
            view_manager.background_color,
        )
        _loading.set_text("Downloading...")

    return True


def run(view_manager) -> None:
    """Run the app."""

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    global _http, _menu, _loading, _request_started, _download_complete, _download_error

    # Check if download completed (callback has finished)
    if _download_complete:
        _download_complete = False
        if _download_error:
            view_manager.alert(f"Download error: {_download_error}", True)
        else:
            view_manager.alert("Download complete!", True)
        return

    if _http and _request_started:
        if _loading:
            _loading.animate()
        return

    if button == BUTTON_UP:
        inp.reset()
        _menu.scroll_up()
    elif button == BUTTON_DOWN:
        inp.reset()
        _menu.scroll_down()
    elif button == BUTTON_CENTER and not _request_started:
        inp.reset()
        selection = _menu.selected_index
        if selection == 0:
            url = "https://httpbin.org/bytes/1024"
            file_name = "httpbin_1kb.bin"
        elif selection == 1:
            url = "https://proof.ovh.net/files/1Mb.dat"
            file_name = "ovh_1mb.bin"
        elif selection == 2:
            url = "https://proof.ovh.net/files/10Mb.dat"
            file_name = "ovh_10mb.bin"
        else:
            url = None
            file_name = None

        if url and file_name:

            storage = view_manager.storage
            try:
                # remove file if it exists
                storage.remove(file_name)
            except Exception:
                pass
            if _http is not None:
                _http.close()
                del _http
                _http = None
            from picoware.system.http import HTTP

            _http = HTTP()
            _http.callback = __http_callback
            _request_started = True
            if not _http.get_async(
                url=url,
                save_to_file=file_name,
                storage=storage,
                headers={
                    "User-Agent": "Raspberry Pi Pico W",
                    "Content-Type": "application/octet-stream",
                },
            ):
                view_manager.alert("Failed to start download request...", False)
                _request_started = False
                _menu.refresh()


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _http, _menu, _loading, _request_started, _download_complete, _download_error

    if _http:
        _http.close()
        del _http
        _http = None

    if _menu:
        del _menu
        _menu = None

    if _loading:
        _loading.stop()
        del _loading
        _loading = None

    _request_started = False
    _download_complete = False
    _download_error = None

    collect()
