class Log:
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
        print(line)

    def reset(self):
        object.__setattr__(self, "logs", [])
