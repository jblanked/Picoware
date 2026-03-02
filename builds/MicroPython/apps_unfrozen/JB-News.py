# picoware app to read news from JB-News API: https://www.jblanked.com/news/api/docs/
from micropython import const

STATE_MENU = const(-1)  # main menu
STATE_VIEW = const(0)  # views news
STATE_OFFSET = const(1)  # set offset
STATE_KEY = const(2)  # set API key
STATE_SOURCE = const(3)  # set news source
STATE_INFO = const(4)  # show info about the app and API

_CAL_HDR_H = const(20)  # header bar height
_CAL_COL_H = const(12)  # column label row height
_CAL_ROW_H = const(22)  # event row height
_CAL_START = const(_CAL_HDR_H + _CAL_COL_H)  # y=32

_DIV_TIME = const(38)  # x divider after TIME
_DIV_CUR = const(68)  # x divider after CUR
_DIV_NAME = const(220)  # x divider after EVENT
_DIV_AF = const(280)  # x divider after ACT/FOR

_state = STATE_MENU
_menu = None
_http = None
_loading = None
_data_fetched = False
_data_loaded = False
_news_data = []
_news_scroll = 0
_news_view_dirty = True
_info_view_dirty = True


def __fetch_news(view_manager) -> bool:
    """Fetch news from JB-News API"""
    from picoware.system.http import HTTP

    global _http

    if _http is not None:
        _http.close()
        del _http

    _http = HTTP(thread_manager=view_manager.thread_manager)

    _api_key = __load_setting("api_key", view_manager)
    _source = __load_setting("news_source", view_manager)

    if not _api_key:
        view_manager.alert("Please set API key first!", False)
        return False

    if not _source:
        _source = "mql5"  # default source

    _url = f"https://www.jblanked.com/news/api/{_source}/calendar/today/"

    _header = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {_api_key}",
    }

    view_manager.storage.remove("picoware/JB-News/news.txt")

    return _http.get_async(
        _url,
        _header,
        save_to_file="picoware/JB-News/news.txt",
        storage=view_manager.storage,
    )


def __subtract_hours(date_str: str, hours: int) -> str:
    """Subtract hours from a date string formatted as YYYY.MM.DD HH:MM:SS"""
    date_part, time_part = date_str.split(" ")
    year, month, day = [int(x) for x in date_part.split(".")]
    hour, minute, second = [int(x) for x in time_part.split(":")]
    hour -= hours
    while hour < 0:
        hour += 24
        day -= 1
        if day < 1:
            month -= 1
            if month < 1:
                month = 12
                year -= 1
            _days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            if month == 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
                day = 29
            else:
                day = _days[month]
    while hour >= 24:
        hour -= 24
        day += 1
        _days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        _max = (
            29
            if month == 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
            else _days[month]
        )
        if day > _max:
            day = 1
            month += 1
            if month > 12:
                month = 1
                year += 1
    return "{:04d}.{:02d}.{:02d} {:02d}:{:02d}:{:02d}".format(
        year, month, day, hour, minute, second
    )


def __parse_news(view_manager) -> list:
    """Load news from storage"""
    from json import loads

    storage = view_manager.storage
    _path = "picoware/JB-News/news.txt"

    if not storage.exists(_path):
        view_manager.alert("No news data found. Please fetch news first!", False)
        return []

    _str_offset = __load_setting("offset", view_manager)
    _offset = int(_str_offset) if _str_offset and _str_offset.isdigit() else 0
    # https://github.com/jblanked/JB-News/blob/72fe9dbe3bac44a5c0a33854d2e5a666b7ca8f69/Python/jb_news/news.py#L291
    _data: dict = storage.serialize(_path)  # should return a list of news events
    _event_list = []
    for data in _data:
        if _offset == 0:
            date = data["Date"]
        else:
            date = __subtract_hours(data["Date"], _offset)

        _event_list.append(
            {
                "Name": data["Name"],
                "Currency": data["Currency"],
                "Date": date,
                "Actual": data["Actual"],
                "Forecast": data["Forecast"],
                "Previous": data["Previous"],
                "Outcome": data["Outcome"],
            }
        )
    return _event_list


def __load_setting(key: str, view_manager) -> str:
    """Load a setting from storage"""
    storage = view_manager.storage
    path = f"picoware/JB-News/{key}.txt"
    return storage.read(path)


def __keyboard_start(
    view_manager, title: str, save_key: str, initial_text: str = ""
) -> bool:
    """Start a keyboard input"""
    kb = view_manager.keyboard
    kb.reset()
    kb.set_save_callback(
        lambda result: view_manager.storage.write(
            f"picoware/JB-News/{save_key}.txt", result
        )
    )
    kb.response = initial_text
    kb.title = title
    return kb.run(force=True)


def __keyboard_run(view_manager) -> bool:
    """Run the keyboard"""
    global _state

    kb = view_manager.keyboard
    if not kb.run():
        _state = STATE_MENU
        return False

    if kb.is_finished:
        # already saved in callback, so just go back to menu
        _state = STATE_MENU
        __menu_start(view_manager)

    return True


def __loading_run(view_manager, message: str = "Fetching...") -> None:
    """Start the loading view"""

    global _loading

    if _loading is None:
        from picoware.gui.loading import Loading

        draw = view_manager.draw
        bg = view_manager.background_color
        fg = view_manager.foreground_color

        _loading = Loading(draw, fg, bg)
        _loading.text = message
        _loading.animate()
    else:
        _loading.animate()


def __menu_start(view_manager):
    """Initialize the Menu"""
    from picoware.gui.menu import Menu
    from picoware.system.colors import TFT_BLUE

    global _menu

    if _menu is not None:
        _menu.clear()
        del _menu
        _menu = None

    draw = view_manager.draw
    bg = view_manager.background_color
    fg = view_manager.foreground_color

    # Set menu
    _menu = Menu(
        draw,
        "JB-News",
        0,
        draw.size.y,
        fg,
        bg,
        TFT_BLUE,
        fg,
    )

    _menu.add_item("View News")
    _menu.add_item("Set Offset")
    _menu.add_item("Set API Key")
    _menu.add_item("Set News Source")
    _menu.add_item("Info")

    _menu.set_selected(0)
    _menu.draw()


def __outcome_color(outcome: str):
    """Return (color, symbol) based on Actual vs Forecast in the outcome string.

    Expected format: "Actual {op} Forecast {optional: op Previous}"
    e.g. "Actual = Forecast > Previous"
         "Actual > Forecast"
         "Actual < Forecast = Previous"
    """
    from picoware.system.colors import TFT_GREEN, TFT_RED, TFT_YELLOW, TFT_DARKGREY

    if not outcome:
        return TFT_DARKGREY, "?"

    s = outcome.strip()
    if "Actual > Forecast" in s:
        return TFT_GREEN, "+"
    if "Actual < Forecast" in s:
        return TFT_RED, "-"
    if "Actual = Forecast" in s:
        return TFT_YELLOW, "="
    return TFT_DARKGREY, "?"


def __draw_news_view(view_manager):
    """Render the calendar-style news view onto the display"""
    from picoware.system.colors import (
        TFT_WHITE,
        TFT_BLACK,
        TFT_BLUE,
        TFT_CYAN,
        TFT_YELLOW,
        TFT_LIGHTGREY,
        TFT_ORANGE,
    )
    from picoware.system.font import FONT_XTRA_SMALL, FONT_SMALL
    from picoware.system.vector import Vector

    global _news_scroll, _news_data

    draw = view_manager.draw
    W = draw.size.x  # 320
    H = draw.size.y  # 320

    # ── palette ──────────────────────────────────────────────────────
    C_HDR_BG = 0x0A28  # deep navy header
    C_COL_BG = 0x2965  # slate column-label bar
    C_ROW_A = 0x0841  # very dark row (even)
    C_ROW_B = 0x10A2  # slightly lighter row (odd)
    C_DIV = 0x2965  # divider lines
    C_TIME = TFT_CYAN
    C_CUR = TFT_YELLOW
    C_NAME = TFT_WHITE
    C_AF = TFT_LIGHTGREY
    C_LBL = TFT_ORANGE

    visible = (H - _CAL_START) // _CAL_ROW_H  # == 13
    total = len(_news_data)

    # ── header bar ───────────────────────────────────────────────────
    draw.fill_rectangle(Vector(0, 0), Vector(W, _CAL_HDR_H), C_HDR_BG)
    # accent strip at very top
    draw.fill_rectangle(Vector(0, 0), Vector(W, 2), TFT_BLUE)

    title = "JB-News"
    tx = (W - draw.len(title, FONT_SMALL)) // 2
    draw.text(Vector(tx, 4), title, TFT_WHITE, FONT_SMALL)

    # scroll indicator top-right
    lo = _news_scroll + 1
    hi = min(_news_scroll + visible, total)
    info = "{}/{}".format(hi, total) if total else "0/0"
    draw.text(
        Vector(W - draw.len(info, FONT_XTRA_SMALL) - 6, 7),
        info,
        TFT_CYAN,
        FONT_XTRA_SMALL,
    )

    # up/down arrows in header if scrollable
    if _news_scroll > 0:
        draw.text(Vector(3, 5), "^", TFT_CYAN, FONT_XTRA_SMALL)
    if _news_scroll + visible < total:
        draw.text(Vector(3, 11), "v", TFT_CYAN, FONT_XTRA_SMALL)

    # ── column label row ─────────────────────────────────────────────
    draw.fill_rectangle(Vector(0, _CAL_HDR_H), Vector(W, _CAL_COL_H), C_COL_BG)
    yc = _CAL_HDR_H + 2
    draw.text(Vector(2, yc), "TIME", C_LBL, FONT_XTRA_SMALL)
    draw.text(Vector(_DIV_TIME + 2, yc), "CUR", C_LBL, FONT_XTRA_SMALL)
    draw.text(Vector(_DIV_CUR + 2, yc), "EVENT", C_LBL, FONT_XTRA_SMALL)
    draw.text(Vector(_DIV_NAME + 2, yc), "A/F", C_LBL, FONT_XTRA_SMALL)
    draw.text(Vector(_DIV_AF + 2, yc), "OUT", C_LBL, FONT_XTRA_SMALL)
    # dividers in column label row
    for xd in (_DIV_TIME, _DIV_CUR, _DIV_NAME, _DIV_AF):
        draw.line_custom(
            Vector(xd, _CAL_HDR_H), Vector(xd, _CAL_HDR_H + _CAL_COL_H - 1), C_DIV
        )

    # ── event rows ───────────────────────────────────────────────────
    for i in range(visible):
        idx = _news_scroll + i
        y = _CAL_START + i * _CAL_ROW_H

        row_bg = C_ROW_A if (i % 2 == 0) else C_ROW_B
        draw.fill_rectangle(Vector(0, y), Vector(W, _CAL_ROW_H), row_bg)

        if idx < total:
            ev = _news_data[idx]

            # ---- TIME  (HH:MM from "YYYY.MM.DD HH:MM:SS") ----
            ds = ev.get("Date", "") or ""
            time_str = ds[11:16] if len(ds) >= 16 else "--:--"
            draw.text(Vector(2, y + 7), time_str, C_TIME, FONT_XTRA_SMALL)

            # ---- CURRENCY (3-char code) ----
            cur = (ev.get("Currency", "") or "")[:3]
            draw.text(Vector(_DIV_TIME + 2, y + 7), cur, C_CUR, FONT_XTRA_SMALL)

            # ---- EVENT NAME  ----
            name = ev.get("Name", "") or ""
            max_chars = 24
            if len(name) > max_chars:
                name = name[: max_chars - 1] + ">"
            draw.text(Vector(_DIV_CUR + 2, y + 7), name, C_NAME, FONT_XTRA_SMALL)

            # ---- ACTUAL / FORECAST ----
            actual = str(ev.get("Actual", "") or "")[:5]
            forecast = str(ev.get("Forecast", "") or "")[:5]
            if actual and forecast:
                af = actual + "/" + forecast
            elif actual:
                af = actual
            elif forecast:
                af = "/" + forecast
            else:
                af = "--"
            if len(af) > 9:
                af = af[:9]
            draw.text(Vector(_DIV_NAME + 2, y + 7), af, C_AF, FONT_XTRA_SMALL)

            # ---- OUTCOME indicator  ----
            out_color, out_sym = __outcome_color(ev.get("Outcome", ""))
            # colored square
            draw.fill_rectangle(Vector(_DIV_AF + 2, y + 6), Vector(8, 8), out_color)
            # symbol to the right of the square
            draw.text(Vector(_DIV_AF + 12, y + 7), out_sym, out_color, FONT_XTRA_SMALL)

        # ---- horizontal divider ----
        draw.line_custom(
            Vector(0, y + _CAL_ROW_H - 1), Vector(W, y + _CAL_ROW_H - 1), C_DIV
        )
        # ---- vertical dividers ----
        for xd in (_DIV_TIME, _DIV_CUR, _DIV_NAME, _DIV_AF):
            draw.line_custom(Vector(xd, y), Vector(xd, y + _CAL_ROW_H - 1), C_DIV)

    # ── bottom accent line ────────────────────────────────────────────
    bottom_y = _CAL_START + visible * _CAL_ROW_H
    if bottom_y < H:
        draw.fill_rectangle(Vector(0, bottom_y), Vector(W, H - bottom_y), TFT_BLACK)

    draw.swap()


def __draw_info_view(view_manager):
    """Render the info/help screen. Called only when dirty."""
    from picoware.system.colors import (
        TFT_WHITE,
        TFT_BLACK,
        TFT_BLUE,
        TFT_CYAN,
        TFT_YELLOW,
        TFT_ORANGE,
        TFT_LIGHTGREY,
        TFT_DARKGREY,
        TFT_GREEN,
    )
    from picoware.system.font import FONT_XTRA_SMALL, FONT_SMALL, FONT_LARGE
    from picoware.system.vector import Vector

    draw = view_manager.draw
    W = draw.size.x  # 320
    H = draw.size.y  # 320

    C_HDR_BG = 0x0A28  # deep navy
    C_CARD_BG = 0x0841  # very dark card
    C_DIV = 0x2965  # slate divider

    # ── full background ──────────────────────────────────────────────
    draw.fill_screen(TFT_BLACK)

    # ── top accent strip ─────────────────────────────────────────────
    draw.fill_rectangle(Vector(0, 0), Vector(W, 2), TFT_BLUE)

    # ── header block ─────────────────────────────────────────────────
    HDR_H = 52
    draw.fill_rectangle(Vector(0, 2), Vector(W, HDR_H), C_HDR_BG)

    # title – large, centred
    title = "JB-News"
    tx = (W - draw.len(title, FONT_LARGE)) // 2
    draw.text(Vector(tx, 8), title, TFT_WHITE, FONT_LARGE)

    # subtitle – small, centred, cyan
    sub = "Economic Calendar API"
    sx = (W - draw.len(sub, FONT_XTRA_SMALL)) // 2
    draw.text(Vector(sx, 36), sub, TFT_CYAN, FONT_XTRA_SMALL)

    # bottom accent under header
    draw.fill_rectangle(Vector(0, 2 + HDR_H), Vector(W, 2), TFT_BLUE)

    # ── info card ────────────────────────────────────────────────────
    CARD_X = 8
    CARD_Y = 62
    CARD_W = W - 16
    CARD_H = H - CARD_Y - 22  # leave room for footer
    CARD_R = 4
    draw.fill_round_rectangle(
        Vector(CARD_X, CARD_Y), Vector(CARD_W, CARD_H), CARD_R, C_CARD_BG
    )
    draw.rect(Vector(CARD_X, CARD_Y), Vector(CARD_W, CARD_H), C_DIV)

    # bullet rows: (bullet_color, text)
    ROWS = [
        (TFT_CYAN, "Free economic news data"),
        (TFT_GREEN, "jblanked.com/news/api/docs/"),
        (TFT_ORANGE, "Sources: mql5 / forex-factory"),
        (TFT_ORANGE, "         fxstreet"),
        (TFT_YELLOW, "Offset adjusts to local time"),
        (TFT_LIGHTGREY, "Mon-Fri, updates at 00:00 EST"),
        (TFT_DARKGREY, "Set API key + source in menu"),
    ]

    LINE_H = 16
    TEXT_X = CARD_X + 16
    DOT_X = CARD_X + 7
    y = CARD_Y + 8

    for col, txt in ROWS:
        # bullet dot (filled 4×4 square)
        draw.fill_rectangle(Vector(DOT_X, y + 3), Vector(4, 4), col)
        draw.text(Vector(TEXT_X, y), txt, col, FONT_XTRA_SMALL)
        y += LINE_H

    # ── footer hint ──────────────────────────────────────────────────
    hint = "[ BACK ] return to menu"
    hx = (W - draw.len(hint, FONT_XTRA_SMALL)) // 2
    draw.text(Vector(hx, H - 14), hint, TFT_DARKGREY, FONT_XTRA_SMALL)

    draw.swap()


def start(view_manager) -> bool:
    """Start the app"""
    wifi = view_manager.wifi

    # if not a wifi device, return
    if not wifi:
        view_manager.alert("WiFi not available...", False)
        return False

    # if wifi isn't connected, return
    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        view_manager.alert("WiFi not connected yet...", False)
        connect_to_saved_wifi(view_manager)
        return False

    storage = view_manager.storage
    storage.mkdir("picoware/JB-News")

    global _state, _data_fetched, _data_loaded, _news_data, _news_scroll, _news_view_dirty, _info_view_dirty

    _state = STATE_MENU
    _data_fetched = False
    _data_loaded = False
    _news_data = []
    _news_scroll = 0
    _news_view_dirty = True
    _info_view_dirty = True

    __menu_start(view_manager)

    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )

    global _state, _menu, _data_fetched, _data_loaded, _http, _news_data, _news_scroll, _news_view_dirty, _info_view_dirty

    inp = view_manager.input_manager
    button = inp.button

    if _state == STATE_MENU:
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
            _state = _menu.selected_index
            if _state in (STATE_OFFSET, STATE_KEY, STATE_SOURCE):
                # load current setting for keyboard input
                title = ["Offset", "API Key", "News Source"][_state - 1]
                save_key = title.lower().replace(" ", "_")
                initial_text = __load_setting(save_key, view_manager)
                __keyboard_start(view_manager, title, save_key, initial_text)
    elif _state == STATE_VIEW:
        # first we fetch news (and show loading animation)
        # then we load news from storage and display it
        if not _data_fetched and not _data_loaded:
            if not __fetch_news(view_manager):
                view_manager.alert("Failed to fetch news!", False)
                _state = STATE_MENU
                __menu_start(view_manager)
                return
            __loading_run(view_manager, "Fetching...")
            _data_fetched = True
        elif _data_fetched and not _data_loaded:
            if _http is None:
                view_manager.alert("HTTP client not initialized!", False)
                _state = STATE_MENU
                __menu_start(view_manager)
                return
            if _http is not None and _http.in_progress:
                __loading_run(view_manager, "Fetching...")
            elif _http is not None and _http.is_finished:
                _http.close()
                del _http
                _http = None
                _data_fetched = False
                _news_data = __parse_news(view_manager)
                _data_loaded = True
                _news_scroll = 0
                _news_view_dirty = True
        elif _data_loaded:
            if not _news_data:
                view_manager.alert(
                    "No news data to display! Check again at 00:00 EST", False
                )
                _state = STATE_MENU
                __menu_start(view_manager)
                return
            # ── calendar view scroll ──────────────────────────────
            visible = (
                _CAL_ROW_H and (view_manager.draw.size.y - _CAL_START) // _CAL_ROW_H
            ) or 13
            total = len(_news_data)
            if button in (BUTTON_UP, BUTTON_LEFT):
                inp.reset()
                if _news_scroll > 0:
                    _news_scroll -= 1
                    _news_view_dirty = True
            elif button in (BUTTON_DOWN, BUTTON_RIGHT):
                inp.reset()
                if _news_scroll + visible < total:
                    _news_scroll += 1
                    _news_view_dirty = True
            # ── redraw when needed ────────────────────────────────
            if _news_view_dirty:
                __draw_news_view(view_manager)
                _news_view_dirty = False

    elif _state in (STATE_OFFSET, STATE_KEY, STATE_SOURCE):
        __keyboard_run(view_manager)
    elif _state == STATE_INFO:
        if _info_view_dirty:
            __draw_info_view(view_manager)
            _info_view_dirty = False
        if button == BUTTON_BACK:
            inp.reset()
            _state = STATE_MENU
            __menu_start(view_manager)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _state, _menu, _http, _loading, _data_fetched, _data_loaded, _news_data, _news_scroll, _news_view_dirty, _info_view_dirty

    _state = None
    _data_fetched = False
    _data_loaded = False
    _news_data = []
    _news_scroll = 0
    _news_view_dirty = True
    _info_view_dirty = True
    if _menu is not None:
        _menu.clear()
        del _menu
        _menu = None
    if _http is not None:
        _http.close()
        del _http
        _http = None
    if _loading is not None:
        _loading.stop()
        del _loading
        _loading = None

    collect()
