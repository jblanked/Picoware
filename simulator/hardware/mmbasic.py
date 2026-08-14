"""Simulator adapter for Picoware's native ``mmbasic`` module.

Firmware uses the C module in ``src/MicroPython/mmbasic``. The Unix simulator
runs the last Python implementation from immediately before that C port, kept
in ``mmbasic_runtime``. This adapter exposes the same constructor and lifecycle
methods as the native module while rendering through the simulator LCD and SD
shims.
"""

import sim_runtime

from mmbasic_runtime.gfx import PicowareGraphics
from mmbasic_runtime.interpreter import Interpreter
from mmbasic_runtime.io import PicowareConsole
from mmbasic_runtime.parser import create_default_def_type_map, parse_source
from mmbasic_runtime.runtime import Runtime


_STATUS_RUNNING = 0
_STATUS_ENDED = 1
_STATUS_STOPPED = 2
_STATUS_INPUT = 3
_STATUS_ERROR = 4


class _Vector:
    __slots__ = ("x", "y", "z")

    def __init__(self, x=0, y=0, z=0):
        self.x = int(x)
        self.y = int(y)
        self.z = int(z)


class _Font:
    __slots__ = ("size",)

    def __init__(self, size):
        self.size = int(size)


class _DrawAdapter:
    """Expose the draw attributes used by the Python MMBasic engine."""

    __slots__ = ("size", "font_size", "_background", "_font_default")

    def __init__(self, width, height, font_width, font_height, background, font):
        self.size = _Vector(width, height)
        self.font_size = _Vector(font_width, font_height)
        self._background = int(background)
        self._font_default = _Font(font)

    def _display(self):
        return sim_runtime.get_lcd()

    def erase(self):
        self._clear(self._background)

    def fill_screen(self, color):
        self._clear(color)

    def _clear(self, color):
        display = self._display()
        if display is not None:
            display._clear(color)

    def _pixel(self, x, y, color):
        display = self._display()
        if display is not None:
            display._pixel(x, y, color)

    def _line(self, x1, y1, x2, y2, color):
        display = self._display()
        if display is not None:
            display._line(x1, y1, x2, y2, color)

    def _rectangle(self, x, y, width, height, color):
        display = self._display()
        if display is not None:
            display._rectangle(x, y, width, height, color)

    def _fill_rectangle(self, x, y, width, height, color):
        display = self._display()
        if display is not None:
            display._fill_rectangle(x, y, width, height, color)

    def _circle(self, x, y, radius, color):
        display = self._display()
        if display is not None:
            display._circle(x, y, radius, color)

    def _fill_circle(self, x, y, radius, color):
        display = self._display()
        if display is not None:
            display._fill_circle(x, y, radius, color)

    def _fill_triangle(self, x1, y1, x2, y2, x3, y3, color):
        display = self._display()
        if display is not None:
            display._fill_triangle(x1, y1, x2, y2, x3, y3, color)

    def _text(self, x, y, text, color, font_size=None):
        display = self._display()
        if display is not None:
            display._text(x, y, text, color, font_size)
        else:
            sim_runtime.note_text(text)

    def swap(self):
        display = self._display()
        if display is not None:
            display.swap()


class _StorageAdapter:
    __slots__ = ()

    def exists(self, path):
        import sd_mp

        return sd_mp.exists(path)

    def read(self, path):
        import sd_mp

        data = sd_mp.read(path)
        if isinstance(data, bytes):
            return data.decode("utf-8")
        return str(data)


class _ViewManagerAdapter:
    __slots__ = (
        "draw",
        "foreground_color",
        "background_color",
        "selected_color",
        "storage",
    )

    def __init__(self, draw, foreground, background, selected):
        self.draw = draw
        self.foreground_color = int(foreground)
        self.background_color = int(background)
        self.selected_color = int(selected)
        self.storage = _StorageAdapter()

    def log(self, message, level=-1):
        del level
        print("[sim:mmbasic]", message)


class MMBasic:
    """Native-compatible MMBasic class backed by the Python interpreter."""

    __slots__ = (
        "_host",
        "_console",
        "_gfx",
        "_interpreter",
        "_source",
        "_error",
    )

    def __init__(
        self,
        foreground_color,
        background_color,
        selected_color,
        screen_width,
        screen_height,
        font_width,
        font_height,
        draw_background,
        default_font_size,
    ):
        draw = _DrawAdapter(
            screen_width,
            screen_height,
            font_width,
            font_height,
            draw_background,
            default_font_size,
        )
        self._host = _ViewManagerAdapter(
            draw,
            foreground_color,
            background_color,
            selected_color,
        )
        self._console = PicowareConsole(self._host)
        self._gfx = PicowareGraphics(self._host)
        self._interpreter = None
        self._source = ""
        self._error = None

    @property
    def has_graphics(self):
        """Return whether the running program has drawn graphics."""
        return self._gfx is not None and self._gfx.has_drawn

    def _start(self, source=None, path=None):
        """Parse and start source text or a file on the simulated SD card."""
        if source is None:
            if path is None:
                return False
            try:
                source = self._host.storage.read(path)
            except Exception:
                return False
        if isinstance(source, bytes):
            try:
                source = source.decode("utf-8")
            except Exception:
                return False
        if not isinstance(source, str) or not source.strip():
            return False

        try:
            program = parse_source(source)
            runtime = Runtime(program, def_type_map=create_default_def_type_map())
            self._interpreter = Interpreter(
                runtime,
                console=self._console,
                gfx=self._gfx,
            )
            self._interpreter.start()
        except Exception as error:
            self._interpreter = None
            self._error = error
            return False

        self._source = source
        self._error = None
        self._console.footer = "BACK=exit"
        self._console.output("MMBasic 6.03  (Picoware)\n")
        self._console.output("-----------------------\n")
        self._console.output("\n")
        self._console.render()
        return True

    def tick(self, max_time_ms):
        """Advance the interpreter and return the native three-item status."""
        if self._interpreter is None:
            message = str(self._error or "Program not started")
            return (_STATUS_ERROR, message, 0)
        try:
            state = self._interpreter.tick(
                max_statements=0,
                max_time_ms=max(0, int(max_time_ms)),
            )
        except Exception as error:
            self._error = error
            return (_STATUS_ERROR, str(error), 0)

        status = {
            "running": _STATUS_RUNNING,
            "ended": _STATUS_ENDED,
            "stopped": _STATUS_STOPPED,
            "input": _STATUS_INPUT,
            "error": _STATUS_ERROR,
        }.get(state.status, _STATUS_ERROR)
        return (status, state.message, state.line)

    def feed_char(self, char):
        """Feed a character to INPUT, INPUT$, or INKEY$."""
        if self._interpreter is not None:
            self._interpreter.feed_char(str(char)[:1])

    def render(self, force):
        """Render the console or present the program framebuffer."""
        del force
        if self._interpreter is not None:
            self._console.set_input_active(self._interpreter.is_input_pending())
        if self.has_graphics:
            self._gfx.present()
        else:
            self._console.render()

    def set_footer(self, text):
        """Set the console footer."""
        self._console.footer = str(text)
        self._console.dirty = True

    def console_output(self, text):
        """Append text to the MMBasic console."""
        self._console.output(str(text))
