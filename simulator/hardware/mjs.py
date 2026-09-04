import math as _math
import time as _time


class MJS:
    """Simulator shim for Picoware's native mjs module.

    This is intentionally a small evaluator for native-module smoke tests and
    simple scripts. It does not implement JavaScript language semantics.
    """

    def __init__(self):
        self._vars = {"log": print}

    def run(self, js_code):
        result = None
        for statement in _split_statements(str(js_code)):
            result = self._eval_statement(statement)
        return result

    def exec(self, path):
        with open(path, "r") as handle:
            return self.run(handle.read())

    def _eval_statement(self, statement):
        statement = statement.strip()
        if not statement:
            return None
        if statement.startswith("if"):
            return self._eval_if(statement)
        if statement.startswith("for"):
            return None
        if statement.startswith("let "):
            return self._assign(statement[4:])
        if "=" in statement and "==" not in statement:
            left, right = statement.split("=", 1)
            name = left.strip()
            if _is_identifier(name):
                return self._set_var(name, self._eval_expr(right.strip()))
        return self._eval_expr(statement)

    def _assign(self, assignment):
        name, expr = assignment.split("=", 1)
        return self._set_var(name.strip(), self._eval_expr(expr.strip()))

    def _set_var(self, name, value):
        self._vars[name] = value
        return value

    def _eval_if(self, statement):
        condition, body = _parse_if(statement)
        body = body.strip()
        while body.startswith("{") and body.endswith("}"):
            body = body[1:-1].strip()
        if self._eval_expr(condition):
            return self.run(body)
        return None

    def _eval_expr(self, expr):
        expr = expr.strip()
        if not expr:
            return None
        if expr.endswith(";"):
            expr = expr[:-1].strip()
        if expr.startswith("import(") and expr.endswith(")"):
            args = _parse_args(expr[len("import("):-1])
            if not args:
                raise ValueError("import expects a module name")
            return _import_module(args[0], args[1:])
        try:
            return _parse_literal(expr)
        except NotImplementedError:
            pass
        if _looks_like_call(expr):
            return self._eval_call(expr)
        if "." in expr:
            root, attr = expr.split(".", 1)
            return _get_member(self._eval_expr(root.strip()), attr.strip())
        if expr in self._vars:
            return self._vars[expr]
        raise NotImplementedError("unsupported simulator mjs expression: " + expr)

    def _eval_call(self, expr):
        target, arg_text = expr.split("(", 1)
        args = [_parse_arg(arg, self) for arg in _split_args(arg_text[:-1])]
        target = target.strip()
        if "." in target:
            root, method = target.rsplit(".", 1)
            value = _get_member(self._eval_expr(root.strip()), method.strip())
        else:
            value = self._vars.get(target)
        if not callable(value):
            raise TypeError("simulator mjs value is not callable: " + target)
        return value(*args)


class _Module(dict):
    def __getattr__(self, name):
        try:
            value = self[name]
            return value.get() if isinstance(value, _DynamicProperty) else value
        except KeyError:
            raise AttributeError(name)


class _DynamicProperty:
    def __init__(self, getter):
        self._getter = getter

    def get(self):
        return self._getter()


class _Pin:
    def __init__(self, pin_id=None, direction=None, pull=None):
        self.pin_id = pin_id
        self.direction = direction
        self.pull = pull
        self._value = 0

    def high(self):
        self._value = 1

    def low(self):
        self._value = 0

    def off(self):
        self.low()

    def on(self):
        self.high()

    def toggle(self):
        self._value = 0 if self._value else 1

    def value(self, new_value=None):
        if new_value is not None:
            self._value = 1 if int(new_value) else 0
        return self._value


class _UART:
    def __init__(self, uart_id=0, tx_pin=0, rx_pin=1, baud_rate=115000, timeout=2000):
        self.uartId = uart_id
        self.txPin = tx_pin
        self.rxPin = rx_pin
        self.baudRate = baud_rate
        self.timeout = timeout
        self.hasData = False
        self.has_data = False
        self.isSending = False
        self.is_sending = False
        self._buffer = []

    def clear(self):
        self._buffer = []

    def flush(self):
        self.isSending = False
        self.is_sending = False

    def println(self, data):
        self.write(str(data) + "\n")

    def readInto(self, buffer, length=1024):
        return 0

    def readLine(self):
        return ""

    def readSerialLine(self):
        return ""

    def write(self, data):
        self.isSending = True
        self.is_sending = True
        self._buffer.append(str(data))


class _WiFi:
    def __init__(self):
        self.deviceIp = "0.0.0.0"
        self.lastError = ""
        self.macAddress = "00:00:00:00:00:00"
        self.state = 0
        self.timeout = 10

    def connect(self, ssid, password="", sta_mode=True):
        self.state = 2
        self.deviceIp = "192.0.2.10"
        self.lastError = ""
        return True

    def connectAsync(self, ssid, password="", sta_mode=True):
        self.state = 1
        return True

    def disconnect(self):
        self.state = 0
        self.deviceIp = "0.0.0.0"

    def isConnected(self):
        return self.state == 2

    def reset(self):
        self.disconnect()

    def scan(self):
        return []


def _split_statements(js_code):
    statements = []
    start = 0
    quote = ""
    depth = 0
    brace_depth = 0
    i = 0
    while i < len(js_code):
        char = js_code[i]
        if quote:
            if char == "\\":
                i += 2
                continue
            if char == quote:
                quote = ""
        elif char in ("'", '"'):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
            if brace_depth == 0:
                statement = js_code[start : i + 1].strip()
                if statement:
                    statements.append(statement)
                start = i + 1
        elif char == ";" and depth == 0 and brace_depth == 0:
            statement = js_code[start:i].strip()
            if statement:
                statements.append(statement)
            start = i + 1
        i += 1
    statement = js_code[start:].strip()
    if statement:
        statements.append(statement)
    return statements


def _parse_if(statement):
    open_paren = statement.find("(")
    close_paren = statement.find(")")
    open_brace = statement.find("{", close_paren)
    close_brace = statement.rfind("}")
    if open_paren < 0 or close_paren < 0 or open_brace < 0 or close_brace < 0:
        raise NotImplementedError("unsupported simulator mjs if statement: " + statement)
    return statement[open_paren + 1 : close_paren].strip(), statement[open_brace + 1 : close_brace]


def _looks_like_call(expr):
    return expr.endswith(")") and "(" in expr


def _split_args(arg_text):
    if not arg_text.strip():
        return []
    args = []
    start = 0
    quote = ""
    depth = 0
    for i, char in enumerate(arg_text):
        if quote:
            if char == "\\":
                continue
            if char == quote:
                quote = ""
        elif char in ("'", '"'):
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            args.append(arg_text[start:i].strip())
            start = i + 1
    args.append(arg_text[start:].strip())
    return args


def _parse_args(arg_text):
    return [_parse_literal(arg) for arg in _split_args(arg_text)]


def _parse_arg(arg, mjs):
    arg = arg.strip()
    if arg in mjs._vars:
        return mjs._vars[arg]
    if _looks_like_call(arg) or "." in arg:
        return mjs._eval_expr(arg)
    return _parse_literal(arg)


def _parse_literal(expr):
    expr = expr.strip()
    if len(expr) >= 2 and expr[0] in ("'", '"') and expr[-1] == expr[0]:
        return expr[1:-1].replace("\\n", "\n")
    if expr in ("true", "True"):
        return True
    if expr in ("false", "False"):
        return False
    if expr in ("null", "undefined", "None"):
        return None
    if expr == "[]":
        return []
    try:
        if "." in expr:
            return float(expr)
        return int(expr)
    except ValueError:
        raise NotImplementedError("unsupported simulator mjs expression: " + expr)


def _get_member(value, attr):
    if isinstance(value, _Module):
        return getattr(value, attr)
    if isinstance(value, dict):
        if attr in value:
            return value[attr]
        raise AttributeError(attr)
    return getattr(value, attr)


def _is_identifier(value):
    if not value:
        return False
    return _is_identifier_start(value[0]) and all(_is_identifier_char(c) for c in value)


def _is_identifier_start(char):
    code = ord(char)
    return char == "_" or 65 <= code <= 90 or 97 <= code <= 122


def _is_identifier_char(char):
    code = ord(char)
    return _is_identifier_start(char) or 48 <= code <= 57


def _import_module(name, args):
    factories = {
        "audio": _audio_module,
        "bluetooth": _bluetooth_module,
        "buttons": _buttons_module,
        "draw": _draw_module,
        "http": _http_module,
        "input": _input_module,
        "math": _math_module,
        "pin": _pin_module,
        "psram": _psram_module,
        "settings": _settings_module,
        "storage": _storage_module,
        "system": _system_module,
        "time": _time_module,
        "uart": _uart_module,
        "websocket": _websocket_module,
        "wifi": _wifi_module,
    }
    if name not in factories:
        raise ImportError("simulator mjs module not implemented: " + str(name))
    return factories[name](*args)


def _audio_module():
    from audio import Audio, AudioNote

    player = Audio()

    def play_sound(sound):
        if not isinstance(sound, dict):
            raise TypeError("audio.playSound expects an object")
        note = AudioNote(
            _int_value(sound.get("leftFrequency", 0)),
            _int_value(sound.get("rightFrequency", 0)),
            _int_value(sound.get("duration", 0)),
        )
        player.play_note(note)

    return _Module(
        {
            "isPlaying": lambda: player.is_playing,
            "playMP3": player.play_mp3,
            "playSound": play_sound,
            "playWAV": player.play_wav,
            "stop": player.stop,
        }
    )


def _bluetooth_module():
    from picoware.system.bluetooth import Bluetooth

    bluetooth = Bluetooth()

    def connect(addr_type, addr, timeout_ms=10000, auto_discover=True):
        if isinstance(addr, str):
            compact = addr.replace(":", "").replace("-", "")
            addr = bytes(int(compact[i : i + 2], 16) for i in range(0, len(compact), 2))
        return bluetooth.connect(int(addr_type), addr, int(timeout_ms), bool(auto_discover))

    return _Module(
        {
            "macAddress": _DynamicProperty(lambda: bluetooth.mac_address),
            "connectedAddress": _DynamicProperty(lambda: bluetooth.connected_address),
            "isPairing": _DynamicProperty(lambda: bluetooth.is_pairing),
            "isScanning": _DynamicProperty(lambda: bluetooth.is_scanning),
            "isConnected": _DynamicProperty(lambda: bluetooth.is_connected),
            "isPeripheralConnected": _DynamicProperty(lambda: bluetooth.is_peripheral_connected),
            "passkey": _DynamicProperty(lambda: bluetooth.passkey),
            "services": _DynamicProperty(lambda: bluetooth.services),
            "characteristics": _DynamicProperty(lambda: bluetooth.characteristics),
            "advertise": bluetooth.advertise,
            "connect": connect,
            "decodeName": bluetooth.decode_name,
            "decodeServices": bluetooth.decode_services,
            "disconnect": bluetooth.disconnect,
            "discoverCharacteristics": bluetooth.discover_characteristics,
            "discoverServices": bluetooth.discover_services,
            "isDevicePaired": bluetooth.is_device_paired,
            "isUartReady": bluetooth.is_uart_ready,
            "loadPairedDevices": bluetooth.load_paired_devices,
            "onNotify": bluetooth.on_notify,
            "onScan": bluetooth.on_scan,
            "onWrite": bluetooth.on_write,
            "pair": bluetooth.pair,
            "passkeyReply": bluetooth.passkey_reply,
            "read": bluetooth.read,
            "register": bluetooth.register,
            "removePairedDevice": bluetooth.remove_paired_device,
            "savePairedDevice": bluetooth.save_paired_device,
            "scan": bluetooth.scan,
            "scanForUartDevices": bluetooth.scan_for_uart_devices,
            "scanStop": bluetooth.scan_stop,
            "send": bluetooth.send,
            "startPeripheral": bluetooth.start_peripheral,
            "stopPeripheral": bluetooth.stop_peripheral,
            "subscribe": bluetooth.subscribe,
            "write": bluetooth.write,
        }
    )


def _buttons_module():
    from picoware.system import buttons

    module = _Module()
    for name in dir(buttons):
        if name.startswith("BUTTON_") or name.startswith("KEY_"):
            module[name] = getattr(buttons, name)
    return module


def _draw_module():
    import lcd

    module = _Module()
    passthrough = (
        "char",
        "circle",
        "clear",
        "fill_circle",
        "fill_rectangle",
        "fill_round_rectangle",
        "fill_triangle",
        "line",
        "pixel",
        "rectangle",
        "text",
        "triangle",
    )
    for name in passthrough:
        js_name = _camel_name(name)
        if hasattr(lcd, name):
            module[js_name] = getattr(lcd, name)
        else:
            module[js_name] = lambda *args, **kwargs: None
    module["swap"] = getattr(lcd, "swap", lambda: None)
    return module


def _http_module():
    import http

    module = _Module()

    def request(url, method="GET", headers=None, payload=None, buffer_size=4096):
        if http.http_send_request(url, method, headers, payload):
            return http.http_get_http_response(None, buffer_size)
        return None

    module["getResponse"] = lambda buffer_size=4096: http.http_get_http_response(None, buffer_size)
    module["isFinished"] = http.http_is_finished
    module["request"] = request
    module["requestStart"] = http.http_send_request
    return module


def _input_module():
    from picoware.system import buttons

    button_chars = {
        buttons.BUTTON_SPACE: " ",
        buttons.BUTTON_0: "0",
        buttons.BUTTON_1: "1",
        buttons.BUTTON_2: "2",
        buttons.BUTTON_3: "3",
        buttons.BUTTON_4: "4",
        buttons.BUTTON_5: "5",
        buttons.BUTTON_6: "6",
        buttons.BUTTON_7: "7",
        buttons.BUTTON_8: "8",
        buttons.BUTTON_9: "9",
    }
    for i, char in enumerate("abcdefghijklmnopqrstuvwxyz"):
        button_chars[buttons.BUTTON_A + i] = char

    return _Module(
        {
            "battery": 87,
            "button": buttons.BUTTON_NONE,
            "wasCapitalized": False,
            "buttonToChar": lambda button: button_chars.get(int(button), ""),
            "read": lambda: buttons.BUTTON_NONE,
            "readNonBlocking": lambda: buttons.BUTTON_NONE,
            "reset": lambda: None,
        }
    )


def _math_module():
    return _Module(
        {
            "ceil": _math.ceil,
            "cos": _math.cos,
            "floor": _math.floor,
            "pow": pow,
            "random": lambda: 0.5,
            "sin": _math.sin,
            "sqrt": _math.sqrt,
        }
    )


def _pin_module(pin_id=None, direction=None, pull=None):
    return _Pin(pin_id, direction, pull)


def _psram_module():
    from picoware_psram import PSRAM

    psram = PSRAM()

    def read(addr, length):
        return psram.read(_int_value(addr), _int_value(length))

    def write(addr, data):
        return psram.write(_int_value(addr), data)

    return _Module(
        {
            "freeHeapSize": _DynamicProperty(psram.mem_free),
            "nextFreeAddr": _DynamicProperty(psram.get_next_free),
            "totalHeapSize": _DynamicProperty(psram.size),
            "usedHeapSize": _DynamicProperty(lambda: psram.size() - psram.mem_free()),
            "isReady": psram.is_ready,
            "size": psram.size,
            "test": psram.test,
            "read8": lambda addr: psram.read8(_int_value(addr)),
            "read16": lambda addr: psram.read16(_int_value(addr)),
            "read32": lambda addr: psram.read32(_int_value(addr)),
            "read": read,
            "read32Bulk": lambda addr, count: psram.read32_bulk(_int_value(addr), _int_value(count)),
            "write8": lambda addr, value: psram.write8(_int_value(addr), _int_value(value)),
            "write16": lambda addr, value: psram.write16(_int_value(addr), _int_value(value)),
            "write32": lambda addr, value: psram.write32(_int_value(addr), _int_value(value)),
            "write": write,
            "write32Bulk": lambda addr, values: psram.write32_bulk(_int_value(addr), values),
            "fill": lambda addr, value, length: psram.fill(_int_value(addr), _int_value(value), _int_value(length)),
            "memset": lambda addr, value, length: psram.memset(_int_value(addr), _int_value(value), _int_value(length)),
            "copy": lambda src, dst, length: psram.copy(_int_value(src), _int_value(dst), _int_value(length)),
            "memcpy": lambda dst, src, length: psram.memcpy(_int_value(dst), _int_value(src), _int_value(length)),
            "malloc": psram.malloc,
            "allocObject": psram.alloc_object,
            "collect": psram.collect,
            "getNextFree": psram.get_next_free,
            "memFree": psram.mem_free,
        }
    )


def _settings_module():
    defaults = {
        "anthropicApiKey": "",
        "darkMode": False,
        "debug": False,
        "deepseekApiKey": "",
        "exitButton": 5,
        "geminiApiKey": "",
        "gmtOffset": 0,
        "localUrl": "http://127.0.0.1:8080/v1/chat/completions",
        "lvglMode": False,
        "onscreenKeyboard": False,
        "openaiApiKey": "",
        "openApiKey": "",
        "screenBrightness": 100,
        "serverSettings": {"username": "", "password": ""},
        "themeColor": 0,
        "usbStream": False,
        "wifiSettings": {"ssid": "", "password": ""},
        "xaiApiKey": "",
    }
    return _Module(defaults)


def _storage_module():
    import sd_mp

    module = _Module()

    def read(path):
        return bytes(sd_mp.read(str(path))).decode()

    def read_chunk(path, offset, chunk_size):
        return bytes(sd_mp.read(str(path), int(offset), int(chunk_size))).decode()

    def size(path):
        return sd_mp.get_file_size(str(path))

    def write(path, data):
        return sd_mp.write(str(path), str(data).encode(), True)

    module["read"] = read
    module["readChunk"] = read_chunk
    module["size"] = size
    module["write"] = write
    return module


def _system_module():
    from picoware.system.system import System

    system = System()
    return _Module(
        {
            "boardId": system.board_id,
            "boardName": system.board_name,
            "deviceName": system.device_name,
            "freePsram": system.free_psram,
            "freeHeap": system.free_heap,
            "freq": system.freq,
            "hasAudio": system.has_audio,
            "hasPsram": system.has_psram,
            "hasSdCard": system.has_sd_card,
            "hasTouch": system.has_touch,
            "hasWifi": system.has_wifi,
            "isCircular": system.is_circular,
            "freeFlash": system.free_flash,
            "totalFlash": system.total_flash,
            "totalHeap": system.total_heap,
            "totalPsram": system.total_psram,
            "usedHeap": system.used_heap,
            "usedPsram": system.used_psram,
            "version": system.version,
            "bootloaderMode": system.bootloader_mode,
            "hardReset": system.hard_reset,
            "softReset": system.soft_reset,
        }
    )


def _time_module():
    return _Module(
        {
            "ticksMs": lambda: int(_time.time() * 1000),
            "ticksDiff": lambda a, b: int(a) - int(b),
            "sleepMs": lambda ms: _time.sleep(float(ms) / 1000),
        }
    )


def _uart_module(uart_id=0, tx_pin=0, rx_pin=1, baud_rate=115000, timeout=2000):
    return _UART(uart_id, tx_pin, rx_pin, baud_rate, timeout)


def _websocket_module():
    import websocket

    return _Module(
        {
            "start": websocket.http_websocket_start,
            "stop": websocket.http_websocket_stop,
            "isConnected": websocket.http_websocket_is_connected,
            "send": websocket.http_websocket_send,
            "getResponse": lambda buffer_size=2048: websocket.http_get_websocket_response(None, buffer_size),
        }
    )


def _wifi_module():
    return _WiFi()


def _int_value(value):
    if isinstance(value, str):
        return int(value, 0)
    return int(value)


def _camel_name(name):
    parts = name.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])
