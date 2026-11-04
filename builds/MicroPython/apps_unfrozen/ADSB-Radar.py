# 
# ADSB-Radar.py 
# 
# Picoware ADS-B Radar v1 
# 
# Controls 
# -------- 
# UP        Range + 
# DOWN      Range - 
# RIGHT     Setup 
# LEFT      Exit 
# 

import math 

from json import loads 
from json import dumps 

from micropython import const 

try: 
  from utime import ticks_ms 
except: 
  from supervisor import ticks_ms 

############################################################################## 
# STATES 
############################################################################## 

STATE_RADAR = const(0) 
STATE_EDIT_LAT = const(1) 
STATE_EDIT_LON = const(2) 
 
############################################################################## 
# CONFIG 
############################################################################## 

CONFIG_FILE = "picoware/adsb/config.json" 

DEFAULT_LAT = 51.2574 
DEFAULT_LON = 3.0021 

DEFAULT_RANGE = 25 

############################################################################## 
# RADAR GEOMETRY 
############################################################################## 

RADAR_X = 160 
RADAR_Y = 160 
RADAR_RADIUS = 125 

############################################################################## 
# FETCH 
############################################################################## 

FETCH_INTERVAL = 10000 

############################################################################## 
# GLOBALS 
############################################################################## 

_state = STATE_RADAR 

_http = None 

_radar_lat = DEFAULT_LAT 
_radar_lon = DEFAULT_LON 
_radar_range = DEFAULT_RANGE 

_aircraft = [] 

_last_fetch = 0 

_download_running = False 

_status = "Starting" 


############################################################################## 
# HELPERS 
############################################################################## 

def load_config(view_manager): 

    global _radar_lat 
    global _radar_lon 
    global _radar_range 
    global _status 

    storage = view_manager.storage 

    try: 
        if storage.exists(CONFIG_FILE): 
            cfg = loads(storage.read(CONFIG_FILE)) 
            _radar_lat = cfg.get("lat", DEFAULT_LAT)
            _radar_lon = cfg.get("lon", DEFAULT_LON) 
            _radar_range = cfg.get("range", DEFAULT_RANGE) 
    except Exception as e: 
        _status = "ERROR: " + e
        pass 

def save_config(view_manager): 

    storage = view_manager.storage 

    storage.mkdir("picoware/adsb") 

    storage.write(CONFIG_FILE, 
        dumps( 
            { 
                "lat": _radar_lat, 
                "lon": _radar_lon, 
                "range": _radar_range, 
            } 
        ), 
    ) 


############################################################################## 
# GEO 
############################################################################## 

def haversine(lat1, lon1, lat2, lon2): 

    dlat = math.radians(lat2 - lat1) 
    dlon = math.radians(lon2 - lon1) 
    a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2) 

    return (6371 * 2 * math.atan2(math.sqrt(a),math.sqrt(1 - a))) 

def bearing(lat1, lon1, lat2, lon2): 

    dlon = math.radians(lon2 - lon1) 

    y = (math.sin(dlon) * math.cos(math.radians(lat2))) 
    x = (math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)) 

    return (math.degrees(math.atan2(y, x)) + 360) % 360 


############################################################################## 
# SETUP 
############################################################################## 

def edit_latitude(view_manager): 

    global _state 

    kb = view_manager.keyboard 
    kb.reset() 
    kb.title = "Latitude" 
    kb.response = str(_radar_lat) 
    kb.run(force=True) 

    _state = STATE_EDIT_LAT 

def edit_longitude(view_manager): 

    global _state 

    kb = view_manager.keyboard 
    kb.reset() 
    kb.title = "Longitude" 
    kb.response = str(_radar_lon) 
    kb.run(force=True) 

    _state = STATE_EDIT_LON 

 
############################################################################## 
# ADSB 
############################################################################## 

def build_url(): 

    nm = (_radar_range / 1.852) 

    return ("https://opendata.adsb.fi/api/v3/lat/" + str(round(_radar_lat, 5)) + "/lon/" + str(round(_radar_lon, 5)) + "/dist/" + str(round(nm, 1))) 

def start_fetch(view_manager):
    global _http
    global _download_running
    global _status

    if _download_running:
        return

    try:
        from picoware.system.http import HTTP

        url = build_url()
        _status = "Connecting..."

        if not _http:
            _http = HTTP()

        _http.close()

        started = _http.get_async(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Picoware-ADSB"
            },
            timeout=15.0
        )

        if started:
            _download_running = True
            _status = "Downloading..."
        else:
            _download_running = False
            error = _http.error if _http else ""
            _status = "HTTP start failed"
            if error:
                _status = str(error)

    except Exception as e:
        _download_running = False
        _status = "Fetch: " + str(e)

def parse_aircraft():
    global _aircraft
    global _status

    if not _http:
        _status = "No HTTP client"
        return

    try:
        response = _http.response

        if response is None:
            _status = "Empty response"
            return

        if response.status_code < 200 or response.status_code >= 300:
            _status = "HTTP " + str(response.status_code)
            return

        text = response.text

        if not text:
            _status = "Empty response body"
            return

        data = loads(text)
        planes = []

        for ac in data.get("ac", []):
            lat = ac.get("lat")
            lon = ac.get("lon")

            if lat is None or lon is None:
                continue

            dist = haversine(_radar_lat, _radar_lon, lat, lon)

            if dist > _radar_range:
                continue

            alt = ac.get("alt_baro", 0)

            if not isinstance(alt, (int, float)):
                alt = 0

            flight = (ac.get("flight") or "").strip()

            planes.append(
                {
                    "hex": ac.get("hex", ""),
                    "flight": str(flight).strip(),
                    "distance": dist,
                    "bearing": bearing(
                        _radar_lat,
                        _radar_lon,
                        lat,
                        lon
                    ),
                    "alt": alt
                }
            )

        _aircraft = planes
        _status = str(len(planes)) + " aircraft"

    except Exception as e:
        _aircraft = []
        _status = "Parse: " + str(e)
 

############################################################################## 
# DRAW 
############################################################################## 

def radar_xy(bearing_deg, distance): 

    radius = (distance / _radar_range ) * RADAR_RADIUS 
    a = math.radians(bearing_deg - 90) 
    x = int(RADAR_X + math.cos(a) * radius) 
    y = int(RADAR_Y + math.sin(a) * radius) 

    return x, y 

def altitude_color(alt): 

    from picoware.system.colors import (TFT_GREEN, TFT_YELLOW, TFT_ORANGE, TFT_RED) 

    if alt < 5000: 
        return TFT_GREEN 

    if alt < 15000: 
        return TFT_YELLOW 

    if alt < 30000: 
        return TFT_ORANGE 

    return TFT_RED 

def draw_radar(view_manager): 

    from picoware.system.colors import (TFT_BLACK, TFT_GREEN, TFT_WHITE, TFT_CYAN) 

    draw = view_manager.draw 
    draw.fill_screen(TFT_BLACK) 
    draw._circle(RADAR_X, RADAR_Y, RADAR_RADIUS, TFT_GREEN) 
    draw._circle(RADAR_X, RADAR_Y, 95, TFT_GREEN) 
    draw._circle(RADAR_X, RADAR_Y, 65, TFT_GREEN) 
    draw._circle(RADAR_X, RADAR_Y, 35, TFT_GREEN) 
    draw._line(RADAR_X - RADAR_RADIUS, RADAR_Y, RADAR_X + RADAR_RADIUS, RADAR_Y, TFT_GREEN) 
    draw._line(RADAR_X, RADAR_Y - RADAR_RADIUS, RADAR_X, RADAR_Y + RADAR_RADIUS, TFT_GREEN) 
    draw._text(156, 20, "N", TFT_GREEN) 
    draw._text(156, 290, "S", TFT_GREEN) 
    draw._text(20, 156, "W", TFT_GREEN) 
    draw._text(290, 156, "E", TFT_GREEN) 

    for plane in _aircraft: 
        if plane["distance"] <= _radar_range:
            x, y = radar_xy(plane["bearing"], plane["distance"]) 
            draw._fill_circle(x, y, 4, altitude_color(plane["alt"])) 
            label = (plane["flight"] or plane["hex"]) 
            draw._text(x + 5, y - 5, label[:8], TFT_WHITE) 

    draw._text(5, 5, _status, TFT_WHITE) 
    draw._text(230, 5, str(_radar_range) + "km", TFT_CYAN) 
    draw.swap() 
 

############################################################################## 
# APP 
############################################################################## 

def start(view_manager):
    global _status
    global _last_fetch

    wifi = view_manager.wifi

    if not wifi:
        _status = "No WiFi"
        return False

    if not wifi.is_connected():
        _status = "Connecting WiFi"
        from picoware.applications.wifi.utils import connect_to_saved_wifi
        connect_to_saved_wifi(view_manager)
        return False

    load_config(view_manager)

    _status = "Ready"
    _last_fetch = ticks_ms() - FETCH_INTERVAL - 1

    return True


def run(view_manager): 

    global _state 
    global _radar_range 
    global _last_fetch 
    global _download_running 
    global _radar_lat 
    global _radar_lon 
    global _status 

    from picoware.system.buttons import ( 
        BUTTON_UP, 
        BUTTON_DOWN, 
        BUTTON_RIGHT, 
        BUTTON_LEFT 
    ) 

    inp = view_manager.input_manager 
    button = inp.button 

    if button == BUTTON_LEFT: 
        inp.reset() 
        view_manager.back() 
        return 

    if _state == STATE_RADAR: 
        if button == BUTTON_UP: 
            _radar_range += 5 
            save_config(view_manager) 
            inp.reset() 
        elif button == BUTTON_DOWN: 
            _radar_range = max(5, _radar_range - 5) 
            save_config(view_manager) 
            inp.reset() 
        elif button == BUTTON_RIGHT: 
            inp.reset() 
            edit_latitude(view_manager) 
        now = ticks_ms() 
        if (now - _last_fetch > FETCH_INTERVAL): 
            _last_fetch = now 
            try:
                start_fetch(view_manager)
            except Exception as e:
               _status = str(e) 
        if _download_running:
            if _http is None:
                _download_running = False
                _status = "No HTTP client"
            elif _http.is_request_complete():
                error = _http.error
                response = _http.response
                _download_running = False
                if error:
                    _status = "HTTP: " + str(error)
                elif response is None:
                    _status = "No HTTP response"
                else:
                    _status = "Parsing..."
                    parse_aircraft()
        draw_radar(view_manager) 
    elif _state == STATE_EDIT_LAT: 
        kb = view_manager.keyboard 
        if kb.is_finished: 
            try: 
                _radar_lat = float(kb.response) 
            except: 
                pass 
            kb.reset() 
            edit_longitude(view_manager) 
        else: 
            kb.run() 
    elif _state == STATE_EDIT_LON: 
        kb = view_manager.keyboard 
        if kb.is_finished: 
            try: 
                _radar_lon = float(kb.response) 
            except: 
                pass 
            save_config(view_manager) 
            kb.reset() 
            _state = STATE_RADAR 
        else: 
            kb.run() 

def stop(view_manager): 

    global _http 

    if _http: 
        try: 
            _http.close() 
        except: 
            pass 

    view_manager.keyboard.reset() 

    from gc import collect 
    collect() 