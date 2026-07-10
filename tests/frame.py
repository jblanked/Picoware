from utime import ticks_ms, ticks_diff
import micropython

start_time = None
last_time = None

@micropython.viper
def start(view_manager) -> bool:
    """Start the app"""
    global start_time, last_time
    start_time = ticks_ms()
    last_time = start_time
    return True

@micropython.native
def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    global last_time

    button = view_manager._button

    if button == BUTTON_BACK:
        view_manager.back()
        return

    now = ticks_ms()
    dt = ticks_diff(now, last_time)
    last_time = now

    d = view_manager.draw
    d.erase()
    d._text(10, 10, f"Time since start: {ticks_diff(now, start_time)} ms", 0xFFFF)
    fps = 1000 / dt if dt > 0 else 0
    d._text(10, 20, f"Frames per second: {fps:.2f}", 0xFFFF)
    d.swap()

@micropython.native
def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    collect()

from picoware.system.view_manager import ViewManager
from picoware.system.view import View

vm = None

try:
    vm = ViewManager()
    vm.add(
        View(
            "app_tester",
            run,
            start,
            stop,
        )
    )
    vm.switch_to("app_tester")
    while True:
        vm.run()
finally:
    del vm
    vm = None