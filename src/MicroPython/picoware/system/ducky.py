"""DuckyScript interpreter for USB HID devices."""

import time

from picoware.system.usb import USBKeyboard, USBMedia


class Ducky:
    """Read and execute DuckyScript commands."""

    _ALIASES = {
        "DEFAULTDELAY": "DEFAULT_DELAY",
        "STRINGDELAY": "STRING_DELAY",
        "DEFAULTSTRINGDELAY": "DEFAULT_STRING_DELAY",
        "ALTCODE": "ALTSTRING",
        "LEFT_CLICK": "LEFTCLICK",
        "RIGHT_CLICK": "RIGHTCLICK",
        "MOUSE_MOVE": "MOUSEMOVE",
        "MOUSE_SCROLL": "MOUSESCROLL",
    }

    _MODIFIERS = {
        "CTRL": USBKeyboard.MOD_LCTRL,
        "CONTROL": USBKeyboard.MOD_LCTRL,
        "SHIFT": USBKeyboard.MOD_LSHIFT,
        "ALT": USBKeyboard.MOD_LALT,
        "GUI": USBKeyboard.MOD_LGUI,
        "WINDOWS": USBKeyboard.MOD_LGUI,
    }

    _SPECIAL_KEYS = {
        "DOWNARROW": USBKeyboard.KEY_DOWN,
        "DOWN": USBKeyboard.KEY_DOWN,
        "LEFTARROW": USBKeyboard.KEY_LEFT,
        "LEFT": USBKeyboard.KEY_LEFT,
        "RIGHTARROW": USBKeyboard.KEY_RIGHT,
        "RIGHT": USBKeyboard.KEY_RIGHT,
        "UPARROW": USBKeyboard.KEY_UP,
        "UP": USBKeyboard.KEY_UP,
        "ENTER": USBKeyboard.KEY_ENTER,
        "RETURN": USBKeyboard.KEY_ENTER,
        "DELETE": USBKeyboard.KEY_DELETE,
        "DEL": USBKeyboard.KEY_DELETE,
        "BACKSPACE": 0x2A,
        "END": 0x4D,
        "HOME": 0x4A,
        "ESCAPE": USBKeyboard.KEY_ESC,
        "ESC": USBKeyboard.KEY_ESC,
        "INSERT": 0x49,
        "PAGEUP": 0x4B,
        "PAGEDOWN": 0x4E,
        "CAPSLOCK": 0x39,
        "NUMLOCK": 0x53,
        "SCROLLLOCK": 0x47,
        "PRINTSCREEN": 0x46,
        "BREAK": 0x48,
        "PAUSE": 0x48,
        "SPACE": USBKeyboard.KEY_SPACE,
        "TAB": USBKeyboard.KEY_TAB,
        "MENU": 0x65,
        "APP": 0x65,
    }

    _MEDIA_KEYS = {
        "POWER": 0x0030,
        "REBOOT": 0x0030,
        "SLEEP": 0x0032,
        "LOGOFF": 0x019A,
        "EXIT": 0x0029,
        "HOME": 0x0223,
        "BACK": 0x0224,
        "FORWARD": 0x0225,
        "REFRESH": 0x0227,
        "SNAPSHOT": 0x0065,
        "PLAY": 0x00B0,
        "PAUSE": 0x00B1,
        "PLAY_PAUSE": USBMedia.USAGE_PLAY_PAUSE,
        "NEXT_TRACK": USBMedia.USAGE_NEXT_TRACK,
        "PREV_TRACK": USBMedia.USAGE_PREV_TRACK,
        "STOP": USBMedia.USAGE_STOP,
        "EJECT": 0x00B8,
        "MUTE": USBMedia.USAGE_MUTE,
        "VOLUME_UP": USBMedia.USAGE_VOL_UP,
        "VOLUME_DOWN": USBMedia.USAGE_VOL_DOWN,
        "FN": 0x0003,
        "BRIGHT_UP": 0x006F,
        "BRIGHT_DOWN": 0x0070,
    }

    _KEYPAD_KEYS = {
        "0": 0x62,
        "1": 0x59,
        "2": 0x5A,
        "3": 0x5B,
        "4": 0x5C,
        "5": 0x5D,
        "6": 0x5E,
        "7": 0x5F,
        "8": 0x60,
        "9": 0x61,
    }

    def __init__(
        self,
        usb_device,
        storage=None,
        media_device=None,
        mouse_device=None,
        button_reader=None,
    ):
        """Create an interpreter for a USB device and optional peripherals.

        Args:
            usb_device: USB keyboard-compatible device.
            storage: Optional storage instance used by :meth:`exec`.
            media_device: Optional USB media-key device.
            mouse_device: Optional USB mouse device.
            button_reader: Optional callable returning whether a button was pressed.
        """
        self.usb_device = usb_device
        self.storage = storage
        self.media_device = media_device
        self.mouse_device = mouse_device
        self.button_reader = button_reader
        self.default_delay = 0
        self.default_string_delay = 0
        self._string_delay = None
        self._last_command = None
        self._held_modifiers = 0
        self._held_keycodes = []
        self.device_id = None

    def exec(self, file_path):
        """Read a DuckyScript file from SD storage and execute it.

        Args:
            file_path (str): Path to the script on the SD card.

        Returns:
            None: The script is executed synchronously.
        """
        return self.run(self.storage.read(file_path))

    def run(self, code):
        """Execute DuckyScript source code synchronously.

        Args:
            code (str or bytes): DuckyScript source to execute.

        Returns:
            None: The script is executed synchronously.
        """
        if isinstance(code, bytes):
            code = code.decode("utf-8")
        if not isinstance(code, str):
            raise TypeError("DuckyScript must be text or bytes")

        self._reset_run_state()
        try:
            for line_number, line in enumerate(code.splitlines(), 1):
                parsed = self._parse_line(line)
                if parsed is None:
                    continue

                command, argument = parsed
                if command == "REPEAT":
                    self._delay_before_command()
                    self._repeat(argument, line_number)
                    continue

                self._execute_command(command, argument, line_number)
                self._last_command = (command, argument)
        finally:
            if self._held_modifiers or self._held_keycodes:
                self._release_all()

    def _reset_run_state(self):
        """Reset per-script parser and key state."""
        self.default_delay = 0
        self.default_string_delay = 0
        self._string_delay = None
        self._last_command = None
        self._held_modifiers = 0
        self._held_keycodes = []

    def _parse_line(self, line):
        """Parse one source line into a command and argument."""
        line = line.strip()
        if not line:
            return None

        parts = line.split(None, 1)
        command = self._ALIASES.get(parts[0].upper(), parts[0].upper())
        argument = parts[1] if len(parts) == 2 else ""
        if command == "REM":
            return None
        return command, argument

    def _execute_command(self, command, argument, line_number):
        """Execute one parsed command."""
        self._delay_before_command()

        if command == "DELAY":
            self._sleep(self._number(argument, command))
        elif command == "DEFAULT_DELAY":
            self.default_delay = self._number(argument, command)
        elif command == "STRING_DELAY":
            self._string_delay = self._number(argument, command)
        elif command == "DEFAULT_STRING_DELAY":
            self.default_string_delay = self._number(argument, command)
        elif command in ("STRING", "STRINGLN"):
            self._string(argument)
            if command == "STRINGLN":
                self._press_key("ENTER")
        elif command == "HOLD":
            self._hold(argument)
        elif command == "RELEASE":
            self._release(argument)
        elif command == "ALTCHAR":
            self._alt_char(argument)
        elif command == "ALTSTRING":
            self._alt_string(argument)
        elif command == "SYSRQ":
            self._sysrq(argument)
        elif command == "MEDIA":
            self._media(argument)
        elif command == "GLOBE":
            self._globe(argument)
        elif command == "WAIT_FOR_BUTTON_PRESS":
            self._wait_for_button()
        elif command == "ID":
            self._set_device_id(argument)
        elif command == "LEFTCLICK":
            self._mouse_click("left")
        elif command == "RIGHTCLICK":
            self._mouse_click("right")
        elif command == "MOUSEMOVE":
            self._mouse_move(argument, command)
        elif command == "MOUSESCROLL":
            self._mouse_scroll(argument, command)
        elif command in ("REM", ""):
            return
        else:
            try:
                key_expression = command
                if argument:
                    key_expression += " " + argument
                self._press_key(key_expression)
            except ValueError as error:
                raise ValueError(
                    "Unknown DuckyScript command on line {}: {}".format(
                        line_number, command
                    )
                ) from error

    def _repeat(self, argument, line_number):
        """Repeat the previously executed command."""
        if self._last_command is None:
            raise ValueError("REPEAT has no previous command on line {}".format(line_number))

        count = self._number(argument, "REPEAT")
        for _ in range(count):
            command, command_argument = self._last_command
            self._execute_command(command, command_argument, line_number)

    def _delay_before_command(self):
        """Apply the configured delay before a command."""
        if self.default_delay:
            self._sleep(self.default_delay)

    def _string(self, text):
        """Type a string using the configured string delay."""
        delay = self._string_delay
        if delay is None:
            delay = self.default_string_delay
        self._string_delay = None

        type_string = getattr(self.usb_device, "type_string", None)
        if type_string is not None:
            type_string(text, delay)
            self._restore_holds()
            return

        for character in text:
            self._press_key(character)
            if delay:
                self._sleep(delay)

    def _press_key(self, argument):
        """Press and release a key or key combination."""
        modifier, keycode = self._key_spec(argument)
        press = getattr(self.usb_device, "press", None)
        if press is not None:
            press(modifier, keycode)
        else:
            self._send_key(modifier, keycode)
            self._release_all()
        self._restore_holds()

    def _hold(self, argument):
        """Press a key without releasing it."""
        modifier, keycode = self._key_spec(argument)
        self._held_modifiers |= modifier
        if keycode:
            self._held_keycodes.append(keycode)
        self._send_held_keys()

    def _release(self, argument):
        """Release all keys or the requested held key."""
        if not argument.strip():
            self._held_modifiers = 0
            self._held_keycodes = []
            self._release_all()
            return

        modifier, keycode = self._key_spec(argument, include_held=False)
        self._held_modifiers &= ~modifier
        if keycode in self._held_keycodes:
            self._held_keycodes.remove(keycode)
        self._release_all()
        if self._held_modifiers or self._held_keycodes:
            self._send_held_keys()

    def _send_held_keys(self):
        """Send the current held-key report."""
        keycode = self._held_keycodes[-1] if self._held_keycodes else 0
        self._send_key(self._held_modifiers, keycode)

    def _restore_holds(self):
        """Restore held keys after a press that released the report."""
        if self._held_modifiers or self._held_keycodes:
            self._send_held_keys()

    def _send_key(self, modifier, keycode):
        """Send a key-down report through the USB device."""
        send_key = getattr(self.usb_device, "send_key", None)
        if send_key is None:
            raise NotImplementedError("USB device does not support held keys")
        send_key(modifier, keycode)

    def _release_all(self):
        """Release all keys through the USB device."""
        release = getattr(self.usb_device, "release", None)
        if release is None:
            raise NotImplementedError("USB device does not support key release")
        release()

    def _key_spec(self, argument, include_held=True):
        """Resolve a DuckyScript key expression."""
        tokens = self._key_tokens(argument)
        if not tokens:
            raise ValueError("Missing key")

        modifier = self._held_modifiers if include_held else 0
        key_tokens = []
        for token in tokens:
            modifier_bit = self._MODIFIERS.get(token.upper())
            if modifier_bit is None:
                key_tokens.append(token)
            else:
                modifier |= modifier_bit

        if not key_tokens:
            return modifier, 0
        if len(key_tokens) != 1:
            raise ValueError("Only one non-modifier key is allowed")

        token = key_tokens[0]
        keycode = self._SPECIAL_KEYS.get(token.upper())
        if keycode is None and token.upper().startswith("F"):
            try:
                function_number = int(token[1:])
            except ValueError:
                function_number = 0
            if 1 <= function_number <= 12:
                keycode = USBKeyboard.KEY_F1 + function_number - 1

        if keycode is None:
            keymap = getattr(
                self.usb_device,
                "KEYMAP",
                USBKeyboard.KEYMAP,
            )
            keycode = keymap.get(token, keymap.get(token.lower()))
            if keycode is None:
                raise ValueError("Unknown key: {}".format(token))
            if (
                len(token) == 1
                and not token.isalpha()
                and token in USBKeyboard.SHIFT_CHARS
            ):
                modifier |= USBKeyboard.MOD_LSHIFT

        return modifier, keycode

    def _key_tokens(self, argument):
        """Split modifier-key syntax using spaces or hyphens."""
        argument = argument.strip()
        if argument == "-":
            return [argument]

        tokens = []
        for part in argument.split():
            if part == "-":
                tokens.append(part)
            else:
                tokens.extend(part.split("-"))
        return [token for token in tokens if token]

    def _alt_char(self, argument):
        """Type one character using the ALT+numpad method."""
        value = argument.strip()
        number = self._number(value, "ALTCHAR")
        if not value.isdigit():
            value = str(number)
        self._send_alt_code(value)

    def _alt_string(self, text):
        """Type a string using ALT+numpad character codes."""
        delay = self._string_delay
        if delay is None:
            delay = self.default_string_delay
        self._string_delay = None

        for character in text:
            self._send_alt_code(str(ord(character)))
            if delay:
                self._sleep(delay)

    def _send_alt_code(self, code):
        """Send a decimal code while holding the ALT modifier."""
        self._send_key(USBKeyboard.MOD_LALT, 0)
        for digit in code:
            self._send_key(
                USBKeyboard.MOD_LALT,
                self._KEYPAD_KEYS[digit],
            )
        self._release_all()
        self._restore_holds()

    def _sysrq(self, argument):
        """Send an ALT+PRINTSCREEN SysRq sequence."""
        _, keycode = self._key_spec(argument)
        self._send_key(
            USBKeyboard.MOD_LALT,
            self._SPECIAL_KEYS["PRINTSCREEN"],
        )
        self._send_key(USBKeyboard.MOD_LALT, keycode)
        self._release_all()
        self._restore_holds()

    def _media(self, argument):
        """Send a consumer-control media key."""
        key_name = argument.strip().upper()
        usage = self._MEDIA_KEYS.get(key_name)
        if usage is None:
            raise ValueError("Unknown media key: {}".format(argument.strip()))

        device = self.media_device or self.usb_device
        press_media = getattr(device, "press_media", None)
        if press_media is not None:
            press_media(usage)
            return

        press = getattr(device, "press", None)
        if self.media_device is not None and press is not None:
            press(usage)
            return
        if isinstance(device, USBMedia) and press is not None:
            press(usage)
            return

        raise NotImplementedError("No USB media-key device is available")

    def _globe(self, argument):
        """Send a Globe/Fn key through an optional device hook."""
        modifier, keycode = self._key_spec(argument)
        device = self.usb_device
        press_globe = getattr(device, "press_globe", None)
        if press_globe is not None:
            press_globe(modifier, keycode)
            return
        raise NotImplementedError("USB device does not support Globe keys")

    def _wait_for_button(self):
        """Wait until the configured button source reports a press."""
        wait_for_button = getattr(self.usb_device, "wait_for_button_press", None)
        if wait_for_button is not None:
            wait_for_button()
            return
        if self.button_reader is None:
            raise NotImplementedError("No button reader is available")
        while not self.button_reader():
            self._sleep(10)

    def _set_device_id(self, argument):
        """Validate and apply a custom USB device ID when supported."""
        parts = argument.strip().split(None, 1)
        if not parts or ":" not in parts[0]:
            raise ValueError("ID requires VID:PID")

        vendor_id, product_id = parts[0].split(":", 1)
        int(vendor_id, 16)
        int(product_id, 16)
        self.device_id = argument.strip()

        set_id = getattr(self.usb_device, "set_id", None)
        if set_id is not None:
            set_id(argument.strip())

    def _mouse_click(self, button):
        """Send a mouse click through an optional mouse device."""
        device = self.mouse_device or self.usb_device
        method = getattr(device, "{}_click".format(button), None)
        if method is None:
            method = getattr(device, "mouse_click", None)
            if method is not None:
                method(button)
                return
        if method is None:
            raise NotImplementedError("USB device does not support mouse clicks")
        method()

    def _mouse_move(self, argument, command):
        """Move the mouse by an x and y offset."""
        values = argument.split()
        if len(values) != 2:
            raise ValueError("{} requires x and y values".format(command))
        x = self._number(values[0], command, allow_negative=True)
        y = self._number(values[1], command, allow_negative=True)
        device = self.mouse_device or self.usb_device
        method = getattr(device, "mouse_move", None)
        if method is None:
            method = getattr(device, "move_mouse", None)
        if method is None:
            raise NotImplementedError("USB device does not support mouse movement")
        method(x, y)

    def _mouse_scroll(self, argument, command):
        """Scroll the mouse by a signed distance."""
        device = self.mouse_device or self.usb_device
        method = getattr(device, "mouse_scroll", None)
        if method is None:
            method = getattr(device, "scroll_mouse", None)
        if method is None:
            raise NotImplementedError("USB device does not support mouse scrolling")
        method(self._number(argument, command, allow_negative=True))

    def _number(self, value, command, allow_negative=False):
        """Parse an integer command argument."""
        try:
            number = int(value.strip(), 0)
        except ValueError as error:
            try:
                number = int(value.strip(), 10)
            except ValueError:
                raise ValueError("{} requires an integer".format(command)) from error
        if number < 0 and not allow_negative:
            raise ValueError("{} cannot be negative".format(command))
        return number

    def _sleep(self, milliseconds):
        """Sleep for a number of milliseconds."""
        sleep_ms = getattr(time, "sleep_ms", None)
        if sleep_ms is not None:
            sleep_ms(milliseconds)
        else:
            time.sleep(milliseconds / 1000)