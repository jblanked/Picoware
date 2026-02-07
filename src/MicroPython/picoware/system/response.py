from response import Response as resp
from json import loads


class Response(resp):
    """Response object for HTTP requests."""

    def __init__(self, body: bytes) -> None:
        """Initialize the response with the given body."""
        super().__init__()
        self.content = body
        self.text = str(body, self.encoding)

    def close(self) -> None:
        """Close the response and release any resources."""
        self.content = b""
        self.encoding = ""
        self.headers = {}
        self.reason = ""
        self.status_code = 0
        self.text = ""

    def json(self) -> dict:
        """Convert the response content to a JSON object."""
        return loads(self.content)
