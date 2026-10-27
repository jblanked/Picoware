class Timer:
    """Timer class to trigger a Python callback function after an expiry time, or periodically at a regular interval.
    
    Args:
        mode (int): The mode of the timer, either ONE_SHOT or PERIODIC.
        callback (callable): The function to call when the timer expires. It must take one argument, which is passed the machine.Timer object.
        interval_ms (int): The interval in milliseconds for the timer.
    """

    ONE_SHOT = 0
    PERIODIC = 1

    __slots__ = ("_mode", "_callback", "_interval", "_timer")
    
    def __init__(self, mode: int = PERIODIC, callback: callable = None, interval_ms: int = 1000):
        self._mode = mode
        self._callback = callback
        self._interval = interval_ms
        self._timer = None

    def __del__(self):
        """Destructor to clean up the timer."""
        self.stop()
        if self._timer is not None:
            del self._timer
        self._timer = None
        self._callback = None

    @property
    def callback(self):
        """Get the callback function of the timer."""
        return self._callback

    @callback.setter
    def callback(self, value: callable):
        """Set the callback function of the timer."""
        self._callback = value

    @property
    def interval(self) -> int:
        """Get the interval of the timer in milliseconds."""
        return self._interval

    @interval.setter
    def interval(self, value: int):
        """Set the interval of the timer in milliseconds."""
        self._interval = value

    @property
    def mode(self) -> int:
        """Get the mode of the timer."""
        return self._mode

    @mode.setter
    def mode(self, value: int):
        """Set the mode of the timer."""
        self._mode = value

    @property
    def timer(self):
        """Get the underlying machine.Timer object."""
        return self._timer

    def start(self):
        """Start the timer with the configured mode and interval."""
        from machine import Timer
        from picoware.system.boards import BOARD_HAS_ESP32
        if self._callback is None:
            raise ValueError("Callback function must be provided")
        # The ESP32 port has no virtual timers, so machine.Timer needs a
        # hardware timer id; rp2 creates a virtual timer when none is given.
        self._timer = Timer(0) if BOARD_HAS_ESP32 else Timer()
        self._timer.init(
            mode=Timer.PERIODIC if self._mode == self.PERIODIC else Timer.ONE_SHOT,
            period=self._interval,
            callback=self._callback,
            hard=False
        )

    def stop(self):
        """Stop the timer."""
        if self._timer is not None:
            self._timer.deinit()
