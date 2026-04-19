import ghouls


class Ghouls(ghouls.Ghouls):
    pass


_ghouls = None


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

    # if settings arent saved, return
    from picoware.applications.system import settings

    username = settings.__load_server_username(view_manager)
    password = settings.__load_server_password(view_manager)

    if not username or not password:
        view_manager.alert(
            "Ghouls requires a username and password to connect to the server.\nAdd them in Library -> System -> Settings -> Server Settings",
            False,
        )
        return False

    global _ghouls

    _ghouls = Ghouls(
        username, password, False
    )  # requires username, password, soundEnabled

    return _ghouls is not None


def run(view_manager) -> None:
    """Run the app"""
    if _ghouls is None:
        return

    button = view_manager.button
    try:
        if not _ghouls.is_active:
            view_manager.back()
            return
        _ghouls.update_draw()
        if button != -1:
            _ghouls.update_input(button)
    except Exception:
        view_manager.back()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _ghouls

    del _ghouls
    _ghouls = None

    collect()
