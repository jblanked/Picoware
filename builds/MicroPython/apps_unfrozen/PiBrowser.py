"""
PiBrowse — text-only browser for PicoCalc / Picoware.

Copy to:
    /sd/picoware/apps/pibrowse.py
"""

from gc import collect
from picoware.system.buttons import (
    BUTTON_BACK,
    BUTTON_CENTER,
    BUTTON_DOWN,
    BUTTON_F6,
    BUTTON_F7,
    BUTTON_F8,
    BUTTON_F9,
    BUTTON_F10,
    BUTTON_LEFT,
    BUTTON_NONE,
    BUTTON_RIGHT,
    BUTTON_UP,
)
from picoware.system.colors import TFT_WHITE
from picoware.system.font import FONT_SMALL
from picoware.system.http import HTTP
from picoware.system.vector import Vector
from picoware.gui.keyboard import Keyboard

APP = "PiBrowse"
CACHE_DIR = "pibrowse"
CACHE_HTML = "pibrowse/page.html"
CACHE_TXT = "pibrowse/page.txt"
CACHE_LNK = "pibrowse/page.lnk"
CACHE_META = "pibrowse/page.meta"
HIST_MAX = 6

MAX_HTML = 32 * 1024
MAX_TXT = 8 * 1024
MAX_LINKS = 24
MAX_LINES = 160
CHUNK = 256
WRAP = 38
ROWS = 15
Y_LIST = 20
ROW_H = 18
STAT1_Y = 288
STAT2_Y = 304
BAR_X = 318

HEADERS = {
    "User-Agent": "Lynx/2.9.2 libwww-FM/2.14",
    "Accept": "text/html,text/plain;q=0.9,*/*;q=0.1",
    "Accept-Encoding": "identity",
    "Accept-Language": "en-US,en;q=0.8",
}

HOME = 0
DIR = 1
KEYS = 2
LOAD = 3
PAGE = 4
LINKS = 5

DIRECTORY = (
    ("CERN 1991 first site", "https://info.cern.ch/"),
    ("Textfiles BBS archive", "https://www.textfiles.com/"),
    ("FrogFind search", "https://frogfind.com/"),
    ("Wiby old-web search", "https://wiby.me/"),
    ("68k News", "https://68k.news/"),
    ("NPR text", "https://text.npr.org/"),
    ("CNN Lite", "https://lite.cnn.com/"),
    ("Simple Wikipedia", "https://simple.wikipedia.org/wiki/Main_Page"),
    ("Jargon File", "https://www.catb.org/jargon/html/index.html"),
    ("Gopher gateway", "https://gopher.floodgap.com/gopher/"),
    ("RFC 791", "https://www.rfc-editor.org/rfc/rfc791.txt"),
    ("Weather (text)", "https://wttr.in/?T"),
    ("example.com", "https://example.com/"),
)

SKIP = {
    "script",
    "noscript",
    "svg",
    "iframe",
    "template",
    "canvas",
    "video",
    "audio",
    "source",
    "picture",
    "img",
    "embed",
    "object",
    "track",
    "map",
    "area",
}
IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".bmp", ".avif")
HIDE_MARKS = (
    "display:none",
    "display: none",
    "visibility:hidden",
    "visibility: hidden",
    "font-size:0",
    "font-size: 0",
)


def _css_is_hide(body):
    low = body.lower()
    for mark in HIDE_MARKS:
        if mark in low:
            return True
    return False


def _css_learn(text, hide_c, hide_i, hide_t):
    """Tiny CSS reader: only cares about rules that hide things."""
    if not text:
        return
    # drop /* comments */
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            if j < 0:
                break
            i = j + 2
            continue
        out.append(text[i])
        i += 1
    css = "".join(out)
    for block in css.split("}"):
        if "{" not in block:
            continue
        sel, body = block.split("{", 1)
        if not _css_is_hide(body):
            continue
        for part in sel.split(","):
            _css_sel(part, hide_c, hide_i, hide_t)


def _css_sel(sel, hide_c, hide_i, hide_t):
    sel = sel.strip()
    if not sel:
        return
    # "nav" or "footer" hides that tag. "div.ad" only hides class ad.
    bare = True
    i = 0
    n = len(sel)
    while i < n:
        ch = sel[i]
        if ch in ".#":
            bare = False
            kind = ch
            i += 1
            a = i
            while i < n and (sel[i].isalnum() or sel[i] in "-_"):
                i += 1
            name = sel[a:i].lower()
            if not name:
                continue
            if kind == ".":
                if name not in hide_c and len(hide_c) < 40:
                    hide_c.append(name)
            elif name not in hide_i and len(hide_i) < 24:
                hide_i.append(name)
        else:
            i += 1
    if bare and sel[0].isalpha():
        i = 0
        while i < n and (sel[i].isalnum() or sel[i] == "-"):
            i += 1
        name = sel[:i].lower()
        if name and name not in hide_t and len(hide_t) < 16:
            hide_t.append(name)


def _hidden_by_css(name, attrs, hide_c, hide_i, hide_t):
    if name in hide_t:
        return True
    style = (attrs.get("style") or "").lower()
    if style and _css_is_hide(style):
        return True
    hid = (attrs.get("hidden") or None)
    if hid is not None:
        return True
    aria = (attrs.get("aria-hidden") or "").lower()
    if aria == "true":
        return True
    eid = (attrs.get("id") or "").lower()
    if eid and eid in hide_i:
        return True
    klass = (attrs.get("class") or "").lower()
    if klass:
        for token in klass.split():
            if token in hide_c:
                return True
    return False
BLOCK = {
    "p",
    "div",
    "br",
    "tr",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "article",
    "section",
    "header",
    "footer",
    "blockquote",
    "pre",
    "ul",
    "ol",
    "table",
    "hr",
}
ENT = {
    "amp": "&",
    "lt": "<",
    "gt": ">",
    "quot": '"',
    "apos": "'",
    "nbsp": " ",
    "mdash": "-",
    "ndash": "-",
    "hellip": "...",
}

_state = HOME
_http = None
_kb = None
_key_mode = "url"
_key_back = HOME
_items = []
_sel = 0
_scroll = 0
_url = ""
_title = APP
_hist = []
_hslot = 0
_offs = []
_page = []
_links = 0
_fallback = 0
_last_err = ""
_rate_bps = 0
_got_bytes = 0


def start(vm) -> bool:
    global _http, _hist, _url, _title, _offs, _links, _hslot
    wifi = vm.wifi
    if not wifi:
        vm.alert("No Wi-Fi on this board.", False)
        return False
    if not wifi.is_connected():
        vm.alert("Connect Wi-Fi first.", False)
        return False
    try:
        if not vm.storage.exists(CACHE_DIR):
            vm.storage.mkdir(CACHE_DIR)
    except Exception:
        pass
    _http = None
    _hist = []
    _hslot = 0
    _url = ""
    _title = APP
    _offs = []
    globals()["_page"] = []
    _links = 0
    globals()["_fallback"] = 0
    _show_home(vm)
    return True


def run(vm) -> None:
    if _state == HOME:
        _run_list(vm, HOME)
    elif _state == DIR:
        _run_list(vm, DIR)
    elif _state == LINKS:
        _run_list(vm, LINKS)
    elif _state == KEYS:
        _run_keys(vm)
    elif _state == LOAD:
        _run_load(vm)
    elif _state == PAGE:
        _run_page(vm)


def stop(vm) -> None:
    global _http, _kb, _hist, _offs, _items, _url, _state
    _close_http()
    _kb = None
    _hist = []
    globals()["_hslot"] = 0
    _offs = []
    globals()["_page"] = []
    _items = []
    _url = ""
    _state = HOME
    collect()


def _close_http():
    global _http
    if _http:
        try:
            _http.close()
        except Exception:
            pass
        _http = None


def _fmt_kb(bps):
    if not bps or bps < 0:
        return "0.0"
    tenths = int(bps / 100.0 + 0.5)  # bytes/s -> 0.1 KB/s
    if tenths > 999:
        tenths = 999
    return "%d.%d" % (tenths // 10, tenths % 10)


def _fmt_kb_total(n):
    if not n or n < 0:
        return "0.0"
    tenths = int(n / 100.0 + 0.5)
    if tenths > 9999:
        tenths = 9999
    return "%d.%d" % (tenths // 10, tenths % 10)


def _bar(vm, addr, row3, row4, foot=""):
    d = vm.draw
    fg = vm.foreground_color
    hi = vm.selected_color
    d.fill_rectangle(Vector(0, 0), Vector(320, 320), vm.background_color)
    # site bar — top
    d.fill_rectangle(Vector(0, 0), Vector(320, 18), hi)
    d.text(Vector(4, 3), _clip(addr or APP, 36), TFT_WHITE, FONT_SMALL)
    if _hist:
        d.text(Vector(304, 3), "<", TFT_WHITE, FONT_SMALL)
    # status bars — bottom
    d.fill_rectangle(Vector(0, STAT1_Y), Vector(320, 16), hi)
    d.text(Vector(4, STAT1_Y + 2), _clip(row3 or "", 38), TFT_WHITE, FONT_SMALL)
    d.fill_rectangle(Vector(0, STAT2_Y), Vector(320, 16), hi)
    line4 = row4 or ""
    if foot:
        if line4:
            line4 = _clip(line4, 16) + "  " + foot
        else:
            line4 = foot
    d.text(Vector(4, STAT2_Y + 2), _clip(line4, 38), TFT_WHITE, FONT_SMALL)


def _scrollbar(d, color, top, total, vis, y0, y1):
    h = y1 - y0
    if h < 8:
        return
    d.fill_rectangle(Vector(BAR_X, y0), Vector(2, h), TFT_WHITE)
    if total <= vis or total <= 1:
        d.fill_rectangle(Vector(BAR_X, y0), Vector(2, h), color)
        return
    thumb = h * vis // total
    if thumb < 6:
        thumb = 6
    if thumb > h:
        thumb = h
    span = total - vis
    if span < 1:
        span = 1
    pos = y0 + (h - thumb) * top // span
    if pos + thumb > y1:
        pos = y1 - thumb
    d.fill_rectangle(Vector(BAR_X, pos), Vector(2, thumb), color)


def _clip(s, n):
    s = s or ""
    if len(s) <= n:
        return s
    return s[: n - 1] + "~"


def _paint_list(vm, addr, foot):
    global _scroll
    n = len(_items)
    _bar(vm, addr, "%d/%d" % (_sel + 1 if n else 0, n), "", foot)
    d = vm.draw
    fg = vm.foreground_color
    hi = vm.selected_color
    n = len(_items)
    vis = ROWS
    top = _scroll
    if top > _sel:
        top = _sel
    if _sel >= top + vis:
        top = _sel - vis + 1
    if top < 0:
        top = 0
    _scroll = top
    y = Y_LIST
    i = top
    while i < n and i < top + vis:
        label = _clip(_items[i], 34)
        if i == _sel:
            d.fill_rectangle(Vector(2, y), Vector(316, ROW_H - 2), hi)
            d.text(Vector(8, y + 2), label, TFT_WHITE)
        else:
            d.text(Vector(8, y + 2), label, fg)
        y += ROW_H
        i += 1
    _scrollbar(d, hi, top, n, vis, Y_LIST, STAT1_Y - 2)
    d.swap()


def _paint_page(vm):
    total = _line_count() or 1
    row3 = "%d/%d   %d links" % (_scroll + 1, total, _links)
    row4 = "%s kb" % _fmt_kb(_rate_bps)
    _bar(vm, _url, row3, row4, "Up/Dn scroll   F10 links")
    d = vm.draw
    fg = vm.foreground_color
    y = Y_LIST
    for line in _read_lines(vm.storage, _scroll, ROWS):
        d.text(Vector(4, y), _clip(line, WRAP), fg, FONT_SMALL)
        y += 16
        if y >= STAT1_Y - 2:
            break
    _scrollbar(d, vm.selected_color, _scroll, total, ROWS, Y_LIST, STAT1_Y - 2)
    d.swap()


def _paint_load(vm, text):
    row3 = text or "Downloading"
    row4 = "%s kb   %s KB" % (_fmt_kb(_rate_bps), _fmt_kb_total(_got_bytes))
    _bar(vm, _url or "", row3, row4, "Back cancels")
    vm.draw.swap()


def _show_home(vm):
    global _state, _items, _sel, _scroll, _url
    _url = "about:home"
    _items = ["Address bar", "Search the web", "1990s directory", "Quit"]
    _sel = 0
    _scroll = 0
    _state = HOME
    _paint_list(vm, "about:home", "Enter open   Back quit")


def _show_dir(vm):
    global _state, _items, _sel, _scroll, _url
    _url = "about:directory"
    _items = [row[0] for row in DIRECTORY] + ["Back"]
    _sel = 0
    _scroll = 0
    _state = DIR
    _paint_list(vm, "about:directory", "Enter open   Back home")


def _show_links(vm):
    global _state, _items, _sel, _scroll
    labels = _link_labels(vm.storage)
    if not labels:
        _items = ["(no links)", "Back"]
    else:
        _items = []
        i = 0
        while i < len(labels):
            _items.append("%d. %s" % (i + 1, labels[i][:30]))
            i += 1
        _items.append("Back")
    _sel = 0
    _scroll = 0
    _state = LINKS
    _paint_list(vm, _url, "Enter follow   Back page")


def _run_list(vm, which):
    global _sel
    btn = vm.input_manager.button
    if btn == BUTTON_NONE:
        return
    vm.input_manager.reset()
    n = len(_items)
    if n == 0:
        return
    if btn == BUTTON_UP:
        if _sel > 0:
            _sel -= 1
            _paint_list(vm, _url, _foot_for(which))
    elif btn == BUTTON_DOWN:
        if _sel < n - 1:
            _sel += 1
            _paint_list(vm, _url, _foot_for(which))
    elif btn == BUTTON_CENTER:
        _activate(vm, which)
    elif btn == BUTTON_F6:
        starter = _url if (_url or "").startswith("http") else "https://"
        _open_kb(vm, "url", starter, which)
    elif btn == BUTTON_F7:
        _open_kb(vm, "search", "", which)
    elif btn in (BUTTON_BACK, BUTTON_LEFT):
        if which == HOME:
            vm.back()
        elif which == LINKS:
            _show_page(vm)
        else:
            _show_home(vm)


def _foot_for(which):
    if which == HOME:
        return "Enter open   Back quit"
    if which == DIR:
        return "Enter open   Back home"
    return "Enter follow   Back page"


def _activate(vm, which):
    if _sel < 0 or _sel >= len(_items):
        return
    name = _items[_sel]
    if which == HOME:
        if name == "Address bar":
            _open_kb(vm, "url", "https://", HOME)
        elif name == "Search the web":
            _open_kb(vm, "search", "", HOME)
        elif name == "1990s directory":
            _show_dir(vm)
        elif name == "Quit":
            vm.back()
        return
    if which == DIR:
        if name == "Back":
            _show_home(vm)
            return
        for label, url in DIRECTORY:
            if label == name:
                _go(vm, url)
                return
        return
    if name == "Back" or name == "(no links)":
        _show_page(vm)
        return
    url = _link_url(vm.storage, _sel)
    if url:
        _go(vm, url)
    else:
        _show_page(vm)


def _open_kb(vm, mode, starter, back):
    global _state, _kb, _key_mode, _key_back
    _key_mode = mode
    _key_back = back
    _kb = Keyboard(
        vm.draw,
        vm.input_manager,
        vm.foreground_color,
        vm.background_color,
        vm.selected_color,
    )
    _kb.title = "Address" if mode == "url" else "Search"
    _kb.reset()
    _kb.response = starter or ""
    _state = KEYS


def _run_keys(vm):
    global _kb
    if _kb is None:
        _kb_cancel(vm)
        return
    keep = _kb.run()
    if _kb.is_finished:
        text = (_kb.response or "").strip()
        _kb = None
        collect()
        if not text:
            _kb_cancel(vm)
            return
        if _key_mode == "search":
            _go(vm, "https://frogfind.com/?q=" + _enc(text))
        else:
            _go(vm, text)
        return
    if keep is False:
        _kb = None
        collect()
        _kb_cancel(vm)


def _kb_cancel(vm):
    if _key_back == PAGE and _page:
        _show_page(vm)
    elif _key_back == DIR:
        _show_dir(vm)
    elif _key_back == LINKS:
        _show_links(vm)
    else:
        _show_home(vm)


def _norm(raw):
    u = (raw or "").strip()
    if not u:
        return ""
    if " " in u and "://" not in u:
        return "https://frogfind.com/?q=" + _enc(u)
    if u.startswith("//"):
        u = "https:" + u
    if "://" not in u:
        u = "https://" + u
    return u


def _go(vm, raw, push=True):
    global _fallback
    url = _norm(raw)
    if not url:
        vm.alert("Empty address", False)
        _show_home(vm)
        return
    if push:
        _push_snap(vm.storage)
    _fallback = 0
    _start_fetch(vm, url)


def _frog_url(url):
    if "frogfind.com/read.php" in url:
        return url
    return "https://frogfind.com/read.php?a=" + url


def _start_fetch(vm, url):
    global _url, _title, _state, _http, _last_err
    _url = url
    _title = _host(url)
    _last_err = ""
    collect()
    st = vm.storage
    for path in (CACHE_HTML, CACHE_TXT, CACHE_LNK):
        try:
            if st.exists(path):
                st.remove(path)
        except Exception:
            pass
    _close_http()
    _http = HTTP(chunk_size=512, thread_manager=vm.thread_manager)
    _state = LOAD
    note = "Downloading..."
    if _fallback == 1:
        note = "Retry HTTP..."
    elif _fallback == 2:
        note = "Retry via FrogFind..."
    _paint_load(vm, note)
    ok = False
    try:
        ok = _http.get_async(
            url,
            headers=HEADERS,
            timeout=30,
            save_to_file=CACHE_HTML,
            storage=st,
        )
    except Exception as exc:
        _close_http()
        _last_err = str(exc)
        if not _try_fallback(vm):
            vm.alert("HTTP:\n%s" % exc, False)
            _show_home(vm)
        return
    if not ok:
        _close_http()
        _last_err = "Download did not start"
        if not _try_fallback(vm):
            vm.alert(_last_err, False)
            _show_home(vm)


def _file_has_text(st):
    try:
        if not st.exists(CACHE_HTML):
            return False
        sz = st.size(CACHE_HTML)
        return bool(sz and sz > 16)
    except Exception:
        try:
            raw = _read_at(st, CACHE_HTML, 0, 32)
            return bool(raw)
        except Exception:
            return False


def _try_fallback(vm):
    global _fallback
    url = _url or ""
    if "frogfind.com/read.php" in url:
        return False
    if _fallback == 0 and url.startswith("https://"):
        _fallback = 1
        _start_fetch(vm, "http://" + url[8:])
        return True
    if _fallback < 2:
        _fallback = 2
        orig = url
        if orig.startswith("http://"):
            orig = "https://" + orig[7:]
        _start_fetch(vm, _frog_url(orig))
        return True
    return False


def _pull_http_stats():
    global _rate_bps, _got_bytes
    if _http is None:
        return
    try:
        _rate_bps = int(_http.download_speed or 0)
    except Exception:
        pass
    try:
        _got_bytes = int(_http.downloaded_bytes or 0)
    except Exception:
        pass


def _run_load(vm):
    global _last_err
    btn = vm.input_manager.button
    if btn == BUTTON_BACK:
        vm.input_manager.reset()
        _close_http()
        _show_home(vm)
        return
    if _http is None or not _http.is_finished:
        _pull_http_stats()
        _paint_load(vm, "Downloading")
        return
    ok = False
    err = "Download failed"
    code = 0
    try:
        ok = bool(_http.is_successful)
        err = _http.error or err
        resp = _http.response
        if resp is not None:
            try:
                code = int(resp.status_code)
            except Exception:
                code = 0
            if 200 <= code < 400:
                ok = True
    except Exception:
        ok = False
    _pull_http_stats()
    _close_http()
    collect()
    saved = _file_has_text(vm.storage)
    if not ok and not saved:
        _last_err = err if not code else ("%s (%d)" % (err, code))
        if _try_fallback(vm):
            return
        vm.alert(_clip(str(_last_err), 90), False)
        _show_home(vm)
        return
    _paint_load(vm, "Extracting text...")
    try:
        _html_to_text(vm.storage, _url)
    except Exception as exc:
        vm.alert("Parse:\n%s" % exc, False)
        _show_home(vm)
        return
    collect()
    _show_page(vm)


def _show_page(vm):
    global _state, _scroll
    _scroll = 0
    _state = PAGE
    _paint_page(vm)


def _run_page(vm):
    global _scroll
    btn = vm.input_manager.button
    if btn == BUTTON_NONE:
        return
    vm.input_manager.reset()
    last = _line_count()
    max_top = last - 1
    if max_top < 0:
        max_top = 0
    if btn == BUTTON_UP:
        if _scroll > 0:
            _scroll -= 1
            if _scroll < 0:
                _scroll = 0
            _paint_page(vm)
    elif btn == BUTTON_DOWN:
        if _scroll < max_top:
            _scroll += 1
            _paint_page(vm)
    elif btn == BUTTON_LEFT:
        _back(vm)
    elif btn in (BUTTON_RIGHT, BUTTON_F10, BUTTON_CENTER):
        _show_links(vm)
    elif btn == BUTTON_F6:
        _open_kb(vm, "url", _url, PAGE)
    elif btn == BUTTON_F7:
        _open_kb(vm, "search", "", PAGE)
    elif btn == BUTTON_F8:
        _go(vm, _url, push=False)
    elif btn == BUTTON_F9:
        _show_home(vm)
    elif btn == BUTTON_BACK:
        _back(vm)


def _snap_paths(slot):
    return (
        "pibrowse/b%d.txt" % slot,
        "pibrowse/b%d.lnk" % slot,
        "pibrowse/b%d.meta" % slot,
    )


def _push_snap(st):
    global _hslot, _hist
    if not _page:
        return
    if not _url or not _url.startswith("http"):
        return
    slot = _hslot
    _hslot = (_hslot + 1) % HIST_MAX
    txt, lnk, meta = _snap_paths(slot)
    body = ""
    i = 0
    while i < len(_page):
        body += _page[i] + "\n"
        i += 1
    try:
        _write(st, txt, body, "w")
    except Exception:
        return
    blob = ""
    try:
        if st.exists(CACHE_LNK):
            raw = _read_at(st, CACHE_LNK, 0, 2500)
            blob = raw.decode("utf-8", "ignore")
    except Exception:
        blob = ""
    try:
        _write(st, lnk, blob, "w")
        _write(st, meta, (_title or APP) + "\n" + _url + "\n", "w")
    except Exception:
        pass
    _hist.append(slot)
    if len(_hist) > HIST_MAX:
        del _hist[0]
    collect()


def _load_snap(st, slot):
    global _url, _title, _page, _links
    txt, lnk, meta = _snap_paths(slot)
    try:
        if not st.exists(txt):
            return False
    except Exception:
        return False
    raw = _read_at(st, txt, 0, MAX_TXT + 200)
    if not raw:
        return False
    try:
        text = raw.decode("utf-8", "ignore")
    except Exception:
        text = raw.decode("latin-1")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        return False
    _page = lines
    title = APP
    url = ""
    try:
        if st.exists(meta):
            m = _read_at(st, meta, 0, 400).decode("utf-8", "ignore").split("\n")
            if m:
                title = m[0] or APP
            if len(m) > 1:
                url = m[1]
    except Exception:
        pass
    _title = title
    if url:
        _url = url
    try:
        if st.exists(lnk):
            data = _read_at(st, lnk, 0, 2500)
            try:
                _write(st, CACHE_LNK, data.decode("utf-8", "ignore"), "w")
            except Exception:
                pass
            n = 0
            for row in data.decode("utf-8", "ignore").split("\n"):
                if row:
                    n += 1
            _links = n
        else:
            _links = 0
            _write(st, CACHE_LNK, "", "w")
    except Exception:
        _links = 0
    collect()
    return True


def _back(vm):
    if _hist:
        slot = _hist.pop()
        if _load_snap(vm.storage, slot):
            _show_page(vm)
            return
    _show_home(vm)


def _write(st, path, data, mode="w"):
    st.write(path, data, mode=mode)


def _read_at(st, path, start, size):
    if size < 1:
        return b""
    data = None
    try:
        data = st.read(path, "b", start, size)
    except Exception:
        try:
            data = st.read_chunked(path, start, size)
        except Exception:
            data = b""
    if data is None:
        return b""
    if isinstance(data, str):
        return data.encode("utf-8")
    return data


def _line_count():
    if _page:
        return len(_page)
    n = len(_offs)
    if n <= 1:
        return 1 if n else 0
    return n - 1


def _read_lines(st, start, count):
    # SD offset-reads on this board keep returning byte 0, so the
    # visible page is kept in _page and we slice that for scroll.
    if _page:
        n = len(_page)
        if start >= n:
            return ["(empty)"]
        end = start + count
        if end > n:
            end = n
        return _page[start:end]
    return ["(empty)"]


def _link_labels(st):
    out = []
    try:
        if not st.exists(CACHE_LNK):
            return out
        raw = _read_at(st, CACHE_LNK, 0, 2000)
        for line in raw.decode("utf-8", "ignore").split("\n"):
            if not line:
                continue
            if "|" in line:
                out.append(line.split("|", 1)[1])
            else:
                out.append(line[:30])
            if len(out) >= MAX_LINKS:
                break
    except Exception:
        pass
    return out


def _link_url(st, index):
    try:
        if not st.exists(CACHE_LNK):
            return ""
        raw = _read_at(st, CACHE_LNK, 0, 2000)
        rows = [ln for ln in raw.decode("utf-8", "ignore").split("\n") if ln]
        if 0 <= index < len(rows):
            return rows[index].split("|", 1)[0]
    except Exception:
        pass
    return ""


def _html_bytes(st):
    """Read the downloaded page once. Never loop the same offset."""
    if not st.exists(CACHE_HTML):
        return b""
    n = MAX_HTML
    try:
        sz = st.size(CACHE_HTML)
        if sz and sz > 0:
            n = sz if sz < MAX_HTML else MAX_HTML
    except Exception:
        n = MAX_HTML
    return _read_at(st, CACHE_HTML, 0, n)


def _looks_html(raw):
    s = raw[:240].lower()
    return (
        b"<html" in s
        or b"<!doctype" in s
        or b"<head" in s
        or b"<body" in s
        or b"<p" in s
        or b"<a " in s
        or b"<h1" in s
    )


def _is_img_url(url):
    low = (url or "").lower().split("?", 1)[0]
    for ext in IMG_EXT:
        if low.endswith(ext):
            return True
    return False


def _save_page(st, title, lines, links, base):
    global _title, _offs, _links, _page
    _title = title or _host(base)
    _page = lines[:MAX_LINES]
    body = ""
    offs = [0]
    pos = 0
    i = 0
    while i < len(lines) and i < MAX_LINES:
        row = lines[i] + "\n"
        body += row
        try:
            pos += len(row.encode("utf-8"))
        except Exception:
            pos += len(row)
        offs.append(pos)
        i += 1
        if pos >= MAX_TXT:
            break
    _write(st, CACHE_TXT, body, "w")
    blob = ""
    for url, lab in links:
        blob += url + "|" + lab[:40] + "\n"
    _write(st, CACHE_LNK, blob, "w")
    _offs = offs
    _links = len(links)
    collect()


def _html_to_text(st, base):
    raw = _html_bytes(st)
    if not raw:
        _save_page(st, _host(base), ["(empty page)"], [], base)
        return
    if not _looks_html(raw):
        try:
            text = raw.decode("utf-8")
        except Exception:
            text = raw.decode("latin-1")
        lines = []
        for para in text.replace("\r", "").split("\n"):
            para = para.rstrip()
            if not para:
                if lines and lines[-1] != "":
                    lines.append("")
                continue
            while len(para) > WRAP:
                lines.append(para[:WRAP])
                para = para[WRAP:]
            lines.append(para)
        _save_page(st, _host(base), lines, [], base)
        del raw
        collect()
        return
    try:
        src = raw.decode("utf-8", "ignore")
    except Exception:
        src = raw.decode("latin-1")
    del raw
    collect()
    p = Parser(base)
    p.feed(src)
    p.finish()
    del src
    lines = []
    blank = 0
    for ln in p.lines:
        if ln == "":
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        lines.append(ln)
    _save_page(st, p.title, lines, p.links, base)
    del p
    collect()


class Parser:
    def __init__(self, base):
        self.base = base
        self.title = ""
        self.lines = []
        self.links = []
        self.full = False
        self.in_tag = False
        self.tag = []
        self.word = []
        self.line = []
        self.skip = None
        self.skip_d = 0
        self.in_title = False
        self.href = None
        self.atxt = []
        self.tbuf = []
        self.in_comment = False
        self.seen = []
        self.in_style = False
        self.sbuf = []
        self.hide_c = []
        self.hide_i = []
        self.hide_t = []

    def feed(self, data):
        i = 0
        n = len(data)
        while i < n and not self.full:
            ch = data[i]
            if self.in_comment:
                if data.startswith("-->", i):
                    self.in_comment = False
                    i += 3
                else:
                    i += 1
                continue
            if self.in_tag:
                if ch == ">":
                    raw = "".join(self.tag)
                    self.tag = []
                    self.in_tag = False
                    if raw.startswith("!--"):
                        if not raw.endswith("--"):
                            self.in_comment = True
                    else:
                        self._tag(raw)
                elif len(self.tag) < 300:
                    self.tag.append(ch)
                i += 1
                continue
            if ch == "<":
                self._flush()
                self.in_tag = True
                self.tag = []
                i += 1
                continue
            if self.skip:
                i += 1
                continue
            if self.in_style:
                if len(self.sbuf) < 3000:
                    self.sbuf.append(ch)
                i += 1
                continue
            if ch in " \t\r\n":
                if self.in_title and len(self.tbuf) < 80:
                    self.tbuf.append(" ")
                self._flush()
                if self.href is not None and len(self.atxt) < 40:
                    self.atxt.append(" ")
                i += 1
                continue
            if self.in_title:
                if len(self.tbuf) < 80:
                    self.tbuf.append(ch)
                i += 1
                continue
            self.word.append(ch)
            if self.href is not None and len(self.atxt) < 40:
                self.atxt.append(ch)
            i += 1

    def finish(self):
        self._flush()
        self._nl()

    def _tag(self, raw):
        raw = raw.strip()
        if not raw:
            return
        closing = raw.startswith("/")
        if closing:
            raw = raw[1:]
        name, attrs = _split(raw)
        if not name:
            return
        if self.skip:
            if name == self.skip:
                if closing:
                    self.skip_d -= 1
                    if self.skip_d <= 0:
                        self.skip = None
                        self.skip_d = 0
                else:
                    self.skip_d += 1
            return
        if name == "style":
            if closing:
                _css_learn("".join(self.sbuf), self.hide_c, self.hide_i, self.hide_t)
                self.sbuf = []
                self.in_style = False
            else:
                self.in_style = True
                self.sbuf = []
            return
        if not closing and _hidden_by_css(name, attrs, self.hide_c, self.hide_i, self.hide_t):
            if name not in ("img", "br", "hr", "input", "meta", "link"):
                self.skip = name
                self.skip_d = 1
            return
        if not closing and name in SKIP:
            # void image tags: drop them, do not capture alt/src
            if name not in ("img", "source", "track", "area"):
                self.skip = name
                self.skip_d = 1
            return
        if name == "title":
            if closing:
                t = _col("".join(self.tbuf))
                if t:
                    self.title = t[:60]
                self.tbuf = []
                self.word = []
                self.in_title = False
            else:
                self.in_title = True
                self.tbuf = []
            return
        if name in BLOCK:
            self._flush()
            self._nl()
            return
        if name != "a":
            return
        if closing:
            href = self.href
            lab = _col("".join(self.atxt))
            self.href = None
            self.atxt = []
            if href and len(self.links) < MAX_LINKS:
                absu = _join(self.base, href)
                if (
                    absu
                    and absu != self.base
                    and not _is_img_url(absu)
                    and absu not in self.seen
                ):
                    self.seen.append(absu)
                    self.links.append((absu, lab or absu))
                    self._add("[%d]" % len(self.links))
            return
        href = attrs.get("href")
        low = (href or "").lower()
        if (
            href
            and not href.startswith("#")
            and "javascript:" not in low
            and not low.startswith("mailto:")
            and not _is_img_url(href)
        ):
            self.href = href
            self.atxt = []
        else:
            self.href = None

    def _flush(self):
        if not self.word:
            return
        w = _ent("".join(self.word))
        self.word = []
        if self.in_title or self.in_style:
            return
        self._add(w)

    def _llen(self):
        n = 0
        for p in self.line:
            n += len(p)
        return n

    def _add(self, w):
        if not w or self.full:
            return
        while len(w) > WRAP:
            room = WRAP - self._llen()
            if room <= 0:
                self._nl()
                room = WRAP
            self.line.append(w[:room])
            w = w[room:]
            self._nl()
            if self.full:
                return
        extra = len(w) + (1 if self.line else 0)
        if self.line and self._llen() + extra > WRAP:
            self._nl()
        if self.line:
            self.line.append(" ")
        self.line.append(w)

    def _nl(self):
        line = "".join(self.line) if self.line else ""
        self.line = []
        if not line:
            if self.lines and self.lines[-1] != "":
                self.lines.append("")
            return
        if self.lines and self.lines[-1] == line:
            return
        self.lines.append(line)
        if len(self.lines) >= MAX_LINES:
            self.full = True


def _split(raw):
    if raw.endswith("/"):
        raw = raw[:-1].rstrip()
    parts = raw.replace("\n", " ").split(None, 1)
    if not parts:
        return "", {}
    name = parts[0].lower()
    attrs = {}
    if len(parts) == 1:
        return name, attrs
    rest = parts[1]
    i = 0
    n = len(rest)
    while i < n:
        while i < n and rest[i] <= " ":
            i += 1
        if i >= n:
            break
        a = i
        while i < n and rest[i] not in "=\t\r\n ":
            i += 1
        key = rest[a:i].lower()
        while i < n and rest[i] == " ":
            i += 1
        val = ""
        if i < n and rest[i] == "=":
            i += 1
            while i < n and rest[i] == " ":
                i += 1
            if i < n and rest[i] in "\"'":
                q = rest[i]
                i += 1
                b = i
                while i < n and rest[i] != q:
                    i += 1
                val = rest[b:i]
                if i < n:
                    i += 1
            else:
                b = i
                while i < n and rest[i] > " ":
                    i += 1
                val = rest[b:i]
        if key:
            attrs[key] = _ent(val)
    return name, attrs


def _ent(text):
    if "&" not in text:
        return text
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch != "&":
            out.append(ch)
            i += 1
            continue
        end = text.find(";", i + 1)
        if end < 0 or end - i > 10:
            out.append(ch)
            i += 1
            continue
        tok = text[i + 1 : end]
        i = end + 1
        if tok.startswith("#x") or tok.startswith("#X"):
            try:
                out.append(chr(int(tok[2:], 16)))
            except Exception:
                pass
        elif tok.startswith("#"):
            try:
                out.append(chr(int(tok[1:])))
            except Exception:
                pass
        else:
            out.append(ENT.get(tok, ""))
    return "".join(out)


def _col(t):
    return " ".join(t.replace("\r", " ").replace("\t", " ").split())


def _host(url):
    try:
        return url.split("://", 1)[-1].split("/", 1)[0]
    except Exception:
        return url[:20]


def _join(base, href):
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        if _is_img_url(href):
            return ""
        return href
    if href.startswith("data:") or href.startswith("javascript:"):
        return ""
    if href.startswith("//"):
        sch = "https"
        if "://" in base:
            sch = base.split("://", 1)[0]
        return sch + ":" + href
    sch = "https"
    host = ""
    path = "/"
    if "://" in base:
        sch, rest = base.split("://", 1)
        if "/" in rest:
            host, path = rest.split("/", 1)
            path = "/" + path.split("?", 1)[0]
        else:
            host = rest.split("?", 1)[0]
            path = "/"
    if href.startswith("/"):
        return "%s://%s%s" % (sch, host, href.split("#", 1)[0])
    folder = path.rsplit("/", 1)[0]
    return "%s://%s%s/%s" % (sch, host, folder, href.split("#", 1)[0])


def _enc(text):
    safe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
    out = []
    for ch in text:
        if ch == " ":
            out.append("+")
        elif ch in safe:
            out.append(ch)
        else:
            for b in ch.encode("utf-8"):
                out.append("%%%02X" % b)
    return "".join(out)
