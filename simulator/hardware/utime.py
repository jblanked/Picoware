import time as _time

from time import ticks_ms, ticks_diff, ticks_add, sleep


def sleep_ms(milliseconds):
    """Sleep while polling simulated machine timers."""
    deadline = _time.time() + max(0, int(milliseconds)) / 1000.0
    while True:
        try:
            from machine import Timer

            Timer.poll_all()
        except ImportError:
            pass
        remaining = deadline - _time.time()
        if remaining <= 0:
            return None
        _time.sleep(min(remaining, 0.001))


def sleep_us(microseconds):
    """Sleep for microseconds without bypassing timer polling."""
    if int(microseconds) > 0:
        sleep_ms(max(1, (int(microseconds) + 999) // 1000))
