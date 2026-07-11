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
        if self.id in (11, 20, 21):
            try:
                import sim_runtime

                sim_runtime.register_touch_callback(handler)
            except Exception:
                pass
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


class I2C:
    _devices = {}

    def __init__(self, id=0, *, scl=None, sda=None, freq=400000, **kwargs):
        self.id = id
        self.scl = scl
        self.sda = sda
        self.freq = int(freq)
        self._active = True

    @classmethod
    def set_device(cls, addr, data=b""):
        cls._devices[int(addr)] = bytearray(data)

    def init(self, *, scl=None, sda=None, freq=400000, **kwargs):
        if scl is not None:
            self.scl = scl
        if sda is not None:
            self.sda = sda
        self.freq = int(freq)
        self._active = True
        return None

    def deinit(self):
        self._active = False
        return None

    def scan(self):
        return sorted(I2C._devices.keys())

    def writeto(self, addr, buf, stop=True):
        data = bytes(buf)
        I2C._devices[int(addr)] = bytearray(data)
        return len(data)

    def readfrom(self, addr, nbytes, stop=True):
        data = I2C._devices.get(int(addr), bytearray())
        out = bytes(data[: int(nbytes)])
        if len(out) < int(nbytes):
            out += b"\x00" * (int(nbytes) - len(out))
        return out

    def readfrom_into(self, addr, buf, stop=True):
        data = self.readfrom(addr, len(buf), stop)
        buf[: len(data)] = data
        return None

    def writeto_mem(self, addr, memaddr, buf, *, addrsize=8):
        addr = int(addr)
        memaddr = int(memaddr)
        data = bytes(buf)
        device = I2C._devices.setdefault(addr, bytearray())
        end = memaddr + len(data)
        if len(device) < end:
            device.extend(b"\x00" * (end - len(device)))
        device[memaddr:end] = data
        return None

    def readfrom_mem(self, addr, memaddr, nbytes, *, addrsize=8):
        addr = int(addr)
        memaddr = int(memaddr)
        data = I2C._devices.get(addr, bytearray())
        out = bytes(data[memaddr : memaddr + int(nbytes)])
        if len(out) < int(nbytes):
            out += b"\x00" * (int(nbytes) - len(out))
        return out

    def readfrom_mem_into(self, addr, memaddr, buf, *, addrsize=8):
        data = self.readfrom_mem(addr, memaddr, len(buf), addrsize=addrsize)
        buf[: len(data)] = data
        return None


class SPI:
    MSB = 0
    LSB = 1

    def __init__(
        self,
        id=0,
        baudrate=1000000,
        polarity=0,
        phase=0,
        bits=8,
        firstbit=MSB,
        sck=None,
        mosi=None,
        miso=None,
        **kwargs
    ):
        self.id = id
        self._rx = bytearray()
        self._tx = bytearray()
        self.init(
            baudrate=baudrate,
            polarity=polarity,
            phase=phase,
            bits=bits,
            firstbit=firstbit,
            sck=sck,
            mosi=mosi,
            miso=miso,
        )

    def init(self, **kwargs):
        self.baudrate = int(kwargs.get("baudrate", getattr(self, "baudrate", 1000000)))
        self.polarity = int(kwargs.get("polarity", getattr(self, "polarity", 0)))
        self.phase = int(kwargs.get("phase", getattr(self, "phase", 0)))
        self.bits = int(kwargs.get("bits", getattr(self, "bits", 8)))
        self.firstbit = kwargs.get("firstbit", getattr(self, "firstbit", self.MSB))
        self.sck = kwargs.get("sck", getattr(self, "sck", None))
        self.mosi = kwargs.get("mosi", getattr(self, "mosi", None))
        self.miso = kwargs.get("miso", getattr(self, "miso", None))
        self._active = True
        return None

    def deinit(self):
        self._active = False
        return None

    def write(self, buf):
        data = bytes(buf)
        self._tx.extend(data)
        self._rx.extend(data)
        return None

    def read(self, nbytes, write=0x00):
        nbytes = int(nbytes)
        out = bytes(self._rx[:nbytes])
        self._rx = self._rx[nbytes:]
        if len(out) < nbytes:
            out += bytes((int(write) & 0xFF,)) * (nbytes - len(out))
        return out

    def readinto(self, buf, write=0x00):
        data = self.read(len(buf), write)
        buf[: len(data)] = data
        return None

    def write_readinto(self, write_buf, read_buf):
        data = bytes(write_buf)
        self._tx.extend(data)
        size = min(len(data), len(read_buf))
        read_buf[:size] = data[:size]
        if len(read_buf) > size:
            read_buf[size:] = b"\x00" * (len(read_buf) - size)
        return None


class ADC:
    _values = {}

    def __init__(self, pin):
        self.pin = pin

    @classmethod
    def set_value(cls, pin, value):
        key = getattr(pin, "id", pin)
        cls._values[key] = max(0, min(65535, int(value)))

    def read_u16(self):
        key = getattr(self.pin, "id", self.pin)
        return ADC._values.get(key, 32768)


class Timer:
    ONE_SHOT = 0
    PERIODIC = 1
    _timers = []

    def __init__(self, id=-1):
        self.id = id
        self._active = False
        self._period = 0
        self._mode = self.ONE_SHOT
        self._callback = None
        self._next_ms = 0
        Timer._timers.append(self)

    def init(self, *, mode=PERIODIC, period=-1, freq=-1, callback=None):
        if period < 0 and freq and freq > 0:
            period = max(1, int(1000 / int(freq)))
        self._period = max(1, int(period if period >= 0 else 1))
        self._mode = mode
        self._callback = callback
        self._next_ms = _ticks_ms() + self._period
        self._active = True
        return None

    def deinit(self):
        self._active = False
        return None

    def _poll(self, now=None):
        if not self._active:
            return False
        if now is None:
            now = _ticks_ms()
        if now < self._next_ms:
            return False
        if self._callback:
            self._callback(self)
        if self._mode == self.ONE_SHOT:
            self._active = False
        else:
            self._next_ms = now + self._period
        return True

    @classmethod
    def poll_all(cls):
        now = _ticks_ms()
        count = 0
        for timer in list(cls._timers):
            if timer._poll(now):
                count += 1
        return count


class WDT:
    _instances = []

    def __init__(self, id=0, timeout=5000):
        self.id = id
        self.timeout = int(timeout)
        self._last_feed = _ticks_ms()
        self._expired = False
        WDT._instances.append(self)

    def feed(self):
        self._last_feed = _ticks_ms()
        self._expired = False
        return None

    def expired(self):
        if not self._expired and _ticks_ms() - self._last_feed > self.timeout:
            self._expired = True
        return self._expired

    @classmethod
    def check_all(cls):
        return [wdt for wdt in cls._instances if wdt.expired()]


def _ticks_ms():
    try:
        return time.ticks_ms()
    except AttributeError:
        return int(time.time() * 1000)


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
        self.control_transfers = []
        self._open_interfaces = set()
        self._host_packets = {}

    def active(self, value=None):
        if value is None:
            return self._active
        self._active = bool(value)
        if self._active and self.reset_cb:
            self.reset_cb()
        if not self._active:
            self._open_interfaces.clear()
            self._host_packets.clear()
        return None

    def config(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        return None

    def submit_xfer(self, ep, data):
        if not self._active:
            return False
        data = bytes(data)
        entry = {
            "ep": ep,
            "data": data,
            "direction": "in" if ep & 0x80 else "out",
            "type": self._classify_xfer(ep, data),
            "status": 0,
        }
        self.transfers.append(entry)
        try:
            import sim_runtime

            path = sim_runtime.sd_root + "/picoware/usb_hid.log"
            sim_runtime.mkdir_p(path.rsplit("/", 1)[0])
            with open(path, "a") as handle:
                handle.write("{}:{}:{}\n".format(ep, entry["type"], data.hex()))
        except Exception:
            pass
        if self.xfer_cb:
            self.xfer_cb(ep, 0, len(data))
        return True

    def control_xfer(self, stage, request):
        request = bytes(request)
        self.control_transfers.append((stage, request))
        if self.control_xfer_cb:
            return self.control_xfer_cb(stage, request)
        return False

    def open_itf(self, itf_num=0):
        self._open_interfaces.add(itf_num)
        if self.open_itf_cb:
            return self.open_itf_cb(itf_num)
        return True

    def host_open_interface(self, itf_num=0):
        return self.open_itf(itf_num)

    def host_control(self, stage, request):
        return self.control_xfer(stage, request)

    def host_receive(self, ep, data):
        data = bytes(data)
        self._host_packets.setdefault(ep, []).append(data)
        if self.xfer_cb:
            self.xfer_cb(ep, 0, len(data))
        return True

    def recv_xfer(self, ep, size=None):
        queue = self._host_packets.get(ep, [])
        if not queue:
            return b""
        data = queue.pop(0)
        if size is not None:
            return data[:size]
        return data

    def transfer_log(self, ep=None):
        if ep is None:
            return tuple(self.transfers)
        return tuple(item for item in self.transfers if item["ep"] == ep)

    def last_transfer(self, ep=None):
        transfers = self.transfer_log(ep)
        if not transfers:
            return None
        return transfers[-1]

    def clear_transfers(self):
        self.transfers = []
        self.control_transfers = []
        self._host_packets = {}
        return None

    def opened_interfaces(self):
        return tuple(sorted(self._open_interfaces))

    def _classify_xfer(self, ep, data):
        if ep & 0x80:
            if len(data) == 8:
                return "hid-keyboard"
            if len(data) == 2:
                return "hid-consumer"
            return "device-in"
        return "host-out"


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
