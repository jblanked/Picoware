"""
MicroBrowser launcher for Picoware.
"""

_app = None


def _add_app_path():
    import sys

    candidates = (
        "/sd/picoware/micro_browser",
        "/picoware/micro_browser",
        "picoware/micro_browser",
    )

    for path in candidates:
        for filename in ("micro_browser_app.mpy", "micro_browser_app.py"):
            try:
                import os
                os.stat(path + "/" + filename)

                if path not in sys.path:
                    sys.path.insert(0, path)

                return path
            except OSError:
                pass

    raise ImportError(
        "micro_browser_app module not found in "
        "/sd/picoware/micro_browser"
    )


def start(view_manager) -> bool:
    global _app

    wifi = view_manager.wifi

    if not wifi:
        view_manager.alert("WiFi not available...", False)
        return False

    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        view_manager.alert("WiFi not connected", False)
        connect_to_saved_wifi(view_manager)
        return False

    _add_app_path()

    from micro_browser_app import MicroBrowserApp

    _app = MicroBrowserApp(view_manager)
    return _app.start()


def run(view_manager) -> None:
    if _app:
        _app.run()


def stop(view_manager) -> None:
    global _app

    if _app:
        _app.stop()
        del _app
        _app = None

    from gc import collect
    collect()
