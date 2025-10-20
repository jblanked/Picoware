# picoware/apps/cat-fact.py

_http = None
_textbox = None


def __alert(view_manager, reason: str) -> None:
    from picoware.gui.alert import Alert
    from time import sleep

    alert = Alert(
        view_manager.get_draw(),
        reason,
        view_manager.get_foreground_color(),
        view_manager.get_background_color(),
    )
    alert.draw("Error")
    sleep(2)
    del alert


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.http import HTTP
    from picoware.gui.textbox import TextBox
    from picoware.system.vector import Vector

    global _http, _textbox

    wifi = view_manager.get_wifi()

    draw = view_manager.get_draw()

    if not wifi:
        __alert(view_manager, "WiFi not available...")
        return False
    if not wifi.is_connected():
        __alert(view_manager, "WiFi not connected...")
        return False

    draw.text(Vector(0, 0), "Loading...", view_manager.get_foreground_color())

    draw.swap()

    _http = HTTP()

    # sync request for this example, although not preferred
    response = _http.get("https://catfact.ninja/fact")

    if not response:
        __alert(view_manager, "No response from server...")
        return False

    _textbox = TextBox(
        view_manager.get_draw(),
        0,
        320,
        view_manager.get_foreground_color(),
        view_manager.get_background_color(),
    )

    _textbox.set_text(response.json().get("fact", "No fact found"))

    response.close()

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    inp = view_manager.get_input_manager()
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _http, _textbox

    if _http:
        del _http
        _http = None

    if _textbox:
        del _textbox
        _textbox = None

    collect()
