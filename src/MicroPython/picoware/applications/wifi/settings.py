_settings_menu = None
_settings_menu_index = 0
_settings_textbox = None
_text_visible = False


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.menu import Menu

    global _settings_menu

    if _settings_menu is None:
        _settings_menu = Menu(
            view_manager.draw,
            "WiFi Settings",
            0,
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
            view_manager.selected_color,
            view_manager.foreground_color,
            2,
        )
        _settings_menu.add_item("Network Info")
        _settings_menu.add_item("Change SSID")
        _settings_menu.add_item("Change Password")
        _settings_menu.set_selected(0)
        _settings_menu.draw()

    return True


def run(view_manager) -> None:
    """Run the app."""
    from picoware.system.view import View
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_RIGHT,
    )

    global _settings_menu
    if not _settings_menu:
        return

    global _text_visible
    global _settings_textbox
    global _settings_menu_index

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        input_manager.reset()
        _settings_menu.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        input_manager.reset()
        _settings_menu.scroll_down()
    elif button == BUTTON_BACK:
        input_manager.reset()
        if not _text_visible:
            view_manager.back()
            return
        _text_visible = False
        if _settings_textbox is not None:
            _settings_textbox.clear()
            _settings_menu.draw()
    elif button == BUTTON_CENTER:
        input_manager.reset()
        _settings_menu_index = _settings_menu.get_selected_index()
        if _settings_menu_index == 0:
            from picoware.applications.wifi.utils import (
                load_wifi_password,
                load_wifi_ssid,
            )

            ssid = load_wifi_ssid(view_manager)
            password = load_wifi_password(view_manager)

            info = "Network Info\n\nSSID: {}\nPassword: {}".format(ssid, password)

            from picoware.gui.textbox import TextBox

            if _settings_textbox is None:
                _settings_textbox = TextBox(
                    view_manager.draw,
                    0,
                    320,
                    view_manager.foreground_color,
                    view_manager.background_color,
                )

            _settings_textbox.set_text(info)
            _text_visible = True

        elif _settings_menu_index == 1:
            from picoware.applications.wifi import ssid

            view_manager.add(
                View(
                    "wifi_ssid",
                    ssid.run,
                    ssid.start,
                    ssid.stop,
                )
            )
            view_manager.switch_to("wifi_ssid")
        elif _settings_menu_index == 2:
            from picoware.applications.wifi import password

            view_manager.add(
                View(
                    "wifi_password",
                    password.run,
                    password.start,
                    password.stop,
                )
            )
            view_manager.switch_to("wifi_password")


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _settings_menu
    global _settings_textbox
    global _text_visible

    if _settings_menu is not None:
        del _settings_menu
        _settings_menu = None

    if _settings_textbox is not None:
        del _settings_textbox
        _settings_textbox = None

    _text_visible = False

    collect()
