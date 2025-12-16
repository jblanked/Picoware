from micropython import const

# view constants
VIEW_MAIN_MENU = const(0)  # Main menu view
VIEW_SENDING_MESSAGE = const(1)  # Sending message view
VIEW_CHANNEL = const(2)  # viewing the channel messages/feed
VIEW_KEYBOARD_TOKEN = const(3)  # viewing the keyboard to enter bot token
VIEW_KEYBOARD_CHAT_ID = const(4)  # viewing the keyboard to enter chat ID

# menu constatnts
MENU_ITEM_SEND_MESSAGE = const(0)  # Menu item to send a message
MENU_ITEM_VIEW_CHANNEL = const(1)  # Menu item to view channel messages/feed
MENU_ITEM_SET_BOT_TOKEN = const(2)  # Menu item to set bot token
MENU_ITEM_SET_CHAT_ID = const(3)  # Menu item to set chat ID

# viewing/feed constants
CHANNEL_FETCHING = const(0)  # Fetching messages
CHANNEL_DISPLAYING = const(1)  # Displaying messages

# sending constants
SENDING_WAITING = const(-1)  # Waiting to send
SENDING_KEYBOARD = const(0)  # Keyboard for message input
SENDING_SENDING = const(1)  # Sending message

# bot token/chat ID constants
KEYBOARD_WAITING = const(-1)  # Waiting for keyboard input
KEYBOARD_ENTERING = const(0)  # Entering via keyboard

# globals
current_view = VIEW_MAIN_MENU
menu_index = MENU_ITEM_SEND_MESSAGE
channel_index = CHANNEL_FETCHING
sending_index = SENDING_WAITING
keyboard_index = KEYBOARD_WAITING

_http = None
_menu = None
_loading = None
_textbox = None
fetch_started = False
_message_to_send = ""


def __alert(view_manager, message: str, back: bool = True) -> None:
    """Show an alert"""

    from picoware.gui.alert import Alert
    from picoware.system.buttons import BUTTON_BACK

    draw = view_manager.get_draw()
    draw.clear()
    _alert = Alert(
        draw,
        message,
        view_manager.get_foreground_color(),
        view_manager.get_background_color(),
    )
    _alert.draw("Alert")

    # Wait for user to acknowledge
    inp = view_manager.get_input_manager()
    while True:
        button = inp.button
        if button == BUTTON_BACK:
            inp.reset()
            break

    if back:
        view_manager.back()


def __channel_display(view_manager) -> None:
    """Display channel messages from saved file"""
    from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_BACK

    inp = view_manager.get_input_manager()
    button = inp.button
    global _textbox, current_view, channel_index
    if button == BUTTON_UP:
        inp.reset()
        _textbox.scroll_up()
    elif button == BUTTON_DOWN:
        inp.reset()
        _textbox.scroll_down()
    elif button == BUTTON_BACK:
        inp.reset()
        current_view = VIEW_MAIN_MENU
        channel_index = CHANNEL_FETCHING
        _menu_start(view_manager)


def __channel_parse(view_manager) -> bool:
    """Parse channel messages from saved file"""
    storage = view_manager.storage
    messages = storage.read("picoware/telegram/messages.txt")

    if not messages:
        __alert(view_manager, "No messages available..", False)
        return False

    from ujson import loads

    # we have much more ram the flipper zero... so let's parse all at once instead of in chunks
    # if anything we can write/read into PSRAM since I fixed it in the 1.5.6 update
    try:
        data = loads(messages)
    except Exception as e:
        __alert(view_manager, f"Failed to parse messages.\n{e}", False)
        return False

    results = data.get("result", [])
    if not results:
        __alert(view_manager, "No messages found in feed.", False)
        return False
    parsed_text = ""
    for item in results:
        channel_post = item.get("channel_post", {})
        text = channel_post.get("text", "")
        date = channel_post.get("date", 0)
        # check for username
        sender_chat = channel_post.get("sender_chat", {})
        username = sender_chat.get("username", "")

        if username:
            parsed_text += f"@{username} ({date}):\n{text}\n\n"
        else:
            parsed_text += f"(ID: {channel_post.get('chat', {}).get('id', 'N/A')}, Date: {date}):\n{text}\n\n"

    from picoware.gui.textbox import TextBox

    global _textbox

    if _textbox is not None:
        del _textbox
        _textbox = None

    draw = view_manager.get_draw()
    _textbox = TextBox(
        draw,
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
    )

    _textbox.set_text(parsed_text)
    return True


def _http_await(view_manager) -> None:
    """Wait for HTTP to complete and process result"""
    global _http, current_view, channel_index, _loading, sending_index

    if _http is None:
        if _loading is not None:
            del _loading
            _loading = None
        return

    if not _http.is_finished:
        message = (
            "Sending..." if current_view == VIEW_SENDING_MESSAGE else "Fetching..."
        )
        _loading_run(view_manager, message)
        return

    if not _http.is_successful:
        __alert(view_manager, f"HTTP request failed.\n{_http.error}", False)
        current_view = VIEW_MAIN_MENU
        sending_index = SENDING_WAITING
        del _http
        _http = None
        del _loading
        _loading = None
        _menu_start(view_manager)
        return

    if current_view == VIEW_SENDING_MESSAGE:
        __alert(view_manager, "Message sent!", False)
        current_view = VIEW_MAIN_MENU
        sending_index = SENDING_WAITING
        _menu_start(view_manager)
    elif current_view == VIEW_CHANNEL:
        channel_index = CHANNEL_DISPLAYING

        if not __channel_parse(view_manager):
            current_view = VIEW_MAIN_MENU
            channel_index = CHANNEL_FETCHING
            _menu_start(view_manager)

    del _http
    _http = None
    del _loading
    _loading = None


def _keyboard_save(view_manager) -> bool:
    """Keyboard callback function"""
    global _message_to_send
    storage = view_manager.storage
    kb = view_manager.keyboard
    if current_view == VIEW_SENDING_MESSAGE:
        _message_to_send = kb.response
        return True
    return storage.write(
        (
            "picoware/telegram/token.txt"
            if current_view == VIEW_KEYBOARD_TOKEN
            else "picoware/telegram/chat_id.txt"
        ),
        kb.response,
    )


def _keyboard_run(view_manager) -> None:
    """Start the keyboard view"""
    global current_view, sending_index, keyboard_index, _message_to_send

    # Initialize keyboard for sending message
    if current_view == VIEW_SENDING_MESSAGE and sending_index == SENDING_WAITING:
        kb = view_manager.keyboard
        kb.reset()
        kb.title = "Enter Message"
        kb.response = ""
        kb.run(force=True)
        kb.run(force=True)
        sending_index = SENDING_KEYBOARD
        return

    # Initialize keyboard for token/chat ID
    if (
        current_view in (VIEW_KEYBOARD_TOKEN, VIEW_KEYBOARD_CHAT_ID)
        and keyboard_index == KEYBOARD_WAITING
    ):
        storage = view_manager.storage
        kb = view_manager.keyboard
        kb.reset()
        if current_view == VIEW_KEYBOARD_TOKEN:
            kb.title = "Enter Bot Token"
            kb.response = storage.read("picoware/telegram/token.txt")
        elif current_view == VIEW_KEYBOARD_CHAT_ID:
            kb.title = "Enter Chat ID"
            kb.response = storage.read("picoware/telegram/chat_id.txt")
        keyboard_index = KEYBOARD_ENTERING
        kb.run(force=True)
        kb.run(force=True)
        return

    # Run keyboard for sending message
    if current_view == VIEW_SENDING_MESSAGE and sending_index == SENDING_KEYBOARD:
        kb = view_manager.keyboard
        kb.run()

        if kb.is_finished:
            if not _keyboard_save(view_manager):
                __alert(view_manager, "Failed to save message.", False)
                current_view = VIEW_MAIN_MENU
                sending_index = SENDING_WAITING
            else:
                # Start sending the message
                if __telegram_send(view_manager, _message_to_send):
                    sending_index = SENDING_SENDING
                else:
                    current_view = VIEW_MAIN_MENU
                    sending_index = SENDING_WAITING
        return

    # Run keyboard for token/chat ID
    if (
        current_view in (VIEW_KEYBOARD_TOKEN, VIEW_KEYBOARD_CHAT_ID)
        and keyboard_index == KEYBOARD_ENTERING
    ):
        kb = view_manager.keyboard
        kb.run()

        if kb.is_finished:
            if not _keyboard_save(view_manager):
                __alert(view_manager, "Failed to save input.", False)
            else:
                __alert(view_manager, "Input saved!", False)
            current_view = VIEW_MAIN_MENU
            keyboard_index = KEYBOARD_WAITING
            _menu_start(view_manager)


def _loading_run(view_manager, message: str = "Fetching...") -> None:
    """Start the loading view"""
    from picoware.gui.loading import Loading

    global _loading

    if _loading is None:
        draw = view_manager.get_draw()
        bg = view_manager.background_color
        fg = view_manager.foreground_color

        _loading = Loading(draw, fg, bg)
        _loading.text = message
    else:
        _loading.animate()


def _menu_start(view_manager) -> None:
    """Start the menu view"""
    from picoware.gui.menu import Menu
    from picoware.system.colors import TFT_BLUE

    global _menu

    if _menu is not None:
        del _menu
        _menu = None

    draw = view_manager.get_draw()
    bg = view_manager.background_color
    fg = view_manager.foreground_color

    # set menu
    _menu = Menu(
        draw,
        "Telegram Menu",
        0,
        draw.size.y,
        fg,
        bg,
        TFT_BLUE,
        fg,
    )

    # add items
    _menu.add_item("Send Message")
    _menu.add_item("View Channel")
    _menu.add_item("Set Bot Token")
    _menu.add_item("Set Chat ID")

    _menu.set_selected(menu_index)
    _menu.set_selected(menu_index)


def __reset(view_manager) -> None:
    """Reset globals"""
    global current_view, menu_index, _http, _menu, _loading, fetch_started
    global sending_index, keyboard_index, channel_index, _message_to_send, _textbox

    current_view = VIEW_MAIN_MENU
    menu_index = MENU_ITEM_SEND_MESSAGE
    sending_index = SENDING_WAITING
    keyboard_index = KEYBOARD_WAITING
    channel_index = CHANNEL_FETCHING
    _message_to_send = ""
    if _http is not None:
        del _http
        _http = None
    if _menu is not None:
        del _menu
        _menu = None
    if _loading is not None:
        del _loading
        _loading = None
    if _textbox is not None:
        del _textbox
        _textbox = None
    fetch_started = False
    view_manager.keyboard.reset()


def __telegram_fetch(view_manager) -> bool:
    """Fetch Telegram messages"""
    from picoware.system.http import HTTP

    global _http
    if _http is not None:
        del _http
        _http = None

    _http = HTTP()

    storage = view_manager.storage
    token = storage.read("picoware/telegram/token.txt")

    if not token:
        __alert(
            view_manager,
            "Bot token not set.",
        )
        return False

    return _http.get_async(
        url=f"https://api.telegram.org/bot{token}/getUpdates",
        save_to_file="picoware/telegram/messages.txt",
        storage=storage,
    )


def __telegram_send(view_manager, text: str) -> bool:
    """Send a message via Telegram"""
    from picoware.system.http import HTTP

    global _http
    if _http is not None:
        del _http
        _http = None

    _http = HTTP()

    storage = view_manager.storage
    token = storage.read("picoware/telegram/token.txt")
    chat_id = storage.read("picoware/telegram/chat_id.txt")

    if not token:
        __alert(
            view_manager,
            "Bot token not set.",
            False,
        )
        return False
    if not chat_id:
        __alert(
            view_manager,
            "Chat ID not set.",
            False,
        )
        return False

    payload: dict = {}
    payload["chat_id"] = chat_id
    payload["text"] = text

    return _http.post_async(
        url=f"https://api.telegram.org/bot{token}/sendMessage",
        payload=payload,
        headers={"Content-Type": "application/json"},
        save_to_file="picoware/telegram/message.txt",
        storage=storage,
    )


def start(view_manager) -> bool:
    """Start the app"""
    if not view_manager.has_sd_card:
        __alert(
            view_manager,
            "Telegram app requires an SD card.",
            False,
        )
        return False

    if not view_manager.has_wifi:
        __alert(
            view_manager,
            "Telegram app requires WiFi.",
            False,
        )
        return False

    if not view_manager.wifi.is_connected:
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        __alert(view_manager, "WiFi not connected...", False)

        connect_to_saved_wifi(view_manager)

        return False

    # create telegram folder if it doesn't exist
    view_manager.get_storage().mkdir("picoware/telegram")

    _menu_start(view_manager)

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_LEFT,
        BUTTON_DOWN,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )

    inp = view_manager.get_input_manager()
    button = inp.button

    global current_view, menu_index, _menu, fetch_started, sending_index, keyboard_index, channel_index

    if current_view == VIEW_MAIN_MENU:
        if button == BUTTON_BACK:
            inp.reset()
            view_manager.back()
        elif button in (BUTTON_UP, BUTTON_LEFT):
            inp.reset()
            _menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            inp.reset()
            _menu.scroll_down()
        elif button == BUTTON_CENTER:
            inp.reset()
            menu_index = _menu.selected_index
            if menu_index == MENU_ITEM_SEND_MESSAGE:
                current_view = VIEW_SENDING_MESSAGE
                _keyboard_run(view_manager)
            elif menu_index == MENU_ITEM_VIEW_CHANNEL:
                current_view = VIEW_CHANNEL
                if __telegram_fetch(view_manager):
                    fetch_started = True
            elif menu_index == MENU_ITEM_SET_BOT_TOKEN:
                current_view = VIEW_KEYBOARD_TOKEN
                _keyboard_run(view_manager)
            elif menu_index == MENU_ITEM_SET_CHAT_ID:
                current_view = VIEW_KEYBOARD_CHAT_ID
                _keyboard_run(view_manager)
    elif current_view == VIEW_SENDING_MESSAGE:
        if button == BUTTON_BACK:
            inp.reset()
            current_view = VIEW_MAIN_MENU
            sending_index = SENDING_WAITING
            _menu_start(view_manager)
        elif sending_index == SENDING_KEYBOARD:
            _keyboard_run(view_manager)
        elif sending_index == SENDING_SENDING:
            _http_await(view_manager)
    elif current_view == VIEW_CHANNEL:
        if button == BUTTON_BACK:
            inp.reset()
            current_view = VIEW_MAIN_MENU
            fetch_started = False
            channel_index = CHANNEL_FETCHING
            _menu_start(view_manager)
        elif channel_index == CHANNEL_FETCHING:
            _http_await(view_manager)
        elif channel_index == CHANNEL_DISPLAYING:
            __channel_display(view_manager)
    elif current_view in (VIEW_KEYBOARD_TOKEN, VIEW_KEYBOARD_CHAT_ID):
        if button == BUTTON_BACK:
            inp.reset()
            current_view = VIEW_MAIN_MENU
            keyboard_index = KEYBOARD_WAITING
            _menu_start(view_manager)
        else:
            _keyboard_run(view_manager)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    __reset(view_manager)

    collect()
