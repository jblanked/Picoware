import json
import os
import time


class StopSimulation(SystemExit):
    pass


class RestartSimulation(SystemExit):
    def __init__(self, reset=False):
        self.reset = reset


class LaunchTargetError(Exception):
    pass


root = "."
sd_root = "simulator/sdcard"
apps_source = "builds/MicroPython/apps_unfrozen"
scale = 2
board = "picocalc-pico2w"
max_frames = 0
headless = False
trace_keys = False
trace_views = False
trace_imports = False
screenshot_path = ""
viewer = False
viewer_frame_path = ""
viewer_keys_path = ""
status_path = ""
error_path = ""
control_path = ""
log_path = ""
record_path = ""
sd_profile = "dev"
network_mode = "real"
bluetooth_mode = "virtual"
audio_mode = "real"
speed_mode = "auto"
target_fps = 0
_frame_interval_ms = 0
_last_frame_ms = 0
_viewer_key_offset = 0
_last_status_ms = 0
_control_offset = 0
audio_muted = False
frame_count = 0
loop_count = 0
open_target = ""
_keys = []
_delayed_keys = []
_held_keys = {}
_lcd = None
_wait_view = ""
_assert_text = ""
_seen_wait_view = False
_seen_assert_text = False
_current_view_name = ""
_recent_text = []
_recent_input = []
_record_text = ""
_touch_point = (0, 0)
_touch_gesture = 0
_touch_callbacks = []
_battery_percentage = 87


KEY_NAMES = {
    "up": 0xB5,
    "down": 0xB6,
    "left": 0xB4,
    "right": 0xB7,
    "escape": 0xB1,
    "esc": 0xB1,
    "back": 0xB1,
    "break": 0xD0,
    "insert": 0xD1,
    "ins": 0xD1,
    "backspace": 8,
    "bs": 8,
    "enter": 13,
    "return": 13,
    "center": 13,
    "newline": 13,
    "tab": 9,
    "home": 0xD2,
    "delete": 0xD4,
    "del": 0xD4,
    "end": 0xD5,
    "pageup": 0xD6,
    "page-up": 0xD6,
    "pgup": 0xD6,
    "pagedown": 0xD7,
    "page-down": 0xD7,
    "pgdn": 0xD7,
    "ctrl-up": 0xC2,
    "ctrlup": 0xC2,
    "ctrl-down": 0xC3,
    "ctrldown": 0xC3,
    "f1": 0x81,
    "f2": 0x82,
    "f3": 0x83,
    "f4": 0x84,
    "f5": 0x85,
    "f6": 0x86,
    "f7": 0x87,
    "f8": 0x88,
    "f9": 0x89,
    "f10": 0x90,
}

LIBRARY_ITEMS = {
    "agent": 0,
    "applications": 1,
    "app store": 2,
    "appstore": 2,
    "bluetooth": 3,
    "file manager": 4,
    "filemanager": 4,
    "gameboy emulator": 5,
    "gameboy": 5,
    "games": 6,
    "python editor": 7,
    "pythoneditor": 7,
    "python repl": 8,
    "repl": 8,
    "screensavers": 9,
    "system": 10,
    "text editor": 11,
    "texteditor": 11,
    "usb": 12,
    "wifi": 13,
}


def configure(_root, _sd_root, _apps_source, _scale, _board, _max_frames, _headless, _trace_keys, _trace_views, _trace_imports, _screenshot, _viewer=False, _viewer_frame="", _viewer_keys="", _network_mode="real", _bluetooth_mode="virtual", _audio_mode="real", _speed_mode="auto", _target_fps=0, _sd_profile="dev", _record_path=""):
    global root, sd_root, apps_source, scale, board, max_frames, headless
    global trace_keys, trace_views, trace_imports, screenshot_path
    global viewer, viewer_frame_path, viewer_keys_path, status_path, error_path, control_path, log_path, record_path
    global sd_profile, network_mode, bluetooth_mode, audio_mode
    global speed_mode, target_fps, _frame_interval_ms, _last_frame_ms, _viewer_key_offset, _last_status_ms, _control_offset, audio_muted
    global frame_count, loop_count, open_target, _keys, _delayed_keys, _held_keys, _lcd
    global _wait_view, _assert_text, _seen_wait_view, _seen_assert_text, _current_view_name, _recent_text
    global _recent_input, _record_text
    root = _root
    sd_root = _sd_root
    apps_source = _apps_source
    scale = _scale if _scale > 0 else 1
    board = _board
    max_frames = _max_frames
    headless = _headless
    trace_keys = _trace_keys
    trace_views = _trace_views
    trace_imports = _trace_imports
    screenshot_path = _screenshot
    viewer = _viewer
    viewer_frame_path = _viewer_frame
    viewer_keys_path = _viewer_keys
    status_path = (_viewer_frame + ".status") if _viewer_frame else ""
    error_path = (_viewer_frame + ".error") if _viewer_frame else ""
    control_path = (_viewer_frame + ".control") if _viewer_frame else ""
    log_path = (_viewer_frame + ".log") if _viewer_frame else ""
    record_path = _record_path
    sd_profile = str(_sd_profile or "dev")
    network_mode = _network_mode
    bluetooth_mode = _bluetooth_mode
    audio_mode = _audio_mode
    speed_mode = _speed_mode
    target_fps = _target_fps
    _frame_interval_ms = _resolve_frame_interval(_speed_mode, _target_fps, _headless, _viewer)
    _last_frame_ms = _ticks_ms()
    _viewer_key_offset = 0
    _last_status_ms = 0
    _control_offset = 0
    audio_muted = False
    frame_count = 0
    loop_count = 0
    open_target = ""
    _keys = []
    _delayed_keys = []
    _held_keys = {}
    _lcd = None
    _wait_view = ""
    _assert_text = ""
    _seen_wait_view = False
    _seen_assert_text = False
    _current_view_name = ""
    _recent_text = []
    _recent_input = []
    _record_text = ""
    if record_path:
        parent = record_path.rsplit("/", 1)[0] if "/" in record_path else "."
        mkdir_p(parent)
        with open(record_path, "w") as handle:
            handle.write("# Picoware simulator input recording\n")
    if log_path:
        try:
            with open(log_path, "w") as handle:
                handle.write("Picoware simulator log\n")
        except OSError:
            pass
    seed_sd(sd_profile)


def _ticks_ms():
    try:
        return time.ticks_ms()
    except AttributeError:
        return int(time.time() * 1000)


def _ticks_diff(a, b):
    try:
        return time.ticks_diff(a, b)
    except AttributeError:
        return a - b


def _resolve_frame_interval(mode, fps, is_headless, is_viewer):
    if mode == "unlimited" or mode == "off":
        return 0
    if fps and fps > 0:
        return max(1, int(1000 / fps))
    if mode == "real" or mode == "pico2w":
        return 33
    if mode == "fast":
        return 0
    # Fast default, real-time interactive.
    if is_viewer or not is_headless:
        return 33
    return 0


def pace_frame():
    global _last_frame_ms
    if _frame_interval_ms <= 0:
        return
    now = _ticks_ms()
    elapsed = _ticks_diff(now, _last_frame_ms)
    if elapsed < _frame_interval_ms:
        time.sleep((_frame_interval_ms - elapsed) / 1000)
        now = _ticks_ms()
    _last_frame_ms = now


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _write_if_missing(path, data):
    if _exists(path):
        return
    parent = path.rsplit("/", 1)[0] if "/" in path else "."
    mkdir_p(parent)
    with open(path, "w") as handle:
        handle.write(data)


def _write_binary_if_missing(path, data):
    if _exists(path):
        return
    parent = path.rsplit("/", 1)[0] if "/" in path else "."
    mkdir_p(parent)
    with open(path, "wb") as handle:
        handle.write(data)


def _quote(path):
    return "'" + str(path).replace("'", "'\"'\"'") + "'"


def _safe_sd_path(base, filename):
    parts = []
    for component in base.replace("\\", "/").split("/"):
        if component == "..":
            if parts:
                parts.pop()
        elif component and component != ".":
            parts.append(component)
    normalized = "/".join(parts)
    return (normalized + "/" + filename) if normalized else filename


def build_native(target):
    script = root + "/simulator/build.sh"
    if not _exists(script):
        script = root + "/sim_mp/build.sh"
    try:
        import subprocess
        status = subprocess.run(["sh", script, target]).returncode
    except ImportError:
        status = os.system("sh " + _quote(script) + " " + _quote(target))
    return status == 0


def native_helper_path(relative, target=None):
    candidates = (
        root + "/simulator/" + relative,
        root + "/sim_mp/" + relative,
    )
    for path in candidates:
        if _exists(path):
            return path
    if target and build_native(target):
        for path in candidates:
            if _exists(path):
                return path
    return candidates[0]


def _merge_json_defaults(path, defaults, fill_blank_keys=()):
    current = {}
    if _exists(path):
        try:
            with open(path, "r") as handle:
                data = handle.read()
            if data:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    current = parsed
        except Exception:
            current = {}
    changed = False
    for key in defaults:
        value = defaults[key]
        if key not in current or (key in fill_blank_keys and current.get(key, "") == ""):
            current[key] = value
            changed = True
    if changed or not _exists(path):
        parent = path.rsplit("/", 1)[0] if "/" in path else "."
        mkdir_p(parent)
        with open(path, "w") as handle:
            handle.write(json.dumps(current))


def seed_sd(profile="dev"):
    profile = str(profile or "dev")
    base_dirs = (
        "picoware",
        "picoware/settings",
        "picoware/wifi",
        "picoware/keyboard",
    )
    dev_dirs = base_dirs + (
        "picoware/apps",
        "picoware/apps/games",
        "picoware/apps/games/ghouls",
        "picoware/apps/games/ghouls/assets",
        "picoware/bluetooth",
    )
    media_dirs = dev_dirs + (
        "picoware/vibesmp",
        "picoware/vibesmp/lang",
        "picoware/vibesmp/playlists",
        "picoware/vibesmp/library",
        "picoware/vibesmp/library/meta",
        "picoware/vibesmp/library/covers",
        "picoware/vibesmp/radio",
    )
    fixture_dirs = media_dirs + (
        "picoware/fixtures",
        "picoware/wikireader",
        "picoware/weather",
        "picoware/github",
    )
    if profile == "clean":
        dirs = base_dirs
    elif profile == "media":
        dirs = media_dirs
    elif profile == "network-fixtures":
        dirs = fixture_dirs
    else:
        dirs = media_dirs
    for name in dirs:
        mkdir_p(sd_root + "/" + name)
    if profile in ("dev", "media", "network-fixtures"):
        _write_if_missing(
            sd_root + "/picoware/vibesmp/settings.json",
            '{"auto_play_next":true,"shuffle":false,"language":"en","theme":"dark","volume":100,"seek_length":5,"first_run":false,"auto_expand_library":true,"loop_mode":0,"focus_timeout":10,"time_24h":true,"list_view_policy":"offset","list_scroll_offset":2}',
        )
        playlist_tracks = '["picoware/vibesmp/library/sim-tone.wav"]' if profile in ("media", "network-fixtures") else "[]"
        _write_if_missing(sd_root + "/picoware/vibesmp/playlists/default.json", '{"tracks":' + playlist_tracks + ',"current_index":0}')
        _write_if_missing(sd_root + "/picoware/vibesmp/radio/stations.json", '[{"name":"Simulator MP3 Radio","url":"http://ice1.somafm.com/groovesalad-128-mp3"}]')
        database = '[{"title":"Simulator Tone","path":"picoware/vibesmp/library/sim-tone.wav","artist":"Picoware Simulator"}]' if profile in ("media", "network-fixtures") else "[]"
        _write_if_missing(sd_root + "/picoware/vibesmp/library/database.json", database)
        _write_if_missing(sd_root + "/picoware/vibesmp/library/state.json", '{}')
        if profile in ("media", "network-fixtures"):
            _write_binary_if_missing(sd_root + "/picoware/vibesmp/library/sim-tone.wav", _wav_fixture())
    _merge_json_defaults(
        sd_root + "/picoware/settings/picoware.json",
        {
            "dark_mode": True,
            "debug": False,
            "exit_button": 177,
            "gmt_offset": 0,
            "lvgl_mode": False,
            "onscreen_keyboard": False,
            "theme_color": 31,
            "wifi_ssid": "Picoware-Sim",
        },
        ("wifi_ssid",),
    )
    _write_if_missing(sd_root + "/picoware/wifi/ssid.json", '{"ssid":"Picoware-Sim"}')
    if profile != "clean":
        _write_if_missing(
            sd_root + "/picoware/apps/games/ghouls/assets/home.ghoulsmap",
            "Picoware simulator placeholder map\n",
        )
    if profile == "network-fixtures":
        _write_if_missing(sd_root + "/picoware/fixtures/catfact.json", '{"fact":"Picoware simulator fixture cat fact.","length":38}')
        _write_if_missing(sd_root + "/picoware/fixtures/weather.txt", "Clear,+21C,45%\n")
        _write_if_missing(sd_root + "/picoware/fixtures/github.json", '{"message":"Picoware simulator GitHub fixture","items":[]}')
        _write_if_missing(sd_root + "/picoware/wikireader/settings.json", '{"full_article":true,"language":"en","theme":"system","history":[],"favorites":[],"offline":[]}')

    # Symlink apps for __import__
    _link_app_files()


def _link_app_files():
    """Symlink app sources into simulated SD for __import__."""
    target = sd_root + "/picoware/apps"
    _link_app_files_into(apps_source, target)
    # Link compiled .mpy subdirectory apps
    _compiled = root + "/builds/MicroPython/apps"
    if _compiled != apps_source:
        _link_app_files_into(_compiled, target, skip_if_py_exists=True)


def _link_app_files_into(src_dir, dst_dir, skip_if_py_exists=False, include_init=False):
    """Recursively symlink .py/.mpy files from src_dir into dst_dir.

    When *skip_if_py_exists* is True, a .mpy file is skipped if a .py
    file with the same base name already exists (or is symlinked) in
    *dst_dir*.  This avoids duplicate app listings when both a source
    .py and a compiled .mpy are available.  Package __init__.py files
    are included below the app root so libraries remain importable."""
    mkdir_p(dst_dir)
    try:
        entries = os.listdir(src_dir)
    except OSError:
        return
    for entry in entries:
        if entry.startswith("."):
            continue
        if entry == "__init__.py" and not include_init:
            continue
        src = src_dir + "/" + entry
        dst = dst_dir + "/" + entry
        try:
            st = os.stat(src)
        except OSError:
            continue
        if st[0] & 0x4000:  # directory
            _link_app_files_into(src, dst, skip_if_py_exists, True)
        else:
            # Skip .mpy if .py exists
            if skip_if_py_exists and entry.endswith(".mpy"):
                _py_name = entry[:-4] + ".py"
                _py_dst = dst_dir + "/" + _py_name
                if _exists(_py_dst):
                    continue
            # Remove stale symlink first
            _rm_f(dst)
            # Try symlink, fallback to ln
            try:
                os.symlink(src, dst)
            except (AttributeError, OSError):
                status = os.system("ln -sf " + _quote(src) + " " + _quote(dst))
                if status != 0:
                    # fallback: copy the file
                    _copy_file(src, dst)


def _rm_f(path):
    """Remove a file or symlink; ignore errors.  Safe with symlinks
    (os.remove / unlink removes the symlink node, not its target)."""
    try:
        os.remove(path)
    except OSError:
        pass


def _copy_file(src, dst):
    """Byte-for-byte file copy (fallback when symlinks aren't available)."""
    try:
        with open(src, "rb") as fsrc:
            data = fsrc.read()
        parent = dst.rsplit("/", 1)[0] if "/" in dst else "."
        mkdir_p(parent)
        with open(dst, "wb") as fdst:
            fdst.write(data)
    except OSError:
        pass


def _wav_fixture():
    sample_rate = 8000
    samples = 800
    data_size = samples * 2
    header = bytearray()
    header.extend(b"RIFF")
    _u32(header, 36 + data_size)
    header.extend(b"WAVEfmt ")
    _u32(header, 16)
    _u16(header, 1)
    _u16(header, 1)
    _u32(header, sample_rate)
    _u32(header, sample_rate * 2)
    _u16(header, 2)
    _u16(header, 16)
    header.extend(b"data")
    _u32(header, data_size)
    for i in range(samples):
        value = 12000 if (i // 20) % 2 == 0 else -12000
        _u16(header, value & 0xFFFF)
    return bytes(header)


def _u16(buf, value):
    buf.append(value & 0xFF)
    buf.append((value >> 8) & 0xFF)


def _u32(buf, value):
    _u16(buf, value & 0xFFFF)
    _u16(buf, (value >> 16) & 0xFFFF)


def set_lcd(lcd):
    global _lcd
    _lcd = lcd


def set_script_expectations(wait_view="", assert_text=""):
    global _wait_view, _assert_text, _seen_wait_view, _seen_assert_text
    _wait_view = str(wait_view or "")
    _assert_text = str(assert_text or "")
    _seen_wait_view = False if _wait_view else True
    _seen_assert_text = False if _assert_text else True


def note_view(name):
    global _current_view_name, _seen_wait_view
    _current_view_name = str(name or "")
    if trace_views and _current_view_name:
        print("[sim:view]", _current_view_name)
    if _wait_view and _current_view_name.lower() == _wait_view.lower():
        _seen_wait_view = True
    _write_status(True)


def note_text(text):
    global _recent_text, _seen_assert_text
    if not text:
        return
    value = str(text)
    _recent_text.append(value)
    if len(_recent_text) > 256:
        _recent_text = _recent_text[-128:]
    if _assert_text and _assert_text in value:
        _seen_assert_text = True


def _check_expectations(final=False):
    if final:
        if _wait_view and not _seen_wait_view:
            raise AssertionError("wait-view not reached: " + _wait_view + " current=" + _current_view_name)
        if _assert_text and not _seen_assert_text:
            raise AssertionError("assert-text not seen: " + _assert_text)


def _log_event(text):
    if not log_path:
        return
    try:
        with open(log_path, "a") as handle:
            handle.write(str(text) + "\n")
    except OSError:
        pass


def push_key(code):
    if trace_keys:
        print("[sim:key]", code)
    _keys.append(code)
    _remember_input(code)


def _remember_input(code):
    global _recent_input
    _recent_input.append(_key_label(code))
    if len(_recent_input) > 32:
        _recent_input = _recent_input[-16:]


def _key_label(code):
    for name in KEY_NAMES:
        if KEY_NAMES[name] == code:
            return name
    if code >= 32 and code < 127:
        return chr(code)
    return str(code)


def _record_key(code):
    global _record_text
    if not record_path:
        return
    label = _key_label(code)
    printable = code >= 32 and code < 127 and label not in KEY_NAMES
    if printable:
        _record_text += chr(code)
        return
    _flush_record_text()
    with open(record_path, "a") as handle:
        if label == "newline":
            handle.write("keys enter\n")
        elif label == "back":
            handle.write("keys back\n")
        elif len(label) == 1:
            handle.write("text " + label + "\n")
        else:
            handle.write("keys " + label + "\n")


def _flush_record_text():
    global _record_text
    if not record_path or not _record_text:
        return
    safe = _record_text.replace("\\", "\\\\").replace("\n", "\\n")
    with open(record_path, "a") as handle:
        handle.write("text " + safe + "\n")
    _record_text = ""


def schedule_key_names(delay_loops, text):
    _delayed_keys.append((loop_count + int(delay_loops), "keys", text))


def schedule_text(delay_loops, text):
    _delayed_keys.append((loop_count + int(delay_loops), "text", text))


def _poll_delayed_keys():
    global _delayed_keys
    if not _delayed_keys:
        return
    remaining = []
    ready = []
    for item in _delayed_keys:
        if loop_count >= item[0]:
            ready.append(item)
        else:
            remaining.append(item)
    _delayed_keys = remaining
    for _, kind, value in ready:
        if kind == "keys":
            enqueue_key_names(value)
        else:
            enqueue_text(value)


def pop_key():
    poll_events()
    if _keys:
        return _keys.pop(0)
    return -1


def has_key():
    poll_events()
    return len(_keys) > 0


def is_key_held(code):
    poll_events()
    try:
        return bool(_held_keys.get(int(code), False))
    except Exception:
        return False


def enqueue_key_names(text):
    parts = text.split(",")
    for raw in parts:
        name = raw.strip()
        if not name:
            continue
        lower = name.lower()
        if lower in KEY_NAMES:
            push_key(KEY_NAMES[lower])
        elif len(name) == 1:
            push_key(ord(name))
        else:
            raise ValueError("Unknown key name: " + name)


def enqueue_text(text):
    for ch in str(text):
        if ch == "\n":
            push_key(KEY_NAMES["newline"])
        elif ch == "\t":
            push_key(KEY_NAMES["tab"])
        else:
            push_key(ord(ch))


def set_touch_point(x, y, gesture=0, notify=True):
    global _touch_point, _touch_gesture
    _touch_point = (int(x), int(y))
    _touch_gesture = int(gesture)
    if not notify:
        return
    for callback in list(_touch_callbacks):
        try:
            callback(None)
        except Exception as e:
            print("[sim:touch] callback failed:", e)


def clear_touch():
    set_touch_point(0, 0, 0, False)


def touch_point():
    return _touch_point


def touch_gesture():
    return _touch_gesture


def register_touch_callback(callback):
    if callback is None:
        _touch_callbacks[:] = []
    elif callback not in _touch_callbacks:
        _touch_callbacks.append(callback)


def set_battery_percentage(value):
    global _battery_percentage
    _battery_percentage = max(0, min(100, int(value)))


def battery_percentage():
    return _battery_percentage


def run_script_file(path):
    try:
        with open(path, "r") as handle:
            lines = handle.read().split("\n")
    except OSError as e:
        raise OSError("script not found: " + str(path) + " " + str(e))
    delay = 0
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if " " in line:
            command, value = line.split(" ", 1)
            value = value.strip()
        else:
            command, value = line, ""
        command = command.lower()
        if command in ("key", "keys"):
            if delay:
                schedule_key_names(delay, value)
                delay += 1
            else:
                enqueue_key_names(value)
        elif command == "text":
            if delay:
                schedule_text(delay, value)
                delay += 1
            else:
                enqueue_text(value)
        elif command == "enter":
            if delay:
                schedule_key_names(delay, "enter")
                delay += 1
            else:
                push_key(KEY_NAMES["enter"])
        elif command == "back":
            if delay:
                schedule_key_names(delay, "back")
                delay += 1
            else:
                push_key(KEY_NAMES["back"])
        elif command == "touch":
            parts = value.replace(",", " ").split()
            if len(parts) < 2:
                raise ValueError("touch expects: touch X Y [GESTURE]")
            gesture = int(parts[2]) if len(parts) > 2 else 6
            set_touch_point(int(parts[0]), int(parts[1]), gesture)
        elif command == "gesture":
            parts = value.replace(",", " ").split()
            if not parts:
                raise ValueError("gesture expects: gesture CODE [X Y]")
            x = int(parts[1]) if len(parts) > 1 else _touch_point[0]
            y = int(parts[2]) if len(parts) > 2 else _touch_point[1]
            set_touch_point(x, y, int(parts[0]))
        elif command == "battery":
            set_battery_percentage(int(value))
        elif command == "open":
            request_open(value)
            delay = max(delay, 120)
        elif command == "app":
            request_app(value)
            delay = max(delay, 180)
        elif command == "game":
            request_game(value)
            delay = max(delay, 180)
        elif command in ("wait", "sleep", "frames"):
            try:
                delay += int(value or "1")
            except ValueError:
                delay += 1
        else:
            raise ValueError("Unknown script command: " + command)


def request_open(name):
    global open_target
    open_target = name
    key = name.lower()
    if key in LIBRARY_ITEMS:
        push_key(KEY_NAMES["enter"])
        for _ in range(LIBRARY_ITEMS[key]):
            push_key(KEY_NAMES["down"])
        push_key(KEY_NAMES["enter"])


def request_app(name):
    target = str(name).lower()
    if target.endswith(".py"):
        target = target[:-3]
    apps = _list_menu_apps(sd_root + "/picoware/apps")
    index = -1
    for i, app in enumerate(apps):
        if app.lower() == target:
            index = i
            break
    if index < 0:
        raise LaunchTargetError("app not found: " + str(name))
    try:
        from picoware.applications import applications

        applications._applications_index = index
    except Exception:
        pass
    request_open("Applications")
    schedule_key_names(80, "enter")
    return True


def request_game(name):
    target = str(name).lower()
    if target.endswith(".py"):
        target = target[:-3]
    games = ["Ghouls"]
    games.extend(_list_menu_apps(sd_root + "/picoware/apps/games"))
    index = -1
    for i, game in enumerate(games):
        if game.lower() == target:
            index = i
            break
    if index < 0:
        raise LaunchTargetError("game not found: " + str(name))
    try:
        from picoware.applications import games as games_app

        games_app._games_index = index
    except Exception:
        pass
    request_open("Games")
    schedule_key_names(80, "enter")
    return True


def _list_menu_apps(path):
    try:
        files = os.listdir(path)
    except OSError:
        files = []
    apps = []
    for item in files:
        if item.startswith("."):
            continue
        if item.endswith(".py"):
            apps.append(item[:-3])
        if item.endswith(".mpy"):
            apps.append(item[:-4])
    apps.sort()
    return apps


def print_capabilities():
    audio_player = native_helper_path("audio/sdl_audio_player")
    radio_player = native_helper_path("audio/sdl_radio_player")
    gameboy_runner = root + "/simulator/gameboy/sim_gameboy_runner"
    ghouls_sidecar = native_helper_path("native/sim_frame_sidecar")
    viewer_bin = native_helper_path("viewer/sdl_fb_viewer")
    jpeg_status = "real" if _host_command_exists("djpeg") else "partial"
    rows = (
        ("lcd", "real" if _exists(viewer_bin) else "partial", "RGB565 framebuffer + SDL viewer sidecar"),
        ("keyboard", "real", "SDL/scripted key queue"),
        ("touch", "simulated", "scripted/viewer touch point and gesture state for touch boards"),
        ("sd_mp", "real", "host directory mapped to simulated SD"),
        ("network", "real" if network_mode == "real" else "fixture", "host sockets/TLS or strict offline fixtures"),
        ("ubluetooth", "simulated", "virtual BLE scan/GATT/UART, no host radio"),
        ("audio", "real" if _exists(audio_player) and _exists(radio_player) else "partial", "SDL/minimp3 local MP3/WAV and HTTP radio sidecars plus silent model"),
        ("jpegdec", jpeg_status, "host djpeg decode with visible placeholder fallback"),
        ("bmp", "real", "direct uncompressed BMP decoder"),
        ("battery", "simulated", "scriptable battery percentage"),
        ("psram", "simulated", "global byte heap + LCD RGB565 render"),
        ("engine", "simulated", "2D lifecycle/collision helpers plus deterministic 3D sprite/wall projection"),
        ("gameboy", "real" if _exists(gameboy_runner) else "partial", "Walnut-CGB native RGB565 frame/input helper with placeholder fallback"),
        ("ghouls", "partial" if _exists(ghouls_sidecar) else "simulated", "Python deterministic scene plus optional native sidecar"),
        ("uf2loader", "simulated", "records and validates flash request"),
        ("machine", "simulated", "Pin/UART/I2S/PWM/USBDevice state/logging shims, no host USB device"),
    )
    for name, status, detail in rows:
        print(name + "\t" + status + "\t" + detail)


def _host_command_exists(name):
    status = os.system("command -v " + name + " >/dev/null 2>&1")
    return status == 0


def poll_events():
    if _lcd is not None:
        _lcd.poll_events()
    if viewer and viewer_frame_path:
        try:
            os.stat(viewer_frame_path + ".quit")
            raise StopSimulation()
        except OSError:
            pass
    poll_viewer_controls()
    poll_viewer_keys()
    _poll_delayed_keys()


def poll_viewer_controls():
    global _control_offset, audio_muted
    if not viewer or not control_path:
        return
    try:
        st = os.stat(control_path)
        size = st[6]
        if size <= _control_offset:
            return
        with open(control_path, "rb") as handle:
            handle.seek(_control_offset)
            data = handle.read()
        _control_offset = size
    except OSError:
        return
    try:
        text = data.decode()
    except AttributeError:
        text = str(data, "utf-8")
    for raw in text.split("\n"):
        command = raw.strip().lower()
        if not command:
            continue
        if command == "screenshot":
            path = sd_root + "/sim_screenshot_" + str(frame_count) + ".bmp"
            if _lcd is not None:
                try:
                    _lcd.screenshot(path)
                    _log_event("screenshot " + path)
                except Exception as e:
                    _log_event("screenshot failed " + str(e))
        elif command == "mute":
            audio_muted = not audio_muted
            cmd = _safe_sd_path(sd_root, "sim_audio.cmd")
            try:
                with open(cmd, "w") as handle:
                    handle.write("volume " + ("0" if audio_muted else "100") + "\n")
            except OSError:
                pass
            _log_event("audio muted " + str(audio_muted))
            _write_status(True)
        elif command == "restart":
            _log_event("restart requested")
            raise RestartSimulation(False)
        elif command == "reset":
            _log_event("reset requested")
            raise RestartSimulation(True)
        else:
            _log_event("unknown control " + command)


def poll_viewer_keys():
    global _viewer_key_offset
    if not viewer or not viewer_keys_path:
        return
    try:
        st = os.stat(viewer_keys_path)
        size = st[6]
        if size <= _viewer_key_offset:
            return
        with open(viewer_keys_path, "rb") as handle:
            handle.seek(_viewer_key_offset)
            data = handle.read()
        _viewer_key_offset = size
    except OSError:
        return

    try:
        text = data.decode()
    except AttributeError:
        text = str(data, "utf-8")
    for line in text.split("\n"):
        if line:
            parts = line.split()
            try:
                if parts[0] == "touch" and len(parts) >= 3:
                    gesture = int(parts[3]) if len(parts) > 3 else 6
                    set_touch_point(int(parts[1]), int(parts[2]), gesture)
                    continue
                if len(parts) >= 2 and parts[0] in ("down", "up"):
                    code = int(parts[1])
                    repeat = len(parts) >= 3 and int(parts[2]) != 0
                    if parts[0] == "down":
                        _held_keys[code] = True
                        if not repeat:
                            push_key(code)
                            _record_key(code)
                    else:
                        _held_keys.pop(code, None)
                else:
                    code = int(line)
                    push_key(code)
                    _record_key(code)
            except ValueError:
                pass


def frame_swapped():
    global frame_count
    pace_frame()
    frame_count += 1
    _write_status(False)
    if screenshot_path and _lcd is not None:
        _lcd.screenshot(screenshot_path)
    if max_frames and frame_count >= max_frames:
        _check_expectations(True)
        raise StopSimulation()


def loop_polled():
    global loop_count
    loop_count += 1
    poll_events()
    _write_status(False)
    if max_frames and loop_count >= max_frames * 200:
        _check_expectations(True)
        raise StopSimulation()


def finish_recording():
    _flush_record_text()


def _write_status(force=False):
    global _last_status_ms
    if not status_path:
        return
    now = _ticks_ms()
    if not force and _ticks_diff(now, _last_status_ms) < 250:
        return
    _last_status_ms = now
    fps = 0
    if _frame_interval_ms > 0:
        fps = int(1000 / _frame_interval_ms)
    text = (
        "Picoware Simulator\n"
        + "View: "
        + str(_current_view_name or "(boot)")
        + "\nFrames: "
        + str(frame_count)
        + " Loops: "
        + str(loop_count)
        + "\nFPS target: "
        + str(fps if fps else "fast")
        + "\nNetwork: "
        + str(network_mode)
        + " Audio: "
        + str(audio_mode)
        + (" muted" if audio_muted else "")
        + "\nSD profile: "
        + str(sd_profile)
        + "\nInput: "
        + ",".join(_recent_input[-8:])
    )
    try:
        with open(status_path, "w") as handle:
            handle.write(text)
    except OSError:
        pass


def host_path(path):
    raw = str(path).replace("\\", "/")
    if raw.startswith("/sd/"):
        raw = raw[4:]
    elif raw.startswith("/sdcard/"):
        raw = raw[8:]
    elif raw.startswith("/"):
        raw = raw[1:]
    return sd_root + ("/" + raw if raw else "")


def app_source_path(path):
    raw = str(path).replace("\\", "/")
    for prefix in ("/sd/picoware/apps", "/sdcard/picoware/apps", "/picoware/apps", "picoware/apps"):
        if raw == prefix:
            return apps_source
        if raw.startswith(prefix + "/"):
            return apps_source + "/" + raw[len(prefix) + 1 :]
    return None


def mkdir_p(path):
    parts = path.replace("\\", "/").split("/")
    current = "/" if path.startswith("/") else ""
    for part in parts:
        if not part:
            continue
        current = current + ("" if current.endswith("/") or not current else "/") + part
        try:
            os.mkdir(current)
        except OSError:
            pass
