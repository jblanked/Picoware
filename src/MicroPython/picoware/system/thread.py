from utime import ticks_ms


class Thread:
    """Class representing a thread."""

    def __init__(self, function: callable, args: tuple = ()) -> None:
        from _thread import allocate_lock

        self._args = args
        self._error = None
        self._function = function
        self._lock = allocate_lock()
        self._running = False
        self._stop_requested = False

    def __del__(self):
        self.stop()
        self._args = ()
        self._error = None
        self._function = None

    @property
    def error(self):
        """Get the error if any occurred during thread execution."""
        with self._lock:
            return self._error

    @property
    def is_running(self) -> bool:
        """Check if the thread is running."""
        with self._lock:
            return self._running

    @property
    def should_stop(self) -> bool:
        """Check if stop was requested."""
        with self._lock:
            return self._stop_requested

    def _wrapper(self) -> None:
        try:
            self._function(*self._args)
        except Exception as e:
            with self._lock:
                self._error = e
        finally:
            with self._lock:
                self._running = False
                self._stop_requested = False

    def run(self) -> bool:
        """Run the thread."""
        import _thread

        with self._lock:
            if self._running:
                return False
            try:
                self._running = True
                self._stop_requested = False
                _thread.start_new_thread(self._wrapper, ())
                return True
            except Exception as e:
                self._error = e
                self._running = False
                return False

    def stop(self) -> None:
        """Request the thread to stop."""
        with self._lock:
            self._stop_requested = True


class ThreadTask:
    """Represents a task to be executed by ThreadManager."""

    __slots__ = (
        "args",
        "error",
        "function",
        "_id",
        "name",
        "result",
        "should_stop",
        "start_time",
        "timeout",
    )

    def __init__(
        self, name: str, function: callable, args: tuple = (), timeout: int = 0
    ) -> None:
        self.args = args
        self.error = None
        self.function = function
        self._id = 0
        self.name = name
        self.should_stop = False
        self.start_time = 0
        self.timeout = timeout

    @property
    def id(self) -> int:
        """Get the task ID."""
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        """Set the task ID."""
        self._id = value

    def stop(self) -> None:
        """Request the task to stop."""
        self.should_stop = True


class ThreadManager:
    """Class to manage multiple threads."""

    def __init__(self) -> None:
        self._id = 0
        self._tasks: list[ThreadTask] = []
        self._active_thread: Thread = None
        self._active_task: ThreadTask = None

    @property
    def task(self) -> ThreadTask:
        """Get the currently active task."""
        return self._active_task

    @property
    def thread(self) -> Thread:
        """Get the currently active thread."""
        return self._active_thread

    def add_task(self, task: ThreadTask) -> None:
        """Add a task to the manager."""
        self._tasks.append(task)

    def remove_task(self, task_id: int) -> None:
        """Remove a task from the manager."""
        if task_id in self._tasks:
            self._tasks.remove(task_id)

    def run(self) -> None:
        """Run tasks one-by-one, waiting for each to complete before starting the next."""
        # Check if active thread finished
        if self._active_thread is not None:
            if not self._active_thread.is_running:
                if self._active_task is not None:
                    print(
                        f"[ThreadManager] Task {self._active_task.name} finished after {ticks_ms() - self._active_task.start_time} ms.\n"
                    )
                    # Task finished, capture error if any
                    self._active_task.error = self._active_thread.error
                self._active_thread = None
                self._active_task = None
            elif self._active_task is not None and self._active_task.should_stop:
                # Stop was requested, stop the thread
                self._active_thread.stop()
                self._active_task.error = Exception("Thread task was stopped.")
            elif (
                self._active_task is not None
                and self._active_task.timeout > 0
                and ticks_ms() - self._active_task.start_time
                > self._active_task.timeout
            ):
                # Task timed out, stop it
                self._active_thread.stop()
                self._active_task.error = Exception("Thread task timed out.")

        # Start next task if no active thread
        if self._active_thread is None and self._tasks:
            task = self._tasks.pop(0)
            # Skip task if stop was requested
            if task.should_stop:
                return
            thread = Thread(task.function, task.args)
            if thread.run():
                task.start_time = ticks_ms()
                task.id = self._id
                self._id += 1
                print(f"[ThreadManager] Task {task.name} started.")
                self._active_thread = thread
                self._active_task = task
            else:
                task.error = thread.error
