# picoware/apps/flip_social/settings.py

_flip_social_settings_menu = None


def __flip_social_settings_start(view_manager) -> bool:
    """Start the settings view"""
    from picoware.gui.menu import Menu

    global _flip_social_settings_menu

    if _flip_social_settings_menu:
        del _flip_social_settings_menu
        _flip_social_settings_menu = None

    draw = view_manager.get_draw()

    _flip_social_settings_menu = Menu(
        draw,  # draw instance
        "Settings",  # title
        0,  # y
        320,  # height
        view_manager.get_foreground_color(),  # text color
        view_manager.get_background_color(),  # background color
        view_manager.get_selected_color(),  # selected color
        view_manager.get_foreground_color(),  # border/separator color
        2,  # border/separator width
    )

    _flip_social_settings_menu.add_item("Change User")
    _flip_social_settings_menu.add_item("Change Password")

    _flip_social_settings_menu.set_selected(0)
    _flip_social_settings_menu.draw()

    return True


def __flip_social_settings_run(view_manager) -> None:
    """Run the settings view"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )

    global _flip_social_settings_menu

    input_manager = view_manager.get_input_manager()
    input_button = input_manager.get_last_button()

    if input_button == BUTTON_UP:
        input_manager.reset()
        _flip_social_settings_menu.scroll_up()
    elif input_button == BUTTON_DOWN:
        input_manager.reset()
        _flip_social_settings_menu.scroll_down()
    elif input_button == BUTTON_BACK:
        input_manager.reset()
        view_manager.back()
    elif input_button in (BUTTON_CENTER, BUTTON_RIGHT):
        from picoware.system.view import View

        input_manager.reset()
        current_item = _flip_social_settings_menu.get_current_item()

        if current_item == "Change User":
            from flip_social.username import (
                __flip_social_user_run,
                __flip_social_user_start,
                __flip_social_user_stop,
            )

            view_manager.add(
                View(
                    "flip_social_user",
                    __flip_social_user_run,
                    __flip_social_user_start,
                    __flip_social_user_stop,
                )
            )
            view_manager.switch_to("flip_social_user")
        if current_item == "Change Password":
            from flip_social.password import (
                __flip_social_password_run,
                __flip_social_password_start,
                __flip_social_password_stop,
            )

            view_manager.add(
                View(
                    "flip_social_password",
                    __flip_social_password_run,
                    __flip_social_password_start,
                    __flip_social_password_stop,
                )
            )
            view_manager.switch_to("flip_social_password")


def __flip_social_settings_stop(view_manager) -> None:
    """Stop the settings view"""
    from gc import collect

    global _flip_social_settings_menu

    if _flip_social_settings_menu:
        del _flip_social_settings_menu
        _flip_social_settings_menu = None

    collect()
