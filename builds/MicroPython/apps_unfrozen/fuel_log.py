from picoware.system.vector import Vector
from picoware.system.colors import (
    TFT_ORANGE, TFT_YELLOW, TFT_WHITE, TFT_GREEN, TFT_RED,
    TFT_CYAN, TFT_BLUE, TFT_DARKGREY
)
from picoware.system.buttons import (
    BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT,
    BUTTON_CENTER, BUTTON_OK, BUTTON_BACK, BUTTON_BACKSPACE,
    BUTTON_A, BUTTON_D, BUTTON_T, BUTTON_P, BUTTON_E, BUTTON_G,
    BUTTON_0, BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4,
    BUTTON_5, BUTTON_6, BUTTON_7, BUTTON_8, BUTTON_9, BUTTON_PERIOD
)

DATA_PATH = "/picoware/data/fuellog.json"
EXPORT_PATH = "/picoware/data/fuellog.csv"
GRADES = ["Reg", "Mid", "Prem", "Diesel"]

DIGITS = {
    BUTTON_0: "0", BUTTON_1: "1", BUTTON_2: "2", BUTTON_3: "3", BUTTON_4: "4",
    BUTTON_5: "5", BUTTON_6: "6", BUTTON_7: "7", BUTTON_8: "8", BUTTON_9: "9",
    BUTTON_PERIOD: ".",
}

TILES = [
    ("Add", "add"), ("Quick", "quick"), ("Log", "history"),
    ("Sum", "summary"), ("Trend", "trend"), ("Chart", "chart"),
    ("Trip", "trip"), ("Presets", "presets"), ("Service", "remind"),
    ("Setup", "settings"), ("Export", "export"), ("Save", "save"),
]

_storage = None
_mode = "home"
_tile = 0
_idx = 0
_field = 0
_buf = ""
_msg = ""
_edit_i = -1
_entries = []
_presets = []
_settings = {
    "units_metric": False,
    "remind_miles": 5000,
    "last_service_odo": 0,
    "remind_enabled": True,
    "tank_gallons": 14.0,
}
_draft = {"odo": "0", "gal": "0", "cost": "0", "partial": False, "grade": 0}
_trip = {"miles": "100", "mpg": "25", "ppg": "3.50"}
_preset_i = 0
_PRESET_NAMES = ["Work", "Home", "Airport", "Moms", "TripA", "TripB"]


def _js():
    try:
        import ujson as js
        return js
    except Exception:
        import json as js
        return js


def _load():
    global _entries, _presets, _settings
    _entries = []
    _presets = []
    try:
        js = _js()
        if _storage and _storage.exists(DATA_PATH):
            raw = _storage.read(DATA_PATH)
            if isinstance(raw, bytes):
                raw = raw.decode()
            data = js.loads(raw)
            if isinstance(data, dict):
                _entries = data.get("entries", [])
                _presets = data.get("presets", [])
                st = data.get("settings", {})
                if isinstance(st, dict):
                    _settings.update(st)
            elif isinstance(data, list):
                _entries = data
    except Exception:
        _entries = []


def _save():
    global _msg
    try:
        js = _js()
        if not _storage.exists("/picoware/data"):
            _storage.mkdir("/picoware/data")
        _storage.write(DATA_PATH, js.dumps({
            "entries": _entries, "presets": _presets, "settings": _settings,
        }))
        _msg = "Saved"
    except Exception:
        _msg = "Save failed"


def _f(s):
    try:
        return float(s)
    except Exception:
        return 0.0


def _i(s):
    try:
        return int(float(s))
    except Exception:
        return 0


def _mpg_for(i):
    if i <= 0 or i >= len(_entries):
        return 0.0
    cur = _entries[i]
    if cur.get("partial"):
        return 0.0
    j = i - 1
    while j >= 0 and _entries[j].get("partial"):
        j -= 1
    if j < 0:
        return 0.0
    miles = int(cur.get("odo", 0)) - int(_entries[j].get("odo", 0))
    gal = float(cur.get("gal", 0))
    if miles <= 0 or gal <= 0:
        return 0.0
    return miles / gal


def _avg_mpg():
    tm = 0
    tg = 0.0
    for i in range(len(_entries)):
        if _mpg_for(i) <= 0:
            continue
        cur = _entries[i]
        j = i - 1
        while j >= 0 and _entries[j].get("partial"):
            j -= 1
        if j < 0:
            continue
        tm += int(cur.get("odo", 0)) - int(_entries[j].get("odo", 0))
        tg += float(cur.get("gal", 0))
    if tg <= 0:
        return 0.0
    return tm / tg


def _rolling5():
    vals = []
    for i in range(len(_entries) - 1, -1, -1):
        m = _mpg_for(i)
        if m > 0:
            vals.append(m)
        if len(vals) >= 5:
            break
    return (sum(vals) / len(vals)) if vals else 0.0


def _eff(mpg):
    if mpg <= 0:
        return "--"
    if _settings.get("units_metric"):
        return "%.1fL/100" % (235.214 / mpg)
    return "%.1fmpg" % mpg


def _ppg(e):
    g = float(e.get("gal", 0))
    c = float(e.get("cost", 0))
    return (c / g) if g > 0 else 0.0


def _remind_text():
    if not _settings.get("remind_enabled"):
        return "Remind off"
    if not _entries:
        return "No odo"
    last = int(_entries[-1].get("odo", 0))
    due = int(_settings.get("last_service_odo", 0)) + int(_settings.get("remind_miles", 5000))
    left = due - last
    if left <= 0:
        return "SERVICE DUE"
    return "Svc %dmi" % left


def _range_text():
    avg = _avg_mpg()
    tank = float(_settings.get("tank_gallons", 14))
    if avg <= 0 or tank <= 0:
        return "Range --"
    return "~%dmi" % int(avg * tank * 0.9)


def _sync_buf():
    global _buf
    if _mode in ("add", "edit"):
        _buf = str(_draft[["odo", "gal", "cost"][_field]])
    elif _mode == "quick":
        _buf = str(_draft["odo"])
    elif _mode == "trip":
        _buf = str(_trip[["miles", "mpg", "ppg"][_field]])
    elif _mode == "settings" and _field == 1:
        _buf = str(int(_settings.get("remind_miles", 5000)))
    elif _mode == "settings" and _field == 3:
        _buf = str(_settings.get("tank_gallons", 14))
    elif _mode == "remind":
        _buf = str(int(_settings.get("last_service_odo", 0)))
    else:
        _buf = ""


def _apply_buf():
    global _buf
    if _buf == "" or _buf == ".":
        _buf = "0"
    if _mode in ("add", "edit"):
        _draft[["odo", "gal", "cost"][_field]] = _buf
    elif _mode == "quick":
        _draft["odo"] = _buf
    elif _mode == "trip":
        _trip[["miles", "mpg", "ppg"][_field]] = _buf
    elif _mode == "settings" and _field == 1:
        _settings["remind_miles"] = max(100, _i(_buf))
    elif _mode == "settings" and _field == 3:
        _settings["tank_gallons"] = max(1.0, _f(_buf))
    elif _mode == "remind":
        _settings["last_service_odo"] = _i(_buf)


def _export():
    global _msg
    try:
        lines = ["odo,gal,cost,partial,grade,ppg,mpg\n"]
        for i, e in enumerate(_entries):
            lines.append("%s,%s,%s,%d,%s,%.3f,%.2f\n" % (
                e.get("odo", 0), e.get("gal", 0), e.get("cost", 0),
                1 if e.get("partial") else 0, e.get("grade", "Reg"),
                _ppg(e), _mpg_for(i)))
        if not _storage.exists("/picoware/data"):
            _storage.mkdir("/picoware/data")
        _storage.write(EXPORT_PATH, "".join(lines))
        _msg = "CSV exported"
    except Exception:
        _msg = "Export failed"


def start(view_manager) -> bool:
    global _storage, _mode, _tile, _msg
    _storage = view_manager.storage
    _mode = "home"
    _tile = 0
    _msg = ""
    _load()
    if _entries:
        _draft["odo"] = str(int(_entries[-1].get("odo", 0)))
    _draw(view_manager)
    return True


def _draw_home(d):
    d.fill_rectangle(Vector(0, 0), Vector(320, 40), TFT_BLUE)
    d.text(Vector(8, 4), "FUEL LOG", TFT_WHITE, 1)
    d.text(Vector(8, 20), "%s   %s   %s" % (_eff(_avg_mpg()), _range_text(), _remind_text()), TFT_YELLOW, 1)

    cols = 3
    tw, th = 100, 34
    ox, oy = 6, 50
    gap_x, gap_y = 6, 6
    for i, (label, _act) in enumerate(TILES):
        r, c = i // cols, i % cols
        x = ox + c * (tw + gap_x)
        y = oy + r * (th + gap_y)
        if i == _tile:
            d.fill_rectangle(Vector(x, y), Vector(tw, th), TFT_CYAN)
            d.text(Vector(x + 14, y + 11), label, TFT_BLUE, 1)
        else:
            d.fill_rectangle(Vector(x, y), Vector(tw, th), TFT_DARKGREY)
            d.rect(Vector(x, y), Vector(tw, th), TFT_CYAN)
            d.text(Vector(x + 14, y + 11), label, TFT_WHITE, 1)

    d.text(Vector(8, 220), "D-pad move tile    OK open    Back quit", TFT_DARKGREY, 1)


def _title_bar(d, text):
    d.fill_rectangle(Vector(0, 0), Vector(320, 26), TFT_BLUE)
    d.text(Vector(8, 7), text, TFT_WHITE, 1)


def _hint(d, text):
    d.fill_rectangle(Vector(0, 220), Vector(320, 20), TFT_DARKGREY)
    d.text(Vector(8, 224), text, TFT_CYAN, 1)


def _draw(vm):
    d = vm.draw
    d.erase()

    if _mode == "home":
        _draw_home(d)
        d.swap()
        return

    titles = {
        "add": "Add fill", "quick": "Quick fill", "edit": "Edit fill",
        "history": "History", "summary": "Summary", "trend": "Trend",
        "chart": "Cost chart", "trip": "Trip calc", "presets": "Presets",
        "remind": "Service", "settings": "Setup",
    }
    _title_bar(d, titles.get(_mode, "Fuel Log"))
    if _msg:
        d.text(Vector(8, 30), str(_msg)[:38], TFT_YELLOW, 1)
    top = 48 if _msg else 34

    if _mode == "history":
        if not _entries:
            d.text(Vector(12, top + 10), "No fills yet", TFT_WHITE, 1)
        else:
            start = max(0, len(_entries) - 1 - _idx - 2)
            end = min(len(_entries), start + 5)
            y = top
            for i in range(end - 1, start - 1, -1):
                e = _entries[i]
                sel = i == len(_entries) - 1 - _idx
                if sel:
                    d.fill_rectangle(Vector(4, y - 2), Vector(312, 30), TFT_BLUE)
                p = "P" if e.get("partial") else " "
                line = "%s%s%d %.1fg $%.2f %s" % (
                    ">" if sel else " ", p, int(e.get("odo", 0)),
                    float(e.get("gal", 0)), float(e.get("cost", 0)), e.get("grade", "Reg"))
                d.text(Vector(8, y), line[:40], TFT_WHITE, 1)
                extra = ""
                ppg = _ppg(e)
                if ppg > 0:
                    extra += "$%.2f/g " % ppg
                m = _mpg_for(i)
                if m > 0:
                    extra += _eff(m)
                d.text(Vector(16, y + 12), extra[:36], TFT_GREEN, 1)
                y += 32
        _hint(d, "E edit   D delete   Back home")

    elif _mode in ("add", "edit"):
        labels = ["Odometer", "Gallons", "Total $"]
        keys = ["odo", "gal", "cost"]
        y = top
        for i in range(3):
            sel = i == _field
            if sel:
                d.fill_rectangle(Vector(6, y - 2), Vector(308, 18), TFT_BLUE)
            val = _buf if sel else str(_draft[keys[i]])
            d.text(Vector(12, y), "%s %s: %s" % (">" if sel else " ", labels[i], val), TFT_CYAN if sel else TFT_WHITE, 1)
            y += 20
        d.text(Vector(12, y + 4), "Partial %s  [P]" % ("YES" if _draft.get("partial") else "no"), TFT_YELLOW, 1)
        d.text(Vector(12, y + 20), "Grade   %s  [G]" % GRADES[int(_draft.get("grade", 0)) % 4], TFT_ORANGE, 1)
        g, c = _f(_draft["gal"]), _f(_draft["cost"])
        if g > 0 and c > 0:
            d.text(Vector(12, y + 36), "$/gal  %.3f" % (c / g), TFT_GREEN, 1)
        _hint(d, "Type digits   OK save   Back")

    elif _mode == "quick":
        d.text(Vector(12, top), "Type new odometer only", TFT_WHITE, 1)
        d.fill_rectangle(Vector(6, top + 22), Vector(308, 22), TFT_BLUE)
        d.text(Vector(12, top + 26), "Odo: %s" % _buf, TFT_CYAN, 1)
        if _entries:
            last = _entries[-1]
            d.text(Vector(12, top + 56), "Reuses last fill:", TFT_YELLOW, 1)
            d.text(Vector(12, top + 74), "%.1fg  $%.2f  %s" % (
                float(last.get("gal", 0)), float(last.get("cost", 0)), last.get("grade", "Reg")), TFT_WHITE, 1)
        else:
            d.text(Vector(12, top + 56), "Add a normal fill first", TFT_RED, 1)
        _hint(d, "Type odo   OK save   Back")

    elif _mode == "summary":
        avg, r5 = _avg_mpg(), _rolling5()
        spend = sum(float(e.get("cost", 0)) for e in _entries)
        gal = sum(float(e.get("gal", 0)) for e in _entries)
        miles = 0
        if len(_entries) >= 2:
            miles = max(0, int(_entries[-1].get("odo", 0)) - int(_entries[0].get("odo", 0)))
        lines = [
            ("Fills", "%d" % len(_entries), TFT_WHITE),
            ("Average", _eff(avg), TFT_GREEN),
            ("Rolling 5", _eff(r5), TFT_CYAN),
            ("Miles", "%d" % miles, TFT_WHITE),
            ("Gallons", "%.1f" % gal, TFT_WHITE),
            ("Spent", "$%.2f" % spend, TFT_YELLOW),
            ("Range", _range_text(), TFT_ORANGE),
        ]
        y = top
        for lab, val, col in lines:
            d.text(Vector(16, y), lab, TFT_DARKGREY, 1)
            d.text(Vector(120, y), val, col, 1)
            y += 18
        _hint(d, "Back home")

    elif _mode == "trend":
        avg, r5 = _avg_mpg(), _rolling5()
        d.text(Vector(12, top), "All-time  %s" % _eff(avg), TFT_WHITE, 1)
        d.text(Vector(12, top + 18), "Rolling5  %s" % _eff(r5), TFT_CYAN, 1)
        if avg > 0 and r5 > 0:
            diff = r5 - avg
            if abs(diff) < 0.3:
                d.text(Vector(12, top + 42), "Steady", TFT_GREEN, 1)
            elif diff > 0:
                d.text(Vector(12, top + 42), "UP +%.1f" % diff, TFT_GREEN, 1)
            else:
                d.text(Vector(12, top + 42), "DOWN %.1f" % diff, TFT_RED, 1)
        recent = []
        for i in range(len(_entries) - 1, -1, -1):
            m = _mpg_for(i)
            if m > 0:
                recent.append(m)
            if len(recent) >= 5:
                break
        y = top + 70
        for i, m in enumerate(recent):
            d.text(Vector(12, y), "Tank %d   %s" % (i + 1, _eff(m)), TFT_WHITE, 1)
            y += 16
        _hint(d, "Back home")

    elif _mode == "chart":
        costs = [float(e.get("cost", 0)) for e in _entries[-7:]]
        if not costs:
            d.text(Vector(12, top + 20), "No data", TFT_YELLOW, 1)
        else:
            mx = max(costs) if max(costs) > 0 else 1
            base = 175
            x = 18
            bw = 38
            for c in costs:
                h = max(4, int(100 * (c / mx)))
                d.fill_rectangle(Vector(x, base - h), Vector(bw - 8, h), TFT_ORANGE)
                d.text(Vector(x, base + 6), str(int(c)), TFT_WHITE, 1)
                x += bw
        _hint(d, "Back home")

    elif _mode == "trip":
        labels = ["Miles", "MPG", "$/gal"]
        keys = ["miles", "mpg", "ppg"]
        y = top
        for i in range(3):
            sel = i == _field
            if sel:
                d.fill_rectangle(Vector(6, y - 2), Vector(308, 18), TFT_BLUE)
            val = _buf if sel else str(_trip[keys[i]])
            d.text(Vector(12, y), "%s %s: %s" % (">" if sel else " ", labels[i], val), TFT_CYAN if sel else TFT_WHITE, 1)
            y += 20
        miles, mpg, ppg = _f(_trip["miles"]), _f(_trip["mpg"]), _f(_trip["ppg"])
        need = (miles / mpg) if mpg > 0 else 0
        d.text(Vector(12, y + 10), "Need  %.1f gal" % need, TFT_GREEN, 1)
        d.text(Vector(12, y + 28), "Est   $%.2f" % (need * ppg), TFT_YELLOW, 1)
        _hint(d, "T avg MPG   A save preset   Back")

    elif _mode == "presets":
        if not _presets:
            d.text(Vector(12, top + 10), "No presets", TFT_WHITE, 1)
            d.text(Vector(12, top + 28), "In Trip press A to save", TFT_YELLOW, 1)
        else:
            y = top
            start = max(0, _idx - 3)
            for i in range(start, min(len(_presets), start + 7)):
                p = _presets[i]
                sel = i == _idx
                if sel:
                    d.fill_rectangle(Vector(6, y - 2), Vector(308, 16), TFT_BLUE)
                d.text(Vector(12, y), "%s %s  %smi" % (">" if sel else " ", p.get("name", "?"), p.get("miles", "?")), TFT_WHITE, 1)
                y += 18
        _hint(d, "OK load   D delete   Back")

    elif _mode == "remind":
        d.text(Vector(12, top), _remind_text(), TFT_ORANGE, 1)
        d.text(Vector(12, top + 28), "Last service odometer", TFT_WHITE, 1)
        d.fill_rectangle(Vector(6, top + 48), Vector(308, 22), TFT_BLUE)
        d.text(Vector(12, top + 52), _buf, TFT_CYAN, 1)
        _hint(d, "Type odo   OK set   Back")

    elif _mode == "settings":
        metric = _settings.get("units_metric")
        en = _settings.get("remind_enabled")
        rows = [
            "Units: " + ("L/100km" if metric else "MPG"),
            "Service every: %s mi" % (_buf if _field == 1 else str(int(_settings.get("remind_miles", 5000)))),
            "Reminders: " + ("ON" if en else "OFF"),
            "Tank size: %s gal" % (_buf if _field == 3 else str(_settings.get("tank_gallons", 14))),
        ]
        y = top
        for i, line in enumerate(rows):
            sel = i == _field
            if sel:
                d.fill_rectangle(Vector(6, y - 2), Vector(308, 18), TFT_BLUE)
            d.text(Vector(12, y), ("%s %s" % (">" if sel else " ", line)), TFT_CYAN if sel else TFT_WHITE, 1)
            y += 22
        _hint(d, "OK change   type on # fields   Back")

    d.swap()


def _open_tile():
    global _mode, _idx, _field, _msg, _edit_i
    label, act = TILES[_tile]
    if act == "export":
        _export()
        return
    if act == "save":
        _save()
        return
    _mode = act
    _idx = 0
    _field = 0
    _edit_i = -1
    _msg = ""
    if act == "add":
        _draft["partial"] = False
        _draft["grade"] = 0
        if _entries:
            _draft["odo"] = str(int(_entries[-1].get("odo", 0)))
        _sync_buf()
    elif act == "quick":
        if _entries:
            _draft["odo"] = str(int(_entries[-1].get("odo", 0)))
        _sync_buf()
    elif act == "trip":
        avg = _avg_mpg()
        if avg > 0:
            _trip["mpg"] = "%.1f" % avg
        _sync_buf()
    elif act in ("remind", "settings"):
        _sync_buf()


def _type_digit(ch):
    global _buf
    if ch == "." and "." in _buf:
        return
    if len(_buf) >= 10:
        return
    if _buf == "0" and ch != ".":
        _buf = ch
    else:
        _buf += ch
    _apply_buf()


def _start_edit():
    global _mode, _edit_i, _field, _msg
    if not _entries:
        return
    real = len(_entries) - 1 - _idx
    if real < 0 or real >= len(_entries):
        return
    e = _entries[real]
    _edit_i = real
    _draft["odo"] = str(int(e.get("odo", 0)))
    _draft["gal"] = str(e.get("gal", 0))
    _draft["cost"] = str(e.get("cost", 0))
    _draft["partial"] = bool(e.get("partial"))
    gr = e.get("grade", "Reg")
    _draft["grade"] = GRADES.index(gr) if gr in GRADES else 0
    _field = 0
    _mode = "edit"
    _sync_buf()
    _msg = "Editing"


def run(vm) -> None:
    global _mode, _tile, _idx, _field, _buf, _msg, _preset_i, _edit_i
    button = vm.button

    typing = _mode in ("add", "edit", "quick", "trip", "remind") or (
        _mode == "settings" and _field in (1, 3)
    )
    if typing and button in DIGITS:
        _type_digit(DIGITS[button])
        _draw(vm)
        return
    if typing and button == BUTTON_BACKSPACE:
        if len(_buf) > 0:
            _buf = _buf[:-1]
            _apply_buf()
        _draw(vm)
        return

    if _mode == "home":
        cols = 3
        rows = (len(TILES) + cols - 1) // cols
        r, c = _tile // cols, _tile % cols
        if button == BUTTON_LEFT:
            c = (c - 1) % cols
        elif button == BUTTON_RIGHT:
            c = (c + 1) % cols
        elif button == BUTTON_UP:
            r = (r - 1) % rows
        elif button == BUTTON_DOWN:
            r = (r + 1) % rows
        elif button == BUTTON_CENTER or button == BUTTON_OK:
            _open_tile()
            _draw(vm)
            return
        elif button == BUTTON_BACK:
            vm.back()
            return
        nt = r * cols + c
        if nt >= len(TILES):
            nt = len(TILES) - 1
        _tile = nt
        _draw(vm)
        return

    if button == BUTTON_BACK:
        if _mode in ("add", "edit", "quick", "trip", "settings", "remind"):
            _apply_buf()
        _mode = "home"
        _msg = ""
        _draw(vm)
        return

    if _mode == "history":
        n = len(_entries)
        if button == BUTTON_UP and n:
            _idx = (_idx + 1) % n
        elif button == BUTTON_DOWN and n:
            _idx = (_idx - 1) % n
        elif button == BUTTON_D and n:
            real = n - 1 - _idx
            if 0 <= real < n:
                _entries.pop(real)
                _idx = min(_idx, max(0, len(_entries) - 1))
                _save()
                _msg = "Deleted"
        elif button == BUTTON_E and n:
            _start_edit()

    elif _mode in ("add", "edit"):
        if button == BUTTON_UP:
            _apply_buf()
            _field = (_field - 1) % 3
            _sync_buf()
        elif button == BUTTON_DOWN:
            _apply_buf()
            _field = (_field + 1) % 3
            _sync_buf()
        elif button == BUTTON_P:
            _draft["partial"] = not _draft.get("partial")
            _msg = "Partial " + ("YES" if _draft["partial"] else "no")
        elif button == BUTTON_G:
            _draft["grade"] = (int(_draft.get("grade", 0)) + 1) % 4
            _msg = GRADES[_draft["grade"]]
        elif button == BUTTON_CENTER or button == BUTTON_OK:
            _apply_buf()
            gal, cost = _f(_draft["gal"]), _f(_draft["cost"])
            if gal <= 0:
                _msg = "Need gallons"
            else:
                row = {
                    "odo": _i(_draft["odo"]), "gal": round(gal, 3), "cost": round(cost, 2),
                    "partial": bool(_draft.get("partial")),
                    "grade": GRADES[int(_draft.get("grade", 0)) % 4],
                }
                if _mode == "edit" and 0 <= _edit_i < len(_entries):
                    _entries[_edit_i] = row
                    _msg = "Updated"
                else:
                    _entries.append(row)
                    _msg = "Saved"
                _save()
                _mode = "home"

    elif _mode == "quick":
        if button == BUTTON_CENTER or button == BUTTON_OK:
            _apply_buf()
            if not _entries:
                _msg = "Need a fill first"
            else:
                last = _entries[-1]
                _entries.append({
                    "odo": _i(_draft["odo"]), "gal": last.get("gal", 0),
                    "cost": last.get("cost", 0), "partial": False,
                    "grade": last.get("grade", "Reg"),
                })
                _save()
                _msg = "Quick saved"
                _mode = "home"

    elif _mode == "trip":
        if button == BUTTON_UP:
            _apply_buf()
            _field = (_field - 1) % 3
            _sync_buf()
        elif button == BUTTON_DOWN:
            _apply_buf()
            _field = (_field + 1) % 3
            _sync_buf()
        elif button == BUTTON_T:
            avg = _avg_mpg()
            if avg > 0:
                _trip["mpg"] = "%.1f" % avg
                if _field == 1:
                    _buf = _trip["mpg"]
                _msg = "Avg MPG"
        elif button == BUTTON_A:
            _apply_buf()
            name = _PRESET_NAMES[_preset_i % len(_PRESET_NAMES)]
            _preset_i += 1
            _presets.append({"name": name, "miles": _trip["miles"], "mpg": _trip["mpg"], "ppg": _trip["ppg"]})
            _save()
            _msg = "Preset " + name

    elif _mode == "presets":
        n = len(_presets)
        if button == BUTTON_UP and n:
            _idx = (_idx - 1) % n
        elif button == BUTTON_DOWN and n:
            _idx = (_idx + 1) % n
        elif (button == BUTTON_OK or button == BUTTON_CENTER) and n:
            p = _presets[_idx]
            _trip["miles"] = str(p.get("miles", "100"))
            _trip["mpg"] = str(p.get("mpg", "25"))
            _trip["ppg"] = str(p.get("ppg", "3.50"))
            _mode = "trip"
            _field = 0
            _sync_buf()
            _msg = "Loaded"
        elif button == BUTTON_D and n:
            _presets.pop(_idx)
            _idx = min(_idx, max(0, len(_presets) - 1))
            _save()
            _msg = "Deleted"

    elif _mode == "remind":
        if button == BUTTON_CENTER or button == BUTTON_OK:
            _apply_buf()
            _save()
            _msg = "Service set"

    elif _mode == "settings":
        if button == BUTTON_UP:
            _apply_buf()
            _field = (_field - 1) % 4
            _sync_buf()
        elif button == BUTTON_DOWN:
            _apply_buf()
            _field = (_field + 1) % 4
            _sync_buf()
        elif button == BUTTON_CENTER or button == BUTTON_OK:
            if _field == 0:
                _settings["units_metric"] = not _settings.get("units_metric")
                _save()
            elif _field in (1, 3):
                _apply_buf()
                _save()
                _msg = "Updated"
            elif _field == 2:
                _settings["remind_enabled"] = not _settings.get("remind_enabled")
                _save()

    _draw(vm)


def stop(vm) -> None:
    global _storage, _entries
    try:
        _save()
    except Exception:
        pass
    _storage = None
    _entries = []