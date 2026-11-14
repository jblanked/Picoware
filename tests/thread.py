"""Demo for the merged ThreadManager scheduler. Run in Thonny on your board.

Needs thread.py saved on the board too (same folder / root).
"""

from utime import sleep_ms, ticks_ms, ticks_diff
from picoware.system.thread import ThreadManager, ThreadTask

tm = ThreadManager()
start = ticks_ms()
beats = 0


def stamp() -> str:
    return f"{ticks_diff(ticks_ms(), start) / 1000:5.1f}s"


def heartbeat():
    """Inline task: runs inside tm.run(), no thread."""
    global beats
    beats += 1
    print(stamp(), "heartbeat", beats)


def legacy_job():
    print(stamp(), "legacy ThreadTask ran on a thread")


def one_shot():
    print(stamp(), "once() fired after 3 seconds")


def slow_worker():
    print(stamp(), "worker start (takes 1.5s)")
    sleep_ms(1500)
    print(stamp(), "worker done")


# Old-style API, now routed through once()
tm.add_task(ThreadTask("legacy", legacy_job))

# New scheduling API
tm.once("one_shot", one_shot, delay=3000)
tm.every("worker", slow_worker, 1000, repeat=3, timeout=5000)  # overlaps -> skipped ticks
heartbeat_id = tm.every("heartbeat", heartbeat, 1000, threaded=False, run_immediately=True)

print("Running... (Ctrl+C / Stop to quit)")
removed = False

while True:
    msg = tm.run()
    if msg:
        print(stamp(), msg.strip())

    # Cancel the repeating heartbeat after 8 seconds
    if not removed and ticks_diff(ticks_ms(), start) > 8000:
        tm.remove_task(heartbeat_id)
        removed = True
        print(stamp(), "heartbeat removed")

    if removed and tm.is_idle:
        print(stamp(), "all done, manager idle")
        break

    sleep_ms(10)