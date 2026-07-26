import sys

_app = None


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
        view_manager.freq()
        return False
    except OSError as e:
        print(f"[ERROR] Initialization failed: {e}")
        sys.print_exception(e)
        if _loading:
            _loading.stop()
        view_manager.freq()
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected initialization failure: {e}")
        sys.print_exception(e)
        if _loading:
            _loading.stop()
        view_manager.freq()
        return False


def start(view_manager):
    """Initialize VibesMP at the portable low clock."""
    global _app

    _app = None
    view_manager.freq(True)
    return _finish_start(view_manager)


def run(view_manager):
    """Execute the VibesApp logic."""
    if not view_manager or not hasattr(view_manager, 'storage'):
        print("[WARN] Invalid view_manager passed to run()")
        return

    global _app
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

    global _app
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
        view_manager.freq()
        _app = None


def create_view(view_manager, callback, *args):
    """Create a View with the given callback."""
    from picoware.system.view import View

    view = View("vibesmp", callback, *args)
    return view
