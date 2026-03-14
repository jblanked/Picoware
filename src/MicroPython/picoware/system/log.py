from micropython import const
import log

# modes
LOG_MODE_REPL = const(0)
LOG_MODE_STORAGE = const(1)
LOG_MODE_ALL = const(2)

# types
LOG_TYPE_NONE = const(-1)
LOG_TYPE_INFO = const(0)
LOG_TYPE_WARN = const(1)
LOG_TYPE_ERROR = const(2)
LOG_TYPE_DEBUG = const(3)


class Log(log.Log):
    """
    Log class for Picoware

    Methods:
        - log(self, message: str, log_type: int = LOG_TYPE_NONE)
        - reset(self)
    Properties:
        - mode: int (getter and setter for log mode)
        - logs: list (getter for stored logs)
    """

    def __init__(
        self,
        mode: int = LOG_MODE_REPL,
        file_path: str = "picoware/log.txt",
        reset: bool = False,
    ):
        super().__init__(mode, file_path, reset)
