import json
import os
import time


class StopSimulation(SystemExit):
    pass


class RestartSimulation(SystemExit):
    def __init__(self, reset=False):
        self.reset = reset


root = "."
sd_root = "sim_mp/sdcard"
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
_lcd = None
_wait_view = ""
_assert_text = ""
_seen_wait_view = False
_seen_assert_text = False
_current_view_name = ""
_recent_text = []
_recent_input = []
_record_text = ""


KEY_NAMES = {
    "up": 0xB5,
    "down": 0xB6,
    "left": 0xB4,
    "right": 0xB7,
    "escape": 0xB1,
    "esc": 0xB1,
    "back": 0xB1,
    "backspace": 8,
    "enter": 13,
    "center": 13,
    "newline": 13,
    "space": 32,
    "tab": 9,
    "alt": 0xA1,
    "shift": 0xA2,
    "left_shift": 0xA2,
    "right_shift": 0xA3,
    "sym": 0xA4,
    "ctrl": 0xA5,
    "control": 0xA5,
    "caps_lock": 0xC1,
    "capslock": 0xC1,
    "ctrl_up": 0xC2,
    "ctrl_down": 0xC3,
    "break": 0xD0,
    "insert": 0xD1,
    "home": 0xD2,
    "delete": 0xD4,
    "end": 0xD5,
    "page_up": 0xD6,
    "pageup": 0xD6,
    "page_down": 0xD7,
    "pagedown": 0xD7,
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
    "comma": 44,
    "period": 46,
    "dot": 46,
    "slash": 47,
    "backslash": 92,
    "minus": 45,
    "dash": 45,
    "equal": 61,
    "equals": 61,
    "semicolon": 59,
    "quote": 39,
    "apostrophe": 39,
    "double_quote": 34,
    "left_bracket": 91,
    "right_bracket": 93,
    "left_brace": 123,
    "right_brace": 125,
    "backtick": 96,
    "grave": 96,
    "tilde": 126,
    "pipe": 124,
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
    global frame_count, loop_count, open_target, _keys, _delayed_keys, _lcd
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
    # Keep automation fast by default, but make interactive runs real-time.
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


def build_native(target):
    script = root + "/sim_mp/build.sh"
    status = os.system("sh " + _quote(script) + " " + _quote(target))
    return status == 0


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
            "deepseek_api_key": "",
            "exit_button": 177,
            "gmt_offset": 0,
            "lvgl_mode": False,
            "onscreen_keyboard": False,
            "openai_api_key": "",
            "server_username": "simulator",
            "server_password": "",
            "theme_color": 31,
            "wifi_ssid": "Picoware-Sim",
            "wifi_password": "",
        },
        ("server_username", "server_password", "wifi_ssid", "wifi_password"),
    )
    _write_if_missing(sd_root + "/picoware/settings/server_username.json", '{"username":"simulator"}')
    _write_if_missing(sd_root + "/picoware/settings/server_password.json", '{"password":""}')
    _write_if_missing(sd_root + "/picoware/wifi/ssid.json", '{"ssid":"Picoware-Sim"}')
    _write_if_missing(sd_root + "/picoware/wifi/password.json", '{"password":""}')
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

    # Symlink app files into simulated SD for __import__
    _link_app_files()


def _link_app_files():
    """Symlink app files from both apps_unfrozen/ (.py source) and apps/
    (.mpy compiled) into the simulated SD card at sd_root/picoware/apps/.
    Recurses into subdirectories so that apps in subfolders (games,
    flip_social, etc.) are also available.  This is needed because
    __import__ searches sys.path via the raw VFS, not through sd_mp."""
    target = sd_root + "/picoware/apps"
    _link_app_files_into(apps_source, target)
    # Also link compiled .mpy files from the apps/ directory — subdirectory
    # apps only exist as .mpy, not as .py in apps_unfrozen/.
    _compiled = root + "/builds/MicroPython/apps"
    if _compiled != apps_source:
        _link_app_files_into(_compiled, target, skip_if_py_exists=True)


def _link_app_files_into(src_dir, dst_dir, skip_if_py_exists=False):
    """Recursively symlink .py/.mpy files from src_dir into dst_dir.

    When *skip_if_py_exists* is True, a .mpy file is skipped if a .py
    file with the same base name already exists (or is symlinked) in
    *dst_dir*.  This avoids duplicate app listings when both a source
    .py and a compiled .mpy are available."""
    mkdir_p(dst_dir)
    try:
        entries = os.listdir(src_dir)
    except OSError:
        return
    for entry in entries:
        if entry.startswith(".") or entry == "__init__.py":
            continue
        src = src_dir + "/" + entry
        dst = dst_dir + "/" + entry
        try:
            st = os.stat(src)
        except OSError:
            continue
        if st[0] & 0x4000:  # directory
            _link_app_files_into(src, dst, skip_if_py_exists)
        else:
            # If we're linking .mpy files and a .py counterpart already
            # exists in the destination, skip to avoid duplicates.
            if skip_if_py_exists and entry.endswith(".mpy"):
                _py_name = entry[:-4] + ".py"
                _py_dst = dst_dir + "/" + _py_name
                if _exists(_py_dst):
                    continue
            # Remove stale symlink / file before re-creating
            _rm_f(dst)
            # Try os.symlink, fall back to ln -sf
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
        elif command == "open":
            request_open(value)
            delay = max(delay, 80)
        elif command == "app":
            request_app(value)
            delay = max(delay, 80)
        elif command == "game":
            request_game(value)
            delay = max(delay, 80)
        elif command in ("wait", "sleep", "frames"):
            # Queue-based script version. Timed waits pass through.
            pass
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
    request_open("Applications")
    target = str(name).lower()
    if target.endswith(".py"):
        target = target[:-3]
    try:
        files = os.listdir(apps_source)
    except OSError:
        files = []
    apps = []
    for item in files:
        if item.startswith("."):
            continue
        if item.endswith(".py"):
            apps.append(item[:-3])
    apps.sort()
    index = -1
    for i, app in enumerate(apps):
        if app.lower() == target:
            index = i
            break
    if index < 0:
        print("[sim] app not found:", name)
        return
    keys = []
    for _ in range(index):
        keys.append("down")
    keys.append("enter")
    schedule_key_names(80, ",".join(keys))


def request_game(name):
    request_open("Games")
    target = str(name).lower()
    if target.endswith(".py"):
        target = target[:-3]
    try:
        files = os.listdir(apps_source + "/games")
    except OSError:
        files = []
    games = ["Ghouls"]
    py_games = []
    for item in files:
        if item.startswith("."):
            continue
        if item.endswith(".py"):
            py_games.append(item[:-3])
    py_games.sort()
    games.extend(py_games)
    index = -1
    for i, game in enumerate(games):
        if game.lower() == target:
            index = i
            break
    if index < 0:
        print("[sim] game not found:", name)
        return
    keys = []
    for _ in range(index):
        keys.append("down")
    keys.append("enter")
    schedule_key_names(80, ",".join(keys))


def print_capabilities():
    audio_player = root + "/sim_mp/audio/sdl_audio_player"
    radio_player = root + "/sim_mp/audio/sdl_radio_player"
    frame_sidecar = root + "/sim_mp/native/sim_frame_sidecar"
    viewer_bin = root + "/sim_mp/viewer/sdl_fb_viewer"
    jpeg_status = "real" if _host_command_exists("djpeg") else "partial"
    rows = (
        ("lcd", "real" if _exists(viewer_bin) else "partial", "RGB565 framebuffer + SDL viewer sidecar"),
        ("keyboard", "real", "SDL/scripted key queue"),
        ("sd_mp", "real", "host directory mapped to simulated SD"),
        ("network", "real" if network_mode == "real" else "fixture", "host sockets/TLS or strict offline fixtures"),
        ("ubluetooth", "simulated", "virtual BLE scan/GATT/UART"),
        ("audio", "real" if _exists(audio_player) and _exists(radio_player) else "partial", "SDL/minimp3 local MP3/WAV and HTTP radio sidecars plus silent model"),
        ("jpegdec", jpeg_status, "host djpeg decode with visible placeholder fallback"),
        ("bmp", "real", "direct uncompressed BMP decoder"),
        ("psram", "simulated", "global byte heap + LCD RGB565 render"),
        ("engine", "partial", "2D callbacks/collision plus basic 3D sprite/wall projection"),
        ("gameboy", "partial" if _exists(frame_sidecar) else "unsupported", "native RGB565 frame/input sidecar shell"),
        ("ghouls", "partial" if _exists(frame_sidecar) else "unsupported", "native RGB565 frame/input sidecar shell with seeded assets"),
        ("uf2loader", "simulated", "records and validates flash request"),
        ("machine", "simulated", "Pin/UART/I2S/PWM/USBDevice state/logging shims"),
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
            cmd = sd_root + "/sim_audio.cmd"
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
            try:
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
