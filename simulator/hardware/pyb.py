"""Functional Pyboard timer/PWM model used by the shared IR transmitter."""

from machine import Pin
import sim_runtime
import time

try:
    import _thread
except ImportError:
    _thread = None


class _PWMChannel:
    def __init__(self, timer, number, pin):
        self.timer = timer
        self.number = int(number)
        self.pin = pin
        self.duty = 0

    def pulse_width_percent(self, value=None):
        if value is None:
            return self.duty
        self.duty = max(0, min(100, int(value)))
        return None


class Timer:
    PWM = 3
    _last_channel = None

    def __init__(self, timer_id=-1, freq=-1, **kwargs):
        self.id = int(timer_id)
        self.frequency = int(freq) if freq and int(freq) > 0 else 0
        self._active = False
        self._callback = None
        self._channel = None
        self._period = 0
        self._generation = 0

    def channel(self, number, mode, pin=None, **kwargs):
        if mode != self.PWM:
            raise ValueError("simulator pyb Timer only supports PWM channels")
        self._channel = _PWMChannel(self, number, pin)
        Timer._last_channel = self._channel
        return self._channel

    def init(self, *, period=-1, tick_hz=-1, prescaler=-1, callback=None, freq=-1, **kwargs):
        self._active = True
        self._callback = callback
        self._period = max(1, int(period)) if period >= 0 else 1
        self._generation += 1
        if freq and int(freq) > 0:
            self.frequency = int(freq)
        if self.id == 5 and callback is not None:
            if _thread is None:
                raise RuntimeError("simulator IR timers require thread support")
            token = self._generation
            _thread.start_new_thread(self._dispatch, (token,))
        return None

    def _dispatch(self, token):
        """Wait one timer period, then deliver the hardware callback."""
        time.sleep_us(self._period)
        if not self._active or token != self._generation:
            return
        self._active = False
        channel = Timer._last_channel
        if channel is not None:
            sim_runtime.record_ir_segment(
                self._period,
                channel.duty > 0,
                channel.timer.frequency,
                channel.duty,
            )
        callback = self._callback
        if callback is not None:
            callback(self)

    def deinit(self):
        self._active = False
        self._callback = None
        self._generation += 1
        return None


__all__ = ["Pin", "Timer"]
