# picoware/apps/games/Free Roam.py
from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_RIGHT,
    BUTTON_CENTER,
)


_free_roam_app_menu = None
_free_roam_app_index: int = 0  # index for the Free Roam app menu

_free_roam_run_instance = None


def __free_roam_game_start(view_manager) -> bool:
    """Start the game view"""
    return _free_roam_run_instance is not None


def __free_roam_game_run(view_manager) -> None:
    """Run the game view"""
    global _free_roam_run_instance

    button = view_manager.button

    if not _free_roam_run_instance or not _free_roam_run_instance.is_active:
        view_manager.back()
        return

    _free_roam_run_instance.update_input(button)
    _free_roam_run_instance.update_draw()


def __free_roam_game_stop(view_manager) -> None:
    """Stop the game view"""
    from gc import collect

    global _free_roam_run_instance

    if _free_roam_run_instance:
        del _free_roam_run_instance
        _free_roam_run_instance = None

    collect()


def start(view_manager) -> bool:
    """Start the main app"""
    from picoware.gui.menu import Menu

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

    view_manager.freq(True)  # set to lower frequency

    global _free_roam_app_menu

    if _free_roam_app_menu:
        del _free_roam_app_menu
        _free_roam_app_menu = None

    draw = view_manager.draw

    _free_roam_app_menu = Menu(
        draw,  # draw instance
        "Free Roam",  # title
        0,  # y
        draw.size.y,  # height
        view_manager.foreground_color,  # text color
        view_manager.background_color,  # background color
        view_manager.selected_color,  # selected color
        view_manager.foreground_color,  # border/separator color
        2,  # border/separator width
    )

    _free_roam_app_menu.add_item("Run")
    _free_roam_app_menu.add_item("Settings")

    _free_roam_app_menu.set_selected(_free_roam_app_index)
    _free_roam_app_menu.draw()
    return True


def run(view_manager) -> None:
    """Run the main app"""
    global _free_roam_app_index, _free_roam_run_instance

    input_button = view_manager.button

    if input_button == BUTTON_UP:
        _free_roam_app_menu.scroll_up()
    elif input_button == BUTTON_DOWN:
        _free_roam_app_menu.scroll_down()
    elif input_button == BUTTON_BACK:
        _free_roam_app_index = 0
        view_manager.back()
    elif input_button in (BUTTON_CENTER, BUTTON_RIGHT):
        from picoware.system.view import View

        _free_roam_app_index = _free_roam_app_menu.selected_index
        current_item = _free_roam_app_menu.current_item

        if current_item == "Run":
            if _free_roam_run_instance:
                del _free_roam_run_instance
                _free_roam_run_instance = None

            from free_roam.game import FreeRoamGame

            _free_roam_run_instance = FreeRoamGame(view_manager)

            view_manager.add(
                View(
                    "free_roam_run",
                    __free_roam_game_run,
                    __free_roam_game_start,
                    __free_roam_game_stop,
                )
            )
            view_manager.switch_to("free_roam_run")
            return

        if current_item == "Settings":
            from free_roam.settings import (
                __free_roam_settings_run,
                __free_roam_settings_start,
                __free_roam_settings_stop,
            )

            view_manager.add(
                View(
                    "free_roam_settings",
                    __free_roam_settings_run,
                    __free_roam_settings_start,
                    __free_roam_settings_stop,
                )
            )
            view_manager.switch_to("free_roam_settings")
            return


def stop(view_manager) -> None:
    """Stop the main app"""
    from gc import collect

    global _free_roam_app_menu

    if _free_roam_app_menu:
        del _free_roam_app_menu
        _free_roam_app_menu = None
    view_manager.freq()  # set to default frequency
    collect()
