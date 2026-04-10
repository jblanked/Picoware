# picoware/apps/games/free_roam/settings.py
_free_roam_settings_menu = None


def __free_roam_settings_start(view_manager) -> bool:
    """Start the settings view"""
    from picoware.gui.menu import Menu

    global _free_roam_settings_menu

    if _free_roam_settings_menu:
        del _free_roam_settings_menu
        _free_roam_settings_menu = None

    draw = view_manager.draw

    _free_roam_settings_menu = Menu(
        draw,  # draw instance
        "Settings",  # title
        0,  # y
        draw.size.y,  # height
        view_manager.foreground_color,  # text color
        view_manager.background_color,  # background color
        view_manager.selected_color,  # selected color
        view_manager.foreground_color,  # border/separator color
        2,  # border/separator width
    )

    _free_roam_settings_menu.add_item("Change User")
    _free_roam_settings_menu.add_item("Change Password")

    _free_roam_settings_menu.set_selected(0)
    _free_roam_settings_menu.draw()

    return True


def __free_roam_settings_run(view_manager) -> None:
    """Run the settings view"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_RIGHT,
        BUTTON_CENTER,
        BUTTON_LEFT,
    )

    global _free_roam_settings_menu

    input_button = view_manager.button

    if input_button in (BUTTON_UP, BUTTON_LEFT):
        _free_roam_settings_menu.scroll_up()
    elif input_button in (BUTTON_DOWN, BUTTON_RIGHT):
        _free_roam_settings_menu.scroll_down()
    elif input_button == BUTTON_BACK:
        view_manager.back()
    elif input_button == BUTTON_CENTER:
        from picoware.system.view import View

        current_item = _free_roam_settings_menu.current_item

        if current_item == "Change User":
            from free_roam.username import (
                __free_roam_user_run,
                __free_roam_user_start,
                __free_roam_user_stop,
            )

            view_manager.add(
                View(
                    "free_roam_user",
                    __free_roam_user_run,
                    __free_roam_user_start,
                    __free_roam_user_stop,
                )
            )
            view_manager.switch_to("free_roam_user")
        if current_item == "Change Password":
            from free_roam.password import (
                __free_roam_password_run,
                __free_roam_password_start,
                __free_roam_password_stop,
            )

            view_manager.add(
                View(
                    "free_roam_password",
                    __free_roam_password_run,
                    __free_roam_password_start,
                    __free_roam_password_stop,
                )
            )
            view_manager.switch_to("free_roam_password")


def __free_roam_settings_stop(view_manager) -> None:
    """Stop the settings view"""
    from gc import collect

    global _free_roam_settings_menu

    if _free_roam_settings_menu:
        del _free_roam_settings_menu
        _free_roam_settings_menu = None

    collect()
