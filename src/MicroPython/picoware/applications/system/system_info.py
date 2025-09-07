_system_info = None


def start(view_manager) -> bool:
    """Start the loading animation."""
    from picoware.gui.textbox import TextBox
    from picoware.system.system import System
    from picoware.system.colors import TFT_BLACK, TFT_WHITE

    global _system_info
    if _system_info is None:
        _system_info = TextBox(view_manager.draw, 0, 320, TFT_WHITE, TFT_BLACK)

        system = System()
        info = f"System Information\n\nFree Heap: {system.free_heap()} bytes\nUsed Heap: {system.used_heap()} bytes\nFree PSRAM: {system.free_psram()} bytes\nUsed PSRAM: {system.used_psram()} bytes"
        _system_info.set_text(info)

    return True


def run(view_manager) -> None:
    """Animate the loading spinner."""
    from picoware.system.buttons import BUTTON_BACK

    input_manager = view_manager.input_manager
    button: int = input_manager.get_last_button()

    if button == BUTTON_BACK:
        view_manager.back()
        input_manager.reset()


def stop(view_manager) -> None:
    """Stop the loading animation."""
    from gc import collect

    global _system_info
    if _system_info:
        del _system_info
        _system_info = None
    collect()
