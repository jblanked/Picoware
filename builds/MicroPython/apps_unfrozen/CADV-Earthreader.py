"""M5Stack Unit Earth with Cardputer shared ADC or MicroPython ADC.

White: GPIO1 analog; yellow: GPIO2 digital; red: 5V; black: GND.
Cardputer requires cardputer_battery.read_grove_adc (shares battery ADC1).
Other boards use machine.ADC. Create picoware/settings/earth-pins.json:
{"board": <BOARD_ID>, "analog": <ADC GPIO>, "digital": <GPIO or null>}
Use available, ADC-capable pins and board-compatible sensor voltages.
ESP32 uses ATTN_11DB; read_u16 is scaled to 0..4095 for calibration.
Generic calibration is stored per board and pin pair; digital is optional.
The keyboard configuration UI requires a display of at least 240x135.
C toggles configuration; Back returns to the moisture display.
D + Enter saves dry (0%); W + Enter saves wet (100%); R + Enter resets.
A starts guided stable-reading calibration.
M opens manual dry/wet ADC entry; Tab selects a field, Enter saves both.
The displayed percentage averages eight half-second measurements.
Calibration persists on SD. Percentage is relative, not water content.
The sensor's trimmer sets the digital threshold. Probes are not intended
for prolonged immersion: https://docs.m5stack.com/en/unit/Unit_Earth
"""

_storage = None
_sensor = None
_adc = None
_cardputer = False
_digital = None
_last = None
_latest = None
_readings = []
_error = None
_dry = None
_wet = None
_pending = None
_notice = ""
_configure = False
_manual = None
_auto = None
_field = 0
_replace = True
CONFIG = "picoware/settings/earth.json"
INTERVAL_MS = 500
SMOOTH_SAMPLES = 8


def _sample():
    global _latest, _error, _pending
    try:
        raw = sum(_sensor() for _ in range(8)) // 8
        digital = _digital.value() if _digital is not None else None
        _latest = (raw, digital)
        # Cardputer ADV has external Grove pull-ups. An open cable and
        # very dry soil can both saturate the ADC: report ambiguity.
        _error = "Check sensor" if _cardputer and raw >= 4090 and digital else None
        if _error:
            _readings.clear()
        else:
            _readings.append(raw)
            if len(_readings) > SMOOTH_SAMPLES:
                _readings.pop(0)
    except (OSError, RuntimeError) as exc:
        _readings.clear()
        _latest = None
        _pending = None
        _error = str(exc)


def _valid(value):
    return value is None or (type(value) is int and 0 <= value <= 4095)


def _load_calibration():
    global _dry, _wet, _notice
    import json
    _dry = _wet = None
    if not _storage.exists(CONFIG):
        return
    try:
        data = json.loads(_storage.read(CONFIG))
        dry, wet = data.get("dry"), data.get("wet")
        if not _valid(dry) or not _valid(wet):
            raise ValueError("Invalid calibration")
        if dry is not None and wet is not None and dry - wet < 100:
            raise ValueError("Invalid calibration span")
        _dry, _wet = dry, wet
    except (OSError, ValueError, TypeError, AttributeError):
        _notice = "Calibration unreadable"


def _percent(raw):
    if _dry is None or _wet is None or _dry - _wet < 100:
        return None
    return max(0, min(100, (( _dry - raw) * 100 + (_dry - _wet) // 2) // (_dry - _wet)))


def _display_percent():
    # Smooth only the display. Calibration uses fresh ADC measurements.
    if not _readings or _latest is None or _error:
        return None
    average = (sum(_readings) + len(_readings)//2)//len(_readings)
    return _percent(average)


def _save_pending():
    global _dry, _wet, _pending, _notice
    import json
    kind, value = _pending
    dry, wet = _dry, _wet
    if kind == "reset":
        dry = wet = None
    elif kind == "pair":
        dry, wet = value
    elif kind == "dry":
        dry = value
    else:
        wet = value
    _pending = None
    if not _valid(dry) or not _valid(wet):
        _notice = "ADC must be 0..4095"
        return False
    if dry is not None and wet is not None and dry - wet < 100:
        _notice = "D%d W%d: gap < 100" % (dry, wet)
        return False
    try:
        payload = json.dumps({"dry": dry, "wet": wet})
        temp = CONFIG + ".tmp"
        assert _storage.write(temp, payload)
        assert _storage.read(temp) == payload
        # Keep the last saved calibration as a recovery copy.
        if _storage.exists(CONFIG):
            backup = CONFIG + ".bak"
            if _storage.exists(backup):
                assert _storage.remove(backup)
            assert _storage.copy(CONFIG, backup)
            assert _storage.remove(CONFIG)
        assert _storage.rename(temp, CONFIG)
        _dry, _wet = dry, wet
        _notice = "Calibration saved"
        return True
    except (OSError, RuntimeError, AssertionError):
        _notice = "Save failed; try again"
        return False


# Compact 5x7 glyphs rendered large without changing shared display state.
_GLYPHS = {
    "0": (14,17,19,21,25,17,14), "1": (4,12,4,4,4,4,14),
    "2": (14,17,1,2,4,8,31), "3": (30,1,1,14,1,1,30),
    "4": (2,6,10,18,31,2,2), "5": (31,16,16,30,1,1,30),
    "6": (14,16,16,30,17,17,14), "7": (31,1,2,4,8,8,8),
    "8": (14,17,17,14,17,17,14), "9": (14,17,17,15,1,1,14),
    "%": (25,26,2,4,8,11,19), "-": (0,0,0,31,0,0,0),
}


def _border_color(pct):
    if _latest is None or _error:
        return 0xF800
    if pct is None:
        return 0xFFFF
    if pct < 30:
        return 0xF800
    if pct < 60:
        return 0xFFE0
    return 0x07E0


def _render_main(draw):
    width, height = int(draw.size.x), int(draw.size.y)
    pct = _display_percent()
    border = _border_color(pct)
    # Two-pixel outline with straight 45-degree clipped corners.
    for inset in (5, 6):
        left, top, right, bottom = inset, inset, width-1-inset, height-1-inset
        clip = 12
        points = ((left+clip,top),(right-clip,top),(right,top+clip),
                  (right,bottom-clip),(right-clip,bottom),(left+clip,bottom),
                  (left,bottom-clip),(left,top+clip))
        for i in range(8):
            a, b = points[i], points[(i+1)%8]
            draw._line(a[0],a[1],b[0],b[1],border)
    draw._text(20, 16, "Earth moisture:", 0xFFFF)
    draw._text(20, height-29, "C: configure", 0xFFFF)
    if _latest is None or _error:
        if _latest is None:
            title, detail = "Sensor read failed", "Check Grove cable"
        else:
            title, detail = "Check sensor", "Unplugged or very dry"
        draw._text((width-len(title)*8)//2, 53, title, 0xFFE0)
        draw._text((width-len(detail)*8)//2, 73, detail, 0xFFFF)
        return
    label = "--%" if pct is None else "%d%%" % pct
    scale = min(6, (width-40)//(len(label)*6-1), (height-68)//7)
    x, y = (width-(len(label)*6-1)*scale)//2, (height-7*scale)//2
    for char in label:
        for row, bits in enumerate(_GLYPHS[char]):
            for col in range(5):
                if bits & (1 << (4-col)):
                    draw._fill_rectangle(x+col*scale,y+row*scale,scale,scale,0xFFFF)
        x += 6*scale
    if pct is None:
        missing = "Set dry + wet" if _dry is None and _wet is None else ("Set dry reference" if _dry is None else "Set wet reference")
        draw._text(20, 91, missing, 0xFFE0)


def _manual_key(button):
    global _manual, _field, _replace, _pending, _notice
    from picoware.system.buttons import (
        BUTTON_0, BUTTON_9, BUTTON_TAB, BUTTON_UP, BUTTON_DOWN,
        BUTTON_D, BUTTON_W, BUTTON_BACKSPACE, BUTTON_DELETE,
        BUTTON_BACK, BUTTON_ESCAPE, BUTTON_LEFT, BUTTON_CENTER, BUTTON_ENTER,
    )
    if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_LEFT):
        _manual = None
        _notice = "Manual edit cancelled"
    elif button in (BUTTON_TAB, BUTTON_UP, BUTTON_DOWN, BUTTON_D, BUTTON_W):
        _field = 0 if button == BUTTON_D else (1 if button == BUTTON_W else 1-_field)
        _replace = True
        _notice = ""
    elif BUTTON_0 <= button <= BUTTON_9:
        value = "" if _replace else _manual[_field]
        if len(value) < 4:
            _manual[_field] = value + str(button-BUTTON_0)
        _replace = False
        _notice = ""
    elif button in (BUTTON_BACKSPACE, BUTTON_DELETE):
        _manual[_field] = _manual[_field][:-1]
        _replace = False
        _notice = ""
    elif button in (BUTTON_CENTER, BUTTON_ENTER):
        if not all(_manual):
            _notice = "Enter both ADC values"
        else:
            _pending = ("pair", (int(_manual[0]), int(_manual[1])))
            if _save_pending():
                _manual = None


def _auto_begin():
    global _auto
    _auto = {"stage": "dry_ready", "samples": [], "dry": None,
             "wet": None, "count": 0, "message": ""}


def _auto_tick():
    # Called every 500 ms: require 20 consecutive samples (10 seconds)
    # within 40 ADC counts. A sliding window tolerates initial settling.
    stage = _auto["stage"]
    if stage not in ("dry_sample", "wet_sample"):
        return
    _sample()
    if _latest is None:
        _auto["stage"] = stage.replace("sample", "ready")
        _auto["message"] = "Read failed; check cable"
        return
    values = _auto["samples"]
    values.append(_latest[0])
    if len(values) > 20:
        values.pop(0)
    _auto["count"] += 1
    if len(values) == 20 and max(values)-min(values) <= 40:
        value = (sum(values)+10)//20
        if stage == "dry_sample":
            _auto["dry"] = value
            _auto["stage"] = "wet_ready"
            _auto["message"] = "Dry captured: %d" % value
        elif _auto["dry"]-value < 100:
            _auto["stage"] = "wet_ready"
            _auto["message"] = "D%d W%d: gap < 100" % (_auto["dry"], value)
        else:
            _auto["wet"] = value
            _auto["stage"] = "review"
            _auto["message"] = "Enter saves both values"
    elif _auto["count"] >= 120:
        _auto["stage"] = stage.replace("sample", "ready")
        _auto["message"] = "Unstable; retry when ready"


def _auto_key(button):
    global _auto, _pending, _notice, _last
    from picoware.system.buttons import (
        BUTTON_BACK, BUTTON_ESCAPE, BUTTON_LEFT, BUTTON_CENTER, BUTTON_ENTER,
    )
    from utime import ticks_ms
    if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_LEFT):
        _auto = None
        _notice = "Auto calibration cancelled"
    elif button in (BUTTON_CENTER, BUTTON_ENTER):
        stage = _auto["stage"]
        if stage in ("dry_ready", "wet_ready"):
            _auto["stage"] = stage.replace("ready", "sample")
            _auto["samples"] = []
            _auto["count"] = 0
            _auto["message"] = "Keep probe still"
            _last = ticks_ms()
        elif stage == "review":
            _pending = ("pair", (_auto["dry"], _auto["wet"]))
            if _save_pending():
                _auto = None
            else:
                _auto["message"] = _notice


def _render_auto(draw):
    stage = _auto["stage"]
    draw._text(4, 2, "Guided calibration", 0x07FF)
    if stage == "review":
        lines = ("Ready to save", "Dry (0%%): %d" % _auto["dry"],
                 "Wet (100%%): %d" % _auto["wet"])
    elif stage.endswith("ready"):
        dry = stage == "dry_ready"
        lines = ("1/2: Place in dry soil" if dry else "2/2: Place in wet soil",
                 "Use same insertion depth" if dry else "Let excess water drain",
                 "Enter: start measurement")
    else:
        values = _auto["samples"]
        spread = max(values)-min(values) if values else 0
        lines = ("Measuring " + ("dry soil" if stage == "dry_sample" else "wet soil"),
                 "Stable window: %d/20" % len(values),
                 "Spread: %d (max 40)" % spread)
    for i, line in enumerate(lines):
        draw._text(4, 26+20*i, line, 0xFFFF)
    draw._text(4, 88, _auto["message"][:29], 0xFFE0)
    draw._text(4, 106, "10s stable; 60s timeout", 0x07FF)
    draw._text(4, 122, "Back: cancel", 0x07FF)


def _render(vm):
    draw = vm.draw
    draw.clear(color=0)
    if _auto is not None:
        _render_auto(draw)
        draw.swap()
        return
    if _manual is not None:
        draw._text(4, 2, "Manual calibration", 0x07FF)
        draw._text(4, 22, "ADC range: 0..4095", 0xFFFF)
        for i, name in enumerate(("Dry (0%)", "Wet (100%)")):
            text = ("> " if i == _field else "  ") + name + ": " + (_manual[i] or "_")
            draw._text(4, 42+i*18, text, 0xFFE0 if i == _field else 0xFFFF)
        draw._text(4, 80, (_notice or "Dry - wet must be >= 100")[:29], 0xFFE0)
        draw._text(4, 98, "Tab: field  Bksp: delete", 0x07FF)
        draw._text(4, 118, "Enter: save  Back: cancel", 0x07FF)
        draw.swap()
        return
    if not _configure:
        _render_main(draw)
        draw.swap()
        return
    white, cyan, yellow = 0xFFFF, 0x07FF, 0xFFE0
    draw._text(4, 2, "CADV-Earthreader", cyan)
    if _latest is None:
        draw._text(4, 24, "Sensor read failed", yellow)
        draw._text(4, 44, (_error or "Retrying...")[:28], white)
    else:
        raw, digital = _latest
        pct = _display_percent()
        draw._text(4, 24, "Moisture: -- (calibrate)" if pct is None else "Moisture: %d%% (4s avg)" % pct, white)
        draw._text(4, 42, "ADC: %d%s" % (raw, " [at limit]" if raw >= 4090 else ""), white)
        draw._text(4, 58, "Threshold: %s" % ("n/a" if digital is None else "HIGH" if digital else "LOW"), white)
    if _pending is not None:
        kind, value = _pending
        label = "Clear calibration?" if kind == "reset" else "Save %s = %d?" % (kind.upper(), value)
        draw._text(4, 84, label, yellow)
        draw._text(4, 104, "Enter: save  Back: cancel", cyan)
    else:
        saved = "Dry:%s Wet:%s" % (_dry if _dry is not None else "--", _wet if _wet is not None else "--")
        draw._text(4, 74, saved, white)
        status = "Unplugged or very dry" if _error == "Check sensor" else _notice
        draw._text(4, 88, status[:28], yellow)
        draw._text(4, 104, "D:dry W:wet M:manual A:auto", cyan)
        draw._text(4, 120, "R:reset C/Back: main", cyan)
    draw.swap()


def _read_adc():
    # Keep the existing calibration units across native ADC resolutions.
    return _adc.read_u16() >> 4


def _open_sensor():
    global _sensor, _digital, _adc, _cardputer, CONFIG
    from picoware.system.boards import BOARD_ID, BOARD_CARDPUTER
    from machine import Pin
    _cardputer = BOARD_ID == BOARD_CARDPUTER
    if _cardputer:
        from cardputer_battery import read_grove_adc
        CONFIG = "picoware/settings/earth.json"
        _sensor = read_grove_adc
        _digital = Pin(2, Pin.IN)
        return

    import json
    from machine import ADC
    path = "picoware/settings/earth-pins.json"
    if not _storage.exists(path):
        raise ValueError("Set board/analog/digital in " + path)
    pins = json.loads(_storage.read(path))
    if type(pins) is not dict or type(pins.get("board")) is not int or pins["board"] != BOARD_ID:
        raise ValueError("earth-pins.json: board must be %d" % BOARD_ID)
    analog, digital = pins.get("analog"), pins.get("digital")
    if type(analog) is not int or analog < 0:
        raise ValueError("analog must be an ADC GPIO number")
    if digital is not None and (type(digital) is not int or digital < 0 or digital == analog):
        raise ValueError("digital must be a different GPIO or null")
    CONFIG = "picoware/settings/earth-%d-%d-%s.json" % (BOARD_ID, analog, digital)
    if hasattr(ADC, "ATTN_11DB"):
        _adc = ADC(Pin(analog), atten=ADC.ATTN_11DB)
    else:
        _adc = ADC(Pin(analog))
    _sensor = _read_adc
    if digital is not None:
        _digital = Pin(digital, Pin.IN)


def start(view_manager):
    global _last, _storage
    from utime import ticks_ms
    stop(view_manager)
    _storage = view_manager.storage
    try:
        _open_sensor()
    except (ImportError, OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
        message = "Earth needs shared-ADC firmware: " if _cardputer else "Earth ADC setup: "
        stop(view_manager)
        view_manager.alert(message + str(exc))
        return False
    _load_calibration()
    _sample()
    _last = ticks_ms()
    _render(view_manager)
    return True


def run(view_manager):
    global _last, _pending, _notice, _configure, _manual, _field, _replace
    from picoware.system.buttons import (
        BUTTON_BACK, BUTTON_ESCAPE, BUTTON_LEFT, BUTTON_D, BUTTON_W,
        BUTTON_R, BUTTON_CENTER, BUTTON_C, BUTTON_M, BUTTON_ENTER, BUTTON_A,
    )
    from utime import ticks_ms, ticks_diff
    button = view_manager.button
    if _auto is not None:
        _auto_key(button)
        if _auto is not None and ticks_diff(ticks_ms(), _last) >= INTERVAL_MS:
            _last = ticks_ms()
            _auto_tick()
        _render(view_manager)
        return
    if _manual is not None:
        _manual_key(button)
        _render(view_manager)
        return
    if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_LEFT):
        if _pending is not None:
            _pending = None
            _render(view_manager)
        elif _configure:
            _configure = False
            _render(view_manager)
        else:
            view_manager.back()
        return
    if _sensor is None:
        return
    if button == BUTTON_C:
        _configure = not _configure
        _pending = None
        _render(view_manager)
    elif _configure and button == BUTTON_A:
        _pending = None
        _auto_begin()
        _render(view_manager)
    elif _configure and button == BUTTON_M:
        _manual = [str(_dry) if _dry is not None else "", str(_wet) if _wet is not None else ""]
        _field = 0
        _replace = True
        _pending = None
        _notice = ""
        _render(view_manager)
    elif _configure and button in (BUTTON_CENTER, BUTTON_ENTER) and _pending is not None:
        _sample()
        if _pending is not None:
            _save_pending()
        _render(view_manager)
    elif _configure and button == BUTTON_R:
        _pending = ("reset", None)
        _render(view_manager)
    elif _configure and button in (BUTTON_D, BUTTON_W):
        _sample()
        if _latest is not None:
            _pending = ("dry" if button == BUTTON_D else "wet", _latest[0])
            _notice = ""
        _render(view_manager)
    now = ticks_ms()
    if ticks_diff(now, _last) >= INTERVAL_MS:
        _last = now
        _sample()
        _render(view_manager)


def stop(view_manager):
    global _adc, _cardputer, _storage
    global _sensor, _digital, _last, _latest, _error, _pending, _notice, _configure, _manual, _auto
    _storage = None
    _readings.clear()
    _auto = None
    _manual = None
    _configure = False
    _pending = None
    _notice = ""
    _sensor = None
    adc, _adc = _adc, None
    if adc is not None:
        deinit = getattr(adc, "deinit", None)
        if deinit is not None:
            try:
                deinit()
            except (OSError, RuntimeError):
                pass
    _cardputer = False
    _digital = None
    _last = None
    _latest = None
    _error = None
