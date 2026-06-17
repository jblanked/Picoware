import time

_frequency = 200000000


def freq(value=None):
    global _frequency
    if value is not None:
        _frequency = value
    return _frequency


def reset():
    raise SystemExit


def soft_reset():
    raise SystemExit


def bootloader():
    raise SystemExit


class Pin:
    IN = 0
    OUT = 1
    PULL_UP = 2
    PULL_DOWN = 1
    IRQ_FALLING = 4
    IRQ_RISING = 8

    def __init__(self, *args, **kwargs):
        self.id = args[0] if args else kwargs.get("id", None)
        self._handler = None
        self._value = int(kwargs.get("value", 0))
        self._mode = args[1] if len(args) > 1 else kwargs.get("mode", self.IN)
        self._pull = args[2] if len(args) > 2 else kwargs.get("pull", None)
        self._irq_trigger = None

    def irq(self, handler=None, trigger=None):
        self._handler = handler
        self._irq_trigger = trigger
        return None

    def value(self, value=None):
        if value is None:
            return self._value
        old = self._value
        self._value = int(value)
        changed = old != self._value
        if changed and self._handler:
            self._handler(self)
        return self._value

    def init(self, mode=-1, pull=-1, value=None):
        if mode != -1:
            self._mode = mode
        if pull != -1:
            self._pull = pull
        if value is not None:
            self.value(value)
        return None


class RTC:
    def datetime(self, value=None):
        if value is not None:
            return None
        now = time.localtime()
        return (now[0], now[1], now[2], now[6], now[3], now[4], now[5], 0)

    def deinit(self):
        return None


class UART:
    _endpoints = {}

    def __init__(self, *args, **kwargs):
        self.id = args[0] if args else kwargs.get("id", 0)
        self.name = kwargs.get("name", "uart{}".format(self.id))
        self._buffer = bytearray()
        self._tx = bytearray()
        self._handler = None
        self._initialized = True
        self._baudrate = kwargs.get("baudrate", kwargs.get("baud_rate", 115200))
        UART._endpoints[self.name] = self

    def init(self, *args, **kwargs):
        self._initialized = True
        if "baudrate" in kwargs:
            self._baudrate = kwargs["baudrate"]
        if "baud_rate" in kwargs:
            self._baudrate = kwargs["baud_rate"]
        return None

    def deinit(self):
        self._initialized = False
        return None

    def any(self):
        return len(self._buffer)

    def read(self, n=None):
        if n is None:
            n = len(self._buffer)
        data = self._buffer[:n]
        self._buffer = self._buffer[n:]
        return data

    def readinto(self, buf):
        data = self.read(len(buf))
        buf[: len(data)] = data
        return len(data)

    def readline(self):
        return self.read()

    def write(self, data):
        if isinstance(data, str):
            data = data.encode()
        self._tx.extend(data)
        _append_log("uart_{}.log".format(self.name), data)
        peer = UART._endpoints.get(self.name + ":rx")
        if peer is not None:
            peer.inject_rx(data)
        return len(data)

    def flush(self):
        return None

    def txdone(self):
        return True

    def irq(self, handler=None, trigger=None):
        self._handler = handler
        return None

    def inject_rx(self, data):
        if isinstance(data, str):
            data = data.encode()
        self._buffer.extend(data)
        _append_log("uart_{}_rx.log".format(self.name), data)
        if self._handler:
            self._handler(self)
        return len(data)

    def tx_buffer(self):
        return bytes(self._tx)

    @classmethod
    def endpoint(cls, name):
        endpoint = cls._endpoints.get(name)
        if endpoint is None:
            endpoint = cls(name=name)
        return endpoint


class I2S:
    RX = 0
    TX = 1
    MONO = 0
    STEREO = 1
    B16 = 16
    B32 = 32

    def __init__(self, *args, **kwargs):
        self._handler = None
        self._active = True
        self._phase = 0
        self._rate = kwargs.get("rate", 16000)
        self._bits = kwargs.get("bits", 16)
        self._format = kwargs.get("format", self.MONO)

    def init(self, *args, **kwargs):
        self._active = True
        return None

    def deinit(self):
        self._active = False
        return None

    def irq(self, handler=None):
        self._handler = handler
        return None

    def readinto(self, buf):
        if not self._active:
            return 0
        # Deterministic low-amplitude waveform.
        for i in range(len(buf)):
            self._phase = (self._phase + 1) & 0xFF
            buf[i] = 128 + ((self._phase % 32) - 16)
        if self._handler:
            self._handler(self)
        return len(buf)

    def write(self, data):
        if isinstance(data, str):
            data = data.encode()
        _append_log("i2s_tx.raw", data, binary=True)
        return len(data)


class PWM:
    def __init__(self, pin, freq=1000, duty_u16=0, duty_ns=0):
        self.pin = pin
        self._freq = int(freq)
        self._duty_u16 = int(duty_u16)
        self._duty_ns = int(duty_ns)
        self._active = True

    def freq(self, value=None):
        if value is None:
            return self._freq
        self._freq = int(value)
        return None

    def duty_u16(self, value=None):
        if value is None:
            return self._duty_u16
        self._duty_u16 = max(0, min(65535, int(value)))
        return None

    def duty_ns(self, value=None):
        if value is None:
            return self._duty_ns
        self._duty_ns = max(0, int(value))
        return None

    def deinit(self):
        self._active = False
        self._duty_u16 = 0
        self._duty_ns = 0
        return None

    def state(self):
        return {
            "freq": self._freq,
            "duty_u16": self._duty_u16,
            "duty_ns": self._duty_ns,
            "active": self._active,
        }


class USBDevice:
    class _BuiltinCDC:
        desc_dev = bytes((18, 1, 0, 2, 2, 0, 0, 64, 0xF4, 0x2E, 0x01, 0x00, 0, 1, 2, 3, 1, 1))
        desc_cfg = bytes((9, 2, 9, 0, 1, 1, 0, 0x80, 50))

    BUILTIN_CDC = _BuiltinCDC()

    def __init__(self):
        self._active = False
        self.builtin_driver = self.BUILTIN_CDC
        self.desc_dev = self.BUILTIN_CDC.desc_dev
        self.desc_cfg = self.BUILTIN_CDC.desc_cfg
        self.desc_strs = {}
        self.open_itf_cb = None
        self.reset_cb = None
        self.control_xfer_cb = None
        self.xfer_cb = None
        self.transfers = []

    def active(self, value=None):
        if value is None:
            return self._active
        self._active = bool(value)
        if self._active and self.reset_cb:
            self.reset_cb()
        return None

    def config(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        return None

    def submit_xfer(self, ep, data):
        data = bytes(data)
        self.transfers.append((ep, data))
        try:
            import sim_runtime

            path = sim_runtime.sd_root + "/picoware/usb_hid.log"
            sim_runtime.mkdir_p(path.rsplit("/", 1)[0])
            with open(path, "a") as handle:
                handle.write("{}:{}\n".format(ep, data.hex()))
        except Exception:
            pass
        if self.xfer_cb:
            self.xfer_cb(ep, 0, len(data))
        return True

    def control_xfer(self, stage, request):
        if self.control_xfer_cb:
            return self.control_xfer_cb(stage, request)
        return False


def _append_log(name, data, binary=False):
    try:
        import sim_runtime

        path = sim_runtime.sd_root + "/picoware/" + name
        sim_runtime.mkdir_p(path.rsplit("/", 1)[0])
        mode = "ab" if binary else "a"
        with open(path, mode) as handle:
            if binary:
                handle.write(data)
            else:
                try:
                    text = data.decode()
                except AttributeError:
                    text = str(data)
                except Exception:
                    text = repr(data)
                handle.write(text)
    except Exception:
        pass
