"""Picoware Notifications Application

Gets FlipSocial, weather, email, and other notifications.
"""

from micropython import const
from picoware.system.colors import (
    TFT_BLACK,
    TFT_CYAN,
    TFT_DARKGREY,
    TFT_LIGHTGREY,
    TFT_ORANGE,
    TFT_RED,
    TFT_WHITE,
    TFT_YELLOW,
)
from picoware.system.decorator import storage_required, wifi_required

STATE_FETCHING_START = const(0)
STATE_FETCHING_FLIP_SOCIAL = const(1)
STATE_FETCHING_WEATHER_2 = const(2)
STATE_FETCHING_EMAIL = const(3)
STATE_DONE = const(4)

_state = STATE_FETCHING_START
_http = None
_cache = None
_imap = None
_request_error = ""
_scroll_offset = 0
_cache_saved = False


def __empty_cache() -> dict:
    """Return the default notification cache."""
    return {
        "flip_social": {},
        "weather_condition": "",
        "weather_temperature": "",
        "weather_humidity": "",
        "unread_email_count": 0,
    }


def __close_http() -> None:
    """Close the HTTP client."""
    global _http

    if _http is not None:
        _http.close()
        del _http
        _http = None


def __close_imap() -> None:
    """Close the IMAP client."""
    global _imap

    if _imap is not None:
        _imap.close()
        del _imap
        _imap = None


def __set_error(message: str) -> None:
    """Store the first request warning."""
    global _request_error

    if not _request_error:
        _request_error = message


def __advance_state() -> None:
    """Move to the next fetch state."""
    global _state

    if _state == STATE_FETCHING_FLIP_SOCIAL:
        _state = STATE_FETCHING_WEATHER_2
    elif _state == STATE_FETCHING_WEATHER_2:
        _state = STATE_FETCHING_EMAIL
    elif _state == STATE_FETCHING_EMAIL:
        _state = STATE_DONE


def __save_cache(view_manager) -> None:
    """Persist completed notification data."""
    global _cache_saved
    view_manager.storage.mkdir("picoware/notifications")
    if not view_manager.storage.serialize(
        _cache,
        "picoware/notifications/cache.json",
    ):
        __set_error("Cache save failed")
    _cache_saved = True


def __request_status() -> str:
    """Return the current fetch status."""
    return {
        STATE_FETCHING_START: "Starting...",
        STATE_FETCHING_FLIP_SOCIAL: "Fetching FlipSocial...",
        STATE_FETCHING_WEATHER_2: "Fetching weather...",
        STATE_FETCHING_EMAIL: "Checking email...",
        STATE_DONE: "Up to date",
    }.get(_state, "Working...")


def __request_start(view_manager) -> bool:
    """Start an asynchronous request based on the current state."""
    global _state, _http, _imap

    if _state == STATE_FETCHING_START:
        _state = STATE_FETCHING_FLIP_SOCIAL
    if _state == STATE_DONE:
        return False

    if _state == STATE_FETCHING_EMAIL:
        storage = view_manager.storage
        stored_email = storage.read("picoware/email/email.txt")
        stored_password = storage.read("picoware/email/password.txt")
        if not stored_email or not stored_password:
            __set_error("Email credentials not configured")
            _state = STATE_DONE
            return True

        try:
            from picoware.applications.email import IMAPAsync

            _imap = IMAPAsync()
            if not _imap.fetch_unread_count(stored_email, stored_password):
                __set_error("Unable to start email check")
                __close_imap()
                return False
            return True
        except Exception as error:
            __set_error(f"Email request failed: {error}")
            __close_imap()
            return False

    try:
        if _http is None:
            from picoware.system.http import HTTP

            _http = HTTP(thread_manager=view_manager.thread_manager)
        if _state == STATE_FETCHING_FLIP_SOCIAL:
            from picoware.system.settings import Settings

            settings = Settings(view_manager.storage)
            server_settings = settings.server_settings or {}
            username = server_settings.get("username", "")
            password = server_settings.get("password", "")
            return _http.request_async(
                "GET",
                f"https://www.jblanked.com/flipper/api/user/notifications/{username}/",
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Raspberry Pi Pico W",
                    "username": username,
                    "password": password,
                    "Setting": "X-Flipper-Redirect",
                },
                save_to_file="picoware/notifications/flip_social.json",
                storage=view_manager.storage,
            )
        if _state == STATE_FETCHING_WEATHER_2:
            url = "https://wttr.in/?format=%C,%t,%h"
            return _http.request_async(
                "GET", 
                url,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Raspberry Pi Pico W",
                },
                save_to_file="picoware/notifications/weather_2.txt", 
                storage=view_manager.storage
            )
    except Exception as error:
        __set_error(f"Request failed: {error}")
        __close_http()
        return False

    return False


def __request_process(view_manager) -> None:
    """Process the result of an asynchronous request."""
    global _state

    if _state in (
        STATE_FETCHING_FLIP_SOCIAL,
        STATE_FETCHING_WEATHER_2,
    ):
        if _http is None or not _http.is_request_complete():
            return

        if _http.state == 2: # HTTP_ISSUE
            __set_error(f"Request failed: {_http.error}")
            __close_http()
            return

        try:
            if _state == STATE_FETCHING_FLIP_SOCIAL:
                data = view_manager.storage.deserialize("picoware/notifications/flip_social.json")
                if data:
                    latest = data.get("latest_feed_item") or {}
                    _cache["flip_social"] = {
                        "new_feed_items": data.get("new_feed_items", 0),
                        "new_messages": data.get("new_messages", 0),
                        "latest_feed_item": latest,
                        "latest_feed_item_user": latest.get("username", ""),
                        "latest_feed_item_message": latest.get("message", ""),
                        "latest_feed_item_date": latest.get("date_created", ""),
                    }
            else:
                values = view_manager.storage.read("picoware/notifications/weather_2.txt").strip().split(",")
                if len(values) == 1:
                    _cache["weather_condition"] = values[0]
                    _cache["weather_temperature"] = ""
                    _cache["weather_humidity"] = ""
                elif len(values) == 2:
                    _cache["weather_condition"] = values[0]
                    _cache["weather_temperature"] = values[1]
                    _cache["weather_humidity"] = ""
                elif len(values) == 3:
                    _cache["weather_condition"] = values[0]
                    _cache["weather_temperature"] = values[1]
                    _cache["weather_humidity"] = values[2]
        except Exception as error:
            __set_error(f"Response parse failed: {error}")

        __close_http()
        __advance_state()
        __save_cache(view_manager)
        return

    if _state == STATE_FETCHING_EMAIL:
        if _imap is None or not _imap.is_finished:
            return
        if _imap.error:
            __set_error(f"Email check failed: {_imap.error}")
        elif _imap.result is not None:
            _cache["unread_email_count"] = _imap.result
        __close_imap()
        _state = STATE_DONE
        __save_cache(view_manager)


def __wrap_text(text: str, width: int) -> list:
    """Wrap text to the display width."""
    lines = []
    for paragraph in str(text or "").split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = ""
        for word in words:
            while len(word) > width:
                if line:
                    lines.append(line)
                    line = ""
                lines.append(word[:width])
                word = word[width:]
            if not word:
                continue
            candidate = word if not line else f"{line} {word}"
            if len(candidate) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
    return lines or [""]


def __fit_text(text: str, max_chars: int) -> str:
    """Fit text within a character limit."""
    text = str(text or "")
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return f"{text[:max_chars - 3]}..."


def __content_cards(view_manager) -> list:
    """Build dashboard cards from notification data."""
    draw = view_manager.draw
    margin = max(4, draw.size.x // 24)
    font = draw.get_font()
    char_width = max(1, font.width + font.spacing)
    detail_width = max(1, (draw.size.x - (margin * 2) - draw.scale_x(34)) // char_width)

    social = _cache.get("flip_social", {})
    social_details = []
    latest_user = social.get("latest_feed_item_user", "")
    latest_date = social.get("latest_feed_item_date", "")
    if latest_user or latest_date:
        social_details.append(
            f"{latest_user} {latest_date}".strip()
        )
    latest_message = social.get("latest_feed_item_message", "")
    if latest_message:
        social_details.extend(__wrap_text(latest_message, detail_width))
    if not social_details:
        social_details.append("No new activity")

    condition = _cache.get("weather_condition", "") or "Unavailable"
    weather_details = __wrap_text(condition, detail_width)

    unread = _cache.get("unread_email_count", 0)
    email_details = [
        "Unread messages waiting" if unread else "Mailbox is clear",
    ]

    cards = [
        {
            "title": "FLIPSOCIAL",
            "icon": "social",
            "accent": TFT_CYAN,
            "metrics": [
                (social.get("new_feed_items", 0), "FEED"),
                (social.get("new_messages", 0), "MESSAGES"),
            ],
            "details": social_details,
        },
        {
            "title": "WEATHER",
            "icon": "weather",
            "accent": TFT_YELLOW,
            "metrics": [
                (_cache.get("weather_temperature", "") or "--", "TEMP"),
                (_cache.get("weather_humidity", "") or "--", "HUMIDITY"),
            ],
            "details": weather_details,
        },
        {
            "title": "EMAIL",
            "icon": "email",
            "accent": TFT_ORANGE,
            "metrics": [(unread, "UNREAD")],
            "details": email_details,
        },
    ]
    if _request_error:
        cards.insert(
            0,
            {
                "title": "NOTICE",
                "icon": "notice",
                "accent": TFT_RED,
                "metrics": [("!", "ATTENTION")],
                "details": __wrap_text(_request_error, detail_width),
            },
        )
    return cards


def __draw_icon(draw, icon: str, x: int, y: int, color: int) -> None:
    """Draw a compact notification icon."""
    if icon == "social":
        draw._fill_circle(x + draw.scale_x(8), y + draw.scale_y(8), draw.scale_x(7), color)
        draw._fill_circle(x + draw.scale_x(5), y + draw.scale_y(7), 1, TFT_BLACK)
        draw._fill_circle(x + draw.scale_x(9), y + draw.scale_y(7), 1, TFT_BLACK)
        draw._fill_circle(x + draw.scale_x(13), y + draw.scale_y(7), 1, TFT_BLACK)
    elif icon == "weather":
        draw._circle(x + draw.scale_x(8), y + draw.scale_y(8), draw.scale_x(4), color)
        draw._line(x + draw.scale_x(8), y, x + draw.scale_x(8), y + draw.scale_y(3), color)
        draw._line(x + draw.scale_x(8), y + draw.scale_y(13), x + draw.scale_x(8), y + draw.scale_y(16), color)
        draw._line(x, y + draw.scale_y(8), x + draw.scale_x(3), y + draw.scale_y(8), color)
        draw._line(x + draw.scale_x(13), y + draw.scale_y(8), x + draw.scale_x(16), y + draw.scale_y(8), color)
    elif icon == "email":
        draw._rectangle(x, y + draw.scale_y(2), draw.scale_x(17), draw.scale_y(12), color)
        draw._line(x + 1, y + draw.scale_y(3), x + draw.scale_x(8), y + draw.scale_y(9), color)
        draw._line(x + draw.scale_x(15), y + draw.scale_y(3), x + draw.scale_x(8), y + draw.scale_y(9), color)
    else:
        draw._fill_circle(x + draw.scale_x(8), y + draw.scale_y(8), draw.scale_x(8), color)
        draw._text(x + draw.scale_x(6), y + draw.scale_y(1), "!", TFT_BLACK)


def __card_height(draw, card: dict, detail_line_height: int) -> int:
    """Calculate a card height from its content."""
    _font = draw.get_font()
    metric_height = _font.height * 2 + draw.scale_y(3)
    return (
        draw.scale_y(8)
        + _font.height
        + draw.scale_y(3)
        + metric_height
        + (len(card["details"]) * detail_line_height)
        + draw.scale_y(7)
    )


def __draw_card(
    draw,
    card: dict,
    x: int,
    y: int,
    width: int,
    height: int,
    body_top: int,
    body_bottom: int,
    detail_line_height: int,
) -> None:
    """Draw one dashboard card."""
    visible_top = max(y, body_top)
    visible_bottom = min(y + height, body_bottom)
    if visible_top >= visible_bottom:
        return

    panel_color = TFT_DARKGREY
    accent = card["accent"]
    if y >= body_top and y + height <= body_bottom:
        draw._fill_round_rectangle(x, y, width, height, draw.scale_y(5), panel_color)
        draw._rectangle(x, y, width, height, accent)
    else:
        draw._fill_rectangle(x, visible_top, width, visible_bottom - visible_top, panel_color)
    draw._fill_rectangle(x, visible_top, 3, visible_bottom - visible_top, accent)

    _font = draw.get_font()
    title_font = _font
    metric_font = _font
    detail_x = x + draw.scale_x(29)
    title_y = y + draw.scale_y(5)
    metric_y = title_y + title_font.height + draw.scale_y(3)
    detail_y = metric_y + metric_font.height + title_font.height + draw.scale_y(4)

    if title_y >= body_top and title_y + title_font.height <= body_bottom:
        __draw_icon(draw, card["icon"], x + draw.scale_x(7), y + draw.scale_y(4), accent)
        draw._text(detail_x, title_y, card["title"], TFT_WHITE)

    metrics = card["metrics"]
    metric_width = max(1, (width - draw.scale_x(36)) // len(metrics))
    for index, metric in enumerate(metrics):
        metric_x = detail_x + index * metric_width
        if metric_y >= body_top and metric_y + metric_font.height <= body_bottom:
            max_chars = max(1, (metric_width - 2) // (metric_font.width + metric_font.spacing)) - 1
            draw._text(metric_x, metric_y, __fit_text(metric[0], max_chars), accent)
            label_y = metric_y + metric_font.height + 1
            draw._text(metric_x, label_y, __fit_text(metric[1], max_chars), TFT_LIGHTGREY)

    for index, line in enumerate(card["details"]):
        line_y = detail_y + index * detail_line_height
        if line_y < body_top or line_y + title_font.height > body_bottom:
            continue
        draw._text(detail_x, line_y, line, TFT_WHITE if index == 0 else TFT_LIGHTGREY)


def __draw(view_manager) -> None:
    """Draw the notification dashboard."""
    global _scroll_offset

    draw = view_manager.draw
    width, screen_height = draw.size.x, draw.size.y
    margin = max(4, width // 24)
    title_font = draw.get_font()
    detail_line_height = max(1, title_font.height + 2)
    header_height = title_font.height * 2 + draw.scale_y(8)
    body_top = header_height + draw.scale_y(4)
    body_bottom = screen_height

    cards = __content_cards(view_manager)
    card_width = width - margin * 2
    card_gap = draw.scale_y(5)
    total_height = 0
    for card in cards:
        total_height += __card_height(draw, card, detail_line_height)
    total_height += max(0, len(cards) - 1) * card_gap
    max_scroll = max(0, total_height - (body_bottom - body_top))
    _scroll_offset = min(_scroll_offset, max_scroll)

    background = view_manager.background_color
    header_color = view_manager.selected_color
    draw.erase()
    draw._fill_rectangle(0, 0, width, header_height, header_color)
    draw._fill_rectangle(0, header_height - 2, width, 2, TFT_CYAN)
    draw._text(margin, draw.scale_y(3), "NOTIFICATIONS", TFT_WHITE)
    draw._text(margin, draw.scale_y(3) + title_font.height + 1, __request_status(), TFT_LIGHTGREY)

    draw._fill_rectangle(
        0, body_top - 2,
        width, body_bottom - body_top + 2,
        background,
    )
    card_y = body_top - _scroll_offset
    for card in cards:
        card_height = __card_height(draw, card, detail_line_height)
        __draw_card(
            draw,
            card,
            margin,
            card_y,
            card_width,
            card_height,
            body_top,
            body_bottom,
            detail_line_height,
        )
        card_y += card_height + card_gap

    draw.swap()


@storage_required
@wifi_required
def start(view_manager):
    """Start the app."""
    global _state, _cache, _request_error, _scroll_offset, _cache_saved

    __close_http()
    __close_imap()
    _request_error = ""
    _scroll_offset = 0
    _cache = view_manager.storage.deserialize("picoware/notifications/cache.json")
    if _cache:
        _cache_saved = True
    else:
        _cache = __empty_cache()
        _cache_saved = False
    return True


def run(view_manager):
    """Run the app."""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_CENTER,
        BUTTON_DOWN,
        BUTTON_UP,
    )

    global _state, _cache, _request_error, _scroll_offset, _cache_saved
    d = view_manager.draw
    scroll_step = max(1, d.font_size.y + d.scale_y(4))
    button = view_manager.button
    if button == BUTTON_BACK:
        view_manager.back()
        return
    if button == BUTTON_CENTER:
        __close_http()
        __close_imap()
        _cache = __empty_cache()
        _state = STATE_FETCHING_START
        _request_error = ""
        _scroll_offset = 0
        _cache_saved = False
    elif button == BUTTON_UP:
        _scroll_offset = max(0, _scroll_offset - scroll_step)
    elif button == BUTTON_DOWN:
        _scroll_offset += scroll_step

    should_start = _state == STATE_FETCHING_START
    should_start = should_start or (
        _state in (
            STATE_FETCHING_FLIP_SOCIAL,
            STATE_FETCHING_WEATHER_2,
        )
        and _http is None
    )
    should_start = should_start or (
        _state == STATE_FETCHING_EMAIL and _imap is None
    )

    if should_start:
        if not __request_start(view_manager):
            __close_http()
            __set_error("Unable to start notification fetch")
            __advance_state()
    elif _state != STATE_DONE:
        __request_process(view_manager)

    if _state == STATE_DONE and not _cache_saved:
        __save_cache(view_manager)
    __draw(view_manager)


def stop(view_manager):
    """Stop the app."""
    from gc import collect

    global _state

    __close_http()
    __close_imap()
    if _state != STATE_DONE:
        _state = STATE_FETCHING_START
    collect()