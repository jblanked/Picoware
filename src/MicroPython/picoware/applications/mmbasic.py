from micropython import const

STATE_MENU = const(0)
STATE_RUNNING = const(1)

_menu = None
_mmbasic_index = 0
_mmbasic = None
_state = STATE_MENU


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.menu import Menu
    from picoware.system.mmbasic import MMBasic

    if not view_manager.has_sd_card:
        view_manager.alert(
            "Applications app requires an SD card.",
            False,
        )
        return False

    # create mmbasic folder if it doesn't exist
    view_manager.storage.mkdir("picoware/mmbasic")

    global _mmbasic
    global _menu
    global _state

    _state = STATE_MENU

    _menu = Menu(
        view_manager.draw,
        "Mmbasic",
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
        2,
    )

    _mmbasic = MMBasic(view_manager)
    file_list = view_manager.storage.listdir("picoware/mmbasic")
    for app in file_list:
        if app.startswith("."):
            continue
        if app.endswith(".bas"):
            _menu.add_item(app[:-4])  # remove .bas extension

    _menu.set_selected(_mmbasic_index)

    _menu.draw()
    return True


def run(view_manager) -> None:
    """Run the app."""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_RIGHT,
    )

    global _mmbasic_index, _state

    if not _mmbasic:
        return

    button: int = view_manager.button

    if _state == STATE_RUNNING:
        if not _mmbasic.run():
            _state = STATE_MENU
            _menu.draw()
        return

    if button in (BUTTON_UP, BUTTON_LEFT):
        _menu.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        _menu.scroll_down()
    elif button == BUTTON_BACK:
        _mmbasic_index = 0
        view_manager.back()
    elif button == BUTTON_CENTER:
        _mmbasic_index = _menu.selected_index

        # Get the selected app name
        selected_app = _menu.current_item

        if selected_app and _mmbasic:
            if not _mmbasic.start(source=view_manager.storage.read(f'picoware/mmbasic/{selected_app}.bas')):
                view_manager.alert(f"\n[MMBasic] {selected_app} failed to start\n")
                return
            _state = STATE_RUNNING



def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _mmbasic, _menu
    if _mmbasic is not None:
        del _mmbasic
        _mmbasic = None
    if _menu is not None:
        del _menu
        _menu = None
    collect()
