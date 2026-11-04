# picoware Gopher protocol browser
# ----------------------------------------------------
# A Picoware app that browses Gopher servers (menus and
# text files).  Copy to picoware/apps/ as gbrowser.mpy
# (or gbrowser.py) and launch from the App Store.
#
# Controls (menu mode):
#   UP / DOWN ........ walk the gopher items, one item per press
#   RIGHT / CENTER ... open the selected item
#   G ................ type a gopher URL and go straight to it
#   P ................ jump to the next menu (type 1) item
#   BACK / LEFT ...... go to previous menu / exit
#   F1 ............... show the help page (all keys)
#
# Controls (text mode):
#   UP / DOWN ........ scroll the text by one line
#   F4 / F5 .......... page up / page down
#   F2 / F3 .......... go to the start / end of the document
#   P ................ jump to the next menu link line
#   G ................ type a gopher URL and go straight to it
#   BACK / LEFT ...... back to the menu you came from
#   F1 ............... show the help page (all keys)
#
# Function keys are used instead of CTRL+arrow, HOME and END
# because the PicoCalc firmware eats those: HOME pops the whole
# app and the CTRL+arrow codes are never delivered.
#
# Type 7 (search) items open the keyboard for a query and the
# query is sent with the item selector, like gopher.py does.
#
# The menu is drawn by hand: every row uses the full screen
# width, starts at the very first column (no leading blank)
# and the list is only ever scrolled by whole items, so the
# arrow pad always lands on a gopher item.  There is no text
# label in front of a row, the colour of the line is the
# item type instead (see TYPE_COLORS).  The top line always
# shows the current URL.
#
# Note: on the PicoCalc, WiFi is DISABLED while the
# "LVGL mode" setting is on.  Turn that setting OFF
# in Picoware Settings if the app reports no WiFi.

import socket
import gc

from picoware.gui.textbox import TextBox
from picoware.system.settings import Settings
from picoware.system.vector import Vector
from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_LEFT,
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_RIGHT,
    BUTTON_CENTER,
    BUTTON_G,
    BUTTON_P,
    BUTTON_F1,
    BUTTON_F2,
    BUTTON_F3,
    BUTTON_F4,
    BUTTON_F5,
)
from picoware.system.colors import (
    TFT_WHITE,
    TFT_BLUE,
    TFT_GREEN,
    TFT_CYAN,
    TFT_RED,
    TFT_ORANGE,
    TFT_MAGENTA,
    TFT_LIGHTGREY,
    TFT_DARKGREY,
)

DEFAULT_HOST = "gopher.black"
DEFAULT_PORT = 70
TITLE_BAND = 24          # pixels reserved for the title at the top
HINT_TEXT = "G = URL   F1 = help"

# Key list shown by the F1 help page.
HELP_LINES = (
    "Gopher Browser - keys",
    "",
    "MENU",
    "  UP / DOWN   move selection",
    "  RIGHT / OK  open item",
    "  G           go to a URL",
    "  P           next menu item",
    "  BACK / LEFT previous menu / exit",
    "",
    "TEXT",
    "  UP / DOWN   scroll one line",
    "  F4 / F5     page up / page down",
    "  F2 / F3     top / bottom",
    "  P           next menu link",
    "  G           go to a URL",
    "  BACK / LEFT back to the menu",
    "",
    "F1            show this help",
)

TYPE_TEXT = "0"
TYPE_MENU = "1"
TYPE_ERROR = "3"
TYPE_SEARCH = "7"
TYPE_TELNET = "8"
TYPE_HTML = "h"
TYPE_INFO = "i"

# The label of a row is the gopher display string only, so the
# item type is told by the colour of the line instead.
TYPE_COLORS = {
    TYPE_TEXT:   TFT_BLUE,      # text file
    TYPE_MENU:   TFT_GREEN,     # menu / directory
    TYPE_ERROR:  TFT_RED,       # server error
    TYPE_SEARCH: TFT_MAGENTA,   # search
    TYPE_TELNET: TFT_ORANGE,    # telnet session
    TYPE_HTML:   TFT_CYAN,      # html document
    TYPE_INFO:   TFT_LIGHTGREY, # informational line
}
ITEM_COLOR = TFT_DARKGREY     # binary and anything unknown

# Type characters a gopher menu (or an embedded link line
# inside a text document) can start with.
MENU_TYPES = "0123456789gGhHiIs"


def _decode(raw):
    return raw.decode("utf-8", "ignore")


# ------------------------------------------------------------------
# Network helpers
# ------------------------------------------------------------------
class _Reader:
    """Buffered line reader over a MicroPython socket."""

    def __init__(self, sock):
        self._sock = sock
        self._buf = b""

    def readline(self):
        while True:
            i = self._buf.find(b"\n")
            if i >= 0:
                line = self._buf[: i + 1]
                self._buf = self._buf[i + 1:]
                return line
            chunk = self._sock.recv(256)
            if not chunk:
                if self._buf:
                    line = self._buf
                    self._buf = b""
                    return line
                return None
            self._buf += chunk


def _fetch_lines(host, port, selector):
    """Run one Gopher transaction.

    Returns (lines, None) on success, (None, error_message) on failure.
    """
    try:
        ai = socket.getaddrinfo(host, port)[0]
    except Exception as e:
        return None, "cannot resolve %s: %s" % (host, e)
    s = socket.socket(ai[0], socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect(ai[4])
        s.sendall((selector + "\r\n").encode("utf-8"))
        lines = []
        r = _Reader(s)
        while True:
            raw = r.readline()
            if raw is None:
                break
            if raw.strip(b"\r\n") == b".":
                break
            lines.append(raw)
        return lines, None
    except Exception as e:
        return None, "cannot talk to %s:%d: %s" % (host, port, e)
    finally:
        s.close()


def _parse_menu(lines):
    """Parse Gopher menu lines into (display, selector, host, port, type)."""
    items = []
    for raw in lines:
        text = _decode(raw).strip("\r\n")
        if not text:
            continue
        itype = text[0]
        fields = text[1:].split("\t")
        display = fields[0] if fields else ""
        selector = fields[1] if len(fields) > 1 else ""
        host = fields[2] if len(fields) > 2 else ""
        port = fields[3] if len(fields) > 3 else ""
        try:
            port = int(port)
        except ValueError:
            port = DEFAULT_PORT
        items.append((display, selector, host, port, itype))
    return items


def _parse_text(lines):
    """Turn raw Gopher file lines into display text (drop the tag line)."""
    body = lines[:-1] if len(lines) > 1 else lines
    return "\n".join(_decode(r).strip("\r\n") for r in body)


def _parse_url(url):
    """Split a gopher URL into (host, port, selector).

    Accepts "gopher://host:port/selector" and the short
    "host[:port][/selector]" form.  Returns (None, message) when
    the URL cannot be read.
    """
    text = url.strip()
    lowered = text.lower()
    for scheme in ("gopher://", "gopher:", "//"):
        if lowered.startswith(scheme):
            text = text[len(scheme):]
            break
    if not text:
        return None, "no host given"

    if "/" in text:
        hostpart, sel = text.split("/", 1)
        sel = "/" + sel
    else:
        hostpart, sel = text, ""

    port = DEFAULT_PORT
    if ":" in hostpart:
        hostpart, port_text = hostpart.rsplit(":", 1)
        try:
            port = int(port_text)
        except ValueError:
            return None, "port must be a number, got %r" % (port_text,)

    host = hostpart.strip()
    if not host:
        return None, "no host given"
    if not 0 < port < 65536:
        return None, "port out of range: %d" % (port,)
    return (host, port, sel), None


def _looks_like_menu(lines):
    """Tell a menu listing from a text file body."""
    for raw in lines:
        text = _decode(raw).strip("\r\n")
        if not text:
            continue
        if "\t" in text and text[0] in MENU_TYPES:
            return True
    return False


def _looks_like_menu_link(line):
    """An embedded gopher MENU link (type 1) inside a text document."""
    if not line:
        return False
    if line[0] != TYPE_MENU:
        return False
    return "\t" in line


# ------------------------------------------------------------------
# Text layout helpers
# ------------------------------------------------------------------
def _build_wrap(text, cpl):
    """Replicate the textbox native word wrapper.

    The native TextBox wraps text into lines of at most `cpl`
    characters, breaking at word boundaries.  This copies that
    algorithm so Python code can map a character offset back to a
    wrapped-line number (used to place the viewport on a link).

    Returns (wrapped, phys, links):
        wrapped[i] ... the char offset where wrapped line i begins
        phys[k]    ... the char offset where physical line k begins
        links      ... sorted (wrapped_index, offset) pairs for the
                       physical lines that look like gopher links
    """
    wrapped = []
    phys = [0]
    links = []
    str_len = len(text)
    i = 0
    line_start = 0
    line_length = 0
    p_start = 0
    p_wrapped = 0

    while i < str_len:
        c = text[i]

        if c == "\n":
            if _looks_like_menu_link(text[p_start:i]):
                links.append((p_wrapped, p_start))
            wrapped.append(line_start)
            i += 1
            while i < str_len and text[i] == " ":
                i += 1
            line_start = i
            line_length = 0
            p_start = line_start
            p_wrapped = len(wrapped)
            phys.append(p_start)
            continue

        if line_length == 0:
            while i < str_len and text[i] == " ":
                i += 1
            line_start = i

        word_start = i
        sp = text.find(" ", i)
        nl = text.find("\n", i)
        if sp == -1 and nl == -1:
            word_end = str_len
        elif sp == -1:
            word_end = nl
        elif nl == -1:
            word_end = sp
        else:
            word_end = sp if sp < nl else nl
        word_len = word_end - word_start

        if line_length + word_len > cpl and line_length > 0:
            wrapped.append(line_start)
            line_start = word_start
            line_length = 0

        if word_len > cpl:
            while word_len > 0:
                space = cpl - line_length
                if space == 0:
                    wrapped.append(line_start)
                    line_start = word_start
                    line_length = 0
                    space = cpl
                take = word_len if word_len < space else space
                line_length += take
                word_start += take
                word_len -= take
            i = word_end
        else:
            line_length += word_len
            i = word_end

        if i < str_len and text[i] == " ":
            line_length += 1
            i += 1

    if line_length > 0 or len(wrapped) == 0 or (
        str_len > 0 and text[str_len - 1] == "\n"
    ):
        wrapped.append(line_start)
        if line_length > 0 and _looks_like_menu_link(text[p_start:]):
            links.append((p_wrapped, p_start))

    return wrapped, phys, links


# ------------------------------------------------------------------
# Browser
# ------------------------------------------------------------------
class GopherBrowser:
    def __init__(self, vm):
        self.vm = vm
        self.draw = vm.draw
        self.fg = vm.foreground_color
        self.bg = vm.background_color
        self.sel = vm.selected_color

        self.mode = "menu"          # "menu", "text" or "input"
        self.title = ""

        self.host = DEFAULT_HOST
        self.port = DEFAULT_PORT
        self.sel_path = ""

        self.menu = None            # current list of parsed items
        self.selected = 0
        self.top = 0                # index of the first drawn item
        self.stack = []             # (host, port, selector, title, items, selected)

        self._textbox = None
        self._keyboard = None
        self._input_kind = "url"
        self._return_mode = "menu"
        self._help_return = "menu"
        self._search_target = (DEFAULT_HOST, DEFAULT_PORT, "")
        self._search_display = ""
        self.last_query = ""

        draw = self.draw
        cell_w = max(1, draw.font_size.x)
        cell_h = max(1, draw.font_size.y)
        self._cols = max(8, draw.size.x // cell_w)   # characters per line
        self._cpl = max(1, int(draw.size.x // cell_w) - 1)
        self._cell_h = cell_h
        self._row_h = cell_h + 2                     # one gopher item per row
        self._row_pad = (self._row_h - cell_h) // 2
        # the last row of the screen is kept for the help line
        self._rows = max(
            1, (draw.size.y - TITLE_BAND - self._row_h) // self._row_h
        )
        self._title_y = (TITLE_BAND - cell_h) // 2

    # ---- drawing -------------------------------------------------
    def _current_url(self):
        """Full gopher URL of the place we are at."""
        url = "gopher://" + self.host
        if self.port != DEFAULT_PORT:
            url += ":" + str(self.port)
        return url + self.sel_path

    def _display_url(self):
        # a search query rides in the selector as "\tquery"
        return self._current_url().replace("\t", " ")

    def _item_label(self, item):
        """The row text: the gopher display string, nothing else."""
        display = item[0].rstrip()
        if len(display) > self._cols:
            display = display[: self._cols]
        return display

    def _item_color(self, item):
        return TYPE_COLORS.get(item[4], ITEM_COLOR)

    def _draw_title(self):
        draw = self.draw
        draw.fill_rectangle(Vector(0, 0), Vector(draw.size.x, TITLE_BAND), self.bg)
        url = self._display_url()
        if self.mode == "menu" and self.menu:
            counter = "%d/%d" % (self.selected + 1, len(self.menu))
            room = self._cols - len(counter) - 1
            if len(url) > room:
                url = url[:room]
            draw.text(Vector(0, self._title_y), url, self.fg)
            draw.text(
                Vector((self._cols - len(counter)) * draw.font_size.x, self._title_y),
                counter,
                self.fg,
            )
        else:
            draw.text(Vector(0, self._title_y), url[: self._cols], self.fg)

    def _draw_hint(self):
        """Small help line in the row kept free under the last item."""
        draw = self.draw
        y = TITLE_BAND + self._rows * self._row_h
        space = draw.size.y - y
        if space < self._cell_h:
            return
        draw.fill_rectangle(Vector(0, y), Vector(draw.size.x, space), self.bg)
        draw.text(
            Vector(0, y + (space - self._cell_h) // 2),
            HINT_TEXT[: self._cols],
            ITEM_COLOR,
        )

    def _draw_row(self, index):
        """Draw a single menu row, highlight bar included."""
        draw = self.draw
        y = TITLE_BAND + (index - self.top) * self._row_h
        if y < TITLE_BAND or y + self._row_h > draw.size.y:
            return
        item = self.menu[index]
        selected = index == self.selected
        color = self.sel if selected else self.bg
        draw.fill_rectangle(Vector(0, y), Vector(draw.size.x, self._row_h), color)
        draw.text(
            Vector(0, y + self._row_pad),
            self._item_label(item),
            self.fg if selected else self._item_color(item),
        )

    def _draw_menu(self):
        draw = self.draw
        draw.fill_rectangle(Vector(0, 0), Vector(draw.size.x, draw.size.y), self.bg)
        self._draw_title()
        last = min(len(self.menu), self.top + self._rows)
        for index in range(self.top, last):
            self._draw_row(index)
        self._draw_hint()
        draw.swap()

    def _show_menu(self, title, items, selected=0):
        self.title = title
        self.menu = items
        self.mode = "menu"

        if not items or not (0 <= selected < len(items)):
            selected = 0
        self.selected = selected
        self._sync_top()
        self._draw_menu()

    def _show_text(self, title, text):
        self.title = title
        self.mode = "text"

        draw = self.draw
        draw.fill_rectangle(Vector(0, 0), Vector(draw.size.x, draw.size.y), self.bg)
        self._draw_title()

        if self._textbox is None:
            self._textbox = TextBox(
                draw,
                TITLE_BAND,
                draw.size.y - TITLE_BAND,
                self.fg,
                self.bg,
            )
        self._textbox.clear()
        self._textbox.set_text(text)
        self._textbox.jump_to_top()
        draw.swap()

    # ---- selection ------------------------------------------------
    def _sync_top(self):
        """Scroll the window by whole items so the selection stays visible."""
        count = len(self.menu)
        if count <= self._rows:
            self.top = 0
            return
        if self.selected < self.top:
            self.top = self.selected
        elif self.selected >= self.top + self._rows:
            self.top = self.selected - self._rows + 1
        if self.top > count - self._rows:
            self.top = count - self._rows
        if self.top < 0:
            self.top = 0

    def _select(self, index):
        """Move the selection by one gopher item and redraw what changed."""
        if not self.menu:
            return
        if index < 0:
            index = 0
        elif index > len(self.menu) - 1:
            index = len(self.menu) - 1
        previous = self.selected
        previous_top = self.top
        self.selected = index
        self._sync_top()

        if self.top != previous_top:
            self._draw_menu()
            return
        self._draw_row(previous)
        self._draw_row(self.selected)
        self._draw_title()
        self.draw.swap()

    def _select_next_menu(self):
        """Move the selection to the next navigable menu (type 1) item."""
        if not self.menu:
            return
        for index in range(self.selected + 1, len(self.menu)):
            if self.menu[index][4] == TYPE_MENU or self.menu[index][4] == TYPE_TEXT or self.menu[index][4] == TYPE_SEARCH or self.menu[index][4] == "2":
                self._select(index)
                return

    # ---- navigation ----------------------------------------------
    def _push_frame(self):
        self.stack.append(
            (self.host, self.port, self.sel_path, self.title, self.menu, self.selected)
        )
        self.selected = 0
        self.top = 0

    def _pop_frame(self):
        if not self.stack:
            return False
        self.host, self.port, self.sel_path, self.title, self.menu, self.selected = (
            self.stack.pop()
        )
        self.top = 0
        self._sync_top()
        return True

    def _open(self, idx):
        if self.menu is None or not (0 <= idx < len(self.menu)):
            return
        display, selector, host, port, itype = self.menu[idx]
        host = host or self.host
        port = int(port or DEFAULT_PORT)

        if itype in (TYPE_TEXT, TYPE_HTML):
            lines, err = _fetch_lines(host, port, selector)
            if lines is None:
                self._show_text(display, "Error: " + err)
            else:
                self._show_text(display, _parse_text(lines))
        elif itype == TYPE_MENU:
            lines, err = _fetch_lines(host, port, selector)
            if lines is None:
                self._show_text(display, "Error: " + err)
            else:
                self._push_frame()
                self.host, self.port, self.sel_path = host, port, selector
                self._show_menu(display, _parse_menu(lines))
        elif itype == TYPE_SEARCH:
            self._search_target = (host, port, selector)
            self._search_display = display
            self._prompt_search()
        elif itype == TYPE_TELNET:
            self._show_text(
                display,
                "Telnet session: %s:%d\n\n(Not available in this app.)" % (host, port),
            )
        elif itype == TYPE_ERROR:
            self._show_text(display, "The server returned an error item.")
        elif itype == TYPE_INFO:
            self._show_text(display, "(informational text)")
        else:
            self._show_text(display, "Unsupported Gopher item type %r" % itype)
        gc.collect()

    def _leave_text(self):
        self.mode = "menu"
        if self.menu is None:
            self.vm.back()
        else:
            self._draw_menu()

    # ---- help page ------------------------------------------------
    def _show_help(self):
        """Overlay the key list without touching the page underneath."""
        self._help_return = self.mode
        self.mode = "help"
        self._draw_help()
        self.draw.swap()

    def _draw_help(self):
        draw = self.draw
        draw.fill_rectangle(Vector(0, 0), Vector(draw.size.x, draw.size.y), self.bg)
        self._draw_title()
        y = TITLE_BAND + self._row_pad
        for line in HELP_LINES:
            draw.text(Vector(0, y), line[: self._cols], self.fg)
            y += self._row_h

    def _leave_help(self):
        """Return to the menu or text page the help was drawn over."""
        if self._help_return == "text" and self._textbox is not None:
            self.mode = "text"
            self._draw_title()
            self._textbox.refresh()
            self.draw.swap()
        elif self.menu is not None:
            self.mode = "menu"
            self._draw_menu()
        else:
            self.mode = "menu"
            self.vm.back()

    # ---- text document navigation ---------------------------------
    def _text_page(self, direction):
        """Scroll the text viewport by one screen (direction: -1 / +1)."""
        tb = self._textbox
        if tb is None:
            return
        try:
            total = tb.total_lines
            lps = tb.lines_per_screen
            cur = tb.current_line
        except Exception:
            return
        if total <= 1 or lps < 1:
            return
        first = max(0, cur + 1 - lps)
        if direction < 0:
            target_first = max(0, first - lps)
        else:
            target_first = first + lps
            if target_first + lps > total:
                target_first = max(0, total - lps)
        new = target_first + lps - 1
        if new < 0:
            new = 0
        if new > total - 1:
            new = total - 1
        if new != cur:
            tb.set_current_line(new)

    def _text_to_top(self):
        tb = self._textbox
        if tb is None:
            return
        try:
            tb.set_current_line(0)
        except Exception:
            pass

    def _text_to_bottom(self):
        tb = self._textbox
        if tb is None:
            return
        try:
            total = tb.total_lines
            if total > 0:
                tb.set_current_line(total - 1)
        except Exception:
            pass

    def _text_next_link(self):
        """Move the text viewport so the next menu link line is on top."""
        tb = self._textbox
        if tb is None:
            return
        try:
            total = tb.total_lines
            lps = tb.lines_per_screen
            cur = tb.current_line
            text = tb.current_text
        except Exception:
            return
        if total <= 1 or lps < 1:
            return
        cpl = self._cpl
        if text and len(text) > cpl * total + cpl:
            # the text is far too large to analyse again each press
            return
        wrapped, phys, links = _build_wrap(text, cpl)
        if not links:
            return
        top = max(0, cur + 1 - lps)
        if top >= len(wrapped):
            top = max(0, len(wrapped) - 1)
        top_offset = wrapped[top] if wrapped else 0
        owner = 0
        for o in phys:
            if o <= top_offset:
                owner = o
            else:
                break
        target = None
        for wi, off in links:
            if off > owner:
                target = wi
                break
        if target is None:
            return
        new = target + lps - 1
        if new < 0:
            new = 0
        if new > total - 1:
            new = total - 1
        if new != cur:
            tb.set_current_line(new)

    # ---- gopher url / search keyboard -----------------------------
    def _begin_keyboard(self, title, initial, kind):
        """Open the keyboard; kind is "url" or "search"."""
        kb = self.vm.keyboard
        kb.reset()
        kb.title = title
        kb.response = initial
        self._keyboard = kb
        self._input_kind = kind
        self._return_mode = self.mode
        self.mode = "input"

    def _prompt_url(self):
        self._begin_keyboard("Enter Gopher URL", self._display_url(), "url")

    def _prompt_search(self):
        self._begin_keyboard(
            "Search " + self._search_display, self.last_query, "search"
        )

    def _run_keyboard(self):
        """Drive the keyboard until it is saved or cancelled."""
        kb = self._keyboard
        if kb is None:
            self._restore_view()
            return
        if not kb.run(force=True):
            kb.reset()
            self._keyboard = None
            self._restore_view()
            return
        if kb.is_finished:
            value = kb.response
            kb.reset()
            self._keyboard = None
            self._restore_view()
            if self._input_kind == "search":
                self._do_search(value)
            else:
                self._goto_url(value)

    def _restore_view(self):
        """Paint the screen the keyboard was sitting on top of."""
        if self._return_mode == "text" and self._textbox is not None:
            self.mode = "text"
            self._draw_title()
            self._textbox.refresh()
            self.draw.swap()
        elif self.menu is not None:
            self.mode = "menu"
            self._draw_menu()
        else:
            self.mode = "text"
            self._show_text(self.title, "No page to go back to.")

    def _goto_url(self, url):
        """Jump straight to a gopher URL typed by the user."""
        target, err = _parse_url(url)
        if err is not None:
            self._show_text("Go to URL", "Cannot read\n%s\n\n%s" % (url.strip(), err))
            return
        host, port, selector = target

        lines, err = _fetch_lines(host, port, selector)
        if lines is None:
            self._show_text(host, "Error: " + err)
            return

        self.stack = []
        self.host, self.port, self.sel_path = host, port, selector
        self.selected = 0
        self.top = 0
        if _looks_like_menu(lines):
            self._show_menu(selector or host, _parse_menu(lines))
        else:
            self._show_text(selector or host, _parse_text(lines))
        gc.collect()

    def _do_search(self, query):
        """Run a type 7 search and show the results as a menu."""
        query = query.strip()
        host, port, selector = self._search_target
        if not query:
            self._show_text(self._search_display, "Search needs a query.")
            return
        self.last_query = query

        lines, err = _fetch_lines(host, port, selector + "\t" + query)
        if lines is None:
            self._show_text(self._search_display, "Error: " + err)
            return

        self._push_frame()
        self.host, self.port, self.sel_path = host, port, selector + "\t" + query
        self._show_menu(self._search_display, _parse_menu(lines))
        gc.collect()

    # ---- lifecycle hooks -----------------------------------------
    def start(self):
        ok, message = self._wifi_ready()
        if not ok:
            self._show_text("Gopher Browser", message + "\n\n(BACK to exit)")
            return True
        lines, err = _fetch_lines(DEFAULT_HOST, DEFAULT_PORT, "")
        if lines is None:
            self._show_text("Gopher Browser", "Could not load %s\n\n%s" % (DEFAULT_HOST, err))
            return True
        self._show_menu(DEFAULT_HOST, _parse_menu(lines))
        return True

    def run(self):
        button = self.vm.button
        if self.mode == "input":
            self._run_keyboard()
            return

        if self.mode == "help":
            if button in (BUTTON_BACK, BUTTON_LEFT, BUTTON_F1):
                self._leave_help()
            return

        if button == BUTTON_F1:
            self._show_help()
            return

        if button in (BUTTON_BACK, BUTTON_LEFT):
            if self.mode == "text":
                self._leave_text()
            elif not self._pop_frame():
                self.vm.back()
            else:
                self._draw_menu()
            return

        if self.mode == "text":
            if self._textbox is None:
                return
            if button == BUTTON_F4:
                self._text_page(-1)
            elif button == BUTTON_F5:
                self._text_page(1)
            elif button == BUTTON_F2:
                self._text_to_top()
            elif button == BUTTON_F3:
                self._text_to_bottom()
            elif button == BUTTON_P:
                self._text_next_link()
            elif button == BUTTON_G:
                self._prompt_url()
            elif button == BUTTON_UP:
                self._textbox.scroll_up()
            elif button == BUTTON_DOWN:
                self._textbox.scroll_down()
            return

        # menu mode: the arrow pad walks the gopher items, never the lines
        if button == BUTTON_G:
            self._prompt_url()
        elif button == BUTTON_P:
            self._select_next_menu()
        elif button == BUTTON_UP:
            self._select(self.selected - 1)
        elif button == BUTTON_DOWN:
            self._select(self.selected + 1)
        elif button in (BUTTON_RIGHT, BUTTON_CENTER):
            self._open(self.selected)

    def stop(self):
        self._textbox = None
        self._keyboard = None
        self.menu = None
        self.selected = 0
        self.top = 0
        gc.collect()

    # ---- wifi ----------------------------------------------------
    def _wifi_ready(self):
        w = self.vm.wifi
        if w is None:
            st = Settings(self.vm.storage)
            if st.lvgl_mode:
                return False, (
                    "WiFi is disabled in LVGL mode.\n\n"
                    "Open Picoware Settings, turn OFF\n"
                    "LVGL mode, then reopen Gopher."
                )
            return False, (
                "This device has no WiFi radio,\n"
                "so Gopher browsing is not possible."
            )
        if w.is_connected():
            return True, ""
        creds = Settings(self.vm.storage).wifi_settings
        ssid = creds.get("ssid", "")
        if not ssid:
            return False, (
                "WiFi is not connected.\n\n"
                "Open Picoware Settings -> WiFi,\n"
                "join a network, then reopen Gopher."
            )
        w.timeout = 5
        if w.connect(ssid, creds.get("password", "")):
            return True, ""
        return False, "Could not connect to WiFi: %s" % (w.last_error or "unknown error")


# ------------------------------------------------------------------
# Picoware hooks
# ------------------------------------------------------------------
def start(view_manager):
    view_manager.browser = GopherBrowser(view_manager)
    return view_manager.browser.start()


def run(view_manager):
    view_manager.browser.run()


def stop(view_manager):
    view_manager.browser.stop()