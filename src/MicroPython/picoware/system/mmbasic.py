from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_CENTER,
    BUTTON_BACKSPACE,
)
from picoware.system.basic.interpreter import Interpreter
from picoware.system.basic.runtime import Runtime
from picoware.system.basic.parser import parse_source, create_default_def_type_map

class MMBasic:
    """MMBasic interpreter"""
    def __init__(self, view_manager, definition_type_map=None):
        from picoware.system.basic import io, gfx

        self._view_manager = view_manager
        self._console = io.PicowareConsole(view_manager)
        self._console.footer = "BACK=exit"
        self._gfx = gfx.PicowareGraphics(view_manager.draw, view_manager)
        self._interpreter = None
        self._script = None
        self._error = None
        self._def_type_map = definition_type_map

    def _feed_button(self, button: int):
        """Route a button press into the interpreter as input."""
        interp = self._interpreter

        if button == BUTTON_BACKSPACE:
            interp.feed_char("\b")
            return
        if button == BUTTON_CENTER:
            interp.feed_char("\n")
            return
        char = self._view_manager.input_manager.button_to_char(button)
        if char:
            interp.feed_char(char)

    def _load(self, source):
        """Parse the source; raises ParseError/LexerError on bad input."""
        self._script = source
        program = parse_source(source, def_type_map=self._def_type_map)
        runtime = Runtime(program, def_type_map=self._def_type_map or
                            create_default_def_type_map())
        self._interpreter = Interpreter(runtime, console=self._console, gfx=self._gfx)
        self._error = None
        return self

    def start(self, source: str = None, path: str = None) -> bool:
        """Run the provided MMBasic source code."""
        if source is None and path is None:
            return False
        if source is not None:
            self._load(source)
        elif path is not None:
            s = self._view_manager.storage
            if not s or not s.exists(path):
                return False
            self._load(s.read(path))

        self._interpreter.start()
        self._console.output("MMBasic 5.21  (Picoware)")
        self._console.output("-----------------------")
        self._console.output("")
        self._console.render()
        return True

    def run(self) -> bool:
        """Poll buttons, tick the interpreter, redraw the console."""
        button = self._view_manager.input_manager.button

        if button != -1:
            self._view_manager.input_manager.reset()
            if button == BUTTON_BACK:
                return False
            self._feed_button(button)

        state = self._interpreter.tick(120)

        if state.status == "error":
            self._console.output("")
            self._console.output("? " + state.message + " (line " + str(state.line) + ")")
            self._console.footer = "Back to exit"
        elif state.status == "ended":
            self._console.footer = "Program ended - back to exit"
        elif state.status == "stopped":
            self._console.footer = "Break - back to exit"
        else:
            self._console.set_input_active(self._interpreter.is_input_pending())

        if state.status == "error" or not self._gfx.display_active:
            self._console.render()

        return True
