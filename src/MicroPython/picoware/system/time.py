class Time:
    """Handles time-related functions."""

    def __init__(self):
        from machine import RTC

        self._rtc = RTC()
        self._is_set = False

    def __del__(self):
        self._rtc.deinit()
        del self._rtc

    @property
    def date(self) -> str:
        """Return the current date only as string"""
        date = self._rtc.datetime()
        return f"{date[1]}/{date[2]}/{date[0]}"

    @property
    def is_set(self) -> bool:
        """Return whether the time has been set."""
        return self._is_set

    @property
    def time(self) -> str:
        """Return the current time only as string"""
        date = self._rtc.datetime()
        return f"{date[4]}:{date[5]}:{date[6]}"

    def set(self, year, month, day, hour, minute, second) -> None:
        """Set the current date and time."""
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
