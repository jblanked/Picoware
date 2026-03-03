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

    draw = view_manager.draw
    fg = view_manager.foreground_color
    height = draw.size.y
    bg = view_manager.background_color
    size = draw.size

    draw.fill_screen(bg)

    msg = f"Listening on GPIO{_uart.rx_pin}"
    display_x = int((size.x - len(msg) * draw.font_size.x) // 2)
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
            top + int(top // 2),
            height - int(top + (top // 2)),
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
        _loading = Loading(view_manager.draw)
        _loading.set_text(text)
    else:
        _loading.animate()


def __set_kb(view_manager, title: str) -> None:
    """Set up the keyboard"""
    kb = view_manager.keyboard
    kb.reset()
    kb.response = ""
    kb.callback = __callback
    kb.title = title
    kb.run(force=True)


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.uart import UART
    from picoware.system.boards import (
        BOARD_WAVESHARE_1_28_RP2350,
        BOARD_WAVESHARE_1_43_RP2350,
        BOARD_WAVESHARE_3_49_RP2350,
    )

    global _textbox, _uart, state, _loading

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

    view_manager.freq(True)  # set to lower frequency
    is_pico_calc = False

    board_id = view_manager.board_id
    if board_id == BOARD_WAVESHARE_1_28_RP2350:
        _uart = UART(uart_id=0, tx_pin=16, rx_pin=17)
    elif board_id in (BOARD_WAVESHARE_1_43_RP2350, BOARD_WAVESHARE_3_49_RP2350):
        _uart = UART(uart_id=1, tx_pin=4, rx_pin=5)
    else:  # PicoCalc
        _uart = UART(uart_id=0, tx_pin=0, rx_pin=1)
        is_pico_calc = True

    # first show info screen about connection
    d = view_manager.draw
    fg = view_manager.foreground_color
    d.erase()
    d._text(0, 0, "To connect to the device, use the following settings:", fg)
    d._text(0, 16, "Baudrate: 115200", fg)
    if not is_pico_calc:
        d._text(0, 32, f"TX Pin: GP{_uart.tx_pin if _uart else 'N/A'}", fg)
        d._text(0, 48, f"RX Pin: GP{_uart.rx_pin if _uart else 'N/A'}", fg)
    else:
        d._text(0, 32, "TX Pin: UART0_TX (GP0)", fg)
        d._text(0, 48, "RX Pin: UART0_RX (GP1)", fg)
    d._text(0, 64, "Press the any button to continue...", fg)
    d.swap()
    inp = view_manager.input_manager
    while True:
        but = inp.button
        if but != -1:
            inp.reset()
            break

    __set_kb(view_manager, "Start the conversation")

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER

    inp = view_manager.input_manager
    button = inp.button

    global state, _loading

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return
    if button == BUTTON_CENTER and state == STATE_VIEWING:
        inp.reset()
        __set_kb(view_manager, "Send a message")
        state = STATE_TYPING

    if state == STATE_TYPING:
        kb = view_manager.keyboard
        if not kb.run():
            view_manager.back()
            return
    elif state == STATE_SENDING:
        if not _uart.is_sending:
            state = STATE_VIEWING
            kb = view_manager.keyboard
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

    view_manager.keyboard.reset()

    view_manager.freq()  # set back to higher frequency

    # cleanup
    collect()
