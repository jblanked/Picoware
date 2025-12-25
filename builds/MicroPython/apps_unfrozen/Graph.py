# translated from https://github.com/lazerduck/PicoCalc_Dashboard/blob/main/graph/graph.py
# graph.py - Simple Graphing Calculator for PicoCalc
# Enter y=f(x) at the bottom, graph is drawn above

SCREEN_WIDTH = 320
SCREEN_HEIGHT = 320
GRAPH_HEIGHT = 280
INPUT_HEIGHT = 40

# Graph area: x in [-10, 10], y in [-10, 10] (default)
XMIN, XMAX = -10, 10
YMIN, YMAX = -10, 10

# Parametric mode t range
TMIN, TMAX = -10, 10


# Map x in [-10,10] to pixel in [0,319]
def x_to_px(x):
    return int((x - XMIN) / (XMAX - XMIN) * (SCREEN_WIDTH - 1))


def px_to_x(px):
    return XMIN + px * (XMAX - XMIN) / (SCREEN_WIDTH - 1)


def y_to_py(y):
    # y=YMAX at top, y=YMIN at bottom
    return int((YMAX - y) / (YMAX - YMIN) * (GRAPH_HEIGHT - 1))


def py_to_y(py):
    return YMAX - py * (YMAX - YMIN) / (GRAPH_HEIGHT - 1)


def draw_axes(fb):
    from picoware.system.vector import Vector
    from picoware.system.colors import TFT_BLUE

    # Draw axes
    # Y axis
    x0 = x_to_px(0)
    fb.fill_rectangle(Vector(x0, 0), Vector(1, GRAPH_HEIGHT), TFT_BLUE)
    # X axis
    y0 = y_to_py(0)
    fb.fill_rectangle(Vector(0, y0), Vector(SCREEN_WIDTH, 1), TFT_BLUE)

    # Draw border
    fb.rect(Vector(0, 0), Vector(SCREEN_WIDTH, GRAPH_HEIGHT), TFT_BLUE)


def draw_input_line(fb, expr, error=None, mode="normal", expr2=None):
    from picoware.system.vector import Vector
    from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_RED

    # Clear input area
    fb.fill_rectangle(
        Vector(0, GRAPH_HEIGHT), Vector(SCREEN_WIDTH, INPUT_HEIGHT), TFT_BLACK
    )
    if mode == "param":
        fb.text(Vector(4, GRAPH_HEIGHT + 4), "x(t)=" + (expr or ""), TFT_WHITE)
        if expr2 is not None:
            fb.text(Vector(4, GRAPH_HEIGHT + 16), "y(t)=" + expr2, TFT_WHITE)
    else:
        fb.text(Vector(4, GRAPH_HEIGHT + 4), "y = " + expr, TFT_WHITE)
    if error:
        fb.text(Vector(200, GRAPH_HEIGHT + 4), error, TFT_RED)


def __exp_list() -> list[tuple[str, object]]:
    import math

    return [
        ("abs", abs),
        ("min", min),
        ("max", max),
        ("pow", pow),
        ("round", round),
        ("int", int),
        ("float", float),
        ("sin", math.sin),
        ("cos", math.cos),
        ("tan", math.tan),
        ("asin", math.asin),
        ("acos", math.acos),
        ("atan", math.atan),
        ("atan2", math.atan2),
        ("log", math.log),
        ("log10", math.log10),
        ("exp", math.exp),
        ("sqrt", math.sqrt),
        ("pi", math.pi),
        ("e", math.e),
        ("floor", math.floor),
        ("ceil", math.ceil),
        ("sinh", math.sinh),
        ("cosh", math.cosh),
        ("tanh", math.tanh),
        ("degrees", math.degrees),
        ("radians", math.radians),
        ("math", math),
    ]


def __param_exp_list() -> list[tuple[str, object]]:
    import math

    return [
        ("abs", abs),
        ("min", min),
        ("max", max),
        ("pow", pow),
        ("round", round),
        ("int", int),
        ("float", float),
        ("sin", math.sin),
        ("cos", math.cos),
        ("tan", math.tan),
        ("asin", math.asin),
        ("acos", math.acos),
        ("atan", math.atan),
        ("atan2", math.atan2),
        ("log", math.log),
        ("log10", math.log10),
        ("exp", math.exp),
        ("sqrt", math.sqrt),
        ("pi", math.pi),
        ("e", math.e),
        ("floor", math.floor),
        ("ceil", math.ceil),
        ("sinh", math.sinh),
        ("cosh", math.cosh),
        ("tanh", math.tanh),
        ("degrees", math.degrees),
        ("radians", math.radians),
        ("math", math),
    ]


def graph_equation(fb, expr):
    import math
    from picoware.system.vector import Vector
    from picoware.system.colors import TFT_BLACK, TFT_GREEN

    fb.fill_screen(TFT_BLACK)
    draw_axes(fb)
    # Try to compile the expression
    try:
        code = compile(expr, "<expr>", "eval")
    except Exception as e:
        draw_input_line(fb, expr, f"Syntax Error: {e}")
        fb.swap()
        return
    # Draw graph pixel by pixel
    points = []
    vec_pixl = Vector(0, 0)
    exp_list = __exp_list()
    for px in range(SCREEN_WIDTH):
        x = px_to_x(px)
        try:
            # Provide a safe eval environment with math functions and common built-ins
            env = {"x": x}
            for k, v in exp_list:
                env[k] = v
            y = eval(code, env)
        except Exception:
            continue
        if not isinstance(y, (int, float)) or math.isnan(y) or math.isinf(y):
            continue
        py = y_to_py(y)
        if 0 <= py < GRAPH_HEIGHT:
            points.append((px, py))
        # Draw in batches for animation
        if px % 16 == 0:
            for ppx, ppy in points:
                vec_pixl.x = ppx
                vec_pixl.y = ppy
                fb.pixel(vec_pixl, TFT_GREEN)
            fb.swap()
            points = []
    # Draw any remaining points
    for ppx, ppy in points:
        vec_pixl.x = ppx
        vec_pixl.y = ppy
        fb.pixel(vec_pixl, TFT_GREEN)
    fb.swap()


def graph_parametric(fb, expr_x, expr_y):
    """
    Graph parametric equations x(t), y(t)
    """
    import math
    from picoware.system.vector import Vector
    from picoware.system.colors import TFT_BLACK, TFT_GREEN

    fb.fill_screen(TFT_BLACK)
    draw_axes(fb)
    # Try to compile the expressions
    try:
        code_x = compile(expr_x, "<expr_x>", "eval")
        code_y = compile(expr_y, "<expr_y>", "eval")
    except Exception as e:
        draw_input_line(fb, expr_x, f"Syntax Error: {e}", mode="param", expr2=expr_y)
        fb.swap()
        return
    points = []
    N = SCREEN_WIDTH  # Number of steps
    vec_pixl = Vector(0, 0)
    exp_list = __param_exp_list()
    for i in range(N):
        t = TMIN + (TMAX - TMIN) * i / (N - 1)
        try:
            env = {"t": t}
            for k, v in exp_list:
                env[k] = v
            x = eval(code_x, env)
            y = eval(code_y, env)
        except Exception:
            continue
        if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
            continue
        if math.isnan(x) or math.isinf(x) or math.isnan(y) or math.isinf(y):
            continue
        px = x_to_px(x)
        py = y_to_py(y)
        if 0 <= px < SCREEN_WIDTH and 0 <= py < GRAPH_HEIGHT:
            points.append((px, py))
        # Draw in batches for animation
        if i % 16 == 0:
            for ppx, ppy in points:
                vec_pixl.x = ppx
                vec_pixl.y = ppy
                fb.pixel(vec_pixl, TFT_GREEN)
            fb.swap()
            points = []
    for ppx, ppy in points:
        vec_pixl.x = ppx
        vec_pixl.y = ppy
        fb.pixel(vec_pixl, TFT_GREEN)
    fb.swap()


mode = ""  # 'normal' or 'param'
expr = ""
expr2 = ""  # default y(t) for parametric
input_buffer = None
input_buffer2 = None
cursor = 0
cursor2 = 0


def start(view_manager) -> bool:
    """Start the app"""
    global mode, expr, expr2, input_buffer, input_buffer2, cursor, cursor2
    mode = "normal"  # 'normal' or 'param'
    expr = "sin(x)*cos(x/2) + exp(-x**2/10)"
    expr2 = "sin(t)"  # default y(t) for parametric
    input_buffer = list(expr)
    input_buffer2 = list(expr2)
    cursor = len(input_buffer)
    cursor2 = len(input_buffer2)
    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_CENTER,
        BUTTON_BACKSPACE,
        BUTTON_M,
        BUTTON_NONE,
    )
    from picoware.system.colors import TFT_BLACK, TFT_WHITE
    from picoware.system.vector import Vector

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()

    fb = view_manager.draw

    global mode, input_buffer, input_buffer2, cursor, cursor2

    fb.fill_screen(TFT_BLACK)

    draw_axes(fb)
    if mode == "param":
        draw_input_line(
            fb, "".join(input_buffer), mode="param", expr2="".join(input_buffer2)
        )
    else:
        draw_input_line(fb, "".join(input_buffer))

    fb.swap()

    # Input loop for editing
    editing = True
    editing_y = False  # For parametric: editing y(t)
    while editing:
        button = inp.button
        if button != BUTTON_NONE:
            key = button
            if key == BUTTON_RIGHT:  # Right arrow
                inp.reset()
                if mode == "param" and editing_y:
                    if cursor2 < len(input_buffer2):
                        cursor2 += 1
                else:
                    if cursor < len(input_buffer):
                        cursor += 1
            elif key == BUTTON_LEFT:  # Left arrow
                inp.reset()
                if mode == "param" and editing_y:
                    if cursor2 > 0:
                        cursor2 -= 1
                else:
                    if cursor > 0:
                        cursor -= 1
            elif key == BUTTON_CENTER:  # Enter key
                inp.reset()
                if mode == "param" and not editing_y:
                    editing_y = True
                    continue
                editing = False
            elif key == BUTTON_BACKSPACE:  # Backspace
                inp.reset()
                if mode == "param" and editing_y:
                    if cursor2 > 0:
                        input_buffer2.pop(cursor2 - 1)
                        cursor2 -= 1
                else:
                    if cursor > 0:
                        input_buffer.pop(cursor - 1)
                        cursor -= 1
            elif key == 3:  # Ctrl+C (clear input)
                inp.reset()
                if mode == "param" and editing_y:
                    input_buffer2 = []
                    cursor2 = 0
                else:
                    input_buffer = []
                    cursor = 0
            elif key == BUTTON_BACK:
                inp.reset()
                view_manager.back()
                return
            elif key == BUTTON_M:  # Toggle mode
                inp.reset()
                if mode == "normal":
                    mode = "param"
                    editing_y = False
                    input_buffer = list("cos(2*t)*(1+0.5*sin(5*t))")
                    input_buffer2 = list("sin(2*t)*(1+0.5*sin(5*t))")
                    cursor = len(input_buffer)
                    cursor2 = len(input_buffer2)
                else:
                    mode = "normal"
                    input_buffer = list(expr)
                    cursor = len(input_buffer)
            elif inp.button_to_char(key) != "":
                inp.reset()
                _converted_char = inp.button_to_char(key)
                if mode == "param" and editing_y:
                    input_buffer2.insert(cursor2, _converted_char)
                    cursor2 += 1
                else:
                    input_buffer.insert(cursor, _converted_char)
                    cursor += 1
        # Draw cursor
        if mode == "param":
            draw_input_line(
                fb, "".join(input_buffer), mode="param", expr2="".join(input_buffer2)
            )
            if editing_y:
                # Cursor for y(t) on second line
                cursor_x = 4 + 6 * len("y(t)=" + "".join(input_buffer2[:cursor2]))
                cursor_y = GRAPH_HEIGHT + 16
            else:
                # Cursor for x(t) on first line
                cursor_x = 4 + 6 * len("x(t)=" + "".join(input_buffer[:cursor]))
                cursor_y = GRAPH_HEIGHT + 4
            fb.fill_rectangle(cursor_x, cursor_y, 6, 8, TFT_WHITE)
        else:
            draw_input_line(fb, "".join(input_buffer))
            cursor_x = 4 + 6 * len("y = " + "".join(input_buffer[:cursor]))
            fb.fill_rectangle(
                Vector(cursor_x, GRAPH_HEIGHT + 4), Vector(6, 8), TFT_WHITE
            )
        fb.swap()
    # Graph the equation
    if mode == "param":
        graph_parametric(fb, "".join(input_buffer), "".join(input_buffer2))
    else:
        graph_equation(fb, "".join(input_buffer))

    # Wait for any key to return to input
    button = inp.button
    while button == BUTTON_NONE:
        button = inp.button
    inp.reset()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global mode, expr, expr2, input_buffer, input_buffer2, cursor, cursor2

    mode = ""  # 'normal' or 'param'
    expr = ""
    expr2 = ""  # default y(t) for parametric
    input_buffer = None
    input_buffer2 = None
    cursor = 0
    cursor2 = 0

    collect()
