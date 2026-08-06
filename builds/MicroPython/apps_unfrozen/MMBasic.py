"""
MMBasic - MBASIC 5.21 interpreter for Picoware.

Runs the `mmbasic` package (lexer/parser/interpreter) on the device, using
the Picoware screen for PRINT output and the buttons for INPUT/INKEY$.

To run your own program, drop a text file at /picoware/mmbasic.bas on the SD
card; the app loads it instead of the built-in demo below.
"""
from picoware.system.buttons import (
    BUTTON_NONE,
    BUTTON_BACK,
    BUTTON_ESCAPE,
    BUTTON_ENTER,
    BUTTON_CENTER,
    BUTTON_BACKSPACE,
)

PROGRAM = """\
10 CLS
20 PRINT "=== MBASIC 5.21 on Picoware ==="
30 PRINT
40 INPUT "Your name"; N$
50 PRINT "Hello "; N$; "!"
60 PRINT
70 FOR I = 1 TO 5
80   PRINT "Square of"; I; "is"; I * I
90 NEXT I
100 GOSUB 300
110 PRINT
120 PRINT "Goodbye"; TAB(14); "END"
130 END
300 PRINT "Random:"; RND(1); RND(1); RND(1)
310 RETURN
"""

_app = None


def _load_program(view_manager):
    """Load /picoware/mmbasic.bas from the SD card, else the demo."""
    try:
        storage = view_manager.storage
        if storage is not None and storage.exists("picoware/mmbasic.bas"):
            data = storage.read("picoware/mmbasic.bas")
            if data and data.strip():
                return data
    except Exception:
        pass
    return PROGRAM


def start(view_manager) -> bool:
    """Start the app: build the console, parse and run the program."""
    global _app

    try:
        from mmbasic import MMBasicEngine, PicowareConsole, PicowareGraphics

        console = PicowareConsole(view_manager)
        console.footer = "BACK=exit"

        # All MMBasic graphics (Pixel/Line/Box/Circle/Polygon/Turtle/CLS ...)
        # are rendered through picoware.gui.draw (double-buffered).
        gfx = PicowareGraphics(view_manager.draw, view_manager)

        source = _load_program(view_manager)

        engine = MMBasicEngine(console=console, gfx=gfx)
        engine.load(source)
        engine.interpreter.start()

        console.output("MBASIC 5.21  (Picoware)")
        console.output("-----------------------")
        console.output("")
        console.render()

        _app = {
            "console": console,
            "engine": engine,
            "state": None,
        }
        view_manager.log("MMBasic started")
        return True

    except Exception as e:
        view_manager.log("MMBasic failed to start: %r" % (e,), 2)
        return False


def _feed_button(view_manager, button):
    """Route a button press into the interpreter as input."""
    engine = _app["engine"]
    interp = engine.interpreter

    if button == BUTTON_BACKSPACE:
        interp.feed_char("\b")
        return
    if button in (BUTTON_ENTER, BUTTON_CENTER):
        interp.feed_char("\n")
        return
    char = view_manager.input_manager.button_to_char(button)
    if char:
        interp.feed_char(char)


def run(view_manager) -> None:
    """Poll buttons, tick the interpreter, redraw the console."""
    global _app
    if not _app:
        return

    input_manager = view_manager.input_manager
    button = input_manager.button

    if button != -1 and button != BUTTON_NONE:
        input_manager.reset()
        if button in (BUTTON_BACK, BUTTON_ESCAPE):
            stop(view_manager)
            view_manager.back()
            return
        _feed_button(view_manager, button)

    engine = _app["engine"]
    interp = engine.interpreter
    console = _app["console"]

    state = interp.tick(120)
    _app["state"] = state

    if state.status == "error":
        console.output("")
        console.output("? " + state.message + " (line " + str(state.line) + ")")
        console.footer = "Back to exit"
    elif state.status == "ended":
        console.footer = "Program ended - back to exit"
    elif state.status == "stopped":
        console.footer = "Break - back to exit"
    else:
        console.set_input_active(interp.is_input_pending())

    # FRAMEBUFFER programs own the display until FRAMEBUFFER CLOSE. Rendering
    # the text console here would immediately erase their presented frame.
    graphics_active = bool(getattr(engine.gfx, "display_active", False))
    if state.status == "error" or not graphics_active:
        console.render()


def stop(view_manager) -> None:
    """Clean up app resources."""
    global _app
    if _app:
        _app["console"] = None
        _app["engine"] = None
        _app = None

    from gc import collect

    collect()
