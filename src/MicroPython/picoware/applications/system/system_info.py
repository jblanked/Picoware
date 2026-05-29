_system_info = None


def __set_text():
    from picoware.system.system import System

    if _system_info:
        system = System()
        info = f"""System Information
        
        Board: {system.board_name}
        Device: {system.device_name}
        Frequency: {system.freq} MHz
        
        Free Heap: {system.free_heap} bytes
        Used Heap: {system.used_heap} bytes
        Total Heap: {system.total_heap} bytes

        Free PSRAM: {system.free_psram} bytes
        Used PSRAM: {system.used_psram} bytes
        Total PSRAM: {system.total_psram} bytes

        Free Flash: {system.free_flash} bytes
        Used Flash: {system.used_flash} bytes
        Total Flash: {system.total_flash} bytes
        """
        _system_info.set_text(info)


def start(view_manager) -> bool:
    """Start the loading animation."""
    from picoware.gui.textbox import TextBox

    global _system_info

    if _system_info is None:
        _system_info = TextBox(
            view_manager.draw,
            0,
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
        )

        __set_text()
        _system_info._set_cursor(0)

    return True


def run(view_manager) -> None:
    """Animate the loading spinner."""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_UP, BUTTON_DOWN

    button: int = view_manager.button

    if button == BUTTON_BACK:
        view_manager.back()
    elif button == BUTTON_UP:
        _system_info.scroll_up()
    elif button == BUTTON_DOWN:
        _system_info.scroll_down()


def stop(view_manager) -> None:
    """Stop the loading animation."""
    from gc import collect

    global _system_info
    if _system_info is not None:
        del _system_info
        _system_info = None

    collect()
