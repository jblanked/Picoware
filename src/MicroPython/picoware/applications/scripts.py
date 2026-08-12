from gc import collect
_scripts = None
_scripts_index = 0
_js = None

def _set_scripts() -> bool:
    """Create a new JS engine instance.

    Returns:
        bool: True on success.
    """
    from picoware.system.js import JS
    global _js
    del _js
    _js = None
    collect()
    _js = JS()
    return _js is not None

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

    # create scripts folder if it doesn't exist
    view_manager.storage.mkdir("picoware/scripts")

    global _scripts

    _scripts = Menu(
        view_manager.draw,
        "Scripts",
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
        view_manager.foreground_color,
        2,
    )

    file_list = view_manager.storage.listdir("picoware/scripts")
    for app in file_list:
        if app.startswith("."):
            continue
        if app.endswith(".js"):
            _scripts.add_item(app[:-3])  # remove .js extension

    _scripts.set_selected(_scripts_index)

    _scripts.draw()
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

    global _scripts_index

    if not _scripts:
        return

    button: int = view_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        _scripts.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        _scripts.scroll_down()
    elif button == BUTTON_BACK:
        _scripts_index = 0
        view_manager.back()
    elif button == BUTTON_CENTER:
        _scripts_index = _scripts.selected_index

        # Get the selected app name
        selected_app = _scripts.current_item

        if selected_app:
            if not _set_scripts():
                view_manager.alert("\n[Script] Failed to initialize JS engine\n")
                return
            
            from utime import ticks_ms

            start_time = ticks_ms()
            result = _js.exec(f'picoware/scripts/{selected_app}.js')
            view_manager.log(f"\n[JS] {result}\n", -1)
            view_manager.log(
                f"[Script]: {selected_app} finished after {ticks_ms() - start_time} ms"
            )
            _scripts.draw()



def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global _scripts, _js
    if _scripts is not None:
        del _scripts
        _scripts = None
    if _js is not None:
        del _js
        _js = None
    collect()
