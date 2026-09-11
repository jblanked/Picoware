"""Email - Send and receive email via SMTP and IMAP."""

# SMTP project details: https://RandomNerdTutorials.com/raspberry-pi-pico-w-send-email-micropython/
# uMail (MicroMail) for MicroPython: https://github.com/shawwwn/uMail/blob/master/umail.py
# Copyright (c) 2018 Shawwwn <shawwwn1@gmail.com> (SMTP client)
# Copyright (c) 2026 JBlanked <jblanked@jblanked.com> (IMAP4 and async wrapper)
# License: GPLv3
from micropython import const
from picoware.system.decorator import storage_required, wifi_required
try:
    import socket
    from ssl import wrap_socket as ssl_wrap_socket
    import _thread
    import binascii
    import re
except ImportError:
    pass

DEFAULT_TIMEOUT = const(10)  # sec
LOCAL_DOMAIN = "127.0.0.1"
CMD_EHLO = "EHLO"
CMD_STARTTLS = "STARTTLS"
CMD_AUTH = "AUTH"
CMD_MAIL = "MAIL"
AUTH_PLAIN = "PLAIN"
AUTH_LOGIN = "LOGIN"

IMAP_DEFAULT_TIMEOUT = const(30)  # sec
MAX_BODY_LENGTH = const(48 * 1024)  # cap stored body bytes

# view constants
VIEW_MAIN_MENU = const(0)  # Main menu view
VIEW_SENDING_MESSAGE = const(1)  # Sending message view
VIEW_KEYBOARD_RECIPIENT = const(2)  # viewing the keyboard to enter recipient email
VIEW_KEYBOARD_EMAIL = const(3)  # viewing the keyboard to enter email
VIEW_KEYBOARD_PASSWORD = const(4)  # viewing the keyboard to enter password
VIEW_KEYBOARD_NAME = const(5)  # viewing the keyboard to enter name
VIEW_KEYBOARD_SUBJECT = const(6)  # viewing the keyboard to enter subject
VIEW_EMAIL_LIST = const(7)  # viewing the list of unread emails
VIEW_EMAIL_VIEW = const(8)  # viewing a single email body

# menu constatnts
MENU_ITEM_SEND_MESSAGE = const(0)  # Menu item to send a message
MENU_ITEM_READ_EMAILS = const(1)  # Menu item to read emails
MENU_ITEM_SET_EMAIL = const(2)  # Menu item to set email
MENU_ITEM_SET_PASSWORD = const(3)  # Menu item to set password
MENU_ITEM_SET_NAME = const(4)  # Menu item to set sender name

# sending constants
SENDING_WAITING = const(-1)  # Waiting to send
SENDING_KEYBOARD = const(0)  # Keyboard for message input
SENDING_SENDING = const(1)  # Sending the message

# email reading constants
EMAIL_LIST_FETCHING = const(0)  # Fetching the unread email list
EMAIL_LIST_READY = const(1)  # Email list is ready
EMAIL_VIEW_FETCHING = const(0)  # Fetching an email body
EMAIL_VIEW_READY = const(1)  # Email body is ready

# bot token/chat ID constants
KEYBOARD_WAITING = const(-1)  # Waiting for keyboard input
KEYBOARD_ENTERING = const(0)  # Entering via keyboard

# globals
current_view = VIEW_MAIN_MENU
menu_index = MENU_ITEM_SEND_MESSAGE
sending_index = SENDING_WAITING
keyboard_index = KEYBOARD_WAITING

_menu = None
_loading = None
smtp = None
_imap = None
_message_to_send = ""

# email reading globals
_email_list = None
_email_textbox = None
_unread_emails = []
_current_email = None
_email_list_state = EMAIL_LIST_FETCHING
_email_view_state = EMAIL_VIEW_FETCHING

# Email details
sender_email = ""
sender_app_password = ""
sender_name = "Picoware"
recipient_email = "REPLACE_WITH_THE_RECIPIENT_EMAIL"
email_subject = "Hello from RPi Pico W"


class SMTP:
    """A minimal SMTP client for MicroPython."""

    def cmd(self, cmd_str):
        """Send a command and read the multi-line response.

        Args:
            cmd_str (str): The SMTP command to send.

        Returns:
            tuple: (code, response lines).
        """
        sock = self._sock
        sock.write("%s\r\n" % cmd_str)
        resp = []
        next = True
        while next:
            code = sock.read(3)
            next = sock.read(1) == b"-"
            resp.append(sock.readline().strip().decode())
        return int(code), resp

    def __init__(self, host, port, ssl=False, username=None, password=None):
        """Connect to an SMTP server.

        Args:
            host (str): The server hostname.
            port (int): The server port.
            ssl (bool): Use SSL/TLS. Defaults to False.
            username (str): The login username. Defaults to None.
            password (str): The login password. Defaults to None.
        """
        self.username = username
        addr = socket.getaddrinfo(host, port)[0][-1]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(DEFAULT_TIMEOUT)
        sock.connect(addr)
        if ssl:
            sock = ssl_wrap_socket(sock)
        code = int(sock.read(3))
        sock.readline()
        assert code == 220, "cant connect to server %d, %s" % (code, resp)
        self._sock = sock

        code, resp = self.cmd(CMD_EHLO + " " + LOCAL_DOMAIN)
        assert code == 250, "%d" % code
        if not ssl and CMD_STARTTLS in resp:
            code, resp = self.cmd(CMD_STARTTLS)
            assert code == 220, "start tls failed %d, %s" % (code, resp)
            self._sock = ssl_wrap_socket(sock)

        if username and password:
            self.login(username, password)

    def login(self, username, password):
        """Authenticate with the SMTP server.

        Args:
            username (str): The login username.
            password (str): The login password.

        Returns:
            tuple: (code, response lines).
        """
        self.username = username
        code, resp = self.cmd(CMD_EHLO + " " + LOCAL_DOMAIN)
        assert code == 250, "%d, %s" % (code, resp)

        auths = None
        for feature in resp:
            if feature[:4].upper() == CMD_AUTH:
                auths = feature[4:].strip("=").upper().split()
        assert auths != None, "no auth method"

        from ubinascii import b2a_base64 as b64

        if AUTH_PLAIN in auths:
            cren = b64("\0%s\0%s" % (username, password))[:-1].decode()
            code, resp = self.cmd("%s %s %s" % (CMD_AUTH, AUTH_PLAIN, cren))
        elif AUTH_LOGIN in auths:
            code, resp = self.cmd(
                "%s %s %s" % (CMD_AUTH, AUTH_LOGIN, b64(username)[:-1].decode())
            )
            assert code == 334, "wrong username %d, %s" % (code, resp)
            code, resp = self.cmd(b64(password)[:-1].decode())
        else:
            raise Exception("auth(%s) not supported " % ", ".join(auths))

        assert code == 235 or code == 503, "auth error %d, %s" % (code, resp)
        return code, resp

    def to(self, addrs, mail_from=None):
        """Set the mail recipients and start the DATA phase.

        Args:
            addrs (str or list): Recipient address(es).
            mail_from (str): The sender address. Defaults to None.

        Returns:
            tuple: (code, response lines).
        """
        mail_from = self.username if mail_from == None else mail_from
        code, resp = self.cmd("MAIL FROM: <%s>" % mail_from)
        assert code == 250, "sender refused %d, %s" % (code, resp)

        if isinstance(addrs, str):
            addrs = [addrs]
        count = 0
        for addr in addrs:
            code, resp = self.cmd("RCPT TO: <%s>" % addr)
            if code != 250 and code != 251:
                print("%s refused, %s" % (addr, resp))
                count += 1
        assert count != len(addrs), "recipient refused, %d, %s" % (code, resp)

        code, resp = self.cmd("DATA")
        assert code == 354, "data refused, %d, %s" % (code, resp)
        return code, resp

    def write(self, content):
        """Write raw content to the SMTP socket.

        Args:
            content (str or bytes): The content to write.
        """
        self._sock.write(content)

    def send(self, content=""):
        """Send the message body and termination sequence.

        Args:
            content (str): The message body. Defaults to "".

        Returns:
            tuple: (code, response text).
        """
        if content:
            self.write(content)
        self._sock.write("\r\n.\r\n")  # the five letter sequence marked for ending
        line = self._sock.readline()
        return (int(line[:3]), line[4:].strip().decode())

    def quit(self):
        """Send QUIT and close the connection."""
        self.cmd("QUIT")
        self._sock.close()


class SMTPAsync:
    '''Threaded version of SMTP for sending emails "asynchronously"'''

    def __init__(self, host, port, ssl=False, username=None, password=None):
        """Initialize the async SMTP wrapper.

        Args:
            host (str): The server hostname.
            port (int): The server port.
            ssl (bool): Use SSL/TLS. Defaults to False.
            username (str): The login username. Defaults to None.
            password (str): The login password. Defaults to None.
        """
        self.smtp = SMTP(host, port, ssl, username, password)
        self._is_running: bool = False
        self._thread = None
        self._lock = _thread.allocate_lock()

    def __del__(self):
        """Destructor to clean up resources."""
        self.close()

    @property
    def is_running(self) -> bool:
        """Check if the SMTPAsync is currently running."""
        return self._is_running

    def __close_thread(self):
        """Internal method to close the thread."""
        if self._thread is not None:
            self._thread = None

    def close(self):
        """Close the WebSocket connection."""
        self._is_running = False

        with self._lock:
            if self.smtp is not None:
                try:
                    self.smtp.quit()
                except Exception:
                    pass
                self.smtp = None
            self.__close_thread()

    def send_email(self, from_email, from_password, to_email, subject, message):
        """Send an email asynchronously.

        Args:
            from_email (str): The sender email.
            from_password (str): The sender app password.
            to_email (str): The recipient email.
            subject (str): The email subject.
            message (str): The email body.
        """

        def send_thread():
            """Run the send operation in a worker thread."""
            try:
                self._is_running = True
                self.smtp.login(from_email, from_password)
                self.smtp.to(to_email)
                self.smtp.write("From:" + sender_name + "<" + from_email + ">\n")
                self.smtp.write("Subject:" + subject + "\n")
                self.smtp.write(message)
                self.smtp.send()
            except Exception as e:
                print("Failed to send email:", e)
            finally:
                self.__close_thread()
                self._is_running = False

        if self._thread is None:
            self._thread = _thread.start_new_thread(send_thread, ())

class IMAP4:
    """A minimal IMAP4 client for MicroPython."""

    def __init__(self, host, port=993):
        """Connect to an IMAP server over SSL.

        Args:
            host (str): The server hostname.
            port (int): The server port. Defaults to 993.
        """
        self._sock = None
        self._tag = 0
        addr = socket.getaddrinfo(host, port)[0][-1]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(IMAP_DEFAULT_TIMEOUT)
        sock.connect(addr)
        sock = ssl_wrap_socket(sock)
        self._sock = sock
        line = self._read_line().strip()
        if not line.startswith(b"* OK"):
            self._sock.close()
            raise OSError("IMAP: bad greeting %r" % line)

    def _read_line(self):
        """Read a single line from the socket."""
        line = self._sock.readline()
        if not line:
            raise OSError("IMAP: connection closed")
        return line

    def _read_exact(self, n):
        """Read exactly n bytes from the socket.

        Args:
            n (int): The number of bytes to read.

        Returns:
            bytes: The bytes read.
        """
        buf = b""
        while len(buf) < n:
            chunk = self._sock.read(n - len(buf))
            if not chunk:
                break
            buf += chunk
        return buf

    def _read_literal(self, size, max_literal=0):
        """Read a literal, keeping only the first max_literal bytes.

        Args:
            size (int): The literal size.
            max_literal (int): Maximum bytes to keep. Defaults to 0.

        Returns:
            bytes: The literal bytes.
        """
        if max_literal and size > max_literal:
            literal = self._read_exact(max_literal)
            remaining = size - max_literal
            while remaining > 0:
                chunk = self._sock.read(min(2048, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
        else:
            literal = self._read_exact(size)
        self._read_line()  # consume trailing CRLF
        return literal

    def _response(self, tag, max_literal=0):
        """Read responses until the tagged response for `tag`.

        Args:
            tag (bytes): The command tag.
            max_literal (int): Maximum literal bytes to keep. Defaults to 0.

        Returns:
            tuple: (status, data); literals are stored as ('literal', bytes).
        """
        data = []
        while True:
            line = self._read_line().rstrip(b"\r\n")
            if line.startswith(b"*"):
                if line.endswith(b"}"):
                    b = line.rfind(b"{")
                    if b > 0:
                        try:
                            size = int(line[b + 1:-1].decode("ascii"))
                        except (ValueError, TypeError):
                            size = -1
                        if size >= 0:
                            data.append(line[:b])
                            data.append(
                                ("literal", self._read_literal(size, max_literal))
                            )
                            continue
                data.append(line)
                continue
            if line.startswith(tag + b" "):
                rest = line[len(tag) + 1:]
                status = rest.split(b" ", 1)[0]
                return status, data

    def _cmd(self, command):
        """Send a tagged IMAP command and return its tag.

        Args:
            command (str): The IMAP command.

        Returns:
            bytes: The command tag.
        """
        self._tag += 1
        tag = b"a%03d" % self._tag
        self._sock.write(tag + b" " + command.encode("utf-8") + b"\r\n")
        return tag

    def login(self, username, password):
        """Authenticate with the server.

        Args:
            username (str): The login username.
            password (str): The login password.

        Returns:
            bool: True on success.
        """
        user = username.replace("\\", "\\\\").replace('"', '\\"')
        pwd = password.replace("\\", "\\\\").replace('"', '\\"')
        tag = self._cmd('LOGIN "%s" "%s"' % (user, pwd))
        status, _ = self._response(tag)
        return status == b"OK"

    def select(self, mailbox="INBOX"):
        """Select a mailbox.

        Args:
            mailbox (str): The mailbox name. Defaults to "INBOX".

        Returns:
            tuple: (ok, response data).
        """
        tag = self._cmd("SELECT %s" % mailbox)
        status, data = self._response(tag)
        return status == b"OK", data

    def uid_search(self, criteria="UNSEEN"):
        """Search by UID.

        Args:
            criteria (str): The search criteria. Defaults to "UNSEEN".

        Returns:
            list: UID strings.
        """
        tag = self._cmd("UID SEARCH %s" % criteria)
        status, data = self._response(tag)
        ids = []
        if status == b"OK":
            for item in data:
                if isinstance(item, bytes) and item.startswith(b"* SEARCH"):
                    for x in item.split(b" ")[2:]:
                        ids.append(x.decode("ascii"))
                    break
        return ids

    def uid_fetch(self, uid, parts, max_literal=0):
        """Fetch a body part by UID.

        Args:
            uid (str): The message UID.
            parts (str): The body part specifier.
            max_literal (int): Maximum literal bytes to keep. Defaults to 0.

        Returns:
            bytes or None: The literal bytes.
        """
        tag = self._cmd("UID FETCH %s %s" % (uid, parts))
        status, data = self._response(tag, max_literal=max_literal)
        if status != b"OK":
            return None
        for item in data:
            if isinstance(item, tuple) and item[0] == "literal":
                return item[1]
        return None

    def uid_store(self, uid, flags="(\\Seen)"):
        """Set flags on a message by UID.

        Args:
            uid (str): The message UID.
            flags (str): The flags to set. Defaults to "(\\Seen)".

        Returns:
            bool: True on success.
        """
        tag = self._cmd("UID STORE %s +FLAGS %s" % (uid, flags))
        status, _ = self._response(tag)
        return status == b"OK"

    def logout(self):
        """Close the IMAP session."""
        try:
            tag = self._cmd("LOGOUT")
            self._response(tag)
        except Exception:
            pass
        try:
            self._sock.close()
        except Exception:
            pass
        self._sock = None


def _b64decode(data):
    """Decode base64 bytes, tolerating whitespace and missing padding.

    Args:
        data (bytes or str): The base64 data.

    Returns:
        bytes: The decoded bytes.
    """
    if isinstance(data, str):
        data = data.encode("ascii")
    data = data.replace(b"\r\n", b"").replace(b"\n", b"").replace(b" ", b"")
    rem = len(data) % 4
    if rem:
        data += b"=" * (4 - rem)
    return binascii.a2b_base64(data)


def _q_decode(s):
    """Decode an RFC 2047 Q-encoded string into unicode.

    Args:
        s (str): The Q-encoded string.

    Returns:
        str: The decoded string.
    """
    out = bytearray()
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "=" and i + 2 < n:
            try:
                out.append(int(s[i + 1:i + 3], 16))
                i += 3
                continue
            except ValueError:
                pass
        if c == "_":
            out.append(0x20)
        else:
            out.extend(c.encode("utf-8"))
        i += 1
    return bytes(out).decode("utf-8", "ignore")


def _decode_encoded_words(raw):
    """Decode RFC 2047 encoded-words in a header value.

    Args:
        raw (str): The header value.

    Returns:
        str: The decoded value.
    """
    if not raw or "=?" not in raw:
        return raw
    out = []
    i = 0
    n = len(raw)
    while i < n:
        sidx = raw.find("=?", i)
        if sidx < 0:
            out.append(raw[i:])
            break
        end = raw.find("?=", sidx + 2)
        if end < 0:
            out.append(raw[i:])
            break
        out.append(raw[i:sidx])
        token = raw[sidx + 2:end]
        parts = token.split("?")
        if len(parts) >= 3 and parts[0]:
            encoding = parts[1].upper()
            payload = parts[2]
            try:
                if encoding == "B":
                    decoded = _b64decode(payload).decode("utf-8", "ignore")
                elif encoding == "Q":
                    decoded = _q_decode(payload)
                else:
                    decoded = payload
            except Exception:
                decoded = payload
            out.append(decoded)
            i = end + 2
        else:
            out.append(raw[i:])
            break
    return "".join(out)


def _qp_decode_bytes(data):
    """Decode a quoted-printable byte string.

    Args:
        data (bytes): The quoted-printable data.

    Returns:
        bytes: The decoded bytes.
    """
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        c = data[i]
        if c == 0x3D:  # '='
            if i + 2 < n and data[i + 1] != 0x0A:
                try:
                    out.append(int(data[i + 1:i + 3].decode("ascii"), 16))
                    i += 3
                    continue
                except ValueError:
                    pass
            if i + 2 < n and data[i + 1] == 0x0D and data[i + 2] == 0x0A:
                i += 3  # soft line break =\r\n
                continue
            if i + 1 < n and data[i + 1] == 0x0A:
                i += 2  # soft line break =\n
                continue
        out.append(c)
        i += 1
    return bytes(out)


def _parse_headers(header_blob):
    """Parse a raw header block into a dict of name -> [values].

    Args:
        header_blob (bytes or str): The raw header block.

    Returns:
        dict: Header names mapped to value lists.
    """
    if isinstance(header_blob, bytes):
        text = header_blob.decode("utf-8", "ignore")
    else:
        text = header_blob
    headers = {}
    if "\r\n" in text:
        lines = text.split("\r\n")
    else:
        lines = text.split("\n")
    current = None
    for line in lines:
        if line.startswith(" ") or line.startswith("\t"):
            if current is not None and headers[current]:
                headers[current][-1] += " " + line.strip()
        elif ":" in line:
            name, _, value = line.partition(":")
            current = name.strip().lower()
            headers.setdefault(current, []).append(value.strip())
        else:
            current = None
    return headers


def _first_header(headers, name):
    """Get the first value for a header name.

    Args:
        headers (dict): Parsed headers.
        name (str): The header name.

    Returns:
        str: The first value, or "".
    """
    if name in headers and headers[name]:
        return headers[name][0]
    return ""


def _header_param(header_value, param):
    """Get a parameter value from a header value.

    Args:
        header_value (str): The header value.
        param (str): The parameter name.

    Returns:
        str or None: The parameter value.
    """
    if not header_value:
        return None
    for part in header_value.split(";")[1:]:
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            if k.strip().lower() == param:
                return v.strip().strip('"').strip("'")
    return None


def _decode_body_part(data, cte, charset=None):
    """Decode a MIME body part into a unicode string.

    Args:
        data (bytes): The body part data.
        cte (str): The content transfer encoding.
        charset (str): The character set. Defaults to None.

    Returns:
        str: The decoded text.
    """
    if not data:
        return ""
    cte = (cte or "").strip().lower()
    try:
        if cte == "base64":
            data = _b64decode(data)
        elif cte == "quoted-printable":
            data = _qp_decode_bytes(data)
    except Exception:
        pass
    try:
        text = data.decode(charset or "utf-8", "ignore")
    except Exception:
        text = data.decode("utf-8", "ignore")
    return text.replace("\r\n", "\n").rstrip()


def _walk_multipart(body_blob, boundary):
    """Walk a multipart body and return concatenated text/plain parts.

    Args:
        body_blob (bytes): The multipart body.
        boundary (str): The MIME boundary.

    Returns:
        str: The concatenated plain-text parts.
    """
    marker = ("--" + boundary).encode("utf-8")
    parts = body_blob.split(marker)
    texts = []
    for part in parts[1:]:
        part = part.lstrip(b"\r\n")
        if part.startswith(b"--"):
            break  # closing delimiter
        sep = part.find(b"\r\n\r\n")
        if sep < 0:
            sep = part.find(b"\n\n")
            if sep < 0:
                continue
            hdr_blob = part[:sep]
            part_body = part[sep + 2:]
        else:
            hdr_blob = part[:sep]
            part_body = part[sep + 4:]
        sub_headers = _parse_headers(hdr_blob)
        ctype_header = _first_header(sub_headers, "content-type")
        sub_ctype = (
            ctype_header.split(";")[0].strip().lower()
            if ctype_header else "text/plain"
        )
        cte = _first_header(sub_headers, "content-transfer-encoding")
        charset = _header_param(ctype_header, "charset")
        if sub_ctype.startswith("multipart/"):
            sub_boundary = _header_param(ctype_header, "boundary")
            if sub_boundary:
                nested = _walk_multipart(part_body, sub_boundary)
                if nested:
                    texts.append(nested)
        elif sub_ctype == "text/plain":
            texts.append(_decode_body_part(part_body, cte, charset))
    return "\n".join(texts)


def _extract_plain_text(body_blob, headers):
    """Extract the plain-text body from a raw MIME body + headers dict.

    Args:
        body_blob (bytes): The message body.
        headers (dict): Parsed headers.

    Returns:
        str: The plain-text body.
    """
    ctype_header = _first_header(headers, "content-type")
    ctype = (
        ctype_header.split(";")[0].strip().lower()
        if ctype_header else "text/plain"
    )
    cte = _first_header(headers, "content-transfer-encoding")
    charset = _header_param(ctype_header, "charset")
    if ctype.startswith("multipart/"):
        boundary = _header_param(ctype_header, "boundary")
        if not boundary:
            return _decode_body_part(body_blob, cte, charset)
        return _walk_multipart(body_blob, boundary)
    return _decode_body_part(body_blob, cte, charset)


def _split_message(literal):
    """Split an RFC822 message into (header_blob, body_blob).

    Args:
        literal (bytes): The raw message.

    Returns:
        tuple: (header_blob, body_blob).
    """
    sep = literal.find(b"\r\n\r\n")
    if sep < 0:
        sep = literal.find(b"\n\n")
        if sep < 0:
            return literal, b""
        return literal[:sep], literal[sep + 2:]
    return literal[:sep], literal[sep + 4:]


def _extract_email_address(header):
    """Extract the email address from a From/To header value.

    Args:
        header (str): The header value.

    Returns:
        str: The email address.
    """
    if not header:
        return ""
    try:
        match = re.search(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", header)
        return match.group(0) if match else header.strip()
    except Exception:
        return header.strip()

def imap_fetch_unread_count(from_email, from_pass):
    """Returns the total count of unread emails.

    Args:
        from_email (str): The sender email.
        from_pass (str): The sender app password.

    Returns:
        int: The total count of unread emails.

    Raises:
        OSError: On connection or auth errors.
    """
    mail = None
    try:
        mail = IMAP4("imap.gmail.com", 993)
        if not mail.login(from_email, from_pass):
            raise OSError("IMAP login failed")
        ok, _ = mail.select("INBOX")
        if not ok:
            raise OSError("IMAP SELECT failed")
        ids = mail.uid_search("UNSEEN")
        if mail is not None:
            mail.logout()
        return len(ids)
    except Exception as e:
        if mail is not None:
            mail.logout()
        raise OSError("IMAP error") from e

def imap_fetch_unread_emails(from_email, from_pass, limit=10):
    """Fetch summaries of the most recent unread emails.

    Args:
        from_email (str): The sender email.
        from_pass (str): The sender app password.
        limit (int): Maximum number of emails. Defaults to 10.

    Returns:
        list: uid/subject/from/to/date dicts (newest first).

    Raises:
        OSError: On connection or auth errors.
    """
    results = []
    mail = None
    try:
        mail = IMAP4("imap.gmail.com", 993)
        if not mail.login(from_email, from_pass):
            raise OSError("IMAP login failed")
        ok, _ = mail.select("INBOX")
        if not ok:
            raise OSError("IMAP SELECT failed")
        ids = mail.uid_search("UNSEEN")[-limit:]
        for uid in reversed(ids):
            literal = mail.uid_fetch(
                uid,
                "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM TO DATE)])",
                max_literal=8192,
            )
            if literal is None:
                continue
            headers = _parse_headers(literal)
            results.append(
                {
                    "uid": str(uid),
                    "subject": _decode_encoded_words(
                        _first_header(headers, "subject")
                    ),
                    "from": _decode_encoded_words(
                        _first_header(headers, "from")
                    ),
                    "to": _decode_encoded_words(
                        _first_header(headers, "to")
                    ),
                    "date": _decode_encoded_words(
                        _first_header(headers, "date")
                    ),
                }
            )
    finally:
        if mail is not None:
            mail.logout()
    return results


def imap_fetch_email_by_uid(from_email, from_pass, uid, mark_seen=False):
    """Fetch a single email by IMAP UID.

    Args:
        from_email (str): The sender email.
        from_pass (str): The sender app password.
        uid (str): The message UID.
        mark_seen (bool): Mark the email as seen. Defaults to False.

    Returns:
        dict or None: The email details.

    Raises:
        OSError: On connection errors.
    """
    mail = None
    try:
        mail = IMAP4("imap.gmail.com", 993)
        if not mail.login(from_email, from_pass):
            raise OSError("IMAP login failed")
        ok, _ = mail.select("INBOX")
        if not ok:
            raise OSError("IMAP SELECT failed")

        if mark_seen:
            literal = mail.uid_fetch(uid, "(RFC822)", max_literal=MAX_BODY_LENGTH)
            if literal is None:
                return None
            hdr_blob, body_blob = _split_message(literal)
            headers = _parse_headers(hdr_blob)
            body = _extract_plain_text(body_blob, headers)
        else:
            hdr_literal = mail.uid_fetch(
                uid,
                "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM TO DATE CONTENT-TYPE CONTENT-TRANSFER-ENCODING)])",
                max_literal=8192,
            )
            if hdr_literal is None:
                return None
            headers = _parse_headers(hdr_literal)
            body_literal = mail.uid_fetch(
                uid, "(BODY.PEEK[TEXT])", max_literal=MAX_BODY_LENGTH
            )
            if body_literal is None:
                return None
            body = _extract_plain_text(body_literal, headers)

        return {
            "uid": str(uid),
            "subject": _decode_encoded_words(_first_header(headers, "subject")),
            "from": _decode_encoded_words(_first_header(headers, "from")),
            "to": _decode_encoded_words(_first_header(headers, "to")),
            "date": _decode_encoded_words(_first_header(headers, "date")),
            "body": body,
        }
    finally:
        if mail is not None:
            mail.logout()


def imap_mark_seen(from_email, from_pass, uid):
    """Mark an email as seen by IMAP UID.

    Args:
        from_email (str): The sender email.
        from_pass (str): The sender app password.
        uid (str): The message UID.

    Returns:
        bool: True on success.
    """
    mail = None
    try:
        mail = IMAP4("imap.gmail.com", 993)
        if not mail.login(from_email, from_pass):
            return False
        ok, _ = mail.select("INBOX")
        if not ok:
            return False
        return mail.uid_store(str(uid), "(\\Seen)")
    finally:
        if mail is not None:
            mail.logout()


class IMAPAsync:
    """Threaded IMAP helper so network fetches don't block the UI."""

    def __init__(self):
        """Initialize the async IMAP helper."""
        self._lock = _thread.allocate_lock()
        self._thread = None
        self._running = False
        self._finished = False
        self._result = None
        self._error = ""

    def __del__(self):
        """Destructor to clean up resources."""
        self.close()

    @property
    def is_running(self) -> bool:
        """Return whether a fetch is running."""
        return self._running

    @property
    def is_finished(self) -> bool:
        """Return whether the fetch has finished."""
        return self._finished

    @property
    def result(self):
        """Return the fetch result."""
        return self._result

    @property
    def error(self) -> str:
        """Return the last error message."""
        return self._error

    def close(self):
        """Reset the helper and release the worker thread."""
        with self._lock:
            self._running = False
            self._finished = True
            self._result = None
            self._error = ""
            self._thread = None

    def _start(self, func) -> bool:
        """Run a function in a background thread if idle.

        Args:
            func (callable): The function to run.

        Returns:
            bool: True if the thread was started.
        """
        def thread_fn():
            """Execute the fetch and store its result."""
            try:
                result = func()
                with self._lock:
                    self._result = result
            except Exception as e:
                print("IMAPAsync error:", e)
                with self._lock:
                    self._error = str(e)
            finally:
                with self._lock:
                    self._finished = True
                    self._running = False
                self._thread = None

        with self._lock:
            if self._thread is not None:
                return False
            self._finished = False
            self._running = True
            self._error = ""
            self._result = None
            self._thread = _thread.start_new_thread(thread_fn, ())
        return True

    def fetch_unread_count(self, from_email, from_pass) -> bool:
        """Fetch the total count of unread emails in the background.

        Args:
            from_email (str): The sender email.
            from_pass (str): The sender app password.

        Returns:
            bool: True if the thread was started.
        """
        return self._start(
            lambda: imap_fetch_unread_count(from_email, from_pass)
        )

    def fetch_unread_emails(self, from_email, from_pass, limit=10) -> bool:
        """Fetch unread email summaries in the background.

        Args:
            from_email (str): The sender email.
            from_pass (str): The sender app password.
            limit (int): Maximum number of emails. Defaults to 10.

        Returns:
            bool: True if the thread was started.
        """
        return self._start(
            lambda: imap_fetch_unread_emails(from_email, from_pass, limit)
        )

    def fetch_email_by_uid(self, from_email, from_pass, uid, mark_seen=False) -> bool:
        """Fetch one email body in the background.

        Args:
            from_email (str): The sender email.
            from_pass (str): The sender app password.
            uid (str): The message UID.
            mark_seen (bool): Mark the email as seen. Defaults to False.

        Returns:
            bool: True if the thread was started.
        """
        return self._start(
            lambda: imap_fetch_email_by_uid(from_email, from_pass, uid, mark_seen)
        )

    def mark_seen_and_refresh(self, from_email, from_pass, uid) -> bool:
        """Mark one email seen, then refetch the unread list in one thread.

        Args:
            from_email (str): The sender email.
            from_pass (str): The sender app password.
            uid (str): The message UID.

        Returns:
            bool: True if the thread was started.
        """

        def task():
            """Mark seen and refetch the unread list."""
            imap_mark_seen(from_email, from_pass, uid)
            return imap_fetch_unread_emails(from_email, from_pass)

        return self._start(task)

def __await_send(view_manager) -> None:
    """Wait for email sending to complete.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global sending_index, current_view
    if smtp.is_running:
        _loading_run(view_manager, "Sending...")
        return
    view_manager.alert("Message sent!", False)
    sending_index = SENDING_WAITING
    current_view = VIEW_MAIN_MENU


def __load_email_credentials(view_manager) -> bool:
    """Load email credentials from storage.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True if credentials are set.
    """
    global sender_email, sender_app_password, sender_name, email_subject
    storage = view_manager.storage
    stored_email = storage.read("picoware/email/email.txt")
    stored_password = storage.read("picoware/email/password.txt")
    stored_name = storage.read("picoware/email/name.txt")
    if stored_email:
        sender_email = stored_email
    if stored_password:
        sender_app_password = stored_password
    if stored_name:
        sender_name = stored_name
    return sender_email != "" and sender_app_password != ""


def _keyboard_save(view_manager) -> bool:
    """Keyboard callback to save the entered value.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    global _message_to_send, recipient_email, email_subject
    storage = view_manager.storage
    kb = view_manager.keyboard
    if current_view == VIEW_SENDING_MESSAGE:
        _message_to_send = kb.response
        return True
    if current_view == VIEW_KEYBOARD_RECIPIENT:
        recipient_email = kb.response
        return True
    if current_view == VIEW_KEYBOARD_SUBJECT:
        email_subject = kb.response
        return True

    # Determine which file to write to based on current view
    file_path = ""
    if current_view == VIEW_KEYBOARD_EMAIL:
        file_path = "picoware/email/email.txt"
    elif current_view == VIEW_KEYBOARD_PASSWORD:
        file_path = "picoware/email/password.txt"
    elif current_view == VIEW_KEYBOARD_NAME:
        file_path = "picoware/email/name.txt"

    if file_path:
        return storage.write(file_path, kb.response)
    return False


def _keyboard_run(view_manager) -> bool:
    """Start the keyboard view.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True while the keyboard is active.
    """
    global current_view, sending_index, keyboard_index

    # Initialize keyboard for subject (part of send flow)
    if current_view == VIEW_KEYBOARD_SUBJECT and keyboard_index == KEYBOARD_WAITING:
        kb = view_manager.keyboard
        kb.reset()
        kb.title = "Enter Subject"
        kb.response = ""
        keyboard_index = KEYBOARD_ENTERING
        kb.run(force=True)
        kb.run(force=True)
        return True

    # Initialize keyboard for recipient email
    if current_view == VIEW_KEYBOARD_RECIPIENT and keyboard_index == KEYBOARD_WAITING:
        kb = view_manager.keyboard
        kb.reset()
        kb.title = "Enter Recipient Email"
        kb.response = (
            recipient_email
            if recipient_email != "REPLACE_WITH_THE_RECIPIENT_EMAIL"
            else ""
        )
        keyboard_index = KEYBOARD_ENTERING
        kb.run(force=True)
        kb.run(force=True)
        return True

    # Initialize keyboard for sending message
    if current_view == VIEW_SENDING_MESSAGE and sending_index == SENDING_WAITING:
        kb = view_manager.keyboard
        kb.reset()
        kb.title = "Enter Message"
        kb.response = ""
        kb.run(force=True)
        kb.run(force=True)
        sending_index = SENDING_KEYBOARD
        return True

    # Initialize keyboard for email/password/name
    if (
        current_view
        in (VIEW_KEYBOARD_EMAIL, VIEW_KEYBOARD_PASSWORD, VIEW_KEYBOARD_NAME)
        and keyboard_index == KEYBOARD_WAITING
    ):
        storage = view_manager.storage
        kb = view_manager.keyboard
        kb.reset()
        if current_view == VIEW_KEYBOARD_EMAIL:
            kb.title = "Enter Email"
            kb.response = storage.read("picoware/email/email.txt")
        elif current_view == VIEW_KEYBOARD_PASSWORD:
            kb.title = "Enter Password"
            kb.response = storage.read("picoware/email/password.txt")
        elif current_view == VIEW_KEYBOARD_NAME:
            kb.title = "Enter Sender Name"
            kb.response = storage.read("picoware/email/name.txt")
        keyboard_index = KEYBOARD_ENTERING
        kb.run(force=True)
        kb.run(force=True)
        return True

    # Run keyboard for subject (part of send flow)
    if current_view == VIEW_KEYBOARD_SUBJECT and keyboard_index == KEYBOARD_ENTERING:
        kb = view_manager.keyboard
        if not kb.run():
            return False

        if kb.is_finished:
            if not _keyboard_save(view_manager):
                view_manager.alert("Failed to save subject.", False)
                current_view = VIEW_MAIN_MENU
                keyboard_index = KEYBOARD_WAITING
            else:
                # Move to recipient email entry
                current_view = VIEW_KEYBOARD_RECIPIENT
                keyboard_index = KEYBOARD_WAITING
                _keyboard_run(view_manager)
        return True

    # Run keyboard for recipient email
    if current_view == VIEW_KEYBOARD_RECIPIENT and keyboard_index == KEYBOARD_ENTERING:
        kb = view_manager.keyboard
        if not kb.run():
            return False

        if kb.is_finished:
            if not _keyboard_save(view_manager):
                view_manager.alert("Failed to save recipient email.", False)
                current_view = VIEW_MAIN_MENU
                keyboard_index = KEYBOARD_WAITING
            else:
                # Move to message entry
                current_view = VIEW_SENDING_MESSAGE
                keyboard_index = KEYBOARD_WAITING
                _keyboard_run(view_manager)
        return True

    # Run keyboard for sending message
    if current_view == VIEW_SENDING_MESSAGE and sending_index == SENDING_KEYBOARD:
        kb = view_manager.keyboard
        if not kb.run():
            return False

        if kb.is_finished:
            if not _keyboard_save(view_manager):
                view_manager.alert("Failed to save message.", False)
                current_view = VIEW_MAIN_MENU
                sending_index = SENDING_WAITING
            else:
                # Start sending the message
                try:
                    if not __load_email_credentials(view_manager):
                        view_manager.alert("Email credentials not set!", False)
                        current_view = VIEW_MAIN_MENU
                        sending_index = SENDING_WAITING
                        return True
                    smtp.send_email(
                        sender_email,
                        sender_app_password,
                        recipient_email,
                        email_subject,
                        _message_to_send,
                    )
                    sending_index = SENDING_SENDING
                    __await_send(view_manager)
                except Exception as e:
                    print("Failed to send email:", e)
                    view_manager.alert(f"Failed to send message: {e}", False)

                current_view = VIEW_MAIN_MENU
                sending_index = SENDING_WAITING
        return True

    # Run keyboard for sender email/password/name
    if (
        current_view
        in (VIEW_KEYBOARD_EMAIL, VIEW_KEYBOARD_PASSWORD, VIEW_KEYBOARD_NAME)
        and keyboard_index == KEYBOARD_ENTERING
    ):
        kb = view_manager.keyboard
        if not kb.run():
            return False

        if kb.is_finished:
            if not _keyboard_save(view_manager):
                view_manager.alert("Failed to save input.", False)
            else:
                view_manager.alert("Input saved!", False)
            current_view = VIEW_MAIN_MENU
            keyboard_index = KEYBOARD_WAITING
            _menu_start(view_manager)
        return True


def _loading_run(view_manager, message: str = "Sending...") -> None:
    """Start the loading view.

    Args:
        view_manager (ViewManager): The view manager context.
        message (str): The loading message. Defaults to "Sending...".
    """
    from picoware.gui.loading import Loading

    global _loading

    if _loading is None:
        draw = view_manager.draw
        bg = view_manager.background_color
        fg = view_manager.foreground_color

        _loading = Loading(draw, fg, bg)
        _loading.text = message
        _loading.animate()
    else:
        _loading.animate()


def _menu_start(view_manager) -> None:
    """Start the menu view.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.gui.menu import Menu

    global _menu

    if _menu is not None:
        del _menu
        _menu = None

    draw = view_manager.draw
    bg = view_manager.background_color
    fg = view_manager.foreground_color

    # set menu
    _menu = Menu(
        draw,
        "Email",
        0,
        draw.size.y,
        fg,
        bg,
        view_manager.selected_color,
        fg,
    )

    # add items
    _menu.add_item("Send Message")
    _menu.add_item("Read Emails")
    _menu.add_item("Set Email")
    _menu.add_item("Set Password")
    _menu.add_item("Set Name")

    _menu.set_selected(menu_index)
    _menu.set_selected(menu_index)


def _reset_email_list() -> None:
    """Clear the email list state."""
    global _email_list, _unread_emails, _current_email, _email_list_state
    _email_list = None
    _unread_emails = []
    _current_email = None
    _email_list_state = EMAIL_LIST_FETCHING


def _build_email_list(view_manager) -> None:
    """Build the List widget from the fetched unread emails.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.gui.menu import Menu

    global _email_list
    draw = view_manager.draw
    bg = view_manager.background_color
    fg = view_manager.foreground_color

    _email_list = Menu(
        draw,
        "Unread Emails",
        0,
        draw.size.y,
        fg,
        bg,
        selected_color=view_manager.selected_color,
        border_color=fg,
    )
    for email in _unread_emails:
        subject = email.get("subject") or "(no subject)"
        _email_list.add_item(subject)
    _email_list.set_selected(0)
    _email_list.draw()


def _open_email(view_manager, summary) -> None:
    """Open a single email: fetch its body and show it.

    Args:
        view_manager (ViewManager): The view manager context.
        summary (dict): The email summary.
    """
    global current_view, _current_email, _email_view_state
    _current_email = summary
    _email_view_state = EMAIL_VIEW_FETCHING
    current_view = VIEW_EMAIL_VIEW
    if not __load_email_credentials(view_manager):
        view_manager.alert("Email credentials not set!", False)
        _back_to_email_list(view_manager)
        return
    _imap.fetch_email_by_uid(sender_email, sender_app_password, summary["uid"])


def _show_email(view_manager, data) -> None:
    """Render a fetched email in a scrollable text box.

    Args:
        view_manager (ViewManager): The view manager context.
        data (dict): The email details.
    """
    from picoware.gui.textbox import TextBox

    global _email_textbox
    draw = view_manager.draw
    bg = view_manager.background_color
    fg = view_manager.foreground_color

    _email_textbox = TextBox(draw, 0, draw.size.y, fg, bg)
    body = data.get("body") or "(no body)"
    text = "From: %s\nTo: %s\nDate: %s\nSubject: %s\n\n%s" % (
        data.get("from", ""),
        data.get("to", ""),
        data.get("date", ""),
        data.get("subject", ""),
        body,
    )
    _email_textbox.set_text(text)


def _back_to_email_list(view_manager) -> None:
    """Return from viewing an email to the email list.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global current_view, _email_view_state, _email_textbox
    _email_view_state = EMAIL_VIEW_FETCHING
    _email_textbox = None
    current_view = VIEW_EMAIL_LIST
    if _email_list is not None:
        _email_list.draw()


def _email_list_run(view_manager) -> bool:
    """Run the email list view.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: False when leaving the view.
    """
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_LEFT,
        BUTTON_DOWN,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )

    global current_view, _email_list_state, _unread_emails

    if _email_list_state == EMAIL_LIST_FETCHING:
        if _imap.is_running:
            _loading_run(view_manager, "Fetching emails...")
            return True
        if _imap.error or _imap.result is None:
            err = _imap.error or "no data"
            view_manager.alert("Fetch failed: " + err[:36], False)
            _reset_email_list()
            current_view = VIEW_MAIN_MENU
            _menu_start(view_manager)
            return False
        _unread_emails = _imap.result
        if not _unread_emails:
            view_manager.alert("No unread emails!", False)
            _reset_email_list()
            current_view = VIEW_MAIN_MENU
            _menu_start(view_manager)
            return False
        _build_email_list(view_manager)
        _email_list_state = EMAIL_LIST_READY
        return True

    # EMAIL_LIST_READY
    inp = view_manager.input_manager
    button = inp.button
    if button == BUTTON_BACK:
        inp.reset()
        _reset_email_list()
        current_view = VIEW_MAIN_MENU
        _menu_start(view_manager)
        return False
    if button in (BUTTON_UP, BUTTON_LEFT):
        inp.reset()
        _email_list.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        inp.reset()
        _email_list.scroll_down()
    elif button == BUTTON_CENTER:
        inp.reset()
        idx = _email_list.selected_index
        if 0 <= idx < len(_unread_emails):
            _open_email(view_manager, _unread_emails[idx])
    return True


def _email_view_run(view_manager) -> bool:
    """Run the single-email view.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: False when leaving the view.
    """
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_LEFT,
        BUTTON_DOWN,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )

    global _email_view_state

    if _email_view_state == EMAIL_VIEW_FETCHING:
        if _imap.is_running:
            _loading_run(view_manager, "Loading email...")
            return True
        if _imap.error or _imap.result is None:
            err = _imap.error or "no data"
            view_manager.alert("Load failed: " + err[:36], False)
            _back_to_email_list(view_manager)
            return False
        _show_email(view_manager, _imap.result)
        _email_view_state = EMAIL_VIEW_READY
        return True

    # EMAIL_VIEW_READY
    inp = view_manager.input_manager
    button = inp.button
    if button == BUTTON_BACK:
        inp.reset()
        _back_to_email_list(view_manager)
        return False
    if button in (BUTTON_UP, BUTTON_LEFT):
        inp.reset()
        _email_textbox.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        inp.reset()
        _email_textbox.scroll_down()
    elif button == BUTTON_CENTER:
        inp.reset()
        _mark_seen_and_refresh(view_manager)
        return False
    return True


def _mark_seen_and_refresh(view_manager) -> None:
    """Mark the current email as seen, then refresh the unread list.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global current_view, _email_textbox, _email_view_state, _email_list_state
    _email_view_state = EMAIL_VIEW_FETCHING
    _email_textbox = None
    if not __load_email_credentials(view_manager):
        _back_to_email_list(view_manager)
        return
    current_view = VIEW_EMAIL_LIST
    _email_list_state = EMAIL_LIST_FETCHING
    _imap.mark_seen_and_refresh(
        sender_email, sender_app_password, _current_email["uid"]
    )

@storage_required
@wifi_required
def start(view_manager) -> bool:
    """Start the app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """

    # create email folder if it doesn't exist
    view_manager.storage.mkdir("picoware/email")

    _menu_start(view_manager)

    global smtp, _imap

    smtp = SMTPAsync("smtp.gmail.com", 465, ssl=True)  # Gmail's SSL port
    _imap = IMAPAsync()  # IMAP client for reading emails

    __load_email_credentials(view_manager)

    return True


def run(view_manager) -> None:
    """Run the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_LEFT,
        BUTTON_DOWN,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )

    inp = view_manager.input_manager
    button = inp.button

    global current_view, menu_index, sending_index, keyboard_index

    if current_view == VIEW_MAIN_MENU:
        if button == BUTTON_BACK:
            inp.reset()
            view_manager.back()
        elif button in (BUTTON_UP, BUTTON_LEFT):
            inp.reset()
            _menu.scroll_up()
        elif button in (BUTTON_DOWN, BUTTON_RIGHT):
            inp.reset()
            _menu.scroll_down()
        elif button == BUTTON_CENTER:
            inp.reset()
            menu_index = _menu.selected_index
            if menu_index == MENU_ITEM_SEND_MESSAGE:
                current_view = VIEW_KEYBOARD_SUBJECT
                if not _keyboard_run(view_manager):
                    view_manager.back()
            elif menu_index == MENU_ITEM_READ_EMAILS:
                current_view = VIEW_EMAIL_LIST
                _email_list_state = EMAIL_LIST_FETCHING
                if not __load_email_credentials(view_manager):
                    view_manager.alert("Email credentials not set!", False)
                    current_view = VIEW_MAIN_MENU
                    _menu_start(view_manager)
                else:
                    _imap.fetch_unread_emails(
                        sender_email, sender_app_password
                    )
            elif menu_index == MENU_ITEM_SET_EMAIL:
                current_view = VIEW_KEYBOARD_EMAIL
                if not _keyboard_run(view_manager):
                    current_view = VIEW_MAIN_MENU
            elif menu_index == MENU_ITEM_SET_PASSWORD:
                current_view = VIEW_KEYBOARD_PASSWORD
                if not _keyboard_run(view_manager):
                    current_view = VIEW_MAIN_MENU
            elif menu_index == MENU_ITEM_SET_NAME:
                current_view = VIEW_KEYBOARD_NAME
                if not _keyboard_run(view_manager):
                    current_view = VIEW_MAIN_MENU
    elif current_view == VIEW_KEYBOARD_SUBJECT:
        if button == BUTTON_BACK or not _keyboard_run(view_manager):
            inp.reset()
            current_view = VIEW_MAIN_MENU
            keyboard_index = KEYBOARD_WAITING
            _menu_start(view_manager)
    elif current_view == VIEW_KEYBOARD_RECIPIENT:
        if button == BUTTON_BACK or not _keyboard_run(view_manager):
            inp.reset()
            current_view = VIEW_MAIN_MENU
            keyboard_index = KEYBOARD_WAITING
            _menu_start(view_manager)
    elif current_view == VIEW_SENDING_MESSAGE:
        if button == BUTTON_BACK:
            inp.reset()
            current_view = VIEW_MAIN_MENU
            sending_index = SENDING_WAITING
            _menu_start(view_manager)
        elif sending_index == SENDING_KEYBOARD:
            if not _keyboard_run(view_manager):
                current_view = VIEW_MAIN_MENU
                sending_index = SENDING_WAITING
                _menu_start(view_manager)
        elif sending_index == SENDING_SENDING:
            __await_send(view_manager)
    elif current_view == VIEW_EMAIL_LIST:
        _email_list_run(view_manager)
    elif current_view == VIEW_EMAIL_VIEW:
        _email_view_run(view_manager)
    elif current_view in (
        VIEW_KEYBOARD_EMAIL,
        VIEW_KEYBOARD_PASSWORD,
        VIEW_KEYBOARD_NAME,
    ):
        if button == BUTTON_BACK or not _keyboard_run(view_manager):
            inp.reset()
            current_view = VIEW_MAIN_MENU
            keyboard_index = KEYBOARD_WAITING
            _menu_start(view_manager)


def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from gc import collect

    global smtp, _menu, _loading, _imap
    global _email_list, _email_textbox, _unread_emails, _current_email
    if smtp is not None:
        smtp.close()
        del smtp
        smtp = None

    del _menu
    _menu = None
    del _loading
    _loading = None

    if _imap is not None:
        _imap.close()
        del _imap
        _imap = None
    _email_list = None
    _email_textbox = None
    _unread_emails = []
    _current_email = None

    view_manager.keyboard.reset()
    collect()
