"""
How MBASIC 5.21 represents and prints a number.

Derived from the real binary under cpmemu rather than from the manual. The
rules, with the value rounded to `digits` significant figures first (6 for
single precision, 16 for double):

* A number is always followed by a space, and preceded by one if it is not
  negative. PRINT 1;2;-3 gives " 1  2 -3 ".
* There is no leading zero: .5, not 0.5.
* Trailing zeros are dropped, and so is a trailing point.
* Unscaled while it fits, scaled when it does not:

      value >= 1     unscaled while the integer part needs no more than
                     `digits` digits.  999999 prints as 999999 and 1000000
                     as 1E+06.
      value < 1      unscaled while the zeros after the point plus the
                     significant digits come to no more than digits + 1.

* The exponent is at least two digits and always signed: 1E+06, 1E-08.
  Double precision uses D where single uses E: 1.234567890123457D+16.

MicroPython port: the upstream uses the `decimal` module; here everything is
done with float math (round-half-away-from-zero) so it runs on MicroPython.
"""

import math
import struct

#: Significant figures MBASIC keeps for each precision. None means the value
#: is INTEGER-typed and prints as a plain whole number.
INTEGER_DIGITS = None
SINGLE_DIGITS = 6
DOUBLE_DIGITS = 16

def _round_half_away(x):
    """Round a float to the nearest integer, halves away from zero."""
    if x >= 0:
        return math.floor(x + 0.5)
    return -math.floor(-x + 0.5)


def _round_to_digits(value, digits):
    """Round a positive value to `digits` significant figures (half away)."""
    if value == 0:
        return 0.0
    exp = math.floor(math.log10(value))
    factor = 10.0 ** (digits - 1 - exp)
    r = _round_half_away(value * factor) / factor
    # Rounding may carry into the next power of ten (999 -> 1000).
    if r > 0 and math.floor(math.log10(r)) != exp:
        exp2 = math.floor(math.log10(r))
        factor2 = 10.0 ** (digits - 1 - exp2)
        r = _round_half_away(value * factor2) / factor2
    return r


def _significant_digits(rounded, exponent, digits):
    """How many significant figures a rounded value actually carries."""
    ndec = max(digits - 1 - exponent, 0)
    text = ("%.*f" % (ndec, rounded)).rstrip("0").rstrip(".")
    s = text.lstrip("-")
    if "." in s:
        s = s.replace(".", "")
    return len(s.lstrip("0")) if s.lstrip("0") else 1


def _unscaled(rounded, ndec):
    """Plain decimal notation: no leading zero, no trailing zeros."""
    text = ("%.*f" % (ndec, rounded)).rstrip("0").rstrip(".")
    if text.startswith("0."):
        text = text[1:]  # .5, not 0.5
    return text or "0"


def _scaled(rounded, digits):
    """Exponential notation, MBASIC style: 1E+06, 1.23457E+06, 1.5D-08."""
    exponent = math.floor(math.log10(rounded))
    mantissa = rounded / (10.0 ** exponent)
    text = ("%.*f" % (digits - 1, mantissa)).rstrip("0").rstrip(".")
    letter = "D" if digits > SINGLE_DIGITS else "E"
    sign = "+" if exponent >= 0 else "-"
    return "%s%c%s%02d" % (text, letter, sign, abs(exponent))


def format_number(value, digits=SINGLE_DIGITS):
    """The characters MBASIC prints for a number, without the padding spaces.

    Args:
        value: an int or float.
        digits: significant figures - SINGLE_DIGITS or DOUBLE_DIGITS, or None
            for an INTEGER-typed value.

    Returns:
        str, e.g. "3934.03", ".333333", "1E+06", "-1.23457E+06".
    """
    if isinstance(value, bool):
        value = int(value)

    if digits is None:
        return str(int(value))

    try:
        if value != value or value in (float("inf"), float("-inf")):
            return str(value)
    except (TypeError, ValueError):
        return str(value)

    if value == 0:
        return "0"

    negative = value < 0
    rounded = _round_to_digits(abs(value), digits)
    exponent = math.floor(math.log10(rounded))
    significant = _significant_digits(rounded, exponent, digits)

    if exponent >= 0:
        unscaled = (exponent + 1) <= digits
    else:
        unscaled = (-exponent - 1) + significant <= digits + 1

    if unscaled:
        ndec = max(digits - 1 - exponent, 0)
        text = _unscaled(rounded, ndec)
    else:
        text = _scaled(rounded, digits)
    return "-" + text if negative else text


def format_for_print(value, digits=SINGLE_DIGITS):
    """As printed in a PRINT list: a leading space unless negative, and a
    trailing space always.

        PRINT 1;2;-3      ->  " 1  2 -3 "
    """
    text = format_number(value, digits)
    if not text.startswith("-"):
        text = " " + text
    return text + " "


def to_single(value):
    """Round to MBASIC single precision (a round trip through float32)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    try:
        return struct.unpack("f", struct.pack("f", value))[0]
    except (OverflowError, struct.error, ValueError):
        return value


def to_integer(value):
    """Round to MBASIC's integer type: nearest, with halves away from zero.

    A% = 3.7 is 4 and A% = -3.7 is -4. A% = 2.5 is 3, so it is not Python's
    banker's rounding either.
    """
    if isinstance(value, str):
        raise TypeError("Type mismatch")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    if isinstance(value, int):
        return value
    return _round_half_away(value)


def coerce_to_type(value, suffix):
    """Store a value the way a variable of this type would hold it."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if suffix in ("%", "!", "#", None):
            raise TypeError("Type mismatch")
        return value
    if not isinstance(value, (int, float)):
        return value
    if suffix == "%":
        return to_integer(value)
    if suffix == "#":
        return float(value)
    if suffix in ("!", None):
        return to_single(value)
    return value
