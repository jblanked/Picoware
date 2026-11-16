"""Thread - Threading and scheduling support for Picoware."""

from utime import ticks_ms, ticks_add, ticks_diff
from gc import collect


class Thread:
    """Class representing a thread."""

    __slots__ = (
        "_args",
        "_error",
        "_function",
        "_lock",
        "_running",
        "_stop_requested",
        "_stack_size",
    )

    def __init__(
        self, function: callable, args: tuple = (), stack_size: int = 0
    ) -> None:
        """Initialize the thread.

        Args:
            function (callable): The function to run in the thread.
            args (tuple): Arguments to pass to the function. Defaults to ().
            stack_size (int): Thread stack size in bytes. Defaults to 0.
        """
        self._lock = None
        try:
            import _thread

            self._lock = _thread.allocate_lock()
        except Exception:
            self._lock = None

        self._args = args
        self._error = None
        self._function = function
        self._running = False
        self._stop_requested = False
        self._stack_size = stack_size

    def __del__(self):
        """Stop the thread and release its resources."""
        self.stop()
        self._args = ()
        self._error = None
        self._function = None

    @property
    def error(self):
        """Get the error if any occurred during thread execution.

        Returns:
            Exception: The captured error, or None if none occurred.
        """
        if not hasattr(self, "_lock") or self._lock is None:
            return None

        with self._lock:
            return self._error

    @property
    def is_running(self) -> bool:
        """Check whether the thread is running.

        Returns:
            bool: True if the thread is running, False otherwise.
        """
        if not hasattr(self, "_lock") or self._lock is None:
            return False

        with self._lock:
            return self._running

    @property
    def should_stop(self) -> bool:
        """Check whether stop was requested.

        Returns:
            bool: True if stop was requested, False otherwise.
        """
        if not hasattr(self, "_lock") or self._lock is None:
            return True

        with self._lock:
            return self._stop_requested

    def _wrapper(self) -> None:
        """Run the target function and capture any error."""
        try:
            self._function(*self._args)
        except Exception as e:
            if hasattr(self, "_lock") and self._lock is not None:
                with self._lock:
                    self._error = e
        finally:
            if hasattr(self, "_lock") and self._lock is not None:
                with self._lock:
                    self._running = False
                    self._stop_requested = False

    def run(self) -> bool:
        """Run the thread.

        Returns:
            bool: True if the thread started, False otherwise.
        """
        if self._lock is None:
            return False

        with self._lock:
            if self._running:
                return False
            try:
                import _thread

                self._running = True
                self._stop_requested = False
                if self._stack_size > 0:
                    _thread.stack_size(self._stack_size)
                _thread.start_new_thread(self._wrapper, ())
                return True
            except Exception as e:
                self._error = e
                self._running = False
                return False

    def stop(self) -> None:
        """Request the thread to stop."""
        if self._lock is None:
            return

        with self._lock:
            self._stop_requested = True


class ThreadTask:
    """Represents a task to be executed by ThreadManager."""

    __slots__ = (
        "args",
        "continuous",
        "delay",
        "error",
        "function",
        "_id",
        "interval",
        "limited",
        "name",
        "next_run",
        "passive",
        "paused",
        "remaining",
        "result",
        "run_count",
        "should_stop",
        "stack_size",
        "start_time",
        "threaded",
        "timeout",
    )

    def __init__(
        self,
        name: str,
        function: callable,
        args: tuple = (),
        timeout: int = 0,
        stack_size: int = 0,
        passive: bool = False,
        interval: int = 0,
        delay: int = 0,
        repeat: int = 0,
        threaded: bool = True,
        continuous: bool = False,
    ) -> None:
        """Initialize the task.

        Args:
            name (str): The task name.
            function (callable): The function to run.
            args (tuple): Arguments to pass to the function. Defaults to ().
            timeout (int): Timeout in milliseconds. Defaults to 0.
            stack_size (int): Thread stack size in bytes. Defaults to 0.
            passive (bool): Whether the task is passive (can run simultaneously with other tasks). Defaults to False.
            interval (int): Milliseconds between runs. 0 means run once. Defaults to 0.
            delay (int): Milliseconds before the first run. Defaults to 0.
            repeat (int): Total number of runs for interval tasks. 0 means unlimited. Defaults to 0.
            threaded (bool): Run on a thread (True) or inline inside ThreadManager.run (False). Defaults to True.
            continuous (bool): Run again as soon as the previous run finishes (back-to-back), ignoring interval. delay still applies to the first run, repeat still limits the total. Defaults to False.
        """
        self.args = args
        self.continuous = continuous
        self.delay = delay
        self.error = None
        self.function = function
        self._id = 0
        self.interval = interval
        self.limited = repeat > 0
        self.name = name
        self.next_run = 0
        self.passive = passive
        self.paused = False
        self.remaining = repeat
        self.run_count = 0
        self.should_stop = False
        self.start_time = 0
        self.stack_size = stack_size
        self.threaded = threaded
        self.timeout = timeout

    @property
    def id(self) -> int:
        """Get the task ID.

        Returns:
            int: The task ID.
        """
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        """Set the task ID.

        Args:
            value (int): The new task ID.
        """
        self._id = value

    def stop(self) -> None:
        """Request the task to stop."""
        self.should_stop = True


class ThreadManager:
    """Class to manage and schedule multiple threads.

    Call run() regularly from your main loop. It promotes scheduled tasks
    that are due, then starts queued tasks. Normal tasks share one exclusive
    thread slot and run one at a time. Passive tasks (passive=True) each get
    their own thread and run alongside everything else.
    """

    __slots__ = (
        "_id",
        "_tasks",
        "_queue",
        "_passive",
        "_active_thread",
        "_active_task",
        "_outgoing",
        "_log",
    )

    def __init__(self, log: bool = True) -> None:
        """Initialize the thread manager."""
        self._id = 0
        self._tasks: list[ThreadTask] = []  # scheduled, waiting to become due
        self._queue: list[ThreadTask] = []  # due, waiting to start
        self._passive: list[tuple] = []  # running passive (Thread, ThreadTask) pairs
        self._active_thread: Thread = None
        self._active_task: ThreadTask = None
        self._outgoing = ""
        self._log = log

    @property
    def task(self) -> ThreadTask:
        """Get the currently active task.

        Returns:
            ThreadTask: The active task, or None if no task is running.
        """
        return self._active_task

    @property
    def thread(self) -> Thread:
        """Get the currently active thread.

        Returns:
            Thread: The active thread, or None if no thread is running.
        """
        return self._active_thread

    @property
    def is_idle(self) -> bool:
        """Return whether nothing is scheduled, queued or running.

        Returns:
            bool: True if the manager has no pending or running tasks.
        """
        return (
            self._active_thread is None
            and not self._passive
            and not self._queue
            and not self._tasks
        )

    @property
    def pending_count(self) -> int:
        """Return the number of scheduled or queued tasks, excluding the active task.

        Returns:
            int: The number of pending tasks.
        """
        count = len(self._queue)
        for task in self._tasks:
            if task not in self._queue:
                count += 1
        return count

    def _schedule(self, task: ThreadTask) -> int:
        """Register a task with the scheduler.

        Args:
            task (ThreadTask): The task to schedule.

        Returns:
            int: The assigned task ID.
        """
        task.id = self._id
        self._id += 1
        task.next_run = ticks_add(ticks_ms(), task.delay)
        self._tasks.append(task)
        return task.id

    def once(
        self,
        name: str = "",
        function: callable = None,
        delay: int = 0,
        args: tuple = (),
        task: ThreadTask = None,
        **kwargs,
    ) -> int:
        """Schedule a task to run once after a delay.

        Pass either name/function (a ThreadTask is built for you) or an
        existing ThreadTask via ``task``. An existing task keeps its own
        interval, delay and repeat settings, so a ThreadTask created with
        an interval repeats.

        Args:
            name (str): The task name.
            function (callable): The function to run.
            delay (int): Milliseconds to wait before running (ignored when task is given). Defaults to 0.
            args (tuple): Arguments to pass to the function. Defaults to ().
            task (ThreadTask): An existing task to schedule instead. Defaults to None.
            **kwargs: Extra ThreadTask options (timeout, stack_size, passive, threaded).

        Returns:
            int: The assigned task ID.
        """
        if task is None:
            task = ThreadTask(name, function, args, delay=delay, **kwargs)
        return self._schedule(task)

    def every(
        self,
        name: str,
        function: callable,
        interval: int,
        args: tuple = (),
        run_immediately: bool = False,
        repeat: int = 0,
        **kwargs,
    ) -> int:
        """Schedule a task to run repeatedly.

        Args:
            name (str): The task name.
            function (callable): The function to run.
            interval (int): Milliseconds between runs.
            args (tuple): Arguments to pass to the function. Defaults to ().
            run_immediately (bool): Run on the next run() call instead of waiting one interval. Defaults to False.
            repeat (int): Total number of runs, 0 for unlimited. Defaults to 0.
            **kwargs: Extra ThreadTask options (timeout, stack_size, passive, threaded).

        Returns:
            int: The assigned task ID.
        """
        return self._schedule(
            ThreadTask(
                name,
                function,
                args,
                interval=interval,
                delay=0 if run_immediately else interval,
                repeat=repeat,
                **kwargs,
            )
        )

    def add_task(self, task: ThreadTask) -> int:
        """Add a task to the manager. It runs as soon as the thread slot is free.

        Args:
            task (ThreadTask): The task to add.

        Returns:
            int: The assigned task ID.
        """
        return self.once(task=task)

    def get_task(self, task_id: int) -> ThreadTask:
        """Get a scheduled, queued or running task by ID.

        Args:
            task_id (int): The task ID.

        Returns:
            ThreadTask: The task, or None if not found.
        """
        if self._active_task is not None and self._active_task.id == task_id:
            return self._active_task
        for _, task in self._passive:
            if task.id == task_id:
                return task
        for task in self._tasks:
            if task.id == task_id:
                return task
        for task in self._queue:
            if task.id == task_id:
                return task
        return None

    def has_task(self, task_id: int) -> bool:
        """Check whether a task is scheduled, queued or currently active.

        Args:
            task_id (int): The ID of the task to look for.

        Returns:
            bool: True if the task is known to the manager, False otherwise.
        """
        return self.get_task(task_id) is not None

    def pause_task(self, task_id: int) -> bool:
        """Pause a scheduled task so it stops becoming due.

        Args:
            task_id (int): The task ID.

        Returns:
            bool: True if the task was paused, False if it isn't scheduled.
        """
        for task in self._tasks:
            if task.id == task_id:
                task.paused = True
                return True
        return False

    def resume_task(self, task_id: int) -> bool:
        """Resume a paused task. Its next run is one interval from now.

        Args:
            task_id (int): The task ID.

        Returns:
            bool: True if the task was resumed, False if it isn't scheduled.
        """
        for task in self._tasks:
            if task.id == task_id:
                task.paused = False
                task.next_run = ticks_add(ticks_ms(), task.interval)
                return True
        return False

    def remove_task(self, task_id: int) -> bool:
        """Stop and remove a scheduled or queued task by ID.

        Args:
            task_id (int): The ID of the task to remove.

        Returns:
            bool: True if the task was removed, False otherwise.
        """
        removed = []
        for tasks in (self._tasks, self._queue):
            for index, task in enumerate(tasks):
                if task.id == task_id:
                    task.stop()
                    tasks.pop(index)
                    removed.append(task)
                    break
        return len(removed) > 0

    def _in_flight(self, task: ThreadTask) -> bool:
        """Return whether a task is queued or currently running.

        Args:
            task (ThreadTask): The task to check.

        Returns:
            bool: True if the task is queued, running, or active.
        """
        if self._active_task is task or task in self._queue:
            return True
        for _, running in self._passive:
            if running is task:
                return True
        return False

    def _emit(self, text: str) -> None:
        """Append a message to the outgoing output, newline-separated."""
        if not self._log:
            return
        if self._outgoing and not self._outgoing.endswith("\n"):
            self._outgoing += "\n"
        self._outgoing += text

    def _promote_due(self) -> None:
        """Move due scheduled tasks to the queue (or run them inline)."""
        if not self._tasks:
            return

        now = ticks_ms()
        # Iterate a copy (removals below)
        for task in self._tasks[:]:
            # Drop cancelled tasks
            if task.should_stop:
                self._tasks.remove(task)
                continue
            if task.paused:
                continue
            if task.continuous:
                # No delay after first run
                if task.run_count == 0 and ticks_diff(now, task.next_run) < 0:
                    continue
                if task.threaded and self._in_flight(task):
                    continue
            else:
                if ticks_diff(now, task.next_run) < 0:
                    continue

                if task.interval > 0:
                    # Never burst after a stall
                    next_run = ticks_add(task.next_run, task.interval)
                    if ticks_diff(now, next_run) >= 0:
                        next_run = ticks_add(now, task.interval)
                    task.next_run = next_run

                    # Skip if still running
                    if task.threaded and self._in_flight(task):
                        self._emit(
                            "[ThreadManager] Task %d (%s) skipped, still running.\n"
                            % (task.id, task.name)
                        )
                        continue

            # Clear previous run's error
            if task.run_count > 0:
                task.error = None

            # Count before the call
            task.run_count += 1
            if task.limited:
                task.remaining -= 1

            if task.threaded:
                self._queue.append(task)
            else:
                try:
                    task.function(*task.args)
                except Exception as e:
                    task.error = e
                    self._emit(
                        f'[ThreadManager] Task {task.id} ({task.name}) failed. Error: "{e}"\n'
                    )

            # Drop finished tasks
            if (not task.continuous and task.interval == 0) or (
                task.limited and task.remaining <= 0
            ):
                self._tasks.remove(task)

    def _poll(self, thread: Thread, task: ThreadTask) -> bool:
        """Check on a running task: finish, stop or time it out.

        Args:
            thread (Thread): The task's thread.
            task (ThreadTask): The running task.

        Returns:
            bool: True if the task has finished, False if it is still running.
        """
        if not thread.is_running:
            msg = "[ThreadManager] Task %d (%s) finished after %d ms." % (
                task.id,
                task.name,
                ticks_diff(ticks_ms(), task.start_time),
            )
            # Capture error if any
            thread_error = thread.error
            if thread_error is not None:
                task.error = thread_error
                msg += f' Error: "{thread_error}"'
            self._emit(msg + "\n")
            collect()
            return True
        if task.should_stop:
            # Stop requested
            thread.stop()
            if task.error is None:
                task.error = Exception("Thread task was stopped.")
        elif (
            task.timeout > 0 and ticks_diff(ticks_ms(), task.start_time) > task.timeout
        ):
            # Task timed out, stop it
            task.stop()
            thread.stop()
            task.error = Exception("Thread task timed out.")
        return False

    def run(self) -> str:
        """Check running tasks, promote due scheduled tasks, and start queued ones.

        Normal tasks run one at a time in the exclusive slot. Passive tasks
        start right away on their own threads. A task that finishes can be
        re-queued and started again within the same call.

        Returns:
            str: Any output messages from started, finished, skipped or failed tasks.
        """
        self._outgoing = ""

        # Check passive threads
        for entry in self._passive[:]:
            if self._poll(entry[0], entry[1]):
                self._passive.remove(entry)

        # Check the exclusive thread
        if self._active_thread is not None:
            finished_task = self._active_task
            if self._poll(self._active_thread, finished_task):
                self._active_thread = None
                self._active_task = None

        self._promote_due()

        # Start queued tasks
        slot_busy = self._active_thread is not None
        for task in self._queue[:]:
            if not task.passive:
                if slot_busy:
                    continue
                slot_busy = True
            self._queue.remove(task)
            # Skip stopped tasks
            if task.should_stop:
                continue
            thread = Thread(task.function, task.args, task.stack_size)
            if thread.run():
                task.start_time = ticks_ms()
                self._emit(
                    "[ThreadManager] Task %d (%s) started." % (task.id, task.name)
                )
                if task.passive:
                    self._passive.append((thread, task))
                else:
                    self._active_thread = thread
                    self._active_task = task
            else:
                task.error = thread.error
                self._emit(
                    "[ThreadManager] Failed to start task %s. Error: %s"
                    % (task.name, task.error)
                )
        return self._outgoing
