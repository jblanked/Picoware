# original from https://github.com/jblanked/FlipSocial
# modified for micropython picoware by @jblanked


_flip_social_alert = None
_flip_social_app_menu = None
_flip_social_app_index: int = 0  # index for the FlipSocial app menu

_flip_social_run_instance = None


def __flip_social_util_get_username(view_manager) -> str:
    """Get the username from storage, or return empty string"""
    storage = view_manager.storage
    data: str = storage.read("picoware/flip_social/username.json")

    if data is not None:
        try:
            from ujson import loads

            obj: dict = loads(data)
            if "username" in obj:
                return obj["username"]
        except Exception:
            pass

    return ""


def __flip_social_util_get_password(view_manager) -> str:
    """Get the password from storage, or return empty string"""
    storage = view_manager.storage
    data: str = storage.read("picoware/flip_social/password.json")

    if data is not None:
        try:
            from ujson import loads

            obj: dict = loads(data)
            if "password" in obj:
                return obj["password"]
        except Exception:
            pass

    return ""


def __flip_social_alert(view_manager, message: str, back: bool = True) -> None:
    """Show an alert"""
    from time import sleep

    global _flip_social_alert

    if _flip_social_alert:
        del _flip_social_alert
        _flip_social_alert = None

    from picoware.gui.alert import Alert

    _flip_social_alert = Alert(
        view_manager.draw,
        message,
        view_manager.foreground_color,
        view_manager.background_color,
    )
    _flip_social_alert.draw("Alert")
    sleep(2)
    if back:
        view_manager.back()


def start(view_manager) -> bool:
    """Start the main app"""
    from picoware.gui.menu import Menu

    wifi = view_manager.wifi

    # if not a wifi device, return
    if not wifi:
        __flip_social_alert(view_manager, "WiFi not available...", False)
        return False

    # if wifi isn't connected, return
    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        __flip_social_alert(view_manager, "WiFi not connected", False)
        connect_to_saved_wifi(view_manager)
        return False

    global _flip_social_app_menu

    if _flip_social_app_menu:
        del _flip_social_app_menu
        _flip_social_app_menu = None

    view_manager.storage.mkdir("picoware/flip_social")

    draw = view_manager.draw

    _flip_social_app_menu = Menu(
        draw,  # draw instance
        "FlipSocial",  # title
        0,  # y
        draw.size.y,  # height
        view_manager.foreground_color,  # text color
        view_manager.background_color,  # background color
        view_manager.selected_color,  # selected color
        view_manager.foreground_color,  # border/separator color
        2,  # border/separator width
    )

    _flip_social_app_menu.add_item("Run")
    _flip_social_app_menu.add_item("Settings")

    _flip_social_app_menu.set_selected(_flip_social_app_index)
    _flip_social_app_menu.draw()

    return True


def run(view_manager) -> None:
    """Run the main app"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )

    global _flip_social_app_index, _flip_social_run_instance

    input_manager = view_manager.input_manager
    input_button = input_manager.button

    if input_button == BUTTON_UP:
        input_manager.reset()
        _flip_social_app_menu.scroll_up()
    elif input_button == BUTTON_DOWN:
        input_manager.reset()
        _flip_social_app_menu.scroll_down()
    elif input_button == BUTTON_BACK:
        input_manager.reset()
        _flip_social_app_index = 0
        view_manager.back()
    elif input_button in (BUTTON_CENTER, BUTTON_RIGHT):
        from picoware.system.view import View

        input_manager.reset()
        _flip_social_app_index = _flip_social_app_menu.get_selected_index()
        current_item = _flip_social_app_menu.get_current_item()

        if current_item == "Run":
            if __flip_social_util_get_username(view_manager) == "":
                __flip_social_alert(
                    view_manager,
                    "Please set your username in \nFlipSocial settings first",
                )
                return
            if __flip_social_util_get_password(view_manager) == "":
                __flip_social_alert(
                    view_manager,
                    "Please set your password in \nFlipSocial settings first",
                )
                return

            if _flip_social_run_instance:
                del _flip_social_run_instance
                _flip_social_run_instance = None

            from flip_social.run import FlipSocialRun

            _flip_social_run_instance = FlipSocialRun(view_manager)

            view_manager.add(
                View(
                    "flip_social_run",
                    _flip_social_run_instance.run,
                    _flip_social_run_instance.start,
                    _flip_social_run_instance.stop,
                )
            )
            view_manager.switch_to("flip_social_run")
            return

        if current_item == "Settings":
            from flip_social.settings import (
                __flip_social_settings_run,
                __flip_social_settings_start,
                __flip_social_settings_stop,
            )

            view_manager.add(
                View(
                    "flip_social_settings",
                    __flip_social_settings_run,
                    __flip_social_settings_start,
                    __flip_social_settings_stop,
                )
            )
            view_manager.switch_to("flip_social_settings")
            return


def stop(view_manager) -> None:
    """Stop the main app"""
    from gc import collect

    global _flip_social_alert, _flip_social_app_menu, _flip_social_run_instance

    if _flip_social_alert:
        del _flip_social_alert
        _flip_social_alert = None
    if _flip_social_app_menu:
        del _flip_social_app_menu
        _flip_social_app_menu = None
    if _flip_social_run_instance:
        del _flip_social_run_instance
        _flip_social_run_instance = None

    collect()
