"""SD-installed PicoChess lifecycle."""

_app = None


def start(view_manager):
    from .splash import show
    from time import ticks_ms, ticks_diff, sleep_ms
    show(view_manager)
    started = ticks_ms()
    from .app import App
    remaining = 1500 - ticks_diff(ticks_ms(), started)
    if remaining > 0: sleep_ms(remaining)
    global _app
    _app = App(view_manager)
    return True


def run(view_manager):
    if _app is not None:
        _app.run()


def stop(view_manager):
    global _app
    if _app is not None:
        _app.close()
        _app = None
