_scripts = None
_scripts_index = 0
_js = None


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.menu import Menu
    from picoware.system.js import JS

    if not view_manager.has_sd_card:
        view_manager.alert(
            "Applications app requires an SD card.",
            False,
        )
        return False

    # create scripts folder if it doesn't exist
    view_manager.storage.mkdir("picoware/scripts")

    global _scripts
    global _js

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

    _js = JS()
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
    """Run the app."""
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

        if selected_app and _js:
            from utime import ticks_ms

            start_time = ticks_ms()
            result = _js.exec(f'picoware/scripts/{selected_app}.js')
            view_manager.log(f"\n[JS] {result}\n", -1)
            view_manager.log(
                f"[Script]: {selected_app} finished after {ticks_ms() - start_time} ms"
            )



def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _scripts, _js
    if _scripts is not None:
        del _scripts
        _scripts = None
    if _js is not None:
        del _js
        _js = None
    collect()
