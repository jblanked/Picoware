from picoware.system.vector import Vector
from picoware.system.colors import (
    TFT_ORANGE,
    TFT_DARKGREY,
    TFT_LIGHTGREY,
    TFT_WHITE,
    TFT_BLACK,
    TFT_BLUE,
    TFT_YELLOW,
    TFT_CYAN,
)
from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_CENTER,
    #
    BUTTON_0,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    BUTTON_7,
    BUTTON_8,
    BUTTON_9,
    #
    BUTTON_PERIOD,
    BUTTON_SLASH,
    BUTTON_BACKSLASH,
    BUTTON_ASTERISK,
    BUTTON_MINUS,
    BUTTON_PLUS,
    BUTTON_EQUAL,
    #
    BUTTON_BACKSPACE,
    BUTTON_SPACE,
    BUTTON_ESCAPE,
)

# Calculator state
display_text = "0"
current_value = 0
stored_value = 0
current_operation = None
new_number = True
buttons = []
selected_button_index = 0
pos_vec = None
size_vec = None
font_width = 0
font_height = 0
len_buttons = 0


class CalcButton:
    """Represents a calculator button"""

    __slots__ = ("text", "pos", "size", "color", "text_color", "action", "text_pos")

    def __init__(self, text, pos, size, color, text_color, action, text_pos) -> None:
        self.text = text
        self.pos = pos
        self.size = size
        self.color = color
        self.text_color = text_color
        self.action = action
        self.text_pos = text_pos


def setup_buttons(screen_width, screen_height):
    """Setup calculator button layout (iPhone style)"""
    global buttons
    buttons = []

    # Button dimensions
    button_width = screen_width // 4 - 8
    button_height = (screen_height - 100) // 5 - 8
    padding = 6

    # Top row starts after display
    start_y = 100

    # Row 1: C, +/-, %, ÷
    row1_y = start_y
    buttons.append(
        CalcButton(
            "C",
            Vector(padding, row1_y),
            Vector(button_width, button_height),
            TFT_LIGHTGREY,
            TFT_BLACK,
            "clear",
            Vector(
                padding + (button_width - (font_width * 1)) // 2,
                row1_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            "+/-",
            Vector(button_width + padding * 2, row1_y),
            Vector(button_width, button_height),
            TFT_LIGHTGREY,
            TFT_BLACK,
            "negate",
            Vector(
                button_width + padding * 2 + (button_width - (font_width * 3)) // 2,
                row1_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            "%",
            Vector(button_width * 2 + padding * 3, row1_y),
            Vector(button_width, button_height),
            TFT_LIGHTGREY,
            TFT_BLACK,
            "percent",
            Vector(
                button_width * 2 + padding * 3 + (button_width - (font_width * 1)) // 2,
                row1_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            "/",
            Vector(button_width * 3 + padding * 4, row1_y),
            Vector(button_width, button_height),
            TFT_ORANGE,
            TFT_WHITE,
            "divide",
            Vector(
                button_width * 3 + padding * 4 + (button_width - (font_width * 1)) // 2,
                row1_y + (button_height - font_height) // 2,
            ),
        )
    )

    # Row 2: 7, 8, 9, ×
    row2_y = start_y + button_height + padding
    buttons.append(
        CalcButton(
            "7",
            Vector(padding, row2_y),
            Vector(button_width, button_height),
            TFT_DARKGREY,
            TFT_WHITE,
            "7",
            Vector(
                padding + (button_width - (font_width * 1)) // 2,
                row2_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            "8",
            Vector(button_width + padding * 2, row2_y),
            Vector(button_width, button_height),
            TFT_DARKGREY,
            TFT_WHITE,
            "8",
            Vector(
                button_width + padding * 2 + (button_width - (font_width * 1)) // 2,
                row2_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            "9",
            Vector(button_width * 2 + padding * 3, row2_y),
            Vector(button_width, button_height),
            TFT_DARKGREY,
            TFT_WHITE,
            "9",
            Vector(
                button_width * 2 + padding * 3 + (button_width - (font_width * 1)) // 2,
                row2_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            "*",
            Vector(button_width * 3 + padding * 4, row2_y),
            Vector(button_width, button_height),
            TFT_ORANGE,
            TFT_WHITE,
            "multiply",
            Vector(
                button_width * 3 + padding * 4 + (button_width - (font_width * 1)) // 2,
                row2_y + (button_height - font_height) // 2,
            ),
        )
    )

    # Row 3: 4, 5, 6, -
    row3_y = start_y + (button_height + padding) * 2
    buttons.append(
        CalcButton(
            "4",
            Vector(padding, row3_y),
            Vector(button_width, button_height),
            TFT_DARKGREY,
            TFT_WHITE,
            "4",
            Vector(
                padding + (button_width - (font_width * 1)) // 2,
                row3_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            "5",
            Vector(button_width + padding * 2, row3_y),
            Vector(button_width, button_height),
            TFT_DARKGREY,
            TFT_WHITE,
            "5",
            Vector(
                button_width + padding * 2 + (button_width - (font_width * 1)) // 2,
                row3_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            "6",
            Vector(button_width * 2 + padding * 3, row3_y),
            Vector(button_width, button_height),
            TFT_DARKGREY,
            TFT_WHITE,
            "6",
            Vector(
                button_width * 2 + padding * 3 + (button_width - (font_width * 1)) // 2,
                row3_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            "-",
            Vector(button_width * 3 + padding * 4, row3_y),
            Vector(button_width, button_height),
            TFT_ORANGE,
            TFT_WHITE,
            "subtract",
            Vector(
                button_width * 3 + padding * 4 + (button_width - (font_width * 1)) // 2,
                row3_y + (button_height - font_height) // 2,
            ),
        )
    )

    # Row 4: 1, 2, 3, +
    row4_y = start_y + (button_height + padding) * 3
    buttons.append(
        CalcButton(
            "1",
            Vector(padding, row4_y),
            Vector(button_width, button_height),
            TFT_DARKGREY,
            TFT_WHITE,
            "1",
            Vector(
                padding + (button_width - (font_width * 1)) // 2,
                row4_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            "2",
            Vector(button_width + padding * 2, row4_y),
            Vector(button_width, button_height),
            TFT_DARKGREY,
            TFT_WHITE,
            "2",
            Vector(
                button_width + padding * 2 + (button_width - (font_width * 1)) // 2,
                row4_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            "3",
            Vector(button_width * 2 + padding * 3, row4_y),
            Vector(button_width, button_height),
            TFT_DARKGREY,
            TFT_WHITE,
            "3",
            Vector(
                button_width * 2 + padding * 3 + (button_width - (font_width * 1)) // 2,
                row4_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            "+",
            Vector(button_width * 3 + padding * 4, row4_y),
            Vector(button_width, button_height),
            TFT_ORANGE,
            TFT_WHITE,
            "add",
            Vector(
                button_width * 3 + padding * 4 + (button_width - (font_width * 1)) // 2,
                row4_y + (button_height - font_height) // 2,
            ),
        )
    )

    # Row 5: 0 (wide), ., =
    row5_y = start_y + (button_height + padding) * 4
    buttons.append(
        CalcButton(
            "0",
            Vector(padding, row5_y),
            Vector(button_width * 2 + padding, button_height),
            TFT_DARKGREY,
            TFT_WHITE,
            "0",
            Vector(
                padding + (button_width * 2 + padding - (font_width * 1)) // 2,
                row5_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            ".",
            Vector(button_width * 2 + padding * 3, row5_y),
            Vector(button_width, button_height),
            TFT_DARKGREY,
            TFT_WHITE,
            "decimal",
            Vector(
                button_width * 2 + padding * 3 + (button_width - (font_width * 1)) // 2,
                row5_y + (button_height - font_height) // 2,
            ),
        )
    )
    buttons.append(
        CalcButton(
            "=",
            Vector(button_width * 3 + padding * 4, row5_y),
            Vector(button_width, button_height),
            TFT_ORANGE,
            TFT_WHITE,
            "equals",
            Vector(
                button_width * 3 + padding * 4 + (button_width - (font_width * 1)) // 2,
                row5_y + (button_height - font_height) // 2,
            ),
        )
    )


def draw_display(draw, text):
    """Draw the calculator display"""
    # Display background
    pos_vec.x, pos_vec.y = 0, 0
    size_vec.x, size_vec.y = draw.size.x, 90
    draw.fill_rectangle(pos_vec, size_vec, TFT_BLACK)

    # Limit display length
    display = text[-15:] if len(text) > 15 else text

    text_width = len(display) * font_width
    x_pos = draw.size.x - text_width - 10
    y_pos = 90 - font_height - 10
    pos_vec.x, pos_vec.y = x_pos, y_pos
    draw.text(pos_vec, display, TFT_WHITE)


def draw_button(draw, button: CalcButton, is_selected: bool = False):
    """Draw a calculator button"""
    # Draw button background
    draw.fill_round_rectangle(button.pos, button.size, 10, button.color)

    # Draw selection highlight border if selected
    if is_selected:
        # Draw thick border by drawing multiple rectangles
        for i in range(3):
            pos_vec.x, pos_vec.y = button.pos.x - i, button.pos.y - i
            size_vec.x, size_vec.y = button.size.x + i * 2, button.size.y + i * 2
            draw.rect(
                pos_vec,
                size_vec,
                TFT_BLUE,
            )

    draw.text(button.text_pos, button.text, button.text_color)


def handle_number(digit):
    """Handle number button press"""
    global display_text, current_value, new_number

    if new_number:
        display_text = str(digit)
        new_number = False
    else:
        if len(display_text) < 12:
            if display_text == "0":
                display_text = str(digit)
            else:
                display_text += str(digit)

    current_value = float(display_text)


def handle_operation(op):
    """Handle operation button press"""
    global current_value, stored_value, current_operation, new_number, display_text

    if current_operation and not new_number:
        calculate()

    stored_value = current_value
    current_operation = op
    new_number = True


def calculate():
    """Perform the calculation"""
    global current_value, stored_value, current_operation, display_text

    if current_operation == "add":
        current_value = stored_value + current_value
    elif current_operation == "subtract":
        current_value = stored_value - current_value
    elif current_operation == "multiply":
        current_value = stored_value * current_value
    elif current_operation == "divide":
        if current_value != 0:
            current_value = stored_value / current_value
        else:
            display_text = "Error"
            current_value = 0
            return

    # Format the result
    if current_value == int(current_value):
        display_text = str(int(current_value))
    else:
        display_text = str(round(current_value, 8))
        # Remove trailing zeros
        if "." in display_text:
            display_text = display_text.rstrip("0").rstrip(".")


def handle_button_action(action):
    """Handle button actions"""
    global display_text, current_value, stored_value, current_operation, new_number

    if action.isdigit():
        handle_number(int(action))
    elif action == "decimal":
        if new_number:
            display_text = "0."
            new_number = False
        elif "." not in display_text:
            display_text += "."
    elif action == "clear":
        display_text = "0"
        current_value = 0
        stored_value = 0
        current_operation = None
        new_number = True
    elif action == "negate":
        current_value = -current_value
        display_text = str(current_value)
        if current_value == int(current_value):
            display_text = str(int(current_value))
    elif action == "percent":
        current_value = current_value / 100
        display_text = str(current_value)
    elif action in ["add", "subtract", "multiply", "divide"]:
        handle_operation(action)
    elif action == "equals":
        if current_operation:
            calculate()
            current_operation = None
            new_number = True


def find_button_by_action(action: str):
    """Find button index by action"""
    btn: CalcButton
    for i, btn in enumerate(buttons):
        if btn.action == action:
            return i
    return None


def start(view_manager) -> bool:
    """Start the app"""
    global display_text, current_value, stored_value, current_operation, new_number, selected_button_index, pos_vec, size_vec, font_width, font_height, len_buttons

    # Reset calculator state
    display_text = "0"
    current_value = 0
    stored_value = 0
    current_operation = None
    new_number = True
    selected_button_index = 0
    pos_vec = Vector(0, 0)
    size_vec = Vector(0, 0)

    # Draw initial UI
    draw = view_manager.draw
    draw.clear()

    font_width = draw.font_size.x
    font_height = draw.font_size.y

    # Setup buttons
    setup_buttons(draw.size.x, draw.size.y)

    len_buttons = len(buttons)

    # Show control guide
    y_pos = 20
    line_height = draw.font_size.y + 4

    draw.text(Vector(10, y_pos), "CONTROLS:", TFT_YELLOW)
    y_pos += line_height
    draw.text(Vector(10, y_pos), "Arrows: Navigate", TFT_CYAN)
    y_pos += line_height
    draw.text(Vector(10, y_pos), "Center/Space: Select", TFT_CYAN)
    y_pos += line_height
    draw.text(Vector(10, y_pos), "0-9,+,-,*,/,.: Direct", TFT_CYAN)
    y_pos += line_height
    draw.text(Vector(10, y_pos), "Backspace: Delete", TFT_CYAN)
    y_pos += line_height
    draw.text(Vector(10, y_pos), "Esc: Clear All", TFT_CYAN)

    draw.swap()
    inp = view_manager.input_manager
    button = inp.button
    while button == -1:
        button = inp.button

    inp.reset()

    # Now draw calculator UI
    draw.clear()
    draw_display(draw, display_text)

    for i, button in enumerate(buttons):
        draw_button(draw, button, i == selected_button_index)

    draw.swap()

    return True


def run(view_manager) -> None:
    """Run the app"""
    global selected_button_index

    draw = view_manager.draw
    inp = view_manager.input_manager
    button = inp.button

    if button == -1:
        return

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    needs_redraw = False

    # Handle button navigation
    if button == BUTTON_RIGHT:
        old_index = selected_button_index
        selected_button_index = (selected_button_index + 1) % len_buttons
        if old_index != selected_button_index:
            needs_redraw = True
        inp.reset()
    elif button == BUTTON_LEFT:
        old_index = selected_button_index
        selected_button_index = (selected_button_index - 1) % len_buttons
        if old_index != selected_button_index:
            needs_redraw = True
        inp.reset()
    elif button == BUTTON_DOWN:
        old_index = selected_button_index
        # Move down one row (4 buttons per row for most rows)
        if selected_button_index < 16:  # Not on bottom row
            selected_button_index = min(selected_button_index + 4, len_buttons - 1)
        if old_index != selected_button_index:
            needs_redraw = True
        inp.reset()
    elif button == BUTTON_UP:
        old_index = selected_button_index
        # Move up one row
        if selected_button_index >= 4:
            selected_button_index = max(selected_button_index - 4, 0)
        if old_index != selected_button_index:
            needs_redraw = True
        inp.reset()
    elif button == BUTTON_CENTER:
        # Activate the selected button
        selected_btn = buttons[selected_button_index]
        handle_button_action(selected_btn.action)
        needs_redraw = True
        inp.reset()
    # Handle direct number input
    elif button == BUTTON_0:
        handle_number(0)
        btn_idx = find_button_by_action("0")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button == BUTTON_1:
        handle_number(1)
        btn_idx = find_button_by_action("1")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button == BUTTON_2:
        handle_number(2)
        btn_idx = find_button_by_action("2")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button == BUTTON_3:
        handle_number(3)
        btn_idx = find_button_by_action("3")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button == BUTTON_4:
        handle_number(4)
        btn_idx = find_button_by_action("4")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button == BUTTON_5:
        handle_number(5)
        btn_idx = find_button_by_action("5")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button == BUTTON_6:
        handle_number(6)
        btn_idx = find_button_by_action("6")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button == BUTTON_7:
        handle_number(7)
        btn_idx = find_button_by_action("7")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button == BUTTON_8:
        handle_number(8)
        btn_idx = find_button_by_action("8")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button == BUTTON_9:
        handle_number(9)
        btn_idx = find_button_by_action("9")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    # Handle operator input
    elif button == BUTTON_PERIOD:
        handle_button_action("decimal")
        btn_idx = find_button_by_action("decimal")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button in (BUTTON_SLASH, BUTTON_BACKSLASH):
        handle_button_action("divide")
        btn_idx = find_button_by_action("divide")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button == BUTTON_ASTERISK:
        handle_button_action("multiply")
        btn_idx = find_button_by_action("multiply")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button == BUTTON_MINUS:
        handle_button_action("subtract")
        btn_idx = find_button_by_action("subtract")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button == BUTTON_PLUS:
        handle_button_action("add")
        btn_idx = find_button_by_action("add")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button in (BUTTON_EQUAL, BUTTON_SPACE):
        handle_button_action("equals")
        btn_idx = find_button_by_action("equals")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    elif button == BUTTON_ESCAPE:
        handle_button_action("clear")
        btn_idx = find_button_by_action("clear")
        if btn_idx is not None:
            selected_button_index = btn_idx
        needs_redraw = True
        inp.reset()
    # Handle backspace (delete last character)
    elif button == BUTTON_BACKSPACE:
        global display_text, current_value, new_number
        if not new_number and len(display_text) > 0:
            if len(display_text) == 1 or display_text == "Error":
                display_text = "0"
                current_value = 0
                new_number = True
            else:
                display_text = display_text[:-1]
                # Handle case where we delete the last char after decimal point
                if display_text == "0.":
                    display_text = "0"
                    current_value = 0
                    new_number = True
                elif display_text == "-" or display_text == "-.":
                    display_text = "0"
                    current_value = 0
                    new_number = True
                else:
                    try:
                        current_value = float(display_text)
                    except ValueError:
                        display_text = "0"
                        current_value = 0
                        new_number = True
        needs_redraw = True
        inp.reset()

    # Redraw if needed
    if needs_redraw:
        draw.clear()
        draw_display(draw, display_text)

        for i, btn in enumerate(buttons):
            draw_button(draw, btn, i == selected_button_index)

        draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global buttons, selected_button_index, display_text, current_value, stored_value, current_operation, new_number, pos_vec, size_vec, font_width, font_height, len_buttons

    buttons = []
    selected_button_index = 0
    display_text = "0"
    current_value = 0
    stored_value = 0
    current_operation = None
    new_number = True
    pos_vec = None
    size_vec = None
    font_width = 0
    font_height = 0
    len_buttons = 0

    collect()
