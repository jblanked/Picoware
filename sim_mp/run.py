"""MicroPython-only Picoware simulator entrypoint."""

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


def _insert_path(path):
    """Insert a directory into sys.path if not present."""
    if path not in sys.path:
        sys.path.insert(0, path)


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
        elif arg == "--reset-sd":
            opts["reset_sd"] = True
        elif arg == "--sd-profile" and i + 1 < len(argv):
            i += 1
            opts["sd_profile"] = argv[i]
        elif arg == "--record" and i + 1 < len(argv):
            i += 1
            opts["record"] = _abspath(argv[i])
        elif arg == "--help":
            print("usage: micropython sim_mp/run.py [--viewer] [--sdl] [--headless] [--frames N] [--exit-after-frames N] [--speed auto|real|pico2w|fast|unlimited] [--fps N] [--network real|offline] [--bluetooth virtual|off] [--audio real|silent] [--keys a,b] [--keys-text TEXT] [--record FILE] [--open NAME] [--app NAME] [--game NAME] [--apps-source PATH] [--reset-sd] [--sd-profile clean|dev|media|network-fixtures] [--screenshot PATH] [--coverage apps|games|all] [--script FILE] [--wait-view NAME] [--assert-text TEXT] [--capabilities] [--sim-check]")
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
        print("Use the default sim_mp/sdcard or a path under /tmp for destructive reset.")
        raise SystemExit(2)
    if target in ("", "/", "/tmp", THIS_DIR, ROOT):
        print("--reset-sd refused root-like path:", target)
        raise SystemExit(2)
    _remove_tree(target)
    _mkdir_p(target)


def _run_main():
    """Execute the Picoware main.py entry point."""
    namespace = {"__name__": "__sim_picoware_main__", "__file__": MICROPYTHON_DIR + "/main.py"}
    with open(MICROPYTHON_DIR + "/main.py", "r") as handle:
        code = handle.read()
    exec(code, namespace)
    namespace["main"]()


def _quote(path):
    """Shell-quote a path string."""
    return "'" + path.replace("'", "'\"'\"'") + "'"


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
            "micropython "
            + _quote(THIS_DIR + "/run.py")
            + " --headless --frames 220 --audio silent --network offline --sd "
            + _quote(opts["sd"])
            + " --apps-source "
            + _quote(opts["apps_source"])
            + (" --app " if kind == "app" else " --game ")
            + _quote(name)
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


def _build_native(target, check=False):
    """Build a native simulator helper via build.sh."""
    cmd = "sh " + _quote(THIS_DIR + "/build.sh")
    if check:
        cmd += " --check"
    cmd += " " + _quote(target)
    return os.system(cmd) == 0


def _run_sim_check(opts):
    """Run the simulator self-check suite."""
    commands = (
        "sh "
        + _quote(THIS_DIR + "/build.sh")
        + " --check",
        "micropython "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --frames 30 --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"]),
        "micropython "
        + _quote(THIS_DIR + "/run.py")
        + " --headless --app VibesMP --frames 120 --audio silent --network offline --sd "
        + _quote(opts["sd"])
        + " --apps-source "
        + _quote(opts["apps_source"]),
    )
    for cmd in commands:
        status = os.system(cmd)
        if status != 0:
            print("[sim-check:fail]", cmd, status)
            raise SystemExit
    print("[sim-check:pass]")


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
    cmd = "micropython " + " ".join(args) + " >/tmp/picoware-sim-restart.log 2>&1 &"
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
        print("Could not build SDL viewer. Run: sh sim_mp/build.sh viewer")
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

    cmd = _quote(binary) + " " + _quote(frame) + " " + _quote(keys) + " " + str(opts["scale"]) + " >/tmp/picoware-sim-viewer.log 2>&1 &"
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
    if opts["open"]:
        sim_runtime.request_open(opts["open"])
    if opts["app"]:
        sim_runtime.request_app(opts["app"])
    if opts["game"]:
        sim_runtime.request_game(opts["game"])

    delayed_input = bool(opts["open"] or opts["app"] or opts["game"])
    if opts["keys_text"]:
        if delayed_input:
            sim_runtime.schedule_text(80, opts["keys_text"])
        else:
            sim_runtime.enqueue_text(opts["keys_text"])
    if opts["keys"]:
        if delayed_input:
            sim_runtime.schedule_key_names(81, opts["keys"])
        else:
            sim_runtime.enqueue_key_names(opts["keys"])
    if opts["script"]:
        sim_runtime.run_script_file(opts["script"])

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
