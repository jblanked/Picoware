from micropython import const

# states
STATE_VIEWING = const(0)
STATE_TYPING = const(1)
STATE_SENDING = const(2)

# global objects
_textbox = None
_uart = None
_loading = None
state = STATE_TYPING
message = ""


def __box_start(view_manager) -> None:
    """Start the textbox for server output"""
    from picoware.gui.textbox import TextBox
    from picoware.system.vector import Vector

    global _textbox

    draw = view_manager.get_draw()
    fg = view_manager.get_foreground_color()
    height = draw.size.y
    bg = view_manager.get_background_color()
    size = draw.size

    draw.fill_screen(bg)

    msg = f"Listening on GPIO{_uart.rx_pin}"
    display_x = (size.x - len(msg) * draw.font_size.x) // 2
    draw.text(
        Vector(display_x, int(size.y * 0.0625)),
        msg,
        fg,
    )
    draw.swap()

    top = int(height * 0.0625)

    if _textbox is None:
        _textbox = TextBox(
            draw,
            top + (top // 2),
            height - (top + (top // 2)),
            fg,
            bg,
        )

        _textbox.set_text(message)
    else:
        _textbox.current_text += message
        _textbox.refresh()


def __callback(result: str) -> None:
    """Callback for keyboard input"""
    global state, message
    message = "\nYou: " + result + "\n"
    state = STATE_SENDING
    _uart.println(result)


def __loading_run(view_manager, text: str = "Sending...") -> None:
    """Start loading animation"""
    from picoware.gui.loading import Loading

    global _loading

    if not _loading:
        _loading = Loading(view_manager.get_draw())
        _loading.set_text(text)
    else:
        _loading.animate()


def __set_kb(view_manager, title: str) -> None:
    """Set up the keyboard"""
    kb = view_manager.get_keyboard()
    kb.set_response("")
    kb.set_save_callback(__callback)
    kb.title = title
    kb.run(force=True)
    kb.run(force=True)


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.uart import UART
    from picoware.system.boards import (
        BOARD_WAVESHARE_1_28_RP2350,
    )

    global _textbox, _uart

    if _textbox is not None:
        del _textbox
        _textbox = None
    if _uart is not None:
        del _uart
        _uart = None

    board_id = view_manager.board_id
    if board_id == BOARD_WAVESHARE_1_28_RP2350:
        _uart = UART(uart_id=0, tx_pin=16, rx_pin=17)
    else:  # PicoCalc and Waveshare 1.43
        _uart = UART(uart_id=1, tx_pin=4, rx_pin=5)

    __set_kb(view_manager, "Start the conversation")

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER

    inp = view_manager.get_input_manager()
    button = inp.button

    global state, _loading

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
    if button == BUTTON_CENTER and state == STATE_VIEWING:
        inp.reset()
        __set_kb(view_manager, "Send a message")
        global state
        state = STATE_TYPING

    if state == STATE_TYPING:
        kb = view_manager.get_keyboard()
        kb.run()
    elif state == STATE_SENDING:
        if not _uart.is_sending:
            state = STATE_VIEWING
            kb = view_manager.get_keyboard()
            kb.reset()
            del _loading
            _loading = None
            __box_start(view_manager)
        else:
            __loading_run(view_manager)
    elif state == STATE_VIEWING:
        if _uart.has_data:
            _textbox.current_text += f"Friend: {_uart.read_line()}\n"
            _textbox.refresh()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _textbox, _uart, _loading, state, message

    if _textbox is not None:
        del _textbox
        _textbox = None
    if _uart is not None:
        del _uart
        _uart = None
    if _loading is not None:
        del _loading
        _loading = None
    state = STATE_TYPING
    message = ""

    collect()
