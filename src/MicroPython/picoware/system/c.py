"""C engine wrapper."""

import c

class C(c.C):
    """A MicroPython wrapper for the C engine.
    
    Methods:
        - exec(path): Executes the C code from the specified file path and returns the result.
        - run(c_code): Executes the provided C code and returns the result.
    """