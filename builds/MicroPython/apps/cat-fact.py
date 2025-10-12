# picoware/apps/cat-fact.py

_http = None
_textbox = None

def start(view_manager) -> bool:
    '''Start the app'''
    from picoware.system.http import HTTP
    from picoware.gui.textbox import TextBox
    
    global _http, _textbox
    
    wifi = view_manager.get_wifi()
    
    if not wifi or not wifi.is_connected():
        return False
    
    _http = HTTP()
    
    # sync request for this example, although not preferred
    response = _http.get("https://catfact.ninja/fact")
    
    if not response:
        return False
    
    _textbox = TextBox(
        view_manager.get_draw(),
        0,
        320,
        view_manager.get_foreground_color(),
        view_manager.get_background_color()
    )
    
    _textbox.set_text(response.text)
           
    return True

def run(view_manager) -> None:
    '''Run the app'''
    from picoware.system.buttons import BUTTON_BACK
    
    inp = view_manager.get_input_manager()
    button = inp.button
    
    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
    
def stop(view_manager) -> None:
    '''Stop the app'''
    from gc import collect
    
    global _http, _textbox
    
    if _http:
        del _http
        _http = None
    
    if _textbox:
        del _textbox
        _textbox = None
        
    collect()
