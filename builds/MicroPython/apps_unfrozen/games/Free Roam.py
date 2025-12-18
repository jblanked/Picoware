# picoware/apps/games/Free Roam.py
_free_roam_alert = None
_game = None


def __free_roam_alert(view_manager, message: str, back: bool = True) -> None:
    """Show an alert"""
    from time import sleep

    global _free_roam_alert

    if _free_roam_alert:
        del _free_roam_alert
        _free_roam_alert = None

    from picoware.gui.alert import Alert

    draw = view_manager.draw
    draw.clear()
    _free_roam_alert = Alert(
        draw,
        message,
        view_manager.foreground_color,
        view_manager.background_color,
    )
    _free_roam_alert.draw("Alert")
    sleep(2)
    if back:
        view_manager.back()


def start(view_manager) -> bool:
    """Start the app"""

    wifi = view_manager.wifi

    # if not a wifi device, return
    if not wifi:
        __free_roam_alert(view_manager, "WiFi not available...", False)
        return False

    # if wifi isn't connected, return
    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        __free_roam_alert(view_manager, "WiFi not connected", False)
        connect_to_saved_wifi(view_manager)
        return False

    global _game
    from free_roam.game import FreeRoamGame

    _game = FreeRoamGame(view_manager)

    return _game is not None


def run(view_manager) -> None:
    """Run the app"""

    inp = view_manager.input_manager
    button = inp.button

    global _game

    if not _game or not _game.is_active:
        inp.reset()
        view_manager.back()
        return

    _game.update_input(button)
    _game.update_draw()

    if button != -1:
        inp.reset()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _free_roam_alert, _game

    if _free_roam_alert:
        del _free_roam_alert
        _free_roam_alert = None
    if _game:
        del _game
        _game = None

    collect()
