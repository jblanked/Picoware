"""
MicroBrowser launcher for Picoware.
"""

_app = None


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

    from micro_browser.micro_browser_app import MicroBrowserApp

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
