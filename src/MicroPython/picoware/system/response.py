class Response:
    """Response object for HTTP requests."""

    def __init__(self, body) -> None:
        self.content = body
        self.encoding = "utf-8"
        self.headers = {}
        self.reason = ""
        self.status_code = None
        self.text = str(self.content, self.encoding)

    def __del__(self) -> None:
        """Destructor to clean up resources."""
        self.close()

    def close(self) -> None:
        """Close the response and release any resources."""
        self.content = None
        self.encoding = None
        self.headers = None
        self.reason = None
        self.status_code = None
        self.text = None

    def json(self) -> dict:
        """Convert the response content to a JSON object."""
        from ujson import loads

        return loads(self.content)
