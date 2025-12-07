from micropython import const

# menu states
STATE_MENU_MAIN = const(0)
STATE_MENU_EDIT = const(1)
STATE_RUNNING = const(2)
STATE_MENU_ADD_PAGE = const(3)
STATE_MENU_VIEW_PAGES = const(4)
STATE_MENU_SETTINGS = const(5)
STATE_MENU_EDIT_PAGE = const(6)  # editing a specific page
STATE_SETTINGS_MODE = const(7)
STATE_SETTINGS_SSID = const(8)
STATE_SETTINGS_PASSWORD = const(9)

# page states
STATE_PAGE_MENU = const(-1)  # showing page menu
STATE_PAGE_URL = const(0)
STATE_PAGE_HTML = const(1)
STATE_PAGE_METHOD = const(2)
STATE_PAGE_SCRIPT = const(3)
STATE_PAGE_DELETE = const(4)

# global objects
server = None
box = None
menu = None

# global variables
menu_state = STATE_MENU_MAIN
edit_page_state = STATE_PAGE_MENU
add_page_state = STATE_PAGE_MENU
view_page_state = STATE_PAGE_MENU
current_page_info = {}
current_page_index = -1  # index of the page being edited
just_started_editing = True
save_requested = False
settings_info = {}  # for storing settings being edited

# locations
SERVER_FOLDER = "picoware/wifi/server"
SERVER_INFO = "picoware/wifi/server/server_info.json"

# json example
# {
#     "pages": [
#         {"url": "/custom", "method": "GET", "html": "page.html", "script": "page.py"},
#         {"url": "/submit", "method": "POST", "html": "submit.html", "script": "submit.py"},
#         {"url": "/data", "method": "GET", "html": "picoware/wifi/server/data.html", "script": "picoware/wifi/server/data.py"}
#     ]
# }


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

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self.server is not None

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

            # add routes from json file
            from picoware.system.storage import Storage

            storage: Storage = self.view_manager.get_storage()
            server_info: dict = storage.serialize(SERVER_INFO)
            if "pages" in server_info:
                for page in server_info["pages"]:
                    url = page.get("url", "/")
                    method = page.get("method", "GET").upper()
                    html_file = page.get("html", None)
                    script_file = page.get("script", None)

                    def make_handler(html_file, script_file):
                        def handler(data=None):
                            response = ""
                            # Execute script if available
                            if script_file:
                                try:
                                    script_code = storage.read(script_file)
                                    # Define a local scope for the script execution
                                    local_scope = {}
                                    exec(script_code, {}, local_scope)
                                    if "handle_request" in local_scope:
                                        response = local_scope["handle_request"](data)
                                except Exception as e:
                                    print(f"Error executing script {script_file}: {e}")

                            # Load HTML file if available
                            if html_file:
                                try:
                                    html_content = storage.read(html_file)
                                    response += html_content
                                except Exception as e:
                                    print(f"Error loading HTML file {html_file}: {e}")
                                    response += f"<h1>Error loading HTML file: {html_file}</h1><p>{e}</p>"

                            return response

                        return handler

                    handler = make_handler(html_file, script_file)
                    self.add_route(url, handler, method)
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

        global box, menu_state, menu

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

            menu_state = STATE_MENU_MAIN
            menu.display.fill_screen(menu.background_color)
            menu.draw()
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

                        menu_state = STATE_MENU_MAIN
                        menu.display.fill_screen(menu.background_color)
                        menu.draw()
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


def __add_page(view_manager) -> None:
    """Add a new page to the server"""
    keyboard = view_manager.get_keyboard()

    if keyboard is None:
        print("No keyboard available")
        return

    global just_started_editing, save_requested, menu_state

    if just_started_editing:
        just_started_editing = False
        keyboard.set_save_callback(__add_page_callback)
        keyboard.set_response("")
        keyboard.run(force=True)
        keyboard.run(force=True)
    else:
        if save_requested:
            save_requested = False
            just_started_editing = True
            url = keyboard.get_response()
            # save new page with default values
            storage = view_manager.get_storage()
            try:
                server_info: dict = storage.serialize(SERVER_INFO)
                if "pages" not in server_info:
                    server_info["pages"] = []
                new_page = {
                    "url": url if url.startswith("/") else "/" + url,
                    "method": "GET",
                    "html": "",
                    "script": "",
                }
                server_info["pages"].append(new_page)
                storage.deserialize(server_info, SERVER_INFO)
            except Exception as e:
                print("Error saving server info:", e)
            #
            keyboard.reset()
            # Go back to edit menu
            menu_state = STATE_MENU_EDIT
            __menu_start(view_manager)
            return

        keyboard.run()


def __add_page_callback(result: str) -> None:
    """Callback for when a page field is saved during add page"""
    global save_requested, just_started_editing

    if just_started_editing:
        return

    save_requested = True


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


def __box_start(view_manager) -> None:
    """Start the textbox for server output"""
    from picoware.gui.textbox import TextBox

    global box

    if box is not None:
        del box
        box = None

    draw = view_manager.get_draw()
    fg = view_manager.get_foreground_color()
    bg = view_manager.get_background_color()
    height = draw.size.y

    top = int(height * 0.0625)

    box = TextBox(
        draw,
        top + (top // 2),
        height - (top + (top // 2)),
        fg,
        bg,
    )

    if menu_state == STATE_RUNNING:
        box.set_text("Server is running...\n")
    elif menu_state == STATE_MENU_VIEW_PAGES:
        box.set_text("")


def __callback_edit_save(result: str) -> None:
    """Callback for when a page field is saved"""
    global current_page_info, just_started_editing

    if just_started_editing:
        return

    global edit_page_state, add_page_state, save_requested

    if edit_page_state == STATE_PAGE_URL:
        current_page_info["url"] = result
    elif edit_page_state == STATE_PAGE_HTML:
        current_page_info["html"] = result
    elif edit_page_state == STATE_PAGE_METHOD:
        current_page_info["method"] = result
    elif edit_page_state == STATE_PAGE_SCRIPT:
        current_page_info["script"] = result
    elif add_page_state == STATE_PAGE_URL:
        current_page_info["url"] = result
    elif add_page_state == STATE_PAGE_HTML:
        current_page_info["html"] = result
    elif add_page_state == STATE_PAGE_METHOD:
        current_page_info["method"] = result
    elif add_page_state == STATE_PAGE_SCRIPT:
        current_page_info["script"] = result

    save_requested = True


def __edit_page(
    view_manager,
    index: int,
    key: str,
    return_status: bool = True,
    return_state: int = STATE_PAGE_MENU,
) -> None:
    """Edit a page given its index"""
    if index < 0:
        return

    global current_page_info, just_started_editing, save_requested, edit_page_state, add_page_state, menu_state

    if current_page_info == {} or "url" not in current_page_info:
        current_page_info = __get_page_info_index(view_manager, index)

    keyboard = view_manager.get_keyboard()

    if keyboard is None:
        print("No keyboard available")
        return

    if just_started_editing:
        just_started_editing = False
        keyboard.set_save_callback(__callback_edit_save)
        keyboard.set_response(current_page_info.get(key, ""))
        keyboard.run(force=True)
        keyboard.run(force=True)
    else:
        if save_requested:
            save_requested = False
            just_started_editing = True
            # Get the updated value from keyboard
            current_page_info[key] = keyboard.get_response()
            storage = view_manager.get_storage()
            try:
                server_info: dict = storage.serialize(SERVER_INFO)
                if "pages" in server_info:
                    if 0 <= index < len(server_info["pages"]):
                        server_info["pages"][index] = {
                            "url": current_page_info.get("url", "/"),
                            "method": current_page_info.get("method", "GET"),
                            "html": current_page_info.get("html", ""),
                            "script": current_page_info.get("script", ""),
                        }
                        storage.deserialize(server_info, SERVER_INFO)
            except Exception as e:
                print("Error saving server info:", e)
            #
            keyboard.reset()
            if return_status:
                edit_page_state = return_state
                add_page_state = return_state
                # Stay in edit page menu to allow editing other fields
                menu_state = STATE_MENU_EDIT_PAGE
                __menu_start(view_manager)
                return

        keyboard.run()


def __get_current_pages(view_manager) -> list[str]:
    """Get the list of current pages from the server info file"""
    from picoware.system.storage import Storage

    storage: Storage = view_manager.get_storage()
    pages = []

    try:
        _current_stats: dict = storage.serialize(SERVER_INFO)
        if "pages" in _current_stats:
            for page in _current_stats["pages"]:
                pages.append(page["url"])
    except Exception as e:
        print("Error reading server info:", e)

    return pages


def __get_page_info_index(view_manager, index: int) -> dict:
    """Get the page info for a given index from the server info file"""
    from picoware.system.storage import Storage

    storage: Storage = view_manager.get_storage()
    page_info = {}

    try:
        _current_stats: dict = storage.serialize(SERVER_INFO)
        if "pages" in _current_stats:
            _page_amount = len(_current_stats["pages"])
            if 0 <= index < _page_amount:
                page_info = _current_stats["pages"][index]
                page_info["count"] = _page_amount
    except Exception as e:
        print("Error reading server info:", e)

    return page_info


def __get_setting(view_manager, key: str, default: str = "") -> str:
    """Get a setting from the server info file"""
    from picoware.system.storage import Storage

    storage: Storage = view_manager.get_storage()
    value = default

    try:
        server_info: dict = storage.serialize(SERVER_INFO)
        if "settings" in server_info:
            value = server_info["settings"].get(key, default)
    except Exception as e:
        print("Error reading server setting:", e)

    return value


def __save_setting(view_manager, key: str, value: str) -> None:
    """Save a setting to the server info file"""
    from picoware.system.storage import Storage

    storage: Storage = view_manager.get_storage()

    try:
        server_info: dict = storage.serialize(SERVER_INFO)
        if "settings" not in server_info:
            server_info["settings"] = {}
        server_info["settings"][key] = value
        storage.deserialize(server_info, SERVER_INFO)
    except Exception as e:
        print("Error saving server setting:", e)


def __delete_page(view_manager, index: int) -> None:
    """Delete a page from the server info file"""
    global menu_state, current_page_index, current_page_info

    from picoware.system.storage import Storage

    storage: Storage = view_manager.get_storage()

    try:
        server_info: dict = storage.serialize(SERVER_INFO)
        if "pages" in server_info:
            if 0 <= index < len(server_info["pages"]):
                del server_info["pages"][index]
                storage.deserialize(server_info, SERVER_INFO)
    except Exception as e:
        print("Error deleting page:", e)

    # Go back to view pages
    menu_state = STATE_MENU_VIEW_PAGES
    current_page_index = -1
    current_page_info = {}
    __menu_start(view_manager)


def __toggle_mode(view_manager, selection: int) -> None:
    """Toggle between AP and STA mode"""
    global menu_state

    mode = "AP" if selection == 0 else "STA"
    __save_setting(view_manager, "mode", mode)

    # Refresh the menu to show updated selection
    __menu_start(view_manager)


def __edit_setting(view_manager, setting_key: str) -> None:
    """Edit a setting using the keyboard"""
    global just_started_editing, save_requested, menu_state, settings_info

    keyboard = view_manager.get_keyboard()

    if keyboard is None:
        print("No keyboard available")
        return

    if just_started_editing:
        just_started_editing = False
        current_value = __get_setting(view_manager, setting_key, "")
        settings_info = {"key": setting_key, "value": current_value}
        keyboard.set_save_callback(__setting_callback)
        keyboard.set_response(current_value)
        keyboard.run(force=True)
        keyboard.run(force=True)
    else:
        if save_requested:
            save_requested = False
            just_started_editing = True
            new_value = keyboard.get_response()
            __save_setting(view_manager, setting_key, new_value)
            keyboard.reset()
            settings_info = {}
            menu_state = STATE_MENU_SETTINGS
            menu.draw()
            return

        keyboard.run()


def __setting_callback(result: str) -> None:
    """Callback for when a setting is saved"""
    global save_requested, just_started_editing

    if just_started_editing:
        return

    save_requested = True


def __menu_run(view_manager) -> None:
    """Run the server"""

    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_RIGHT,
    )

    inp = view_manager.get_input_manager()
    button = inp.button

    global menu_state, edit_page_state, current_page_index, current_page_info

    if menu is None:
        __menu_start(view_manager)

    if button == BUTTON_BACK:
        inp.reset()
        if menu_state == STATE_MENU_MAIN:
            view_manager.back()
        elif menu_state in (STATE_RUNNING, STATE_MENU_EDIT):
            menu_state = STATE_MENU_MAIN
            __menu_start(view_manager)
        elif menu_state == STATE_MENU_ADD_PAGE:
            menu_state = STATE_MENU_EDIT
            __menu_start(view_manager)
        elif menu_state == STATE_MENU_VIEW_PAGES:
            menu_state = STATE_MENU_EDIT
            __menu_start(view_manager)
        elif menu_state == STATE_MENU_EDIT_PAGE:
            # Go back to view pages
            menu_state = STATE_MENU_VIEW_PAGES
            edit_page_state = STATE_PAGE_MENU
            current_page_index = -1
            current_page_info = {}
            __menu_start(view_manager)
        elif menu_state == STATE_MENU_SETTINGS:
            menu_state = STATE_MENU_EDIT
            __menu_start(view_manager)
        elif menu_state in (
            STATE_SETTINGS_MODE,
            STATE_SETTINGS_SSID,
            STATE_SETTINGS_PASSWORD,
        ):
            menu_state = STATE_MENU_SETTINGS
            __menu_start(view_manager)

    elif button in (BUTTON_UP, BUTTON_LEFT):
        inp.reset()
        menu.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        inp.reset()
        menu.scroll_down()
    elif button == BUTTON_CENTER:
        inp.reset()
        selection = menu.get_selected_index()

        if menu_state == STATE_RUNNING:
            if server is not None:
                if not server.is_running:
                    __server_start(view_manager)
                server.run()
        elif menu_state == STATE_MENU_MAIN:
            if selection == 0:  # Start
                menu_state = STATE_RUNNING
                __server_start(view_manager)
            elif selection == 1:  # Edit
                menu_state = STATE_MENU_EDIT
                __menu_start(view_manager)
        elif menu_state == STATE_MENU_EDIT:
            if selection == 0:  # Add Page
                menu_state = STATE_MENU_ADD_PAGE
                __menu_start(view_manager)
            elif selection == 1:  # View Pages
                menu_state = STATE_MENU_VIEW_PAGES
                __menu_start(view_manager)
            elif selection == 2:  # Settings
                menu_state = STATE_MENU_SETTINGS
                __menu_start(view_manager)
        elif menu_state == STATE_MENU_VIEW_PAGES:
            # User selected a page to edit
            pages = __get_current_pages(view_manager)
            if pages and selection < len(pages):
                current_page_index = selection
                current_page_info = __get_page_info_index(view_manager, selection)
                menu_state = STATE_MENU_EDIT_PAGE
                edit_page_state = STATE_PAGE_MENU
                __menu_start(view_manager)
            # If no pages exist, do nothing (user clicked on "(No pages)")
        elif menu_state == STATE_MENU_EDIT_PAGE:
            # User selected which field to edit
            if selection == 0:  # URL
                edit_page_state = STATE_PAGE_URL
            elif selection == 1:  # HTML
                edit_page_state = STATE_PAGE_HTML
            elif selection == 2:  # Method
                edit_page_state = STATE_PAGE_METHOD
            elif selection == 3:  # Script
                edit_page_state = STATE_PAGE_SCRIPT
            elif selection == 4:  # Delete
                __delete_page(view_manager, current_page_index)
                return
        elif menu_state == STATE_MENU_SETTINGS:
            if selection == 0:  # Mode
                menu_state = STATE_SETTINGS_MODE
                __menu_start(view_manager)
            elif selection == 1:  # SSID
                menu_state = STATE_SETTINGS_SSID
            elif selection == 2:  # Password
                menu_state = STATE_SETTINGS_PASSWORD
        elif menu_state == STATE_SETTINGS_MODE:
            # Toggle between AP and STA
            __toggle_mode(view_manager, selection)

    # Handle keyboard states
    if menu_state == STATE_RUNNING:
        if server is not None:
            if server.is_running:
                server.run()
    elif menu_state == STATE_MENU_ADD_PAGE:
        __add_page(view_manager)
    elif menu_state == STATE_MENU_EDIT_PAGE and edit_page_state != STATE_PAGE_MENU:
        state_map = {
            STATE_PAGE_URL: "url",
            STATE_PAGE_HTML: "html",
            STATE_PAGE_METHOD: "method",
            STATE_PAGE_SCRIPT: "script",
        }
        __edit_page(
            view_manager,
            current_page_index,
            state_map.get(edit_page_state, "url"),
            True,
            STATE_PAGE_MENU,
        )
    elif menu_state == STATE_SETTINGS_SSID:
        __edit_setting(view_manager, "ssid")
    elif menu_state == STATE_SETTINGS_PASSWORD:
        __edit_setting(view_manager, "password")


def __menu_start(view_manager) -> None:
    """Show a menu to select from options"""

    from picoware.gui.menu import Menu

    global menu

    if menu is not None:
        del menu
        menu = None

    draw = view_manager.get_draw()
    draw.clear()
    title = ""
    options = []
    if menu_state == STATE_MENU_MAIN:
        title = "Server"
        options = ["Start", "Edit"]
    elif menu_state == STATE_MENU_EDIT:
        title = "Edit"
        options = ["Add Page", "View Pages", "Settings"]
    elif menu_state == STATE_MENU_VIEW_PAGES:
        title = "View Pages"
        options = __get_current_pages(view_manager)
        if not options:
            options = ["(No pages)"]
    elif menu_state == STATE_MENU_EDIT_PAGE:
        title = "Edit Page"
        options = [
            f"URL: {current_page_info.get('url', '/')}",
            f"HTML: {current_page_info.get('html', '')}",
            f"Method: {current_page_info.get('method', 'GET')}",
            f"Script: {current_page_info.get('script', '')}",
            "Delete Page",
        ]
    elif menu_state == STATE_MENU_SETTINGS:
        title = "Settings"
        options = ["Mode", "SSID", "Password"]
    elif menu_state == STATE_SETTINGS_MODE:
        title = "Mode"
        # Get current mode from settings
        current_mode = __get_setting(view_manager, "mode", "STA")
        options = [
            f"{'[X]' if current_mode == 'AP' else '[ ]'} AP (Access Point)",
            f"{'[X]' if current_mode == 'STA' else '[ ]'} STA (Station)",
        ]
    fg = view_manager.get_foreground_color()
    bg = view_manager.get_background_color()
    sel = view_manager.get_selected_color()
    menu = Menu(
        draw,
        title,
        0,
        draw.size.y,
        fg,
        bg,
        sel,
        fg,
        2,
    )
    for option in options:
        menu.add_item(option)

    menu.draw()


def __server_start(view_manager) -> bool:
    """Start the server app"""

    global box

    if box is not None:
        del box
        box = None

    if server.start():
        from picoware.system.vector import Vector

        bg = view_manager.get_background_color()
        fg = view_manager.get_foreground_color()

        draw = view_manager.draw
        draw.fill_screen(bg)
        size = draw.size
        msg = f"Server started at http://{view_manager.wifi.device_ip}"
        display_x = (size.x - len(msg) * draw.font_size.x) // 2
        draw.text(
            Vector(display_x, int(size.y * 0.0625)),
            msg,
            fg,
        )
        draw.swap()

        __box_start(view_manager)

        return True


def start(view_manager) -> bool:
    """Start the app"""

    # if not a wifi device, return
    if not view_manager.has_wifi:
        __alert(view_manager, "WiFi not available...", False)
        return False

    # if no sd card, return
    if not view_manager.has_sd_card:
        __alert(view_manager, "Server app requires an SD card")
        return False

    # create server folder
    view_manager.get_storage().mkdir("picoware/wifi/server")

    wifi = view_manager.wifi

    # if wifi isn't connected, return
    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        __alert(view_manager, "WiFi not connected", False)
        connect_to_saved_wifi(view_manager)
        return False

    global server

    if menu is None:
        __menu_start(view_manager)

    if server is None:
        server = Server(view_manager)

    return True


def run(view_manager) -> None:
    """Run the app"""

    __menu_run(view_manager)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global server, box, menu
    global menu_state, edit_page_state, add_page_state, view_page_state
    global current_page_info, just_started_editing, save_requested
    global current_page_index, settings_info

    if menu is not None:
        del menu
        menu = None

    if server is not None:
        del server
        server = None

    if box is not None:
        del box
        box = None

    menu_state = STATE_MENU_MAIN
    edit_page_state = STATE_PAGE_MENU
    add_page_state = STATE_PAGE_MENU
    view_page_state = STATE_PAGE_MENU

    current_page_info = {}
    current_page_index = -1
    just_started_editing = True
    save_requested = False
    settings_info = {}

    collect()
