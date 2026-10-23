"""System Info - Display system information."""

_system_info = None
_last_refresh = None


def __set_text(view_manager, scroll_delta=0):
    """Populate the system information text box.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from picoware.system.system import System
    from picoware.system.boards import (
        BOARD_ID, BOARD_WAVESHARE_2_06, BOARD_WAVESHARE_C6_2_06,
    )

    if _system_info:
        system = System()
        free_flash, used_flash, total_flash = system.flash_usage()
        battery = view_manager.battery
        runtime = getattr(battery, "runtime", None)
        percentage = (battery.cached_percentage if hasattr(battery, "cached_percentage")
                      else battery.percentage)
        level = "Unavailable" if percentage is None else str(percentage) + "%"
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

        Free Flash: {free_flash} bytes
        Used Flash: {used_flash} bytes
        Total Flash: {total_flash} bytes

        Battery Level: {level}
        """
        if runtime is not None:
            info += "Battery remaining: " + runtime.text + "\n"
        elif battery.time_remaining > 0:
            info += f"Battery time remaining: {battery.time_remaining} minutes\n"
        if battery.has_voltage:
            try:
                voltage = battery.voltage
                # The shared Waveshare driver returns volts; preserve its API.
                if BOARD_ID in (BOARD_WAVESHARE_2_06, BOARD_WAVESHARE_C6_2_06):
                    voltage = round(voltage * 1000)
                info += f"Battery voltage: {voltage} mV\n"
            except (OSError, RuntimeError):
                info += "Battery voltage: Unavailable\n"

        _system_info.set_text(info, preserve_scroll=True, scroll_delta=scroll_delta)


def start(view_manager) -> bool:
    """Start the app and show system information.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        bool: True if the app started.
    """
    from picoware.gui.textbox import TextBox

    global _system_info, _last_refresh

    if _system_info is None:
        _system_info = TextBox(
            view_manager.draw,
            0,
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
        )

        from time import ticks_ms

        if hasattr(view_manager.battery, "update"):
            view_manager.battery.update()
        _last_refresh = ticks_ms()
        __set_text(view_manager)

    return True


def run(view_manager) -> None:
    """Run the app and handle scrolling input.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from picoware.system.buttons import BUTTON_BACK, BUTTON_UP, BUTTON_DOWN

    from time import ticks_ms, ticks_diff

    global _last_refresh
    now = ticks_ms()
    button: int = view_manager.button

    if button == BUTTON_BACK:
        view_manager.back()
        return
    scroll_delta = -1 if button == BUTTON_UP else (1 if button == BUTTON_DOWN else 0)

    if _last_refresh is None or ticks_diff(now, _last_refresh) >= 30000:
        _last_refresh = now
        __set_text(view_manager, scroll_delta)
    elif scroll_delta < 0:
        _system_info.scroll_up()
    elif scroll_delta > 0:
        _system_info.scroll_down()


def stop(view_manager) -> None:
    """Stop the app and clean up.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.
    """
    from gc import collect

    global _system_info
    if _system_info is not None:
        del _system_info
        _system_info = None

    collect()
