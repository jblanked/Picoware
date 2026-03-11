class Time:
    """Handles time-related functions."""

    __slots__ = (
        "_rtc",
        "_is_set",
        "_thread_manager",
        "_current_task",
        "_running",
        "_lock",
    )

    def __init__(self, thread_manager=None):
        from machine import RTC
        from _thread import allocate_lock

        self._rtc = RTC()
        self._is_set = False
        self._thread_manager = thread_manager
        self._current_task = None
        self._running = False
        self._lock = allocate_lock()

    def __del__(self):
        self._rtc.deinit()
        del self._rtc
        self._rtc = None
        self._is_set = False
        if self._current_task:
            self._current_task.stop()
            self._current_task = None
        self._lock = None

    @property
    def date(self) -> str:
        """Return the current date only as string"""
        with self._lock:
            date = self._rtc.datetime()
            return f"{date[1]}/{date[2]}/{date[0]}"

    @property
    def is_fetching(self) -> bool:
        """Return whether the time is currently being fetched."""
        with self._lock:
            return self._running

    @property
    def is_set(self) -> bool:
        """Return whether the time has been set."""
        with self._lock:
            return self._is_set

    @property
    def rtc(self):
        """Return the RTC object."""
        with self._lock:
            return self._rtc

    @property
    def time(self) -> str:
        """Return the current time only as string"""
        with self._lock:
            date = self._rtc.datetime()
            _seconds = date[6]
            if _seconds < 10:
                _seconds = f"0{_seconds}"
            _minutes = date[5]
            if _minutes < 10:
                _minutes = f"0{_minutes}"
            return f"{date[4]}:{_minutes}:{_seconds}"

    def fetch(self, offset: int = 0) -> bool:
        """
        Fetch the current date and time from ntp.
        Originated from: https://github.com/micropython/micropython-lib/blob/master/micropython/net/ntptime/ntptime.py
        """
        try:
            with self._lock:
                if self._running:
                    return False
                if self._is_set:
                    return True

            def fetch_ntp_time() -> None:
                """Fetch the current time from an NTP server and set the RTC accordingly."""
                from time import gmtime
                import usocket as socket
                import ustruct as struct

                with self._lock:
                    self._is_set = False
                    self._running = True
                NTP_QUERY = bytearray(48)
                NTP_QUERY[0] = 0x1B
                host = "pool.ntp.org"
                timeout = 1
                addr = socket.getaddrinfo(host, 123)[0][-1]
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    s.settimeout(timeout)
                    s.sendto(NTP_QUERY, addr)
                    msg = s.recv(48)
                finally:
                    s.close()
                val = struct.unpack("!I", msg[40:44])[0]

                # 2024-01-01 00:00:00 converted to an NTP timestamp
                MIN_NTP_TIMESTAMP = 3913056000
                if val < MIN_NTP_TIMESTAMP:
                    val += 0x100000000

                # Convert timestamp from NTP format to our internal format
                EPOCH_YEAR = gmtime(0)[0]
                if EPOCH_YEAR == 2000:
                    # (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
                    NTP_DELTA = 3155673600
                elif EPOCH_YEAR == 1970:
                    # (date(1970, 1, 1) - date(1900, 1, 1)).days * 24*60*60
                    NTP_DELTA = 2208988800
                else:
                    print("Unsupported epoch: {}".format(EPOCH_YEAR))
                    with self._lock:
                        self._running = False
                        self._is_set = False
                    return

                t = val - NTP_DELTA
                tm = gmtime(t)
                with self._lock:
                    self._rtc.datetime(
                        (
                            tm[0],  # year
                            tm[1],  # month
                            tm[2],  # day of the month
                            tm[6] + 1,  # weekday
                            tm[3] + offset,  # hour with offset
                            tm[4],  # minute
                            tm[5],  # second
                            0,  # subseconds
                        )
                    )
                    self._is_set = True
                    self._running = False

            if not self._thread_manager:
                return fetch_ntp_time()

            from picoware.system.thread import ThreadTask

            task = ThreadTask("Time", function=fetch_ntp_time)
            self._current_task = task
            self._thread_manager.add_task(task)
            return True
        except Exception as e:
            print(f"Failed to fetch time: {e}")
            with self._lock:
                self._running = False
                self._is_set = False
            return False

    def set(self, year, month, day, hour, minute, second) -> None:
        """Set the current date and time."""
        with self._lock:
            self._rtc.datetime(
                (
                    year,  # year
                    month,  # month
                    day,  # day of the month
                    0,  # weekday
                    hour,  # hour
                    minute,  # minute
                    second,  # second
                    0,  # subseconds
                )
            )
            self._is_set = True
