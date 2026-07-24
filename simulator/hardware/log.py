class Log:
    LOG_MODE_REPL = 0
    LOG_MODE_STORAGE = 1
    LOG_MODE_ALL = 2

    LOG_TYPE_NONE = -1
    LOG_TYPE_INFO = 0
    LOG_TYPE_WARN = 1
    LOG_TYPE_ERROR = 2
    LOG_TYPE_DEBUG = 3

    _TYPE_NAMES = {
        -1: "",
        0: "[INFO]",
        1: "[WARN]",
        2: "[ERROR]",
        3: "[DEBUG]",
    }
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

    def _uses_storage(self):
        return self.mode in (self.LOG_MODE_STORAGE, self.LOG_MODE_ALL)

    def _storage_path(self):
        if not self.file_path:
            return None

        import sim_runtime

        path = str(self.file_path).replace("\\", "/")
        if ".." in path.split("/"):
            return None
        return sim_runtime.host_path(path)

    def _prepare_storage_path(self):
        path = self._storage_path()
        if path is None:
            return None

        import sim_runtime

        parent = path.rsplit("/", 1)[0] if "/" in path else "."
        sim_runtime.mkdir_p(parent)
        return path

    def log(self, message, log_type=-1):
        line = self._TYPE_NAMES.get(log_type, "") + str(message)
        self.logs.append(line)

        if self.mode in (self.LOG_MODE_REPL, self.LOG_MODE_ALL):
            color = self._COLORS.get(log_type, "")
            if color:
                print(f"{color}{line}{self._RESET}")
            else:
                print(line)

        if self._uses_storage():
            try:
                path = self._prepare_storage_path()
                if path is None:
                    return False
                with open(path, "a") as handle:
                    handle.write(line + "\n")
            except OSError:
                return False

        return True

    def reset(self):
        self.logs[:] = []
        if not self._uses_storage():
            return True

        try:
            path = self._prepare_storage_path()
            if path is None:
                return False
            with open(path, "w"):
                pass
        except OSError:
            return False
        return True
