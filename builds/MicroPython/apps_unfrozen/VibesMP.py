import sys
from utime import ticks_diff, ticks_ms

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
            "[VibesMP] Keeping 220 MHz because background work is active.",
            2,
        )


def _finish_start(view_manager):
    """Initialize the VibesApp instance."""
    global _app

    try:
        from vibesmp_lib.loading import MusicLoader
        _loading = MusicLoader(view_manager.draw, "VibesMP...", view_manager.selected_color)
        _loading.animate()
    except Exception as e:
        print("[ERROR] Failed to init MusicLoader:", e)
        _loading = None

    try:
        from vibesmp_lib.app import VibesApp
        _app = VibesApp(view_manager, loading_screen=_loading)
        return True
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        sys.print_exception(e)
        if _loading:
            _loading.stop()
        _restore_frequency(view_manager)
        return False
    except OSError as e:
        print(f"[ERROR] Initialization failed: {e}")
        sys.print_exception(e)
        if _loading:
            _loading.stop()
        _restore_frequency(view_manager)
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected initialization failure: {e}")
        sys.print_exception(e)
        if _loading:
            _loading.stop()
        _restore_frequency(view_manager)
        return False


def start(view_manager):
    """Wait for a safe clock boundary before initializing VibesMP."""
    global _app, _startup_pending, _frequency_idle_since

    _app = None
    _startup_pending = True
    _frequency_idle_since = 0
    return True


def run(view_manager):
    """Execute the VibesApp logic."""
    if not view_manager or not hasattr(view_manager, 'storage'):
        print("[WARN] Invalid view_manager passed to run()")
        return

    global _app, _startup_pending
    if _startup_pending:
        if not _prepare_app_frequency(view_manager):
            return
        _startup_pending = False
        if not _finish_start(view_manager):
            view_manager.back()
        return

    try:
        if _app:
            app = _app
            render_due = app.run(view_manager)
            if render_due and _app is app and hasattr(app, "render"):
                _app.render(view_manager)
    except Exception as e:
        print(f"[ERROR] VibesApp.run() failed: {e}")
        sys.print_exception(e)


def stop(view_manager):
    """Cleanup the application and release resources."""
    if not view_manager or not hasattr(view_manager, 'storage'):
        return

    global _app, _startup_pending, _frequency_idle_since
    _startup_pending = False
    _frequency_idle_since = 0
    try:
        if _app:
            try:
                _app.stop(view_manager)
            except (AttributeError, OSError):
                pass  # stop() might not be available in all versions

            # Release storage and audio resources if methods exist
            if hasattr(view_manager.storage, 'release'):
                try:
                    view_manager.storage.release()
                except (AttributeError, OSError):
                    pass
            if hasattr(view_manager.audio, 'release'):
                try:
                    view_manager.audio.release()
                except (AttributeError, OSError):
                    pass

            print("[INFO] Application stopped")
    except Exception as e:
        print(f"[ERROR] Stop failed: {e}")
        sys.print_exception(e)
    finally:
        _restore_frequency(view_manager)
        _app = None


def create_view(view_manager, callback, *args):
    """Create a View with the given callback."""
    from picoware.system.view import View

    view = View("vibesmp", callback, *args)
    return view
