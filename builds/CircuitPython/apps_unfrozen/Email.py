# Complete project details: https://RandomNerdTutorials.com/raspberry-pi-pico-w-send-email-micropython/
# uMail (MicroMail) for MicroPython: https://github.com/shawwwn/uMail/blob/master/umail.py
# Copyright (c) 2018 Shawwwn <shawwwn1@gmail.com>
# License: MIT
from micropython import const
import socket
from ssl import wrap_socket as ssl_wrap_socket
import _thread

DEFAULT_TIMEOUT = const(10)  # sec
LOCAL_DOMAIN = "127.0.0.1"
CMD_EHLO = "EHLO"
CMD_STARTTLS = "STARTTLS"
CMD_AUTH = "AUTH"
CMD_MAIL = "MAIL"
AUTH_PLAIN = "PLAIN"
AUTH_LOGIN = "LOGIN"


class SMTP:
    def cmd(self, cmd_str):
        sock = self._sock
        sock.write("%s\r\n" % cmd_str)
        resp = []
        next = True
        while next:
            code = sock.read(3)
            next = sock.read(1) == b"-"
            resp.append(sock.readline().strip().decode())
        return int(code), resp

    def __init__(self, host, port, ssl=False, username=None, password=None):
        self.username = username
        addr = socket.getaddrinfo(host, port)[0][-1]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(DEFAULT_TIMEOUT)
        sock.connect(addr)
        if ssl:
            sock = ssl_wrap_socket(sock)
        code = int(sock.read(3))
        sock.readline()
        assert code == 220, "cant connect to server %d, %s" % (code, resp)
        self._sock = sock

        code, resp = self.cmd(CMD_EHLO + " " + LOCAL_DOMAIN)
        assert code == 250, "%d" % code
        if not ssl and CMD_STARTTLS in resp:
            code, resp = self.cmd(CMD_STARTTLS)
            assert code == 220, "start tls failed %d, %s" % (code, resp)
            self._sock = ssl_wrap_socket(sock)

        if username and password:
            self.login(username, password)

    def login(self, username, password):
        self.username = username
        code, resp = self.cmd(CMD_EHLO + " " + LOCAL_DOMAIN)
        assert code == 250, "%d, %s" % (code, resp)

        auths = None
        for feature in resp:
            if feature[:4].upper() == CMD_AUTH:
                auths = feature[4:].strip("=").upper().split()
        assert auths != None, "no auth method"

        from ubinascii import b2a_base64 as b64

        if AUTH_PLAIN in auths:
            cren = b64("\0%s\0%s" % (username, password))[:-1].decode()
            code, resp = self.cmd("%s %s %s" % (CMD_AUTH, AUTH_PLAIN, cren))
        elif AUTH_LOGIN in auths:
            code, resp = self.cmd(
                "%s %s %s" % (CMD_AUTH, AUTH_LOGIN, b64(username)[:-1].decode())
            )
            assert code == 334, "wrong username %d, %s" % (code, resp)
            code, resp = self.cmd(b64(password)[:-1].decode())
        else:
            raise Exception("auth(%s) not supported " % ", ".join(auths))

        assert code == 235 or code == 503, "auth error %d, %s" % (code, resp)
        return code, resp

    def to(self, addrs, mail_from=None):
        mail_from = self.username if mail_from == None else mail_from
        code, resp = self.cmd("MAIL FROM: <%s>" % mail_from)
        assert code == 250, "sender refused %d, %s" % (code, resp)

        if isinstance(addrs, str):
            addrs = [addrs]
        count = 0
        for addr in addrs:
            code, resp = self.cmd("RCPT TO: <%s>" % addr)
            if code != 250 and code != 251:
                print("%s refused, %s" % (addr, resp))
                count += 1
        assert count != len(addrs), "recipient refused, %d, %s" % (code, resp)

        code, resp = self.cmd("DATA")
        assert code == 354, "data refused, %d, %s" % (code, resp)
        return code, resp

    def write(self, content):
        self._sock.write(content)

    def send(self, content=""):
        if content:
            self.write(content)
        self._sock.write("\r\n.\r\n")  # the five letter sequence marked for ending
        line = self._sock.readline()
        return (int(line[:3]), line[4:].strip().decode())

    def quit(self):
        self.cmd("QUIT")
        self._sock.close()


class SMTPAsync:
    '''Threaded version of SMTP for sending emails "asynchronously"'''

    def __init__(self, host, port, ssl=False, username=None, password=None):
        self.smtp = SMTP(host, port, ssl, username, password)
        self._is_running: bool = False
        self._thread = None
        self._lock = _thread.allocate_lock()

    def __del__(self):
        """Destructor to clean up resources."""
        self.close()

    @property
    def is_running(self) -> bool:
        """Check if the SMTPAsync is currently running."""
        return self._is_running

    def __close_thread(self):
        """Internal method to close the thread."""
        if self._thread is not None:
            self._thread = None

    def close(self):
        """Close the WebSocket connection."""
        self._is_running = False

        with self._lock:
            if self.smtp is not None:
                try:
                    self.smtp.quit()
                except Exception:
                    pass
                self.smtp = None
            self.__close_thread()

    def send_email(self, from_email, from_password, to_email, subject, message):
        """Send an email asynchronously."""

        def send_thread():
            try:
                self._is_running = True
                self.smtp.login(from_email, from_password)
                self.smtp.to(to_email)
                self.smtp.write("From:" + sender_name + "<" + from_email + ">\n")
                self.smtp.write("Subject:" + subject + "\n")
                self.smtp.write(message)
                self.smtp.send()
            except Exception as e:
                print("Failed to send email:", e)
            finally:
                self.__close_thread()
                self._is_running = False

        if self._thread is None:
            self._thread = _thread.start_new_thread(send_thread, ())


# view constants
VIEW_MAIN_MENU = const(0)  # Main menu view
VIEW_SENDING_MESSAGE = const(1)  # Sending message view
VIEW_KEYBOARD_RECIPIENT = const(2)  # viewing the keyboard to enter recipient email
VIEW_KEYBOARD_EMAIL = const(3)  # viewing the keyboard to enter email
VIEW_KEYBOARD_PASSWORD = const(4)  # viewing the keyboard to enter password
VIEW_KEYBOARD_NAME = const(5)  # viewing the keyboard to enter name
VIEW_KEYBOARD_SUBJECT = const(6)  # viewing the keyboard to enter subject

# menu constatnts
MENU_ITEM_SEND_MESSAGE = const(0)  # Menu item to send a message
MENU_ITEM_SET_EMAIL = const(1)  # Menu item to set email
MENU_ITEM_SET_PASSWORD = const(2)  # Menu item to set password
MENU_ITEM_SET_NAME = const(3)  # Menu item to set sender name

# sending constants
SENDING_WAITING = const(-1)  # Waiting to send
SENDING_KEYBOARD = const(0)  # Keyboard for message input
SENDING_SENDING = const(1)  # Sending the message

# bot token/chat ID constants
KEYBOARD_WAITING = const(-1)  # Waiting for keyboard input
KEYBOARD_ENTERING = const(0)  # Entering via keyboard

# globals
current_view = VIEW_MAIN_MENU
menu_index = MENU_ITEM_SEND_MESSAGE
sending_index = SENDING_WAITING
keyboard_index = KEYBOARD_WAITING

_menu = None
_loading = None
smtp = None
_message_to_send = ""

# Email details
sender_email = ""
sender_app_password = ""
sender_name = "Picoware"
recipient_email = "REPLACE_WITH_THE_RECIPIENT_EMAIL"
email_subject = "Hello from RPi Pico W"


def __await_send(view_manager) -> None:
    """Thread function to wait for email sending to complete"""
    global sending_index, current_view
    if smtp.is_running:
        _loading_run(view_manager, "Sending...")
        return
    view_manager.alert("Message sent!", False)
    sending_index = SENDING_WAITING
    current_view = VIEW_MAIN_MENU


def __load_email_credentials(view_manager) -> bool:
    """Load email credentials from storage"""
    global sender_email, sender_app_password, sender_name, email_subject
    storage = view_manager.storage
    stored_email = storage.read("picoware/email/email.txt")
    stored_password = storage.read("picoware/email/password.txt")
    stored_name = storage.read("picoware/email/name.txt")
    if stored_email:
        sender_email = stored_email
    if stored_password:
        sender_app_password = stored_password
    if stored_name:
        sender_name = stored_name
    return sender_email != "" and sender_app_password != ""


def _keyboard_save(view_manager) -> bool:
    """Keyboard callback function"""
    global _message_to_send, recipient_email, email_subject
    storage = view_manager.storage
    kb = view_manager.keyboard
    if current_view == VIEW_SENDING_MESSAGE:
        _message_to_send = kb.response
        return True
    if current_view == VIEW_KEYBOARD_RECIPIENT:
        recipient_email = kb.response
        return True
    if current_view == VIEW_KEYBOARD_SUBJECT:
        email_subject = kb.response
        return True

    # Determine which file to write to based on current view
    file_path = ""
    if current_view == VIEW_KEYBOARD_EMAIL:
        file_path = "picoware/email/email.txt"
    elif current_view == VIEW_KEYBOARD_PASSWORD:
        file_path = "picoware/email/password.txt"
    elif current_view == VIEW_KEYBOARD_NAME:
        file_path = "picoware/email/name.txt"

    if file_path:
        return storage.write(file_path, kb.response)
    return False


def _keyboard_run(view_manager) -> bool:
    """Start the keyboard view"""
    global current_view, sending_index, keyboard_index

    # Initialize keyboard for subject (part of send flow)
    if current_view == VIEW_KEYBOARD_SUBJECT and keyboard_index == KEYBOARD_WAITING:
        kb = view_manager.keyboard
        kb.reset()
        kb.title = "Enter Subject"
        kb.response = ""
        keyboard_index = KEYBOARD_ENTERING
        kb.run(force=True)
        kb.run(force=True)
        return True

    # Initialize keyboard for recipient email
    if current_view == VIEW_KEYBOARD_RECIPIENT and keyboard_index == KEYBOARD_WAITING:
        kb = view_manager.keyboard
        kb.reset()
        kb.title = "Enter Recipient Email"
        kb.response = (
            recipient_email
            if recipient_email != "REPLACE_WITH_THE_RECIPIENT_EMAIL"
            else ""
        )
        keyboard_index = KEYBOARD_ENTERING
        kb.run(force=True)
        kb.run(force=True)
        return True

    # Initialize keyboard for sending message
    if current_view == VIEW_SENDING_MESSAGE and sending_index == SENDING_WAITING:
        kb = view_manager.keyboard
        kb.reset()
        kb.title = "Enter Message"
        kb.response = ""
        kb.run(force=True)
        kb.run(force=True)
        sending_index = SENDING_KEYBOARD
        return True

    # Initialize keyboard for email/password/name
    if (
        current_view
        in (VIEW_KEYBOARD_EMAIL, VIEW_KEYBOARD_PASSWORD, VIEW_KEYBOARD_NAME)
        and keyboard_index == KEYBOARD_WAITING
    ):
        storage = view_manager.storage
        kb = view_manager.keyboard
        kb.reset()
        if current_view == VIEW_KEYBOARD_EMAIL:
            kb.title = "Enter Email"
            kb.response = storage.read("picoware/email/email.txt")
        elif current_view == VIEW_KEYBOARD_PASSWORD:
            kb.title = "Enter Password"
            kb.response = storage.read("picoware/email/password.txt")
        elif current_view == VIEW_KEYBOARD_NAME:
            kb.title = "Enter Sender Name"
            kb.response = storage.read("picoware/email/name.txt")
        keyboard_index = KEYBOARD_ENTERING
        kb.run(force=True)
        kb.run(force=True)
        return True

    # Run keyboard for subject (part of send flow)
    if current_view == VIEW_KEYBOARD_SUBJECT and keyboard_index == KEYBOARD_ENTERING:
        kb = view_manager.keyboard
        if not kb.run():
            return False

        if kb.is_finished:
            if not _keyboard_save(view_manager):
                view_manager.alert("Failed to save subject.", False)
                current_view = VIEW_MAIN_MENU
                keyboard_index = KEYBOARD_WAITING
            else:
                # Move to recipient email entry
                current_view = VIEW_KEYBOARD_RECIPIENT
                keyboard_index = KEYBOARD_WAITING
                _keyboard_run(view_manager)
        return True

    # Run keyboard for recipient email
    if current_view == VIEW_KEYBOARD_RECIPIENT and keyboard_index == KEYBOARD_ENTERING:
        kb = view_manager.keyboard
        if not kb.run():
            return False

        if kb.is_finished:
            if not _keyboard_save(view_manager):
                view_manager.alert("Failed to save recipient email.", False)
                current_view = VIEW_MAIN_MENU
                keyboard_index = KEYBOARD_WAITING
            else:
                # Move to message entry
                current_view = VIEW_SENDING_MESSAGE
                keyboard_index = KEYBOARD_WAITING
                _keyboard_run(view_manager)
        return True

    # Run keyboard for sending message
    if current_view == VIEW_SENDING_MESSAGE and sending_index == SENDING_KEYBOARD:
        kb = view_manager.keyboard
        if not kb.run():
            return False

        if kb.is_finished:
            if not _keyboard_save(view_manager):
                view_manager.alert("Failed to save message.", False)
                current_view = VIEW_MAIN_MENU
                sending_index = SENDING_WAITING
            else:
                # Start sending the message
                try:
                    if not __load_email_credentials(view_manager):
                        view_manager.alert("Email credentials not set!", False)
                        current_view = VIEW_MAIN_MENU
                        sending_index = SENDING_WAITING
                        return True
                    smtp.send_email(
                        sender_email,
                        sender_app_password,
                        recipient_email,
                        email_subject,
                        _message_to_send,
                    )
                    sending_index = SENDING_SENDING
                    __await_send(view_manager)
                except Exception as e:
                    print("Failed to send email:", e)
                    view_manager.alert(f"Failed to send message: {e}", False)

                current_view = VIEW_MAIN_MENU
                sending_index = SENDING_WAITING
        return True

    # Run keyboard for sender email/password/name
    if (
        current_view
        in (VIEW_KEYBOARD_EMAIL, VIEW_KEYBOARD_PASSWORD, VIEW_KEYBOARD_NAME)
        and keyboard_index == KEYBOARD_ENTERING
    ):
        kb = view_manager.keyboard
        if not kb.run():
            return False

        if kb.is_finished:
            if not _keyboard_save(view_manager):
                view_manager.alert("Failed to save input.", False)
            else:
                view_manager.alert("Input saved!", False)
            current_view = VIEW_MAIN_MENU
            keyboard_index = KEYBOARD_WAITING
            _menu_start(view_manager)
        return True


def _loading_run(view_manager, message: str = "Sending...") -> None:
    """Start the loading view"""
    from picoware.gui.loading import Loading

    global _loading

    if _loading is None:
        draw = view_manager.draw
        bg = view_manager.background_color
        fg = view_manager.foreground_color

        _loading = Loading(draw, fg, bg)
        _loading.text = message
        _loading.animate()
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

    draw = view_manager.draw
    bg = view_manager.background_color
    fg = view_manager.foreground_color

    # set menu
    _menu = Menu(
        draw,
        "Email",
        0,
        draw.size.y,
        fg,
        bg,
        TFT_BLUE,
        fg,
    )

    # add items
    _menu.add_item("Send Message")
    _menu.add_item("Set Email")
    _menu.add_item("Set Password")
    _menu.add_item("Set Name")

    _menu.set_selected(menu_index)
    _menu.set_selected(menu_index)


def start(view_manager) -> bool:
    """Start the app"""
    if not view_manager.has_sd_card:
        view_manager.alert(
            "Email app requires an SD card.",
            False,
        )
        return False

    if not view_manager.has_wifi:
        view_manager.alert(
            "Email app requires WiFi.",
            False,
        )
        return False

    if not view_manager.wifi.is_connected:
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        view_manager.alert("WiFi not connected...", False)

        connect_to_saved_wifi(view_manager)

        return False

    # create email folder if it doesn't exist
    view_manager.storage.mkdir("picoware/email")

    _menu_start(view_manager)

    global smtp

    smtp = SMTPAsync("smtp.gmail.com", 465, ssl=True)  # Gmail's SSL port

    __load_email_credentials(view_manager)

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

    inp = view_manager.input_manager
    button = inp.button

    global current_view, menu_index, sending_index, keyboard_index

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
                current_view = VIEW_KEYBOARD_SUBJECT
                if not _keyboard_run(view_manager):
                    view_manager.back()
            elif menu_index == MENU_ITEM_SET_EMAIL:
                current_view = VIEW_KEYBOARD_EMAIL
                if not _keyboard_run(view_manager):
                    current_view = VIEW_MAIN_MENU
            elif menu_index == MENU_ITEM_SET_PASSWORD:
                current_view = VIEW_KEYBOARD_PASSWORD
                if not _keyboard_run(view_manager):
                    current_view = VIEW_MAIN_MENU
            elif menu_index == MENU_ITEM_SET_NAME:
                current_view = VIEW_KEYBOARD_NAME
                if not _keyboard_run(view_manager):
                    current_view = VIEW_MAIN_MENU
    elif current_view == VIEW_KEYBOARD_SUBJECT:
        if button == BUTTON_BACK or not _keyboard_run(view_manager):
            inp.reset()
            current_view = VIEW_MAIN_MENU
            keyboard_index = KEYBOARD_WAITING
            _menu_start(view_manager)
    elif current_view == VIEW_KEYBOARD_RECIPIENT:
        if button == BUTTON_BACK or not _keyboard_run(view_manager):
            inp.reset()
            current_view = VIEW_MAIN_MENU
            keyboard_index = KEYBOARD_WAITING
            _menu_start(view_manager)
    elif current_view == VIEW_SENDING_MESSAGE:
        if button == BUTTON_BACK:
            inp.reset()
            current_view = VIEW_MAIN_MENU
            sending_index = SENDING_WAITING
            _menu_start(view_manager)
        elif sending_index == SENDING_KEYBOARD:
            if not _keyboard_run(view_manager):
                current_view = VIEW_MAIN_MENU
                sending_index = SENDING_WAITING
                _menu_start(view_manager)
        elif sending_index == SENDING_SENDING:
            __await_send(view_manager)
    elif current_view in (
        VIEW_KEYBOARD_EMAIL,
        VIEW_KEYBOARD_PASSWORD,
        VIEW_KEYBOARD_NAME,
    ):
        if button == BUTTON_BACK or not _keyboard_run(view_manager):
            inp.reset()
            current_view = VIEW_MAIN_MENU
            keyboard_index = KEYBOARD_WAITING
            _menu_start(view_manager)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global smtp, _menu, _loading
    del smtp
    smtp = None
    del _menu
    _menu = None
    del _loading
    _loading = None
    view_manager.keyboard.reset()
    collect()
