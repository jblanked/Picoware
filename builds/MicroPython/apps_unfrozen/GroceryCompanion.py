import sys
from utime import ticks_diff, ticks_ms

# VERSION 2.23
_app = None
_clock_changed = False
_startup_pending = False
_frequency_idle_since = 0
APP_CPU_FREQUENCY = 220000000
FREQUENCY_SETTLE_MS = 100


def _thread_manager_is_idle(view_manager):
    thread_manager = view_manager.thread_manager
    return thread_manager is None or thread_manager.is_idle


def _prepare_app_frequency(view_manager):
    global _clock_changed, _frequency_idle_since

    now = ticks_ms()
    if not _thread_manager_is_idle(view_manager):
        _frequency_idle_since = 0
        return False
    if _frequency_idle_since == 0:
        _frequency_idle_since = now
        return False
    if ticks_diff(now, _frequency_idle_since) < FREQUENCY_SETTLE_MS:
        return False
    view_manager.freq(False, APP_CPU_FREQUENCY)
    _clock_changed = True
    _frequency_idle_since = 0
    return True


def _restore_frequency(view_manager):
    global _clock_changed

    if not _clock_changed:
        return
    if _thread_manager_is_idle(view_manager):
        view_manager.freq()
        _clock_changed = False
    else:
        view_manager.log(
            "[GroceryCompanion] Keeping 220 MHz because background work is active.",
            2,
        )


def _finish_start(view_manager) -> bool:
    global _app

    # Initial Loading Screen
    try:
        from grocery_lib.loading import CartLoader
        _loading = CartLoader(view_manager.draw, "Grocery Companion...")
        _loading.animate()
    except:
        _loading = None

    try:
        from grocery_lib.app import GroceryApp
        _app = GroceryApp(view_manager, _loading)
        if _loading: _loading.stop()
        _app._initial_boot()
        if _loading: del _loading
        return True
    except Exception as e:
        sys.print_exception(e)
        if "_loading" in locals() and _loading:
            _loading.stop()
        return False


def start(view_manager) -> bool:
    global _app, _startup_pending, _frequency_idle_since
    _app = None
    _startup_pending = True
    _frequency_idle_since = 0
    return True


def run(view_manager) -> None:
    global _startup_pending
    if _startup_pending:
        if not _prepare_app_frequency(view_manager):
            return
        _startup_pending = False
        if not _finish_start(view_manager):
            _restore_frequency(view_manager)
            view_manager.back()
        return

    if _app:
        _app.run()


def stop(view_manager) -> None:
    global _app, _startup_pending, _frequency_idle_since
    _startup_pending = False
    _frequency_idle_since = 0
    if _app:
        try: _app.stop()
        except Exception: pass
        _app = None

    from gc import collect
    collect()
    _restore_frequency(view_manager)
