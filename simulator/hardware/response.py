class Response:
    def __init__(self):
        self.set_content(b"")
        self.set_encoding("utf-8")
        self.set_headers({})
        self.set_reason("")
        self.set_status_code(0)
        self.set_text("")

    def set_content(self, value):
        object.__setattr__(self, "content", value)

    def set_encoding(self, value):
        object.__setattr__(self, "encoding", value)

    def set_headers(self, value):
        object.__setattr__(self, "headers", value)

    def set_reason(self, value):
        object.__setattr__(self, "reason", value)

    def set_status_code(self, value):
        object.__setattr__(self, "status_code", value)

    def set_text(self, value):
        object.__setattr__(self, "text", value)
