"""Forecast - a lightweight weather application for Picoware.

Data providers require no account or API key:
  * Open-Meteo (up to 16 daily forecasts, including rain probability)
  * 7Timer! (compact three-hour forecast, grouped into daily summaries)
"""

from micropython import const


# Non-blocking application states. Network operations get their own states so
# run() can keep animating and accepting Picoware lifecycle events while a
# background request is active.
STATE_MAIN = const(0)
STATE_SAVED = const(1)
STATE_MANAGE = const(2)
STATE_INPUT = const(3)
STATE_SEARCHING = const(4)
STATE_RESULTS = const(5)
STATE_FETCHING = const(6)
STATE_FORECAST = const(7)
STATE_SETTINGS = const(8)

CONFIG_PATH = "picoware/forecast.json"
PAGE_DAYS = const(4)
MAX_LOCATIONS = const(12)

# Forecast-screen vertical layout (pixels on the 320 x 320 PicoCalc display).
# Keeping these values together makes future physical-display tuning simple.
TITLE_Y = const(4)         # Small-font, single-line saved location heading.
STATUS_Y = const(34)       # Provider/unit/page, clear of graph temperatures.
GRAPH_TOP = const(58)      # Top edge of the temperature plot.
GRAPH_BOTTOM = const(166)  # Shorter plot leaves space for weekday and date.
WEEKDAY_Y = const(179)     # Full weekday name above its calendar date.
DATE_Y = const(196)        # Date row, moved slightly down from the old layout.
ICON_Y = const(225)        # Center line for sun/cloud/rain symbols.
CONDITION_Y = const(251)   # Sunny, cloudy, rain, snow, etc.
RAIN_Y = const(268)        # Daily precipitation probability.
WIND_Y = const(285)        # Daily maximum wind speed.

# Fonts built into Picoware. The title deliberately uses the smaller font so a
# long administrative location name has substantially more horizontal room.
TITLE_FONT = const(1)

# Runtime UI/network objects are created lazily to conserve Pico 2 W memory.
_state = STATE_MAIN
_menu = None
_http = None
_loading = None
# Persistent/user data and normalized forecast data. Locations are stored as
# name/latitude/longitude dictionaries; days use one provider-neutral schema.
_locations = []
_search_results = []
_days = []
_selected_location = None
_page = 0
# User preferences. These defaults also migrate older configuration files that
# do not yet contain the newer unit/date/provider keys.
_provider = "Open-Meteo"
_temperature_unit = "Celsius"
_wind_unit = "km/h"
_date_format = "day-month"
_input_started = False
_pending_query = ""


def _new_menu(view_manager, title):
    from picoware.gui.menu import Menu

    draw = view_manager.draw
    return Menu(
        draw, title, 0, draw.size.y,
        view_manager.foreground_color, view_manager.background_color,
        view_manager.selected_color, view_manager.foreground_color,
    )


def _set_menu(view_manager, title, items, state):
    global _menu, _state
    view_manager.draw.erase()
    _menu = _new_menu(view_manager, title)
    for item in items:
        _menu.add_item(item)
    _menu.draw()
    _state = state


def _show_main(view_manager):
    _set_menu(view_manager, "Forecast",
              ("Saved locations", "Add/Remove location", "Settings"), STATE_MAIN)


def _show_saved(view_manager):
    # Fold names here as a final guard for configurations created by an older
    # Forecast version before location transliteration was introduced.
    items = [_latin_text(loc["name"]) for loc in _locations]
    if not items:
        items = ["No saved locations"]
    _set_menu(view_manager, "Saved locations", items, STATE_SAVED)


def _show_manage(view_manager):
    items = ["Add location"]
    for loc in _locations:
        items.append("Remove: " + _latin_text(loc["name"]))
    _set_menu(view_manager, "Add/Remove", items, STATE_MANAGE)


def _show_settings(view_manager):
    _set_menu(view_manager, "Settings", (
        "Source: " + _provider,
        "Temperature: " + ("C" if _temperature_unit == "Celsius" else "F"),
        "Wind: " + _wind_unit,
        "Date: " + _date_format,
    ), STATE_SETTINGS)


def _save(view_manager):
    """Persist preferences and saved coordinates as JSON on the SD card."""
    view_manager.storage.mkdir("picoware")
    view_manager.storage.deserialize({
        "provider": _provider, "temperature_unit": _temperature_unit,
        "wind_unit": _wind_unit, "date_format": _date_format,
        "locations": _locations,
    }, CONFIG_PATH)


def _load(view_manager):
    """Load configuration defensively, preserving defaults for missing keys."""
    global _locations, _provider, _temperature_unit, _wind_unit, _date_format
    if not view_manager.storage.exists(CONFIG_PATH):
        return
    data = view_manager.storage.serialize(CONFIG_PATH)
    if isinstance(data, dict):
        locations = data.get("locations", [])
        if isinstance(locations, list):
            _locations = []
            for item in locations:
                if (isinstance(item, dict) and "name" in item and
                        "lat" in item and "lon" in item):
                    # Normalize previously saved Unicode names as they enter
                    # memory, so every menu and forecast screen sees safe text.
                    _locations.append({
                        "name": _latin_text(str(item["name"])),
                        "lat": item["lat"], "lon": item["lon"],
                    })
                    if len(_locations) >= MAX_LOCATIONS:
                        break
        provider = data.get("provider", "Open-Meteo")
        if provider in ("Open-Meteo", "7Timer"):
            _provider = provider
        temperature_unit = data.get("temperature_unit", "Celsius")
        if temperature_unit in ("Celsius", "Fahrenheit"):
            _temperature_unit = temperature_unit
        wind_unit = data.get("wind_unit", "km/h")
        if wind_unit in ("km/h", "m/s", "knots"):
            _wind_unit = wind_unit
        date_format = data.get("date_format", "day-month")
        if date_format in ("day-month", "month-day"):
            _date_format = date_format


def _url_encode(text):
    """Percent-encode a Unicode location query without urllib dependencies."""
    safe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
    out = ""
    for char in text:
        if char in safe:
            out += char
        elif char == " ":
            out += "%20"
        else:
            for value in char.encode("utf-8"):
                out += "%%%02X" % value
    return out


def _start_request(view_manager, url, label, next_state):
    """Start one asynchronous HTTP request and its loading animation."""
    global _http, _loading, _state
    from picoware.system.http import HTTP
    from picoware.gui.loading import Loading

    if _http is None:
        _http = HTTP(chunk_size=4096, thread_manager=view_manager.thread_manager)
    if _loading is None:
        _loading = Loading(view_manager.draw, view_manager.foreground_color, view_manager.background_color)
    else:
        _loading.stop()
    _loading.set_text(label)
    if _http.get_async(url, headers={"User-Agent": "Picoware Forecast/1.0"}, timeout=15):
        _state = next_state
        return True
    _loading.stop()
    view_manager.alert("Could not start request", False)
    return False


def _search(view_manager, query):
    """Resolve a human location query with Open-Meteo's geocoding service."""
    url = ("https://geocoding-api.open-meteo.com/v1/search?name=" + _url_encode(query) +
           "&count=8&language=en&format=json")
    return _start_request(view_manager, url, "Searching...", STATE_SEARCHING)


def _forecast_url(location):
    """Build the selected provider URL from saved WGS84 coordinates."""
    lat = str(location["lat"])
    lon = str(location["lon"])
    if _provider == "7Timer":
        return "https://www.7timer.info/bin/api.pl?lon=%s&lat=%s&product=civil&output=json" % (lon, lat)
    return ("https://api.open-meteo.com/v1/forecast?latitude=" + lat + "&longitude=" + lon +
            "&daily=weather_code,temperature_2m_max,temperature_2m_min," +
            "precipitation_probability_max,wind_speed_10m_max&timezone=auto&forecast_days=16")


def _fetch_forecast(view_manager, location):
    """Remember the selected location and begin downloading its forecast."""
    global _selected_location
    _selected_location = location
    return _start_request(view_manager, _forecast_url(location), "Updating...", STATE_FETCHING)


def _weather_name(code):
    """Convert a WMO weather code into a short PicoCalc-friendly label."""
    if code == 0:
        return "Sunny"
    if code in (1, 2):
        return "Part cloudy"
    if code in (3, 45, 48):
        return "Cloudy"
    if code in (51, 53, 55, 56, 57):
        return "Drizzle"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "Rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow"
    if code in (95, 96, 99):
        return "Storm"
    return "Mixed"


def _is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _add_days(date_text, days):
    """Add a small positive day count without importing datetime."""
    year, month, day = (int(value) for value in date_text.split("-"))
    month_days = (31, 29 if _is_leap(year) else 28, 31, 30, 31, 30,
                  31, 31, 30, 31, 30, 31)
    while days:
        remaining = month_days[month - 1] - day
        if days <= remaining:
            day += days
            break
        days -= remaining + 1
        day = 1
        month += 1
        if month == 13:
            year += 1
            month = 1
            month_days = (31, 29 if _is_leap(year) else 28, 31, 30, 31, 30,
                          31, 31, 30, 31, 30, 31)
    return "%04d-%02d-%02d" % (year, month, day)


def _format_date(date_text):
    """Format an ISO provider date according to the user's selected order."""
    if len(date_text) >= 10 and date_text[4] == "-":
        month, day = date_text[5:7], date_text[8:10]
        return (day + "-" + month) if _date_format == "day-month" else (month + "-" + day)
    return date_text


def _weekday(date_text):
    """Return an English weekday for YYYY-MM-DD without importing datetime."""
    # Sakamoto's Gregorian-calendar algorithm: Sunday is index zero. It keeps
    # the app lightweight and works on MicroPython builds without datetime.
    names = ("Sunday", "Monday", "Tuesday", "Wednesday",
             "Thursday", "Friday", "Saturday")
    offsets = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)
    try:
        year, month, day = (int(value) for value in date_text[:10].split("-"))
        adjusted_year = year - 1 if month < 3 else year
        index = (adjusted_year + adjusted_year // 4 - adjusted_year // 100 +
                 adjusted_year // 400 + offsets[month - 1] + day) % 7
        return names[index]
    except Exception:
        # A provider without a valid ISO date should not break the whole page.
        return ""


def _latin_text(text):
    """Fold common European accented characters into LCD-safe Latin text."""
    # Picoware's bitmap fonts do not contain every Unicode glyph. This explicit
    # map covers common German, Romanian, Romance, Nordic, and Slavic names.
    replacements = {
        "ä": "a", "á": "a", "à": "a", "â": "a", "ã": "a", "å": "a",
        "ă": "a", "ą": "a", "æ": "ae", "Ä": "A", "Á": "A", "À": "A",
        "Â": "A", "Ã": "A", "Å": "A", "Ă": "A", "Ą": "A", "Æ": "AE",
        "ç": "c", "ć": "c", "č": "c", "Ç": "C", "Ć": "C", "Č": "C",
        "ď": "d", "đ": "d", "Ď": "D", "Đ": "D",
        "é": "e", "è": "e", "ê": "e", "ë": "e", "ę": "e", "ě": "e",
        "É": "E", "È": "E", "Ê": "E", "Ë": "E", "Ę": "E", "Ě": "E",
        "í": "i", "ì": "i", "î": "i", "ï": "i", "Í": "I", "Ì": "I",
        "Î": "I", "Ï": "I", "ł": "l", "ľ": "l", "Ł": "L", "Ľ": "L",
        "ñ": "n", "ń": "n", "ň": "n", "Ñ": "N", "Ń": "N", "Ň": "N",
        "ö": "o", "ó": "o", "ò": "o", "ô": "o", "õ": "o", "ø": "o",
        "œ": "oe", "Ö": "O", "Ó": "O", "Ò": "O", "Ô": "O", "Õ": "O",
        "Ø": "O", "Œ": "OE", "ř": "r", "Ř": "R",
        "ś": "s", "š": "s", "ș": "s", "ş": "s", "ß": "ss", "Ś": "S",
        "Š": "S", "Ș": "S", "Ş": "S", "ť": "t", "ț": "t", "ţ": "t",
        "Ť": "T", "Ț": "T", "Ţ": "T", "ü": "u", "ú": "u", "ù": "u",
        "û": "u", "Ü": "U", "Ú": "U", "Ù": "U", "Û": "U",
        "ý": "y", "ÿ": "y", "Ý": "Y", "Ÿ": "Y", "ž": "z", "ź": "z",
        "ż": "z", "Ž": "Z", "Ź": "Z", "Ż": "Z",
    }
    return "".join(replacements.get(character, character) for character in text)


def _fit_text(draw, text, max_width, font_size=0):
    """Truncate text by rendered pixel width and add an ellipsis if needed."""
    if draw.len(text, font_size) <= max_width:
        return text
    suffix = "..."
    available = max_width - draw.len(suffix, font_size)
    end = len(text)
    while end > 0 and draw.len(text[:end], font_size) > available:
        end -= 1
    return text[:end].rstrip() + suffix


def _display_temp(celsius):
    """Convert canonical Celsius data into the configured display unit."""
    return round(celsius * 9 / 5 + 32) if _temperature_unit == "Fahrenheit" else round(celsius)


def _display_wind(kmh):
    """Convert canonical km/h wind data into the configured display unit."""
    if _wind_unit == "m/s":
        return round(kmh / 3.6, 1)
    if _wind_unit == "knots":
        return round(kmh / 1.852, 1)
    return round(kmh)


def _parse_open_meteo(data):
    """Normalize Open-Meteo daily arrays into compact per-day dictionaries."""
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    high = daily.get("temperature_2m_max", [])
    low = daily.get("temperature_2m_min", [])
    rain = daily.get("precipitation_probability_max", [])
    wind = daily.get("wind_speed_10m_max", [])
    codes = daily.get("weather_code", [])
    result = []
    count = min(len(dates), len(high), len(low), len(codes))
    for i in range(count):
        result.append({
            "date": dates[i], "high": high[i], "low": low[i],
            "rain": round(rain[i]) if i < len(rain) and rain[i] is not None else 0,
            "wind": round(wind[i]) if i < len(wind) else 0,
            "weather": _weather_name(codes[i]),
            # Open-Meteo daily data starts with the local current date.
            "today": i == 0,
        })
    return result


def _parse_7timer(data):
    """Group 7Timer three-hour samples and normalize them into daily data."""
    series = data.get("dataseries", [])
    result = []
    init = str(data.get("init", ""))
    base_date = (init[0:4] + "-" + init[4:6] + "-" + init[6:8]) if len(init) >= 8 else ""
    init_hour = int(init[8:10]) if len(init) >= 10 else 0
    # 7Timer reports Beaufort-like categories; use representative km/h values.
    wind_kmh = (0, 3, 8, 15, 24, 34, 44, 55, 68, 82)
    # 7Timer steps are three hours. Group each eight steps as one compact day.
    for start in range(0, len(series), 8):
        group = series[start:start + 8]
        if not group:
            break
        temps = [item.get("temp2m", 0) for item in group]
        winds = []
        for item in group:
            category = item.get("wind10m", {}).get("speed", 0)
            winds.append(wind_kmh[category] if 0 <= category < len(wind_kmh) else 82)
        names = [item.get("weather", "cloudy") for item in group]
        rainy = sum(1 for name in names if "rain" in name or "shower" in name or "storm" in name)
        name = names[len(names) // 2]
        if "clear" in name:
            weather = "Sunny"
        elif "rain" in name or "shower" in name:
            weather = "Rain"
        elif "snow" in name:
            weather = "Snow"
        elif "storm" in name:
            weather = "Storm"
        elif "cloud" in name:
            weather = "Cloudy"
        else:
            weather = "Mixed"
        group_date = (_add_days(base_date,
                               (init_hour + group[0].get("timepoint", start * 3)) // 24)
                      if base_date else "Day " + str(len(result) + 1))
        result.append({
            "date": group_date,
            "high": max(temps), "low": min(temps),
            "rain": round(rainy * 100 / len(group)), "wind": max(winds), "weather": weather,
            # The downloaded initialization date is 7Timer's current date.
            "today": bool(base_date) and group_date == base_date,
        })
    return result


def _request_done(view_manager, kind):
    """Poll and parse a completed search or forecast request without blocking."""
    global _search_results, _days
    if not _http.is_request_complete():
        _loading.animate(http=_http)
        return False
    _loading.stop()
    try:
        if not _http.is_successful or _http.response is None:
            raise RuntimeError(_http.error or "Network error")
        data = _http.response.json()
        if kind == "search":
            raw = data.get("results", [])
            _search_results = []
            for item in raw:
                name = item.get("name", "Unknown")
                area = item.get("admin1") or item.get("country") or ""
                label = name + (", " + area if area and area != name else "")
                # Normalize immediately so search results, saved names, and the
                # forecast header all use the same LCD-supported characters.
                label = _latin_text(label)
                _search_results.append({"name": label, "lat": item["latitude"], "lon": item["longitude"]})
            if not _search_results:
                raise RuntimeError("No locations found")
            _set_menu(view_manager, "Search results", [x["name"] for x in _search_results], STATE_RESULTS)
        else:
            _days = _parse_7timer(data) if _provider == "7Timer" else _parse_open_meteo(data)
            if not _days:
                raise RuntimeError("Empty forecast")
            _draw_forecast(view_manager)
        return True
    except Exception as exc:
        view_manager.log("[Forecast] " + str(exc), 2)
        view_manager.alert("Forecast error: " + str(exc), False)
        _show_saved(view_manager) if kind == "forecast" else _show_manage(view_manager)
        return True


def _draw_weather_icon(draw, x, y, weather, rain_color, cloud_color, sun_color):
    """Draw the condition symbol centered on its day's vertical axis."""
    from picoware.system.vector import Vector
    if weather == "Sunny":
        # A filled disc is the compact sunny/clear-sky symbol.
        draw.fill_circle(Vector(x, y), 7, sun_color)
    else:
        # Two overlapping circles and a base form the cloud silhouette.
        draw.fill_circle(Vector(x - 5, y + 2), 6, cloud_color)
        draw.fill_circle(Vector(x + 3, y), 8, cloud_color)
        draw.fill_rectangle(Vector(x - 10, y + 2), Vector(21, 8), cloud_color)
        if weather in ("Rain", "Storm", "Drizzle"):
            # Two short diagonal strokes below the cloud indicate precipitation.
            draw.line_custom(Vector(x - 5, y + 13), Vector(x - 8, y + 20), rain_color)
            draw.line_custom(Vector(x + 5, y + 13), Vector(x + 2, y + 20), rain_color)


def _is_dark(color):
    # Approximate RGB565 luminance; supports custom Picoware themes too.
    red, green, blue = (color >> 11) & 31, (color >> 5) & 63, color & 31
    return red * 2 + green * 3 + blue < 126


def _column_center(width, index):
    """Center of one of the four forecast columns."""
    return ((index * 2 + 1) * width) // (PAGE_DAYS * 2)


def _center_text(draw, center, y, text, color, font_size=0, bold=False):
    """Draw text around a shared column center, optionally with faux bold."""
    x = center - draw.len(text, font_size) // 2
    draw._text(x, y, text, color, font_size)
    if bold:
        # Picoware has no separate bold face; a one-pixel duplicate thickens it.
        draw._text(x + 1, y, text, color, font_size)


def _thick_line(draw, start, end, color):
    """Draw a clearly visible three-pixel temperature segment."""
    from picoware.system.vector import Vector
    draw.line_custom(Vector(start.x, start.y - 1), Vector(end.x, end.y - 1), color)
    draw.line_custom(start, end, color)
    draw.line_custom(Vector(start.x, start.y + 1), Vector(end.x, end.y + 1), color)


def _low_label_y(point_y, graph_bottom):
    """Keep a low-temperature number clear of the bottom frame/date row."""
    return point_y - 14 if point_y > graph_bottom - 18 else point_y + 5


def _high_label_y(point_y, graph_top):
    """Keep a high-temperature number clear of the status text above."""
    # This mirrors _low_label_y: labels normally sit above a high point, but
    # flip below it inside the top 18 pixels of the graph.
    return point_y + 5 if point_y < graph_top + 18 else point_y - 13


def _draw_forecast(view_manager):
    """Render the complete forecast page and all of its visual elements."""
    global _state
    from picoware.system.colors import (TFT_BLUE, TFT_CYAN, TFT_DARKGREEN,
                                         TFT_DARKGREY, TFT_GREEN, TFT_LIGHTGREY,
                                         TFT_ORANGE, TFT_RED, TFT_YELLOW)
    from picoware.system.vector import Vector

    draw = view_manager.draw
    # Clear the old page before selecting accessible theme-dependent colors.
    draw.erase()
    dark = _is_dark(view_manager.background_color)
    cool_color = TFT_CYAN if dark else TFT_BLUE
    wind_color = TFT_GREEN if dark else TFT_DARKGREEN
    warm_color = TFT_YELLOW if dark else TFT_ORANGE
    cloud_color = TFT_LIGHTGREY if dark else TFT_DARKGREY
    width, height = draw.size.x, draw.size.y

    # Header: fold unsupported accents, then truncate by actual rendered width.
    # The smaller font and ellipsis keep even long administrative names on one
    # line rather than allowing them to cover the status row.
    title = _fit_text(draw, _latin_text(_selected_location["name"]),
                      width - 16, TITLE_FONT)
    draw._text(8, TITLE_Y, title, view_manager.foreground_color, TITLE_FONT)

    # Status sits lower and closer to the graph, leaving a clean gap below the
    # location. It identifies source, temperature unit, and the visible page.
    unit = "F" if _temperature_unit == "Fahrenheit" else "C"
    draw._text(8, STATUS_Y, _provider + "  " + unit + "  " + str(_page + 1) + "/" + str((len(_days) + PAGE_DAYS - 1) // PAGE_DAYS), cool_color)

    # Graph frame: equal ten-pixel left/right margins and fixed vertical bounds.
    shown = _days[_page * PAGE_DAYS:(_page + 1) * PAGE_DAYS]
    # Equal ten-pixel margins. Points use the exact same column centers as all
    # weather details below, keeping every day's information vertically aligned.
    graph_left, graph_top = 10, GRAPH_TOP
    graph_right, graph_bottom = width - 10, GRAPH_BOTTOM

    # Establish a shared scale covering every high and low on this page.
    all_temps = []
    for day in shown:
        all_temps.extend((_display_temp(day["low"]), _display_temp(day["high"])))
    t_min, t_max = min(all_temps), max(all_temps)
    if t_max == t_min:
        t_max += 1
    draw.rect(Vector(graph_left, graph_top), Vector(graph_right - graph_left, graph_bottom - graph_top), TFT_DARKGREY)

    # Curves: red is the daily high; blue/cyan is the daily low. Both use
    # three-pixel segments, round points, and a numeric label at every point.
    previous_high = None
    previous_low = None
    for i, day in enumerate(shown):
        high, low = _display_temp(day["high"]), _display_temp(day["low"])
        x = _column_center(width, i)
        yh = graph_bottom - int((high - t_min) * (graph_bottom - graph_top) / (t_max - t_min))
        yl = graph_bottom - int((low - t_min) * (graph_bottom - graph_top) / (t_max - t_min))
        if previous_high:
            _thick_line(draw, previous_high, Vector(x, yh), TFT_RED)
            _thick_line(draw, previous_low, Vector(x, yl), cool_color)
        draw.fill_circle(Vector(x, yh), 3, TFT_RED)
        draw.fill_circle(Vector(x, yl), 3, cool_color)
        # Near the top border, put the high value below its point. This avoids
        # collisions with the source/unit/page text immediately above the plot.
        high_label_y = _high_label_y(yh, graph_top)
        _center_text(draw, x, high_label_y, str(high), TFT_RED)
        # Near the bottom border, put the low value above its point. This keeps
        # cold/minimum values away from the frame and the date immediately below.
        low_label_y = _low_label_y(yl, graph_bottom)
        _center_text(draw, x, low_label_y, str(low), cool_color)
        previous_high, previous_low = Vector(x, yh), Vector(x, yl)

    # Daily detail columns. Every row shares the same x center as its two graph
    # points: weekday, date, icon, condition, rain probability, then wind.
    for i, day in enumerate(shown):
        center = _column_center(width, i)
        weekday = _weekday(day["date"])
        date = _format_date(day["date"])
        condition = day["weather"][:10]
        rain = "Rain " + str(day["rain"]) + "%"
        wind_suffix = "k/h" if _wind_unit == "km/h" else ("kt" if _wind_unit == "knots" else "m/s")
        wind = "W:" + str(_display_wind(day["wind"])) + wind_suffix

        # Weekends use thick red text. Weekdays retain the active theme color.
        weekend = weekday in ("Saturday", "Sunday")
        calendar_color = TFT_RED if weekend else view_manager.foreground_color
        _center_text(draw, center, WEEKDAY_Y, weekday, calendar_color,
                     bold=weekend)
        _center_text(draw, center, DATE_Y, date, calendar_color, bold=weekend)

        # The provider marks the current local day. A red outline groups its
        # weekday and date without changing weekday/weekend text semantics.
        if day.get("today", False):
            box_width = width // PAGE_DAYS - 6
            draw.rect(Vector(center - box_width // 2, WEEKDAY_Y - 3),
                      Vector(box_width, DATE_Y - WEEKDAY_Y + 15), TFT_RED)

        # Weather symbol and metrics continue down the same vertical axis.
        _draw_weather_icon(draw, center, ICON_Y, day["weather"], cool_color, cloud_color, warm_color)
        _center_text(draw, center, CONDITION_Y, condition, warm_color)
        _center_text(draw, center, RAIN_Y, rain, cool_color)
        _center_text(draw, center, WIND_Y, wind, wind_color)

    # Footer documents page navigation, manual refresh, and returning to menus.
    draw._text(6, height - 14, "LEFT/RIGHT pan   CENTER refresh   BACK", view_manager.foreground_color)
    draw.swap()
    _state = STATE_FORECAST


def _keyboard_saved(text):
    global _pending_query
    _pending_query = text.strip()


def _start_input(view_manager):
    global _state, _input_started, _pending_query
    _pending_query = ""
    kb = view_manager.keyboard
    kb.set_save_callback(_keyboard_saved)
    kb.title = "Search town or city"
    kb.response = ""
    view_manager.input_manager.reset()
    view_manager.draw.clear(color=view_manager.background_color)
    kb.run(force=True)
    _input_started = True
    _state = STATE_INPUT


def start(view_manager):
    """Load saved locations and open the Forecast main menu."""
    _load(view_manager)
    _show_main(view_manager)
    return True


def run(view_manager):
    """Handle one non-blocking UI/network update."""
    global _provider, _temperature_unit, _wind_unit, _date_format
    global _input_started, _page
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP

    if _state == STATE_SEARCHING:
        _request_done(view_manager, "search")
        return
    if _state == STATE_FETCHING:
        _request_done(view_manager, "forecast")
        return
    if _state == STATE_INPUT:
        kb = view_manager.keyboard
        alive = kb.run()
        if not alive:
            kb.reset()
            _input_started = False
            _show_manage(view_manager)
        elif kb.is_save_pressed:
            query = _pending_query
            kb.reset()
            _input_started = False
            if query:
                _search(view_manager, query)
            else:
                _show_manage(view_manager)
        return

    button = view_manager.button
    if button == BUTTON_BACK:
        if _state == STATE_MAIN:
            view_manager.back()
        else:
            _show_main(view_manager)
        return
    if _state in (STATE_MAIN, STATE_SAVED, STATE_MANAGE, STATE_RESULTS, STATE_SETTINGS):
        if button == BUTTON_UP:
            _menu.scroll_up()
        elif button == BUTTON_DOWN:
            _menu.scroll_down()
        elif button == BUTTON_CENTER:
            index = _menu.selected_index
            if _state == STATE_MAIN:
                if index == 0:
                    _show_saved(view_manager)
                elif index == 1:
                    _show_manage(view_manager)
                else:
                    _show_settings(view_manager)
            elif _state == STATE_SAVED:
                if _locations and index < len(_locations):
                    _page = 0
                    _fetch_forecast(view_manager, _locations[index])
            elif _state == STATE_MANAGE:
                if index == 0:
                    _start_input(view_manager)
                else:
                    loc_index = index - 1
                    if 0 <= loc_index < len(_locations):
                        _locations.pop(loc_index)
                        _save(view_manager)
                        _show_manage(view_manager)
            elif _state == STATE_SETTINGS:
                if index == 0:
                    _provider = "7Timer" if _provider == "Open-Meteo" else "Open-Meteo"
                elif index == 1:
                    _temperature_unit = ("Fahrenheit" if _temperature_unit == "Celsius"
                                         else "Celsius")
                elif index == 2:
                    units = ("km/h", "m/s", "knots")
                    _wind_unit = units[(units.index(_wind_unit) + 1) % len(units)]
                elif index == 3:
                    _date_format = ("month-day" if _date_format == "day-month"
                                    else "day-month")
                _save(view_manager)
                _show_settings(view_manager)
            elif _state == STATE_RESULTS and index < len(_search_results):
                chosen = _search_results[index]
                if not any(x["name"] == chosen["name"] for x in _locations):
                    if len(_locations) >= MAX_LOCATIONS:
                        view_manager.alert("Maximum 12 locations", False)
                    else:
                        _locations.append(chosen)
                        _save(view_manager)
                _page = 0
                _fetch_forecast(view_manager, chosen)
        return
    if _state == STATE_FORECAST:
        pages = (len(_days) + PAGE_DAYS - 1) // PAGE_DAYS
        if button == BUTTON_LEFT and _page > 0:
            _page -= 1
            _draw_forecast(view_manager)
        elif button == BUTTON_RIGHT and _page + 1 < pages:
            _page += 1
            _draw_forecast(view_manager)
        elif button == BUTTON_CENTER:
            _fetch_forecast(view_manager, _selected_location)


def stop(view_manager):
    """Release the sizeable UI, response, and forecast objects."""
    global _menu, _http, _loading, _search_results, _days, _selected_location
    if _loading:
        _loading.stop()
    if _http:
        _http.close()
    _menu = None
    _http = None
    _loading = None
    _search_results = []
    _days = []
    _selected_location = None
    from gc import collect
    collect()
