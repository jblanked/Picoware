import response
from json import loads


class Response(response.Response):
    """Response object for HTTP requests."""

    def __init__(self, body: bytes) -> None:
        """Initialize the response with the given body."""
        super().__init__()
        self.set_content(body)
        self.set_text(str(body, self.encoding))

    def __setattr__(self, name, value):
        if name == "content":
            self.set_content(value)
        elif name == "encoding":
            self.set_encoding(value)
        elif name == "headers":
            self.set_headers(value)
        elif name == "reason":
            self.set_reason(value)
        elif name == "status_code":
            self.set_status_code(value)
        elif name == "text":
            self.set_text(value)
        else:
            super().__setattr__(name, value)

    def close(self) -> None:
        """Close the response and release any resources."""
        self.set_content(b"")
        self.set_encoding("")
        self.set_headers({})
        self.set_reason("")
        self.set_status_code(0)
        self.set_text("")

    def json(self) -> dict:
        """Convert the response content to a JSON object."""
        return loads(self.content)
