"""
MBASIC 5.21 for Picoware/MicroPython.

A self-contained MMBasic interpreter: lexer, parser, runtime and a
cooperative interpreter, plus a Picoware console bridge that renders PRINT
output to the device screen and accepts button input.

Public API (used by the MMBasic.py app):
    run_source(source, console=None, def_type_map=None) -> Interpreter
    MMBasicEngine  - wraps parsing + interpreter lifecycle
    Lexer, Parser, Runtime, Interpreter, PicowareConsole
    LexerError, ParseError, RuntimeError_
"""

from .lexer import Lexer, LexerError, tokenize
from .parser import (
    Parser, ParseError, parse_source, create_default_def_type_map,
)
from .ast_nodes import ProgramNode
from .runtime import Runtime, RuntimeError_
from .interpreter import Interpreter, InterpreterState
from .basic_builtins import (
    BuiltinFunctions, TabMarker, SpcMarker, UsingFormatter, KeyInputPending,
)
from .picoware_io import PicowareConsole
from .picoware_gfx import PicowareGraphics, NullGraphics, rgb_to_565


def run_source(source, console=None, def_type_map=None, gfx=None):
    """Parse `source` and return a started Interpreter ready to tick().

    `console` may be a PicowareConsole or any object with output()/newline()/
    echo()/backspace(). If omitted, a plain console that prints to stdout is
    used (useful for host testing).
    """
    if console is None:
        console = _StdoutConsole()
    program = parse_source(source, def_type_map=def_type_map)
    runtime = Runtime(program, def_type_map=def_type_map or
                      create_default_def_type_map())
    interpreter = Interpreter(runtime, console=console, gfx=gfx)
    interpreter.start()
    return interpreter


class _StdoutConsole:
    """Minimal console for host testing / no-display use."""

    def __init__(self):
        self._buffer = ""

    def output(self, text):
        """Buffer text and print complete lines."""
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            print(line)

    def newline(self):
        """Print a newline."""
        self.output("\n")

    def echo(self, ch):
        """Append a character to the buffer."""
        self._buffer += ch

    def backspace(self):
        """Remove the last buffered character."""
        if self._buffer:
            self._buffer = self._buffer[:-1]

    def pos(self):
        """Return the current buffered column."""
        return len(self._buffer)


class MMBasicEngine:
    """High-level wrapper: parse + run a BASIC program, driving input.

    Example (host):
        engine = MMBasicEngine()
        engine.load('10 PRINT "HELLO"')
        while engine.tick(500).status == "running":
            pass
    """

    def __init__(self, console=None, def_type_map=None, gfx=None):
        """Set up the console, default types and graphics backend."""
        self.console = console
        self.def_type_map = def_type_map
        self.gfx = gfx
        self.interpreter = None
        self.program_text = ""
        self.error = None

    def load(self, source):
        """Parse the source; raises ParseError/LexerError on bad input."""
        self.program_text = source
        program = parse_source(source, def_type_map=self.def_type_map)
        runtime = Runtime(program, def_type_map=self.def_type_map or
                          create_default_def_type_map())
        self.interpreter = Interpreter(runtime, console=self.console, gfx=self.gfx)
        self.error = None
        return self

    def run(self, max_statements=500):
        """Start and run to completion (host use; blocks on input)."""
        if self.interpreter is None:
            raise RuntimeError("No program loaded")
        self.interpreter.start()
        state = self.interpreter.tick(max_statements)
        while state.status == "running" or state.status == "input":
            if state.status == "input":
                # No console input source on the host; treat Enter as blank.
                self.interpreter.feed_char("\n")
            state = self.interpreter.tick(max_statements)
        return state
