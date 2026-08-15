"""JS - JavaScript (MJS) engine wrapper."""

import mjs

class JS(mjs.MJS):
    """A MicroPython wrapper for the MJS JavaScript engine.
    
    Methods:
        - exec(path): Executes the JavaScript code from the specified file path and returns the result.
        - run(js_code): Executes the provided JavaScript code and returns the result.
    """