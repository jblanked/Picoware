from micropython import const
from picoware.system.js import JS

your_ssid = const("your-ssid")
your_pass = const("your-pass")

_js = None
_wifi_started = False
_status_printed = False


def start(view_manager) -> bool:
    """Start the app — import wifi and begin async connect."""
    global _js, _wifi_started

    _js = JS()
    _js.run(f"""
let wifi = import('wifi');
if (!wifi.connectAsync('{your_ssid}', '{your_pass}')) {{
    log('Failed to start wifi connection');
}}
""")

    _wifi_started = True
    return True


def run(view_manager) -> None:
    """Run the app — poll wifi connection status each frame."""
    from picoware.system.buttons import BUTTON_BACK

    global _status_printed, _js, _wifi_started

    if view_manager.button == BUTTON_BACK:
        view_manager.back()
    
    if not _wifi_started or _js is None:
        return

    state = _js.run("wifi.state;")
    if state == 1:  # WIFI_STATE_CONNECTING
        print("connecting...")
    elif state == 2:  # WIFI_STATE_CONNECTED
        info = _js.run("""
JSON.stringify({ip: wifi.deviceIp, mac: wifi.macAddress});
""")
        print("WiFi connected: " + info)
    elif state == 0:  # WIFI_STATE_IDLE
        print("Connection failed — state is idle")
    else:  # WIFI_STATE_ISSUE (3) or WIFI_STATE_TIMEOUT (4)
        info = _js.run("""
JSON.stringify({state: wifi.state, error: wifi.lastError});
""")
        print("Connection failed: " + info)
    


def stop(view_manager) -> None:
    """Stop the app."""
    global _js
    from gc import collect

    if _js is not None:
        del _js
        _js = None
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
