"""MicroPython-only Picoware simulator entrypoint."""

import builtins
import gc
import os
import sys


def _dirname(path):
    """Return the directory portion of a path."""
    path = path.replace("\\", "/")
    if "/" not in path:
        return "."
    value = path.rsplit("/", 1)[0]
    return value if value else "/"


def _abspath(path):
    """Return an absolute path, resolving relative to cwd."""
    if path.startswith("/"):
        return path
    return os.getcwd() + "/" + path


THIS_DIR = _dirname(_abspath(sys.argv[0]))
ROOT = _dirname(THIS_DIR)
HARDWARE_DIR = THIS_DIR + "/hardware"
MICROPYTHON_DIR = ROOT + "/src/MicroPython"

_BOARD_DISPLAY_SIZES = {
    "picocalc-pico": (320, 320),
    "picocalc-picow": (320, 320),
    "picocalc-pico2": (320, 320),
    "picocalc-pico2w": (320, 320),
    "picocalc-pimoroni-2w": (320, 320),
    "pimoroni-2w": (320, 320),
    "waveshare-1.28-rp2350": (240, 240),
    "waveshare-1.43-rp2350": (466, 466),
    "waveshare-1.69-rp2350": (240, 280),
    "waveshare-3.49-rp2350": (172, 640),
    "crowpanel-10.1": (1024, 600),
    "crowpanel": (1024, 600),
    "cardputer": (240, 135),
    "waveshare-2.06": (410, 502),
    "waveshare-2.06-esp32s3": (410, 502),
    "pancake": (320, 480),
    "v8": (240, 320),
    "flipper-zero": (128, 64),
    "flipper": (128, 64),
    "desktop": (320, 320),
    "unix": (320, 320),
}


def _insert_path(path):
    """Insert a directory into sys.path if not present."""
    if path not in sys.path:
        sys.path.insert(0, path)


def _simulator_display_size(board_name):
    """Return a framebuffer size that fits the default Unix MicroPython heap."""
    width, height = _BOARD_DISPLAY_SIZES.get(board_name, (320, 320))
    if width * height > 320 * 480:
        return 320, 320
    return width, height


def _parse_args(argv):
    """Parse command-line arguments into an options dict."""
    opts = {
        "headless": True,
        "viewer": False,
        "frames": 0,
        "exit_after_frames": 0,
        "scale": 2,
        "sd": THIS_DIR + "/sdcard",
        "apps_source": ROOT + "/builds/MicroPython/apps_unfrozen",
        "board": "picocalc-pico2w",
        "keys": "",
        "keys_text": "",
        "open": "",
        "app": "",
        "game": "",
        "screenshot": "",
        "trace_keys": False,
        "trace_views": False,
        "trace_imports": False,
        "network": "real",
        "bluetooth": "virtual",
        "audio": "real",
        "speed": "auto",
        "fps": 0,
        "capabilities": False,
        "coverage": "",
        "script": "",
        "wait_view": "",
        "assert_text": "",
        "sim_check": False,
        "agent_check": False,
        "reset_sd": False,
        "sd_profile": "dev",
        "record": "",
    }
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--headless":
            opts["headless"] = True
        elif arg == "--viewer":
            opts["viewer"] = True
            opts["headless"] = True
        elif arg == "--sdl":
            opts["headless"] = False
        elif arg == "--frames" and i + 1 < len(argv):
            i += 1
            opts["frames"] = int(argv[i])
        elif arg == "--exit-after-frames" and i + 1 < len(argv):
            i += 1
            opts["exit_after_frames"] = int(argv[i])
        elif arg == "--scale" and i + 1 < len(argv):
            i += 1
            opts["scale"] = int(argv[i])
        elif arg == "--sd" and i + 1 < len(argv):
            i += 1
            opts["sd"] = _abspath(argv[i])
        elif arg == "--apps-source" and i + 1 < len(argv):
            i += 1
            opts["apps_source"] = _abspath(argv[i])
        elif arg == "--board" and i + 1 < len(argv):
            i += 1
            opts["board"] = argv[i]
        elif arg == "--keys" and i + 1 < len(argv):
            i += 1
            opts["keys"] = argv[i]
        elif arg == "--keys-text" and i + 1 < len(argv):
            i += 1
            opts["keys_text"] = argv[i]
        elif arg == "--open" and i + 1 < len(argv):
            i += 1
            opts["open"] = argv[i]
        elif arg == "--app" and i + 1 < len(argv):
            i += 1
            opts["app"] = argv[i]
        elif arg == "--game" and i + 1 < len(argv):
            i += 1
            opts["game"] = argv[i]
        elif arg == "--screenshot" and i + 1 < len(argv):
            i += 1
            opts["screenshot"] = argv[i]
        elif arg == "--trace-keys":
            opts["trace_keys"] = True
        elif arg == "--trace-views":
            opts["trace_views"] = True
        elif arg == "--trace-imports":
            opts["trace_imports"] = True
        elif arg == "--network" and i + 1 < len(argv):
            i += 1
            opts["network"] = argv[i]
        elif arg == "--bluetooth" and i + 1 < len(argv):
            i += 1
            opts["bluetooth"] = argv[i]
        elif arg == "--audio" and i + 1 < len(argv):
            i += 1
            opts["audio"] = argv[i]
        elif arg == "--speed" and i + 1 < len(argv):
            i += 1
            opts["speed"] = argv[i]
        elif arg == "--fps" and i + 1 < len(argv):
            i += 1
            opts["fps"] = int(argv[i])
        elif arg == "--capabilities":
            opts["capabilities"] = True
        elif arg == "--coverage" and i + 1 < len(argv):
            i += 1
            opts["coverage"] = argv[i]
        elif arg == "--script" and i + 1 < len(argv):
            i += 1
            opts["script"] = _abspath(argv[i])
        elif arg == "--wait-view" and i + 1 < len(argv):
            i += 1
            opts["wait_view"] = argv[i]
        elif arg == "--assert-text" and i + 1 < len(argv):
            i += 1
            opts["assert_text"] = argv[i]
        elif arg == "--sim-check":
            opts["sim_check"] = True
        elif arg == "--agent-check":
            opts["agent_check"] = True
        elif arg == "--reset-sd":
            opts["reset_sd"] = True
        elif arg == "--sd-profile" and i + 1 < len(argv):
            i += 1
            opts["sd_profile"] = argv[i]
        elif arg == "--record" and i + 1 < len(argv):
            i += 1
            opts["record"] = _abspath(argv[i])
        elif arg == "--help":
            print("usage: micropython simulator/run.py [--viewer] [--sdl] [--headless] [--frames N] [--exit-after-frames N] [--speed auto|real|pico2w|fast|unlimited] [--fps N] [--network real|offline] [--bluetooth virtual|off] [--audio real|silent] [--keys a,b] [--keys-text TEXT] [--record FILE] [--open NAME] [--app NAME] [--game NAME] [--apps-source PATH] [--reset-sd] [--sd-profile clean|dev|media|network-fixtures] [--screenshot PATH] [--coverage apps|games|all] [--script FILE] [--wait-view NAME] [--assert-text TEXT] [--capabilities] [--agent-check] [--sim-check]")
            raise SystemExit
        else:
            print("Unknown argument:", arg)
            raise SystemExit
        i += 1
    return opts


def _mkdir_p(path):
    """Create a directory tree, ignoring existing directories."""
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


def _remove_tree(path):
    """Recursively delete a directory tree."""
    try:
        names = os.listdir(path)
    except OSError:
        try:
            os.remove(path)
        except OSError:
            pass
        return
    for name in names:
        child = path.rstrip("/") + "/" + name
        try:
            mode = os.stat(child)[0]
        except OSError:
            # os.stat() fails for a broken symlink.  Remove the link node so
            # --reset-sd can actually clear persistent simulator fixtures.
            try:
                os.remove(child)
            except OSError:
                pass
            continue
        if mode & 0x4000:
            _remove_tree(child)
        else:
            try:
                os.remove(child)
            except OSError:
                pass
    try:
        os.rmdir(path)
    except OSError:
        pass


def _safe_reset_sd(path):
    """Reset the SD card path, with safety guards."""
    target = _abspath(path)
    sim_default = THIS_DIR + "/sdcard"
    allowed = target == sim_default or target.startswith("/tmp/")
    if not allowed:
        print("--reset-sd refused unsafe path:", target)
        print("Use the default simulator/sdcard or a path under /tmp for destructive reset.")
        raise SystemExit(2)
    if target in ("", "/", "/tmp", THIS_DIR, ROOT):
        print("--reset-sd refused root-like path:", target)
        raise SystemExit(2)
    _remove_tree(target)
    _mkdir_p(target)


def _run_main():
    """Execute the Picoware main.py entry point."""
    fatal_errors = []

    def main_print(*args, **kwargs):
        separator = kwargs.get("sep", " ")
        message = separator.join(str(arg) for arg in args)
        if message.startswith("Error occurred:"):
            fatal_errors.append(message)
        builtins.print(*args, **kwargs)

    namespace = {
        "__name__": "__sim_picoware_main__",
        "__file__": MICROPYTHON_DIR + "/main.py",
        "print": main_print,
    }
    with open(MICROPYTHON_DIR + "/main.py", "r") as handle:
        code = handle.read()
    exec(code, namespace)
    try:
        result = namespace["main"]()
    except BaseException:
        if fatal_errors:
            raise RuntimeError(
                "Picoware main reported a fatal error: " + fatal_errors[-1]
            )
        raise
    if result is False:
        raise RuntimeError("Picoware main reported a fatal error")
    if fatal_errors:
        raise RuntimeError(
            "Picoware main reported a fatal error: " + fatal_errors[-1]
        )


def _install_view_tracking():
    """Report ViewManager transitions to the simulator harness."""
    try:
        import sim_runtime
        from picoware.system.input import Input
        from picoware.system.view_manager import ViewManager
    except Exception:
        return

    if getattr(ViewManager, "_sim_view_tracking_installed", False):
        return

    def current_name(manager):
        view = getattr(manager, "_current_view", None)
        return getattr(view, "name", "")

    def note(manager):
        try:
            name = current_name(manager)
            if name != getattr(sim_runtime, "_current_view_name", ""):
                sim_runtime.note_view(name)
        except Exception:
            pass

    def note_name(name):
        try:
            if str(name or "") != getattr(sim_runtime, "_current_view_name", ""):
                sim_runtime.note_view(name)
        except Exception:
            pass

    original_set = ViewManager.set
    original_switch_to = ViewManager.switch_to
    original_back = ViewManager.back
    original_remove = ViewManager.remove

    def tracked_set(self, *args, **kwargs):
        if args:
            note_name(args[0])
        result = original_set(self, *args, **kwargs)
        note(self)
        return result

    def tracked_switch_to(self, *args, **kwargs):
        if args:
            note_name(args[0])
        result = original_switch_to(self, *args, **kwargs)
        note(self)
        return result

    def tracked_back(self, *args, **kwargs):
        result = original_back(self, *args, **kwargs)
        note(self)
        return result

    def tracked_remove(self, *args, **kwargs):
        result = original_remove(self, *args, **kwargs)
        note(self)
        return result

    def tracked_input_button(self):
        from picoware.system.boards import (
            BOARD_CARDPUTER,
            BOARD_CROWPANEL_10_1,
            BOARD_FLIPPER_ZERO,
            BOARD_PANCAKE,
            BOARD_WAVESHARE_2_06,
        )

        sim_runtime.input_polled()
        if self._current_board_id in (
            BOARD_CROWPANEL_10_1,
            BOARD_WAVESHARE_2_06,
            BOARD_PANCAKE,
        ):
            self._poll_touch()
        elif self._current_board_id == BOARD_CARDPUTER:
            from cardputer_keyboard import key_available, poll

            poll()
            if key_available():
                self.on_key_callback()
        elif self._current_board_id == BOARD_FLIPPER_ZERO:
            from flipper_input import key_available, poll

            poll()
            if key_available():
                self.on_key_callback()
        return self._last_button

    ViewManager.set = tracked_set
    ViewManager.switch_to = tracked_switch_to
    ViewManager.back = tracked_back
    ViewManager.remove = tracked_remove
    Input.button = property(tracked_input_button)
    ViewManager._sim_view_tracking_installed = True


def _quote(path):
    """Shell-quote a path string."""
    return "'" + path.replace("'", "'\"'\"'") + "'"


def _interpreter_command():
    """Return the current MicroPython executable for child simulator runs."""
    executable = getattr(sys, "executable", "")
    return _quote(executable if executable else "micropython")


def _board_option(opts):
    """Return the selected simulator board as a quoted child-process option."""
    return " --board " + _quote(opts["board"])


def _file_exists(path):
    """Return True if the given path exists."""
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _is_newer(path, other):
    """Return True if path was modified after other."""
    try:
        return os.stat(path)[8] > os.stat(other)[8]
    except Exception:
        return True


def _json_escape(text):
    """Escape a string for inclusion in JSON."""
    text = str(text)
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    text = text.replace("\n", "\\n")
    text = text.replace("\r", "\\r")
    text = text.replace("\t", "\\t")
    return text


def _list_py_entries(path):
    """Return sorted list of .py module names in a directory."""
    try:
        files = os.listdir(path)
    except OSError:
        return []
    out = []
    for item in files:
        if item.startswith(".") or item == "__init__.py":
            continue
        if item.endswith(".py"):
            out.append(item[:-3])
    out.sort()
    return out


def _write_coverage_report(path, mode, rows):
    """Write a JSON coverage report to disk."""
    _mkdir_p(_dirname(path))
    passed = 0
    failed = 0
    skipped = 0
    with open(path, "w") as handle:
        handle.write('{"mode":"' + _json_escape(mode) + '","results":[')
        first = True
        for row in rows:
            status = row[2]
            if status == "pass":
                passed += 1
            elif status == "fail":
                failed += 1
            else:
                skipped += 1
            if not first:
                handle.write(",")
            first = False
            handle.write(
                '{"kind":"'
                + _json_escape(row[0])
                + '","name":"'
                + _json_escape(row[1])
                + '","status":"'
                + _json_escape(row[2])
                + '","reason":"'
                + _json_escape(row[3])
                + '","log":"'
                + _json_escape(row[4])
                + '"}'
            )
        handle.write('],"summary":{"pass":%d,"fail":%d,"skipped":%d}}' % (passed, failed, skipped))
    print("coverage", mode, "pass", passed, "fail", failed, "skipped", skipped)
    print("report", path)


def _run_coverage(opts):
    """Run headless coverage sweep over apps and games."""
    mode = opts["coverage"].lower()
    if mode not in ("apps", "games", "all"):
        print("--coverage expects apps, games, or all")
        raise SystemExit
    report_dir = opts["sd"] + "/sim_reports"
    _mkdir_p(report_dir)
    rows = []
    entries = []
    if mode in ("apps", "all"):
        for name in _list_py_entries(opts["apps_source"]):
            entries.append(("app", name))
    if mode in ("games", "all"):
        entries.append(("game", "Ghouls"))
        for name in _list_py_entries(opts["apps_source"] + "/games"):
            entries.append(("game", name))
    if not entries:
        rows.append(("coverage", mode, "skipped", "no entries found", ""))
    for kind, name in entries:
        safe = (kind + "-" + name).replace("/", "_").replace(" ", "_")
        log_path = report_dir + "/" + safe + ".log"
        cmd = (
            _interpreter_command()
            + " "
            + _quote(THIS_DIR + "/run.py")
            + " --headless --frames 220 --audio silent --network offline --sd "
            + _quote(opts["sd"])
            + " --apps-source "
            + _quote(opts["apps_source"])
            + _board_option(opts)
            + (" --app " if kind == "app" else " --game ")
            + _quote(name)
            + " --wait-view "
            + _quote(("app_" if kind == "app" else "game_") + name)
            + " >"
            + _quote(log_path)
            + " 2>&1"
        )
        status = os.system(cmd)
        if status == 0:
            rows.append((kind, name, "pass", "", log_path))
            print("[coverage:pass]", kind, name)
        else:
            rows.append((kind, name, "fail", "child run exited " + str(status), log_path))
            print("[coverage:fail]", kind, name, status)
    _write_coverage_report(report_dir + "/coverage-" + mode + ".json", mode, rows)
    if any(row[2] == "fail" for row in rows):
        raise SystemExit(1)


def _build_native(target, check=False):
    """Build a native simulator helper via build.sh."""
    cmd = "sh " + _quote(THIS_DIR + "/build.sh")
    if check:
        cmd += " --check"
    cmd += " " + _quote(target)
    return os.system(cmd) == 0


def _run_sim_check(opts):
    """Run the simulator self-check suite."""
    board_name = str(opts["board"]).lower().replace("_", "-")
    if board_name in ("desktop", "unix"):
        _run_desktop_native_check(opts)
    _run_library_route_check()
    _run_stale_app_link_check(opts)
    _run_duplicate_app_link_check(opts)
    commands = (
        "sh "
        + _quote(THIS_DIR + "/build.sh")
        + " --check",
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --frames 30 --wait-view desktop_view --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"])
        + _board_option(opts),
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --app Calculator --wait-view app_Calculator --frames 160 --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"])
        + _board_option(opts),
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --open Agent --wait-view agent --frames 220 --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"])
        + _board_option(opts),
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --open System --wait-view system --frames 220 --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"])
        + _board_option(opts),
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --open MMBasic --wait-view mmbasic --keys enter --assert-text "
        + _quote("MMBasic 6.03")
        + " --frames 300 --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"])
        + _board_option(opts),
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --app Forecast --wait-view app_Forecast --frames 220 --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"])
        + _board_option(opts),
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --app MicroBrowser --wait-view app_MicroBrowser --frames 220 --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"])
        + _board_option(opts),
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --board pancake --app keyboard-simple --frames 40 --wait-view app_keyboard-simple --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"]),
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --board waveshare-1.69-rp2350 --frames 30 --wait-view desktop_view --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"]),
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --board waveshare-2.06 --frames 30 --wait-view desktop_view --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"]),
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --board crowpanel --frames 30 --wait-view desktop_view --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"]),
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --board v8 --frames 30 --wait-view desktop_view --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"]),
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --board flipper-zero --app Calculator --frames 40 --wait-view app_Calculator --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"]),
    )
    for cmd in commands:
        status = os.system(cmd)
        if status != 0:
            print("[sim-check:fail]", cmd, status)
            raise SystemExit(1)
    _run_keyboard_background_check()
    _run_lcd_parity_check()
    _run_uart_parity_check()
    _run_engine_parity_check()
    _run_board_parity_check()
    _run_font_parity_check()
    _run_scripts_fixture_check(opts)
    _run_touch_check()
    _run_waveshare_169_check()
    _run_v8_battery_check()
    _run_flipper_battery_check()
    _run_log_storage_check(opts)
    _run_audio_shutdown_check()
    _run_circular_choice_check()
    _run_fatal_exit_check(opts)
    _run_agent_mcp_contracts()
    _run_mjs_check()
    print("[sim-check:pass]")


def _run_desktop_native_check(opts):
    """Exercise the compiled Desktop MMBasic module and its host bridge."""
    try:
        import picoware_desktop
    except ImportError:
        raise RuntimeError(
            "sim-check requires the Desktop interpreter; "
            "run sh tools/run-micropython-desktop.sh --sim-check"
        )

    if picoware_desktop.BOARD_ID != 15:
        raise RuntimeError("Desktop interpreter board ID mismatch")
    expected_modules = ("auto_complete", "font", "mmbasic", "response", "vector")
    if picoware_desktop.native_modules() != expected_modules:
        raise RuntimeError("Desktop interpreter native module set mismatch")

    import auto_complete
    import font
    import lcd
    import mmbasic
    import response
    import sd_mp
    import sim_runtime
    import vector

    completion = auto_complete.AutoComplete()
    if not completion.add_word("desktop"):
        raise RuntimeError("native AutoComplete rejected a word")
    if completion.search("desk") != ("desktop",):
        raise RuntimeError("native AutoComplete search mismatch")
    font_size = font.FontSize(2)
    if font_size.spacing != 1:
        raise RuntimeError("native FontSize spacing mismatch")
    font_size.set_size(0)
    if font_size.size != 0:
        raise RuntimeError("native FontSize setter mismatch")
    native_response = response.Response()
    native_response.set_status_code(200)
    native_response.set_content(b"ok")
    if native_response.status_code != 200 or native_response.content != b"ok":
        raise RuntimeError("native Response state mismatch")
    native_vector = vector.Vector(1, 2, 3, True)
    if (native_vector.x, native_vector.y, native_vector.z) != (1, 2, 3):
        raise RuntimeError("native Vector state mismatch")

    original_headless = sim_runtime.headless
    original_lcd = sim_runtime.get_lcd()
    original_sd_root = sim_runtime.sd_root
    path = "sim_reports/mmbasic-native.bas"
    try:
        sim_runtime.headless = True
        sim_runtime.sd_root = opts["sd"]
        lcd.LCD()

        engine = mmbasic.MMBasic(0xFFFF, 0, 0x07E0, 320, 320, 8, 8, 0, 0)
        if engine._start():
            raise RuntimeError("native MMBasic accepted an empty start")
        if not engine._start(source='PRINT "Desktop native"\nEND'):
            raise RuntimeError("native MMBasic rejected source input")
        if engine.has_graphics:
            raise RuntimeError("native MMBasic misclassified console source")
        if engine.tick(5) != (1, "", 0):
            raise RuntimeError("native MMBasic END status mismatch")

        sd_mp.write(path, b'CLS\nDO WHILE INKEY$ = "": LOOP\n')
        engine = mmbasic.MMBasic(0xFFFF, 0, 0x07E0, 320, 320, 8, 8, 0, 0)
        if not engine._start(path=path):
            raise RuntimeError("native MMBasic rejected simulated SD input")
        if engine.tick(5) != (0, "", 0) or not engine.has_graphics:
            raise RuntimeError("native MMBasic graphics/input state mismatch")
        engine.feed_char("x")
        if engine.tick(5) != (1, "", 0):
            raise RuntimeError("native MMBasic input completion mismatch")
        engine.render(True)
    finally:
        sd_mp.remove(path)
        sim_runtime.set_lcd(original_lcd)
        sim_runtime.sd_root = original_sd_root
        sim_runtime.headless = original_headless
        gc.collect()
    print("[sim-check:ok] Desktop native logic and MMBasic hardware bridge")


def _run_library_route_check():
    """Keep simulator --open routes synchronized with the Library menu."""
    import sim_runtime

    source = MICROPYTHON_DIR + "/picoware/applications/library.py"
    marker = '_library.add_item("'
    items = []
    with open(source, "r") as handle:
        for line in handle:
            if marker not in line:
                continue
            label = line.split(marker, 1)[1].split('"', 1)[0]
            items.append(label)

    if not items:
        raise RuntimeError("simulator Library route check found no menu items")
    for index, label in enumerate(items):
        actual = sim_runtime.LIBRARY_ITEMS.get(label.lower())
        if actual != index:
            raise RuntimeError(
                "simulator Library route mismatch for "
                + label
                + ": expected "
                + str(index)
                + ", got "
                + str(actual)
            )
    indices = sorted(set(sim_runtime.LIBRARY_ITEMS.values()))
    if indices != list(range(len(items))):
        raise RuntimeError("simulator Library route indices are not contiguous")
    print("[sim-check:ok] Library routes synchronized (" + str(len(items)) + " items)")


def _run_stale_app_link_check(opts):
    """Verify persistent SD cleanup removes only broken managed links."""
    import sim_runtime

    probe = opts["sd"] + "/sim-stale-link-check"
    broken = probe + "/RemovedApp.py"
    local = probe + "/LocalApp.py"
    _mkdir_p(probe)
    with open(local, "w") as handle:
        handle.write("# user-installed simulator app\n")
    status = os.system(
        "ln -sf "
        + _quote(ROOT + "/builds/MicroPython/apps_unfrozen/RemovedApp.py")
        + " "
        + _quote(broken)
    )
    if status != 0 or "RemovedApp.py" not in os.listdir(probe):
        _remove_tree(probe)
        raise RuntimeError("simulator stale-link fixture setup failed")
    sim_runtime._prune_stale_links(probe)
    entries = os.listdir(probe)
    if "RemovedApp.py" in entries:
        _remove_tree(probe)
        raise RuntimeError("simulator stale app link was not removed")
    if "LocalApp.py" not in entries:
        _remove_tree(probe)
        raise RuntimeError("simulator stale-link cleanup removed a local app")
    _remove_tree(probe)
    print("[sim-check:ok] stale app links pruned, local apps preserved")


def _run_duplicate_app_link_check(opts):
    """Remove managed .mpy duplicates while preserving regular SD files."""
    import sd_mp
    import sim_runtime

    probe = opts["sd"] + "/sim-duplicate-link-check"
    source_py = probe + "/source-py"
    source_mpy = probe + "/source-mpy"
    destination = probe + "/apps"
    _mkdir_p(source_py)
    _mkdir_p(source_mpy)
    _mkdir_p(destination)
    with open(source_py + "/ManagedApp.py", "w") as handle:
        handle.write("# managed source app\n")
    with open(source_py + "/CaseApp.py", "w") as handle:
        handle.write("# canonical case app\n")
    with open(source_py + "/caseApp.py", "w") as handle:
        handle.write("# duplicate case app\n")
    with open(source_mpy + "/ManagedApp.mpy", "w") as handle:
        handle.write("managed compiled app\n")
    with open(source_mpy + "/LocalApp.mpy", "w") as handle:
        handle.write("compiled source placeholder\n")
    with open(destination + "/LocalApp.py", "w") as handle:
        handle.write("# local source app\n")
    with open(destination + "/LocalApp.mpy", "w") as handle:
        handle.write("local compiled app\n")

    status = os.system(
        "ln -sf "
        + _quote(source_py + "/caseApp.py")
        + " "
        + _quote(destination + "/caseApp.py")
    )
    if status != 0:
        _remove_tree(probe)
        raise RuntimeError("simulator case-duplicate fixture setup failed")
    sim_runtime._link_app_files_into(source_py, destination)
    case_entries = [name for name in os.listdir(destination)
                    if name.lower() == "caseapp.py"]
    if case_entries != ["CaseApp.py"]:
        _remove_tree(probe)
        raise RuntimeError("simulator case-insensitive app duplicate was not removed")
    merged_names = []
    seen_names = {}
    sd_mp._append_unique_names(
        merged_names, seen_names, ["caseApp.py", "CaseApp.py"]
    )
    if merged_names != ["CaseApp.py"]:
        _remove_tree(probe)
        raise RuntimeError("simulator FAT directory view exposed case duplicates")
    status = os.system(
        "ln -sf "
        + _quote(source_mpy + "/ManagedApp.mpy")
        + " "
        + _quote(destination + "/ManagedApp.mpy")
    )
    if status != 0:
        _remove_tree(probe)
        raise RuntimeError("simulator duplicate-link fixture setup failed")
    sim_runtime._link_app_files_into(
        source_mpy, destination, skip_if_py_exists=True
    )
    entries = os.listdir(destination)
    if "ManagedApp.mpy" in entries:
        _remove_tree(probe)
        raise RuntimeError("simulator managed .mpy duplicate was not removed")
    try:
        with open(destination + "/LocalApp.mpy", "r") as handle:
            local_contents = handle.read()
    except OSError:
        local_contents = ""
    if local_contents != "local compiled app\n":
        _remove_tree(probe)
        raise RuntimeError("simulator duplicate cleanup removed a local .mpy app")
    _remove_tree(probe)
    print("[sim-check:ok] duplicate managed apps pruned, local .mpy preserved")


def _run_keyboard_background_check():
    """Exercise the PicoCalc background-poll callback contract."""
    import picoware_keyboard
    import sim_runtime

    received = []

    def on_key(_):
        received.append(picoware_keyboard.get_key_nonblocking())

    sim_runtime._keys = []
    picoware_keyboard.init()
    picoware_keyboard.set_key_available_callback(on_key)
    picoware_keyboard.set_background_poll(True)
    sim_runtime.push_key(ord("a"))
    sim_runtime.push_key(ord("b"))
    sim_runtime.input_polled()
    if received != [ord("a")]:
        raise RuntimeError("simulator background keyboard dispatched wrong first key")
    sim_runtime.input_polled()
    if received != [ord("a"), ord("b")]:
        raise RuntimeError("simulator background keyboard did not dispatch queued keys")

    picoware_keyboard.set_background_poll(False)
    sim_runtime.push_key(ord("c"))
    sim_runtime.input_polled()
    if received != [ord("a"), ord("b")]:
        raise RuntimeError("simulator background keyboard ignored disabled state")
    if sim_runtime.pop_key() != ord("c"):
        raise RuntimeError("simulator disabled background keyboard consumed a key")
    picoware_keyboard.deinit()
    print("[sim-check:ok] picocalc background keyboard callbacks")


def _run_lcd_parity_check():
    """Verify LCD APIs added by the current Picoware runtime."""
    import lcd

    display = lcd.LCD()
    display.set_brightness(37)
    if display._brightness != 37:
        raise RuntimeError("simulator LCD brightness state mismatch")
    display.set_rgb_led(17, 34, 51)
    if display._rgb_led != (17, 34, 51):
        raise RuntimeError("simulator LCD RGB LED state mismatch")

    display._clear(0)
    display._bytearray(0, 0, 2, 1, bytearray((0x00, 0xFF)), True)
    if display._get_pixel(0, 0) != 0xFFFF or display._get_pixel(1, 0) != 0x0000:
        raise RuntimeError("simulator LCD bytearray inversion mismatch")

    display._clear(0x001F)
    display._fill_triangle_alpha(1, 1, 5, 1, 1, 5, 0xF800, 128)
    blended = display._get_pixel(2, 2)
    if blended in (0x001F, 0xF800):
        raise RuntimeError("simulator LCD alpha triangle mismatch")
    print("[sim-check:ok] lcd brightness RGB LED bytearray inversion alpha triangle")


def _run_uart_parity_check():
    """Verify board-default UART pins, including STM32 CPU pin names."""
    from machine import Pin
    from picoware.system import boards
    from picoware.system.uart import UART

    original_board_id = boards.BOARD_ID
    port = None
    try:
        port = UART()
        if (port._uart_id, port.tx_pin, port.rx_pin) != (0, 0, 1):
            raise RuntimeError("simulator PicoCalc UART defaults mismatch")
        del port
        port = None
        gc.collect()

        boards.BOARD_ID = boards.BOARD_FLIPPER_ZERO
        port = UART()
        if (port._uart_id, port.tx_pin, port.rx_pin) != (
            1,
            Pin.cpu.B6,
            Pin.cpu.B7,
        ):
            raise RuntimeError("simulator Flipper UART defaults mismatch")
    finally:
        boards.BOARD_ID = original_board_id
        if port is not None:
            del port
        gc.collect()
    print("[sim-check:ok] PicoCalc and Flipper UART defaults")


def _run_engine_parity_check():
    """Exercise the latest Level and Sprite3D native API additions."""
    import sd_mp
    import sim_runtime
    from engine import Level, Sprite3D, Triangle3D
    from picoware.gui.draw import Draw
    from picoware.system.vector import Vector

    path = "sim_reports/engine-roundtrip.sprite3d"
    sprite = Sprite3D()
    triangle = Triangle3D(
        2.0,
        -0.5,
        -0.5,
        2.0,
        0.5,
        0.0,
        2.0,
        -0.5,
        0.5,
        0x07E0,
        True,
        0,
    )
    triangle.wireframe = False
    sprite.triangles.append(triangle)
    if not sprite.to_path(path):
        raise RuntimeError("simulator Sprite3D.to_path failed")

    loaded = Sprite3D()
    if not loaded.from_path(path, False) or len(loaded.triangles) != 1:
        raise RuntimeError("simulator Sprite3D.from_path failed")
    loaded_triangle = loaded.triangles[0]
    if loaded_triangle.color != 0x07E0 or loaded_triangle.wireframe:
        raise RuntimeError("simulator Sprite3D round-trip data mismatch")
    loaded.set_wireframe(True)
    if not loaded_triangle.wireframe:
        raise RuntimeError("simulator Sprite3D.set_wireframe failed")

    class GameProbe:
        pass

    class PlayerProbe:
        pass

    original_headless = sim_runtime.headless
    draw = None
    try:
        sim_runtime.headless = True
        draw = Draw()
        game = GameProbe()
        game.draw = draw
        player = PlayerProbe()
        player.is_player = True
        player.position = Vector(0, 0, 0)
        player.direction = Vector(1, 0, 0)
        level = Level(game=game)
        level.entities.append(player)
        if abs(level.light_direction.x - 0.577) > 0.001:
            raise RuntimeError("simulator Level default light direction mismatch")
        level.set_light_direction(0, 3, 4)
        if (
            abs(level.light_direction.y - 0.6) > 0.001
            or abs(level.light_direction.z - 0.8) > 0.001
        ):
            raise RuntimeError("simulator Level.set_light_direction failed")
        level.set_shadow_color(0x39E7)
        if level.shadow_color != 0x39E7:
            raise RuntimeError("simulator Level.set_shadow_color failed")
        level.render_3d_sprite(path, 0.0, False, True)
        if not any(draw._buffer):
            raise RuntimeError("simulator Level.render_3d_sprite drew no pixels")
    finally:
        draw = None
        sim_runtime.set_lcd(None)
        sim_runtime.headless = original_headless
        sd_mp.remove(path)
        gc.collect()
    print("[sim-check:ok] engine Level and Sprite3D parity")


def _run_font_parity_check():
    """Verify board-default fonts and the corrected Font16 spacing."""
    import lcd
    import picoware_boards as boards
    from font import FontSize

    small = (boards.BOARD_CARDPUTER, boards.BOARD_WAVESHARE_2_06)
    medium = (
        boards.BOARD_WAVESHARE_1_43_RP2350,
        boards.BOARD_WAVESHARE_3_49_RP2350,
    )
    for board_id in range(boards.BOARD_DESKTOP + 1):
        expected = 1 if board_id in small else 2 if board_id in medium else 0
        if lcd.default_font_for_board(board_id, boards) != expected:
            raise RuntimeError("simulator board default font mismatch")
    if FontSize(2).spacing != 1:
        raise RuntimeError("simulator Font16 spacing mismatch")
    print("[sim-check:ok] board default fonts and Font16 spacing")


def _run_scripts_fixture_check(opts):
    """Verify bundled JavaScript files are linked into the simulated SD."""
    path = opts["sd"].rstrip("/") + "/picoware/scripts/hello.js"
    try:
        with open(path, "r") as handle:
            contents = handle.read()
    except OSError:
        contents = ""
    if 'draw.text(0, 10, "Hello From JavaScript")' not in contents:
        raise RuntimeError("simulator bundled scripts fixture is missing")
    print("[sim-check:ok] bundled JavaScript scripts fixture")


def _run_board_parity_check():
    """Verify the latest board profile and capability helpers."""
    import picoware_boards as boards

    picocalc_ids = (
        boards.BOARD_PICOCALC_PICO,
        boards.BOARD_PICOCALC_PICOW,
        boards.BOARD_PICOCALC_PICO_2,
        boards.BOARD_PICOCALC_PICO_2W,
        boards.BOARD_PICOCALC_PIMORONI_2W,
    )
    if boards.BOARD_HAS_PICOCALC != int(boards.BOARD_ID in picocalc_ids):
        raise RuntimeError("simulator PicoCalc capability mismatch")
    if boards.get_name(boards.BOARD_V8) != "V8":
        raise RuntimeError("simulator V8 board name mismatch")
    if boards.get_display_size(boards.BOARD_V8) != (240, 320):
        raise RuntimeError("simulator V8 display size mismatch")
    if not boards.has_sd_card(boards.BOARD_V8):
        raise RuntimeError("simulator V8 SD capability mismatch")
    if not boards.has_touch(boards.BOARD_V8):
        raise RuntimeError("simulator V8 touch capability mismatch")
    if not boards.has_wifi(boards.BOARD_V8):
        raise RuntimeError("simulator V8 WiFi capability mismatch")
    if boards.has_audio(boards.BOARD_V8):
        raise RuntimeError("simulator V8 audio capability mismatch")
    if boards.has_psram(boards.BOARD_V8):
        raise RuntimeError("simulator V8 PSRAM capability mismatch")
    if boards.get_name(boards.BOARD_WAVESHARE_1_69_RP2350) != "Waveshare 1.69":
        raise RuntimeError("simulator Waveshare 1.69 board name mismatch")
    if boards.get_display_size(boards.BOARD_WAVESHARE_1_69_RP2350) != (240, 280):
        raise RuntimeError("simulator Waveshare 1.69 display size mismatch")
    if boards.has_sd_card(boards.BOARD_WAVESHARE_1_69_RP2350):
        raise RuntimeError("simulator Waveshare 1.69 SD capability mismatch")
    if not boards.has_touch(boards.BOARD_WAVESHARE_1_69_RP2350):
        raise RuntimeError("simulator Waveshare 1.69 touch capability mismatch")
    if boards.has_wifi(boards.BOARD_WAVESHARE_1_69_RP2350):
        raise RuntimeError("simulator Waveshare 1.69 WiFi capability mismatch")
    if boards.has_audio(boards.BOARD_WAVESHARE_1_69_RP2350):
        raise RuntimeError("simulator Waveshare 1.69 audio capability mismatch")
    if boards.has_psram(boards.BOARD_WAVESHARE_1_69_RP2350):
        raise RuntimeError("simulator Waveshare 1.69 PSRAM capability mismatch")
    if boards.get_name(boards.BOARD_DESKTOP) != "Desktop":
        raise RuntimeError("simulator Desktop board name mismatch")
    if boards.get_display_size(boards.BOARD_DESKTOP) != (320, 320):
        raise RuntimeError("simulator Desktop display size mismatch")
    if not boards.has_sd_card(boards.BOARD_DESKTOP):
        raise RuntimeError("simulator Desktop SD capability mismatch")
    if boards.has_touch(boards.BOARD_DESKTOP):
        raise RuntimeError("simulator Desktop touch capability mismatch")
    if not boards.has_wifi(boards.BOARD_DESKTOP):
        raise RuntimeError("simulator Desktop WiFi capability mismatch")
    if not boards.has_audio(boards.BOARD_DESKTOP):
        raise RuntimeError("simulator Desktop audio capability mismatch")
    if boards.has_psram(boards.BOARD_DESKTOP):
        raise RuntimeError("simulator Desktop PSRAM capability mismatch")
    print("[sim-check:ok] V8, Waveshare 1.69, and Desktop board profiles")


def _run_touch_check():
    """Verify scripted keys land in the shared percentage-based touch zones."""
    import picoware_boards
    import sim_runtime
    from touch import Touch

    profiles = (
        ("crowpanel", picoware_boards.BOARD_CROWPANEL_10_1),
        ("waveshare-2.06", picoware_boards.BOARD_WAVESHARE_2_06),
        ("pancake", picoware_boards.BOARD_PANCAKE),
        ("v8", picoware_boards.BOARD_V8),
    )
    expected = (
        (sim_runtime.KEY_NAMES["up"], "up"),
        (sim_runtime.KEY_NAMES["down"], "down"),
        (sim_runtime.KEY_NAMES["left"], "left"),
        (sim_runtime.KEY_NAMES["right"], "right"),
        (sim_runtime.KEY_NAMES["back"], "back"),
        (sim_runtime.KEY_NAMES["enter"], "center"),
    )

    def zone(point, size):
        x, y = point
        width, height = size
        if 0 <= x <= width * 0.1 and 0 <= y <= height * 0.1:
            return "back"
        if width * 0.9 <= x <= width and height * 0.3 <= y <= height * 0.7:
            return "right"
        if 0 <= x <= width * 0.1 and height * 0.3 <= y <= height * 0.7:
            return "left"
        if width * 0.2 <= x <= width * 0.8 and 0 <= y <= height * 0.2:
            return "up"
        if width * 0.2 <= x <= width * 0.8 and height * 0.8 <= y <= height:
            return "down"
        if width * 0.4 <= x <= width * 0.6 and height * 0.4 <= y <= height * 0.6:
            return "center"
        return "none"

    original_board = sim_runtime.board
    try:
        touch = Touch()
        for board, board_id in profiles:
            size = picoware_boards.get_display_size(board_id)
            sim_runtime.board = board
            for key, expected_zone in expected:
                point = touch._point_for_key(key)
                actual_zone = zone(point, size)
                if actual_zone != expected_zone:
                    raise RuntimeError(
                        "simulator touch key mismatch: "
                        + board
                        + " "
                        + expected_zone
                        + " -> "
                        + str(point)
                        + " ("
                        + actual_zone
                        + ")"
                    )
    finally:
        sim_runtime.board = original_board
    print("[sim-check:ok] touch layout crowpanel waveshare-2.06 pancake v8")


def _run_v8_battery_check():
    """Exercise the V8 battery shim used by the desktop."""
    import sim_runtime
    import v8_battery

    original_percentage = sim_runtime.battery_percentage()
    try:
        if v8_battery.init() is not None:
            raise RuntimeError("simulator V8 battery init return mismatch")
        sim_runtime.set_battery_percentage(64)
        if v8_battery.get_percentage() != 64:
            raise RuntimeError("simulator V8 battery percentage mismatch")
        voltage = v8_battery.get_voltage()
        if voltage < 3.0 or voltage > 5.0:
            raise RuntimeError("simulator V8 battery voltage mismatch")
    finally:
        sim_runtime.set_battery_percentage(original_percentage)
    print("[sim-check:ok] V8 battery percentage and voltage")


def _run_waveshare_169_check():
    """Exercise the Waveshare 1.69 hard-IRQ touch and battery shims."""
    from machine import Pin
    import sim_runtime
    import waveshare_battery
    import waveshare_touch

    original_percentage = sim_runtime.battery_percentage()
    pin = Pin(21, Pin.IN, Pin.PULL_UP)
    try:
        waveshare_touch.reset_state()
        pin.irq(
            handler=waveshare_touch.read_data,
            trigger=Pin.IRQ_FALLING,
            hard=True,
        )
        waveshare_touch.set_touch_point(120, 140)
        if waveshare_touch.get_cached_point() != (120, 140):
            raise RuntimeError("simulator Waveshare 1.69 cached touch mismatch")
        if not pin._irq_hard:
            raise RuntimeError("simulator Waveshare 1.69 hard IRQ flag mismatch")
        waveshare_touch.reset()
        if waveshare_touch.get_cached_point() != (0, 0):
            raise RuntimeError("simulator Waveshare 1.69 touch reset mismatch")

        if waveshare_battery.init() is not None:
            raise RuntimeError("simulator Waveshare battery init return mismatch")
        sim_runtime.set_battery_percentage(64)
        if waveshare_battery.get_percentage() != 64:
            raise RuntimeError("simulator Waveshare battery percentage mismatch")
        voltage = waveshare_battery.get_voltage()
        if voltage < 3.0 or voltage > 5.0:
            raise RuntimeError("simulator Waveshare battery voltage mismatch")
        raw = waveshare_battery.read()
        if raw < 0 or raw > 4095:
            raise RuntimeError("simulator Waveshare battery ADC mismatch")
    finally:
        pin.irq(handler=None)
        waveshare_touch.reset_state()
        sim_runtime.set_battery_percentage(original_percentage)
    print("[sim-check:ok] Waveshare 1.69 hard IRQ touch and battery")


def _run_flipper_battery_check():
    """Exercise the Flipper battery shim lifecycle and simulated shutdown."""
    import flipper_battery
    import sim_runtime

    if flipper_battery.deinit() is not True:
        raise RuntimeError("simulator Flipper battery deinit failed")
    if flipper_battery.is_initialized():
        raise RuntimeError("simulator Flipper battery stayed initialized")

    for getter in (flipper_battery.get_percentage, flipper_battery.get_voltage_mv):
        try:
            getter()
        except RuntimeError:
            pass
        else:
            raise RuntimeError("simulator Flipper battery getter worked before init")

    if flipper_battery.init() is not True or not flipper_battery.is_initialized():
        raise RuntimeError("simulator Flipper battery init failed")
    percentage = flipper_battery.get_percentage()
    voltage = flipper_battery.get_voltage_mv()
    if percentage < 0 or percentage > 100 or voltage <= 0:
        raise RuntimeError("simulator Flipper battery reading is invalid")

    if flipper_battery.deinit() is not True or flipper_battery.is_initialized():
        raise RuntimeError("simulator Flipper battery lifecycle mismatch")
    if flipper_battery.deinit() is not True:
        raise RuntimeError("simulator Flipper battery deinit is not idempotent")

    flipper_battery.init()
    try:
        flipper_battery.shutdown()
    except sim_runtime.StopSimulation:
        pass
    else:
        raise RuntimeError("simulator Flipper shutdown did not stop the simulation")
    if flipper_battery.is_initialized():
        raise RuntimeError("simulator Flipper shutdown did not deinitialize battery")
    print("[sim-check:ok] flipper battery lifecycle shutdown")


def _run_log_storage_check(opts):
    """Verify storage-mode logs persist under the selected simulated SD root."""
    import log
    import sim_runtime

    original_sd_root = sim_runtime.sd_root
    relative_path = "sim_reports/log-parity.txt"
    try:
        sim_runtime.sd_root = opts["sd"]
        logger = log.Log(log.Log.LOG_MODE_STORAGE, relative_path, True)
        if logger.log("stored", log.Log.LOG_TYPE_INFO) is not True:
            raise RuntimeError("simulator storage log write failed")

        path = sim_runtime.host_path(relative_path)
        try:
            with open(path, "r") as handle:
                contents = handle.read()
        except OSError:
            contents = ""
        if contents != "[INFO]stored\n":
            raise RuntimeError("simulator storage log contents mismatch")
        if logger.logs != ["[INFO]stored"]:
            raise RuntimeError("simulator in-memory log contents mismatch")

        if logger.reset() is not True or logger.logs:
            raise RuntimeError("simulator storage log reset failed")
        with open(path, "r") as handle:
            if handle.read():
                raise RuntimeError("simulator storage log file was not reset")
    finally:
        sim_runtime.sd_root = original_sd_root
    print("[sim-check:ok] storage log persistence reset")


def _run_audio_shutdown_check():
    """Verify shutdown signals every active simulator audio helper."""
    import sim_runtime

    probe_root = "/tmp/picoware-sim-audio-shutdown-check"
    filenames = (
        "sim_audio.status",
        "sim_audio.cmd",
        "sim_audio_mix_1.status",
        "sim_audio_mix_1.cmd",
        "unrelated.status",
    )
    original_sd_root = sim_runtime.sd_root
    _mkdir_p(probe_root)
    try:
        for name in filenames:
            try:
                os.remove(probe_root + "/" + name)
            except OSError:
                pass
        with open(probe_root + "/sim_audio.status", "w") as handle:
            handle.write("playing=1\n")
        with open(probe_root + "/sim_audio_mix_1.status", "w") as handle:
            handle.write("playing=1\n")
        with open(probe_root + "/unrelated.status", "w") as handle:
            handle.write("playing=1\n")

        sim_runtime.sd_root = probe_root
        if sim_runtime.shutdown_audio_sidecars(0):
            raise RuntimeError("simulator audio shutdown ignored active helpers")
        for name in ("sim_audio.cmd", "sim_audio_mix_1.cmd"):
            with open(probe_root + "/" + name, "r") as handle:
                if handle.read() != "stop\n":
                    raise RuntimeError("simulator audio shutdown command mismatch")
        if sim_runtime._exists(probe_root + "/unrelated.cmd"):
            raise RuntimeError("simulator audio shutdown signaled an unrelated helper")
    finally:
        sim_runtime.sd_root = original_sd_root
        for name in filenames + ("unrelated.cmd",):
            try:
                os.remove(probe_root + "/" + name)
            except OSError:
                pass
        try:
            os.rmdir(probe_root)
        except OSError:
            pass
    print("[sim-check:ok] audio sidecar shutdown")


def _run_circular_choice_check():
    """Render the native circular Choice path without board-module reloading."""
    import sim_runtime
    from picoware.gui.choice import Choice
    from picoware.gui.draw import Draw
    from picoware.system.vector import Vector

    original_headless = sim_runtime.headless
    draw = None
    choice = None
    start_text = len(getattr(sim_runtime, "_recent_text", []))
    try:
        sim_runtime.headless = True
        draw = Draw()
        choice = Choice(
            draw,
            Vector(0, 0),
            draw.size,
            "Circular choice",
            ["No", "Yes"],
        )
        choice.is_circular = True
        choice.draw()
        rendered = getattr(sim_runtime, "_recent_text", [])[start_text:]
        for text in ("Circular choice", "No", "Yes"):
            if text not in rendered:
                raise RuntimeError(
                    "simulator circular Choice did not render text: " + text
                )
    finally:
        choice = None
        draw = None
        sim_runtime.set_lcd(None)
        sim_runtime.headless = original_headless
        gc.collect()
    print("[sim-check:ok] circular Choice render")


def _run_fatal_exit_check(opts):
    """Prove a main.py-caught assertion still makes the child exit nonzero."""
    probe_sd = "/tmp/picoware-sim-fatal-probe-sd"
    probe_log = "/tmp/picoware-sim-fatal-probe.log"
    missing_text = "__PICOWARE_SIM_EXPECTED_MISSING_TEXT__"
    cmd = (
        _interpreter_command()
        + " "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --frames 1 --assert-text "
        + _quote(missing_text)
        + " --audio silent --network offline --reset-sd --sd "
        + _quote(probe_sd)
        + " --apps-source "
        + _quote(opts["apps_source"])
        + " >"
        + _quote(probe_log)
        + " 2>&1"
    )
    status = os.system(cmd)
    try:
        with open(probe_log, "r") as handle:
            output = handle.read()
    except OSError:
        output = ""
    if status == 0:
        raise RuntimeError("simulator fatal-error probe unexpectedly exited zero")
    if "assert-text not seen: " + missing_text not in output:
        raise RuntimeError("simulator fatal-error probe missed assertion evidence")
    if "Picoware main reported a fatal error" not in output:
        raise RuntimeError("simulator fatal-error probe missed propagated failure")
    print("[sim-check:ok] fatal main errors exit nonzero")


def _run_mjs_check():
    """Smoke-test the JavaScript modules supplied by the simulator shim."""
    import mjs
    import sim_runtime

    js = mjs.MJS()
    js.run('let audio = import("audio");')
    if js.run("audio.isPlaying();") is not False:
        raise RuntimeError("simulator mjs audio state mismatch")

    js.run('let psram = import("psram");')
    js.run('psram.write32("0x20", "0x12345678");')
    if js.run('psram.read32("0x20");') != 0x12345678:
        raise RuntimeError("simulator mjs psram round-trip failed")

    js.run('let bluetooth = import("bluetooth");')
    if not js.run("bluetooth.register();"):
        raise RuntimeError("simulator mjs bluetooth registration failed")

    js.run('let websocket = import("websocket");')
    if js.run("websocket.isConnected();") is not False:
        raise RuntimeError("simulator mjs websocket state mismatch")

    js.run('let draw = import("draw");')
    if js.run('draw.len("Hello World");') != 66:
        raise RuntimeError("simulator mjs draw length mismatch")
    screenshot_path = sim_runtime.host_path("sim_reports/mjs.bmp")
    _mkdir_p(_dirname(screenshot_path))
    js.run('draw.screenshot("sim_reports/mjs.bmp");')
    try:
        if os.stat(screenshot_path)[6] <= 54:
            raise RuntimeError("simulator mjs screenshot is empty")
    except OSError:
        raise RuntimeError("simulator mjs screenshot missing")

    js.run('let settings = import("settings");')
    expected_settings = (
        ("settings.anthropicApiKey", ""),
        ("settings.geminiApiKey", ""),
        ("settings.localUrl", "http://127.0.0.1:8080/v1/chat/completions"),
        ("settings.screenBrightness", 100),
        ("settings.xaiApiKey", ""),
    )
    for expression, expected in expected_settings:
        if js.run(expression + ";") != expected:
            raise RuntimeError("simulator mjs setting mismatch: " + expression)
    print("[sim-check:ok] mjs draw settings audio bluetooth psram websocket")


def _run_agent_mcp_contracts():
    """Exercise only the contracts required by the Agent MCP workflow."""
    import json as _json
    from picoware.system.agent.agent import (
        Agent, MODE_CHAT, _followup_prompt, _mcp_answer_guard,
        _mcp_conversation_context, _request_tool_names,
    )
    from picoware.system.agent.authorization import request_authorizes_mutation
    from picoware.system.agent.llm import LOCAL_MCP
    from picoware.system.agent.mcp import (
        MAX_MCP_CALLS,
        MAX_MCP_EVENT_BYTES,
        MAX_MCP_EVIDENCE_CHARS,
        MCP_OUTCOME_COMPLETED,
        MCP_OUTCOME_FAILED,
        MCP_OUTCOME_NOT_NEEDED,
        MCPClient,
        _utf8_size,
        explicit_integration_records,
        integration_key,
        normalize_integration_record,
        parse_integration_catalog,
        parse_integration_records,
        preserve_catalog_records,
        serialize_integration_records,
    )
    from picoware.system.agent.mcp_lmstudio import (
        IntegrationStreamSink, LMStudioMCPAdapter,
    )
    from picoware.applications.agent import (
        _save_mcp_server, _settings_menu_items,
    )

    def _record(identity, label, tools, capabilities=None):
        return normalize_integration_record({
            "type": "plugin",
            "id": identity,
            "label": label,
            "capabilities": capabilities or [],
            "tools": tools,
        })

    catalog = _record(
        "fixture/catalog-index", "Integration Catalog", [{
            "name": "list_integrations",
            "description": "List configured integrations",
            "annotations": {
                "readOnlyHint": True, "destructiveHint": False,
            },
        }], ["catalog"],
    )
    search = _record(
        "fixture/alpha-index", "Alpha Index", [{
            "name": "alpha_lookup",
            "description": "Search available pages",
            "inputs": ["query"],
            "annotations": {
                "readOnlyHint": True, "destructiveHint": False,
            },
        }], ["search"],
    )
    browser = _record(
        "fixture/resource-session", "Resource Session", [{
            "name": "resource_open",
            "description": "Navigate to a URL",
            "inputs": ["url"],
            "annotations": {
                "readOnlyHint": False, "destructiveHint": True,
                "openWorldHint": True,
            },
            "capabilities": ["fetch"],
            "request_scoped": True,
        }, {
            "name": "resource_snapshot",
            "description": "Capture current page content",
            "inputs": ["filename"],
            "annotations": {
                "readOnlyHint": True, "destructiveHint": False,
                "openWorldHint": True,
            },
        }], ["fetch"],
    )

    class _View:
        def __init__(self, storage=None):
            self.storage = storage
            self.messages = []
            self.gmt_offset = 0
            self.time = None

        def log(self, message):
            self.messages.append(message)

    class _FixtureMCP(MCPClient):
        def __init__(self, records, responses):
            self.view_manager = _View()
            self.http = None
            self.llm = None
            self.records = list(records)
            self.integrations = [integration_key(item) for item in records]
            self.lmstudio = None
            self.status_callback = None
            self._last_gateway_provider = ""
            self._last_gateway_tool = ""
            self.responses = list(responses)
            self.stage_calls = []

        def _run_stage(
            self, request, integrations, max_calls=MAX_MCP_CALLS,
            optional=False, conversation_context="", continuation_plans=None,
        ):
            self.stage_calls.append({
                "request": request,
                "integrations": integrations,
                "max_calls": max_calls,
                "optional": optional,
                "context": conversation_context,
                "plans": continuation_plans or [],
            })
            if not self.responses:
                return "", 0, "fixture response missing"
            provider, tool, evidence, calls, error = self.responses.pop(0)
            if tool:
                self._gateway_tool_status(provider, tool)
            return evidence, calls, error

    # 1. Catalog, activation, compact persistence, and legacy normalization.
    legacy_server = normalize_integration_record({
        "type": "mcp_server",
        "server_label": "Legacy Endpoint",
        "server_url": "https://example.invalid/mcp",
        "protocol": "legacy",
        "headers": {"Authorization": "private"},
        "tools": [{
            "name": "resource_read",
            "description": "x" * 400,
            "inputSchema": {"properties": {"url": {}}},
            "annotations": {
                "readOnlyHint": True, "destructiveHint": False,
            },
        }],
    })
    persisted = serialize_integration_records([legacy_server])
    if (
        parse_integration_records("{malformed")
        or legacy_server.get("type") != "ephemeral_mcp"
        or "private" in persisted or "inputSchema" in persisted
        or "protocol" in persisted
    ):
        raise RuntimeError("Agent MCP compact settings contract failed")

    class _SettingsStorage:
        def __init__(self):
            self.values = {"picoware/settings/picoware.json": "{}"}

        def exists(self, path):
            return path in self.values

        def read(self, path):
            return self.values.get(path)

        def write(self, path, value, mode="w"):
            self.values[path] = value
            return True

    class _SettingsView:
        def __init__(self):
            self.storage = _SettingsStorage()

        def alert(self, _message, _warning):
            return None

    settings_view = _SettingsView()
    if not _save_mcp_server(
        settings_view, "Manual Endpoint|https://example.invalid/manual"
    ):
        raise RuntimeError("Agent MCP settings activation was rejected")
    saved_settings = _json.loads(settings_view.storage.values[
        "picoware/settings/picoware.json"
    ])
    saved_records = parse_integration_records(
        saved_settings.get("mcp_integrations", "")
    )
    if (
        len(saved_records) != 1
        or saved_records[0].get("type") != "ephemeral_mcp"
    ):
        raise RuntimeError("Agent MCP settings activation contract failed")
    discovered_payload = _json.dumps({"integrations": [search, browser]})
    if len(parse_integration_catalog(discovered_payload)) != 2:
        raise RuntimeError("Agent MCP catalog parsing contract failed")
    scan_client = _FixtureMCP([
        catalog,
        normalize_integration_record({
            "type": "plugin", "id": "fixture/alpha-index",
            "label": "Alpha Index", "capabilities": ["generic"],
        }),
    ], [("fixture/catalog-index", "list_integrations",
         discovered_payload, 1, "")])
    scanned, scan_error = scan_client.scan_integrations()
    active = preserve_catalog_records(scanned, [browser])
    if (
        scan_error or len(scanned) != 3
        or search.get("tool_hints") != scanned[1].get("tool_hints")
        or [integration_key(item) for item in active]
        != [integration_key(catalog), integration_key(browser)]
    ):
        raise RuntimeError("Agent MCP scan and activation contract failed")

    # 2. An optional gateway pass may decline tools without a retry or failure.
    no_tool = _FixtureMCP([search], [("", "", "", 0, "")])
    no_tool_outcome = no_tool.research_result("Write a concise greeting")
    if (
        no_tool_outcome.get("status") != MCP_OUTCOME_NOT_NEEDED
        or len(no_tool.stage_calls) != 1
        or no_tool.stage_calls[0].get("optional") is not True
    ):
        raise RuntimeError("Agent MCP no-tool fallthrough contract failed")

    class _OptionalAdapter(LMStudioMCPAdapter):
        def __init__(self):
            self.attempts = 0

        def run_stage_once(
            self, _message, _integrations, _max_calls,
            _force_retry=False, optional=False, conversation_context="",
            continuation_plans=None,
        ):
            self.attempts += 1
            return "", 0, "" if optional else "no tool"

    optional_adapter = _OptionalAdapter()
    if (
        optional_adapter.run_stage(
            "Greeting", [{"type": "plugin", "id": "fixture/alpha"}],
            optional=True,
        ) != ("", 0, "")
        or optional_adapter.attempts != 1
    ):
        raise RuntimeError("Agent MCP optional adapter retried")

    # 3. LM Studio receives provider-neutral metadata and owns tool selection.
    named, ambiguous = explicit_integration_records(
        [search, browser], "Use Alpha Index for this request"
    )
    ordinary, ordinary_ambiguous = explicit_integration_records(
        [search, browser], "Find the newest release"
    )
    neutral = _FixtureMCP(
        [search, browser],
        [("fixture/alpha-index", "alpha_lookup", "one result", 1, "")],
    )
    neutral_outcome = neutral.research_result("Find the newest release")
    sent = neutral.stage_calls[0].get("integrations", [])
    sent_ids = [item.get("id", item.get("server_label", "")) for item in sent]
    if (
        named != [search] or ambiguous or ordinary or ordinary_ambiguous
        or neutral_outcome.get("status") != MCP_OUTCOME_COMPLETED
        or sent_ids != ["fixture/alpha-index", "fixture/resource-session"]
        or "playwright" in neutral.stage_calls[0]["request"].lower()
        or "duckduckgo" in neutral.stage_calls[0]["request"].lower()
    ):
        raise RuntimeError("Agent MCP provider-neutral execution contract failed")

    # 4. A URL result gets one bounded action-to-observer follow-on.
    chained = _FixtureMCP([
        search, browser,
    ], [
        (
            "fixture/alpha-index", "alpha_lookup",
            "Release: https://example.invalid/release", 1, "",
        ),
        (
            "fixture/resource-session", "resource_snapshot",
            "Release title; final URL; observed inline content", 2, "",
        ),
    ])
    chained_outcome = chained.research_result("Find the newest release")
    second = chained.stage_calls[1]
    second_tools = second["integrations"][0].get("allowed_tools", [])
    if (
        chained_outcome.get("status") != MCP_OUTCOME_COMPLETED
        or chained_outcome.get("calls") != 3
        or len(chained.stage_calls) != 2
        or second.get("max_calls") != MAX_MCP_CALLS - 1
        or second_tools != ["resource_open", "resource_snapshot"]
        or second.get("plans") != [{
            "provider": "fixture/resource-session",
            "actions": ["resource_open"],
            "observers": ["resource_snapshot"],
        }]
        or "# Integration evidence" not in chained_outcome.get("evidence", "")
        or "# Opened page evidence" not in chained_outcome.get("evidence", "")
    ):
        raise RuntimeError("Agent MCP bounded URL follow-on contract failed")

    # 5. Streaming enforces retry, bounds, temporary cleanup, and call budget.
    class _SinkHTTP:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    def _sink_event(sink, value):
        sink.write(
            b"data: " + _json.dumps(value).encode("utf-8") + b"\n\n"
        )

    retry_http = _SinkHTTP()
    retry_sink = IntegrationStreamSink(
        retry_http, max_calls=MAX_MCP_CALLS,
        continuation_plans=[{
            "provider": "fixture/resource-session",
            "actions": ["resource_open"],
            "observers": ["resource_snapshot"],
        }],
    )
    _sink_event(retry_sink, {
        "type": "tool_call.arguments",
        "provider_info": {"plugin_id": "fixture/resource-session"},
        "tool": "resource_open", "arguments": {"url": "bad"},
    })
    _sink_event(retry_sink, {
        "type": "tool_call.success",
        "provider_info": {"plugin_id": "fixture/resource-session"},
        "tool": "resource_open",
        "output": {"isError": True, "error": "navigation failed"},
    })
    _sink_event(retry_sink, {
        "type": "tool_call.arguments",
        "provider_info": {"plugin_id": "fixture/resource-session"},
        "tool": "resource_open", "arguments": {"url": "corrected"},
    })
    _sink_event(retry_sink, {
        "type": "tool_call.success",
        "provider_info": {"plugin_id": "fixture/resource-session"},
        "tool": "resource_open", "output": {"ok": True},
    })
    _sink_event(retry_sink, {
        "type": "tool_call.arguments",
        "provider_info": {"plugin_id": "fixture/resource-session"},
        "tool": "resource_snapshot", "arguments": {},
    })
    _sink_event(retry_sink, {
        "type": "tool_call.success",
        "provider_info": {"plugin_id": "fixture/resource-session"},
        "tool": "resource_snapshot", "output": "observed content",
    })
    if (
        retry_sink.error or retry_sink.call_count != 3
        or retry_sink.evidence != ["observed content"]
        or not retry_sink.complete or not retry_http.closed
    ):
        raise RuntimeError("Agent MCP nested-error retry contract failed")

    budget_sink = IntegrationStreamSink(_SinkHTTP(), max_calls=1)
    _sink_event(budget_sink, {
        "type": "tool_call.arguments", "tool": "one", "arguments": {},
    })
    _sink_event(budget_sink, {
        "type": "tool_call.arguments", "tool": "two", "arguments": {},
    })
    event_sink = IntegrationStreamSink(_SinkHTTP(), max_calls=1)
    event_sink.write(b"x" * (MAX_MCP_EVENT_BYTES + 1))
    large = _FixtureMCP([
        search,
    ], [("fixture/alpha-index", "alpha_lookup", "界" * 5000, 1, "")])
    large_outcome = large.research_result("Find current data")
    if (
        "budget" not in budget_sink.issue
        or "event" not in event_sink.issue
        or _utf8_size(large_outcome.get("evidence", ""))
        > MAX_MCP_EVIDENCE_CHARS
    ):
        raise RuntimeError("Agent MCP stream bound contract failed")

    class _ScratchStorage:
        def __init__(self):
            self.values = {}
            self.files = {}
            self.removed = []

        def write(self, path, value, mode="w"):
            previous = self.values.get(path, "") if mode == "a" else ""
            self.values[path] = previous + value
            return True

        def remove(self, path):
            self.values.pop(path, None)
            self.files.pop(path, None)
            self.removed.append(path)
            return True

        def file_open(self, path):
            self.files[path] = bytearray()
            return path

        def file_write(self, handle, value, _mode="wb"):
            self.files[handle].extend(value)
            return True

        def file_close(self, _handle):
            return None

    class _Response:
        status_code = 200
        reason = "OK"

        def close(self):
            return None

    class _StreamHTTP(_SinkHTTP):
        def post(
            self, _url, payload=None, headers=None, timeout=0, storage=None,
            send_file="", stream_sink=None,
        ):
            _sink_event(stream_sink, {
                "type": "tool_call.arguments",
                "provider_info": {"plugin_id": "fixture/alpha-index"},
                "tool": "alpha_lookup", "arguments": {"query": "alpha"},
            })
            _sink_event(stream_sink, {
                "type": "tool_call.success", "output": "cleanup evidence",
            })
            return _Response()

    class _LLM:
        url = "http://127.0.0.1:1234/api/v1/chat"
        model = "fixture"
        headers = {"Content-Type": "application/json"}

    scratch = _ScratchStorage()
    adapter = LMStudioMCPAdapter(_View(scratch), _StreamHTTP(), _LLM())
    cleanup_result = adapter.run_stage_once(
        "Find alpha", [{"type": "plugin", "id": "fixture/alpha-index"}], 1,
    )
    if (
        cleanup_result != ("cleanup evidence", 1, "")
        or adapter.request_path in scratch.values
        or adapter.spool_path in scratch.files
        or adapter.request_path not in scratch.removed
        or adapter.spool_path not in scratch.removed
    ):
        raise RuntimeError("Agent MCP scratch cleanup contract failed")

    # 6. Authorization and the final answer boundary remain deterministic.
    mutating = _record(
        "fixture/destructive-store", "Destructive Store", [{
            "name": "delete_record", "description": "Delete one record",
            "annotations": {
                "readOnlyHint": False, "destructiveHint": True,
            },
        }], ["generic"],
    )
    denied = _FixtureMCP([
        mutating,
    ], [("fixture/destructive-store", "delete_record", "deleted", 1, "")])
    denied_outcome = denied.research_result("Show the record")
    allowed = _FixtureMCP([
        mutating,
    ], [("fixture/destructive-store", "delete_record", "deleted", 1, "")])
    allowed_outcome = allowed.research_result(
        "Use Destructive Store to delete the record",
        allow_mutation=True, require_tool=True,
    )
    if (
        denied_outcome.get("status") != MCP_OUTCOME_FAILED
        or denied.stage_calls
        or allowed_outcome.get("status") != MCP_OUTCOME_COMPLETED
        or not request_authorizes_mutation("Delete the record")
        or request_authorizes_mutation("Do not delete the record")
        or _request_tool_names(MODE_CHAT, "hello", True)
    ):
        raise RuntimeError("Agent MCP authorization boundary contract failed")

    class _ConversationStorage:
        def __init__(self):
            self.values = {}

        def exists(self, path):
            return path in self.values

        def write(self, path, value, mode="w"):
            previous = self.values.get(path, "") if mode == "a" else ""
            self.values[path] = previous + value
            return True

    class _AgentShell:
        def __init__(self):
            self.view_manager = _View(_ConversationStorage())
            self._conv_path = "conversation.json"

        def _append_json_escaped_text(self, storage, path, text):
            Agent._append_json_escaped_text(storage, path, text)

    final_agent = _AgentShell()
    Agent._conv_append_user_request(
        final_agent, "Answer the request", "verified evidence",
        {"status": MCP_OUTCOME_COMPLETED},
    )
    final_content = _json.loads(
        final_agent.view_manager.storage.values[final_agent._conv_path]
    ).get("content", "")
    followup = _mcp_conversation_context([
        {"role": "user", "content": "Find the Alpha release"},
        {
            "role": "assistant",
            "content": "Result https://example.invalid/release",
        },
    ])
    if (
        "Current integration evidence" not in final_content
        or "verified evidence" not in final_content
        or "https://example.invalid/release" not in followup
    ):
        raise RuntimeError("Agent MCP final evidence handoff contract failed")

    # 8. Follow-up questions are opt-in and add no prompt bytes when disabled.
    if (
        _followup_prompt(False) != b""
        or b"ask one concise follow-up question" not in _followup_prompt(True)
        or "ask one concise follow-up question" not in _mcp_answer_guard(True)
        or "Do not ask for confirmation" not in _mcp_answer_guard(False)
        or _settings_menu_items(LOCAL_MCP, False)[2]
        != "Follow-up Questions: Off"
        or _settings_menu_items(LOCAL_MCP, True)[2]
        != "Follow-up Questions: On"
        or len(_settings_menu_items(LOCAL_MCP, True)) != 6
    ):
        raise RuntimeError("Agent follow-up question toggle contract failed")

    print(
        "[sim-check:ok] Agent MCP catalog fallthrough routing chain "
        "bounds cleanup authorization"
    )


def _write_error_file(path, exc):
    """Write exception details to an error log file."""
    if not path:
        return
    try:
        import sys as _sys

        with open(path, "w") as handle:
            handle.write("Picoware simulator exception\n")
            try:
                import sim_runtime

                handle.write("View: " + str(getattr(sim_runtime, "_current_view_name", "")) + "\n")
            except Exception:
                pass
            handle.write("\n")
            try:
                _sys.print_exception(exc, handle)
            except Exception:
                handle.write(str(exc))
                handle.write("\n")
    except OSError:
        pass


def _wait_for_viewer_close(frame):
    """Block until the viewer quit signal appears."""
    quit_path = frame + ".quit"
    while True:
        try:
            os.stat(quit_path)
            return
        except OSError:
            pass
        time_sleep(0.1)


def _relaunch_self(reset_sd=False):
    """Restart the simulator process via micropython."""
    args = []
    for arg in sys.argv:
        args.append(_quote(str(arg)))
    if reset_sd and "--reset-sd" not in sys.argv:
        args.append("--reset-sd")
    cmd = _interpreter_command() + " " + " ".join(args) + " >/tmp/picoware-sim-restart.log 2>&1 &"
    os.system(cmd)


def time_sleep(seconds):
    """Sleep for the given number of seconds."""
    try:
        import time

        time.sleep(seconds)
    except Exception:
        pass


def _start_viewer(opts):
    """Build and launch the native SDL viewer, returning frame/key paths."""
    frame = opts["sd"] + "/sim_frame.rgb565"
    keys = opts["sd"] + "/sim_keys.txt"
    binary = THIS_DIR + "/viewer/sdl_fb_viewer"

    if not _build_native("viewer"):
        print("Could not build SDL viewer. Run: sh simulator/build.sh viewer")
        raise SystemExit

    try:
        os.remove(keys)
    except OSError:
        pass
    try:
        os.remove(frame + ".stop")
    except OSError:
        pass
    try:
        os.remove(frame + ".quit")
    except OSError:
        pass
    try:
        os.remove(frame + ".error")
    except OSError:
        pass
    try:
        os.remove(frame + ".status")
    except OSError:
        pass
    try:
        os.remove(frame + ".control")
    except OSError:
        pass
    try:
        os.remove(frame + ".log")
    except OSError:
        pass

    board_name = str(opts["board"]).lower().replace("_", "-")
    width, height = _simulator_display_size(board_name)
    cmd = (
        _quote(binary)
        + " "
        + _quote(frame)
        + " "
        + _quote(keys)
        + " "
        + str(opts["scale"])
        + " "
        + str(width)
        + " "
        + str(height)
        + " >/tmp/picoware-sim-viewer.log 2>&1 &"
    )
    os.system(cmd)
    return frame, keys


def main():
    """Picoware simulator entry point."""
    _insert_path(ROOT)
    _insert_path(MICROPYTHON_DIR)
    _insert_path(HARDWARE_DIR)

    import sim_usocket
    import sim_tls

    sys.modules["usocket"] = sim_usocket
    sys.modules["socket"] = sim_usocket
    sys.modules["tls"] = sim_tls
    sys.modules["ssl"] = sim_tls

    opts = _parse_args(sys.argv)
    if opts["reset_sd"]:
        _safe_reset_sd(opts["sd"])
    _mkdir_p(opts["sd"])

    if opts["sim_check"]:
        _run_sim_check(opts)
        return

    if opts["agent_check"]:
        _run_agent_mcp_contracts()
        return

    if opts["coverage"]:
        _run_coverage(opts)
        return

    viewer_frame = ""
    viewer_keys = ""
    if opts["viewer"]:
        viewer_frame, viewer_keys = _start_viewer(opts)

    import sim_runtime

    frame_limit = opts["exit_after_frames"]
    if not frame_limit and opts["headless"] and not opts["viewer"]:
        frame_limit = opts["frames"]

    sim_runtime.configure(
        ROOT,
        opts["sd"],
        opts["apps_source"],
        opts["scale"],
        opts["board"],
        frame_limit,
        opts["headless"],
        opts["trace_keys"],
        opts["trace_views"],
        opts["trace_imports"],
        opts["screenshot"],
        opts["viewer"],
        viewer_frame,
        viewer_keys,
        opts["network"],
        opts["bluetooth"],
        opts["audio"],
        opts["speed"],
        opts["fps"],
        opts["sd_profile"],
        opts["record"],
    )
    sim_runtime.set_script_expectations(opts["wait_view"], opts["assert_text"])
    if opts["capabilities"]:
        sim_runtime.print_capabilities()
        return
    _install_view_tracking()
    try:
        if opts["open"]:
            sim_runtime.request_open(opts["open"])
        if opts["app"]:
            sim_runtime.request_app(opts["app"])
        if opts["game"]:
            sim_runtime.request_game(opts["game"])

        delayed_input = bool(opts["open"] or opts["app"] or opts["game"])
        delayed_loops = 180 if opts["app"] or opts["game"] else 120
        if opts["keys_text"]:
            if delayed_input:
                sim_runtime.schedule_text(delayed_loops, opts["keys_text"])
            else:
                sim_runtime.enqueue_text(opts["keys_text"])
        if opts["keys"]:
            if delayed_input:
                sim_runtime.schedule_key_names(delayed_loops + 1, opts["keys"])
            else:
                sim_runtime.enqueue_key_names(opts["keys"])
        if opts["script"]:
            sim_runtime.run_script_file(opts["script"])
    except sim_runtime.LaunchTargetError as e:
        print("[sim:launch:fail]", e)
        raise SystemExit(2)

    restart_requested = False
    restart_reset_sd = False
    try:
        _run_main()
    except sim_runtime.StopSimulation:
        pass
    except sim_runtime.RestartSimulation as r:
        restart_requested = True
        restart_reset_sd = bool(getattr(r, "reset", False))
    except Exception as e:
        try:
            sys.print_exception(e)
        except Exception:
            print("Unhandled simulator exception:", e)
        if opts["viewer"] and viewer_frame:
            _write_error_file(viewer_frame + ".error", e)
            _wait_for_viewer_close(viewer_frame)
        else:
            _write_error_file(opts["sd"] + "/sim_error.txt", e)
        raise SystemExit(1)
    finally:
        try:
            sim_runtime.shutdown_audio_sidecars()
        except Exception:
            pass
        try:
            sim_runtime.finish_recording()
        except Exception:
            pass
        if opts["viewer"] and viewer_frame:
            try:
                with open(viewer_frame + ".stop", "w") as handle:
                    handle.write("stop\n")
            except OSError:
                pass
        gc.collect()
    if restart_requested:
        _relaunch_self(restart_reset_sd)


main()
