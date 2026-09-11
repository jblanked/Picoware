"""C - Run C programs."""

from gc import collect
_programs = None
_programs_index = 0
_c = None

def _set_programs() -> bool:
    """Create a new JS engine instance.

    Returns:
        bool: True on success.
    """
    from picoware.system.c import C
    global _c
    del _c
    _c = None
    collect()
    _c = C()
    return _c is not None

def start(view_manager) -> bool:
    """Start the app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    from picoware.gui.menu import Menu

    if not view_manager.has_sd_card:
        view_manager.alert(
            "Applications app requires an SD card.",
            False,
        )
        return False

    # create c folder if it doesn't exist
    view_manager.storage.mkdir("picoware/c")

    global _programs

    _programs = Menu(
        view_manager.draw,
        "C",
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
        2,
    )

    file_list = view_manager.storage.listdir("picoware/c")
    for app in file_list:
        if app.startswith("."):
            continue
        if app.endswith(".c"):
            _programs.add_item(app[:-2])  # remove .c extension

    _programs.set_selected(_programs_index)

    _programs.draw()
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

    global _programs_index

    if not _programs:
        return

    button: int = view_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        _programs.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        _programs.scroll_down()
    elif button == BUTTON_BACK:
        _programs_index = 0
        view_manager.back()
    elif button == BUTTON_CENTER:
        _programs_index = _programs.selected_index

        # Get the selected app name
        selected_app = _programs.current_item

        if selected_app:
            if not _set_programs():
                view_manager.alert("\n[Script] Failed to initialize C engine\n")
                return
            
            from utime import ticks_ms

            start_time = ticks_ms()
            result = _c.exec(f'picoware/c/{selected_app}.c')
            view_manager.log(f"\n[C] {result}\n", -1)
            view_manager.log(
                f"[Script]: {selected_app} finished after {ticks_ms() - start_time} ms"
            )
            _programs.draw()



def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global _programs, _c
    if _programs is not None:
        del _programs
        _programs = None
    if _c is not None:
        del _c
        _c = None
    collect()
