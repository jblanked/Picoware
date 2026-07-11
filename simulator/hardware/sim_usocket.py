try:
    import socket as _socket
except ImportError:
    _socket = None

try:
    import sim_runtime
except ImportError:
    sim_runtime = None

try:
    AF_INET = _socket.AF_INET
except Exception:
    AF_INET = 2
try:
    SOCK_STREAM = _socket.SOCK_STREAM
except Exception:
    SOCK_STREAM = 1
try:
    SOL_SOCKET = _socket.SOL_SOCKET
except Exception:
    SOL_SOCKET = 1
try:
    SO_REUSEADDR = _socket.SO_REUSEADDR
except Exception:
    SO_REUSEADDR = 2


def _network_mode():
    if sim_runtime is None:
        return "real"
    return getattr(sim_runtime, "network_mode", "real")


def _is_fixture_host(host):
    h = str(host).lower()
    return (
        "wikipedia.org" in h
        or h == "catfact.ninja"
        or "open-meteo.com" in h
        or "api.github.com" in h
        or "raw.githubusercontent.com" in h
        or h.endswith(".githubusercontent.com")
    )


def _should_fixture(host):
    mode = _network_mode()
    return mode == "offline" or mode == "fixture"


def getaddrinfo(host, port, *args):
    if _should_fixture(host):
        return [(AF_INET, SOCK_STREAM, 0, "", (host, port))]
    if _socket is None:
        raise OSError("socket module unavailable")
    return _socket.getaddrinfo(host, port, *args)


def socket(family=AF_INET, type=SOCK_STREAM, proto=0):
    return _Socket(family, type, proto)


class _Socket:
    def __init__(self, family=AF_INET, type=SOCK_STREAM, proto=0):
        self.family = family
        self.type = type
        self.proto = proto
        self._real = None
        self._fixture = False
        self._connected = None
        self._request = b""
        self._response = b""
        self._offset = 0
        self._timeout = None
        self._websocket = False

    @property
    def _sim_fixture(self):
        return self._fixture

    def settimeout(self, value):
        self._timeout = value
        if self._real is not None:
            try:
                self._real.settimeout(value)
            except AttributeError:
                pass

    def setblocking(self, flag):
        if flag:
            self._timeout = None
        else:
            self._timeout = 0
        if self._real is not None:
            try:
                return self._real.setblocking(flag)
            except AttributeError:
                try:
                    return self._real.settimeout(self._timeout)
                except AttributeError:
                    pass
        return None

    def setsockopt(self, *args):
        if self._real is not None:
            return self._real.setsockopt(*args)
        return None

    def bind(self, *args):
        self._ensure_real()
        return self._real.bind(*args)

    def listen(self, *args):
        self._ensure_real()
        return self._real.listen(*args)

    def accept(self):
        self._ensure_real()
        client, addr = self._real.accept()
        wrapped = _Socket(self.family, self.type, self.proto)
        wrapped._real = client
        return wrapped, addr

    def connect(self, address):
        self._connected = address
        host = address[0] if isinstance(address, tuple) else address
        if _should_fixture(host):
            self._fixture = True
            return None
        self._ensure_real()
        return self._real.connect(address)

    def write(self, data):
        if isinstance(data, str):
            data = data.encode()
        if self._fixture:
            if self._websocket:
                self._response += _websocket_frames(data)
                return len(data)
            self._request += data
            if b"\r\n\r\n" in self._request and not self._response:
                self._response = _build_response(self._connected, self._request)
                if self._response.startswith(b"HTTP/1.1 101"):
                    self._websocket = True
            return len(data)
        self._ensure_real()
        try:
            return self._real.write(data)
        except AttributeError:
            return self._real.send(data)

    def send(self, data):
        if self._fixture:
            return self.write(data)
        self._ensure_real()
        return self._real.send(data)

    def sendall(self, data):
        if isinstance(data, str):
            data = data.encode()
        if self._fixture:
            self.write(data)
            return None
        self._ensure_real()
        try:
            return self._real.sendall(data)
        except AttributeError:
            sent = 0
            while sent < len(data):
                n = self._real.send(data[sent:])
                if n <= 0:
                    raise OSError("socket send failed")
                sent += n
            return None

    def recv(self, count):
        return self.read(count)

    def readline(self):
        if self._fixture:
            if not self._response:
                self._response = _build_response(self._connected, self._request)
            if self._offset >= len(self._response):
                return b""
            end = self._response.find(b"\n", self._offset)
            if end < 0:
                end = len(self._response) - 1
            data = self._response[self._offset : end + 1]
            self._offset = end + 1
            return data
        self._ensure_real()
        try:
            return self._real.readline()
        except AttributeError:
            chunks = []
            while True:
                data = self._real.recv(1)
                if not data:
                    break
                chunks.append(data)
                if data == b"\n":
                    break
            return b"".join(chunks)

    def read(self, count=-1):
        if self._fixture:
            if not self._response:
                self._response = _build_response(self._connected, self._request)
            if self._offset >= len(self._response):
                return b""
            if count is None or count < 0:
                count = len(self._response) - self._offset
            end = min(len(self._response), self._offset + count)
            data = self._response[self._offset:end]
            self._offset = end
            return data
        self._ensure_real()
        if count is None or count < 0:
            chunks = []
            while True:
                data = self._real.recv(4096)
                if not data:
                    break
                chunks.append(data)
            return b"".join(chunks)
        return self._real.recv(count)

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)

    def makefile(self, *args):
        self._ensure_real()
        return self._real.makefile(*args)

    def fileno(self):
        self._ensure_real()
        return self._real.fileno()

    def close(self):
        if self._real is not None:
            return self._real.close()
        return None

    def _sim_real_socket(self):
        self._ensure_real()
        return self._real

    def _ensure_real(self):
        if self._real is None:
            if _socket is None:
                raise OSError("socket module unavailable")
            self._real = _socket.socket(self.family, self.type, self.proto)
            if self._timeout is not None:
                try:
                    self._real.settimeout(self._timeout)
                except AttributeError:
                    pass


def _parse_request(request):
    try:
        line = request.split(b"\r\n", 1)[0].decode()
    except Exception:
        line = "GET / HTTP/1.1"
    parts = line.split(" ")
    method = parts[0] if len(parts) > 0 else "GET"
    path = parts[1] if len(parts) > 1 else "/"
    return method, path


def _query_value(path, key):
    marker = key + "="
    if "?" not in path:
        return ""
    query = path.split("?", 1)[1]
    for item in query.split("&"):
        if item.startswith(marker):
            value = item[len(marker) :]
            return _url_decode(value)
    return ""


def _url_decode(value):
    value = value.replace("+", " ")
    out = ""
    i = 0
    while i < len(value):
        if value[i] == "%" and i + 2 < len(value):
            try:
                out += chr(int(value[i + 1 : i + 3], 16))
                i += 3
                continue
            except Exception:
                pass
        out += value[i]
        i += 1
    return out


def _json_escape(value):
    out = ""
    for ch in str(value):
        code = ord(ch)
        if ch == "\\":
            out += "\\\\"
        elif ch == '"':
            out += '\\"'
        elif ch == "\n":
            out += "\\n"
        elif ch == "\r":
            out += "\\r"
        elif ch == "\t":
            out += "\\t"
        elif code < 32:
            out += "\\u%04x" % code
        else:
            out += ch
    return out


def _json_response(text):
    data = text.encode()
    header = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: application/json\r\n"
        + b"Content-Length: "
        + str(len(data)).encode()
        + b"\r\nConnection: close\r\n\r\n"
    )
    return header + data


def _bytes_response(data, content_type="application/octet-stream", status="200 OK"):
    header = (
        b"HTTP/1.1 "
        + status.encode()
        + b"\r\nContent-Type: "
        + content_type.encode()
        + b"\r\nContent-Length: "
        + str(len(data)).encode()
        + b"\r\nConnection: close\r\n\r\n"
    )
    return header + data


def _build_response(address, request):
    host = ""
    if isinstance(address, tuple) and address:
        host = str(address[0]).lower()
    method, path = _parse_request(request)
    if b"Upgrade: websocket" in request or b"upgrade: websocket" in request:
        return (
            b"HTTP/1.1 101 Switching Protocols\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Accept: picoware-sim-fixture\r\n\r\n"
        )
    if "wikipedia.org" in host:
        return _wikipedia_response(path)
    if "telegram" in host:
        return _json_response('{"ok":true,"result":[{"update_id":1,"message":{"text":"Picoware simulator Telegram fixture"}}]}')
    if "newsapi" in host or "hacker-news" in host or "algolia" in host:
        return _json_response('{"status":"ok","articles":[{"title":"Picoware simulator news","description":"Offline fixture article","url":"https://example.invalid/news"}],"hits":[]}')
    if host == "catfact.ninja":
        return _json_response('{"fact":"Picoware simulator fixture cat fact.","length":38}')
    if "open-meteo.com" in host:
        return _json_response(
            '{"latitude":52.52,"longitude":13.41,"current_weather":{"temperature":21.5,"windspeed":8.0,"weathercode":1}}'
        )
    if "api.github.com" in host:
        return _json_response('{"message":"Picoware simulator GitHub fixture","items":[]}')
    if "githubusercontent.com" in host:
        return _bytes_response(
            b"Picoware simulator fixture asset generated for offline development.\n",
            "application/octet-stream",
        )
    return _json_response(
        '{"ok":true,"method":"' + method + '","fixture":"picoware simulator"}'
    )


def _websocket_frame(opcode, payload):
    if isinstance(payload, str):
        payload = payload.encode()
    length = len(payload)
    head = bytearray()
    head.append(0x80 | (opcode & 0x0F))
    if length < 126:
        head.append(length)
    elif length < 65536:
        head.append(126)
        head.append((length >> 8) & 0xFF)
        head.append(length & 0xFF)
    else:
        head.append(127)
        for shift in (56, 48, 40, 32, 24, 16, 8, 0):
            head.append((length >> shift) & 0xFF)
    return bytes(head) + payload


def _websocket_frames(data):
    out = b""
    offset = 0
    while offset + 2 <= len(data):
        b0 = data[offset]
        b1 = data[offset + 1]
        opcode = b0 & 0x0F
        masked = bool(b1 & 0x80)
        length = b1 & 0x7F
        offset += 2
        if length == 126:
            if offset + 2 > len(data):
                break
            length = (data[offset] << 8) | data[offset + 1]
            offset += 2
        elif length == 127:
            if offset + 8 > len(data):
                break
            length = 0
            for _ in range(8):
                length = (length << 8) | data[offset]
                offset += 1
        mask = b""
        if masked:
            if offset + 4 > len(data):
                break
            mask = data[offset : offset + 4]
            offset += 4
        if offset + length > len(data):
            break
        payload = data[offset : offset + length]
        offset += length
        if masked:
            unmasked = bytearray(length)
            for i in range(length):
                unmasked[i] = payload[i] ^ mask[i & 3]
            payload = bytes(unmasked)
        if opcode == 0x1:
            out += _websocket_frame(0x1, payload)
        elif opcode == 0x9:
            out += _websocket_frame(0xA, payload)
        elif opcode == 0x8:
            out += _websocket_frame(0x8, payload)
        elif opcode == 0x2:
            out += _websocket_frame(0x2, payload)
    return out


def _wikipedia_response(path):
    title = _query_value(path, "titles") or _query_value(path, "title") or "MicroPython"
    search = _query_value(path, "srsearch") or "MicroPython"
    pageid = _query_value(path, "pageids") or "1"
    title_json = _json_escape(title)
    search_json = _json_escape(search)
    if "list=random" in path:
        return _json_response('{"query":{"random":[{"id":1,"ns":0,"title":"MicroPython"}]}}')
    if "list=search" in path:
        body = (
            '{"query":{"search":[{"pageid":1,"title":"MicroPython","snippet":"Python for microcontrollers"},'
            '{"pageid":2,"title":"Raspberry Pi Pico","snippet":"RP2040 development board"},'
            '{"pageid":3,"title":"Picoware","snippet":"Simulator fixture result for '
            + search_json
            + '"}]}}'
        )
        return _json_response(body)
    if "prop=links" in path:
        body = (
            '{"query":{"pages":[{"pageid":'
            + pageid
            + ',"title":"'
            + title_json
            + '","links":[{"ns":0,"title":"Python"},{"ns":0,"title":"Microcontroller"},{"ns":0,"title":"Raspberry Pi Pico"}]}]}}'
        )
        return _json_response(body)
    body = (
        '{"query":{"pages":[{"pageid":'
        + pageid
        + ',"title":"'
        + title_json
        + '","extract":"'
        + title_json
        + ' article from the Picoware simulator fixture. This text is returned by the MicroPython usocket shim so WikiReader can be tested without external network access.\\n\\n== Development ==\\nNavigation, scrolling, and article rendering should work here."}]}}'
    )
    return _json_response(body)
