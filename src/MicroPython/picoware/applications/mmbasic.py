from micropython import const
from gc import collect
from picoware.system.decorator import storage_required
from picoware.system.mmbasic import MMBasic

STATE_MENU = const(0)
STATE_RUNNING = const(1)
STATE_FINISHED = const(2)

_menu = None
_mmbasic_index = 0
_mmbasic = None
_state = STATE_MENU

def _set_mmbasic(vm) -> bool:
    """Create a new MMBasic instance.

    Args:
        vm (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    global _mmbasic
    del _mmbasic
    _mmbasic = None
    collect()
    _mmbasic = MMBasic(vm)
    return _mmbasic is not None

@storage_required
def start(view_manager) -> bool:
    """Start the app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    from picoware.gui.menu import Menu

    # create mmbasic folder if it doesn't exist
    view_manager.storage.mkdir("picoware/mmbasic")

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
    """Run the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_RIGHT,
    )

    global _mmbasic_index, _state, _mmbasic, _menu

    button: int = view_manager.button

    if _state == STATE_RUNNING:
        if _mmbasic is None or not _mmbasic.run():
            if _mmbasic is not None and _mmbasic.is_over and _mmbasic.has_graphics:
                _state = STATE_FINISHED
            else:
                _state = STATE_MENU
                _menu.draw()
        return

    if _state == STATE_FINISHED:
        if button == BUTTON_BACK:
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

        if selected_app:
            if not _set_mmbasic(view_manager):
                view_manager.alert("\n[MMBasic] Failed to initialize MMBasic\n")
                return False
            
            if not _mmbasic.start(source=view_manager.storage.read(f'picoware/mmbasic/{selected_app}.bas')):
                view_manager.alert(f"\n[MMBasic] {selected_app} failed to start\n")
                return
            _state = STATE_RUNNING



def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global _mmbasic, _menu
    if _mmbasic is not None:
        del _mmbasic
        _mmbasic = None
    if _menu is not None:
        del _menu
        _menu = None
    collect()
