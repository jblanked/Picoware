server = None
box = None


class Server:
    """Simple HTTP Server for MicroPython WiFi Devices"""

    def __init__(
        self,
        view_manager,
        append_question_mark=True,
    ):
        """
        Initialize the Server.

        :param wifi: WiFi interface instance.
        :param append_question_mark: Whether to append '?' to URLs.
        """
        self.view_manager = view_manager
        self.server = None
        self.routes = {}  # Routing table as a dictionary
        self.http_type = "HTTP/1.1"
        self.append_question_mark = append_question_mark
        self.client = None
        self.last_response = None

    def __del__(self):
        self.close()
        self.last_response = None
        self.routes = None

    def close(self, reason=None):
        """Close the server and client connections."""
        if reason:
            print(reason)
        if self.client is not None:
            self.client.close()
            del self.client
            self.client = None
        if self.server:
            self.server.close()
            del self.server
            self.server = None

        print("Server closed.")

    def start(self, port=80) -> bool:
        """Start the server on the specified port."""
        try:
            import socket

            address = socket.getaddrinfo("0.0.0.0", port)[0][-1]
            self.server = socket.socket()
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(address)
            self.server.listen(5)  # Allow up to 5 queued connections
            return True
        except Exception as e:
            print("Failed to start server:", e)
            return False

    def add_route(self, path, handler, method="GET"):
        """
        Register a new route with its handler.

        :param path: URL path (e.g., "/custom")
        :param handler: Function to handle the route. It should return the HTML response as a string.
        :param method: HTTP method (e.g., "GET", "POST")
        """
        normalized_path = path.rstrip("/") if path != "/" else path
        method = method.upper()

        if normalized_path not in self.routes:
            self.routes[normalized_path] = {}

        self.routes[normalized_path][method] = {
            "handler": handler,
        }

    def accept_points(self):
        """
        Serve the acceptance page for users.
        """
        html = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Accept Terms</title>
                <script type="text/javascript">
                    function acceptTerms() {
                        // Redirect to a success page or perform other actions
                        alert("Terms Accepted!");
                        window.location.href = "/";
                    }
                </script>
            </head>
            <body>
                <h1>Welcome!</h1>
                <p>Please accept the terms and conditions to continue.</p>
                <button onclick="acceptTerms()">Accept</button>
            </body>
            </html>
        """
        return html

    def webpage(self):
        """
        Generate a basic HTML page.
        """
        html = """ 
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Server</title>
            </head>
            <body>
                <h1>Server</h1>
                <p>Welcome to the Server.</p>
            </body>
            </html>
        """
        return html

    def run(self):
        """Run the server to accept and handle incoming connections."""
        from json import loads
        from picoware.system.buttons import BUTTON_BACK

        global box

        if not self.server:
            print("Server is not started. Call start() before run().")
            return

        inp = self.view_manager.get_input_manager()
        but = inp.button
        if but == BUTTON_BACK:
            inp.reset()
            box.current_text += "Connection closed by user.\n"
            box.refresh()
            print("Connection closed by user.")
            self.view_manager.back()
            return

        try:
            self.server.setblocking(False)
            try:
                self.client, addr = self.server.accept()
            except OSError:
                return
            finally:
                # Restore blocking mode
                self.server.setblocking(True)

            # Ensure client socket is in blocking mode
            self.client.setblocking(True)

            buffer = b""  # Initialize an empty buffer for the incoming data

            while True:
                try:
                    but = inp.button
                    if but == BUTTON_BACK:
                        inp.reset()
                        box.current_text += "Connection closed by user.\n"
                        box.refresh()
                        print("Connection closed by user.")
                        self.view_manager.back()
                        break
                    data = self.client.recv(1024)
                    if not data:
                        box.current_text += f"Client {addr} disconnected.\n"
                        box.refresh()
                        print(f"Client {addr} disconnected.")
                        break
                    buffer += data
                    # Check if we've received all headers
                    header_end = buffer.find(b"\r\n\r\n")
                    if header_end == -1:
                        # Headers not fully received yet
                        continue

                    # Split headers and body
                    headers_part = buffer[:header_end].decode("utf-8", "ignore")
                    body_part = buffer[header_end + 4 :]

                    # Parse request line and headers
                    lines = headers_part.split("\r\n")
                    request_line = lines[0]
                    try:
                        method, path, protocol = request_line.split()
                    except ValueError:
                        self.client.close()
                        box.current_text += (
                            f"Malformed request line from {addr}. Connection closed.\n"
                        )
                        box.refresh()
                        print(f"Malformed request line from {addr}. Connection closed.")
                        break

                    headers = {}
                    for header_line in lines[1:]:
                        if not header_line:
                            continue
                        parts = header_line.split(": ", 1)
                        if len(parts) == 2:
                            headers[parts[0].lower()] = parts[1]

                    # Determine content length
                    content_length = int(headers.get("content-length", "0"))

                    # Check if the entire body has been received
                    if len(body_part) < content_length:
                        # Need to read more data
                        while len(body_part) < content_length:
                            more_data = self.client.recv(1024)
                            if not more_data:
                                break
                            body_part += more_data

                    body = body_part[:content_length]

                    # Normalize path (remove query parameters and trailing slash)
                    if "?" in path:
                        path = path.split("?")[0]
                    path = path.rstrip("/") if path != "/" else path

                    # Initialize response variables
                    response_content = ""
                    status_line = "200 OK\r\n"  # Default status
                    response_headers = {
                        "Content-Type": "text/html",
                        "Connection": "close",
                    }

                    # Handle the request based on the method and path
                    if path in self.routes:
                        route_methods = self.routes[path]
                        if method in route_methods:
                            route_info = self.routes[path][method]
                            handler = route_info["handler"]

                            if method == "GET":
                                # Execute the handler for GET (no data)
                                if handler:
                                    try:
                                        response_content = handler()
                                    except Exception as handler_e:
                                        box.current_text += f"Handler error for path '{path}': {handler_e}\n"
                                        box.refresh()
                                        print(
                                            f"Handler error for path '{path}': {handler_e}"
                                        )
                                        response_content = "<h1>500 Internal Server Error</h1><p>Handler execution failed.</p>"
                                        status_line = "500 Internal Server Error\r\n"

                            elif method == "POST":
                                # Determine Content-Type
                                content_type_header = headers.get("content-type", "")

                                if "application/json" in content_type_header:
                                    # Parse JSON data
                                    try:
                                        parsed_body = loads(body.decode("utf-8"))
                                    except ValueError as ve:
                                        box.current_text += (
                                            f"JSON decoding error: {ve}\n"
                                        )
                                        box.refresh()
                                        print(f"JSON decoding error: {ve}")
                                        response_content = "<h1>400 Bad Request</h1><p>Invalid JSON.</p>"
                                        status_line = "400 Bad Request\r\n"
                                        parsed_body = None
                                else:
                                    # Assume URL-encoded
                                    try:
                                        parsed_body = {}
                                        for pair in body.decode("utf-8").split("&"):
                                            if "=" in pair:
                                                key, value = pair.split("=", 1)
                                                parsed_body[key] = value.replace(
                                                    "+", " "
                                                )
                                    except Exception as e:
                                        box.current_text += (
                                            f"Error parsing POST data: {e}\n"
                                        )
                                        box.refresh()
                                        print(f"Error parsing POST data: {e}")
                                        parsed_body = {}

                                # Execute the handler with the parsed data
                                try:
                                    handler_response = handler(parsed_body)
                                    # Determine if handler returned a tuple or single value
                                    if isinstance(handler_response, tuple):
                                        response_content, handler_status_line = (
                                            handler_response
                                        )
                                        status_line = handler_status_line
                                    else:
                                        response_content = handler_response
                                        # status_line remains "200 OK\r\n"
                                except Exception as handler_e:
                                    box.current_text += f"Handler error for path '{path}': {handler_e}\n"
                                    box.refresh()
                                    print(
                                        f"Handler error for path '{path}': {handler_e}"
                                    )
                                    response_content = "<h1>500 Internal Server Error</h1><p>Handler execution failed.</p>"
                                    status_line = "500 Internal Server Error\r\n"
                    elif path == "/":
                        # Handle Home page (assuming GET)
                        if method == "GET":
                            response_content = self.webpage()
                        else:
                            status_line = "405 Method Not Allowed\r\n"
                            response_headers["Content-Type"] = "text/html"
                            response_content = "<h1>405 Method Not Allowed</h1>"
                    else:
                        # Path not found
                        status_line = "404 Not Found\r\n"
                        response_headers["Content-Type"] = "text/html"
                        response_content = "<h1>404 Not Found</h1>"

                    # Build the full HTTP response
                    response = f"HTTP/1.1 {status_line}"
                    for header, value in response_headers.items():
                        response += f"{header}: {value}\r\n"
                    response += "\r\n"
                    response += response_content

                    # Send the response
                    self.client.send(response.encode("utf-8"))
                    printer = f'"{request_line}" {status_line.strip()}'
                    box.current_text += f"{printer}\n"
                    box.refresh()
                    print(printer)

                    # Remove the processed request from the buffer
                    buffer = buffer[header_end + 4 + content_length :]
                    break  # Close connection after response

                except OSError as e:
                    from errno import ETIMEDOUT

                    if e.args and e.args[0] == ETIMEDOUT:
                        box.current_text += f"Connection with {addr} timed out.\n"
                        box.refresh()
                        print(f"Connection with {addr} timed out.")
                    else:
                        box.current_text += f"OS error: {e}\n"
                        box.refresh()
                        print(f"OS error: {e}")
                    break
                except Exception as e:
                    box.current_text += f"Unexpected error: {e}\n"
                    box.refresh()
                    print(f"Unexpected error: {e}")
                    break

            # Close the client connection
            self.client.close()
        except KeyboardInterrupt:
            box.current_text += "Connection closed by user.\n"
            box.refresh()
            self.close("Server stopped by user")
        except OSError as e:
            box.current_text += f"Server accept error: {e}\n"
            box.refresh()
            print(f"Server accept error: {e}")
        except Exception as e:
            box.current_text += f"Unexpected error: {e}\n"
            box.refresh()
            print(f"Unexpected error: {e}")


def __alert(view_manager, message: str, back: bool = True) -> None:
    """Show an alert"""

    from picoware.gui.alert import Alert
    from picoware.system.buttons import BUTTON_BACK

    draw = view_manager.get_draw()
    draw.clear()
    _alert = Alert(
        draw,
        message,
        view_manager.get_foreground_color(),
        view_manager.get_background_color(),
    )
    _alert.draw("Alert")

    # Wait for user to acknowledge
    inp = view_manager.get_input_manager()
    while True:
        button = inp.button
        if button == BUTTON_BACK:
            inp.reset()
            break

    if back:
        view_manager.back()


def start(view_manager) -> bool:
    """Start the app"""

    # if not a wifi device, return
    if not view_manager.has_wifi:
        __alert(view_manager, "WiFi not available...", False)
        return False

    wifi = view_manager.wifi

    # if wifi isn't connected, return
    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        __alert(view_manager, "WiFi not connected", False)
        connect_to_saved_wifi(view_manager)
        return False

    global server, box

    if server is None:
        server = Server(view_manager)

        if server.start():
            from picoware.system.vector import Vector

            draw = view_manager.draw
            size = draw.size
            msg = f"Server started at http://{wifi.device_ip}"
            display_x = (size.x - len(msg) * draw.font_size.x) // 2
            draw.text(
                Vector(display_x, int(size.y * 0.0625)),
                msg,
                view_manager.get_foreground_color(),
            )
            draw.swap()

            from picoware.gui.textbox import TextBox

            top = int(draw.size.y * 0.0625)

            box = TextBox(
                draw,
                top + (top // 2),
                draw.size.y - (top + (top // 2)),
                view_manager.get_foreground_color(),
                view_manager.get_background_color(),
            )

            box.set_text("Server is running...\n")
            return True

    return False


def run(view_manager) -> None:
    """Run the app"""

    from picoware.system.buttons import BUTTON_BACK

    inp = view_manager.get_input_manager()
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()

    global server

    server.run()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global server, box

    if server is not None:
        del server
        server = None

    if box is not None:
        del box
        box = None

    collect()
