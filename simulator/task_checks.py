"""Desktop checks for upstream background tasks and offline WebSockets."""

from time import sleep_ms, ticks_diff, ticks_ms


def _check_websocket_worker(managed, protocol_close):
    import _thread
    import sys
    from picoware.system.thread import ThreadManager
    from picoware.system.websocket import WebSocketAsync

    manager = ThreadManager() if managed else None
    events = []
    finished = []
    stopped = []
    original_start = _thread.start_new_thread

    def on_close():
        events.append("close")

    def on_receive(data):
        events.append(data)
        if not protocol_close and data == "callback-echo":
            deadline = ticks_ms()
            while not stopped:
                assert ticks_diff(ticks_ms(), deadline) < 5000, "close not requested"
                sleep_ms(1)

    def on_start():
        events.append("start")

    def on_tick(client):
        if events == ["start"]:
            events.append("tick")
            assert client.send("callback-echo")
        elif protocol_close and events == ["start", "tick", "callback-echo"]:
            assert client.last_received == "callback-echo"
            client.clear()
            assert client.last_received is None
            # A truncated header exercises the documented ConnectionClosed
            # callback through the real parser, not a mocked recv method.
            sock = client._ws._sock
            sock._response = sock._response[sock._offset:] + b"\x81"
            sock._offset = 0
        sleep_ms(1)

    def start_worker(function, args):
        def tracked_worker():
            try:
                function(*args)
            finally:
                finished.append(True)
        return original_start(tracked_worker, ())

    class ThreadProbe:
        allocate_lock = staticmethod(_thread.allocate_lock)
        stack_size = staticmethod(_thread.stack_size)
        start_new_thread = staticmethod(start_worker)

    ws = WebSocketAsync("ws://example.com/parity", on_receive=on_receive,
                        on_start=on_start, on_tick=on_tick, on_close=on_close,
                        thread_manager=manager)
    try:
        # The raw-thread API exposes no join. Observe the worker returning;
        # close() flags alone cannot establish that it has exited.
        sys.modules["_thread"] = ThreadProbe
        assert ws.connect()
        deadline = ticks_ms()
        while not finished:
            if manager is not None:
                manager.run()
            if not protocol_close and events == ["start", "tick", "callback-echo"]:
                ws.close()
                stopped.append(True)
            assert ticks_diff(ticks_ms(), deadline) < 5000, events
            sleep_ms(1)
        if manager is not None:
            _drain(manager)
        expected = ["start", "tick", "callback-echo"]
        if protocol_close:
            expected.append("close")
        assert events == expected, events
        assert not ws.is_connected and not ws.is_running
    finally:
        sys.modules["_thread"] = _thread
        ws.close()
        stopped.append(True)


def _drain(manager):
    deadline = ticks_ms()
    while not manager.is_idle:
        manager.run()
        assert ticks_diff(ticks_ms(), deadline) < 5000, "background tasks timed out"
        sleep_ms(1)


def check_app_tasks():
    from picoware.system.boards import BOARD_FLIPPER_ZERO, BOARD_ID
    from picoware.system.view_manager import ViewManager

    if BOARD_ID == BOARD_FLIPPER_ZERO:
        print("[sim-check:skip] background apps unsupported on Flipper Zero")
        return

    manager = ViewManager()
    app_path = "picoware/apps/sim_task_probe.py"
    script_path = "picoware/apps/sim_script_probe.py"
    assert not manager.storage.exists(app_path), "app probe path already exists"
    assert not manager.storage.exists(script_path), "script probe path already exists"
    try:
        manager.storage.write(app_path,
                              "events = []\ndef start(vm):\n events.append('start')\n return True\n"
                              "def run(vm):\n events.append('run')\n"
                              "def stop(vm):\n events.append('stop')\n")
        manager.storage.write(script_path,
                              "import sim_task_probe\nsim_task_probe.events.append('script')\n")
        loader = manager.app_loader
        assert loader.run_app_task("sim_task_probe", repeat=3, continuous=True)
        app = loader.load_app("sim_task_probe")
        _drain(manager.thread_manager)
        assert app.events == ["start", "run", "run", "run"], app.events
        assert loader.run_script_task(script_path)
        _drain(manager.thread_manager)
        assert app.events[-1] == "script", app.events
        assert all(task.error is None for task in loader._app_tasks)
        loader.cleanup_tasks()
        assert not loader._app_tasks
    finally:
        manager.storage.remove(app_path)
        manager.storage.remove(script_path)
        manager.__cleanup()
    print("[sim-check:ok] background app start/run, finite repeats, script execution, cleanup")


def check_scheduler():
    from picoware.system.thread import ThreadManager, ThreadTask

    manager = ThreadManager()
    events = []
    paused = manager.every("paused", lambda: events.append("paused"), 1,
                           repeat=1, threaded=False)
    assert manager.pause_task(paused)
    sleep_ms(3)
    manager.run()
    assert not events
    assert manager.resume_task(paused)
    cancelled = manager.once("cancelled", lambda: events.append("cancelled"), delay=100)
    assert manager.remove_task(cancelled)
    assert not manager.has_task(cancelled)
    manager.every("inline", lambda: events.append("inline"), 2,
                  repeat=3, threaded=False, run_immediately=True)
    task = ThreadTask("worker", lambda: events.append("worker"),
                      continuous=True, repeat=3)
    manager.add_task(task)
    _drain(manager)
    assert events.count("paused") == 1, events
    assert events.count("inline") == 3, events
    assert events.count("worker") == 3, events
    assert "cancelled" not in events
    assert task.error is None
    print("[sim-check:ok] scheduler pause/resume, cancellation, inline and threaded repeats")


def check_websocket():
    from picoware.system.websocket import WebSocket

    # A consumed echo must not retain the history of a multiplayer session.
    ws = WebSocket.connect("ws://example.com/parity")
    try:
        for index in range(64):
            message = "echo-" + str(index) + "x" * 128
            assert ws.send(message)
            assert ws.recv() == message
        assert len(ws._sock._response) < 256, "offline WebSocket retains consumed frames"
        assert ws.send("first unread")
        assert ws.send(b"second unread")
        assert ws.recv() == "first unread"
        assert ws.recv() == b"second unread"
        assert ws.recv() == ""
        assert ws.pong(b"probe")
        assert ws._sock.readline() == b""
        assert ws.recv() == ""
        assert ws.is_connected
        assert ws.ping(b"probe")
        assert ws.recv() == "PONG"
        assert ws.send("after-pong")
        assert ws.recv() == "after-pong"
    finally:
        ws.close()

    for managed in (False, True):
        for protocol_close in (False, True):
            _check_websocket_worker(managed, protocol_close)
    print("[sim-check:ok] bounded WebSocket echoes, Pong, direct/managed callbacks and worker exit")
