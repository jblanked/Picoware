"""PicoGTA - Downloadable game with asset management."""

from micropython import const
from picoware.system.decorator import (
    storage_required,
    wifi_required,
    server_settings_required,
)
import pico_gta


class PicoGTA(pico_gta.PicoGTA):
    """Class for the PicoGTA game"""

    __slots__ = ("is_active",)


STATE_DOWNLOADING = const(0)
STATE_PLAYING = const(1)

_TOTAL_ASSETS = const(1)

_pico_gta = None
_http = None
_loading = None
_asset_index = 0
_state = STATE_DOWNLOADING
_username = None
_password = None


def __get_asset_info() -> dict:
    """Get the asset name, download link, and save path.

    Returns:
        dict: Asset info with name, url, and path keys.
    """
    global _asset_index

    base_url = "https://raw.githubusercontent.com/jblanked/PicoGTA/dev/src/assets/"
    base_path = "picoware/apps/games/pico_gta/assets/"

    asset_list = __get_asset_list()

    current = asset_list[_asset_index]

    _data = {
        "name": current,
        "url": base_url + current,
        "path": base_path + current,
    }

    _asset_index += 1

    return _data


def __get_asset_list() -> list:
    """Get the list of assets to download.

    Returns:
        list: Asset filenames to download.
    """
    return ["woman.sprite3d"]


def __init_pico_gta() -> bool:
    """Initialize the PicoGTA game.

    Returns:
        bool: True on success.
    """
    global _pico_gta

    # requires username, password
    _pico_gta = PicoGTA(_username, _password)

    return _pico_gta is not None


def __is_assets_loaded(view_manager) -> bool:
    """Check if at least the first asset is loaded.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True if all assets exist.
    """
    s = view_manager.storage
    if s is None:
        return False
    asset_list = __get_asset_list()
    root_path = "picoware/apps/games/pico_gta/assets/"
    for asset in asset_list:
        if not s.exists(root_path + asset):
            return False
    return True


@storage_required
@wifi_required
@server_settings_required
def start(view_manager) -> bool:
    """Start the app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    global _state, _asset_index, _http, _username, _password, _loading

    from picoware.system.settings import Settings

    _settings = Settings(view_manager.storage)
    server_settings = _settings.server_settings
    _username = server_settings.get("username")
    _password = server_settings.get("password")

    if __is_assets_loaded(view_manager):
        _state = STATE_PLAYING
        # view_manager.freq(True, 210000000)  # set to 210MHz
        return __init_pico_gta()

    if view_manager.alert(
        "PicoGTA requires downloading assets on first run. This may take up to 15 minutes... Continue?",
    ):
        _state = STATE_DOWNLOADING
        _asset_index = 0

        from picoware.system.http import HTTP
        from picoware.gui.loading import Loading

        _http = HTTP(view_manager=view_manager)

        storage = view_manager.storage
        storage.mkdir("picoware/apps/games/pico_gta")
        storage.mkdir("picoware/apps/games/pico_gta/assets")

        asset_info = __get_asset_info()

        while storage.exists(asset_info["path"]):
            if _asset_index >= _TOTAL_ASSETS:
                break
            asset_info = __get_asset_info()

        _loading = Loading(
            view_manager.draw,
            view_manager.foreground_color,
            view_manager.background_color,
        )
        _loading.set_text(f"Downloading {_asset_index}/{_TOTAL_ASSETS}...")

        return _http.get_async(
            asset_info["url"],
            save_to_file=asset_info["path"],
            storage=storage,
            headers={"User-Agent": "Raspberry Pi Pico W"},
        )

    return False  # exit app.. assets are required!


def run(view_manager) -> None:
    """Run the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """

    global _state, _pico_gta, _loading

    # button = view_manager.button

    if _state == STATE_PLAYING:
        if _pico_gta is None:
            return

        while _pico_gta.is_active:
            _pico_gta.run()
            view_manager.thread_manager.run()
        view_manager.back()
        return

    if _state == STATE_DOWNLOADING:
        if not _http.is_request_complete():
            if _loading:
                _loading.animate(http=_http)
            return

        # Current asset download complete — start the next one
        if _asset_index < _TOTAL_ASSETS:
            asset_info = __get_asset_info()
            while view_manager.storage.exists(asset_info["path"]):
                if _asset_index >= _TOTAL_ASSETS:
                    break
                asset_info = __get_asset_info()
            from picoware.gui.loading import Loading

            if not _loading:
                _loading = Loading(
                    view_manager.draw,
                    view_manager.foreground_color,
                    view_manager.background_color,
                )
            else:
                _loading.stop()
            _loading.set_text(f"Downloading {_asset_index}/{_TOTAL_ASSETS}...")
            _http.get_async(
                asset_info["url"],
                save_to_file=asset_info["path"],
                storage=view_manager.storage,
                headers={"User-Agent": "Raspberry Pi Pico W"},
            )
        else:
            # All assets downloaded — initialise game
            if _loading:
                _loading.stop()
                _loading = None
            _state = STATE_PLAYING
            view_manager.freq(True, 210000000)  # set to 210MHz
            if not __init_pico_gta():
                view_manager.alert("Failed to initialize PicoGTA", False)
                view_manager.back()


def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from gc import collect

    global _pico_gta, _http, _loading, _asset_index, _state, _username, _password

    if _pico_gta is not None:
        del _pico_gta
        _pico_gta = None

    if _http is not None:
        del _http
        _http = None

    if _loading is not None:
        _loading.stop()
        del _loading
        _loading = None

    _asset_index = 0
    _state = STATE_DOWNLOADING
    _username = None
    _password = None

    view_manager.freq()  # set back to higher frequency

    collect()
