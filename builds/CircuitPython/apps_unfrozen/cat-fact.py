# picoware/apps/cat-fact.py

_http = None
_textbox = None


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.http import HTTP
    from picoware.gui.textbox import TextBox
    from picoware.system.vector import Vector

    global _http, _textbox

    wifi = view_manager.wifi

    draw = view_manager.draw

    if not wifi:
        view_manager.alert("WiFi not available...", False)
        return False
    if not wifi.is_connected():
        view_manager.alert("WiFi not connected...", False)
        return False

    draw.text(Vector(0, 0), "Loading...", view_manager.foreground_color)

    draw.swap()

    _http = HTTP()

    # sync request for this example, although not preferred
    response = _http.get("https://catfact.ninja/fact")

    if not response:
        view_manager.alert("No response from server...", False)
        return False

    _textbox = TextBox(
        draw,
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
    )

    _textbox.set_text(response.json().get("fact", "No fact found"))

    response.close()

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    inp = view_manager.input_manager
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
