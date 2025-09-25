_dark_mode = None
_toggle_index = 0


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.toggle import Toggle
    from picoware.system.vector import Vector
    from picoware.system.storage import Storage

    global _dark_mode

    if _dark_mode is None:
        _dark_mode = Toggle(
            view_manager.get_draw(),
            Vector(10, 10),
            Vector(300, 30),
            "Dark Mode",
            False,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
            view_manager.get_selected_color(),
            view_manager.get_foreground_color(),
            2,
        )

        storage: Storage = view_manager.get_storage()

        # create settings directory if it doesn't exist
        storage.mkdir("picoware/settings")

        data = storage.read("picoware/settings/dark_mode.json")

        if data is not None:
            try:
                import ujson

                obj = ujson.loads(data)
                if "dark_mode" in obj:
                    _dark_mode.set_state(bool(obj["dark_mode"]))
            except Exception:
                pass

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.colors import TFT_BLACK, TFT_WHITE
    from picoware.system.buttons import (
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_BACK,
    )

    input_manager = view_manager.get_input_manager()
    button = input_manager.get_last_button()

    global _dark_mode, _toggle_index

    if button == BUTTON_UP:
        if _toggle_index > 0:
            _toggle_index -= 1
            input_manager.reset()
    elif button == BUTTON_DOWN:
        if _toggle_index < 1:
            _toggle_index += 1
            input_manager.reset()
    elif button in (BUTTON_LEFT, BUTTON_BACK):
        view_manager.back()
        input_manager.reset()
    elif button == BUTTON_CENTER:
        if _toggle_index == 0 and _dark_mode is not None:
            if _dark_mode:
                _dark_mode.toggle()

                # Save the state to flash
                import ujson

                obj = {"dark_mode": _dark_mode.get_state()}
                data = ujson.dumps(obj)
                storage = view_manager.get_storage()
                storage.write("picoware/settings/dark_mode.json", data)

                # Update the background color based on the toggle state
                # we should probably move this to the ViewManager..
                if _dark_mode.get_state():
                    view_manager.set_background_color(TFT_BLACK)
                    view_manager.set_foreground_color(TFT_WHITE)
                else:
                    view_manager.set_background_color(TFT_WHITE)
                    view_manager.set_foreground_color(TFT_BLACK)

        input_manager.reset(True)

    if _dark_mode is not None:
        _dark_mode.draw()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _dark_mode

    if _dark_mode:
        del _dark_mode
        _dark_mode = None

    collect()
