"""Response - HTTP response object."""

import response
from json import loads


class Response(response.Response):
    """Response object for HTTP requests.
    
    Attributes:
        content (bytes): The raw response body.
        encoding (str): The character encoding of the response.
        headers (dict): The HTTP headers of the response.
        reason (str): The HTTP reason phrase.
        status_code (int): The HTTP status code of the response.
        text (str): The response body decoded as a string.
    """

    def __init__(self, body: bytes) -> None:
        """Initialize the response with the given body.

        Args:
            body (bytes): The raw response body.
        """
        super().__init__()
        self.set_content(body)
        self.set_text(str(body, self.encoding))

    def __setattr__(self, name, value):
        """Set a response attribute, routing to the matching setter.

        Args:
            name (str): Attribute name to set.
            value (object): New value for the attribute.
        """
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
        """Convert the response content to a JSON object.

        Returns:
            dict: The parsed JSON object.
        """
        return loads(self.content)
