"""SimpleRPN: a compact four-level RPN calculator for Picoware."""

import ujson as json
from math import sqrt, log, exp, frexp, ldexp
from utime import ticks_add, ticks_diff, ticks_ms

# Older firmware can still run the app using its on-screen register keys.
try:
    from picoware.system.buttons import BUTTON_CTRL_0
except ImportError:
    BUTTON_CTRL_0 = None

from picoware.system.vector import Vector
from picoware.system.font import FONT_XTRA_SMALL, FONT_SMALL, FONT_MEDIUM
from picoware.system.colors import TFT_WHITE
from picoware.system.buttons import (
    BUTTON_A,
    BUTTON_Z,
    BUTTON_BACK,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_CENTER,
    BUTTON_0,
    BUTTON_9,
    BUTTON_PERIOD,
    BUTTON_SLASH,
    BUTTON_BACKSLASH,
    BUTTON_ASTERISK,
    BUTTON_MINUS,
    BUTTON_PLUS,
    BUTTON_EQUAL,
    BUTTON_PERCENT,
    BUTTON_BACKSPACE,
    BUTTON_DELETE,
    BUTTON_SPACE,
    BUTTON_TAB,
    BUTTON_ESCAPE,
    BUTTON_C,
    BUTTON_D,
    BUTTON_F,
    BUTTON_H,
    BUTTON_I,
    BUTTON_J,
    BUTTON_K,
    BUTTON_L,
    BUTTON_N,
    BUTTON_P,
    BUTTON_Q,
    BUTTON_R,
    BUTTON_S,
    BUTTON_T,
    BUTTON_U,
    BUTTON_V,
    BUTTON_X,
)


def _rgb565(red, green, blue):
    return ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)


# Restrained industrial palette: powder-coated shell, green-grey LCD, amber focus.
COLOR_BG = _rgb565(15, 18, 19)
COLOR_EDGE = _rgb565(91, 101, 100)
COLOR_SHADOW = _rgb565(7, 9, 9)
COLOR_LCD = _rgb565(177, 193, 160)
COLOR_LCD_DARK = _rgb565(25, 38, 28)
COLOR_LCD_MID = _rgb565(72, 91, 72)
COLOR_KEY = _rgb565(54, 61, 62)
COLOR_KEY_TOP = _rgb565(77, 85, 85)
COLOR_KEY_FN = _rgb565(69, 73, 69)
COLOR_KEY_OP = _rgb565(139, 84, 30)
COLOR_AMBER = _rgb565(245, 166, 57)
COLOR_MUTED = _rgb565(161, 168, 164)
COLOR_ERROR = _rgb565(244, 102, 83)

STATE_FILE = "picoware/settings/srpn.json"
STATE_TEMP = "picoware/settings/srpn.tmp"
STATE_BACKUP = "picoware/settings/srpn.bak"
STATE_VERSION = 3
SAVE_DELAY_MS = 1000
HELP_PAGE_COUNT = 3
MAX_STATE_BYTES = 8192


KEYS = (
    ("CLX", "clear", "function"),
    ("+/-", "negate", "function"),
    ("%", "percent", "function"),
    ("/", "divide", "operator"),
    ("x2", "square", "function"),
    ("SQRT", "sqrt", "function"),
    ("1/x", "reciprocal", "function"),
    ("*", "multiply", "operator"),
    ("7", "7", "number"),
    ("8", "8", "number"),
    ("9", "9", "number"),
    ("-", "subtract", "operator"),
    ("4", "4", "number"),
    ("5", "5", "number"),
    ("6", "6", "number"),
    ("+", "add", "operator"),
    ("1", "1", "number"),
    ("2", "2", "number"),
    ("3", "3", "number"),
    ("ENTER", "enter", "enter"),
    ("DROP", "drop", "function"),
    ("0", "0", "number"),
    (".", "decimal", "number"),
    ("SWAP", "swap", "function"),
    ("STO", "store", "memory"),
    ("RCL", "recall", "memory"),
    ("UNDO", "undo", "function"),
    ("MODE", "mode", "function"),
)

COMPACT_KEY_LABELS = {"CLR TVM": "CLR", "TIMES": "TMS", "PRICE": "PRC"}

ACTION_INDEX = {}
for _key_index in range(len(KEYS)):
    ACTION_INDEX[KEYS[_key_index][1]] = _key_index

ENTER_INDEX = ACTION_INDEX["enter"]


# Financial values use the cash-flow sign convention: receipts +, payments -.
FIN_PAGES = ("tvm", "amort", "interest", "cash", "margin", "markup")
FIN_DEFAULTS = {"N": 0.0, "I/YR": 0.0, "PV": 0.0, "PMT": 0.0,
                "FV": 0.0, "P/YR": 12.0, "NOM": 0.0, "EFF": 0.0,
                "COST": 0.0, "PRICE": 0.0, "MARG": 0.0, "MARK": 0.0,
                "FIRST": 1.0, "LAST": 12.0}
MAX_CASH_GROUPS = 50
MAX_FIN_PERIODS = 1000000
MAX_AMORT_PERIODS = 100000


def _finite(value):
    value = float(value)
    if value != value or abs(value) == float("inf"):
        raise ValueError("NON-FINITE VALUE")
    return value


def _whole(value, low, high):
    value = _finite(value)
    if value != int(value) or not low <= value <= high:
        raise ValueError("INVALID COUNT")
    return int(value)


def _log1p(value):
    if value <= -1:
        raise ValueError("RATE MUST EXCEED -100%/PERIOD")
    if abs(value) < 0.00001:
        return value * (1 - value * (0.5 - value * (1 / 3 - value * 0.25)))
    return log(1 + value)


def _expm1(value):
    if abs(value) < 0.1:
        # exp(x)-1 loses significant digits at small rates. Eleven Taylor
        # terms keep this interval accurate to double precision.
        total = term = value
        for divisor in range(2, 12):
            term *= value / divisor
            total += term
        return total
    return exp(value) - 1


def _sum_products(terms, binary=False):
    """Sum products exactly, returning a float or (integer, binary exponent).

    The binary form postpones range limits until the final result. Integer
    significands retain cancellation between large terms. Cash flows use
    at most 51 groups; no repeated-payment arrays are needed.
    """
    total, exponent = 0, 0
    for factors in terms:
        mantissa, power = 1, 0
        for factor in factors:
            if isinstance(factor, int):
                mantissa *= factor
            else:
                fraction, exp2 = frexp(_finite(factor))
                mantissa *= int(ldexp(fraction, 53))
                power += exp2 - 53
        if not mantissa:
            continue
        if not total:
            total, exponent = mantissa, power
        elif power < exponent:
            total = (total << (exponent - power)) + mantissa
            exponent = power
        else:
            total += mantissa << (power - exponent)
    return (total, exponent) if binary else _binary_float((total, exponent))


def _binary_float(value):
    """Round an integer significand and unrestricted binary exponent once."""
    total, exponent = value
    if not total:
        return 0.0
    magnitude = abs(total)
    upper, shift = magnitude, 0
    while upper >= (1 << 85):
        upper >>= 32
        shift += 32
    while upper >= (1 << 53):
        upper >>= 1
        shift += 1
    # Discard values below half the smallest subnormal without allocating
    # an integer as large as a long cash-flow schedule's exponent.
    if -1074 - exponent > shift + 53:
        return 0.0
    # Subnormal doubles have fewer than 53 significant bits.
    shift = max(shift, -1074 - exponent)
    upper = magnitude >> shift
    if shift:
        remainder = magnitude - (upper << shift)
        half = 1 << (shift - 1)
        if remainder > half or (remainder == half and upper & 1):
            upper += 1
    return _finite(ldexp(float(-upper if total < 0 else upper), exponent + shift))


def _binary_normalize(value):
    total, exponent = value
    upper, shift = abs(total), 0
    while upper >= (1 << 53):
        upper >>= 32
        shift += 32
    fraction, power = frexp(_binary_float((total, -shift)))
    return fraction, exponent + shift + power


def _binary_ratio(numerator, denominator):
    top, top_power = _binary_normalize(numerator)
    bottom, bottom_power = _binary_normalize(denominator)
    power = top_power - bottom_power
    if not bottom:
        raise ZeroDivisionError
    if not top or power < -1075:
        return 0.0
    if power > 1024 and top:
        raise OverflowError
    return _finite(ldexp(top / bottom, power))


def _binary_log_ratio(numerator, denominator):
    """Log of a positive ratio without overflowing or losing a small delta."""
    difference = _binary_add(numerator, (-denominator[0], denominator[1]))
    delta_fraction, delta_power = _binary_normalize(difference)
    bottom, bottom_power = _binary_normalize(denominator)
    if delta_power <= bottom_power:
        delta = ldexp(delta_fraction / bottom, delta_power - bottom_power)
        if abs(delta) < 0.5:
            return _log1p(delta)
    top, top_power = _binary_normalize(numerator)
    return log(top / bottom) + (top_power - bottom_power) * 0.6931471805599453


def _binary_log(value):
    fraction, power = _binary_normalize(value)
    return log(abs(fraction)) + power * 0.6931471805599453


def _binary_add(left, right):
    if not left[0]:
        return right
    if not right[0]:
        return left
    # Exponential factors can have enormous exponents. A gap larger than
    # the entire double range cannot affect a rounded result or cancel.
    _, lp = _binary_normalize(left)
    _, rp = _binary_normalize(right)
    if abs(lp - rp) > 4096:
        return left if lp > rp else right
    power = min(left[1], right[1])
    return ((left[0] << (left[1] - power)) + (right[0] << (right[1] - power)), power)


def _binary_exp(value, power):
    if not value[0]:
        return value
    # Keep exp(power)'s exponent separate so it neither overflows nor
    # underflows before being multiplied by the monetary coefficient.
    # Retain the full integer coefficient until later additions cancel;
    # normalizing it to a float here would discard low monetary bits.
    coefficient, exponent = value
    shift = int(power / 0.6931471805599453)
    remainder = power - shift * 0.6931471805599453
    product, product_power = _sum_products(((coefficient, exp(remainder)),), True)
    return product, product_power + exponent + shift


def _cash_integers(pv, pmt, fv):
    """Common binary unit: retain every input bit, including subnormals."""
    values = [_sum_products(((v,),), True) for v in (pv, pmt, fv)]
    power = min(e for m, e in values if m)
    return tuple(m << (e - power) if m else 0 for m, e in values)


def _decimal_parts(value, precise=False):
    text = ("%.16e" if precise else "%.15e") % abs(_finite(value))
    mantissa, exponent = text.lower().split("e")
    digits = mantissa.replace(".", "")
    return int(digits), int(exponent) - len(digits) + 1


def _round_ratio(numerator, denominator):
    units, remainder = divmod(abs(numerator), denominator)
    if remainder * 2 >= denominator:
        units += 1
    return -units if numerator < 0 else units


def _money_units(value, digits):
    mantissa, power = _decimal_parts(value)
    # Keep the full stored precision when the currency grid reaches the
    # sixteenth significant digit; otherwise retain decimal half ties.
    if abs(value) >= 10 ** (15 - digits):
        mantissa, power = _decimal_parts(value, True)
    power += digits
    units = mantissa * (10 ** power) if power >= 0 else _round_ratio(mantissa, 10 ** -power)
    return -units if value < 0 else units


def _units_value(units, digits):
    # Parsing the decimal result avoids overflowing a float intermediate
    # when an otherwise finite monetary amount has many decimal places.
    return _finite(float(str(units) + "e-" + str(digits)))


def _rate_root(residual, guess, periods=1, certify=None):
    """Bracket across representable rates; a small residual alone is not a root."""
    lower = log(2.0 ** -53)
    upper = _log1p(1.7976931348623157e308 / (100 * periods))
    center = max(lower, min(upper, _log1p(guess)))
    def zero(t):
        rate = _expm1(t)
        if certify is not None and not certify(rate):
            raise ValueError("IRR ZERO CANNOT BE CERTIFIED")
        return rate

    fc = residual(_expm1(center))
    if fc == 0:
        return zero(center)
    left = right = center
    fl = fr = fc
    step = 0.0001
    bracket = None
    for _ in range(32):
        nl, nr = max(lower, center - step), min(upper, center + step)
        fnl, fnr = residual(_expm1(nl)), residual(_expm1(nr))
        if fnl == 0:
            return zero(nl)
        if fnr == 0:
            return zero(nr)
        if (fnl > 0) != (fl > 0):
            bracket = (nl, left, fnl)
            break
        if (fr > 0) != (fnr > 0):
            bracket = (right, nr, fr)
            break
        left, right, fl, fr = nl, nr, fnl, fnr
        if nl == lower and nr == upper:
            break
        step *= 2
    if bracket is None:
        raise ValueError("NO BRACKET: TRY ANOTHER RATE")
    left, right, fl = bracket
    fr = residual(_expm1(right))
    for _ in range(96):
        mid = (left + right) * 0.5
        fm = residual(_expm1(mid))
        if fm == 0:
            return _expm1(mid)
        if right - left <= 1e-13 or mid == left or mid == right:
            # The sign-changing bracket certifies a root. Near -1, the
            # nearest representable rate may still have a sizable residual.
            best = min((abs(fl), left), (abs(fm), mid), (abs(fr), right))
            return _expm1(best[1])
        if (fl > 0) != (fm > 0):
            right, fr = mid, fm
        else:
            left, fl = mid, fm
    raise ValueError("RATE DID NOT CONVERGE")


def _cash_trim(value, bits):
    """Bound geometric-factor products while preserving small rate increments."""
    number, exponent = value
    upper, shift = abs(number), 0
    while upper >= (1 << (bits + 32)):
        upper >>= 32
        shift += 32
    while upper >= (1 << bits):
        upper >>= 1
        shift += 1
    if shift:
        remainder = abs(number) - (upper << shift)
        half = 1 << (shift - 1)
        if remainder > half or (remainder == half and upper & 1):
            upper += 1
    return (-upper if number < 0 else upper), exponent + shift


def _cash_product(left, right):
    return left[0] * right[0], left[1] + right[1]


def _cash_divide(top, bottom, bits):
    """Keep exact divisible balances; otherwise retain the requested precision."""
    numerator, denominator = top[0], bottom[0]
    exponent = top[1] - bottom[1]
    whole, remainder = divmod(numerator, denominator)
    if not remainder:
        return whole, exponent
    _, top_bits = _binary_normalize((abs(numerator), 0))
    _, bottom_bits = _binary_normalize((abs(denominator), 0))
    shift = bits + bottom_bits - top_bits
    if shift >= 0:
        numerator <<= shift
    else:
        denominator <<= -shift
    sign = -1 if (numerator < 0) != (denominator < 0) else 1
    quotient, remainder = divmod(abs(numerator), abs(denominator))
    if 2 * remainder > abs(denominator) or (2 * remainder == abs(denominator) and quotient & 1):
        quotient += 1
    return sign * quotient, exponent - shift


def _cash_factors(discount, count, bits):
    """Return d**count and d+...+d**count in O(log count), with bounded integers."""
    power, total = (1, 0), (0, 0)
    block_power = block_total = discount
    while count:
        if count & 1:
            total = _cash_trim(_binary_add(total, _cash_product(power, block_total)), bits)
            power = _cash_trim(_cash_product(power, block_power), bits)
        count >>= 1
        if count:
            block_total = _cash_trim(_binary_add(block_total, _cash_product(block_power, block_total)), bits)
            block_power = _cash_trim(_cash_product(block_power, block_power), bits)
    return power, total


def _cash_balance(flows, annual, frequency):
    """Evaluate grouped cash flows backwards, cancelling before discounting."""
    if annual == 0:
        return _sum_products(tuple((amount, count) for amount, count in flows), True)
    growth = _sum_products(((frequency,), (annual,)), True)
    if growth[0] <= 0:
        raise ValueError("RATE MUST EXCEED -100%/PERIOD")
    unit = (int(frequency), 0)
    annual_binary = _sum_products(((annual,),), True)
    log_rate = _log1p(annual / frequency)
    factors = {}
    # Tiny rates must survive adding one before powers are evaluated.
    # Ordinary rates use 128 bits; even subnormal inputs stay bounded.
    _, annual_power = frexp(annual)
    _, frequency_power = frexp(frequency)
    bits = 128 + max(0, frequency_power - annual_power)
    discount = None
    balance = (0, 0)
    for index in range(len(flows) - 1, 0, -1):
        amount, count = flows[index]
        if not amount and not balance[0]:
            continue
        money = _sum_products(((amount,),), True)
        if count == 1:
            balance = _cash_divide(_cash_product(_binary_add(balance, money), unit), growth, bits)
        elif abs(count * log_rate) >= 0.5:
            # Combine the balance and repeated-payment coefficient before
            # applying the exponential. This both preserves cancellation
            # and avoids powering large groups at every IRR trial.
            payment = _cash_product(money, unit)
            coefficient = _binary_add(_cash_product(balance, annual_binary),
                                      (-payment[0], payment[1]))
            discounted = _binary_exp(coefficient, -count * log_rate)
            balance = _cash_divide(_binary_add(discounted, payment), annual_binary, bits)
        else:
            if discount is None:
                discount = _cash_divide(unit, growth, bits)
            if count not in factors:
                factors[count] = _cash_factors(discount, count, bits)
            power, total = factors[count]
            balance = _binary_add(_cash_product(balance, power), _cash_product(money, total))
    return _binary_add(balance, _sum_products(((flows[0][0],),), True))


def _cash_exact_root(flows, rate):
    """Certify an unbracketed zero on short schedules using exact integers."""
    if rate == 0:
        return not _sum_products(tuple((amount, count) for amount, count in flows), True)[0]
    if sum(count for _, count in flows[1:]) > 64:
        return False
    numerator, power = _sum_products(((1,), (rate,)), True)
    while power < 0 and not numerator & 1:
        numerator >>= 1
        power += 1
    denominator = 1 << -power if power < 0 else 1
    numerator <<= max(power, 0)
    amounts = [_sum_products(((amount,),), True) for amount, _ in flows]
    unit = min(exponent for amount, exponent in amounts if amount)
    coefficients = [amount << (exponent - unit) if amount else 0 for amount, exponent in amounts]
    value, divisor = coefficients[0], 1
    for index in range(1, len(flows)):
        for _ in range(flows[index][1]):
            divisor *= denominator
            value = value * numerator + coefficients[index] * divisor
    return value == 0


def _normalized_terms(terms):
    """Sum nonempty signed log magnitudes on a common finite scale."""
    largest = max(magnitude for _, magnitude in terms)
    value = norm = 0.0
    for sign, magnitude in terms:
        term = exp(magnitude - largest)
        value += sign * term
        norm += term
    return value, norm, largest


def _log_abs_expm1(value):
    # Avoid overflow when only the logarithm of the magnitude is needed.
    return value + log(-_expm1(-value)) if value > 0 else log(-_expm1(value))


def _tvm_residual(t, n, pv, pmt, fv, logs):
    """Discounted balance after combining flows at the two endpoints."""
    remaining = n - 1
    if max(abs(n * t), abs(t)) < 0.5:
        # Near zero, summing the products directly avoids subtracting logs
        # of nearly equal balances. Fall back to log scaling if they overflow.
        annuity = -_expm1(-remaining * t) / _expm1(t) if t else remaining
        discount = exp(-n * t)
        try:
            terms = ((pv, 1), (pmt, annuity), (fv, discount))
            value = _sum_products(terms, True)
            norm = _sum_products(tuple((abs(a), abs(b)) for a, b in terms), True)
            if norm[0]:
                return _binary_ratio(value, norm)
        except (ValueError, OverflowError):
            pass
    terms = []
    if pv:
        terms.append((1 if pv > 0 else -1, logs[0]))
    if pmt and remaining:
        annuity = (_log_abs_expm1(-remaining * t) - _log_abs_expm1(t)
                   if t else log(abs(remaining)))
        terms.append((1 if (pmt > 0) == (remaining > 0) else -1,
                      logs[1] + annuity))
    if fv:
        terms.append((1 if fv > 0 else -1, logs[2] - n * t))
    if not terms:
        raise ValueError("RATE IS UNDETERMINED")
    value, norm, _ = _normalized_terms(terms)
    return value / norm


def _tvm_slope_log(t, n):
    """Log magnitude of K = sum(k * exp((n-k)*t)), k=1..n-1.

    Its geometric-series extension also covers fractional N. K has the
    sign of N-1 and its magnitude increases with t. The balance derivative
    vanishes when PMT*K + N*FV = 0 (FV includes the last END payment).
    """
    if max(abs(t), abs(n * t)) < 0.1:
        # Factor n*(n-1)*t**2 before evaluating the second difference
        # exp(n*t) - n*exp(t) + n-1 near zero.
        series, geometric, power, factorial = 0.5, 1.0, 1.0, 2.0
        for k in range(3, 18):
            geometric = n * geometric + 1
            power *= t
            factorial *= k
            series += geometric * power / factorial
        ratio = _expm1(t) / t if t else 1.0
        return t + log(n) + log(abs(n - 1)) + log(series) - 2 * log(ratio)
    # Equivalent second difference, retaining precision for N near one:
    # exp(t)*expm1((n-1)*t) - (n-1)*expm1(t).
    first = t + _log_abs_expm1((n - 1) * t)
    second = log(abs(n - 1)) + _log_abs_expm1(t)
    difference = max(first, second) + log(-_expm1(-abs(first - second)))
    return t + difference - 2 * _log_abs_expm1(t)


def _tvm_quadratic(a, b, c, guess):
    """Solve in r, using an exact integer discriminant and stable roots."""
    if not a:
        if not b:
            raise ValueError("RATE IS UNDETERMINED" if not c else "NO VALID RATE")
        result = _binary_ratio((-c, 0), (b, 0))
        if result <= -1:
            raise ValueError("NO VALID RATE")
        return result
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        raise ValueError("NO VALID RATE")
    if not discriminant:
        return _tvm_quadratic(0, 2 * a, b, guess)
    fraction, exponent = _binary_normalize((discriminant, 0))
    if exponent & 1:
        fraction *= 2
        exponent -= 1
    root = _sum_products(((sqrt(fraction),),), True)
    root = (root[0] * (-1 if b >= 0 else 1), root[1] + exponent // 2)
    numerator = _binary_add((-b, 0), root)
    candidates = []
    for top, bottom in ((numerator, (2 * a, 0)), ((2 * c, 0), numerator)):
        try:
            result = _binary_ratio(top, bottom)
            if result > -1:
                candidates.append(result)
        except (ValueError, OverflowError, ZeroDivisionError):
            pass
    if not candidates:
        raise ValueError("NO VALID RATE")
    center = _log1p(guess)
    return min(candidates, key=lambda r: abs(_log1p(r) - center))


def _tvm_exact_root(t, n, pv, pmt, fv):
    """Certify a nearby rational root instead of accepting a small residual.

    This bounded check covers short integer and binary-fraction schedules.
    Other unresolved tangencies fail explicitly rather than invent a rate.
    """
    numerator, power = _sum_products(((n,),), True)
    while power < 0 and not numerator & 1:
        numerator >>= 1
        power += 1
    denominator = 1 << -power if power < 0 else 1
    numerator <<= max(power, 0)
    if max(numerator, denominator) > 64:
        return None
    x = exp(t / denominator)
    old_a, a, old_b, b = 0, 1, 1, 0
    for _ in range(24):
        whole = int(x)
        old_a, a = a, whole * a + old_a
        old_b, b = b, whole * b + old_b
        if b > 1000000 or a > 10 ** 15:
            break
        if a and b:
            ad, bd = a ** denominator, b ** denominator
            result = _binary_ratio((ad - bd, 0), (bd, 0))
            if result > -1 and abs(_log1p(result) - t) < 1e-9:
                if ad == bd:
                    valid = (pv + fv) * denominator + pmt * (numerator - denominator) == 0
                else:
                    an, bn = a ** numerator, b ** numerator
                    valid = pv * an * (ad - bd) + pmt * (an * bd - ad * bn) + fv * bn * (ad - bd) == 0
                if valid:
                    return result
        fraction = x - whole
        if not fraction:
            break
        x = 1 / fraction
    return None


def _tvm_rate(n, pv, pmt, fv, begin, guess, periods=1):
    # Combining same-date flows prevents a large cancelling payment from
    # making every trial rate appear to have a negligible residual.
    pv, pmt, fv = _cash_integers(pv, pmt, fv)
    # The common-unit integers can safely exceed the float range here.
    if begin:
        pv += pmt
    else:
        fv += pmt
    if n == 1:
        if not pv and not fv:
            raise ValueError("RATE IS UNDETERMINED")
        if not pv or not fv or (pv > 0) == (fv > 0):
            raise ValueError("NO VALID RATE")
        result = _binary_ratio((-pv - fv, 0), (pv, 0))
        if result <= -1:
            raise ValueError("NO VALID RATE")
        return result

    if n == 2:
        return _tvm_quadratic(pv, 2 * pv + pmt, pv + pmt + fv, guess)

    # Endpoint coefficients are fixed throughout this solve. Preserve the
    # exact integers for the near-zero branch, but convert their logs once.
    logs = tuple(_binary_log((value, 0)) if value else 0.0 for value in (pv, pmt, fv))

    def residual(t):
        return _tvm_residual(t, n, pv, pmt, fv, logs)

    # Search the representable domain, including rates outside exp(+/-30).
    # 2**-53 is the smallest 1+r for a binary64 rate strictly above -1;
    # the upper bound also leaves room to convert the rate to annual percent.
    lower = log(2.0 ** -53)
    upper = _log1p(1.7976931348623157e308 / (100 * periods))
    points = [lower, upper]
    # The discounted balance has at most one turning point. Split there
    # to find both crossing roots and a repeated root that only touches zero.
    if pmt and fv and ((pmt > 0) == (fv > 0)) == (n < 1):
        target = log(n) + logs[2] - logs[1]
        left, right = points
        if _tvm_slope_log(left, n) < target < _tvm_slope_log(right, n):
            for _ in range(64):
                mid = (left + right) * 0.5
                if _tvm_slope_log(mid, n) < target:
                    left = mid
                else:
                    right = mid
            turning = (left + right) * 0.5
            if abs(residual(turning)) <= 1e-12:
                certified = _tvm_exact_root(turning, n, pv, pmt, fv)
                if certified is not None:
                    return certified
                raise ValueError("RATE TOO CLOSE TO TURNING POINT")
            points.insert(1, turning)
    center = max(lower, min(upper, _log1p(guess)))
    brackets = []
    left, fl = points[0], residual(points[0])
    for right in points[1:]:
        fr = residual(right)
        if fl == 0:
            return _expm1(left)
        if fr == 0:
            return _expm1(right)
        if fl * fr < 0:
            distance = max(left - center, center - right, 0)
            brackets.append((distance, left, right, fl))
        left, fl = right, fr
    if not brackets:
        raise ValueError("NO VALID RATE")
    _, left, right, fl = min(brackets)
    for _ in range(96):
        mid = (left + right) * 0.5
        fm = residual(mid)
        # At large log-rates adjacent floats can be farther apart than
        # 1e-13. Stop when bisection cannot move, still checking the residual.
        if fm == 0 or ((right - left <= 1e-13 or mid == left or mid == right)
                       and abs(fm) <= 1e-12):
            return _expm1(mid)
        if fl * fm < 0:
            right = mid
        else:
            left, fl = mid, fm
    raise ValueError("RATE DID NOT CONVERGE")


class FinancialState:
    """Independent financial registers; calculations return before committing."""

    def __init__(self):
        self.values = dict(FIN_DEFAULTS)
        self.mode = False
        self.page = "tvm"
        self.begin = False
        self.decimals = 2
        self.pending = False
        self.flows = [[0.0, 1]]
        self.cash_index = 0
        self.amort_result = None
        self.cash_result = None

    def snapshot(self):
        return {"values": dict(self.values), "mode": self.mode, "page": self.page,
                "begin": self.begin, "decimals": self.decimals, "pending": self.pending,
                "flows": [row[:] for row in self.flows], "cash_index": self.cash_index,
                "amort_result": self.amort_result, "cash_result": self.cash_result}

    @staticmethod
    def restored(data):
        state = FinancialState()
        if not isinstance(data, dict):
            raise ValueError("INVALID FINANCIAL STATE")
        values = data.get("values", {})
        for name in FIN_DEFAULTS:
            state.store(name, values.get(name, FIN_DEFAULTS[name]))
        for name in ("mode", "begin", "pending"):
            value = data.get(name, False)
            if not isinstance(value, bool):
                raise ValueError("INVALID FINANCIAL FLAG")
            setattr(state, name, value)
        state.page = data.get("page", "tvm")
        if state.page not in FIN_PAGES:
            raise ValueError("INVALID FINANCIAL PAGE")
        state.decimals = _whole(data.get("decimals", 2), 0, 9)
        flows = data.get("flows", [[0.0, 1]])
        if not isinstance(flows, list) or not 1 <= len(flows) <= MAX_CASH_GROUPS + 1:
            raise ValueError("INVALID CASH FLOWS")
        state.flows = []
        for row in flows:
            if not isinstance(row, list) or len(row) != 2:
                raise ValueError("INVALID CASH FLOW")
            state.flows.append([_finite(row[0]), _whole(row[1], 1, MAX_FIN_PERIODS)])
        if state.flows[0][1] != 1:
            raise ValueError("CF0 HAS NO REPEATS")
        state.cash_index = _whole(data.get("cash_index", 0), 0, len(flows) - 1)
        result = data.get("amort_result")
        if result is not None:
            if not isinstance(result, (list, tuple)) or len(result) != 3:
                raise ValueError("INVALID AMORTIZATION")
            state.amort_result = tuple(_finite(v) for v in result)
        result = data.get("cash_result")
        if result is not None:
            if not isinstance(result, (list, tuple)) or len(result) != 3 or result[0] not in ("NPV", "IRR"):
                raise ValueError("INVALID CASH RESULT")
            state.cash_result = (result[0], _finite(result[1]), bool(result[2]))
        return state

    def store(self, name, value):
        value = _finite(value)
        if name == "N" and not 0 <= value <= MAX_FIN_PERIODS:
            raise ValueError("INVALID N")
        if name == "P/YR":
            value = _whole(value, 1, 10000)
        if name in ("FIRST", "LAST"):
            value = _whole(value, 1, MAX_AMORT_PERIODS)
        self.values[name] = value
        self.amort_result = None
        self.cash_result = None

    def solve(self, name):
        v = self.values
        n, annual, pv, pmt, fv, periods = (v[k] for k in ("N", "I/YR", "PV", "PMT", "FV", "P/YR"))
        rate = annual / (100 * periods)
        if name == "I/YR":
            if n <= 0:
                raise ValueError("N MUST BE POSITIVE")
            if not min(pv, pmt, fv) < 0 < max(pv, pmt, fv):
                raise ValueError("RATE NEEDS + AND - VALUES")
            return _finite(_tvm_rate(n, pv, pmt, fv, self.begin, rate, periods) * 100 * periods)
        if name in ("N", "PV", "PMT", "FV"):
            t = _log1p(rate)
            timing = 1 + rate if self.begin else 1
            annual = v["I/YR"]
            frequency = 100 * periods
            payment_terms = [(pmt, frequency)]
            if self.begin:
                payment_terms.append((pmt, annual))
            if name == "N":
                if rate == 0:
                    balance = _sum_products(((-pv, 1), (-fv, 1)), True)
                    result = _binary_ratio(balance, _sum_products(((pmt,),), True))
                else:
                    denominator = _sum_products(payment_terms + [(pv, annual)], True)
                    numerator = _sum_products(payment_terms + [(-fv, annual)], True)
                    if (not denominator[0] or not numerator[0]
                            or (denominator[0] > 0) != (numerator[0] > 0)):
                        raise ValueError("NO VALID N")
                    result = _binary_log_ratio(numerator, denominator) / t
                if not 0 < result <= MAX_FIN_PERIODS:
                    raise ValueError("NO VALID N")
                return _finite(result)
            if n <= 0:
                raise ValueError("N MUST BE POSITIVE")
            if n == 1:
                # Combine same-date cash flows before rounding the growth
                # factor. Even a rate too small to change 1+r can produce
                # a finite amount when a large principal cancels a payment.
                growth = _sum_products(((frequency,), (annual,)), True)
                unit = (int(frequency), 0)
                if name == "FV":
                    terms = [(pv, frequency), (pv, annual), (pmt, frequency)]
                    if self.begin:
                        terms.append((pmt, annual))
                    denominator = unit
                elif name == "PV":
                    terms = [(pmt, frequency), (fv, frequency)]
                    if self.begin:
                        terms.append((pmt, annual))
                    denominator = growth
                else:  # PMT
                    terms = [(pv, frequency), (pv, annual), (fv, frequency)]
                    denominator = growth if self.begin else unit
                return -_binary_ratio(_sum_products(terms, True), denominator)
            if name == "FV":
                if not rate:
                    return -_sum_products(((pv, 1), (pmt, n)))
                power = n * t
                if abs(power) < 0.5:
                    return -_sum_products(((pv, exp(power)),
                        (pmt, timing, _expm1(power) / rate)))
                coefficient = _sum_products(payment_terms + [(pv, annual)], True)
                # Avoid subtracting nearly equal discounted balances and
                # magnifying that error by dividing by a tiny discount.
                growth = _binary_exp(coefficient, power)
                numerator = _binary_add(_sum_products(payment_terms, True), (-growth[0], growth[1]))
                return _binary_ratio(numerator, _sum_products(((annual,),), True))
            if name == "PMT" and rate < 0:
                # At negative rates the future-value form stays bounded;
                # discounting first can overflow despite a finite payment.
                growth = _binary_exp(_sum_products(((pv,),), True), n * t)
                annuity = (_expm1(n * t) / rate) * timing
                numerator = _binary_add(growth, _sum_products(((fv,),), True))
                return -_binary_ratio(numerator, _sum_products(((annuity,),), True))
            if name == "PV" and abs(n * t) >= 0.5:
                coefficient = _sum_products(payment_terms + [(-fv, annual)], True)
                discounted = _binary_exp(coefficient, -n * t)
                payment = _sum_products(payment_terms, True)
                numerator = _binary_add(discounted, (-payment[0], payment[1]))
                return _binary_ratio(numerator, _sum_products(((annual,),), True))
            discount = exp(-n * t)
            annuity = (-_expm1(-n * t) / rate if rate else n) * timing
            if name == "PV":
                return -_sum_products(((pmt, annuity), (fv, discount)))
            discounted = _binary_exp(_sum_products(((fv,),), True), -n * t)
            numerator = _binary_add(_sum_products(((pv,),), True), discounted)
            return -_binary_ratio(numerator, _sum_products(((annuity,),), True))
        if name == "EFF":
            return _finite(100 * _expm1(periods * _log1p(v["NOM"] / (100 * periods))))
        if name == "NOM":
            return _finite(100 * periods * _expm1(_log1p(v["EFF"] / 100) / periods))
        cost, price = v["COST"], v["PRICE"]
        percent = v["MARG" if self.page == "margin" else "MARK"] / 100
        if name == "COST":
            return _finite(price * (1 - percent) if self.page == "margin" else price / (1 + percent))
        if name == "PRICE":
            return _finite(cost / (1 - percent) if self.page == "margin" else cost * (1 + percent))
        if name in ("MARG", "MARK"):
            profit = _sum_products(((price, 100), (-cost, 100)), True)
            base = price if name == "MARG" else cost
            return _binary_ratio(profit, _sum_products(((base,),), True))
        raise ValueError("ENTER A VALUE FIRST")

    def clone(self):
        # Internal state has already been validated at entry/load boundaries.
        state = FinancialState()
        for name, value in self.snapshot().items():
            setattr(state, name, value)
        return state

    def npv(self):
        return _binary_float(_cash_balance(self.flows, self.values["I/YR"],
                                           100 * self.values["P/YR"]))

    def irr(self):
        signs = [1 if row[0] > 0 else -1 for row in self.flows if row[0] != 0]
        changes = sum(signs[i] != signs[i - 1] for i in range(1, len(signs)))
        if not changes:
            raise ValueError("IRR NEEDS + AND - CASH FLOWS")
        # Removing empty endpoints or shifting every payment by the same
        # number of periods cannot change an IRR. Normalize before choosing
        # the solver so a trailing zero cannot hide a quadratic tangency.
        first, last = 0, len(self.flows)
        while not self.flows[first][0]:
            first += 1
        while not self.flows[last - 1][0]:
            last -= 1
        amount, repeats = self.flows[first]
        flows = [[amount, 1]]
        if repeats > 1:
            flows.append([amount, repeats - 1])
        flows.extend(self.flows[first + 1:last])
        periods = self.values["P/YR"]
        guess = self.values["I/YR"] / (100 * periods)
        count = sum(row[1] for row in flows[1:])
        if count <= 2:
            # Certify short schedules with an exact discriminant, including
            # tangencies and near-tangencies that residual tolerances cannot distinguish.
            amounts = [flows[0][0]]
            for amount, repeats in flows[1:]:
                amounts.extend([amount] * repeats)
            while len(amounts) < 3:
                amounts.append(0.0)
            a, b, c = _cash_integers(*amounts)
            rate = _tvm_quadratic(a, 2 * a + b, a + b + c, guess)
        else:
            def residual(rate):
                value = _cash_balance(flows, rate, 1)
                fraction, power = _binary_normalize(value)
                # Bisection needs a sign, not a second absolute-flow solve.
                # Clamp only the exponent so tiny nonzero balances cannot
                # underflow to an apparent root, nor large ones overflow.
                return ldexp(fraction, max(-1073, min(1023, power)))
            rate = _rate_root(residual, guess, periods,
                              lambda r: changes == 1 or _cash_exact_root(flows, r))
        return _finite(rate * 100 * periods), changes > 1

    def amortization(self):
        for progress, result in self.amortization_steps():
            pass
        return result

    def amortization_steps(self):
        """Yield between small batches; final result uses identical rounding."""
        v = self.values
        first = _whole(v["FIRST"], 1, MAX_AMORT_PERIODS)
        last = _whole(v["LAST"], first, min(int(v["N"]), MAX_AMORT_PERIODS))
        rate = v["I/YR"] / (100 * v["P/YR"])
        _log1p(rate)
        balance = _money_units(v["PV"], self.decimals)
        payment = _money_units(v["PMT"], self.decimals)
        numerator, power = _decimal_parts(v["I/YR"])
        if v["I/YR"] < 0:
            numerator = -numerator
        denominator = 100 * int(v["P/YR"])
        if power >= 0:
            numerator *= 10 ** power
        else:
            denominator *= 10 ** -power
        principal_total = interest_total = 0
        limit = 10 ** (309 + self.decimals)
        for period in range(1, last + 1):
            interest = 0 if self.begin and period == 1 else _round_ratio(-balance * numerator, denominator)
            principal = payment - interest
            balance += principal
            if abs(balance) >= limit:
                raise OverflowError("AMORTIZATION OVERFLOW")
            if period >= first:
                principal_total += principal
                interest_total += interest
            if period % 8 == 0 and period < last:
                yield period, None
        yield last, tuple(_units_value(value, self.decimals)
                          for value in (principal_total, interest_total, balance))


def format_number(value):
    """Return a compact value suitable for the calculator display."""
    if value != value:
        return "NAN"
    if abs(value) == float("inf"):
        return "OVERFLOW"
    if abs(value) < 1000000000000.0 and value == int(value):
        return str(int(value))
    text = "%.10g" % value
    if len(text) > 15:
        text = "%.7e" % value
    return text.replace("e", "E")


class RPNStack:
    """Four-level T/Z/Y/X stack with an editable X register."""

    __slots__ = (
        "stack",
        "entry",
        "entering",
        "lift_on_entry",
        "error",
        "status",
        "variables",
        "variable_set",
        "undo_state",
        "undo_label",
    )

    def __init__(self):
        # Initialize stack: X=0, Y=0, Z=0, T=0
        self.stack: list[float] = [0.0, 0.0, 0.0, 0.0]
        self.entry: str = ""
        self.entering: bool = False
        self.lift_on_entry: bool = False
        self.error: str = ""
        self.status: str = "READY"
        self.variables: list[float] = [0.0] * 26
        self.variable_set: list[bool] = [False] * 26
        self.undo_state: tuple | None = None
        self.undo_label: str = ""

    def snapshot(self):
        """Persist this mode's working memory independently of the other mode."""
        return {"stack": self.stack, "entry": self.entry, "entering": self.entering,
                "lift_on_entry": self.lift_on_entry, "variables": self.variables,
                "variable_set": self.variable_set}

    @staticmethod
    def restored(saved):
        saved_stack = saved.get("stack")
        saved_variables = saved.get("variables")
        saved_variable_set = saved.get("variable_set")
        if (
            not isinstance(saved_stack, list)
            or len(saved_stack) != 4
            or not isinstance(saved_variables, list)
            or len(saved_variables) != 26
            or not isinstance(saved_variable_set, list)
            or len(saved_variable_set) != 26
        ):
            raise ValueError("INVALID CALCULATOR MEMORY")

        restored_stack = [_finite(value) for value in saved_stack]
        restored_variables = [_finite(value) for value in saved_variables]
        restored_variable_set = [bool(value) for value in saved_variable_set]
        entry = saved.get("entry", "")
        entering = bool(saved.get("entering", False))
        if not isinstance(entry, str):
            raise ValueError("INVALID CALCULATOR MEMORY")
        # Entry allows 15 digits plus an optional decimal point and sign.
        unsigned = entry[1:] if entry.startswith("-") else entry
        if (len(unsigned.replace(".", "")) > 15 or unsigned.count(".") > 1
                or any(c not in "0123456789." for c in unsigned)):
            raise ValueError("INVALID CALCULATOR MEMORY")
        if entering and entry not in ("", "-", ".", "-."):
            _finite(entry)
        elif not entering:
            entry = ""

        result = RPNStack()
        result.stack = restored_stack
        result.variables = restored_variables
        result.variable_set = restored_variable_set
        result.entry = entry
        result.entering = entering
        result.lift_on_entry = bool(saved.get("lift_on_entry", False))
        result.status = "MEMORY RESTORED"
        return result

    def remember_undo(self, label: str) -> None:
        """Remember one complete pre-action state for mistake recovery."""
        self.undo_state = (
            self.stack[:],
            self.entry,
            self.entering,
            self.lift_on_entry,
            self.error,
            self.variables[:],
            self.variable_set[:],
            financial.snapshot() if financial.mode else None,
        )
        self.undo_label = label

    def undo(self):
        """Restore and consume the most recently remembered state."""
        global financial
        if self.undo_state is None:
            self.error = ""
            self.status = "NOTHING TO UNDO"
            return False
        # Validate undo state structure before applying
        state = self.undo_state
        label = self.undo_label
        if not isinstance(state, tuple) or len(state) != 8:
            self.error = "CORRUPT UNDO STATE"
            self.status = self.error
            self.undo_state = None
            return False
        try:
            self.stack = list(state[0])
            self.entry = str(state[1]) if state[1] else ""
            self.entering = bool(state[2])
            self.lift_on_entry = bool(state[3])
            self.error = str(state[4]) if state[4] else ""
            self.variables = list(state[5])
            self.variable_set = list(state[6])
            if state[7] is not None:
                financial = FinancialState.restored(state[7])
        except (TypeError, ValueError, IndexError):
            self.error = "CORRUPT UNDO STATE"
            self.status = self.error
            self.undo_state = None
            return False
        self.undo_state = None
        self.undo_label = ""
        self.status = "UNDID " + label
        return True

    def clear(self) -> None:
        """Clear the entire stack."""
        self.stack[0] = 0.0
        self.stack[1] = 0.0
        self.stack[2] = 0.0
        self.stack[3] = 0.0
        self.entry = ""
        self.entering = False
        self.lift_on_entry = False
        self.error = ""
        self.status = "STACK CLEARED"

    def clear_x(self) -> None:
        """Clear only the X register."""
        self.stack[0] = 0.0
        self.entry = ""
        self.entering = False
        self.lift_on_entry = False
        self.error = ""
        self.status = "X CLEARED - C/ESC AGAIN: ALL"

    def reset(self) -> None:
        """Clear error state and restore consistent calculator state."""
        self.error = ""
        self.entry = ""
        self.entering = False
        self.lift_on_entry = False
        self.status = "RESET - READY"

    def _dismiss_error(self) -> None:
        """Clear any pending error."""
        self.error = ""

    def _set_error(self, message: str) -> None:
        """Set an error message and status."""
        self.error = message
        self.status = message
        self.entry = ""
        self.entering = False

    def _lift(self) -> None:
        """Rotate stack Y→Z, Z→X, X→Y."""
        x, y, z = self.stack[0], self.stack[1], self.stack[2]
        self.stack[3] = z
        self.stack[2] = y
        self.stack[1] = x

    def _begin_entry(self) -> None:
        self._dismiss_error()
        if self.lift_on_entry:
            self._lift()
        self.entry = ""
        self.stack[0] = 0.0
        self.entering = True
        self.lift_on_entry = False

    def _sync_entry(self):
        if self.entry in ("", "-", ".", "-."):
            self.stack[0] = 0.0
        else:
            try:
                self.stack[0] = float(self.entry)
            except (ValueError, OverflowError):
                self._set_error("Invalid number")

    def _commit_entry(self):
        if self.entering:
            self._sync_entry()
            self.entry = ""
            self.entering = False

    def digit(self, digit: str) -> None:
        """Add a digit to the current entry."""
        if not self.entering:
            self._begin_entry()
        digits = len(self.entry) - self.entry.startswith("-") - ("." in self.entry)
        if digits >= 15:
            self.status = "ENTRY LIMIT"
            return
        if self.entry in ("0", "-0") and "." not in self.entry:
            self.entry = "-" + digit if self.entry.startswith("-") else digit
        else:
            self.entry += digit
        self._sync_entry()
        self.status = "ENTER VALUE"

    def decimal(self) -> None:
        """Add a decimal point to the current entry."""
        if not self.entering:
            self._begin_entry()
        if "." not in self.entry:
            self.entry = (self.entry if self.entry else "0") + "."
        self._sync_entry()
        self.status = "ENTER VALUE"

    def backspace(self) -> None:
        self._dismiss_error()
        if not self.entering:
            self.stack[0] = 0.0
            self.lift_on_entry = False
            self.status = "X CLEARED"
            return
        self.entry = self.entry[:-1]
        if self.entry in ("", "-"):
            self.entry = ""
            self.entering = False
        self._sync_entry()
        self.status = "EDIT X"

    def enter(self):
        self._dismiss_error()
        self._commit_entry()
        self._lift()
        self.entry = ""
        self.entering = False
        self.lift_on_entry = False
        self.status = "X ENTERED"

    def drop(self):
        self._dismiss_error()
        self._commit_entry()
        self.stack[0] = self.stack[1]
        self.stack[1] = self.stack[2]
        self.stack[2] = self.stack[3]
        self.lift_on_entry = True
        self.status = "STACK DROP"

    def swap(self):
        self._dismiss_error()
        self._commit_entry()
        self.stack[0], self.stack[1] = self.stack[1], self.stack[0]
        self.lift_on_entry = True
        self.status = "X / Y SWAPPED"

    def negate(self):
        self._dismiss_error()
        if self.entering:
            if self.entry.startswith("-"):
                self.entry = self.entry[1:]
            else:
                self.entry = "-" + (self.entry if self.entry else "0")
            self._sync_entry()
        else:
            self.stack[0] = -self.stack[0]
            self.lift_on_entry = True
        self.status = "SIGN CHANGED"

    def percent(self):
        """Replace X with X percent of Y and retain Y for + or -."""
        self._dismiss_error()
        self._commit_entry()
        try:
            # Scale before multiplying: the final percentage may be finite
            # even when Y * X would overflow (or prematurely underflow).
            x, x_power = frexp(self.stack[0])
            y, y_power = frexp(self.stack[1])
            result = ldexp(x * y / 100.0, x_power + y_power)
            if abs(result) == float("inf") or result != result:
                raise OverflowError
        except (OverflowError, ValueError):
            self._set_error("OVERFLOW")
            return
        self.stack[0] = result
        self.lift_on_entry = True
        self.status = "Y RETAINED: USE + OR -"

    def unary(self, action):
        self._dismiss_error()
        self._commit_entry()
        x = self.stack[0]
        try:
            if action == "square":
                result = x * x
                label = "X SQUARED"
            elif action == "sqrt":
                if x < 0:
                    self._set_error("SQRT DOMAIN")
                    return
                result = sqrt(x)
                label = "SQUARE ROOT"
            else:
                if x == 0:
                    self._set_error("DIVIDE BY ZERO")
                    return
                result = 1.0 / x
                label = "RECIPROCAL"
            if abs(result) == float("inf") or result != result:
                raise OverflowError
        except (OverflowError, ValueError):
            self._set_error("OVERFLOW")
            return
        self.stack[0] = result
        self.lift_on_entry = True
        self.status = label

    def binary(self, action):
        self._dismiss_error()
        self._commit_entry()
        x, y = self.stack[0], self.stack[1]
        try:
            if action == "add":
                result = y + x
                label = "ADD"
            elif action == "subtract":
                result = y - x
                label = "SUBTRACT"
            elif action == "multiply":
                result = y * x
                label = "MULTIPLY"
            else:
                if x == 0:
                    self._set_error("DIVIDE BY ZERO")
                    return
                result = y / x
                label = "DIVIDE"
            if abs(result) == float("inf") or result != result:
                raise OverflowError
        except (OverflowError, ValueError):
            self._set_error("OVERFLOW")
            return
        self.stack[0] = result
        self.stack[1] = self.stack[2]
        self.stack[2] = self.stack[3]
        self.lift_on_entry = True
        self.status = label

    def store(self, index):
        """Store X in the named variable without changing the stack."""
        self._dismiss_error()
        self._commit_entry()
        # Bounds checking for variable indices
        if not (0 <= index < len(self.variables)):
            self._set_error("Invalid variable")
            return
        self.variables[index] = self.stack[0]
        self.variable_set[index] = True
        self.lift_on_entry = True
        self.status = "STO " + chr(ord("A") + index)

    def recall(self, index):
        """Lift the stack and recall the named variable into X."""
        self._dismiss_error()
        # Bounds checking for variable indices
        if not (0 <= index < len(self.variables)):
            self._set_error("Invalid variable")
            return False
        name = chr(ord("A") + index)
        if not self.variable_set[index]:
            self.status = "RCL " + name + ": EMPTY"
            return False
        self._commit_entry()
        self._lift()
        self.stack[0] = self.variables[index]
        self.entry = ""
        self.entering = False
        self.lift_on_entry = True
        self.status = "RCL " + name
        return True

    def clear_variable(self, index):
        """Clear one named variable without affecting the stack."""
        self.variables[index] = 0.0
        self.variable_set[index] = False
        self.status = "CLEARED " + chr(ord("A") + index)

    def display(self, level):
        if level == 0 and self.entering:
            return self.entry if self.entry not in ("", "-") else "0"
        return format_number(self.stack[level])


calculator = None
standard_calculator = None
financial_calculator = None
financial = None


def _reset_session():
    """Reset transient UI, caches and storage bookkeeping, separate from data."""
    global fin_overlay, fin_selection, fin_recall, fin_message, selected_index
    global help_visible, help_page, variable_view_mode, selected_variable, variable_confirm_action
    global variable_confirm_index, escape_armed, back_exit_armed, flash_index, flash_until
    global storage, state_dirty, save_due, last_saved_state, help_cache
    global fin_menu_cache, fin_panel_key, amort_job, state_recovery, save_error
    fin_overlay = None
    fin_selection = 0
    fin_recall = False
    fin_message = ()
    selected_index = ENTER_INDEX
    help_visible = False
    help_page = 0
    variable_view_mode = None
    selected_variable = 0
    variable_confirm_action = None
    variable_confirm_index = -1
    escape_armed = False
    back_exit_armed = False
    flash_index = -1
    flash_until = 0
    storage = None
    state_dirty = False
    save_due = 0
    last_saved_state = ""
    help_cache = None
    fin_menu_cache = None
    fin_panel_key = None
    amort_job = None
    state_recovery = False
    save_error = ""


def _state_checksum(text):
    # FNV-1a detects accidental storage corruption; not an authentication tag.
    # Saved calculator JSON is ASCII. Byte iteration avoids allocating a
    # one-character string and calling ord() for every character. Keep the
    # original code-point checksum for any legacy non-ASCII text as well.
    data = text.encode()
    if len(data) != len(text):
        data = map(ord, text)
    value = 2166136261
    for byte in data:
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return "%08x" % value


def _save_failed():
    return bool(save_error) or calculator.status.startswith("SAVE FAILED:")


def _display_status():
    if amort_job is not None:
        return calculator.status
    if save_error:
        return save_error
    if calculator.status.startswith("SAVE FAILED:"):
        return calculator.status
    return "RCL: SELECT KEY" if financial.mode and fin_recall else calculator.error or calculator.status


def _state_json():
    """Serialize the complete calculator memory for the next app cycle."""
    # Keep the top-level memory as Standard, regardless of the visible mode.
    state_data = standard_calculator.snapshot()
    state_data.update({"version": STATE_VERSION,
                       "financial_stack": financial_calculator.snapshot(),
                       "financial": financial.snapshot()})
    serialized = json.dumps(state_data)
    checksum = _state_checksum(serialized)
    serialized = serialized[:-1] + ', "_checksum": "' + checksum + '"}'
    if len(serialized) > MAX_STATE_BYTES:
        raise ValueError("SAVE TOO LARGE")
    return serialized


def _load_state():
    """Prefer the committed save, then recover from a verified previous save."""
    global state_recovery
    state_recovery = False
    if storage is None:
        return False
    for path in (STATE_FILE, STATE_BACKUP, STATE_TEMP):
        if _load_state_file(path):
            if path != STATE_FILE:
                state_recovery = True
                calculator.status = "MEMORY RECOVERED"
                _queue_save()
            return True
    return False


def _load_state_file(path):
    global last_saved_state, financial, calculator, standard_calculator, financial_calculator
    if not storage.exists(path):
        return False
    try:
        if storage.size(path) > MAX_STATE_BYTES:
            return False
        raw = storage.read(path, "r")
        saved = json.loads(raw)
        if "_checksum" in saved:
            prefix, _ = raw.rsplit(', "_checksum": ', 1)
            if saved["_checksum"] != _state_checksum(prefix + "}"):
                return False
        if saved.get("version") not in (1, 2, STATE_VERSION):
            return False


        restored_financial = FinancialState.restored(saved.get("financial", {}))
        restored_standard = RPNStack.restored(saved)
        if saved.get("version") == STATE_VERSION:
            restored_working = RPNStack.restored(saved["financial_stack"])
        elif saved.get("version") == 2:
            # Version 2 shared one stack: retain it in both independent memories.
            restored_working = RPNStack.restored(saved)
        else:
            restored_working = RPNStack()
            restored_financial.pending = False
        # Apply only after both memories and financial registers validate.
        financial = restored_financial
        standard_calculator = restored_standard
        financial_calculator = restored_working
        calculator = financial_calculator if financial.mode else standard_calculator
        last_saved_state = raw
        if saved.get("version") != STATE_VERSION or "_checksum" not in saved:
            _queue_save()
        return True
    except (AttributeError, KeyError, TypeError, ValueError, OSError, OverflowError):
        return False


def _queue_save():
    """Defer state writes briefly so rapid key entry does not wear the SD card."""
    global state_dirty, save_due
    state_dirty = True
    save_due = ticks_add(ticks_ms(), SAVE_DELAY_MS)


def _write_verified_state(path, serialized):
    if not storage.write(path, serialized, "w"):
        raise OSError("SAVE FAILED")
    if (not storage.exists(path) or storage.size(path) != len(serialized)
            or storage.read(path, "r") != serialized):
        raise OSError("SAVE VERIFY FAILED")


def _clear_save_error():
    global fin_menu_cache, save_error
    if _save_failed():
        if calculator.status.startswith("SAVE FAILED:"):
            calculator.status = "MEMORY SAVED"
        save_error = ""
        fin_menu_cache = None


def _save_state(force=False):
    """Write changed calculator memory to Picoware's SD settings folder."""
    global state_dirty, last_saved_state, state_recovery, fin_menu_cache, save_error
    if storage is None or calculator is None or (not force and not state_dirty):
        return False
    try:
        serialized = _state_json()
        if serialized == last_saved_state and not state_recovery:
            state_dirty = False
            _clear_save_error()
            return True
        # Stage and read back before touching the committed file. Retain a
        # verified previous state throughout a partial write or power loss.
        state_recovery = True
        _write_verified_state(STATE_TEMP, serialized)
        if last_saved_state:
            previous = last_saved_state
            if ', "_checksum": ' not in previous:
                previous = previous[:-1] + ', "_checksum": "' + _state_checksum(previous) + '"}'
            _write_verified_state(STATE_BACKUP, previous)
        _write_verified_state(STATE_FILE, serialized)
        last_saved_state = serialized
        state_recovery = False
        state_dirty = False
        _clear_save_error()
        return True
    except (OSError, TypeError, ValueError) as error:
        # Back off retries while retaining every pending value.
        _queue_save()
        save_error = "SAVE FAILED: " + (str(error) or "STORAGE ERROR")
        calculator.status = save_error
        fin_menu_cache = None
        return False


FIN_TOP = {
    "tvm": (("N", "@N"), ("I/YR", "@I/YR"), ("PV", "@PV"), ("PMT", "@PMT"),
            ("FV", "@FV"), ("P/YR", "@P/YR"), ("SOLVE", "solve_menu"), ("MORE", "more")),
    "interest": (("NOM", "@NOM"), ("EFF", "@EFF"), ("P/YR", "@P/YR"), ("MORE", "more"),
                 ("REGS", "registers"), ("FIX", "decimals"), ("TVM", "page:tvm"), ("B/E", "begin")),
    "amort": (("FROM", "@FIRST"), ("TO", "@LAST"), ("CALC", "amortize"), ("MORE", "more"),
              ("REGS", "registers"), ("FIX", "decimals"), ("TVM", "page:tvm"), ("B/E", "begin")),
    "cash": (("CF0", "@CF0"), ("AMT", "@AMT"), ("TIMES", "@TIMES"), ("EDIT", "cashlist"),
             ("I/YR", "@I/YR"), ("NPV", "npv"), ("IRR", "irr"), ("MORE", "more")),
    "margin": (("COST", "@COST"), ("PRICE", "@PRICE"), ("MARG", "@MARG"), ("MORE", "more"),
               ("REGS", "registers"), ("FIX", "decimals"), ("TVM", "page:tvm"), ("B/E", "begin")),
    "markup": (("COST", "@COST"), ("PRICE", "@PRICE"), ("MARK", "@MARK"), ("MORE", "more"),
               ("REGS", "registers"), ("FIX", "decimals"), ("TVM", "page:tvm"), ("B/E", "begin")),
}
FIN_TAIL = (
    ("7", "7", "number"), ("8", "8", "number"), ("9", "9", "number"), ("/", "divide", "operator"),
    ("4", "4", "number"), ("5", "5", "number"), ("6", "6", "number"), ("*", "multiply", "operator"),
    ("1", "1", "number"), ("2", "2", "number"), ("3", "3", "number"), ("-", "subtract", "operator"),
    ("+/-", "negate", "function"), ("0", "0", "number"), (".", "decimal", "number"), ("+", "add", "operator"),
    ("RCL", "fin_recall", "memory"), ("ENTER", "enter", "enter"), ("UNDO", "undo", "function"), ("MODE", "mode", "function"),
)
FIN_KEYS = {page: tuple((label, action, "memory") for label, action in top) + FIN_TAIL
            for page, top in FIN_TOP.items()}
FIN_KEYS["tvm"] = FIN_KEYS["tvm"][:-1] + (("CLR TVM", "confirm_tvm", "function"),)
FIN_MENU = (("Time value of money", "page:tvm"), ("Amortization", "page:amort"),
            ("Interest conversion", "page:interest"), ("Cash flows", "page:cash"),
            ("Margin", "page:margin"), ("Markup", "page:markup"),
            ("Registers / full precision", "registers"), ("Decimal places", "decimals"),
            ("Clear financial", "confirm_clear"), ("Solve register", "solve_menu"),
            ("Toggle BEGIN / END", "begin"), ("Mode / Help", "mode"))
FIN_ENTER_ACTIONS = ("more", "solve_menu", "confirm_tvm")
FIN_HELP = (
    (("FINANCIAL MODE", COLOR_AMBER),
     ("F switches Standard / Financial.", TFT_WHITE),
     ("MODE or MORE > Mode / Help opens Help.", TFT_WHITE),
     ("Type a value, select its register, then press SPACE to STORE.", TFT_WHITE),
     ("CTRL + small key number stores X directly, without moving selection. Numbers follow the current page.", TFT_WHITE),
     ("Register keys always STORE X. SOLVE selects an unknown to calculate.", TFT_WHITE),
     ("RCL then a register recalls. No RETURN needed to store.", TFT_WHITE),
     ("RETURN opens highlighted MORE, SOLVE or CLR TVM; elsewhere it duplicates X into Y.", TFT_WHITE),
     ("C / CLR TVM clears N, I/YR, PV, PMT and FV after confirmation. Stack unchanged; UNDO restores TVM.", TFT_WHITE),
     ("Receipts positive; payments negative.", COLOR_AMBER),
     ("N counts periods. I/YR is annual %. P/YR defaults to 12.", TFT_WHITE),
     ("MORE > Toggle BEGIN / END sets payment timing; B/E on other pages toggles it.", TFT_WHITE),
     ("Loan: N=12, I/YR=0, PV=1200, FV=0; solve PMT=-100.", TFT_WHITE),
     ("Savings: N=1, P/YR=1, I/YR=5, PV=-1000, PMT=0; FV=1050.", TFT_WHITE)),
    (("MORE FINANCIAL TOOLS", COLOR_AMBER),
     ("Amortization: FROM/TO store X; CALC totals that payment range.", TFT_WHITE),
     ("Principal and interest use cash-flow signs. Balance follows PV's sign.", TFT_WHITE),
     ("Payments and interest round each period to FIX decimals.", TFT_WHITE),
     ("Interest: NOM/EFF convert annual rates using P/YR; TVM rate stays unchanged.", TFT_WHITE),
     ("Margin: (PRICE-COST)/PRICE * 100.", TFT_WHITE),
     ("Markup: (PRICE-COST)/COST * 100.", TFT_WHITE),
     ("Store known values; use MORE > Solve register for the unknown.", TFT_WHITE),
     ("REGS shows full precision; FIX sets 0-9 decimal places (default 2).", TFT_WHITE),
     ("Display rounding changes no values except amortization calculations.", TFT_WHITE)),
    (("CASH FLOWS", COLOR_AMBER),
     ("CF0 is time zero. EDIT selects, adds or deletes later groups.", TFT_WHITE),
     ("AMT stores X in the selected group; TIMES sets its repeat count.", TFT_WHITE),
     ("RCL then CF0/AMT/TIMES recalls. Space alone always stores X.", TFT_WHITE),
     ("NPV discounts at I/YR with P/YR periods/year. IRR returns annual nominal %.", TFT_WHITE),
     ("IRR uses I/YR as its guess. Multiple sign changes: result may not be unique.", COLOR_AMBER),
     ("No solution? Check signs or enter another I/YR guess.", TFT_WHITE),
     ("Limits: 50 groups after CF0; repeats and N up to 1,000,000.", TFT_WHITE),
     ("Amortization TO <= 100,000; P/YR 1-10,000. Counts must be whole.", TFT_WHITE),
     ("UNDO restores one financial change. Clear financial asks first.", TFT_WHITE),
     ("Mode, settings and cash flows save with the RPN stack.", TFT_WHITE)),
)


def _keys():
    return FIN_KEYS[financial.page] if financial.mode else KEYS


def _fin_format(value):
    value = _finite(value)
    # Do not allocate hundreds of fixed-point digits for extreme inputs.
    if abs(value) >= 1e14:
        return "%.8E" % value
    return "%.*f" % (financial.decimals, value)


def _fin_rows():
    v = financial.values
    if financial.page == "cash":
        i = financial.cash_index
        amount, count = financial.flows[i]
        rows = [("CF", str(i)), ("AMT", _fin_format(amount)), ("TIMES", str(count)),
                ("I/YR", _fin_format(v["I/YR"]))]
        if financial.cash_result:
            name, result, warning = financial.cash_result
            rows.append((name + ("!" if warning else ""), _fin_format(result)))
        return rows
    if financial.page == "amort":
        rows = [("FROM", str(int(v["FIRST"]))), ("TO", str(int(v["LAST"])))]
        if financial.amort_result:
            rows.extend((name, _fin_format(value)) for name, value in
                        zip(("PRIN", "INT", "BAL"), financial.amort_result))
        return rows
    names = {"tvm": ("N", "I/YR", "PV", "PMT", "FV"),
             "interest": ("NOM", "EFF"), "margin": ("COST", "PRICE", "MARG"),
             "markup": ("COST", "PRICE", "MARK")}[financial.page]
    return [(name, _fin_format(v[name])) for name in names]


def _draw_header(draw):
    width = int(draw.size.x)
    draw.fill_rectangle(Vector(0, 0), Vector(width, 20), COLOR_BG)
    if financial.mode and calculator.entering:
        # Keep all 15 editable digits visible even on the Cardputer panel.
        draw.text(Vector(7, 6), "X " + calculator.entry, TFT_WHITE, FONT_XTRA_SMALL)
        _right_text(draw, width - 7, 6, "FIN", COLOR_AMBER, FONT_XTRA_SMALL)
    else:
        draw.text(Vector(7, 6), "SimpleRPN", TFT_WHITE, FONT_SMALL)
        if financial.mode:
            draw.text(Vector(90, 9), "FIN " + financial.page.upper(), COLOR_AMBER, FONT_XTRA_SMALL)
        elif width >= 240:
            draw.text(Vector(90, 9), "4-LEVEL", COLOR_MUTED, FONT_XTRA_SMALL)
        if not financial.mode:
            draw.fill_rectangle(Vector(width - 14, 8), Vector(6, 6), COLOR_AMBER)


def _financial_intent(recalling):
    """Register activation is explicit, independent of entry history."""
    return "RCL" if recalling else "STO"


def _financial_preview():
    """Describe the selected register action without consuming input intent."""
    label, action, _ = _keys()[selected_index]
    if action.startswith("@"):
        intent = _financial_intent(fin_recall)
        return ("STO X>" if intent == "STO" else intent + " ") + label
    if fin_recall:
        return "RCL READY"
    return "STO READY"


def _draw_financial(draw, partial=False):
    global fin_panel_key
    key = (id(draw), int(draw.size.x), int(draw.size.y), financial.page)
    partial = partial and financial.page == "tvm" and fin_panel_key == key
    _draw_header(draw)
    (x, y, w, h), _ = _layout(draw)
    if not partial:
        draw.fill_rectangle(Vector(x + 2, y + 3), Vector(w, h), COLOR_SHADOW)
        draw.fill_rectangle(Vector(x, y), Vector(w, h), COLOR_EDGE)
        draw.fill_rectangle(Vector(x + 2, y + 2), Vector(w - 4, h - 4), COLOR_LCD)
    settings = "P%d %s D%d" % (financial.values["P/YR"], "BGN" if financial.begin else "END", financial.decimals)
    # Long P/YR settings are abbreviated here and fully shown in REGS.
    settings_x = _draw_register_label_number(draw, x + 5, y + 4, "P/YR", not partial)
    if partial:
        draw.fill_rectangle(Vector(settings_x, y + 4), Vector(x + w - 2 - settings_x, 9), COLOR_LCD)
    settings, font = _fit_value(draw, settings, x + w - 5 - settings_x, FONT_XTRA_SMALL)
    draw.text(Vector(settings_x, y + 4), settings, COLOR_LCD_MID, font)
    for row, (name, value) in enumerate(_fin_rows()):
        row_y = y + 15 + row * 9
        label_x = _draw_register_label_number(draw, x + 5, row_y, name, not partial)
        value_left = label_x + 4 + draw.len(name, FONT_XTRA_SMALL)
        if partial:
            draw.fill_rectangle(Vector(value_left, row_y), Vector(x + w - 2 - value_left, 9), COLOR_LCD)
        else:
            draw.text(Vector(label_x, row_y), name, COLOR_LCD_MID, FONT_XTRA_SMALL)
        _right_text(draw, x + w - 5, row_y, value, COLOR_LCD_DARK, FONT_XTRA_SMALL, value_left)
    x_y = y + 61
    if partial:
        draw.fill_rectangle(Vector(x + 16, x_y), Vector(w - 18, 9), COLOR_LCD)
        # Preview and status can shrink, wrap, or change color independently.
        draw.fill_rectangle(Vector(x + 2, y + 71), Vector(w - 4, h - 73), COLOR_LCD)
    else:
        draw.text(Vector(x + 5, x_y), "X", COLOR_LCD_MID, FONT_XTRA_SMALL)
    value = calculator.entry if calculator.entering else _fin_format(calculator.stack[0])
    _right_text(draw, x + w - 5, x_y, value, COLOR_LCD_DARK, FONT_XTRA_SMALL,
                x + 16, calculator.entering)
    draw.text(Vector(x + 5, y + 71), _financial_preview(), COLOR_LCD_DARK, FONT_XTRA_SMALL)
    status = _display_status()
    lines = _wrap_text(draw, status, w - 10)
    if len(lines) > 2:
        lines = lines[:2]
        last = lines[-1]
        while last and draw.len(last + "...", FONT_XTRA_SMALL) > w - 10:
            last = last[:-1]
        lines[-1] = last + "..."
    for row, line in enumerate(lines):
        draw.text(Vector(x + 5, y + h - 5 - len(lines) * 9 + row * 9), line,
                  COLOR_ERROR if calculator.error and amort_job is None else COLOR_LCD_MID, FONT_XTRA_SMALL)
    fin_panel_key = key


def _fin_menu_items():
    if fin_overlay == "mode":
        return (("Standard", "standard"), ("Financial", "financial"), ("Help", "help"))
    if fin_overlay == "more":
        return FIN_MENU
    if fin_overlay == "solve_menu":
        if financial.page not in ("tvm", "interest", "margin", "markup"):
            return (("Choose TVM, Interest, Margin or Markup first", "close"),)
        return tuple(("Solve " + label, "solve:" + action[1:])
                     for label, action, _ in _keys()
                     if action.startswith("@") and action != "@P/YR")
    if fin_overlay == "decimals":
        return tuple((str(i) + " decimal places", "digits:" + str(i)) for i in range(10))
    if fin_overlay == "registers":
        names = ("N", "I/YR", "PV", "PMT", "FV", "P/YR", "NOM", "EFF",
                 "COST", "PRICE", "MARG", "MARK", "FIRST", "LAST")
        rows = [(name + " = %.15g" % financial.values[name], "noop") for name in names]
        rows.extend((("Timing: " + ("BEGIN" if financial.begin else "END"), "noop"),
                     ("Decimals: " + str(financial.decimals), "noop"),
                     ("X = %.15g" % calculator.stack[0], "noop"),
                     ("Y = %.15g" % calculator.stack[1], "noop"),
                     ("Z = %.15g" % calculator.stack[2], "noop"),
                     ("T = %.15g" % calculator.stack[3], "noop"),
                     ("Status: " + _display_status(), "noop")))
        if financial.cash_result and financial.cash_result[2]:
            rows.append(("IRR MAY NOT BE UNIQUE", "noop"))
        return rows
    if fin_overlay == "cashlist":
        rows = [("CF%d = %.15g x%d" % (i, value, count), "cash:" + str(i))
                for i, (value, count) in enumerate(financial.flows)]
        rows.extend((("Add group from X", "cash_add"), ("Delete selected group", "confirm_delete")))
        return rows
    if fin_overlay == "confirm_tvm":
        return (("Cancel", "close"), ("Clear N, I/YR, PV, PMT, FV? YES", "clear_tvm"))
    if fin_overlay == "confirm_clear":
        return (("Cancel", "close"), ("Clear all financial data? YES", "clear_financial"))
    if fin_overlay == "confirm_delete":
        return (("Cancel", "cashlist"), ("Delete CF%d? YES" % financial.cash_index, "cash_delete"))
    return tuple((line, "close") for line in fin_message) or (("Back", "close"),)


def _open_fin_menu(view_manager, name):
    global fin_overlay, fin_selection, flash_index, fin_recall, fin_menu_cache
    fin_menu_cache = None
    fin_overlay = name
    fin_selection = (financial.decimals if name == "decimals" else
                     financial.cash_index if name == "cashlist" else 0)
    flash_index = -1
    fin_recall = False
    _draw_fin_menu(view_manager)


def _draw_fin_menu(view_manager):
    global fin_menu_cache, fin_panel_key
    fin_panel_key = None
    draw = view_manager.draw
    width, height = int(draw.size.x), int(draw.size.y)
    draw.clear(size=draw.size, color=COLOR_BG)
    title = {"mode": "MODE", "more": "FINANCIAL", "registers": "REGISTERS",
             "decimals": "DECIMAL PLACES", "cashlist": "CASH FLOW EDITOR",
             "confirm_clear": "CLEAR FINANCIAL", "confirm_delete": "DELETE GROUP",
             "confirm_tvm": "CLEAR TVM", "solve_menu": "SOLVE REGISTER", "message": "FINANCIAL MESSAGE"}.get(fin_overlay, "FINANCIAL")
    draw.fill_rectangle(Vector(0, 0), Vector(width, 20), COLOR_KEY_OP)
    draw.text(Vector(5, 5), title, TFT_WHITE, FONT_XTRA_SMALL)
    save_failed = _save_failed()
    banner_height = 13 if save_failed else 0
    if save_failed:
        draw.text(Vector(5, 23), "SAVE FAILED - RETRYING", COLOR_ERROR, FONT_XTRA_SMALL)
    key = (fin_overlay, width, height, save_failed)
    if fin_menu_cache is None or fin_menu_cache[0] != key:
        items = _fin_menu_items()
        available = height - 49 - banner_height
        pages, page, used = [], [], 0
        for i, (label, action) in enumerate(items):
            lines = _wrap_text(draw, label, width - 18)
            size = len(lines) * 9 + 4
            if page and used + size > available:
                pages.append(page)
                page, used = [], 0
            page.append((i, lines, size))
            used += size
        if page:
            pages.append(page)
        fin_menu_cache = (key, items, pages)
    else:
        _, items, pages = fin_menu_cache
    page_index = next(n for n, page in enumerate(pages)
                      if any(i == fin_selection for i, _, _ in page))
    visible = pages[page_index]
    _right_text(draw, width - 5, 5, "%d/%d" % (page_index + 1, len(pages)),
                TFT_WHITE, FONT_XTRA_SMALL)
    y = 24 + banner_height
    for i, lines, size in visible:
        selected = i == fin_selection
        if selected:
            draw.fill_rectangle(Vector(4, y), Vector(width - 8, size), COLOR_AMBER)
        for row, line in enumerate(lines):
            draw.text(Vector(8, y + 2 + row * 9), line,
                      COLOR_LCD_DARK if selected else TFT_WHITE, FONT_XTRA_SMALL)
        y += size
    draw.text(Vector(5, height - 22), "UP/DN SELECT  ENTER ACT", COLOR_MUTED, FONT_XTRA_SMALL)
    draw.text(Vector(5, height - 11), "ESC/BACK CLOSE", COLOR_MUTED, FONT_XTRA_SMALL)
    draw.swap()


def _set_fin_mode(view_manager, enabled):
    global fin_overlay, fin_recall, flash_index, selected_index, help_visible, escape_armed
    global calculator, back_exit_armed
    escape_armed = back_exit_armed = False
    financial.mode = enabled
    calculator = financial_calculator if enabled else standard_calculator
    fin_overlay = None
    fin_recall = False
    help_visible = False
    flash_index = -1
    selected_index = 25 if enabled else ENTER_INDEX
    _queue_save()
    _redraw(view_manager)


def _fin_input_value():
    if calculator.entering:
        return _finite(float(calculator.entry))
    return _finite(calculator.stack[0])


def _fin_complete_x(value, lift=False):
    if lift:
        calculator._lift()
    calculator.stack[0] = value
    calculator.entry = ""
    calculator.entering = False
    calculator.lift_on_entry = True
    calculator.error = ""


def _commit_financial(view_manager, updated, status, result=None, recalling=False,
                      stored=False, undo_label=None, redraw=False):
    """Commit a validated financial change with one Undo snapshot and redraw."""
    global financial, fin_recall, fin_overlay, flash_index
    old_page, old_overlay, old_flash = financial.page, fin_overlay, flash_index
    calculator.remember_undo(undo_label or status)
    financial = updated
    fin_recall, fin_overlay, flash_index = False, None, -1
    if result is not None:
        _fin_complete_x(result, recalling)
    elif stored:
        # Match Standard STO: commit the current entry without an RPN Enter/lift.
        calculator._commit_entry()
        calculator.lift_on_entry = True
    calculator.error = ""
    calculator.status = status
    _queue_save()
    if redraw or old_overlay is not None or old_page != financial.page:
        _redraw(view_manager)
    else:
        _refresh_stack(view_manager, False)
        if old_flash >= 0:
            _draw_key(view_manager.draw, old_flash, old_flash == selected_index)
        view_manager.draw.swap()


def _financial_action(view_manager, action):
    """Route financial UI; validate on a copy before changing saved state."""
    global fin_recall, fin_overlay, selected_index, flash_index, amort_job, escape_armed
    # A clear-all confirmation is valid only until another action occurs.
    if action != "clear":
        escape_armed = False
    if action in ("mode", "more", "registers", "decimals", "cashlist", "confirm_clear", "confirm_delete", "solve_menu", "confirm_tvm"):
        _open_fin_menu(view_manager, action)
        return True
    if action in ("standard", "financial"):
        _set_fin_mode(view_manager, action == "financial")
        return True
    if action == "close":
        fin_overlay = None
        _redraw(view_manager)
        return True
    if action == "noop":
        return True
    if action == "help":
        _open_help(view_manager)
        return True
    if action == "fin_recall":
        fin_recall = not fin_recall
        _refresh_stack(view_manager)
        return True
    if action.startswith("page:"):
        financial.page = action[5:]
        fin_overlay, fin_recall, flash_index = None, False, -1
        selected_index = 25
        _queue_save()
        _redraw(view_manager)
        return True
    if action.startswith("cash:"):
        financial.cash_index = int(action[5:])
        fin_overlay = None
        _queue_save()
        _redraw(view_manager)
        return True
    if not (action.startswith("@") or action.startswith("solve:") or action.startswith("digits:") or action in
            ("begin", "amortize", "npv", "irr", "cash_add", "cash_delete", "clear_financial", "clear_tvm")):
        return False
    try:
        updated = financial.clone()
        result, recalling, stored = None, False, False
        status = ""
        if action.startswith("@"):
            name = action[1:]
            cash_field = name in ("CF0", "AMT", "TIMES")
            index = 0 if name == "CF0" else updated.cash_index
            intent = _financial_intent(fin_recall)
            if intent == "RCL":
                result = updated.flows[index][1 if name == "TIMES" else 0] if cash_field else updated.values[name]
                recalling = True
                status = "RCL " + name
            elif intent == "STO":
                value = _fin_input_value()
                if cash_field:
                    if name == "TIMES":
                        value = _whole(value, 1, MAX_FIN_PERIODS)
                        if index == 0 and value != 1:
                            raise ValueError("CF0 HAS NO REPEATS")
                    updated.flows[index][1 if name == "TIMES" else 0] = value
                    updated.cash_result = None
                else:
                    updated.store(name, value)
                stored, status = True, "STO " + name
            updated.pending = False
        elif action.startswith("solve:"):
            name = action[6:]
            result = updated.solve(name)
            updated.store(name, result)
            updated.pending = False
            status = "CALC " + name
        elif action == "begin":
            updated.begin = not updated.begin
            updated.amort_result = None
            status = "BEGIN" if updated.begin else "END"
        elif action.startswith("digits:"):
            updated.decimals = int(action[7:])
            updated.amort_result = None
            status = "FIX " + str(updated.decimals)
        elif action == "amortize":
            if updated.values["LAST"] > 360:
                amort_job = (updated, updated.amortization_steps(), calculator.status, ticks_add(ticks_ms(), -250))
                _advance_amortization(view_manager)
                return True
            updated.amort_result = updated.amortization()
            result = updated.amort_result[2]
            updated.pending = False
            status = "PRINCIPAL / INTEREST / BALANCE"
        elif action in ("npv", "irr"):
            if action == "npv":
                result, warning = updated.npv(), False
            else:
                result, warning = updated.irr()
            updated.cash_result = (action.upper(), result, warning)
            updated.pending = False
            status = "IRR MAY NOT BE UNIQUE" if warning else "CALC " + action.upper()
        elif action == "cash_add":
            if len(updated.flows) > MAX_CASH_GROUPS:
                raise ValueError("CASH FLOW CAPACITY: 50 GROUPS")
            updated.flows.append([_fin_input_value(), 1])
            updated.cash_index = len(updated.flows) - 1
            updated.cash_result = None
            updated.pending = False
            stored, status = True, "ADDED CF" + str(updated.cash_index)
        elif action == "cash_delete":
            if updated.cash_index == 0:
                raise ValueError("CF0 CANNOT BE DELETED; STORE 0")
            del updated.flows[updated.cash_index]
            updated.cash_index = min(updated.cash_index, len(updated.flows) - 1)
            updated.cash_result = None
            status = "GROUP DELETED"
        elif action == "clear_tvm":
            for name in ("N", "I/YR", "PV", "PMT", "FV"):
                updated.store(name, 0.0)
            status = "TVM CLEARED"
        elif action == "clear_financial":
            updated = FinancialState()
            updated.mode = financial.mode
            status = "FINANCIAL CLEARED"
        _commit_financial(view_manager, updated, status, result, recalling, stored)
    except (ValueError, OverflowError, ZeroDivisionError) as error:
        _financial_error(view_manager, error)
    return True


def _advance_amortization(view_manager):
    global amort_job
    updated, steps, previous_status, last_draw = amort_job
    started = ticks_ms()
    try:
        while True:
            progress, result = next(steps)
            if result is not None:
                updated.amort_result = result
                updated.pending = False
                amort_job = None
                _commit_financial(view_manager, updated, "PRINCIPAL / INTEREST / BALANCE",
                                  result[2], undo_label="AMORTIZATION", redraw=True)
                return
            if ticks_diff(ticks_ms(), started) >= 8:
                break
        now = ticks_ms()
        if ticks_diff(now, last_draw) >= 250:
            calculator.status = "CALC %d%% ESC CANCEL" % (progress * 100 // updated.values["LAST"])
            _refresh_stack(view_manager)
            amort_job = (updated, steps, previous_status, now)
    except (ValueError, OverflowError, ZeroDivisionError) as error:
        amort_job = None
        calculator.status = previous_status
        _financial_error(view_manager, error)


def _financial_error(view_manager, error):
    global fin_message
    reason = str(error) if isinstance(error, ValueError) else "DIVISION BY ZERO" if isinstance(error, ZeroDivisionError) else "OVERFLOW"
    fin_message = (reason or "INVALID INPUT", "Previous values retained.")
    _open_fin_menu(view_manager, "message")


def _run_fin_menu(view_manager, button):
    global fin_selection, fin_overlay
    if button in (BUTTON_BACK, BUTTON_ESCAPE):
        fin_overlay = None
        _redraw(view_manager)
    elif button in (BUTTON_UP, BUTTON_LEFT, BUTTON_DOWN, BUTTON_RIGHT):
        count = len(fin_menu_cache[1]) if fin_menu_cache else len(_fin_menu_items())
        fin_selection = (fin_selection + (-1 if button in (BUTTON_UP, BUTTON_LEFT) else 1)) % count
        _draw_fin_menu(view_manager)
    elif button in (BUTTON_CENTER, BUTTON_SPACE, BUTTON_EQUAL, BUTTON_TAB):
        items = fin_menu_cache[1] if fin_menu_cache else _fin_menu_items()
        _financial_action(view_manager, items[fin_selection][1])


def _wrap_text(draw, text, width, font=FONT_XTRA_SMALL):
    """Wrap words, splitting long tokens only when necessary."""
    lines = []
    line = ""
    for word in text.split():
        candidate = line + " " + word if line else word
        if draw.len(candidate, font) <= width:
            line = candidate
            continue
        if line:
            lines.append(line)
        line = ""
        for char in word:
            if line and draw.len(line + char, font) > width:
                lines.append(line)
                line = ""
            line += char
    if line:
        lines.append(line)
    return lines or [""]


def _fit_value(draw, text, width, preferred=FONT_SMALL, entry=False):
    font = preferred
    while font > FONT_XTRA_SMALL and draw.len(text, font) > width:
        font -= 1
    if draw.len(text, font) <= width:
        return text, font
    if not entry:
        try:
            for precision in range(7, -1, -1):
                compact = ("%.*e" % (precision, float(text))).replace("e", "E")
                if draw.len(compact, font) <= width:
                    return compact, font
        except ValueError:
            pass
    while text and draw.len("<" + text, font) > width:
        text = text[1:]
    return "<" + text, font


def _right_text(draw, right, y, text, color, font_size, left=0, entry=False):
    text, font_size = _fit_value(draw, text, right - left, font_size, entry)
    draw.text(Vector(right - draw.len(text, font_size), y), text, color, font_size)


def _layout(draw):
    """Shared panel and keypad geometry, including decoration footprints."""
    width, height = int(draw.size.x), int(draw.size.y)
    side = width > height and height < 240
    top = 21 if side else 25
    gap = 3
    if side:
        panel_w = max(88, (width - 15) * 2 // 5)
        panel_h = height - top - 5
        key_x = panel_w + 10
        key_y = top
        key_area_w = width - key_x - 5
    else:
        panel_w = width - 10
        # Financial panels include an action preview below X and two status lines.
        panel_h = min(113, max(104 if financial.mode else 83, height - top - 120))
        key_x = 5
        key_y = top + panel_h + 7
        key_area_w = width - 10
    key_w = (key_area_w - 3 * gap - 2) // 4
    key_h = (height - key_y - 5 - 6 * gap - 2) // 7
    return (5, top, panel_w, panel_h), (key_x, key_y, gap, key_w, key_h)


def _draw_stack(draw, width):
    if financial.mode:
        _draw_financial(draw)
        return
    panel, _ = _layout(draw)
    x, y, w, h = panel
    draw.fill_rectangle(Vector(x + 2, y + 3), Vector(w, h), COLOR_SHADOW)
    draw.fill_rectangle(Vector(x, y), Vector(w, h), COLOR_EDGE)
    draw.fill_rectangle(Vector(x + 2, y + 2), Vector(w - 4, h - 4), COLOR_LCD)
    status_lines = _wrap_text(draw, _display_status(), w - 12)
    status_rows = len(status_lines)
    row_h = (h - 12 - status_rows * 9) // 4
    for row, label in enumerate(("T", "Z", "Y", "X")):
        row_y = y + 5 + row * row_h
        draw.text(Vector(x + 5, row_y), label, COLOR_LCD_MID, FONT_XTRA_SMALL)
        preferred = FONT_MEDIUM if row == 3 and row_h >= 18 else FONT_SMALL
        if row_h < 14:
            preferred = FONT_XTRA_SMALL
        _right_text(draw, x + w - 6, row_y, calculator.display(3 - row),
                    COLOR_LCD_DARK, preferred, x + 16,
                    row == 3 and calculator.entering)
    status_y = y + h - 5 - status_rows * 9
    for line in status_lines:
        draw.text(Vector(x + 6, status_y), line,
                  COLOR_ERROR if calculator.error and amort_job is None else COLOR_LCD_MID, FONT_XTRA_SMALL)
        status_y += 9


def _key_geometry(draw):
    return _layout(draw)[1]


# Compact 3x5 digits reserve space even on the Cardputer's narrow keys.
_SHORTCUT_DIGITS = ((2, 6, 2, 2, 7), (7, 1, 7, 4, 7), (7, 1, 7, 1, 7),
                    (5, 5, 7, 1, 1), (7, 4, 7, 1, 7), (7, 4, 7, 5, 7))


def _register_shortcut(index):
    if not financial.mode or not _keys()[index][1].startswith("@"):
        return 0
    return sum(1 for _, action, _ in _keys()[:index + 1] if action.startswith("@"))


def _draw_shortcut_number(draw, x, y, number, color):
    for row, bits in enumerate(_SHORTCUT_DIGITS[number - 1]):
        for col in range(3):
            if bits & (4 >> col):
                draw.fill_rectangle(Vector(x + col, y + row), Vector(1, 1), color)


def _draw_register_label_number(draw, x, y, label, paint=True):
    """Return the label origin after its matching keypad shortcut number."""
    for index, (key_label, action, _) in enumerate(_keys()):
        if key_label == label and action.startswith("@"):
            if paint:
                _draw_shortcut_number(draw, x, y + 1, _register_shortcut(index), COLOR_LCD_MID)
            return x + 6
    return x


def _draw_key(draw, index, selected, flashed=False):
    margin, keypad_y, gap, key_width, key_height = _key_geometry(draw)
    row = index // 4
    col = index % 4
    x = margin + col * (key_width + gap)
    y = keypad_y + row * (key_height + gap)
    text, _, key_type = _keys()[index]

    # Clear only this key's outline and shadow; the next outline starts one pixel later.
    draw.fill_rectangle(
        Vector(x - 1, y - 1),
        Vector(key_width + 3, key_height + 3),
        COLOR_BG,
    )

    if flashed:
        color = COLOR_AMBER
    elif key_type in ("operator", "enter"):
        color = COLOR_KEY_OP
    elif key_type in ("function", "memory"):
        color = COLOR_KEY_FN
    else:
        color = COLOR_KEY

    draw.fill_rectangle(Vector(x + 2, y + 2), Vector(key_width, key_height), COLOR_SHADOW)
    draw.fill_rectangle(Vector(x, y), Vector(key_width, key_height), color)
    draw.line_custom(
        Vector(x + 1, y + 1),
        Vector(x + key_width - 2, y + 1),
        COLOR_KEY_TOP,
    )

    if selected:
        draw.rect(Vector(x - 1, y - 1), Vector(key_width + 2, key_height + 2), COLOR_AMBER)
        draw.rect(Vector(x, y), Vector(key_width, key_height), COLOR_AMBER)

    number = _register_shortcut(index)
    inset = 6 if number else 0
    if draw.len(text, FONT_XTRA_SMALL) > key_width - inset:
        text = COMPACT_KEY_LABELS.get(text, text)
    font_size = FONT_XTRA_SMALL
    if key_height >= 20 and draw.len(text, FONT_SMALL) <= key_width - inset - 2:
        font_size = FONT_SMALL
    font_height = 12 if font_size == FONT_SMALL else 8
    text_x = x + inset + (key_width - inset - draw.len(text, font_size)) // 2
    text_y = y + (key_height - font_height) // 2
    text_color = COLOR_LCD_DARK if flashed else TFT_WHITE
    draw.text(Vector(text_x, text_y), text, text_color, font_size)
    if number:
        _draw_shortcut_number(draw, x + 2, y + 2, number, text_color)


def _redraw(view_manager):
    global fin_panel_key
    fin_panel_key = None
    draw = view_manager.draw
    width = draw.size.x
    draw.clear(size=draw.size, color=COLOR_BG)

    if not financial.mode:
        _draw_header(draw)
    _draw_stack(draw, width)

    for index in range(len(KEYS)):
        _draw_key(draw, index, index == selected_index)
    draw.swap()


def _variable_layout(draw):
    width, height = int(draw.size.x), int(draw.size.y)
    if variable_view_mode in ("store", "recall"):
        controls = "A-Z SELECT  ENTER/=/SPACE ACT"
        close = "ARROWS SELECT  ESC/BACK/DEL CANCEL"
    else:
        controls = "ENTER/= RCL  SPACE STORE?"
        close = "DEL CLEAR?  ESC/BACK CLOSE"
    footer = [("SAVE FAILED - RETRYING", COLOR_ERROR)] if _save_failed() else []
    for text, color in ((calculator.status, COLOR_AMBER),
                        (controls, COLOR_MUTED), (close, COLOR_MUTED)):
        for line in _wrap_text(draw, text, width - 14):
            footer.append((line, color))
    footer_y = height - 5 - len(footer) * 9
    columns = 1 if width < 240 else 2
    rows = min(13 if columns == 2 else 26, max(1, (footer_y - 32) // 18))
    return columns, rows, footer_y, footer


def _draw_variable_viewer(view_manager):
    global fin_panel_key
    fin_panel_key = None
    draw = view_manager.draw
    width = draw.size.x
    height = draw.size.y
    draw.clear(size=draw.size, color=COLOR_BG)

    if variable_view_mode == "store":
        title = "STO VARIABLE"
    elif variable_view_mode == "recall":
        title = "RCL VARIABLE"
    else:
        title = "VARIABLE VIEWER"

    columns, rows_per_column, footer_y, footer = _variable_layout(draw)
    page_size = rows_per_column * columns
    page_start = (selected_variable // page_size) * page_size
    page_end = page_start + page_size
    if page_end > 26:
        page_end = 26

    draw.fill_rectangle(Vector(0, 0), Vector(width, 23), COLOR_KEY_OP)
    draw.text(Vector(7, 5), title, TFT_WHITE,
              FONT_SMALL if width >= 240 else FONT_XTRA_SMALL)
    range_text = chr(ord("A") + page_start) + "-" + chr(ord("A") + page_end - 1)
    draw.text(
        Vector(width - draw.len(range_text, FONT_XTRA_SMALL) - 7, 8),
        range_text,
        COLOR_AMBER,
        FONT_XTRA_SMALL,
    )

    cell_width = (width - 10 - (columns - 1) * 4) // columns
    for index in range(page_start, page_end):
        offset = index - page_start
        column = offset // rows_per_column
        row = offset % rows_per_column
        x = 5 + column * (cell_width + 4)
        y = 29 + row * 18
        selected = index == selected_variable
        text_color = COLOR_LCD_DARK if selected else TFT_WHITE
        value_color = COLOR_LCD_DARK if selected else COLOR_MUTED

        if selected:
            draw.fill_rectangle(Vector(x, y), Vector(cell_width, 16), COLOR_AMBER)
        else:
            draw.rect(Vector(x, y), Vector(cell_width, 16), COLOR_KEY)

        name = chr(ord("A") + index)
        value = format_number(calculator.variables[index])
        if not calculator.variable_set[index]:
            value = "--"
        draw.text(Vector(x + 4, y + 2), name, text_color, FONT_SMALL)
        _right_text(
            draw,
            x + cell_width - 4,
            y + 4,
            value,
            value_color,
            FONT_XTRA_SMALL,
            x + 18,
        )

    for text, color in footer:
        draw.text(Vector(7, footer_y), text, color, FONT_XTRA_SMALL)
        footer_y += 9
    draw.swap()


def _help_lines(section):
    if section >= HELP_PAGE_COUNT:
        return FIN_HELP[section - HELP_PAGE_COUNT]
    if section == 0:
        lines = (
            ("RPN QUICK START", COLOR_AMBER),
            ("1  Type first value: 2", TFT_WHITE),
            ("2  Press RETURN", TFT_WHITE),
            ("3  Type next value: 3", TFT_WHITE),
            ("4  Press +       result: 5", TFT_WHITE),
            ("THE STACK", COLOR_AMBER),
            ("X  current value / input", TFT_WHITE),
            ("Y  previous value", TFT_WHITE),
            ("Z/T older values", TFT_WHITE),
            ("Operators calculate Y op X", COLOR_AMBER),
            ("Example: 8 RET 2 / -> 4", TFT_WHITE),
            ("No final equals is needed", COLOR_MUTED),
            ("RETURN / = enters X", TFT_WHITE),
            ("F switches financial mode", TFT_WHITE),
            ("Modes keep separate input,", TFT_WHITE),
            ("stacks, A-Z memory and Undo", TFT_WHITE),
            ("MODE chooses mode / help", TFT_WHITE),
            ("H / ESC / BACK  close help", COLOR_MUTED),
            ("LEFT / RIGHT  change help page", COLOR_MUTED),
        )
    elif section == 1:
        lines = (
            ("KEYBOARD", COLOR_AMBER),
            ("RETURN / =  enter / lift", TFT_WHITE),
            ("SPACE / TOUCH  use selected key", TFT_WHITE),
            ("ARROWS       move keypad cursor", TFT_WHITE),
            ("0-9 . + - * / \\  direct input", TFT_WHITE),
            ("BS / DEL     edit entry / clear X", TFT_WHITE),
            ("C            clear TVM (confirm)" if financial.mode else "C / ESC      clear X; again: all", TFT_WHITE),
            ("SYSTEM EXIT KEY x2  exit app", TFT_WHITE),
            ("STACK TOOLS", COLOR_AMBER),
            ("D drop     S swap     Z undo", TFT_WHITE),
            ("N sign     Q sqrt     X square", TFT_WHITE),
            ("R reciprocal       P percent", TFT_WHITE),
            ("FAST OPERATORS", COLOR_AMBER),
            ("U divide          I multiply", TFT_WHITE),
            ("J subtract        K add", TFT_WHITE),
            ("T store  L recall  V vars  H help", TFT_WHITE),
            ("H/ESC/BACK close; LEFT/RIGHT page", COLOR_MUTED),
        )
    else:
        lines = (
            ("MEMORY", COLOR_AMBER),
            ("T / STO    choose variable A-Z", TFT_WHITE),
            ("L / RCL    choose variable A-Z", TFT_WHITE),
            ("V / VARS   open variable viewer", TFT_WHITE),
            ("STO copies X; RCL lifts into X", COLOR_MUTED),
            ("VARIABLE VIEWER", COLOR_AMBER),
            ("A-Z / ARROWS  select variable", TFT_WHITE),
            ("RET / TOUCH / =  recall selected", TFT_WHITE),
            ("SPACE       arm store X", TFT_WHITE),
            ("DEL         arm variable clear", TFT_WHITE),
            ("RET / =     confirm armed action", TFT_WHITE),
            ("ESC / BACK  cancel / close", TFT_WHITE),
            ("Pending STO/RCL: A-Z selects", COLOR_MUTED),
            ("RET / TOUCH / = / SPACE confirms", COLOR_MUTED),
            ("PERCENT", COLOR_AMBER),
            ("200 RET 15 % + -> 230", TFT_WHITE),
            ("Y remains base after % for + / -", COLOR_MUTED),
            ("H/ESC/BACK close; LEFT/RIGHT page", COLOR_MUTED),
        )
    return lines


def _help_pages(draw):
    global help_cache
    key = (int(draw.size.x), int(draw.size.y), financial.mode, _save_failed())
    if help_cache is not None and help_cache[0] == key:
        return help_cache[1]
    font = FONT_SMALL if draw.size.y >= 300 and draw.size.x >= 240 else FONT_XTRA_SMALL
    step = 15 if font == FONT_SMALL else 11
    capacity = max(1, (int(draw.size.y) - 47 - (13 if _save_failed() else 0)) // step)
    pages = []
    start_section = HELP_PAGE_COUNT if financial.mode else 0
    for section in range(start_section, start_section + HELP_PAGE_COUNT):
        page = []
        for text, color in _help_lines(section):
            wrapped = _wrap_text(draw, text, int(draw.size.x) - 16, font)
            # Keep a complete instruction together when it fits on one page.
            needed = len(wrapped) + (1 if color == COLOR_AMBER else 0)
            if page and needed <= capacity and len(page) + needed > capacity:
                pages.append(page)
                page = []
            for line in wrapped:
                if len(page) == capacity:
                    pages.append(page)
                    page = []
                page.append((line, color))
        if page:
            pages.append(page)
    result = (pages, font, step)
    help_cache = (key, result)
    return result


def _open_help(view_manager):
    global fin_overlay, help_visible, help_page, escape_armed, flash_index, fin_recall
    fin_overlay = None
    fin_recall = False
    help_visible, help_page = True, 0
    escape_armed = False
    flash_index = -1
    _draw_help(view_manager)


def _draw_help(view_manager):
    global fin_panel_key, help_page
    fin_panel_key = None
    draw = view_manager.draw
    width, height = int(draw.size.x), int(draw.size.y)
    pages, font, step = _help_pages(draw)
    help_page = min(help_page, len(pages) - 1)
    draw.clear(size=draw.size, color=COLOR_BG)
    draw.fill_rectangle(Vector(0, 0), Vector(width, 23), COLOR_KEY_OP)
    draw.text(Vector(7, 5), "SimpleRPN HELP", TFT_WHITE,
              FONT_SMALL if width >= 240 else FONT_XTRA_SMALL)
    _right_text(draw, width - 7, 7, str(help_page + 1) + "/" + str(len(pages)),
                COLOR_AMBER, FONT_XTRA_SMALL)
    y = 29
    if _save_failed():
        draw.text(Vector(7, y), "SAVE FAILED - RETRYING", COLOR_ERROR, FONT_XTRA_SMALL)
        y += 13
    for text, color in pages[help_page]:
        draw.text(Vector(8, y), text, color, font)
        y += step
    draw.text(Vector(7, height - 12), "L/R PAGE  H/BACK CLOSE", COLOR_MUTED, FONT_XTRA_SMALL)
    draw.swap()


def _reset_variable_confirmation():
    global variable_confirm_action, variable_confirm_index
    variable_confirm_action = None
    variable_confirm_index = -1


def _set_variable_selection_status():
    name = chr(ord("A") + selected_variable)
    if variable_view_mode == "store":
        calculator.status = "STO " + name + ": ENTER TO CONFIRM"
    elif variable_view_mode == "recall":
        calculator.status = "RCL " + name + ": ENTER TO CONFIRM"
    else:
        calculator.status = "SELECTED " + name


def _arm_variable_confirmation(action):
    global variable_confirm_action, variable_confirm_index
    variable_confirm_action = action
    variable_confirm_index = selected_variable
    name = chr(ord("A") + selected_variable)
    if action == "store":
        if calculator.variable_set[selected_variable]:
            calculator.status = "OVERWRITE " + name + "? ENTER YES"
        else:
            calculator.status = "STORE X TO " + name + "? ENTER YES"
    elif calculator.variable_set[selected_variable]:
        calculator.status = "DELETE " + name + "? ENTER/DEL YES"
    else:
        calculator.status = name + " IS ALREADY EMPTY"
        _reset_variable_confirmation()


def _confirm_variable_action(view_manager):
    action = variable_confirm_action
    index = variable_confirm_index
    _reset_variable_confirmation()
    if action == "store" and index >= 0:
        _complete_variable_action(view_manager, index, "store")
        return True
    if action == "delete" and index >= 0:
        calculator.remember_undo("DELETE " + chr(ord("A") + index))
        calculator.clear_variable(index)
        _queue_save()
        _draw_variable_viewer(view_manager)
        return True
    return False


def _open_variable_viewer(view_manager, mode):
    global variable_view_mode, flash_index, escape_armed, fin_recall
    # Named-variable memory starts a separate recall/store interaction.
    fin_recall = False
    variable_view_mode = mode
    _reset_variable_confirmation()
    flash_index = -1
    escape_armed = False
    if mode == "store":
        calculator.status = "STO: CHOOSE A-Z"
    elif mode == "recall":
        calculator.status = "RCL: CHOOSE A-Z"
    else:
        calculator.status = "BROWSE A-Z"
    _draw_variable_viewer(view_manager)


def _close_variable_viewer(view_manager):
    global variable_view_mode, flash_index, escape_armed
    variable_view_mode = None
    _reset_variable_confirmation()
    flash_index = -1
    escape_armed = False
    _redraw(view_manager)


def _complete_variable_action(view_manager, index, action=None):
    """Apply a viewer action, returning True when the viewer closes."""
    global variable_view_mode, selected_variable
    selected_variable = index
    _reset_variable_confirmation()
    action = action or variable_view_mode

    if action == "store":
        calculator.remember_undo("STO " + chr(ord("A") + index))
        calculator.store(index)
        _queue_save()
        if variable_view_mode == "view":
            _draw_variable_viewer(view_manager)
            return False
        variable_view_mode = None
        _redraw(view_manager)
        return True

    if action == "recall":
        if not calculator.variable_set[index]:
            calculator.recall(index)
            _draw_variable_viewer(view_manager)
            return False
        calculator.remember_undo("RCL " + chr(ord("A") + index))
        if not calculator.recall(index):
            _draw_variable_viewer(view_manager)
            return False
        if financial.mode:
            financial.pending = True
        _queue_save()
        variable_view_mode = None
        _redraw(view_manager)
        return True

    return False


def _move_variable_selection(view_manager, button):
    global selected_variable
    _, rows_per_column, _, _ = _variable_layout(view_manager.draw)
    if button == BUTTON_UP:
        selected_variable = (selected_variable - 1) % 26
    elif button == BUTTON_DOWN:
        selected_variable = (selected_variable + 1) % 26
    elif button == BUTTON_LEFT:
        candidate = selected_variable - rows_per_column
        if candidate >= 0:
            selected_variable = candidate
    elif button == BUTTON_RIGHT:
        candidate = selected_variable + rows_per_column
        if candidate < 26:
            selected_variable = candidate


def _key_hint(view_manager):
    action = _keys()[selected_index][1]
    touch = view_manager.input_manager.has_touch_support
    if financial.mode and action.startswith("@"):
        intent = _financial_intent(fin_recall)
        verb = "STORE" if intent == "STO" else "SOLVE" if intent == "CALC" else "RECALL"
        return ("TAP: " if touch else "SPACE: ") + verb
    if financial.mode and action in FIN_ENTER_ACTIONS:
        return "TAP: OPEN" if touch else "RET/SPACE: OPEN"
    return "TAP: USE" if touch else "SPACE: USE RET: ENTER"


def _refresh_stack(view_manager, swap=True):
    if (financial.mode and calculator.entering and _keys()[selected_index][1].startswith("@")
            and calculator.status in ("ENTER VALUE", "EDIT X", "SIGN CHANGED")):
        calculator.status = _key_hint(view_manager)
    draw = view_manager.draw
    if financial.mode:
        _draw_financial(draw, partial=True)
    else:
        _draw_stack(draw, draw.size.x)
    if swap:
        draw.swap()


def _flash_action(view_manager, action):
    global flash_index, flash_until
    draw = view_manager.draw
    index = next((i for i, key in enumerate(_keys()) if key[1] == action), None)
    if index is None:
        draw.swap()
        return
    draw = view_manager.draw
    if flash_index >= 0 and flash_index != index:
        _draw_key(draw, flash_index, flash_index == selected_index)
    flash_index = index
    flash_until = ticks_ms() + 90
    _draw_key(draw, index, index == selected_index, True)
    draw.swap()


def _finish_flash(view_manager):
    global flash_index
    if flash_index < 0 or ticks_diff(ticks_ms(), flash_until) < 0:
        return
    index = flash_index
    flash_index = -1
    draw = view_manager.draw
    _draw_key(draw, index, index == selected_index)
    draw.swap()


def _run_variable_viewer(view_manager, button):
    global selected_variable
    if button in (BUTTON_BACK, BUTTON_ESCAPE):
        if variable_confirm_action is not None:
            _reset_variable_confirmation()
            calculator.status = "ACTION CANCELLED"
            _draw_variable_viewer(view_manager)
            return
        _close_variable_viewer(view_manager)
        return

    if button in (BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT):
        _reset_variable_confirmation()
        _move_variable_selection(view_manager, button)
        _set_variable_selection_status()
        _draw_variable_viewer(view_manager)
        return

    if BUTTON_A <= button <= BUTTON_Z:
        _reset_variable_confirmation()
        index = button - BUTTON_A
        selected_variable = index
        _set_variable_selection_status()
        _draw_variable_viewer(view_manager)
        return

    if button in (BUTTON_BACKSPACE, BUTTON_DELETE):
        if variable_view_mode in ("store", "recall"):
            calculator.status = variable_view_mode.upper() + " CANCELLED"
            _close_variable_viewer(view_manager)
            return
        if (
            variable_confirm_action == "delete"
            and variable_confirm_index == selected_variable
        ):
            _confirm_variable_action(view_manager)
            return
        _arm_variable_confirmation("delete")
        _draw_variable_viewer(view_manager)
        return

    if button in (BUTTON_CENTER, BUTTON_EQUAL):
        if variable_confirm_action is not None:
            _confirm_variable_action(view_manager)
            return
        action = variable_view_mode if variable_view_mode != "view" else "recall"
        _complete_variable_action(view_manager, selected_variable, action)
        return

    if button == BUTTON_SPACE:
        if variable_view_mode != "view":
            _complete_variable_action(view_manager, selected_variable, variable_view_mode)
            return
        _arm_variable_confirmation("store")
        _draw_variable_viewer(view_manager)


def _edit_entry():
    """Apply the shared Back/Backspace/Delete entry edit bookkeeping."""
    global escape_armed
    calculator.backspace()
    if financial.mode:
        financial.pending = calculator.entering
    escape_armed = False
    _queue_save()


def _perform_clear():
    global escape_armed
    if escape_armed:
        calculator.clear()
        escape_armed = False
    else:
        calculator.remember_undo("CLEAR")
        calculator.clear_x()
        if financial.mode:
            calculator.status = "X CLEARED - ESC AGAIN: ALL"
        escape_armed = True
    if financial.mode:
        financial.pending = False
    _queue_save()


def _perform(action):
    if action and action[0] >= "0" and action[0] <= "9" and len(action) == 1:
        calculator.digit(action)
    elif action == "decimal":
        calculator.decimal()
    elif action == "enter":
        calculator.remember_undo("ENTER")
        calculator.enter()
        if financial.mode and not calculator.error:
            calculator.status = "X COPIED TO Y"
    elif action == "undo":
        calculator.undo()
    elif action == "clear":
        _perform_clear()
        return
    elif action == "drop":
        calculator.remember_undo("DROP")
        calculator.drop()
    elif action == "swap":
        calculator.remember_undo("SWAP")
        calculator.swap()
    elif action == "negate":
        calculator.remember_undo("SIGN")
        calculator.negate()
    elif action == "percent":
        calculator.remember_undo("PERCENT")
        calculator.percent()
    elif action in ("square", "sqrt", "reciprocal"):
        calculator.remember_undo(action.upper())
        calculator.unary(action)
    elif action in ("add", "subtract", "multiply", "divide"):
        calculator.remember_undo(action.upper())
        calculator.binary(action)
    else:
        return
    if financial.mode and action not in ("enter", "undo") and not calculator.error:
        financial.pending = True
    _queue_save()


def start(view_manager):
    global calculator, financial, storage, selected_index, standard_calculator, financial_calculator
    _reset_session()
    financial = FinancialState()
    standard_calculator = RPNStack()
    financial_calculator = RPNStack()
    calculator = standard_calculator
    storage = view_manager.storage
    if not _load_state():
        calculator.status = "TRY: 2 RET 3 + -> 5"
    selected_index = 25 if financial.mode else ENTER_INDEX
    view_manager.input_manager.reset()
    _redraw(view_manager)
    return True


def run(view_manager):
    global selected_index, help_visible, help_page, escape_armed, back_exit_armed
    global flash_index, fin_recall
    global amort_job
    inp = view_manager.input_manager
    button = inp.button
    if amort_job is not None:
        if button in (BUTTON_ESCAPE, BUTTON_BACK):
            calculator.status = amort_job[2]
            amort_job = None
            _redraw(view_manager)
        else:
            _advance_amortization(view_manager)
        inp.reset()
        return
    if button == -1:
        if state_dirty and storage is not None and ticks_diff(ticks_ms(), save_due) >= 0:
            previous_status, previous_save_error = calculator.status, save_error
            saved = _save_state()
            if not saved or calculator.status != previous_status or save_error != previous_save_error:
                if fin_overlay is not None:
                    _draw_fin_menu(view_manager)
                elif help_visible:
                    _draw_help(view_manager)
                elif variable_view_mode is not None:
                    _draw_variable_viewer(view_manager)
                else:
                    _refresh_stack(view_manager)
        if not help_visible and variable_view_mode is None and fin_overlay is None:
            _finish_flash(view_manager)
        return

    if button != BUTTON_BACK:
        back_exit_armed = False

    if variable_view_mode is not None:
        _run_variable_viewer(view_manager, button)
        inp.reset()
        return

    if button == BUTTON_F:
        _set_fin_mode(view_manager, not financial.mode)
        inp.reset()
        return

    if fin_overlay is not None:
        if button == BUTTON_H:
            _financial_action(view_manager, "help")
        else:
            _run_fin_menu(view_manager, button)
        inp.reset()
        return

    if BUTTON_CTRL_0 is not None and BUTTON_CTRL_0 <= button <= BUTTON_CTRL_0 + 9:
        if financial.mode and not help_visible:
            number = button - BUTTON_CTRL_0
            for index in range(len(_keys())):
                if number and _register_shortcut(index) == number:
                    # The shortcut always stores, even if RCL was armed.
                    fin_recall = False
                    action = _keys()[index][1]
                    _financial_action(view_manager, action)
                    if fin_overlay is None:
                        _flash_action(view_manager, action)
                    break
        inp.reset()
        return

    if fin_recall and button in (BUTTON_ESCAPE, BUTTON_BACK):
        fin_recall = False
        inp.reset()
        _refresh_stack(view_manager)
        return

    if help_visible:
        if button in (BUTTON_H, BUTTON_ESCAPE, BUTTON_BACK):
            help_visible = False
            flash_index = -1
            inp.reset()
            _redraw(view_manager)
            return
        if button == BUTTON_LEFT:
            help_page = (help_page - 1) % len(_help_pages(view_manager.draw)[0])
            inp.reset()
            _draw_help(view_manager)
            return
        if button == BUTTON_RIGHT:
            help_page = (help_page + 1) % len(_help_pages(view_manager.draw)[0])
            inp.reset()
            _draw_help(view_manager)
            return
        inp.reset()
        return

    if button == BUTTON_H:
        inp.reset()
        _open_help(view_manager)
        return

    if button == BUTTON_BACK:
        if calculator.entering:
            _edit_entry()
            back_exit_armed = False
            inp.reset()
            _refresh_stack(view_manager)
            return
        escape_armed = False
        if not back_exit_armed:
            back_exit_armed = True
            calculator.status = "BACK AGAIN: EXIT"
            inp.reset()
            _refresh_stack(view_manager)
            return
        back_exit_armed = False
        if storage is not None and not _save_state(force=True):
            inp.reset()
            _refresh_stack(view_manager)
            return
        inp.reset()
        view_manager.back()
        return

    action = None
    direct_action = False
    old_selected_index = selected_index
    if button == BUTTON_LEFT:
        selected_index = (selected_index - 1) % len(KEYS)
    elif button == BUTTON_RIGHT:
        selected_index = (selected_index + 1) % len(KEYS)
    elif button == BUTTON_UP:
        selected_index = (selected_index - 4) % len(KEYS)
    elif button == BUTTON_DOWN:
        selected_index = (selected_index + 4) % len(KEYS)
    elif button == BUTTON_CENTER:
        # Return opens financial menus; otherwise preserve the RPN Enter key.
        selected_action = _keys()[selected_index][1]
        if inp.has_touch_support or (financial.mode and selected_action in FIN_ENTER_ACTIONS):
            action = selected_action
        else:
            action = "enter"
        direct_action = not inp.has_touch_support
    elif button == BUTTON_SPACE:
        action = _keys()[selected_index][1]
        direct_action = True
    elif button == BUTTON_TAB:
        action = _keys()[selected_index][1]
    elif BUTTON_0 <= button <= BUTTON_9:
        action = str(button - BUTTON_0)
        direct_action = True
    elif button == BUTTON_PERIOD:
        action = "decimal"
        direct_action = True
    elif button in (BUTTON_SLASH, BUTTON_BACKSLASH):
        action = "divide"
        direct_action = True
    elif button == BUTTON_ASTERISK:
        action = "multiply"
        direct_action = True
    elif button == BUTTON_MINUS:
        action = "subtract"
        direct_action = True
    elif button == BUTTON_PLUS:
        action = "add"
        direct_action = True
    elif button == BUTTON_EQUAL:
        action = "enter"
        direct_action = True
    elif button == BUTTON_PERCENT:
        action = "percent"
        direct_action = True
    elif button in (BUTTON_BACKSPACE, BUTTON_DELETE):
        _edit_entry()
        _refresh_stack(view_manager)
    elif button == BUTTON_ESCAPE:
        _perform_clear()
        _refresh_stack(view_manager, False)
        _flash_action(view_manager, "clear")
    elif button == BUTTON_C:
        action = "confirm_tvm" if financial.mode else "clear"
        direct_action = True
    elif button == BUTTON_D:
        action = "drop"
        direct_action = True
    elif button == BUTTON_I:
        action = "multiply"
        direct_action = True
    elif button == BUTTON_J:
        action = "subtract"
        direct_action = True
    elif button == BUTTON_K:
        action = "add"
        direct_action = True
    elif button == BUTTON_L:
        action = "recall"
        direct_action = True
    elif button == BUTTON_N:
        action = "negate"
        direct_action = True
    elif button == BUTTON_P:
        action = "percent"
        direct_action = True
    elif button == BUTTON_Q:
        action = "sqrt"
        direct_action = True
    elif button == BUTTON_R:
        action = "reciprocal"
        direct_action = True
    elif button == BUTTON_S:
        action = "swap"
        direct_action = True
    elif button == BUTTON_T:
        action = "store"
        direct_action = True
    elif button == BUTTON_U:
        action = "divide"
        direct_action = True
    elif button == BUTTON_V:
        action = "variables"
        direct_action = True
    elif button == BUTTON_X:
        action = "square"
        direct_action = True
    elif button == BUTTON_Z:
        action = "undo"
        direct_action = True

    if action is not None:
        if _financial_action(view_manager, action):
            if direct_action and fin_overlay is None and not help_visible and amort_job is None:
                _flash_action(view_manager, action)
            inp.reset()
            return
        if action in ("store", "recall", "variables"):
            mode = action if action != "variables" else "view"
            inp.reset()
            _open_variable_viewer(view_manager, mode)
            return
        _perform(action)
        if action == "undo":
            flash_index = -1
            _redraw(view_manager)
            inp.reset()
            return
        if direct_action:
            _refresh_stack(view_manager, False)
            _flash_action(view_manager, action)
        else:
            _refresh_stack(view_manager)

    if old_selected_index != selected_index:
        escape_armed = False
        calculator.status = _key_hint(view_manager)
        _refresh_stack(view_manager, False)
        draw = view_manager.draw
        if flash_index >= 0:
            _draw_key(draw, flash_index, flash_index == old_selected_index)
            flash_index = -1
        _draw_key(draw, old_selected_index, False)
        _draw_key(draw, selected_index, True)
        draw.swap()

    inp.reset()


def stop(view_manager):
    global calculator, standard_calculator, financial_calculator, financial
    _save_state(force=True)
    calculator = standard_calculator = financial_calculator = financial = None
    _reset_session()
    from gc import collect

    collect()
