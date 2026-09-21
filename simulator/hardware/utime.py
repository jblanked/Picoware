from time import ticks_ms, ticks_diff, ticks_add, sleep, sleep_ms, sleep_us
from time import ticks_us as _host_ticks_us


def ticks_us():
    """Return host microseconds, or the next deterministic IR timestamp."""
    try:
        import sim_runtime

        timestamp = sim_runtime.next_ir_timestamp()
        if timestamp is not None:
            return timestamp
    except (ImportError, AttributeError):
        pass
    return _host_ticks_us()
