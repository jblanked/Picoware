class Log:
    LOG_TYPE_NONE = -1
    LOG_TYPE_INFO = 0
    LOG_TYPE_WARN = 1
    LOG_TYPE_ERROR = 2
    LOG_TYPE_DEBUG = 3

    _COLORS = {
        -1: "",           # NONE: default terminal color
        0: "\033[92m",    # INFO: green
        1: "\033[93m",    # WARN: yellow
        2: "\033[91m",    # ERROR: red
        3: "\033[94m",    # DEBUG: blue
    }
    _RESET = "\033[0m"

    def __init__(self, mode=0, file_path="picoware/log.txt", reset=False):
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "file_path", file_path)
        object.__setattr__(self, "logs", [])
        if reset:
            self.reset()

    def set_mode(self, value):
        object.__setattr__(self, "mode", value)

    def set_file_path(self, value):
        object.__setattr__(self, "file_path", value)

    def log(self, message, log_type=-1):
        line = str(message)
        self.logs.append(line)
        color = self._COLORS.get(log_type, "")
        if color:
            print(f"{color}{line}{self._RESET}")
        else:
            print(line)

    def reset(self):
        object.__setattr__(self, "logs", [])
