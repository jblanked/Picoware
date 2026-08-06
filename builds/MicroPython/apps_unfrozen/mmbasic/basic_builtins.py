"""
Built-in functions for Microsoft BASIC-80 (from BASIC-80 Reference Manual
Version 5.21), plus TAB/SPC markers and a PRINT USING formatter.

MicroPython port: plain classes, no typing. `io_provider` is a callable that
returns the console object used by INKEY$/INPUT$ and POS.
"""

import math
import gc
import struct


class TabMarker:
    """TAB(n) marker returned by the TAB() function in a PRINT list."""

    __slots__ = ("column",)

    def __init__(self, column):
        self.column = column

    def __repr__(self):
        return "TAB(%d)" % self.column


class SpcMarker:
    """SPC(n) marker returned by the SPC() function in a PRINT list."""

    __slots__ = ("count",)

    def __init__(self, count):
        self.count = count

    def __repr__(self):
        return "SPC(%d)" % self.count


class UsingFormatter:
    """PRINT USING formatter: a small but faithful subset of MBASIC fields.

    Supported:
        #      digit placeholder
        .      decimal point
        ,      thousands separator
        + / -  sign control
        !      first character of a string
        &      whole string
        \\ \\   string of (n+2) characters, left-justified
        _      next character is literal
    Overflow prints a leading '%' like MBASIC.
    """

    def __init__(self, format_string):
        self.format_string = format_string
        self.fields = self._parse(format_string)

    def _parse(self, fmt):
        """Split the format string into (literal_text, field_spec) segments."""
        fields = []
        i = 0
        n = len(fmt)
        literal = []
        while i < n:
            c = fmt[i]
            if c == "_" and i + 1 < n:
                literal.append(fmt[i + 1])
                i += 2
                continue
            if c == "#" or c == "!" or c == "&" or c == "\\":
                if literal:
                    fields.append(("literal", "".join(literal)))
                    literal = []
                if c == "\\":
                    j = i
                    while j < n and fmt[j] == "\\":
                        j += 1
                    width = j - i + 2
                    fields.append(("string", {"kind": "bs", "width": width}))
                    i = j
                    continue
                if c == "!":
                    fields.append(("string", {"kind": "bang"}))
                    i += 1
                    continue
                if c == "&":
                    fields.append(("string", {"kind": "amp"}))
                    i += 1
                    continue
                # '#' numeric field
                j = i
                spec = {"sign": None, "digits": 0, "decimals": 0,
                        "commas": False, "exponent": 0}
                if j < n and fmt[j] in "+-":
                    spec["sign"] = fmt[j]
                    j += 1
                while j < n and (fmt[j] in "#*$,"):
                    if fmt[j] == ",":
                        spec["commas"] = True
                    elif fmt[j] in "*$":
                        spec["fill"] = fmt[j]
                    j += 1
                while j < n and fmt[j] == "#":
                    spec["digits"] += 1
                    j += 1
                if j < n and fmt[j] == ".":
                    j += 1
                    while j < n and fmt[j] == "#":
                        spec["decimals"] += 1
                        j += 1
                if j < n and fmt[j] == "^":
                    while j < n and fmt[j] == "^":
                        spec["exponent"] += 1
                        j += 1
                fields.append(("number", spec))
                i = j
                continue
            literal.append(c)
            i += 1
        if literal:
            fields.append(("literal", "".join(literal)))
        return fields

    def format_values(self, values):
        out = []
        vi = 0
        for kind, data in self.fields:
            if kind == "literal":
                out.append(data)
            elif kind == "string":
                if vi >= len(values):
                    break
                value = values[vi]
                vi += 1
                out.append(self._format_string(str(value), data))
            else:  # number
                if vi >= len(values):
                    break
                value = values[vi]
                vi += 1
                out.append(self._format_number(value, data))
        return "".join(out)

    def _format_string(self, value, spec):
        kind = spec["kind"]
        if kind == "bang":
            return value[:1] if value else " "
        if kind == "amp":
            return value
        # backslash field: width chars, left justified
        return (value + " " * spec["width"])[:spec["width"]]

    def _format_number(self, value, spec):
        try:
            x = float(value)
        except (TypeError, ValueError):
            return "%" + str(value)
        overflow = False
        digits = spec.get("digits", 1) or 1
        decimals = spec.get("decimals", 0)
        int_digits = digits - decimals
        if int_digits < 1:
            int_digits = 1

        negative = x < 0
        x = abs(x)
        if spec.get("exponent", 0) > 0:
            return self._exponential(x, negative, spec)

        scaled = round(x, decimals)
        max_int = 10 ** int_digits - 1
        if scaled >= 10 ** (int_digits + decimals):
            overflow = True
        if scaled > max_int + (10 ** -decimals) * 0.999:
            overflow = True

        frac = int(round((scaled - int(scaled)) * (10 ** decimals))) if decimals else 0
        whole = int(scaled)
        if frac >= 10 ** decimals:
            frac -= 10 ** decimals
            whole += 1
            if whole >= 10 ** int_digits:
                overflow = True

        num_text = ("%0*d" % (decimals, frac)) if decimals else ""
        whole_text = str(whole)
        if spec.get("commas"):
            out = []
            for i, c in enumerate(reversed(whole_text)):
                if i and i % 3 == 0:
                    out.append(",")
                out.append(c)
            whole_text = "".join(reversed(out))
        if decimals:
            num_text = whole_text + "." + num_text
        else:
            num_text = whole_text

        fill = spec.get("fill")
        if fill:
            fill_n = int_digits - len(whole_text)
            if fill_n > 0:
                num_text = fill * fill_n + num_text
            if negative:
                num_text = "-" + num_text
            elif spec.get("sign") == "+":
                num_text = "+" + num_text
            return ("%" if overflow else "") + num_text

        sign = ""
        if negative:
            sign = "-"
        elif spec.get("sign") == "+":
            sign = "+"
        elif spec.get("sign") == "-":
            sign = " "
        return ("%" if overflow else "") + sign + num_text

    @staticmethod
    def _exponential(x, negative, spec):
        if x != 0:
            exp = int(math.floor(math.log10(x)))
            mant = x / (10.0 ** exp)
        else:
            exp = 0
            mant = 0.0
        decimals = spec.get("decimals", 2)
        mant = round(mant, decimals)
        if mant >= 10.0:
            mant /= 10.0
            exp += 1
        text = ("%0.*f" % (decimals, mant))
        sign = "-" if negative else "+"
        return "%sE%s%02d" % (text, sign, abs(exp))


class KeyInputPending(Exception):
    """Raised when INPUT$ needs keys that have not arrived yet.

    The interpreter catches this to yield control (cooperative tick), then
    re-executes the statement once the keys arrive.
    """

    def __init__(self, remaining):
        super().__init__("key input pending")
        self.remaining = remaining


class BuiltinFunctions:
    """MBASIC 5.21 built-in functions."""

    def __init__(self, runtime, io_provider=None):
        self.runtime = runtime
        self._io_provider = io_provider  # callable returning the console

    def _io(self):
        if self._io_provider:
            return self._io_provider()
        return None


    def ABS(self, x):
        return abs(self._num(x))

    def ATN(self, x):
        return math.atan(self._num(x))

    def COS(self, x):
        return math.cos(self._num(x))

    def EXP(self, x):
        return math.exp(self._num(x))

    def FIX(self, x):
        return int(self._num(x))

    def INT(self, x):
        return math.floor(self._num(x))

    def LOG(self, x):
        return math.log(self._num(x))

    def SGN(self, x):
        v = self._num(x)
        return -1 if v < 0 else (1 if v > 0 else 0)

    def SIN(self, x):
        return math.sin(self._num(x))

    def SQR(self, x):
        return math.sqrt(self._num(x))

    def TAN(self, x):
        return math.tan(self._num(x))

    def RND(self, x=None):
        if x is None:
            return self.runtime.rnd.next()
        return self.runtime.rnd.next(self._num(x))

    def CINT(self, x):
        from .number_format import to_integer
        v = to_integer(self._num(x))
        return (v + 0x8000) % 0x10000 - 0x8000  # wrap to signed 16-bit

    def CSNG(self, x):
        from .number_format import to_single
        return to_single(self._num(x))

    def CDBL(self, x):
        return float(self._num(x))

    def PEEK(self, addr):
        memory = getattr(self.runtime, "memory", {})
        return memory.get(int(self._num(addr)) & 0xFFFF, 0)

    def INP(self, _port):
        return 0

    def POS(self, _dummy=None):
        io = self._io()
        if io is not None and hasattr(io, "pos"):
            return io.pos()
        return 0

    def FRE(self, _x=None):
        return gc.mem_free()

    def ERR(self, *_a):
        return getattr(self.runtime, "last_error_code", 0)

    def ERL(self, *_a):
        return getattr(self.runtime, "last_error_line", 0)

    def LOC(self, file_num):
        return 0

    def LOF(self, file_num):
        return 0

    def EOF(self, file_num):
        try:
            fn = int(self._num(file_num))
            return -1 if self.runtime.files.get(fn, {}).get("eof") else 0
        except Exception:
            return 0

    def USR(self, *_a):
        return 0

    def VARPTR(self, *_a):
        return 0


    def ASC(self, s):
        s = str(s)
        if not s:
            raise ValueError("Illegal function call")
        return ord(s[0])

    def CHR(self, x):
        return chr(int(self._num(x)) & 0xFF)

    def HEX(self, x):
        v = int(self._num(x)) & 0xFFFF
        return format(v, "X")

    def OCT(self, x):
        v = int(self._num(x)) & 0xFFFF
        return format(v, "o")

    def INSTR(self, *args):
        # INSTR([start,] s1, s2)
        if len(args) == 3:
            start = int(self._num(args[0]))
            s1 = str(args[1])
            s2 = str(args[2])
        else:
            start = 1
            s1 = str(args[0])
            s2 = str(args[1])
        if start < 1:
            start = 1
        if start > len(s1):
            return 0
        idx = s1.find(s2, start - 1)
        if idx < 0:
            return 0
        return idx + 1

    def LEFT(self, s, n):
        s = str(s)
        n = max(int(self._num(n)), 0)
        return s[:n]

    def LEN(self, s):
        return len(str(s))

    def MID(self, *args):
        s = str(args[0])
        start = int(self._num(args[1]))
        if start < 1:
            start = 1
        if len(args) > 2:
            length = max(int(self._num(args[2])), 0)
            return s[start - 1:start - 1 + length]
        return s[start - 1:]

    def RIGHT(self, s, n):
        s = str(s)
        n = max(int(self._num(n)), 0)
        if n == 0:
            return ""
        return s[-n:]

    def SPACE(self, n):
        n = max(int(self._num(n)), 0)
        return " " * n

    def STR(self, x):
        from .number_format import format_number, SINGLE_DIGITS
        text = format_number(self._num(x), SINGLE_DIGITS)
        if not text.startswith("-"):
            text = " " + text
        return text

    def STRING(self, n, char):
        n = max(int(self._num(n)), 0)
        if isinstance(char, str):
            c = char[0] if char else " "
        else:
            c = chr(int(self._num(char)) & 0xFF)
        return c * n

    def TIME(self):
        """Return the local RTC time in MMBasic's HH:MM:SS form."""
        import time

        now = time.localtime()
        return "%02d:%02d:%02d" % (now[3], now[4], now[5])

    def VAL(self, s):
        s = str(s).strip()
        if not s:
            return 0
        i = 0
        n = len(s)
        if s[0] in "+-":
            i = 1
        while i < n and (s[i].isdigit() or s[i] in ".eEdD"):
            i += 1
        token = s[:i]
        if not token or token in ("+", "-", "."):
            return 0
        try:
            if "D" in token or "d" in token:
                token = token.replace("D", "E").replace("d", "e")
            return float(token) if (any(c in token for c in ".eE")) else int(token)
        except ValueError:
            return 0


    def MKI(self, x):
        return struct.pack("<h", int(self._num(x)) & 0xFFFF)

    def MKS(self, x):
        return struct.pack("<f", self._num(x))

    def MKD(self, x):
        return struct.pack("<d", self._num(x))

    def CVI(self, s):
        s = self._as_bytes(s)
        if len(s) < 2:
            return 0
        return struct.unpack("<h", s[:2])[0]

    def CVS(self, s):
        s = self._as_bytes(s)
        if len(s) < 4:
            return 0.0
        return struct.unpack("<f", s[:4])[0]

    def CVD(self, s):
        s = self._as_bytes(s)
        if len(s) < 8:
            return 0.0
        return struct.unpack("<d", s[:8])[0]

    @staticmethod
    def _as_bytes(s):
        if isinstance(s, bytes):
            return s
        if isinstance(s, bytearray):
            return bytes(s)
        return bytes(ord(c) & 0xFF for c in str(s))


    def TAB(self, n):
        return TabMarker(max(int(self._num(n)), 1))

    def SPC(self, n):
        return SpcMarker(max(int(self._num(n)), 0))

    def CHOICE(self, cond, a, b):
        """Return a if cond is true (non-zero), else b."""
        try:
            truthy = float(cond) != 0
        except (TypeError, ValueError):
            truthy = bool(cond)
        return a if truthy else b


    def INKEY(self):
        io = self._io()
        if io is None or not hasattr(io, "read_key"):
            return ""
        return io.read_key()

    def INPUT(self, num, file_num=None):
        io = self._io()
        if io is None or not hasattr(io, "key_input"):
            raise KeyInputPending(int(self._num(num)))
        return io.key_input(int(self._num(num)))


    @staticmethod
    def _num(x):
        if isinstance(x, bool):
            return int(x)
        if isinstance(x, (int, float)):
            return x
        if isinstance(x, bytes):
            try:
                return float(x)
            except Exception:
                pass
        raise TypeError("Type mismatch")
