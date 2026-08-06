"""MBASIC 5.21's random number generator, reproduced exactly.

Read out of `com/mbasic.com` rather than guessed at, and checked against the
binary running under cpmemu: 200 consecutive values, the three argument forms,
and RANDOMIZE all match digit for digit.

It is not the RND from the 6502 Microsoft BASICs, and the constants published
for those (11879546.0 and 3.92767778E-8) do not appear in this image. The
routine lives at 0x37DD and works like this:

    seed = seed * MULTIPLIERS[i8] + ADDENDS[i3]      in single precision

then it takes the three mantissa bytes of that product and puts them back in a
different order, exclusive-ORing one of them:

    high' = low ^ 0x4F        low' = high (as stored, sign bit and all)

sets the exponent so the value lies in [0.5,1), clears the sign, and
normalises. The byte the normaliser shifts in from below - the guard byte - is
the *old exponent* (`MOV B,M` at 0x3824), which is what makes the low bits
come out the way they do; getting that wrong is a two-digit error, and it is
the one thing here nobody would guess.

Two indices walk the constant tables: `i8` counts 0..7 and picks the
multiplier, `i3` cycles 1,2,3 and picks the addend. A third counter runs to
171 and then perturbs three bytes once, which is why a sequence has to be
checked well past 171 values before it can be believed.

Addresses, for anyone reading the image:

    0x37DD  the routine          0x3846  the 171-counter
    0x3847  i3                   0x3848  i8
    0x3849  the eight multipliers, four bytes each
    0x3869  the seed             0x386D  the three addends
    0x37C8  the seed RUN starts from
    0x24AD  RANDOMIZE            0x25DA  the normaliser

A single is stored low byte first: low, mid, high-with-sign, exponent.
"""

import math
import struct

#: Multiplier table at 0x3849, indexed 0..7 by the counter at 0x3848.
MULTIPLIERS = (
    -26514538.0, 16129081.0, -11769122.0, 13098250.0,
    -20161190.0, -10426890.0, -13483109.0, 12482518.0,
)

#: Addend table at 0x386D, indexed 1..3 by the counter at 0x3847. Index 0 is
#: the seed itself, which is why the counter skips it.
ADDENDS = (
    0.0,
    4.626181748790259e-08,
    -6.841145960834183e-08,
    5.723364893128746e-08,
)

#: The seed RUN copies from 0x37C8. Every run of a program starts here, which
#: is why MBASIC gives the same "random" numbers every time unless the program
#: says RANDOMIZE.
INITIAL_SEED = 0.8116351366043091

#: The byte the scramble exclusive-ORs into the high mantissa byte.
SCRAMBLE_XOR = 0x4F

#: The count at which the third counter wraps and perturbs the result.
PERTURB_AT = 0xAB


def _single(value):
    """Round to single precision, the width MBASIC computes in."""
    try:
        return struct.unpack('f', struct.pack('f', value))[0]
    except (OverflowError, struct.error, ValueError):
        return value


def _unpack(value):
    """(low, mid, high-as-stored, exponent byte) of an MBF single."""
    if value == 0:
        return 0, 0, 0, 0
    fraction, exponent = math.frexp(abs(value))
    mantissa = round(fraction * 2 ** 24)
    if mantissa >> 24:                      # rounded up out of 24 bits
        mantissa >>= 1
        exponent += 1
    high = ((mantissa >> 16) & 0x7F) | (0x80 if value < 0 else 0)
    return mantissa & 0xFF, (mantissa >> 8) & 0xFF, high, (exponent + 128) & 0xFF


def _normalise(high, mid, low, guard):
    """The routine at 0x25DA, for a value whose exponent has been forced to
    0x80 and whose sign has been cleared.

    Shifts left until the mantissa's top bit is set, pulling in bits from the
    guard byte, then rounds up if what is left of the guard has its top bit
    set.
    """
    bits = (high << 24) | (mid << 16) | (low << 8) | guard
    if bits == 0:
        return 0.0
    exponent = 0x80
    while not bits & 0x80000000:
        bits = (bits << 1) & 0xFFFFFFFF
        exponent -= 1
    mantissa = bits >> 8
    if bits & 0xFF >= 0x80:                 # CM 2635 - round away from zero
        mantissa += 1
        if mantissa >> 24:
            mantissa >>= 1
            exponent += 1
    return mantissa * 2.0 ** (exponent - 152)


class MbasicRandom:
    """The generator, with the state MBASIC keeps in three counters and a seed."""

    def __init__(self):
        self.reset()

    def reset(self):
        """What RUN does at 0x4358: reload the seed, zero the counters.

        This is why a program that does not say RANDOMIZE gets the same
        numbers every time it is run - on the real machine and now here.
        """
        self.seed = INITIAL_SEED
        self.count = 0          # 0x3846
        self.addend_index = 0   # 0x3847
        self.mult_index = 0     # 0x3848


    def next(self, argument=None):
        """One RND.

        RND and RND(x>0) advance the sequence; RND(0) repeats the last value
        without drawing; RND(x<0) restarts from a value derived from x - and
        only from its mantissa, so RND(-1) and RND(-2) give the same number
        while RND(-1000) does not.
        """
        if argument is not None and argument == 0:
            return self.seed

        if argument is not None and argument < 0:
            # The sign test leaves 0xFF in A, and the negative path writes it
            # to all three counters and scrambles the argument itself.
            self.count = self.addend_index = self.mult_index = 0xFF
            value = _single(argument)
        else:
            self.mult_index = (self.mult_index + 1) & 7
            self.addend_index = self.addend_index + 1 if self.addend_index < 3 else 1
            value = _single(_single(self.seed * MULTIPLIERS[self.mult_index])
                            + ADDENDS[self.addend_index])

        low, mid, high, exponent = _unpack(value)
        new_high = (low ^ SCRAMBLE_XOR) & 0xFF
        new_mid = mid
        new_low = high

        self.count = (self.count + 1) & 0xFF
        if self.count == PERTURB_AT:
            # Once every 171 draws: INR C / DCR D / INR E at 0x3832.
            self.count = 0
            new_high = (new_high + 1) & 0xFF
            new_mid = (new_mid - 1) & 0xFF
            new_low = (new_low + 1) & 0xFF

        self.seed = _normalise(new_high, new_mid, new_low, exponent)
        return self.seed

    def randomize(self, seed):
        """RANDOMIZE n, from 0x24AD.

        The argument becomes a 16-bit integer and replaces the *middle two*
        bytes of the seed - its low byte and exponent are left alone - and then
        one value is drawn and discarded. That is why RANDOMIZE 1 twice in the
        same run does not give the same number twice: what it did not overwrite
        is different the second time.
        """
        n = int(seed) & 0xFFFF
        low, _mid, _high, exponent = _unpack(self.seed)
        self.seed = _mbf(low, n & 0xFF, (n >> 8) & 0xFF, exponent)
        self.next(1)

    # For a statement that has to be run again - see src/statement_attempt.py

    def state(self):
        """Everything a retry would have to put back."""
        return (self.seed, self.count, self.addend_index, self.mult_index)

    def restore(self, state):
        (self.seed, self.count, self.addend_index, self.mult_index) = state


def _mbf(low, mid, high, exponent):
    """Rebuild a value from its four stored bytes."""
    if exponent == 0:
        return 0.0
    mantissa = ((high | 0x80) << 16) | (mid << 8) | low
    return (-1 if high & 0x80 else 1) * mantissa * 2.0 ** (exponent - 152)
