class Response:
    """Response object for HTTP requests."""

    def __init__(self, body: bytes) -> None:
        from response import Response as resp

        self._context: resp = resp()
        self._context.content = body

        self._context.text = str(body, self._context.encoding)

    def __del__(self) -> None:
        if self._context is not None:
            del self._context
            self._context = None

    def __str__(self) -> str:
        return str(self._context)

    @property
    def content(self) -> bytes:
        """Get the response content as bytes."""
        return self._context.content

    @content.setter
    def content(self, value: bytes) -> None:
        """Set the response content."""
        self._context.content = value

    @property
    def encoding(self) -> str:
        """Get the response encoding."""
        return self._context.encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        """Set the response encoding."""
        self._context.encoding = value

    @property
    def headers(self) -> dict:
        """Get the response headers."""
        return self._context.headers

    @headers.setter
    def headers(self, value: dict) -> None:
        """Set the response headers."""
        self._context.headers = value

    @property
    def reason(self) -> str:
        """Get the response reason phrase."""
        return self._context.reason

    @reason.setter
    def reason(self, value: str) -> None:
        """Set the response reason phrase."""
        self._context.reason = value

    @property
    def status_code(self) -> int:
        """Get the response status code."""
        return self._context.status_code

    @status_code.setter
    def status_code(self, value: int) -> None:
        """Set the response status code."""
        self._context.status_code = value

    @property
    def text(self) -> str:
        """Get the response content as a string."""
        return self._context.text

    @text.setter
    def text(self, value: str) -> None:
        """Set the response content as a string."""
        self._context.text = value

    def close(self) -> None:
        """Close the response and release any resources."""
        from response import Response as resp

        del self._context
        self._context = resp()

    def json(self) -> dict:
        """Convert the response content to a JSON object."""
        from ujson import loads

        return loads(self.content)
