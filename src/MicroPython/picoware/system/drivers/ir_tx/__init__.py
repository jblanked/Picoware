# __init__.py Nonblocking IR blaster
# Runs on Pyboard D or Pyboard 1.x (not Pyboard Lite), ESP32, RP2 and Flipper Zero.

# Released under the MIT License (MIT). See LICENSE.
# Source: https://github.com/peterhinch/micropython_ir/

# Copyright (c) 2020-2021 Peter Hinch
from sys import platform
from machine import idle
ESP32 = platform == 'esp32'  # Loboris not supported owing to RMT
RP2 = platform == 'rp2'
try:
    from picoware_boards import BOARD_ID, BOARD_FLIPPER_ZERO
except ImportError:
    BOARD_ID = -1
    BOARD_FLIPPER_ZERO = -2
FLIPPER_ZERO = platform == 'pyboard' and BOARD_ID == BOARD_FLIPPER_ZERO
if ESP32:
    from machine import Pin, PWM
    from esp32 import RMT
elif RP2:
    from .rp2_rmt import RP2_RMT
elif FLIPPER_ZERO:
    from pyb import Pin, Timer
else:
    from pyb import Pin, Timer  # Pyboard does not support machine.PWM

from micropython import const
from array import array
from time import ticks_us, ticks_diff, sleep_ms
# import micropython
# micropython.alloc_emergency_exception_buf(100)


# Shared by NEC
STOP = const(0)  # End of data

# IR abstract base class. Array holds periods in μs between toggling 36/38KHz
# carrier on or off. Physical transmission occurs in an ISR context controlled
# by timer 2 and timer 5. See TRANSMITTER.md for details of operation.
class IR:
    _active_high = True  # Hardware turns IRLED on if pin goes high.
    _space = 0  # Duty ratio that causes IRLED to be off
    timeit = False  # Print timing info

    @classmethod
    def active_low(cls):
        if ESP32:
            raise ValueError('Cannot set active low on ESP32')
        cls._active_high = False
        cls._space = 100

    def __init__(self, pin, cfreq, asize, duty, verbose):
        if ESP32:
            self._rmt = RMT(0, pin=pin, clock_div=80, tx_carrier = (cfreq, duty, 1))
            # 1μs resolution
        elif RP2:  # PIO-based RMT-like device
            self._rmt = RP2_RMT(pin_pulse=None, carrier=(pin, cfreq, duty))  # 1μs resolution
            asize += 1  # Allow for possible extra space pulse
        elif FLIPPER_ZERO:
            self._flipper_freq = cfreq
            self._flipper_duty = duty
        else:  # Pyboard
            if not IR._active_high:
                duty = 100 - duty
            carrier_timer = Timer(2, freq=cfreq)  # Timer 2/pin produces 36/38/40KHz carrier
            self._ch = carrier_timer.channel(1, Timer.PWM, pin=pin)
            self._ch.pulse_width_percent(self._space)  # Turn off IR LED
            # Pyboard: 0 <= pulse_width_percent <= 100
            self._duty = duty
            self._tim = Timer(5)  # Timer 5 controls carrier on/off times
        self._tcb = self._cb  # Pre-allocate
        self._arr = array('H', (0 for _ in range(asize)))  # on/off times (μs)
        self._levels = None
        self._mva = memoryview(self._arr)
        # Subclass interface
        self.verbose = verbose
        self.carrier = False  # Notional carrier state while encoding biphase
        self.aptr = 0  # Index into array
        self._busy = False

    def _cb(self, t):  # T5 callback, generate a carrier mark or space
        self._busy = True
        t.deinit()
        p = self.aptr
        v = self._arr[p]
        if v == STOP:
            self._ch.pulse_width_percent(self._space)  # Turn off IR LED.
            self._busy = False
            return
        if self._levels is None:
            mark = not (p & 1)
        else:
            mark = self._levels[p]
        self._ch.pulse_width_percent(self._duty if mark else self._space)
        if FLIPPER_ZERO:
            self._tim.init(period=v, tick_hz=1_000_000, callback=self._tcb)
        else:
            self._tim.init(prescaler=84, period=v, callback=self._tcb)
        self.aptr += 1

    def busy(self):
        if ESP32:
            return not self._rmt.wait_done()
        if RP2:
            return self._rmt.busy()
        if FLIPPER_ZERO:
            return False
        return self._busy

    def deinit(self):
        if ESP32:
            self._rmt.deinit()
        elif RP2:
            self._rmt.cancel()
        elif FLIPPER_ZERO:
            return
        else:
            self._tim.deinit()
            self._ch.pulse_width_percent(self._space)

    # Public interface
    # Before populating array, zero pointer, set notional carrier state (off).
    def transmit(self, addr, data, toggle=0, validate=False):  # NEC: toggle is unused
        while self.busy():
            idle()
        t = ticks_us()
        if validate:
            if addr > self.valid[0] or addr < 0:
                raise ValueError('Address out of range', addr)
            if data > self.valid[1] or data < 0:
                raise ValueError('Data out of range', data)
            if toggle > self.valid[2] or toggle < 0:
                raise ValueError('Toggle out of range', toggle)
        self.aptr = 0  # Inital conditions for tx: index into array
        self.carrier = False
        self.tx(addr, data, toggle)  # Subclass populates ._arr
        self.trigger()  # Initiate transmission
        if self.timeit:
            dt = ticks_diff(ticks_us(), t)
            print('Time = {}μs'.format(dt))
        sleep_ms(1)  # Ensure ._busy is set prior to return

    # Subclass interface
    def trigger(self):  # Used by NEC to initiate a repeat frame
        if ESP32:
            durations = tuple(self._mva[0 : self.aptr])
            if self._levels is None:
                self._rmt.write_pulses(durations)
            else:
                self._rmt.write_pulses(durations, tuple(self._levels[0 : self.aptr]))
        elif RP2:
            self.append(STOP)
            self._rmt.send(self._arr)
        elif FLIPPER_ZERO:
            from flipper_ir import send

            durations = tuple(self._mva[0 : self.aptr])
            if self._levels is None:
                levels = tuple(not (index & 1) for index in range(self.aptr))
            else:
                levels = tuple(self._levels[0 : self.aptr])
            send(durations, levels, self._flipper_freq, self._flipper_duty)
        else:
            self.append(STOP)
            self.aptr = 0  # Reset pointer
            self._cb(self._tim)  # Initiate physical transmission.

    def append(self, *times):  # Append one or more time peiods to ._arr
        for t in times:
            self._arr[self.aptr] = t
            self.aptr += 1
            self.carrier = not self.carrier  # Keep track of carrier state
            self.verbose and print('append', t, 'carrier', self.carrier)

    def add(self, t):  # Increase last time value (for biphase)
        assert t > 0
        self.verbose and print('add', t)
        # .carrier unaffected
        self._arr[self.aptr - 1] += t


# Given an iterable (e.g. list or tuple) of times, emit it as an IR stream.
class Player(IR):

    def __init__(self, pin, freq=38000, verbose=False, asize=68, duty=33):  # NEC specifies 38KHz
        super().__init__(pin, freq, asize, duty, verbose)

    def play(self, lst, levels=None):
        if levels is not None and len(lst) != len(levels):
            raise ValueError('durations and levels must have the same length')
        self._levels = levels
        count = 0
        for x, t in enumerate(lst):
            self._arr[x] = t
            count = x + 1
        if count == 0:
            return
        self.aptr = count
        self.trigger()
