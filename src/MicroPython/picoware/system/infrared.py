"""Infrared signals handling for Picoware."""
try:
    from micropython import const
except ImportError:
    def const(value):
        return value

_FILE_TYPE = "IR signals file"
_LIBRARY_FILE_TYPE = "IR library file"
_FILE_VERSION = const(1)
_MAX_TIMINGS = const(1024)


class RemoteFormatError(ValueError):
    """Raised when an infrared remote file is invalid."""


def _required(fields, key):
    value = fields.get(key)
    if value is None or not value.strip():
        raise RemoteFormatError("missing infrared field: {}".format(key))
    return value.strip()


def _parse_hex_value(value):
    parts = value.replace(",", " ").split()
    if not parts:
        raise RemoteFormatError("empty hexadecimal value")

    if len(parts) == 1:
        token = parts[0]
        if token.lower().startswith("0x"):
            token = token[2:]
        try:
            return int(token, 16)
        except ValueError as error:
            raise RemoteFormatError("invalid hexadecimal value: {}".format(value)) from error

    result = 0
    for index, token in enumerate(parts):
        if token.lower().startswith("0x"):
            token = token[2:]
        try:
            byte = int(token, 16)
        except ValueError as error:
            raise RemoteFormatError("invalid hexadecimal byte: {}".format(token)) from error
        if byte < 0 or byte > 0xFF:
            raise RemoteFormatError("hexadecimal byte out of range: {}".format(token))
        result |= byte << (index * 8)
    return result


def _parse_timings(value):
    try:
        timings = [int(item, 10) for item in value.replace(",", " ").split()]
    except ValueError as error:
        raise RemoteFormatError("invalid raw timing data") from error

    if not timings or len(timings) > _MAX_TIMINGS:
        raise RemoteFormatError("raw timing count must be between 1 and {}".format(_MAX_TIMINGS))
    if any(item <= 0 for item in timings):
        raise RemoteFormatError("raw timings must be positive")
    return tuple(timings)


def _parse_frequency(value):
    try:
        frequency = int(value, 10)
    except ValueError as error:
        raise RemoteFormatError("invalid carrier frequency") from error
    if frequency <= 0:
        raise RemoteFormatError("carrier frequency must be positive")
    return frequency


def _parse_duty_cycle(value):
    try:
        duty_cycle = float(value)
    except ValueError as error:
        raise RemoteFormatError("invalid carrier duty cycle") from error
    if not 0 < duty_cycle <= 1:
        raise RemoteFormatError("carrier duty cycle must be between 0 and 1")
    return duty_cycle


def _default_frequency(protocol):
    return {
        "RC5": 36000,
        "RC5X": 36000,
        "RC6": 36000,
        "SIRC": 40000,
        "SIRC15": 40000,
        "SIRC20": 40000,
    }.get(protocol.upper(), 38000)


def _validate_header(header):
    file_type = header.get("filetype", "").lower()
    if file_type not in (_FILE_TYPE.lower(), _LIBRARY_FILE_TYPE.lower()):
        raise RemoteFormatError("not an infrared signals file")
    try:
        version = int(header.get("version", ""), 10)
    except ValueError as error:
        raise RemoteFormatError("missing or invalid infrared file version") from error
    if version != _FILE_VERSION:
        raise RemoteFormatError("unsupported infrared file version: {}".format(version))
    return header["filetype"]


class Signal:
    """One parsed or raw signal from a Flipper ``.ir`` file."""

    __slots__ = (
        "name",
        "signal_type",
        "protocol",
        "address",
        "command",
        "toggle",
        "frequency",
        "duty_cycle",
        "data",
    )

    def __init__(self, fields):
        self.name = _required(fields, "name")
        self.signal_type = _required(fields, "type").lower()
        self.protocol = None
        self.address = 0
        self.command = 0
        self.toggle = 0
        self.frequency = 38000
        self.duty_cycle = 0.33
        self.data = ()

        if self.signal_type == "parsed":
            self.protocol = _required(fields, "protocol")
            self.address = _parse_hex_value(_required(fields, "address"))
            self.command = _parse_hex_value(_required(fields, "command"))
            if fields.get("toggle"):
                self.toggle = int(fields["toggle"], 10)
            self.frequency = _default_frequency(self.protocol)
        elif self.signal_type == "raw":
            self.frequency = _parse_frequency(_required(fields, "frequency"))
            self.duty_cycle = _parse_duty_cycle(_required(fields, "duty_cycle"))
            self.data = _parse_timings(_required(fields, "data"))
        else:
            raise RemoteFormatError("unsupported infrared signal type: {}".format(self.signal_type))

    @property
    def is_raw(self):
        """Return True when the signal contains raw timings."""
        return self.signal_type == "raw"

    @property
    def is_parsed(self):
        """Return True when the signal has a known protocol."""
        return self.signal_type == "parsed"


def parse_ir(text):
    """Parse a Flipper ``.ir`` remote and return its signals."""
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    if not isinstance(text, str):
        raise TypeError("infrared file must be text or bytes")

    header = {}
    fields = None
    signals = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if fields:
                signals.append(Signal(fields))
                fields = None
            continue
        if ":" not in line:
            raise RemoteFormatError("invalid infrared line: {}".format(line))

        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if fields is None:
            if key in ("filetype", "version"):
                header[key] = value
            elif key == "name":
                fields = {"name": value}
            continue

        if key == "name":
            signals.append(Signal(fields))
            fields = {"name": value}
            continue
        if key == "data" and key in fields:
            fields[key] = fields[key] + " " + value
        else:
            fields[key] = value

    if fields:
        signals.append(Signal(fields))

    _validate_header(header)
    if not signals:
        raise RemoteFormatError("infrared file contains no signals")
    return signals


class RemoteFile:
    """A remote loaded ``.ir`` file."""

    __slots__ = ("path", "_signals", "_records", "_storage", "_file_type")

    def __init__(self, path, text=None, storage=None, file_size=None):
        self.path = path
        self._storage = storage
        self._records = None
        self._file_type = _FILE_TYPE
        if text is not None:
            self._signals = tuple(parse_ir(text))
        elif storage is not None:
            self._signals, self._records, self._file_type = self._index_storage(file_size)
        else:
            raise TypeError("RemoteFile requires text or storage")

    def _index_storage(self, file_size):
        if file_size is None:
            file_size = self._storage.size(self.path)
        if file_size <= 0:
            raise RemoteFormatError("infrared file is empty")

        header = {}
        records = []
        current_name = None
        current_start = None
        pending = b""
        pending_start = 0
        read_offset = 0
        chunk_size = 2048

        while read_offset < file_size:
            chunk = self._storage.read(
                self.path,
                "rb",
                read_offset,
                min(chunk_size, file_size - read_offset),
            )
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            if not chunk:
                break
            if not pending:
                pending_start = read_offset
            pending += chunk
            read_offset += len(chunk)

            while True:
                newline = pending.find(b"\n")
                if newline < 0:
                    break
                line_start = pending_start
                line = pending[:newline].strip()
                pending = pending[newline + 1 :]
                pending_start = line_start + newline + 1
                current_name, current_start = self._index_line(
                    line,
                    line_start,
                    header,
                    records,
                    current_name,
                    current_start,
                )

        if pending:
            current_name, current_start = self._index_line(
                pending,
                pending_start,
                header,
                records,
                current_name,
                current_start,
            )

        if current_start is not None:
            records.append((current_name, current_start, file_size))
        file_type = _validate_header(header)
        if not records:
            raise RemoteFormatError("infrared file contains no signals")
        return None, tuple(records), file_type

    @staticmethod
    def _index_line(
        line,
        line_start,
        header,
        records,
        current_name,
        current_start,
    ):
        if not line:
            return current_name, current_start
        if line.startswith(b"#"):
            if current_start is not None:
                records.append((current_name, current_start, line_start))
            return None, None
        if b":" not in line:
            return current_name, current_start

        key, value = line.split(b":", 1)
        key = key.strip().lower()
        value = value.strip()
        if current_start is None and key in (b"filetype", b"version"):
            header[key.decode("ascii")] = value.decode("utf-8")
            return current_name, current_start
        if key == b"name":
            if current_start is not None:
                records.append((current_name, current_start, line_start))
            return value.decode("utf-8"), line_start
        return current_name, current_start

    def _read_record(self, record):
        _, start, end = record
        text = self._storage.read(self.path, "rb", start, end - start)
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        prefix = "Filetype: {}\nVersion: {}\n#\n".format(
            self._file_type,
            _FILE_VERSION,
        )
        signals = parse_ir(prefix + text)
        return signals[0]

    @property
    def signals(self):
        """Return all signals, loading lazy records on first access."""
        if self._signals is None:
            self._signals = tuple(
                self._read_record(record) for record in self._records
            )
        return self._signals

    @property
    def names(self):
        """Return the signal names in file order."""
        if self._records is not None:
            return tuple(record[0] for record in self._records)
        return tuple(signal.name for signal in self._signals)

    def get(self, name_or_index=0):
        """Return a signal by name or zero-based index."""
        if isinstance(name_or_index, int):
            try:
                if self._records is not None:
                    return self._read_record(self._records[name_or_index])
                return self._signals[name_or_index]
            except IndexError as error:
                raise KeyError(name_or_index) from error
        for index, name in enumerate(self.names):
            if name == name_or_index:
                return self.get(index)
        raise KeyError(name_or_index)

    def __getitem__(self, name_or_index):
        return self.get(name_or_index)

    def find_all(self, name):
        """Return every signal with a matching name."""
        return tuple(self.get(index) for index, signal_name in enumerate(self.names) if signal_name == name)

    def __len__(self):
        return len(self._records) if self._records is not None else len(self._signals)

    def __iter__(self):
        for index in range(len(self)):
            yield self.get(index)


class RemoteLibrary:
    """Discover and load Flipper-compatible remotes from SD storage."""

    def __init__(self, storage, root="infrared"):
        self.storage = storage
        self.root = root.rstrip("/") or "/"

    def _resolve(self, path):
        if path.startswith("/"):
            return path
        return self.root.rstrip("/") + "/" + path

    def _read(self, path):
        content = self.storage.read(path, "r")
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        if content:
            return content

    def load(self, path):
        """Load a remote by absolute path or filename under ``root``.""" 
        resolved = self._resolve(path)
        file_size = self.storage.size(resolved)
        if file_size:
            return RemoteFile(resolved, storage=self.storage, file_size=file_size)
        return RemoteFile(resolved, self._read(resolved), storage=self.storage)

    def _walk(self, path, result):
        entries = self.storage.listdir(path)
        for entry in entries:
            if not isinstance(entry, str):
                entry = entry.get("filename", "")
            if not entry or entry in (".", "..") or entry.startswith("."):
                continue
            child = path.rstrip("/") + "/" + entry
            if self.storage.is_directory(child):
                self._walk(child, result)
            elif entry.lower().endswith(".ir"):
                result.append(child)

    def list_files(self):
        """Return all ``.ir`` files below ``root``."""
        result = []
        self._walk(self.root, result)
        result.sort()
        return result

    def save_raw(
        self,
        path,
        name,
        timings,
        frequency=38000,
        duty_cycle=0.33,
    ):
        """Write one captured raw signal in Flipper format."""
        path = self._resolve(path)
        timings = tuple(timings)
        if not timings or len(timings) > _MAX_TIMINGS:
            raise ValueError("invalid raw timing count")
        if any(int(item) <= 0 for item in timings):
            raise ValueError("raw timings must be positive")
        self._ensure_parent_dirs(path, self.storage)
        text = "Filetype: {}\nVersion: {}\n#\n".format(_FILE_TYPE, _FILE_VERSION)
        text += "name: {}\ntype: raw\nfrequency: {}\nduty_cycle: {:.6f}\ndata: {}\n".format(
            name,
            int(frequency),
            float(duty_cycle),
            " ".join(str(int(item)) for item in timings),
        )

        if not self.storage.write(path, text, "w"):
            raise OSError("unable to write infrared remote: {}".format(path))

        return RemoteFile(path, text, storage=self.storage)

    def _ensure_parent_dirs(self, path, storage):
        """Create missing SD directories before writing a remote."""
        parent = path.rsplit("/", 1)[0]
        if not parent:
            return

        current = ""
        for part in parent.strip("/").split("/"):
            if not part:
                continue
            current += "/" + part
            if storage.is_directory(current):
                continue
            if not storage.mkdir(current) and not storage.is_directory(current):
                raise OSError("unable to create infrared directory: {}".format(current))
        return


def _split_raw_timings(timings, max_timing):
    """Split long alternating timings into explicit same-level chunks."""
    if max_timing <= 0:
        raise ValueError("max_timing must be positive")
    durations = []
    levels = []
    level = True
    for timing in timings:
        remaining = int(timing)
        while remaining > max_timing:
            durations.append(max_timing)
            levels.append(level)
            remaining -= max_timing
        durations.append(remaining)
        levels.append(level)
        level = not level
    if len(timings) & 1:
        durations.append(1)
        levels.append(False)
    return tuple(durations), tuple(levels)


def _default_tx_pin():
    from machine import Pin
    from picoware.system.boards import BOARD_ID, BOARD_CARDPUTER, BOARD_FLIPPER_ZERO

    if BOARD_ID == BOARD_CARDPUTER:
        return Pin(44, Pin.OUT, value=0)
    if BOARD_ID == BOARD_FLIPPER_ZERO:
        try:
            return Pin.board.IR_TX
        except AttributeError:
            return Pin.cpu.B9
    raise ValueError("no built-in infrared transmitter on this board")


def _default_rx_pin():
    from machine import Pin
    from picoware.system.boards import BOARD_ID, BOARD_FLIPPER_ZERO

    if BOARD_ID != BOARD_FLIPPER_ZERO:
        raise ValueError("this board has no built-in infrared receiver")
    try:
        return Pin(Pin.board.IR_RX, Pin.IN)
    except AttributeError:
        return Pin(Pin.cpu.A0, Pin.IN)


def _protocol_encoder(signal, pin, verbose):
    protocol = signal.protocol.upper()
    if protocol == "NEC":
        from picoware.system.drivers.ir_tx.nec import NEC

        return NEC(pin, signal.frequency, verbose)
    if protocol == "NECEXT":
        from picoware.system.drivers.ir_tx.nec import NEC_EXT

        return NEC_EXT(pin, signal.frequency, verbose)
    if protocol == "SAMSUNG32":
        from picoware.system.drivers.ir_tx.nec import SAMSUNG32

        return SAMSUNG32(pin, signal.frequency, verbose)
    if protocol in ("SIRC", "SIRC15", "SIRC20"):
        from picoware.system.drivers.ir_tx.sony import SONY_12, SONY_15, SONY_20

        return {
            "SIRC": SONY_12,
            "SIRC15": SONY_15,
            "SIRC20": SONY_20,
        }[protocol](pin, signal.frequency, verbose)
    if protocol in ("RC5", "RC5X"):
        from picoware.system.drivers.ir_tx.philips import RC5

        return RC5(pin, signal.frequency, verbose)
    if protocol == "RC6":
        from picoware.system.drivers.ir_tx.philips import RC6_M0

        return RC6_M0(pin, signal.frequency, verbose)
    if protocol == "MCE":
        from picoware.system.drivers.ir_tx.mce import MCE

        return MCE(pin, signal.frequency, verbose)
    raise ValueError("parsed infrared protocol is not supported: {}".format(signal.protocol))


class InfraredTransmitter:
    """Transmit parsed or raw signals using the current board's IR output."""

    def __init__(self, pin=None, verbose=False):
        self.pin = _default_tx_pin() if pin is None else pin
        self.verbose = verbose

    def _wait(self, transmitter):
        from time import sleep_ms

        while transmitter.busy():
            sleep_ms(1)

    def _send_raw(self, signal, repeats):
        from picoware.system.drivers.ir_tx import Player
        from picoware.system.boards import BOARD_ID, BOARD_CARDPUTER, BOARD_FLIPPER_ZERO

        if BOARD_ID == BOARD_CARDPUTER:
            timings, levels = _split_raw_timings(signal.data, 32767)
        elif BOARD_ID == BOARD_FLIPPER_ZERO:
            timings, levels = _split_raw_timings(signal.data, 65535)
        else:
            timings = list(signal.data)
            if len(timings) & 1:
                timings.append(1)
            if any(item > 65535 for item in timings):
                raise ValueError("raw timing exceeds transmitter limit of 65535 us")
            levels = None

        player = Player(
            self.pin,
            signal.frequency,
            self.verbose,
            len(timings) + 1,
            int(signal.duty_cycle * 100),
        )
        try:
            for _ in range(repeats):
                player.play(timings, levels)
                self._wait(player)
        finally:
            player.deinit()

    def send(self, signal, repeats=1):
        """Transmit a signal one or more times."""
        if not isinstance(signal, Signal):
            raise TypeError("send expects an infrared Signal")
        repeats = int(repeats)
        if repeats < 1:
            raise ValueError("repeats must be positive")
        if signal.is_raw:
            self._send_raw(signal, repeats)
            return

        transmitter = _protocol_encoder(signal, self.pin, self.verbose)
        protocol = signal.protocol.upper()
        if protocol == "SIRC20":
            address = signal.address & 0x1F
            extended = (signal.address >> 5) & 0xFF
        else:
            address = signal.address
            extended = signal.toggle
        try:
            for _ in range(repeats):
                transmitter.transmit(address, signal.command, extended, True)
                self._wait(transmitter)
        finally:
            transmitter.deinit()


class InfraredReceiver:
    """Decode one supported protocol from the current board's IR input."""

    def __init__(self, protocol="NEC", callback=None, pin=None):
        from picoware.system.drivers.ir_rx.mce import MCE
        from picoware.system.drivers.ir_rx.nec import NEC_8, NEC_16, SAMSUNG
        from picoware.system.drivers.ir_rx.philips import RC5_IR, RC6_M0
        from picoware.system.drivers.ir_rx.sony import SONY_12, SONY_15, SONY_20

        decoder_classes = {
            "NEC": NEC_8,
            "NECEXT": NEC_16,
            "SAMSUNG32": SAMSUNG,
            "SIRC": SONY_12,
            "SIRC15": SONY_15,
            "SIRC20": SONY_20,
            "RC5": RC5_IR,
            "RC5X": RC5_IR,
            "RC6": RC6_M0,
            "MCE": MCE,
        }
        key = protocol.upper()
        try:
            decoder_class = decoder_classes[key]
        except KeyError as error:
            raise ValueError("unsupported infrared receive protocol: {}".format(protocol)) from error

        self.pin = _default_rx_pin() if pin is None else pin
        self.protocol = protocol
        self._decoder = decoder_class(self.pin, callback or (lambda *_: None))

    def error_function(self, callback):
        """Set the decoder error callback."""
        self._decoder.error_function(callback)

    def close(self):
        """Stop decoding and release the input interrupt."""
        self._decoder.close()


class Infrared:
    """High-level SD remote library and transmitter facade."""

    __slots__ = ("library", "_tx_pin", "_verbose", "_transmitter")

    def __init__(self, storage, root="infrared", tx_pin=None, verbose=False):
        self.library = RemoteLibrary(storage, root)
        self._tx_pin = tx_pin
        self._verbose = verbose
        self._transmitter = None

    @property
    def transmitter(self):
        """Return the lazily-created transmitter."""
        if self._transmitter is None:
            self._transmitter = InfraredTransmitter(self._tx_pin, self._verbose)
        return self._transmitter

    def load(self, path):
        """Load a remote from SD storage."""
        return self.library.load(path)

    def list_files(self):
        """List remote files below the configured SD root."""
        return self.library.list_files()

    def send(self, remote, name_or_index=0, repeats=1):
        """Send a signal, or a named signal from a loaded remote."""
        if isinstance(remote, RemoteFile):
            signal = remote.get(name_or_index)
        elif isinstance(remote, Signal):
            signal = remote
        elif isinstance(remote, str):
            signal = self.load(remote).get(name_or_index)
        else:
            raise TypeError("send expects a Signal, RemoteFile, or path")
        self.transmitter.send(signal, repeats)

    def receiver(self, protocol="NEC", callback=None, pin=None):
        """Create a receiver for one supported protocol."""
        return InfraredReceiver(protocol, callback, pin)

    def capture(self, path=None, name="Signal", nedges=100, twait=100, display=False):
        """Capture a raw signal and optionally save it to the SD library."""
        from picoware.system.drivers.ir_rx.acquire import IR_GET

        receiver = IR_GET(
            _default_rx_pin(),
            nedges=nedges,
            twait=twait,
            display=display,
        )
        timings = receiver.acquire()
        if path is None:
            return timings
        return self.library.save_raw(path, name, timings)


IRSignal = Signal
parse = parse_ir
