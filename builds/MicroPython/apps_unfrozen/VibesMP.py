import sys
import time

_app = None

def start(view_manager):
    """Initialize the VibesApp instance."""
    global _app

    try:
        from vibesmp_lib.resources import MusicLoader
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
        return False
    except OSError as e:
        print(f"[ERROR] Initialization failed: {e}")
        sys.print_exception(e)
        if _loading:
            _loading.stop()
        return False


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
        _app = None


def create_view(view_manager, callback, *args):
    """Create a View with the given callback."""
    from picoware.system.view import View

    view = View("vibesmp", callback, *args)
    return view


if __name__ == "__main__":
    # Create the main view manager
    vm = None
    try:
        from picoware.system.view_manager import ViewManager
        from picoware.system.view import View

        vm = ViewManager()

        # Add a view with our custom callback
        vm.add(
            View("vibesmp", run, start, stop),
            storage=vm.storage,
            audio=vm.audio
        )

        # Switch to the "vibesmp" view
        vm.switch_to("vibesmp")

        print("[INFO] VibesMP started at ~50fps (20ms sleep)")

        while True:
            vm.run()
            time.sleep_ms(20)  # Throttling to save CPU/SD bus
    finally:
        if vm and hasattr(vm, 'storage'):
            try:
                del vm.storage
                del vm.audio
            except Exception:
                pass
