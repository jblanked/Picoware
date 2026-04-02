# Author: JBlanked
# License: GPL-3.0 License
# Source: https://github.com/jblanked/Picoware

from machine import USBDevice
import struct, time


class USBKeyboard:
    """USB HID keyboard device that runs alongside the built-in CDC (serial) interface.

    Builds a composite USB descriptor by appending a HID keyboard interface to
    the existing CDC configuration so both the REPL serial port and the keyboard
    are available at the same time.
    """

    HID_REPORT_DESC = bytes(
        [
            0x05,
            0x01,
            0x09,
            0x06,
            0xA1,
            0x01,
            0x05,
            0x07,
            0x19,
            0xE0,
            0x29,
            0xE7,
            0x15,
            0x00,
            0x25,
            0x01,
            0x75,
            0x01,
            0x95,
            0x08,
            0x81,
            0x02,
            0x95,
            0x01,
            0x75,
            0x08,
            0x81,
            0x03,
            0x95,
            0x06,
            0x75,
            0x08,
            0x15,
            0x00,
            0x25,
            0x65,
            0x05,
            0x07,
            0x19,
            0x00,
            0x29,
            0x65,
            0x81,
            0x00,
            0xC0,
        ]
    )

    HID_IAD = bytes([0x08, 0x0B, 0x02, 0x01, 0x03, 0x01, 0x01, 0x00])

    # Modifiers
    MOD_LCTRL = 0x01
    MOD_LSHIFT = 0x02
    MOD_LALT = 0x04
    MOD_LGUI = 0x08
    MOD_RCTRL = 0x10
    MOD_RSHIFT = 0x20
    MOD_RALT = 0x40
    MOD_RGUI = 0x80

    # Special keys
    KEY_ENTER = 0x28
    KEY_ESC = 0x29
    KEY_TAB = 0x2B
    KEY_SPACE = 0x2C
    KEY_DELETE = 0x4C
    KEY_UP = 0x52
    KEY_DOWN = 0x51
    KEY_LEFT = 0x50
    KEY_RIGHT = 0x4F
    KEY_F1 = 0x3A
    KEY_F2 = 0x3B
    KEY_F3 = 0x3C
    KEY_F4 = 0x3D
    KEY_F5 = 0x3E
    KEY_F6 = 0x3F
    KEY_F7 = 0x40
    KEY_F8 = 0x41
    KEY_F9 = 0x42
    KEY_F10 = 0x43
    KEY_F11 = 0x44
    KEY_F12 = 0x45

    KEYMAP = {
        "a": 0x04,
        "b": 0x05,
        "c": 0x06,
        "d": 0x07,
        "e": 0x08,
        "f": 0x09,
        "g": 0x0A,
        "h": 0x0B,
        "i": 0x0C,
        "j": 0x0D,
        "k": 0x0E,
        "l": 0x0F,
        "m": 0x10,
        "n": 0x11,
        "o": 0x12,
        "p": 0x13,
        "q": 0x14,
        "r": 0x15,
        "s": 0x16,
        "t": 0x17,
        "u": 0x18,
        "v": 0x19,
        "w": 0x1A,
        "x": 0x1B,
        "y": 0x1C,
        "z": 0x1D,
        "1": 0x1E,
        "2": 0x1F,
        "3": 0x20,
        "4": 0x21,
        "5": 0x22,
        "6": 0x23,
        "7": 0x24,
        "8": 0x25,
        "9": 0x26,
        "0": 0x27,
        "\n": 0x28,
        "\t": 0x2B,
        " ": 0x2C,
        "-": 0x2D,
        "=": 0x2E,
        "[": 0x2F,
        "]": 0x30,
        "\\": 0x31,
        ";": 0x33,
        "'": 0x34,
        "`": 0x35,
        ",": 0x36,
        ".": 0x37,
        "/": 0x38,
        "A": 0x04,
        "B": 0x05,
        "C": 0x06,
        "D": 0x07,
        "E": 0x08,
        "F": 0x09,
        "G": 0x0A,
        "H": 0x0B,
        "I": 0x0C,
        "J": 0x0D,
        "K": 0x0E,
        "L": 0x0F,
        "M": 0x10,
        "N": 0x11,
        "O": 0x12,
        "P": 0x13,
        "Q": 0x14,
        "R": 0x15,
        "S": 0x16,
        "T": 0x17,
        "U": 0x18,
        "V": 0x19,
        "W": 0x1A,
        "X": 0x1B,
        "Y": 0x1C,
        "Z": 0x1D,
        "!": 0x1E,
        "@": 0x1F,
        "#": 0x20,
        "$": 0x21,
        "%": 0x22,
        "^": 0x23,
        "&": 0x24,
        "*": 0x25,
        "(": 0x26,
        ")": 0x27,
        "_": 0x2D,
        "+": 0x2E,
        "{": 0x2F,
        "}": 0x30,
        "|": 0x31,
        ":": 0x33,
        '"': 0x34,
        "~": 0x35,
        "<": 0x36,
        ">": 0x37,
        "?": 0x38,
    }

    SHIFT_CHARS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+{}|:"<>?~')

    def __init__(
        self, manufacturer="MicroPython", product="Picoware Keyboard", serial="000000"
    ):
        """Create a USBKeyboard instance.

        Args:
            manufacturer: Manufacturer string reported in the USB device descriptor.
            product: Product string reported in the USB device descriptor.
            serial: Serial number string reported in the USB device descriptor.
        """
        self._usbdev = None
        self._xfer_done = True
        self._manufacturer = manufacturer
        self._product = product
        self._serial = serial

    def init(self):
        """Initialise and activate the composite CDC + HID USB device.

        Appends a HID keyboard interface to the built-in CDC descriptor,
        re-configures the USBDevice, and activates it. Must be called once
        before any key-sending methods are used.
        """
        hid_iface = bytes(
            [
                0x09,
                0x04,
                0x02,
                0x00,
                0x01,
                0x03,
                0x01,
                0x01,
                0x00,
                0x09,
                0x21,
                0x11,
                0x01,
                0x00,
                0x01,
                0x22,
                len(self.HID_REPORT_DESC),
                0x00,
                0x07,
                0x05,
                0x83,
                0x03,
                0x08,
                0x00,
                0x0A,
            ]
        )
        self._xfer_done = True
        usbdev = USBDevice()
        desc_dev = bytes(usbdev.BUILTIN_CDC.desc_dev)
        desc_cfg = bytearray(usbdev.BUILTIN_CDC.desc_cfg)
        desc_cfg = desc_cfg + self.HID_IAD + hid_iface
        desc_cfg[4] += 1
        struct.pack_into("<H", desc_cfg, 2, len(desc_cfg))
        usbdev.active(False)
        usbdev.builtin_driver = usbdev.BUILTIN_CDC
        usbdev.config(
            desc_dev=desc_dev,
            desc_cfg=bytes(desc_cfg),
            desc_strs={
                0: None,
                1: self._manufacturer,
                2: self._product,
                3: self._serial,
            },
            open_itf_cb=None,
            reset_cb=None,
            control_xfer_cb=self._on_control_xfer_cb,
            xfer_cb=self._on_xfer_cb,
        )
        usbdev.active(True)
        self._usbdev = usbdev

    def _on_xfer_cb(self, ep, res, num_bytes):
        """Transfer-complete callback invoked by the USB stack.

        Sets ``_xfer_done`` when the HID IN endpoint (0x83) finishes so that
        ``_wait`` can unblock.

        Args:
            ep: Endpoint address that completed the transfer.
            res: Result code from the USB stack.
            num_bytes: Number of bytes transferred.
        """
        if ep == 0x83:
            self._xfer_done = True

    def _on_control_xfer_cb(self, stage, request):
        """Control-transfer callback invoked by the USB stack for HID class requests.

        Handles GET_DESCRIPTOR (HID report descriptor), SET_IDLE / SET_PROTOCOL,
        and GET_PROTOCOL requests required by the HID class specification.

        Args:
            stage: Transfer stage (1 = SETUP, 3 = ACK).
            request: Raw 8-byte SETUP packet.

        Returns:
            bytes with the requested data, True to ACK with no data, or False
            to stall the request.
        """
        bmRequestType = request[0]
        bRequest = request[1]
        wValue = request[2] | (request[3] << 8)
        wIndex = request[4] | (request[5] << 8)
        wLength = request[6] | (request[7] << 8)

        if (
            bmRequestType == 0x81
            and bRequest == 0x06
            and (wValue >> 8) == 0x22
            and wIndex == 2
        ):
            return self.HID_REPORT_DESC[:wLength]

        if bmRequestType == 0x21 and bRequest in (0x0A, 0x0B):
            if stage in (1, 3):
                return True

        if bmRequestType == 0xA1 and bRequest == 0x03:
            return bytes([1])

        return False

    def _wait(self, timeout_ms=500):
        """Block until the previous HID transfer completes or the timeout expires.

        Args:
            timeout_ms: Maximum number of milliseconds to wait.

        Returns:
            True if the transfer completed within the timeout, False otherwise.
        """
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        while not self._xfer_done:
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                return False
        return True

    def send_key(self, modifier=0, keycode=0):
        """Send a single HID key-down report without releasing the key.

        Args:
            modifier: Modifier byte (e.g. ``MOD_LSHIFT``, ``MOD_LCTRL``).
            keycode: HID usage-ID of the key to press.
        """
        self._wait()
        self._xfer_done = False
        self._usbdev.submit_xfer(0x83, bytes([modifier, 0, keycode, 0, 0, 0, 0, 0]))

    def release(self):
        """Send an all-zeros HID report to release all currently held keys."""
        self._wait()
        self._xfer_done = False
        self._usbdev.submit_xfer(0x83, bytes(8))

    def press(self, modifier=0, keycode=0):
        """Press and immediately release a key.

        Args:
            modifier: Modifier byte (e.g. ``MOD_LSHIFT``, ``MOD_LCTRL``).
            keycode: HID usage-ID of the key to press.
        """
        self.send_key(modifier, keycode)
        self.release()

    def shortcut(self, modifier, keycode, delay_ms=100):
        """Press a key combination and wait briefly after releasing.

        Useful for triggering OS-level shortcuts where a short post-press delay
        ensures the host has time to process the keystroke.

        Args:
            modifier: Modifier byte (e.g. ``MOD_LGUI``, ``MOD_LCTRL``).
            keycode: HID usage-ID of the key to press.
            delay_ms: Milliseconds to sleep after the key is released.
        """
        self.press(modifier, keycode)
        time.sleep_ms(delay_ms)

    def type_string(self, s, delay_ms=50):
        """Type a string by pressing each character in sequence.

        Characters present in ``SHIFT_CHARS`` are automatically sent with the
        left-shift modifier. Characters not found in ``KEYMAP`` are silently
        skipped.

        Args:
            s: The string to type.
            delay_ms: Milliseconds to wait between each keystroke.
        """
        for ch in s:
            kc = self.KEYMAP.get(ch, 0)
            mod = self.MOD_LSHIFT if ch in self.SHIFT_CHARS else 0
            if kc:
                self.press(mod, kc)
                time.sleep_ms(delay_ms)


class USBMedia:
    """USB HID Consumer Control device for media key input.

    Builds a composite USB descriptor by appending a HID Consumer Control
    interface to the existing CDC configuration so both the REPL serial port
    and the media keys are available at the same time.
    """

    # Consumer Control HID report descriptor (16-bit usage, 1 usage per report)
    HID_REPORT_DESC = bytes(
        [
            0x05,
            0x0C,  # Usage Page (Consumer)
            0x09,
            0x01,  # Usage (Consumer Control)
            0xA1,
            0x01,  # Collection (Application)
            0x15,
            0x00,  # Logical Minimum (0)
            0x26,
            0xFF,
            0x03,  # Logical Maximum (1023)
            0x19,
            0x00,  # Usage Minimum (0)
            0x2A,
            0xFF,
            0x03,  # Usage Maximum (1023)
            0x75,
            0x10,  # Report Size (16)
            0x95,
            0x01,  # Report Count (1)
            0x81,
            0x00,  # Input (Data, Array, Absolute)
            0xC0,  # End Collection
        ]
    )

    HID_IAD = bytes([0x08, 0x0B, 0x02, 0x01, 0x03, 0x01, 0x01, 0x00])

    # Consumer Control usages (HID Usage Tables 1.3, Usage Page 0x0C)
    USAGE_PLAY_PAUSE = 0x00CD
    USAGE_NEXT_TRACK = 0x00B5
    USAGE_PREV_TRACK = 0x00B6
    USAGE_STOP = 0x00B7
    USAGE_VOL_UP = 0x00E9
    USAGE_VOL_DOWN = 0x00EA
    USAGE_MUTE = 0x00E2

    def __init__(
        self, manufacturer="MicroPython", product="Pico Media", serial="000002"
    ):
        """Create a USBMedia instance.

        Args:
            manufacturer: Manufacturer string reported in the USB device descriptor.
            product: Product string reported in the USB device descriptor.
            serial: Serial number string reported in the USB device descriptor.
        """
        self._usbdev = None
        self._xfer_done = True
        self._manufacturer = manufacturer
        self._product = product
        self._serial = serial

    def init(self):
        """Initialise and activate the composite CDC + HID Consumer Control device.

        Appends a HID Consumer Control interface to the built-in CDC descriptor,
        re-configures the USBDevice, and activates it. Must be called once
        before any key-sending methods are used.
        """
        hid_iface = bytes(
            [
                0x09,
                0x04,
                0x02,
                0x00,
                0x01,
                0x03,
                0x01,
                0x01,
                0x00,
                0x09,
                0x21,
                0x11,
                0x01,
                0x00,
                0x01,
                0x22,
                len(self.HID_REPORT_DESC),
                0x00,
                0x07,
                0x05,
                0x83,
                0x03,
                0x02,
                0x00,
                0x0A,
            ]
        )
        self._xfer_done = True
        usbdev = USBDevice()
        desc_dev = bytes(usbdev.BUILTIN_CDC.desc_dev)
        desc_cfg = bytearray(usbdev.BUILTIN_CDC.desc_cfg)
        desc_cfg = desc_cfg + self.HID_IAD + hid_iface
        desc_cfg[4] += 1
        struct.pack_into("<H", desc_cfg, 2, len(desc_cfg))
        usbdev.active(False)
        usbdev.builtin_driver = usbdev.BUILTIN_CDC
        usbdev.config(
            desc_dev=desc_dev,
            desc_cfg=bytes(desc_cfg),
            desc_strs={
                0: None,
                1: self._manufacturer,
                2: self._product,
                3: self._serial,
            },
            open_itf_cb=None,
            reset_cb=None,
            control_xfer_cb=self._on_control_xfer_cb,
            xfer_cb=self._on_xfer_cb,
        )
        usbdev.active(True)
        self._usbdev = usbdev

    def _on_xfer_cb(self, ep, res, num_bytes):
        """Transfer-complete callback; unblocks ``_wait`` when EP 0x83 finishes."""
        if ep == 0x83:
            self._xfer_done = True

    def _on_control_xfer_cb(self, stage, request):
        """Control-transfer callback for HID class requests."""
        bmRequestType = request[0]
        bRequest = request[1]
        wValue = request[2] | (request[3] << 8)
        wIndex = request[4] | (request[5] << 8)
        wLength = request[6] | (request[7] << 8)

        if (
            bmRequestType == 0x81
            and bRequest == 0x06
            and (wValue >> 8) == 0x22
            and wIndex == 2
        ):
            return self.HID_REPORT_DESC[:wLength]

        if bmRequestType == 0x21 and bRequest in (0x0A, 0x0B):
            if stage in (1, 3):
                return True

        if bmRequestType == 0xA1 and bRequest == 0x03:
            return bytes([1])

        return False

    def _wait(self, timeout_ms=500):
        """Block until the previous HID transfer completes or the timeout expires."""
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        while not self._xfer_done:
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                return False
        return True

    def press(self, usage):
        """Send a Consumer Control key press and immediately release it.

        Args:
            usage: HID Consumer Control usage ID (e.g. ``USAGE_PLAY_PAUSE``).
        """
        self._wait()
        self._xfer_done = False
        self._usbdev.submit_xfer(0x83, bytes([usage & 0xFF, (usage >> 8) & 0xFF]))
        self._wait()
        self._xfer_done = False
        self._usbdev.submit_xfer(0x83, bytes([0, 0]))
