from micropython import const
import ghouls


class Ghouls(ghouls.Ghouls):
    """Class for the Ghouls game"""

    __slots__ = ("is_active",)


STATE_DOWNLOADING = const(0)
STATE_PLAYING = const(1)

_TOTAL_ASSETS = const(16)

_ghouls = None
_http = None
_loading = None
_asset_index = 0
_state = STATE_DOWNLOADING
_username = None
_password = None


def __get_asset_info() -> dict:
    """Get the asset name, download link, and save path for the current asset index"""
    global _asset_index

    base_url = "https://raw.githubusercontent.com/jblanked/Ghouls/dev/src/assets/"
    base_path = "picoware/apps/games/ghouls/assets/"

    asset_list = [
        "ambience.wav",
        "crossbow.wav",
        "forest.ghoulsmap",
        "ghouls-growl-loud.wav",
        "ghouls-growl-medium.wav",
        "ghouls-growl-soft.wav",
        "ghouls-growling.wav",
        "graveyard.ghoulsmap",
        "home.ghoulsmap",
        "maze.ghoulsmap",
        "menu-click.wav",
        "rifle.wav",
        "rocket-launcher.wav",
        "shotgun.wav",
        "tron.ghoulsmap",
        "weapon-pickup.wav",
    ]

    current = asset_list[_asset_index]

    _data = {
        "name": current,
        "url": base_url + current,
        "path": base_path + current,
    }

    _asset_index += 1

    return _data


def __init_ghouls() -> bool:
    """'Initialize the Ghouls game"""
    global _ghouls

    # requires username, password, soundEnabled
    _ghouls = Ghouls(_username, _password, True)

    return _ghouls is not None


def __is_assets_loaded(view_manager) -> bool:
    """Check if at least the first asset is loaded"""
    s = view_manager.storage
    return s is not None and s.exists(
        "picoware/apps/games/ghouls/assets/home.ghoulsmap"
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

    global _state, _asset_index, _http, _username, _password, _loading

    # if settings arent saved, return
    from picoware.system.settings import Settings

    _settings = Settings(view_manager.storage)
    server_settings = _settings.server_settings
    _username = server_settings.get("username")
    _password = server_settings.get("password")

    if not _username or not _password:
        view_manager.alert(
            "Ghouls requires a username and password to connect to the server.\nAdd them in Library -> System -> Settings -> Server Settings",
            False,
        )
        return False

    if __is_assets_loaded(view_manager):
        _state = STATE_PLAYING
        view_manager.freq(True, 210000000)  # set to 210MHz
        return __init_ghouls()

    if view_manager.alert(
        "Ghouls requires downloading assets on first run. This may take up to 15 minutes... Continue?",
    ):
        _state = STATE_DOWNLOADING
        _asset_index = 0

        from picoware.system.http import HTTP
        from picoware.gui.loading import Loading

        _http = HTTP(thread_manager=view_manager.thread_manager)

        storage = view_manager.storage
        storage.mkdir("picoware/apps/games/ghouls")
        storage.mkdir("picoware/apps/games/ghouls/assets")

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
    """Run the app"""

    global _state, _ghouls, _loading

    button = view_manager.button

    if _state == STATE_PLAYING:
        if _ghouls is None:
            return

        if button != -1:
            _ghouls.update_input(button)

        if not _ghouls.is_active:
            view_manager.back()
            return

        _ghouls.update_draw()

    elif _state == STATE_DOWNLOADING:
        if not _http.is_request_complete():
            if _loading:
                _loading.animate()
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
            if not __init_ghouls():
                view_manager.alert("Failed to initialize Ghouls", False)
                view_manager.back()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _ghouls, _http, _loading, _asset_index, _state, _username, _password

    if _ghouls is not None:
        del _ghouls
        _ghouls = None

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
