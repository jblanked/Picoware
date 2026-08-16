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
        "agent_live_check": False,
        "agent_live_app_check": False,
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
        elif arg == "--agent-live-check":
            opts["agent_live_check"] = True
        elif arg == "--agent-live-app-check":
            opts["agent_live_app_check"] = True
        elif arg == "--reset-sd":
            opts["reset_sd"] = True
        elif arg == "--sd-profile" and i + 1 < len(argv):
            i += 1
            opts["sd_profile"] = argv[i]
        elif arg == "--record" and i + 1 < len(argv):
            i += 1
            opts["record"] = _abspath(argv[i])
        elif arg == "--help":
            print("usage: micropython simulator/run.py [--viewer] [--sdl] [--headless] [--frames N] [--exit-after-frames N] [--speed auto|real|pico2w|fast|unlimited] [--fps N] [--network real|offline] [--bluetooth virtual|off] [--audio real|silent] [--keys a,b] [--keys-text TEXT] [--record FILE] [--open NAME] [--app NAME] [--game NAME] [--apps-source PATH] [--reset-sd] [--sd-profile clean|dev|media|network-fixtures] [--screenshot PATH] [--coverage apps|games|all] [--script FILE] [--wait-view NAME] [--assert-text TEXT] [--capabilities] [--agent-check] [--agent-live-check] [--agent-live-app-check] [--sim-check]")
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
        from picoware.system.view import View
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
    if sim_runtime.trace_views:
        # Trace mode is diagnostic: let the top-level simulator handler print
        # the real exception and traceback instead of reducing it to an alert.
        def traced_view_run(self, view_manager):
            if self._run and self.active:
                self._run(view_manager)

        View.run = traced_view_run
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


def _run_agent_check():
    """Run only the deterministic Picoware Agent contracts."""
    _run_agent_ui_check()
    _run_agent_storage_check()
    _run_agent_mcp_check()
    print("[agent-check:pass]")


def _live_agent_context():
    """Return a configured simulator view and exact saved Agent selection."""
    from time import localtime
    from picoware.system.agent.llm import LOCAL_MCP
    from picoware.system.storage import Storage

    class LiveRTC:
        def datetime(self):
            value = localtime()
            return (
                value[0], value[1], value[2], value[6],
                value[3], value[4], value[5], 0,
            )

    class LiveTime:
        is_set = True
        is_fetching = False
        rtc = LiveRTC()

    class LiveView:
        def __init__(self):
            self.storage = Storage()
            self.thread_manager = None
            self.time = LiveTime()
            self.gmt_offset = 2
            self.has_wifi = False

        def log(self, message):
            print(message)

    view = LiveView()
    selection = view.storage.serialize("picoware/settings/current_agent.json")
    if not isinstance(selection, dict):
        raise RuntimeError("Agent settings are missing from the simulator SD")
    provider = selection.get("provider")
    model = selection.get("model", "")
    if provider != LOCAL_MCP or not model:
        raise RuntimeError(
            "select Local + MCP and an exact loaded model before a live check"
        )
    return view, provider, model


def _run_agent_live_check():
    """Research a joke through the configured live MCP integration path."""
    from picoware.system.agent.agent import Agent, MODE_CHAT
    from picoware.system.agent.llm import LLM
    from picoware.system.agent.mcp import integration_label

    class MCPProbe:
        def __init__(self, client):
            self.client = client
            self.calls = 0
            self.evidence = ""
            self.error = ""

        @property
        def enabled(self):
            return self.client.enabled

        @property
        def integrations(self):
            return self.client.integrations

        @property
        def records(self):
            return self.client.records

        def explicit_selection(self, message):
            return self.client.explicit_selection(message)

        def selected_integrations(self, message):
            return self.client.selected_integrations(message)

        def research(self, message):
            self.calls += 1
            self.selected = self.client.selected_integrations(message)
            self.evidence, self.error = self.client.research(message)
            return self.evidence, self.error

    view, provider, model = _live_agent_context()
    storage = view.storage
    paths = (
        "picoware/settings/agent-live-request.json",
        "picoware/settings/agent-live-conv.json",
        "picoware/settings/agent-live-mem.json",
        "picoware/settings/agent-live-stream.tmp",
        "picoware/settings/agent-live-state.json",
    )
    for path in paths:
        storage.remove(path)
    agent = Agent(view, MODE_CHAT, LLM(storage, provider, model), paths[0])
    agent._conv_path = paths[1]
    agent._mem_path = paths[2]
    agent._msg_path = paths[3]
    agent._state_path = paths[4]
    agent._conversation = []
    probe = MCPProbe(agent.mcp)
    probe.selected = []
    agent.mcp = probe
    try:
        result = agent.run_payload({
            "message": "research a good joke",
            "conversation": [],
        })
        answer = result.get("message", "")
        denial_markers = (
            "no access", "do not have access", "don't have access",
            "cannot access", "can't access",
        )
        if result.get("status") != "completed" or not answer.strip():
            raise RuntimeError("live Agent research returned no answer: " + answer)
        if probe.calls != 1 or not probe.evidence or probe.error:
            raise RuntimeError(
                "live Agent research did not produce MCP evidence: " + probe.error
            )
        if any(marker in answer.lower() for marker in denial_markers):
            raise RuntimeError("live Agent denied its successful MCP integration")
        print("[agent-live-check:pass] " + answer[:500].replace("\n", " | "))

        opener_records = []
        for wanted in ("browser", "fetch"):
            for record in probe.records:
                if (
                    wanted in record.get("capabilities", [])
                    and record not in opener_records
                ):
                    opener_records.append(record)
        if not opener_records:
            raise RuntimeError(
                "live Agent check needs one active page-opening integration"
            )
        opener_failures = []
        opener_answer = ""
        for opener_record in opener_records:
            opener_label = integration_label(opener_record)
            probe.calls = 0
            probe.evidence = ""
            probe.error = ""
            probe.selected = []
            opener_result = agent.run_payload({
                "message": (
                    "Use " + opener_label + " to open https://example.com and "
                    "report its page title."
                ),
                "conversation": [],
            })
            opener_answer = opener_result.get("message", "")
            selected_ids = [
                item.get("id", item.get("server_label", ""))
                for item in probe.selected
            ]
            expected_id = opener_record.get(
                "id", opener_record.get("server_label", "")
            )
            if selected_ids != [expected_id]:
                raise RuntimeError(
                    "live Agent dynamic MCP routing mismatch: "
                    + str(selected_ids)
                )
            answer_lower = opener_answer.lower()
            failure_markers = denial_markers + (
                "encountered an error", "unable to retrieve", "failed to",
                "could not retrieve", "working directory",
            )
            if (
                opener_result.get("status") == "completed"
                and probe.calls == 1
                and probe.evidence
                and not probe.error
                and not any(marker in answer_lower for marker in failure_markers)
            ):
                print(
                    "[agent-live-open-check:pass] "
                    + opener_answer[:500].replace("\n", " | ")
                )
                break
            opener_failures.append(
                opener_label + ": " + (probe.error or opener_answer)[:160]
            )
        else:
            raise RuntimeError(
                "live Agent page-opening MCPs failed: "
                + " | ".join(opener_failures)
            )
    finally:
        agent.cancel()
        for path in paths:
            storage.remove(path)


def _run_agent_live_app_check():
    """Exercise current Chat Completions App Creator generation on simulator SD."""
    from picoware.system.agent.agent import Agent, MODE_APP_CREATOR
    from picoware.system.agent.llm import LLM

    view, provider, model = _live_agent_context()
    storage = view.storage
    app_path = "picoware/apps/AgentLiveApp.py"
    paths = (
        "picoware/settings/agent-live-app-request.json",
        "picoware/settings/agent-live-app-conv.json",
        "picoware/settings/agent-live-app-mem.json",
        "picoware/settings/agent-live-app-stream.tmp",
        "picoware/settings/agent-live-app-state.json",
        app_path,
    )
    for path in paths:
        storage.remove(path)
    agent = Agent(
        view, MODE_APP_CREATOR, LLM(storage, provider, model), paths[0]
    )
    agent._conv_path = paths[1]
    agent._mem_path = paths[2]
    agent._msg_path = paths[3]
    agent._state_path = paths[4]
    agent._conversation = []
    try:
        result = agent.run_payload({
            "message": (
                "Create a minimal Picoware app at exactly " + app_path + ". "
                "It must define start, run, and stop; return True from start; "
                "and handle BUTTON_BACK with view_manager.back() in run. Use "
                "the API reference, write the file, validate it, and read it "
                "back before reporting success."
            ),
            "conversation": [],
        })
        if result.get("status") != "completed" or not storage.exists(app_path):
            raise RuntimeError(
                "live App Creator failed: " + str(result.get("message", ""))
            )
        source = storage.read(app_path, "r")
        for required in (
            "def start", "def run", "def stop", "BUTTON_BACK",
            "view_manager.back",
        ):
            if required not in source:
                raise RuntimeError("live App Creator omitted " + required)
        compile(source, app_path, "exec")
        print("[agent-live-app-check:pass]")
    finally:
        agent.cancel()
        for path in paths:
            storage.remove(path)


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
    _run_agent_ui_check()
    _run_agent_storage_check()
    _run_agent_mcp_check()
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


def _run_agent_ui_check():
    """Verify responsive Agent UI, typing, liveness, and Shift+N reset."""
    from picoware.applications import agent as agent_app
    from picoware.system.buttons import BUTTON_A, BUTTON_N

    class ProbeKeyboard:
        def __init__(self):
            self.response = "stale"
            self.title = ""
            self.forced = False

        def reset(self):
            self.response = ""

        def run(self, force=False):
            self.forced = force
            return True

    class TypingInput:
        was_capitalized = False

        def __init__(self):
            self.reset_called = False

        def button_to_char(self, button):
            return "A" if button == BUTTON_A else ""

        def reset(self):
            self.reset_called = True

    class TypingView:
        def __init__(self):
            self.button = BUTTON_A
            self.keyboard = ProbeKeyboard()
            self.input_manager = TypingInput()

    typing_view = TypingView()
    agent_app._state = agent_app.STATE_CHAT
    agent_app._mode_label = "Chat"
    agent_app.run(typing_view)
    if (
        agent_app._state != agent_app.STATE_TYPE
        or typing_view.keyboard.response != "A"
        or typing_view.keyboard.title != "Chat"
        or not typing_view.keyboard.forced
        or not typing_view.input_manager.reset_called
    ):
        raise RuntimeError("Agent chat letter did not seed the input editor")

    class ProbeSize:
        def __init__(self, width=320, height=320):
            self.x = width
            self.y = height

    class ProbeFont:
        def __init__(self, width=5, height=8):
            self.width = width
            self.spacing = 1
            self.height = height
            self.size = 0

    class ProbeFontSize:
        y = 8

    class ProbeDraw:
        def __init__(self, width=320, height=320, font_height=8):
            self.size = ProbeSize(width, height)
            self._font = ProbeFont(height=font_height)
            self.font_size = ProbeFontSize()
            self.font_size.y = font_height
            self.font = 0
            self.text = []
            self.rectangles = []
            self.swaps = 0

        def get_font(self, _font):
            return self._font

        def fill_screen(self, _color):
            return

        def _fill_rectangle(self, x, y, width, height, color):
            self.rectangles.append((x, y, width, height, color))

        def _fill_round_rectangle(self, *_args):
            return

        def _text(self, _x, _y, value, _color, _font):
            self.text.append(value)

        def len(self, value):
            return len(value) * (self._font.width + self._font.spacing)

        def swap(self):
            self.swaps += 1

    class ResetInput:
        was_capitalized = True

        def button_to_char(self, _button):
            return ""

    class ProbeAgent:
        def __init__(self):
            self.reset_calls = 0
            self._conversation = [{"role": "user", "content": "old"}]

        @property
        def conversation(self):
            return list(self._conversation)

        def reset_conversation(self):
            self.reset_calls += 1
            self._conversation = []

    class UIManager:
        def __init__(self, confirmed=True, width=320, height=320, font_height=8):
            self.button = BUTTON_N
            self.draw = ProbeDraw(width, height, font_height)
            self.background_color = 0
            self.foreground_color = 0xFFFF
            self.selected_color = 1
            self.input_manager = ResetInput()
            self.confirmed = confirmed
            self.alert_message = ""

        def alert(self, message, _back):
            self.alert_message = message
            return self.confirmed

    activity_view = UIManager()
    agent_app._start_activity(activity_view, "Preparing", True)
    first_frame = agent_app._activity_frame
    agent_app._activity_last_ms = agent_app.ticks_ms() - agent_app.ACTIVITY_FRAME_MS
    agent_app._activity_started_ms = agent_app.ticks_ms() - 3000
    agent_app._animate_activity(activity_view, "MCP research")
    if (
        agent_app._activity_frame == first_frame
        or activity_view.draw.swaps != 2
        or "Request in progress" not in activity_view.draw.text
        or "BACK=Cancel" not in activity_view.draw.text
        or len(activity_view.draw.rectangles) != agent_app.ACTIVITY_SEGMENTS * 2
    ):
        raise RuntimeError("Agent activity indicator did not visibly advance")

    for label in ("Chat", "App Creator", "Device Manager"):
        view = UIManager()
        probe_agent = ProbeAgent()
        agent_app._agent = probe_agent
        agent_app._mode_label = label
        agent_app._conversation = probe_agent.conversation
        agent_app._state = agent_app.STATE_CHAT
        agent_app.run(view)
        if (
            probe_agent.reset_calls != 1
            or agent_app._conversation
            or "Start a new " + label + " session?" not in view.alert_message
            or not any("Shift+N" in text for text in view.draw.text)
        ):
            raise RuntimeError("Agent Shift+N new-session failed for " + label)

    cancelled_view = UIManager(False)
    probe_agent = ProbeAgent()
    agent_app._agent = probe_agent
    agent_app._mode_label = "Chat"
    agent_app._conversation = probe_agent.conversation
    agent_app._state = agent_app.STATE_CHAT
    agent_app.run(cancelled_view)
    if probe_agent.reset_calls or not agent_app._conversation:
        raise RuntimeError("Agent cancelled new-session confirmation lost chat")

    compact = UIManager(width=128, height=64, font_height=8)
    large_font = UIManager(width=320, height=320, font_height=16)
    compact_layout = agent_app._chat_layout(compact)
    large_layout = agent_app._chat_layout(large_font)
    if compact_layout[1] < 12 or compact_layout[3] <= 0:
        raise RuntimeError("Agent compact-screen chat layout is invalid")
    if large_layout[0] < 32 or large_layout[1] < 24:
        raise RuntimeError("Agent layout did not scale with font size")

    agent_app._agent = None
    agent_app._conversation = None
    agent_app._state = agent_app.STATE_MENU
    print("[sim-check:ok] Agent responsive UI typing activity and Shift+N reset")


def _run_agent_storage_check():
    """Verify Agent storage capacity and binary write-mode semantics."""
    from picoware.system.agent.tools.storage import storage_get_info
    from picoware.system.storage import Storage

    class StorageView:
        def __init__(self, storage):
            self.storage = storage

    storage = Storage()
    path = "sim_reports/agent-storage-mode.bin"
    try:
        storage.remove(path)
        if not storage.write(path, b"first", "wb"):
            raise RuntimeError("Agent binary overwrite fixture could not be created")
        if not storage.write(path, b"second", "wb"):
            raise RuntimeError("Agent binary overwrite failed")
        if storage.read(path, "rb") != b"second":
            raise RuntimeError("Agent wb mode appended instead of overwriting")
        if not storage.write(path, b"+", "ab"):
            raise RuntimeError("Agent binary append failed")
        if storage.read(path, "rb") != b"second+":
            raise RuntimeError("Agent ab mode did not append")
        if storage.write(path, b"invalid", "b"):
            raise RuntimeError("Agent storage accepted an invalid write mode")
        capacity = storage_get_info(StorageView(storage))
        if (
            capacity.get("total_space", 0) <= 0
            or capacity.get("free_space", -1) < 0
            or capacity.get("free_space", 0) > capacity.get("total_space", 0)
        ):
            raise RuntimeError("Agent storage capacity contract mismatch")
    finally:
        storage.remove(path)
    print("[sim-check:ok] Agent storage capacity and binary write modes")


def _run_agent_dynamic_mcp_hardening_check():
    """Verify multi-name typo routing and bounded pending-task recovery."""
    from picoware.system.agent.agent import Agent, _declines_pending_mcp
    from picoware.system.agent.mcp import (
        explicit_integration_records,
        normalize_integration_record,
    )

    records = [
        normalize_integration_record({
            "id": "danielsig/duckduckgo",
            "label": "DuckDuckGo",
            "capabilities": ["search"],
        }),
        normalize_integration_record({
            "id": "mcp/microsoft/playwright-mcp",
            "label": "Playwright",
            "capabilities": ["browser"],
        }),
    ]

    def record_ids(values):
        return [item.get("id", "") for item in values]

    independent, independent_ambiguous = explicit_integration_records(
        records,
        "Use duckuck go and playwrith to research Dresden weather",
    )
    if independent_ambiguous or record_ids(independent) != [
        "danielsig/duckduckgo", "mcp/microsoft/playwright-mcp",
    ]:
        raise RuntimeError("Agent did not resolve two independent MCP typos")
    mixed, mixed_ambiguous = explicit_integration_records(
        records,
        "Use DuckDuckGo and playwrith to research Dresden weather",
    )
    if mixed_ambiguous or record_ids(mixed) != [
        "danielsig/duckduckgo", "mcp/microsoft/playwright-mcp",
    ]:
        raise RuntimeError("Agent did not compose exact and fuzzy MCP matches")
    for phrasing in (
        "Use DuckDuckGo then Playwright to research Dresden weather",
        "Use DuckDuckGo for search and Playwright for browsing",
    ):
        phrased, phrased_ambiguous = explicit_integration_records(
            records, phrasing
        )
        if phrased_ambiguous or record_ids(phrased) != [
            "danielsig/duckduckgo", "mcp/microsoft/playwright-mcp",
        ]:
            raise RuntimeError("Agent lost a sequenced MCP name: " + phrasing)

    topic_records = [
        records[0],
        normalize_integration_record({
            "id": "vendor/weather-fetcher",
            "label": "WeatherFetcher",
            "capabilities": ["generic"],
        }),
    ]
    named_only, named_ambiguous = explicit_integration_records(
        topic_records,
        "Use DuckDuckGo to research WeatherFetcher",
    )
    if named_ambiguous or record_ids(named_only) != [
        "danielsig/duckduckgo",
    ]:
        raise RuntimeError("Agent selected an MCP from an exact topic word")

    ambiguous_records = [
        normalize_integration_record({
            "id": "vendor/atlasnavigatorx",
            "capabilities": ["browser"],
        }),
        normalize_integration_record({
            "id": "vendor/atlasnavigatory",
            "capabilities": ["browser"],
        }),
    ]
    ambiguous, ambiguity = explicit_integration_records(
        ambiguous_records, "Use atlasnavigatorz for this"
    )
    resolved, resolved_ambiguity = explicit_integration_records(
        ambiguous_records, "Use atlasnavigatorx for this"
    )
    if (
        ambiguous or not ambiguity or resolved_ambiguity
        or record_ids(resolved) != ["vendor/atlasnavigatorx"]
    ):
        raise RuntimeError("Agent exact MCP label did not resolve ambiguity")

    class RoutingMCP:
        def selected_integrations(self, message):
            selected, ambiguous = explicit_integration_records(records, message)
            return [] if ambiguous else selected

    class RoutingState:
        def __init__(self, conversation):
            self.mcp = RoutingMCP()
            self._conversation = conversation

    original = (
        "Get the current weather of Dresden using duckuck go and playwrith"
    )
    clarification = {
        "role": "assistant",
        "content": (
            "Please use the exact integration label because more than one "
            "configured integration matches."
        ),
    }
    exact_state = RoutingState([
        {"role": "user", "content": original}, clarification,
    ])
    exact_message = Agent._mcp_request_message(
        exact_state, "Use DuckDuckGo and Playwright"
    )
    if (
        original not in exact_message
        or record_ids(exact_state.mcp.selected_integrations(exact_message)) != [
            "danielsig/duckduckgo", "mcp/microsoft/playwright-mcp",
        ]
    ):
        raise RuntimeError("Agent exact MCP labels lost the original topic")

    chained_state = RoutingState([
        {"role": "user", "content": original},
        clarification,
        {"role": "user", "content": "Use DuckDuckGo and Playwright"},
        {
            "role": "assistant",
            "content": "Would you like me to search and open the result?",
        },
        {"role": "user", "content": "yes"},
        {
            "role": "assistant",
            "content": "I'll now navigate to the result. Please wait.",
        },
    ])
    chained_message = Agent._mcp_request_message(chained_state, "go on")
    if (
        original not in chained_message
        or "go on" not in chained_message
        or record_ids(
            chained_state.mcp.selected_integrations(chained_message)
        ) != ["danielsig/duckduckgo", "mcp/microsoft/playwright-mcp"]
    ):
        raise RuntimeError(
            "Agent lost the original exact-label MCP task across confirmations"
        )

    declined_topic = "Use DuckDuckGo to research Dresden weather"
    declined_state = RoutingState([
        {"role": "user", "content": declined_topic},
        {
            "role": "assistant",
            "content": "Would you like me to search for Dresden now?",
        },
    ])
    for reply in (
        "no", "cancel", "stop", "Do not use DuckDuckGo",
        "Cancel DuckDuckGo",
    ):
        if Agent._mcp_request_message(declined_state, reply) != reply:
            raise RuntimeError("Agent carried a declined MCP request: " + reply)
    for replacement in (
        "No, use Playwright instead",
        "No, search for cats instead",
    ):
        if _declines_pending_mcp(
            replacement, declined_state._conversation
        ):
            raise RuntimeError(
                "Agent treated a replacement task as cancellation: "
                + replacement
            )
    replacement_message = Agent._mcp_request_message(
        declined_state, "No, use Playwright instead"
    )
    replacement_ids = record_ids(
        declined_state.mcp.selected_integrations(replacement_message)
    )
    if (
        declined_topic not in replacement_message
        or "mcp/microsoft/playwright-mcp" not in replacement_ids
    ):
        raise RuntimeError("Agent lost the topic on an MCP replacement")


def _run_agent_mcp_metadata_bounds_check():
    """Verify persisted MCP metadata is rejected or filtered at its bounds."""
    from picoware.system.agent.mcp import (
        MAX_MCP_ALLOWED_TOOL_CHARS,
        MAX_MCP_CAPABILITY_CHARS,
        MAX_MCP_RECORD_ID_CHARS,
        MAX_MCP_RECORD_LABEL_CHARS,
        MAX_MCP_RECORD_URL_CHARS,
        normalize_integration_record,
    )

    if normalize_integration_record({
        "id": "i" * (MAX_MCP_RECORD_ID_CHARS + 1),
    }) is not None:
        raise RuntimeError("Agent accepted an oversized MCP record ID")
    if normalize_integration_record({
        "type": "mcp_server",
        "server_label": "l" * (MAX_MCP_RECORD_LABEL_CHARS + 1),
        "server_url": "https://example.invalid/mcp",
    }) is not None:
        raise RuntimeError("Agent accepted an oversized MCP server label")
    oversized_url = (
        "https://example.invalid/"
        + "u" * MAX_MCP_RECORD_URL_CHARS
    )
    if normalize_integration_record({
        "type": "mcp_server",
        "server_label": "Bounded",
        "server_url": oversized_url,
    }) is not None:
        raise RuntimeError("Agent accepted an oversized MCP server URL")

    filtered = normalize_integration_record({
        "id": "vendor/bounded-metadata",
        "label": "l" * (MAX_MCP_RECORD_LABEL_CHARS + 1),
        "capabilities": [
            "search", "c" * (MAX_MCP_CAPABILITY_CHARS + 1),
        ],
        "allowed_tools": [
            "web_search", "t" * (MAX_MCP_ALLOWED_TOOL_CHARS + 1),
        ],
    })
    if (
        filtered.get("label") is not None
        or filtered.get("capabilities") != ["search"]
        or filtered.get("allowed_tools") != ["web_search"]
    ):
        raise RuntimeError("Agent did not filter oversized MCP metadata")

    bounded_headers = normalize_integration_record({
        "type": "mcp_server",
        "server_label": "Bounded headers",
        "server_url": "https://example.invalid/mcp",
        "headers": {
            "Authorization": "local-test-token",
            "k" * 65: "value",
            "X-Oversized": "v" * 513,
        },
    })
    if bounded_headers.get("headers") != {
        "Authorization": "local-test-token",
    }:
        raise RuntimeError("Agent did not filter oversized MCP headers")


def _run_agent_mcp_explicit_stage_check():
    """Verify explicit records each run once and dual records run both roles."""
    from picoware.system.agent.mcp import MCPClient, normalize_integration_record

    class StageProbe(MCPClient):
        def __init__(self):
            self.stages = []

        def _run_stage(self, message, integrations, max_calls=4):
            identities = [
                item.get("id", item.get("server_label", ""))
                for item in integrations
            ]
            self.stages.append((identities, max_calls, message))
            return "Evidence from " + identities[0], 1, ""

    search_records = [
        normalize_integration_record({
            "id": "vendor/alpha-search",
            "label": "AlphaSearch",
            "capabilities": ["search"],
        }),
        normalize_integration_record({
            "id": "vendor/beta-search",
            "label": "BetaSearch",
            "capabilities": ["search"],
        }),
    ]
    search_probe = StageProbe()
    _evidence, search_error = search_probe._research_legacy(
        "Use AlphaSearch and BetaSearch to research this topic",
        search_records, force_each=True,
    )
    if search_error or [stage[:2] for stage in search_probe.stages] != [
        (["vendor/alpha-search"], 1),
        (["vendor/beta-search"], 1),
    ]:
        raise RuntimeError("Agent grouped explicitly named search MCP stages")

    dual_record = normalize_integration_record({
        "id": "vendor/dual-route",
        "label": "DualRoute",
        "capabilities": ["search", "browser"],
    })
    dual_probe = StageProbe()
    _evidence, dual_error = dual_probe._research_legacy(
        "Use DualRoute to research and open the result",
        [dual_record], force_each=True,
    )
    if dual_error or [stage[:2] for stage in dual_probe.stages] != [
        (["vendor/dual-route"], 1),
        (["vendor/dual-route"], 1),
    ]:
        raise RuntimeError("Agent did not route a dual-capability MCP twice")
    if "Search evidence:" not in dual_probe.stages[1][2]:
        raise RuntimeError("Agent browser MCP stage missed its search evidence")


def _run_agent_mcp_turn_evidence_bound_check():
    """Verify one turn bounds combined legacy and direct MCP evidence."""
    from picoware.system.agent.mcp import (
        MAX_MCP_EVIDENCE_CHARS,
        MCPClient,
        normalize_integration_record,
    )

    class View:
        def log(self, _message):
            return

    class DirectProbe:
        def __init__(self, fill):
            self.calls = 0
            self.fill = fill

        def research(self, _message, records):
            self.calls += 1
            if len(records) != 1:
                return "", "direct records were grouped"
            return "# Direct MCP evidence\n" + self.fill * 6000, ""

    class EvidenceProbe(MCPClient):
        def __init__(self, records, fill):
            self.records = records
            self.view_manager = View()
            self.direct = DirectProbe(fill)
            self.stages = []
            self.fill = fill

        def _run_stage(self, _message, integrations, max_calls=4):
            identity = integrations[0].get(
                "id", integrations[0].get("server_label", "")
            )
            self.stages.append((identity, max_calls))
            return identity + "\n" + self.fill * 6000, 1, ""

    records = [
        normalize_integration_record({
            "id": "vendor/alpha-search",
            "label": "AlphaSearch",
            "capabilities": ["search"],
        }),
        normalize_integration_record({
            "id": "vendor/page-browser",
            "label": "PageBrowser",
            "capabilities": ["browser"],
        }),
        normalize_integration_record({
            "id": "vendor/ordinary-data",
            "label": "OrdinaryData",
            "capabilities": ["generic"],
        }),
        normalize_integration_record({
            "type": "mcp_server",
            "server_label": "DirectEvidence",
            "server_url": "https://example.invalid/mcp",
            "capabilities": ["generic"],
        }),
    ]
    request = (
        "Use AlphaSearch and PageBrowser and OrdinaryData and "
        "DirectEvidence to research this topic"
    )
    probe = EvidenceProbe(records, "A")
    evidence, error = probe.research(request)
    if error or len(evidence) != MAX_MCP_EVIDENCE_CHARS:
        raise RuntimeError(
            "Agent turn-wide MCP evidence bound mismatch: "
            + str((error, len(evidence), MAX_MCP_EVIDENCE_CHARS))
        )
    if [stage[0] for stage in probe.stages] != [
        "vendor/alpha-search", "vendor/page-browser", "vendor/ordinary-data",
    ]:
        raise RuntimeError("Agent skipped a bounded legacy MCP evidence stage")
    if any(stage[1] != 1 for stage in probe.stages) or probe.direct.calls != 1:
        raise RuntimeError("Agent changed explicit MCP evidence call isolation")
    if "# Direct MCP evidence" not in evidence:
        raise RuntimeError("Agent turn evidence cap did not reserve direct evidence")

    emoji_probe = EvidenceProbe(records, "😀")
    emoji_evidence, emoji_error = emoji_probe.research(request)
    emoji_bytes = len(emoji_evidence.encode("utf-8"))
    if (
        emoji_error
        or emoji_bytes > MAX_MCP_EVIDENCE_CHARS
        or emoji_bytes < MAX_MCP_EVIDENCE_CHARS - 3
        or "# Direct MCP evidence" not in emoji_evidence
    ):
        raise RuntimeError(
            "Agent multibyte turn evidence exceeded its byte bound: "
            + str((emoji_error, emoji_bytes, MAX_MCP_EVIDENCE_CHARS))
        )


def _run_agent_bare_mcp_label_context_check(view_factory, llm):
    """Verify a bare MCP label only inherits an immediately pending topic."""
    from picoware.system.agent.agent import (
        Agent,
        MCP_EXACT_LABEL_CLARIFICATION,
        MODE_CHAT,
    )
    from picoware.system.agent.mcp import (
        explicit_integration_records,
        normalize_integration_record,
    )

    record = normalize_integration_record({
        "id": "vendor/atlas-navigator",
        "label": "AtlasNavigator",
        "capabilities": ["browser"],
    })

    class LabelMCP:
        enabled = True

        def __init__(self):
            self.records = [record]
            self.integrations = ["plugin:vendor/atlas-navigator"]
            self.calls = 0

        def explicit_selection(self, message):
            return explicit_integration_records(self.records, message)

        def selected_integrations(self, message):
            selected, ambiguous = self.explicit_selection(message)
            return [] if ambiguous else selected

        def research(self, _message):
            self.calls += 1
            return "", "bare label unexpectedly reached MCP transport"

    bare_label = "Use AtlasNavigator"
    for conversation in (
        [],
        [
            {"role": "user", "content": "Research Dresden weather"},
            {
                "role": "assistant",
                "content": "Dresden is 21 C according to the completed research.",
            },
        ],
    ):
        mcp = LabelMCP()
        agent = Agent(view_factory(), MODE_CHAT, llm)
        agent.mcp = mcp
        result = agent.run_payload({
            "message": bare_label,
            "conversation": conversation,
        })
        if (
            result.get("status") != "completed"
            or "specify the page or topic" not in result.get(
                "message", ""
            ).lower()
            or mcp.calls
        ):
            raise RuntimeError("Agent bare MCP label reused a non-pending topic")

    prior_topic = "Research the current Dresden weather"
    for clarification in (
        MCP_EXACT_LABEL_CLARIFICATION,
        "I do not have access to that integration.",
    ):
        pending_agent = Agent(view_factory(), MODE_CHAT, llm)
        pending_agent.mcp = LabelMCP()
        pending_agent._conversation = [
            {"role": "user", "content": prior_topic},
            {"role": "assistant", "content": clarification},
        ]
        carried = pending_agent._mcp_request_message(bare_label)
        if (
            "Previous topic:\n" + prior_topic not in carried
            or "User instruction:\n" + bare_label not in carried
        ):
            raise RuntimeError("Agent bare MCP label lost its pending topic")


def _run_agent_deferral_classifier_check():
    """Verify only unfinished integration-action responses are retried."""
    from picoware.system.agent.agent import _response_defers_completed_work

    for value in (
        "Please confirm that I should search the web.",
        "I'll now navigate to the result. Please wait.",
        "Sure. I can now use the browser; please wait.",
        "Of course. I'll now search the supplied evidence.",
        "Absolutely! Let me browse the relevant result.",
        "I have no evidence yet, so let me search the web.",
        "möchtest du, dass ich danach suche?",
    ):
        if not _response_defers_completed_work(value):
            raise RuntimeError("Agent missed an MCP deferral: " + value)
    for value in (
        "The evidence is insufficient, so I cannot determine the weather.",
        "Dresden is 21 C. Would you like me to search for tomorrow too?",
        "I searched the evidence and found a joke.",
        "Would you like me to explain the limitation?",
    ):
        if _response_defers_completed_work(value):
            raise RuntimeError("Agent misclassified a final answer: " + value)


def _run_agent_large_stream_hardening_check():
    """Verify long Chat/MCP SSE remains RAM-bounded and SD-spool-capped."""
    import json

    from picoware.system.agent.agent import (
        ChatCompletionStreamSink,
        MAX_CHAT_EVENT_BYTES,
        MAX_CHAT_STREAM_BYTES,
        MAX_CHAT_TOOL_ID_CHARS,
        MAX_CHAT_TOOL_NAME_CHARS,
        MAX_CHAT_TOOL_TYPE_CHARS,
        MAX_MESSAGE_CHARS,
    )
    from picoware.system.agent.mcp import (
        IntegrationStreamSink,
        MAX_MCP_EVIDENCE_CHARS,
        MAX_MCP_EVENT_BYTES,
        MAX_MCP_STREAM_BYTES,
        MAX_MCP_TOOL_ID_CHARS,
    )

    class SinkHTTP:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    class CountingStorage:
        def __init__(self):
            self.bytes_written = 0

        def remove(self, _path):
            return True

        def file_open(self, _path):
            return object()

        def file_write(self, _file_obj, data, _mode="wb"):
            self.bytes_written += len(data)
            return True

        def file_close(self, _file_obj):
            return

    chat_storage = CountingStorage()
    chat_sink = ChatCompletionStreamSink(
        SinkHTTP(), chat_storage,
        "picoware/settings/agent_large_chat_stream.tmp",
    )
    chat_chatter = (
        "data: "
        + json.dumps({
            "choices": [{
                "delta": {"reasoning_content": "r" * 6000},
                "finish_reason": None,
            }]
        })
        + "\n\n"
    ).encode("utf-8")
    chat_count = (262144 // len(chat_chatter)) + 2
    for _ in range(chat_count):
        chat_sink.write(chat_chatter)
    chat_answer = (
        "data: "
        + json.dumps({
            "choices": [{
                "delta": {"content": "Dresden evidence answer"},
                "finish_reason": "stop",
            }]
        })
        + "\n\ndata: [DONE]\n\n"
    ).encode("utf-8")
    chat_sink.write(chat_answer)
    chat_sink.close()
    chat_message, chat_error = chat_sink.result()
    chat_total = chat_count * len(chat_chatter) + len(chat_answer)
    chat_spooled = min(chat_total, MAX_CHAT_STREAM_BYTES)
    if (
        chat_error
        or chat_message != {"content": "Dresden evidence answer"}
        or chat_sink.total_bytes != chat_total
        or chat_sink.total_bytes <= 262144
        or chat_sink.spooled_bytes != chat_spooled
        or chat_storage.bytes_written != chat_spooled
        or len(chat_sink.buffer) > MAX_CHAT_EVENT_BYTES
        or len(chat_sink.content) > MAX_MESSAGE_CHARS
    ):
        raise RuntimeError(
            "Agent large Chat stream was not SD-spooled with bounded RAM: "
            + str((
                chat_error, chat_sink.total_bytes, chat_sink.spooled_bytes,
                chat_storage.bytes_written, len(chat_sink.buffer),
            ))
        )

    framed_chat = ChatCompletionStreamSink(SinkHTTP())
    framed_chat_event = (
        b": heartbeat\n\n"
        b"event: message\nid: chat-1\n"
        + (
            "data: "
            + json.dumps({
                "choices": [{
                    "delta": {"content": "framed answer"},
                    "finish_reason": "stop",
                }]
            })
            + "\n\n"
        ).encode("utf-8")
        + b"event: done\ndata: [DONE]\n\n"
    )
    framed_chat.write(framed_chat_event[:31])
    framed_chat.write(framed_chat_event[31:])
    framed_message, framed_error = framed_chat.result()
    if framed_error or framed_message != {"content": "framed answer"}:
        raise RuntimeError("Agent Chat SSE event-field compatibility mismatch")

    for field, limit in (
        ("id", MAX_CHAT_TOOL_ID_CHARS),
        ("name", MAX_CHAT_TOOL_NAME_CHARS),
        ("type", MAX_CHAT_TOOL_TYPE_CHARS),
    ):
        metadata_sink = ChatCompletionStreamSink(SinkHTTP())
        tool_delta = {
            "index": 0,
            "function": {"name": "storage_read", "arguments": "{}"},
        }
        if field == "name":
            tool_delta["function"]["name"] = "x" * (limit + 1)
        else:
            tool_delta[field] = "x" * (limit + 1)
        metadata_sink._append_tool_calls([tool_delta])
        if not metadata_sink.error:
            raise RuntimeError(
                "Agent streamed tool " + field + " was not memory-bounded"
            )

    mcp_storage = CountingStorage()
    mcp_sink = IntegrationStreamSink(
        SinkHTTP(), mcp_storage,
        "picoware/settings/agent_large_mcp_stream.tmp", max_calls=1,
    )
    mcp_chatter = (
        "data: "
        + json.dumps({"type": "chat.delta", "content": "c" * 6000})
        + "\n\n"
    ).encode("utf-8")
    mcp_count = (262144 // len(mcp_chatter)) + 2
    for _ in range(mcp_count):
        mcp_sink.write(mcp_chatter)
    mcp_result = (
        b'data: {"type":"tool_call.arguments","tool":"search",'
        b'"arguments":{"q":"Dresden"}}\n\n'
        b'data: {"type":"tool_call.success",'
        b'"output":"current Dresden evidence"}\n\n'
    )
    mcp_sink.write(mcp_result)
    mcp_sink.close()
    mcp_total = mcp_count * len(mcp_chatter) + len(mcp_result)
    mcp_spooled = min(mcp_total, MAX_MCP_STREAM_BYTES)
    if (
        mcp_sink.issue
        or mcp_sink.error
        or mcp_sink.call_count != 1
        or mcp_sink.evidence != ["current Dresden evidence"]
        or mcp_sink.total_bytes != mcp_total
        or mcp_sink.total_bytes <= 262144
        or mcp_sink.spooled_bytes != mcp_spooled
        or mcp_storage.bytes_written != mcp_spooled
        or len(mcp_sink.buffer) > MAX_MCP_EVENT_BYTES
    ):
        raise RuntimeError(
            "Agent large MCP stream was not SD-spooled with bounded RAM: "
            + str((
                mcp_sink.issue, mcp_sink.error, mcp_sink.total_bytes,
                mcp_sink.spooled_bytes, mcp_storage.bytes_written,
                len(mcp_sink.buffer),
            ))
        )

    framed_mcp = IntegrationStreamSink(SinkHTTP(), max_calls=1)
    framed_mcp.write(
        b": gateway heartbeat\n\n"
        b"event: tool\nid: mcp-1\n"
        b'data: {"type":"tool_call.arguments","tool":"search",'
        b'"arguments":{"q":"Dresden"}}\n\n'
        b"event: tool\n"
        b'data: {"type":"tool_call.success",'
        b'"output":"framed MCP evidence"}\n\n'
    )
    if (
        framed_mcp.issue or framed_mcp.error
        or framed_mcp.call_count != 1
        or framed_mcp.evidence != ["framed MCP evidence"]
    ):
        raise RuntimeError("Agent LM MCP SSE event-field compatibility mismatch")

    emoji_sink = IntegrationStreamSink(SinkHTTP(), max_calls=4)
    emoji_sink.write(
        b'data: {"type":"tool_call.arguments","tool":"search",'
        b'"arguments":{"q":"emoji"}}\n\n'
    )
    emoji_output = "😀" * 1000
    for _ in range(4):
        emoji_sink.write(
            (
                "data: "
                + json.dumps({
                    "type": "tool_call.success", "output": emoji_output,
                })
                + "\n\n"
            ).encode("utf-8")
        )
    joined_emoji_evidence = "".join(emoji_sink.evidence)
    joined_emoji_bytes = len(joined_emoji_evidence.encode("utf-8"))
    if (
        emoji_sink.issue or emoji_sink.error
        or emoji_sink.evidence_bytes != MAX_MCP_EVIDENCE_CHARS
        or joined_emoji_bytes != MAX_MCP_EVIDENCE_CHARS
    ):
        raise RuntimeError(
            "Agent streamed MCP evidence exceeded its UTF-8 byte cap: "
            + str((
                emoji_sink.issue, emoji_sink.error,
                emoji_sink.evidence_bytes, joined_emoji_bytes,
            ))
        )

    identity_sink = IntegrationStreamSink(SinkHTTP(), max_calls=1)
    identity_sink.write(
        (
            'data: {"type":"tool_call.arguments","tool":"'
            + ("x" * (MAX_MCP_TOOL_ID_CHARS + 1))
            + '","arguments":{}}\n\n'
        ).encode("utf-8")
    )
    if not identity_sink.issue:
        raise RuntimeError("Agent MCP tool identity was not memory-bounded")


def _run_agent_negative_mcp_check(storage_factory):
    """Verify declined pending work never reaches an MCP transport."""
    import json

    from picoware.system.agent.agent import Agent, MODE_CHAT
    from picoware.system.agent.llm import LLM, LOCAL
    from picoware.system.agent.mcp import (
        explicit_integration_records,
        normalize_integration_record,
    )

    record = normalize_integration_record({
        "id": "danielsig/duckduckgo",
        "label": "DuckDuckGo",
        "capabilities": ["search"],
    })

    class View:
        def __init__(self, storage):
            self.storage = storage
            self.thread_manager = None

        def log(self, _message):
            return

    class ProbeMCP:
        enabled = True
        integrations = ["plugin:danielsig/duckduckgo"]

        def __init__(self):
            self.transport_calls = 0

        def explicit_selection(self, message):
            return explicit_integration_records([record], message)

        def selected_integrations(self, message):
            selected, ambiguous = self.explicit_selection(message)
            return [] if ambiguous else selected

        def research(self, message):
            if self.selected_integrations(message):
                self.transport_calls += 1
            return "", ""

    class Response:
        status_code = 200
        reason = b"OK"

        def close(self):
            return

    class HTTP:
        def close(self):
            return

        def post(self, _url, **kwargs):
            kwargs["stream_sink"].write(
                (
                    "data: "
                    + json.dumps({
                        "choices": [{
                            "delta": {"content": "Acknowledged."},
                            "finish_reason": "stop",
                        }]
                    })
                    + "\n\ndata: [DONE]\n\n"
                ).encode("utf-8")
            )
            return Response()

    pending = [
        {
            "role": "user",
            "content": "Use DuckDuckGo to research Dresden weather",
        },
        {
            "role": "assistant",
            "content": "Would you like me to search for Dresden now?",
        },
    ]
    for index, reply in enumerate((
        "no", "cancel", "stop", "Do not use DuckDuckGo",
        "Cancel DuckDuckGo",
    )):
        storage = storage_factory()
        probe = ProbeMCP()
        agent = Agent(
            View(storage), MODE_CHAT, LLM(storage, LOCAL, "local/test"),
            file_path=(
                "picoware/settings/agent-negative-" + str(index) + ".json"
            ),
        )
        agent.mcp = probe
        agent.http = HTTP()
        result = agent.run_payload({
            "message": reply, "conversation": pending,
        })
        if result.get("status") != "completed" or probe.transport_calls:
            raise RuntimeError("Agent invoked MCP for declined work: " + reply)


def _run_agent_utf8_context_check(storage_factory):
    """Verify SD context streaming preserves split UTF-8 code points."""
    import json

    from picoware.system.agent.agent import Agent

    storage = storage_factory()
    source_path = "picoware/settings/agent-utf8-source.tmp"
    destination_path = "picoware/settings/agent-utf8-destination.tmp"
    source = ("a" * 2047) + "€" + ' quote=" slash=\\\nend'
    try:
        storage.write(source_path, source.encode("utf-8"), "wb")
        storage.remove(destination_path)
        Agent._stream_file_json_escaped(
            storage, source_path, destination_path
        )
        escaped = storage.read(destination_path, "r")
        if json.loads('"' + escaped + '"') != source:
            raise RuntimeError("Agent split UTF-8 SD context changed content")
    finally:
        storage.remove(source_path)
        storage.remove(destination_path)


def _run_agent_control_character_json_check(storage_factory):
    """Verify streamed control characters remain valid in request JSON."""
    import json

    from picoware.system.agent.agent import (
        Agent,
        MCP_EVIDENCE_PREAMBLE,
        MODE_CHAT,
    )
    from picoware.system.agent.llm import LLM, LOCAL
    from picoware.system.agent.mcp import IntegrationStreamSink

    class SinkHTTP:
        def close(self):
            return

    control_evidence = "nul\x00back\bform\f"
    sink = IntegrationStreamSink(SinkHTTP(), max_calls=1)
    sink.write(
        (
            "data: "
            + json.dumps({
                "type": "tool_call.arguments",
                "tool": "control_probe",
                "arguments": {},
            })
            + "\n\ndata: "
            + json.dumps({
                "type": "tool_call.success",
                "output": control_evidence,
            })
            + "\n\n"
        ).encode("utf-8")
    )
    if sink.issue or sink.error or sink.evidence != [control_evidence]:
        raise RuntimeError("Agent changed streamed MCP control characters")

    class View:
        def __init__(self, storage):
            self.storage = storage
            self.thread_manager = None

        def log(self, _message):
            return

    storage = storage_factory()
    request_path = "picoware/settings/agent-control-request.json"
    agent = Agent(
        View(storage), MODE_CHAT, LLM(storage, LOCAL, "local/test"),
        file_path=request_path,
    )
    user_request = "request\x00back\bform\f"
    try:
        storage.remove(agent._conv_path)
        agent._conv_append_user_request(user_request, sink.evidence[0])
        agent._build_request([])
        raw_request = storage.read(request_path, "r")
        if any(char in raw_request for char in ("\x00", "\b", "\f")):
            raise RuntimeError("Agent wrote a raw control byte into request JSON")
        payload = json.loads(raw_request)
        expected = user_request + MCP_EVIDENCE_PREAMBLE + control_evidence
        if payload["messages"][0].get("content") != expected:
            raise RuntimeError("Agent request JSON changed control characters")
    finally:
        storage.remove(agent._conv_path)
        storage.remove(request_path)


def _run_agent_request_limit_check(storage_factory, retry_requests):
    """Verify exact per-mode Chat Completions output limits, including retry."""
    import json

    from picoware.system.agent.agent import (
        Agent,
        MAX_APP_OUTPUT_TOKENS,
        MAX_CHAT_OUTPUT_TOKENS,
        MAX_MANAGER_OUTPUT_TOKENS,
        MODE_APP_CREATOR,
        MODE_CHAT,
        MODE_DEVICE_MANAGER,
    )
    from picoware.system.agent.llm import LLM, LOCAL

    class View:
        def __init__(self, storage):
            self.storage = storage
            self.thread_manager = None

        def log(self, _message):
            return

    expected = (
        (MODE_CHAT, MAX_CHAT_OUTPUT_TOKENS),
        (MODE_DEVICE_MANAGER, MAX_MANAGER_OUTPUT_TOKENS),
        (MODE_APP_CREATOR, MAX_APP_OUTPUT_TOKENS),
    )
    for mode, token_limit in expected:
        storage = storage_factory()
        request_path = (
            "picoware/settings/agent-limit-" + str(mode) + ".json"
        )
        agent = Agent(
            View(storage), mode, LLM(storage, LOCAL, "local/test"),
            file_path=request_path,
        )
        storage.write(
            agent._conv_path,
            '{"role":"system","content":""},'
            '{"role":"user","content":"test"}',
            "w",
        )
        agent._build_request([], require_visible_answer=(mode == MODE_CHAT))
        payload = json.loads(storage.read(request_path, "r"))
        if payload.get("max_tokens") != token_limit:
            raise RuntimeError(
                "Agent mode max_tokens mismatch: "
                + str((mode, payload.get("max_tokens"), token_limit))
            )
    if not retry_requests or any(
        request.get("max_tokens") != MAX_CHAT_OUTPUT_TOKENS
        for request in retry_requests
    ):
        raise RuntimeError("Agent Chat retry changed the exact max_tokens limit")


def _run_agent_direct_planner_limit_check(requests, model_url):
    """Verify the direct MCP planner has its exact small output budget."""
    from picoware.system.agent.mcp_standard import MAX_MCP_PLANNER_TOKENS

    planner = [
        payload for url, payload, _headers in requests
        if url == model_url and isinstance(payload, dict)
        and not payload.get("method")
    ]
    if (
        MAX_MCP_PLANNER_TOKENS != 256 or len(planner) != 1
        or planner[0].get("max_tokens") != MAX_MCP_PLANNER_TOKENS
    ):
        raise RuntimeError("Agent direct MCP planner max_tokens mismatch")


def _run_agent_scratch_cleanup_check(storage_factory):
    """Verify scratch files are deleted while durable Agent state survives."""
    import json

    from picoware.system.agent.agent import Agent, MODE_CHAT
    from picoware.system.agent.llm import LLM, LOCAL

    class View:
        def __init__(self, storage):
            self.storage = storage
            self.thread_manager = None

        def log(self, _message):
            return

    class Response:
        status_code = 200
        reason = b"OK"

        def close(self):
            return

    class HTTP:
        def __init__(self, fail=False):
            self.fail = fail

        def close(self):
            return

        def post(self, _url, **kwargs):
            if self.fail:
                return None
            kwargs["stream_sink"].write(
                (
                    "data: "
                    + json.dumps({
                        "choices": [{
                            "delta": {"content": "OK"},
                            "finish_reason": "stop",
                        }]
                    })
                    + "\n\ndata: [DONE]\n\n"
                ).encode("utf-8")
            )
            return Response()

    def run_case(fail):
        suffix = "error" if fail else "success"
        storage = storage_factory()
        request_path = "picoware/settings/agent-clean-" + suffix + ".json"
        agent = Agent(
            View(storage), MODE_CHAT, LLM(storage, LOCAL, "local/test"),
            file_path=request_path,
        )
        agent._conv_path = "picoware/settings/agent-clean-conv-" + suffix
        agent._mem_path = "picoware/settings/agent-clean-mem-" + suffix
        agent._msg_path = "picoware/settings/agent-clean-msg-" + suffix
        agent._state_path = "picoware/settings/agent-clean-state-" + suffix
        prior = [
            {"role": "user", "content": "Earlier"},
            {"role": "assistant", "content": "Earlier answer"},
        ] if fail else []
        agent.http = HTTP(fail)
        result = agent.run_payload({
            "message": "Say OK", "conversation": prior,
        })
        expected_status = "error" if fail else "completed"
        if result.get("status") != expected_status:
            raise RuntimeError("Agent scratch cleanup fixture status mismatch")
        for path in (
            request_path, agent._conv_path, agent._mem_path, agent._msg_path,
        ):
            if storage.exists(path):
                raise RuntimeError("Agent retained scratch file: " + path)
        if not storage.exists(agent._state_path):
            raise RuntimeError("Agent cleanup removed durable state")
        state = storage.serialize(agent._state_path)
        expected_conversation = prior if fail else [
            {"role": "user", "content": "Say OK"},
            {"role": "assistant", "content": "OK"},
        ]
        if state.get("conversation") != expected_conversation:
            raise RuntimeError("Agent cleanup changed durable conversation state")

    run_case(False)
    run_case(True)


def _run_agent_evidence_completion_hardening_check(storage, view_factory):
    """Verify MCP evidence is synthesized without another approval turn."""
    import json

    from picoware.system.agent.agent import Agent, MODE_CHAT
    from picoware.system.agent.llm import LLM, LOCAL

    class OKResponse:
        status_code = 200
        reason = b"OK"

        def close(self):
            return

    class EvidenceMCP:
        enabled = True

        def __init__(self):
            self.calls = 0
            self.integrations = ["plugin:vendor/web-search"]

        def explicit_selection(self, _message):
            return [], False

        def selected_integrations(self, _message):
            return [{"type": "plugin", "id": "vendor/web-search"}]

        def research(self, _message):
            self.calls += 1
            return (
                "# Search evidence\nDresden weather evidence "
                "https://example.com/weather",
                "",
            )

    class DeferralHTTP:
        def __init__(self, responses):
            self.responses = responses
            self.requests = []

        def close(self):
            return

        def post(self, _url, **kwargs):
            request_bytes = storage.writes[kwargs["send_file"]]
            self.requests.append(
                json.loads(bytes(request_bytes).decode("utf-8"))
            )
            index = min(len(self.requests) - 1, len(self.responses) - 1)
            kwargs["stream_sink"].write(
                (
                    "data: "
                    + json.dumps({
                        "choices": [{
                            "delta": {"content": self.responses[index]},
                            "finish_reason": "stop",
                        }]
                    })
                    + "\n\ndata: [DONE]\n\n"
                ).encode("utf-8")
            )
            return OKResponse()

    evidence_mcp = EvidenceMCP()
    deferral_http = DeferralHTTP([
        "Please confirm that I should search for the requested weather.",
        "Dresden weather: 21 C according to the supplied evidence.",
    ])
    deferral_agent = Agent(
        view_factory(), MODE_CHAT,
        LLM(storage, LOCAL, "qwen/qwen3.5-9b"),
        file_path="picoware/settings/agent-deferral-request.json",
    )
    deferral_agent.mcp = evidence_mcp
    deferral_agent.http = deferral_http
    result = deferral_agent.run_payload({
        "message": "Research Dresden weather", "conversation": [],
    })
    if (
        result.get("status") != "completed"
        or result.get("message")
        != "Dresden weather: 21 C according to the supplied evidence."
        or evidence_mcp.calls != 1
        or len(deferral_http.requests) != 2
        or result.get("conversation") != [
            {"role": "user", "content": "Research Dresden weather"},
            {
                "role": "assistant",
                "content": (
                    "Dresden weather: 21 C according to the supplied evidence."
                ),
            },
        ]
    ):
        raise RuntimeError("Agent post-evidence deferral recovery mismatch")
    retry_messages = deferral_http.requests[1].get("messages", [])
    retry_text = "\n".join(
        message.get("content", "")
        for message in retry_messages
        if isinstance(message, dict)
    ).lower()
    if (
        "already completed" not in retry_text
        or "confirmation" not in retry_text
        or "answer" not in retry_text
        or any(
            message.get("role") == "assistant"
            and "please confirm" in message.get("content", "").lower()
            for message in retry_messages
            if isinstance(message, dict)
        )
    ):
        raise RuntimeError("Agent post-evidence retry lacked a completion guard")
    for request in deferral_http.requests:
        saw_non_system = False
        for message in request.get("messages", []):
            if message.get("role") == "system":
                if saw_non_system:
                    raise RuntimeError(
                        "Agent emitted a system message after conversation start"
                    )
            else:
                saw_non_system = True

    repeated_mcp = EvidenceMCP()
    repeated_http = DeferralHTTP([
        "I'll now search the supplied evidence. Please wait.",
    ])
    repeated_agent = Agent(
        view_factory(), MODE_CHAT,
        LLM(storage, LOCAL, "qwen/qwen3.5-9b"),
        file_path="picoware/settings/agent-repeated-deferral-request.json",
    )
    repeated_agent.mcp = repeated_mcp
    repeated_agent.http = repeated_http
    repeated = repeated_agent.run_payload({
        "message": "Research Dresden weather", "conversation": [],
    })
    if (
        repeated.get("status") != "error"
        or not repeated.get("message", "").startswith("API error:")
        or repeated_mcp.calls != 1
        or len(repeated_http.requests) != 2
        or repeated_agent.conversation
    ):
        raise RuntimeError("Agent repeated post-evidence deferral was not bounded")


def _run_agent_mcp_check():
    """Verify provider-6 compatibility, MCP selection, and body streaming."""
    import json

    from picoware.applications import agent as agent_app
    from picoware.system.agent.agent import (
        Agent,
        ChatCompletionStreamSink,
        MAX_CHAT_TOOL_ARGUMENT_CHARS,
        MODE_APP_CREATOR,
        MODE_CHAT,
        MODE_DEVICE_MANAGER,
        _clean_model_content,
        _mcp_reference_needs_topic,
        _request_tool_names,
    )
    from picoware.system.agent.llm import (
        LLM, LOCAL, LOCAL_MCP, OPENAI,
        local_model_catalog_url, parse_local_models,
    )
    from picoware.system.agent.mcp import (
        IntegrationStreamSink,
        MCPClient,
        _current_time_grounding,
        _tool_loop_issue as _mcp_tool_loop_issue,
        explicit_integration_records,
        integration_key,
        integration_gateway_url,
        merge_integration_records,
        normalize_integration_record,
        parse_integration_catalog,
        parse_integration_records,
        parse_integrations,
        preserve_catalog_records,
        serialize_integration_records,
    )
    from picoware.system.agent.mcp_standard import (
        BoundedJSONSink,
        MCP_PROTOCOL_LEGACY,
        MCP_PROTOCOL_MODERN,
        StandardMCPAdapter,
    )
    from picoware.system.agent.mcp_lmstudio import MAX_BROWSER_MCP_CALLS
    from picoware.system.agent.tools.network import (
        MAX_NETWORK_SPOOL_BYTES, NetworkResponseStreamSink,
    )
    from picoware.system.agent.tools.storage import storage_read
    from picoware.system.http import HTTP
    from picoware.system.settings import Settings

    class ConfigStorage:
        class File:
            def __init__(self, path):
                self.path = path
                self.position = 0

        def __init__(self):
            self.writes = {}
            self.config = {
                "local_url": "http://192.0.2.10:1234/v1/chat/completions",
                "local_api_key": "configured",
                "local_mcp_servers": (
                    "plugin:local/toolguard-current-time,"
                    "vendor/web-search,vendor/page-browser,"
                    "server:Private Search|http://192.0.2.20/mcp"
                ),
            }

        def exists(self, path):
            return path == "picoware/settings/picoware.json" or path in self.writes

        def read(self, path, mode="r", index=0, count=0):
            if path == "picoware/settings/picoware.json":
                return json.dumps(self.config)
            value = self.writes.get(path, b"")
            if isinstance(value, str):
                value = value.encode("utf-8")
            else:
                value = bytes(value)
            if count:
                value = value[index:index + count]
            return value.decode("utf-8") if mode == "r" else value

        def write(self, path, data, mode="w"):
            if path == "picoware/settings/picoware.json":
                if not isinstance(data, str):
                    data = bytes(data).decode("utf-8")
                self.config = json.loads(data)
                return True
            if isinstance(data, str):
                data = data.encode("utf-8")
            data = bytearray(data)
            if mode in ("a", "ab") and path in self.writes:
                current = self.writes[path]
                if isinstance(current, str):
                    current = current.encode("utf-8")
                self.writes[path] = bytearray(current) + data
            else:
                self.writes[path] = data
            return True

        def remove(self, path):
            self.writes.pop(path, None)
            return True

        def file_open(self, path):
            if path not in self.writes:
                self.writes[path] = bytearray()
            return self.File(path)

        def file_write(self, file_obj, data, mode="wb"):
            if isinstance(data, str):
                data = data.encode("utf-8")
            value = self.writes[file_obj.path]
            if isinstance(value, str):
                value = bytearray(value.encode("utf-8"))
            elif not isinstance(value, bytearray):
                value = bytearray(value)
            if file_obj.position == len(value):
                value.extend(data)
                file_obj.position += len(data)
                self.writes[file_obj.path] = value
                return True
            end = file_obj.position + len(data)
            if end > len(value):
                value.extend(b"\x00" * (end - len(value)))
            value[file_obj.position:end] = data
            file_obj.position = end
            self.writes[file_obj.path] = value
            return True

        def file_close(self, _file_obj):
            return

        def file_readinto(self, file_obj, buffer):
            value = self.writes.get(file_obj.path, b"")
            if isinstance(value, str):
                value = value.encode("utf-8")
            start = file_obj.position
            count = min(len(buffer), max(0, len(value) - start))
            if count:
                buffer[:count] = value[start:start + count]
                file_obj.position += count
            return count

        def serialize(self, path):
            if path not in self.writes:
                return {}
            return json.loads(self.read(path, "r"))

        def deserialize(self, data, path):
            return self.write(path, json.dumps(data), "w")

    storage = ConfigStorage()
    llm = LLM(storage, LOCAL_MCP, "qwen/qwen3.5-9b")
    if llm.name != "Local + MCP" or llm.id != 6:
        raise RuntimeError("Agent provider-6 compatibility mismatch")
    if llm.url != "http://192.0.2.10:1234/v1/chat/completions":
        raise RuntimeError("Agent Local + MCP did not use Chat Completions")
    if "Authorization" not in llm.headers:
        raise RuntimeError("Agent Local + MCP omitted configured authentication")
    if "local_mcp_servers" in storage.config:
        raise RuntimeError("Agent MCP legacy setting was not migrated once")
    if not storage.config.get("mcp_integrations"):
        raise RuntimeError("Agent MCP legacy migration lost integrations")

    migrated = storage.config["mcp_integrations"]
    settings = Settings(storage)
    settings.mcp_integrations = ""
    storage.config["local_mcp_servers"] = migrated
    if Settings(storage).mcp_integrations != "":
        raise RuntimeError("Agent MCP clear resurrected a legacy setting")
    settings = Settings(storage)
    settings.mcp_integrations = migrated
    if "local_mcp_servers" in storage.config:
        raise RuntimeError("Agent MCP setter retained the legacy setting")
    if settings.mcp_gateway_url:
        raise RuntimeError("Agent generic settings derived a provider endpoint")
    if integration_gateway_url("", llm.url) != (
        "http://192.0.2.10:1234/api/v1/chat"
    ):
        raise RuntimeError("Agent LM Studio adapter fallback mismatch")

    if _request_tool_names(MODE_CHAT, "research a good joke", True):
        raise RuntimeError("Agent exposed device tools after MCP evidence")
    if _request_tool_names(MODE_CHAT, "tell me a joke"):
        raise RuntimeError("Agent exposed device tools for plain chat")
    if _request_tool_names(MODE_CHAT, "scan nearby wifi networks") != (
        "network_scan_wifi",
    ):
        raise RuntimeError("Agent Chat Wi-Fi tool routing mismatch")
    if "storage_write" not in _request_tool_names(
        MODE_APP_CREATOR, "create an app"
    ):
        raise RuntimeError("Agent App Creator storage tools missing")
    if "network_send_request" not in _request_tool_names(
        MODE_DEVICE_MANAGER, "fetch a URL"
    ):
        raise RuntimeError("Agent Device Manager network tools missing")

    cleaned_history = Agent._sanitize_conversation(
        None,
        [
            {"role": "user", "content": "research a good joke"},
            {
                "role": "assistant",
                "content": (
                    "An error occurred during processing: "
                    "memory allocation failed, allocating 61920 bytes"
                ),
            },
            {"role": "user", "content": "working question"},
            {"role": "assistant", "content": "working answer"},
            {"role": "user", "content": "interrupted question"},
        ],
    )
    if cleaned_history != [
        {"role": "user", "content": "working question"},
        {"role": "assistant", "content": "working answer"},
    ]:
        raise RuntimeError("Agent retained a failed historical turn")

    standard_items = agent_app._settings_menu_items(0)
    local_mcp_items = agent_app._settings_menu_items(LOCAL_MCP)
    if "Scan Integrations" in standard_items:
        raise RuntimeError("Agent integration scanner shown outside Local + MCP")
    if "Scan Integrations" not in local_mcp_items:
        raise RuntimeError("Agent integration scanner hidden for Local + MCP")
    if "Add MCP Server" not in local_mcp_items:
        raise RuntimeError("Agent self-hosted MCP entry hidden for Local + MCP")
    if "Add MCP Catalog" not in local_mcp_items:
        raise RuntimeError("Agent MCP catalog entry hidden for Local + MCP")
    if not agent_app._provider_change_preserves_model(LOCAL, LOCAL_MCP):
        raise RuntimeError("Agent Local to Local + MCP model was not preserved")
    if not agent_app._provider_change_preserves_model(LOCAL_MCP, LOCAL):
        raise RuntimeError("Agent Local + MCP to Local model was not preserved")
    if not agent_app._provider_change_preserves_model(OPENAI, OPENAI):
        raise RuntimeError("Agent same-provider model was not preserved")
    if agent_app._provider_change_preserves_model(LOCAL_MCP, OPENAI):
        raise RuntimeError("Agent cross-provider model was incorrectly preserved")

    parsed = parse_integrations(
        "plugin:local/toolguard-current-time,mcp/duckduckgo,"
        "mcp/microsoft/playwright-mcp"
    )
    if parsed != [
        "local/toolguard-current-time",
        "mcp/duckduckgo",
        "mcp/microsoft/playwright-mcp",
    ]:
        raise RuntimeError("Agent MCP opaque integration IDs were changed")
    records = parse_integration_records(storage.config["mcp_integrations"])
    if records[-1].get("type") != "ephemeral_mcp" or (
        records[-1].get("server_url") != "http://192.0.2.20/mcp"
    ):
        raise RuntimeError("Agent self-hosted MCP record migration mismatch")
    round_trip = parse_integration_records(serialize_integration_records(records))
    if [integration_key(item) for item in round_trip] != [
        integration_key(item) for item in records
    ]:
        raise RuntimeError("Agent MCP record serialization mismatch")
    wrapped_records = parse_integration_records({
        "integrations": "plugin:vendor/one,plugin:vendor/two"
    })
    if [integration_key(item) for item in wrapped_records] != [
        "plugin:vendor/one", "plugin:vendor/two",
    ]:
        raise RuntimeError("Agent MCP wrapped string records were split into characters")
    gateway = integration_gateway_url("", llm.url)
    if gateway != "http://192.0.2.10:1234/api/v1/chat":
        raise RuntimeError("Agent MCP gateway fallback mismatch")
    if integration_gateway_url("http://host/mcp", llm.url) != "http://host/mcp":
        raise RuntimeError("Agent MCP explicit gateway was not preserved")

    class ViewManager:
        def __init__(self):
            self.storage = storage
            self.thread_manager = None

        def log(self, _message):
            return

    class ModelResponse:
        status_code = 200

        def json(self):
            return {
                "data": [
                    {"id": "qwen/qwen3.5-9b@q4_k_m"},
                    {"id": "local/custom-model"},
                ]
            }

        def close(self):
            return

    class ModelHTTP:
        def __init__(self):
            self.url = ""

        def get(self, url, **_kwargs):
            self.url = url
            return ModelResponse()

    model_http = ModelHTTP()
    custom_model = "qwen/qwen3.5-9b@q4_k_m"
    local_models = agent_app._get_llm_models(
        ViewManager(), LOCAL_MCP, custom_model, http=model_http
    )
    if model_http.url != "http://192.0.2.10:1234/v1/models":
        raise RuntimeError("Agent llama.cpp model discovery URL mismatch")
    if custom_model not in local_models:
        raise RuntimeError("Agent model chooser dropped a custom Local model")
    custom_index = local_models.index(custom_model)
    saved_models = agent_app._get_llm_models(
        ViewManager(), LOCAL_MCP, local_models[custom_index], http=ModelHTTP()
    )
    if saved_models[custom_index] != custom_model:
        raise RuntimeError("Agent model chooser changed a custom Local model")
    old_models = agent_app._get_llm_models(
        ViewManager(), LOCAL_MCP, "qwen3.5:9b", http=ModelHTTP()
    )
    if "qwen3.5:9b" in old_models:
        raise RuntimeError("Agent retained a removed Ollama-style model default")
    if local_model_catalog_url(llm.url) != model_http.url:
        raise RuntimeError("Agent model discovery helper mismatch")
    if parse_local_models(ModelResponse().json()) != local_models:
        raise RuntimeError("Agent local model catalog parsing mismatch")
    if agent_app._model_at_index(local_models, custom_index) != custom_model:
        raise RuntimeError("Agent model chooser did not preserve its displayed snapshot")
    if agent_app._model_at_index([], custom_index):
        raise RuntimeError("Agent model chooser accepted a stale model index")

    class ErrorResponse:
        status_code = 400
        reason = b"Bad Request"

        def close(self):
            return

    class ErrorHTTP:
        def close(self):
            return

        def post(self, _url, **kwargs):
            kwargs["stream_sink"].write(
                b'{"error":{"message":"Invalid model identifier"}}'
            )
            return ErrorResponse()

    error_client = MCPClient(ViewManager(), ErrorHTTP(), llm)
    _evidence, error_calls, gateway_error = error_client._run_stage(
        "Call one tool", ["mcp/test"], max_calls=1
    )
    if error_calls != 0 or gateway_error != (
        "MCP gateway HTTP 400: Invalid model identifier"
    ):
        raise RuntimeError("Agent MCP HTTP error reporting mismatch")

    class OKResponse:
        status_code = 200
        reason = b"OK"

        def close(self):
            return

    class NoToolThenSuccessHTTP:
        def __init__(self):
            self.calls = 0
            self.requests = []

        def close(self):
            return

        def post(self, _url, **kwargs):
            self.calls += 1
            self.requests.append(storage.writes[kwargs["send_file"]])
            sink = kwargs["stream_sink"]
            if self.calls == 1:
                sink.write(b'data: {"type":"chat.end"}')
            else:
                # Valid gateway streams do not always emit arguments first.
                sink.write(
                    b'data: {"type":"tool_call.success",'
                    b'"output":"retried evidence"}'
                )
            sink.flush()
            return OKResponse()

    retry_http = NoToolThenSuccessHTTP()
    retry_client = MCPClient(ViewManager(), retry_http, llm)
    retry_evidence, retry_calls, retry_error = retry_client._run_stage(
        "research a good joke",
        [{"type": "plugin", "id": "mcp/duckduckgo"}],
        max_calls=1,
    )
    if (
        retry_error or retry_calls != 1
        or retry_evidence != "retried evidence"
        or retry_http.calls != 2
    ):
        raise RuntimeError("Agent MCP bounded no-tool retry mismatch")
    retry_payload = json.loads(retry_http.requests[-1])
    if "must call exactly one" not in retry_payload["input"]:
        raise RuntimeError("Agent MCP retry did not strengthen tool instruction")

    class NoResponseHTTP:
        def __init__(self):
            self.calls = 0

        def close(self):
            return

        def post(self, _url, **_kwargs):
            self.calls += 1
            return None

    no_response_http = NoResponseHTTP()
    no_response_client = MCPClient(ViewManager(), no_response_http, llm)
    _evidence, no_response_calls, no_response_error = (
        no_response_client._run_stage(
            "research a good joke",
            [{"type": "plugin", "id": "mcp/duckduckgo"}],
            max_calls=1,
        )
    )
    if (
        no_response_calls != 0
        or no_response_http.calls != 1
        or no_response_error != "MCP gateway returned no response."
    ):
        raise RuntimeError("Agent MCP transport failure was treated as no-tool output")

    repeated_history = []
    if _mcp_tool_loop_issue(repeated_history, "search", {"q": "same"}):
        raise RuntimeError("Agent MCP loop guard rejected the first call")
    if "repeated with identical arguments" not in _mcp_tool_loop_issue(
        repeated_history, "search", {"q": "same"}
    ):
        raise RuntimeError("Agent MCP loop guard allowed a duplicate call")

    client = MCPClient(ViewManager(), object(), llm)
    generic_record = normalize_integration_record({
        "type": "plugin",
        "id": "vendor/ordinary-files",
        "capabilities": ["generic"],
    })
    dynamic_browser = normalize_integration_record({
        "type": "plugin",
        "id": "vendor/acmeatlasnavigator-mcp",
        "capabilities": ["browser"],
    })
    shared_vendor_reader = normalize_integration_record({
        "type": "plugin",
        "id": "acme/first-reader",
        "capabilities": ["fetch"],
    })
    shared_vendor_search = normalize_integration_record({
        "type": "plugin",
        "id": "acme/second-search",
        "capabilities": ["search"],
    })
    client.records.extend((
        generic_record,
        dynamic_browser,
        shared_vendor_reader,
        shared_vendor_search,
    ))
    current = client.selected_integrations("What is the current time today?")
    if [item["id"] for item in current] != ["local/toolguard-current-time"]:
        raise RuntimeError("Agent MCP current-time profile mismatch")
    web = client.selected_integrations(
        "Search the web and open this page to inspect the result"
    )
    web_ids = [item.get("id", item.get("server_label")) for item in web]
    if (
        "vendor/web-search" not in web_ids
        or "vendor/page-browser" not in web_ids
        or "Private Search" not in web_ids
    ):
        raise RuntimeError("Agent MCP web profile mismatch")
    named_search = client.selected_integrations("Use web-search")
    if [item["id"] for item in named_search] != ["vendor/web-search"]:
        raise RuntimeError("Agent MCP named integration routing mismatch")
    named_amazon = client.selected_integrations(
        "Use web-search to search Amazon"
    )
    if [item["id"] for item in named_amazon] != ["vendor/web-search"]:
        raise RuntimeError("Agent explicit MCP selection lost to topic routing")
    research = client.selected_integrations("research a good joke")
    research_ids = [item.get("id", "") for item in research]
    if "vendor/web-search" not in research_ids:
        raise RuntimeError("Agent generic research did not select search capability")
    if not any(item.get("type") == "ephemeral_mcp" for item in research):
        raise RuntimeError("Agent generic research excluded self-hosted MCP")
    if "vendor/ordinary-files" in research_ids:
        raise RuntimeError("Agent web research selected a generic integration")
    exact_dynamic = client.selected_integrations(
        "Use atlasnavigator to open https://example.com"
    )
    if [item.get("id", "") for item in exact_dynamic] != [
        "vendor/acmeatlasnavigator-mcp"
    ]:
        raise RuntimeError("Agent did not match a product embedded in a dynamic ID")
    fuzzy_dynamic = client.selected_integrations(
        "Use atlasnavigater for this"
    )
    if [item.get("id", "") for item in fuzzy_dynamic] != [
        "vendor/acmeatlasnavigator-mcp"
    ]:
        raise RuntimeError("Agent did not resolve a unique dynamic MCP typo")
    if client.selected_integrations("An article mentions atlasnavigater"):
        raise RuntimeError("Agent fuzzy-matched an MCP without explicit intent")
    shared_vendor = client.selected_integrations(
        "Use acme/first-reader to open https://example.com"
    )
    if [item.get("id", "") for item in shared_vendor] != [
        "acme/first-reader"
    ]:
        raise RuntimeError("Agent selected another MCP through a shared vendor word")
    multiple_named = client.selected_integrations(
        "Use acme/first-reader and acme/second-search"
    )
    if [item.get("id", "") for item in multiple_named] != [
        "acme/first-reader", "acme/second-search",
    ]:
        raise RuntimeError("Agent dropped explicitly named dynamic MCPs")
    _run_agent_dynamic_mcp_hardening_check()
    _run_agent_mcp_metadata_bounds_check()
    _run_agent_mcp_explicit_stage_check()
    _run_agent_mcp_turn_evidence_bound_check()
    _run_agent_bare_mcp_label_context_check(ViewManager, llm)
    _run_agent_deferral_classifier_check()
    _run_agent_negative_mcp_check(ConfigStorage)
    _run_agent_utf8_context_check(ConfigStorage)
    _run_agent_control_character_json_check(ConfigStorage)
    ambiguous_records = [
        normalize_integration_record({
            "id": "vendor/atlasnavigatorx",
            "capabilities": ["browser"],
        }),
        normalize_integration_record({
            "id": "vendor/atlasnavigatory",
            "capabilities": ["browser"],
        }),
    ]
    ambiguous_match, ambiguous = explicit_integration_records(
        ambiguous_records, "Use atlasnavigatorz for this"
    )
    if ambiguous_match or not ambiguous:
        raise RuntimeError("Agent fuzzy MCP ambiguity was not rejected")
    ambiguous_client = MCPClient(ViewManager(), object(), llm)
    ambiguous_client.records = ambiguous_records
    ambiguous_agent = Agent(ViewManager(), MODE_CHAT, llm)
    ambiguous_agent.mcp = ambiguous_client
    ambiguous_result = ambiguous_agent.run_payload({
        "message": "Use atlasnavigatorz for this",
        "conversation": [],
    })
    if (
        ambiguous_result.get("status") != "completed"
        or "exact integration label" not in ambiguous_result.get(
            "message", ""
        ).lower()
    ):
        raise RuntimeError("Agent did not clarify an ambiguous dynamic MCP name")
    suffix_typo, suffix_ambiguous = explicit_integration_records(
        [normalize_integration_record({
            "id": "vendor/acmenovelwright-mcp",
            "capabilities": ["browser"],
        })],
        "Use novelwrite for this",
    )
    if (
        suffix_ambiguous
        or [item.get("id", "") for item in suffix_typo]
        != ["vendor/acmenovelwright-mcp"]
    ):
        raise RuntimeError("Agent missed a suffix typo in a dynamic MCP name")
    reported_typo, reported_ambiguous = explicit_integration_records(
        [normalize_integration_record({
            "id": "mcp/microsoftplaywright-mcp",
            "capabilities": ["browser"],
        })],
        "find the current weather for dresden saxony on wetter.com "
        "using playwrte",
    )
    if (
        reported_ambiguous
        or [item.get("id", "") for item in reported_typo]
        != ["mcp/microsoftplaywright-mcp"]
    ):
        raise RuntimeError("Agent missed the reported dynamic MCP typo")
    distant_prefix, distant_ambiguous = explicit_integration_records(
        [normalize_integration_record({
            "id": "vendor/playzz-mcp",
            "capabilities": ["browser"],
        })],
        "Use playwrte for this",
    )
    if distant_prefix or distant_ambiguous:
        raise RuntimeError("Agent accepted a distant same-prefix MCP name")
    search_and_open = client.selected_integrations(
        "Search the web and open the result"
    )
    search_and_open_ids = [item.get("id", "") for item in search_and_open]
    if (
        "vendor/web-search" not in search_and_open_ids
        or "vendor/page-browser" not in search_and_open_ids
        or "vendor/ordinary-files" in search_and_open_ids
    ):
        raise RuntimeError("Agent capability routing did not compose search and browser")

    class BrowserBudgetClient(MCPClient):
        def __init__(self):
            super().__init__(ViewManager(), object(), llm)
            self.budgets = []

        def _run_stage(self, _message, _integrations, max_calls=4):
            self.budgets.append(max_calls)
            return "browser evidence", 1, ""

    budget_client = BrowserBudgetClient()
    budget_evidence, budget_error = budget_client._research_legacy(
        "Inspect the requested page", [dynamic_browser]
    )
    if (
        budget_error or "browser evidence" not in budget_evidence
        or budget_client.budgets != [MAX_BROWSER_MCP_CALLS]
        or MAX_BROWSER_MCP_CALLS < 2
    ):
        raise RuntimeError(
            "Agent browser MCP did not receive a multi-step budget: "
            + str((budget_error, budget_evidence, budget_client.budgets,
                   MAX_BROWSER_MCP_CALLS))
        )
    if client.selected_integrations("Reply with exactly OK"):
        raise RuntimeError("Agent MCP loaded integrations for plain chat")
    if not _mcp_reference_needs_topic("Use atlasnavigater for this"):
        raise RuntimeError("Agent missed an incomplete explicit MCP reference")

    clarification_agent = Agent(ViewManager(), MODE_CHAT, llm)
    clarification_agent.mcp = client
    clarification_result = clarification_agent.run_payload({
        "message": "Use atlasnavigater for this",
        "conversation": [],
    })
    if (
        clarification_result.get("status") != "completed"
        or "specify the page or topic" not in clarification_result.get(
            "message", ""
        ).lower()
    ):
        raise RuntimeError("Agent called an integration without a referenced topic")

    class RoutingState:
        def __init__(self, conversation):
            self.mcp = client
            self._conversation = conversation

    clarification = RoutingState([
        {"role": "user", "content": "do a websearch"},
        {
            "role": "assistant",
            "content": "Please specify a search topic or query.",
        },
    ])
    carried = Agent._mcp_request_message(
        clarification, "topic is dad joke"
    )
    if (
        "Previous request:\ndo a websearch" not in carried
        or "User clarification:\ntopic is dad joke" not in carried
    ):
        raise RuntimeError("Agent MCP clarification routing mismatch")
    completed = RoutingState([
        {"role": "user", "content": "search for a good joke"},
        {"role": "assistant", "content": "Here is a researched joke."},
    ])
    if Agent._mcp_request_message(completed, "thanks") != "thanks":
        raise RuntimeError("Agent repeated completed MCP research")
    confirmation = RoutingState([
        {
            "role": "user",
            "content": "Use atlasnavigater to inspect the weather page",
        },
        {
            "role": "assistant",
            "content": (
                "The page showed the wrong city. Would you like me to search "
                "for the requested city or try another site?"
            ),
        },
    ])
    confirmed_message = Agent._mcp_request_message(confirmation, "yes")
    confirmed_ids = [
        item.get("id", "")
        for item in client.selected_integrations(confirmed_message)
    ]
    if (
        "User confirmation:\nyes" not in confirmed_message
        or confirmed_ids != ["vendor/acmeatlasnavigator-mcp"]
    ):
        raise RuntimeError("Agent lost an affirmative dynamic MCP continuation")
    if Agent._mcp_request_message(confirmation, "no") != "no":
        raise RuntimeError("Agent treated a negative MCP reply as confirmation")
    non_action_offer = RoutingState([
        confirmation._conversation[0],
        {
            "role": "assistant",
            "content": "Would you like me to explain the limitation?",
        },
    ])
    if Agent._mcp_request_message(non_action_offer, "yes") != "yes":
        raise RuntimeError("Agent carried MCP into a non-tool confirmation")
    stale_confirmation = RoutingState([
        confirmation._conversation[0], confirmation._conversation[1],
        {"role": "user", "content": "Thanks"},
        {"role": "assistant", "content": "You are welcome."},
    ])
    if Agent._mcp_request_message(stale_confirmation, "yes") != "yes":
        raise RuntimeError("Agent reused a stale MCP confirmation")
    named_followup = RoutingState([
        {"role": "user", "content": "topic is dad joke"},
        {
            "role": "assistant",
            "content": "I do not have access to that search tool.",
        },
    ])
    named_message = Agent._mcp_request_message(
        named_followup, "use web-search"
    )
    if (
        "Previous topic:\ntopic is dad joke" not in named_message
        or "User instruction:\nuse web-search" not in named_message
    ):
        raise RuntimeError("Agent MCP named follow-up lost its topic")
    dynamic_followup = RoutingState(clarification_result["conversation"])
    dynamic_message = Agent._mcp_request_message(
        dynamic_followup, "research cookware"
    )
    dynamic_ids = [
        item.get("id", "")
        for item in client.selected_integrations(dynamic_message)
    ]
    if (
        "Previous request:\nUse atlasnavigater for this" not in dynamic_message
        or dynamic_ids != ["vendor/acmeatlasnavigator-mcp"]
    ):
        raise RuntimeError("Agent lost a dynamic MCP choice after clarification")
    refusal_followup = RoutingState([
        {"role": "user", "content": "Use atlasnavigater for this"},
        {
            "role": "assistant",
            "content": "I do not have access to that integration.",
        },
    ])
    refusal_message = Agent._mcp_request_message(
        refusal_followup, "research cookware"
    )
    refusal_ids = [
        item.get("id", "")
        for item in client.selected_integrations(refusal_message)
    ]
    if refusal_ids != ["vendor/acmeatlasnavigator-mcp"]:
        raise RuntimeError("Agent did not recover a previously refused dynamic MCP")
    client._write_request("What is the current time today?", current)
    gateway_payload = json.loads(storage.writes[client.request_path])
    if "think" in gateway_payload or "reasoning" in gateway_payload:
        raise RuntimeError("Agent MCP leaked provider-specific reasoning settings")
    if "Call at least one provided integration tool" not in gateway_payload["input"]:
        raise RuntimeError("Agent MCP did not require selected tool execution")

    catalog = parse_integration_catalog(
        {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps([
                        {"id": "mcp/picoware-integration-catalog"},
                        {
                            "id": "danielsig/duckduckgo",
                            "capabilities": ["search"],
                            "allowed_tools": ["Web Search"],
                        },
                        {"id": "plugin:local/toolguard-current-time"},
                        {
                            "type": "ephemeral_mcp",
                            "server_label": "Docs",
                            "server_url": "http://192.0.2.30/mcp",
                            "capabilities": ["fetch"],
                        },
                    ]),
                }
            ]
        }
    )
    catalog_keys = [integration_key(item) for item in catalog]
    if catalog_keys != [
        "plugin:danielsig/duckduckgo",
        "plugin:local/toolguard-current-time",
        "server:Docs|http://192.0.2.30/mcp",
    ]:
        raise RuntimeError("Agent MCP integration catalog parsing mismatch")
    if catalog[0].get("allowed_tools") != ["Web Search"]:
        raise RuntimeError("Agent MCP catalog dropped tool metadata")

    class ScanClient(MCPClient):
        def _run_stage(self, _message, integrations, max_calls=4):
            if integrations != [
                {"type": "plugin", "id": "mcp/picoware-integration-catalog"}
            ]:
                return "", 0, "catalog route mismatch"
            return json.dumps([
                {"id": "danielsig/duckduckgo", "capabilities": ["search"]},
                {"id": "vendor/new-search", "capabilities": ["search"]},
            ]), 1, ""

    scan_client = ScanClient(ViewManager(), object(), llm)
    unconfigured_scan, unconfigured_error = scan_client.scan_integrations()
    if unconfigured_scan or "No integration catalog configured" not in (
        unconfigured_error
    ):
        raise RuntimeError("Agent MCP scanner pretended configured records were discoveries")
    catalog_record = normalize_integration_record(
        "mcp/picoware-integration-catalog"
    )
    scan_client.records.append(catalog_record)
    configured_keys = [integration_key(item) for item in scan_client.records]
    scanned, scan_error = scan_client.scan_integrations()
    scanned_keys = [integration_key(item) for item in scanned]
    if scan_error or not all(key in scanned_keys for key in configured_keys):
        raise RuntimeError("Agent MCP integration scan mismatch")
    if "plugin:vendor/new-search" not in scanned_keys:
        raise RuntimeError("Agent MCP integration scan did not merge discoveries")
    if merge_integration_records(records, []) != records:
        raise RuntimeError("Agent MCP empty scan changed configured records")

    protected_catalog = normalize_integration_record({
        "type": "plugin",
        "id": "mcp/picoware-integration-catalog",
        "capabilities": ["catalog"],
    })
    staged_search = normalize_integration_record({
        "type": "plugin",
        "id": "vendor/new-search",
        "capabilities": ["search"],
    })
    preserved = preserve_catalog_records(
        [protected_catalog, catalog[0]], [staged_search], 16
    )
    preserved_keys = [integration_key(item) for item in preserved]
    if preserved_keys != [
        "plugin:mcp/picoware-integration-catalog",
        "plugin:vendor/new-search",
    ]:
        raise RuntimeError("Agent MCP tool edit did not preserve its catalog")
    if agent_app._selectable_integration_records(
        [protected_catalog, staged_search]
    ) != [staged_search]:
        raise RuntimeError("Agent MCP catalog remained user-toggleable")
    recovered_catalog = agent_app._catalog_input_record(
        "mcp/picoware-integration-catalog"
    )
    if (
        integration_key(recovered_catalog)
        != "plugin:mcp/picoware-integration-catalog"
        or recovered_catalog.get("capabilities") != ["catalog"]
    ):
        raise RuntimeError("Agent MCP plugin catalog recovery mismatch")
    recovered_endpoint = agent_app._catalog_input_record(
        "Docs|http://192.0.2.30/mcp"
    )
    if (
        integration_key(recovered_endpoint)
        != "server:Docs|http://192.0.2.30/mcp"
        or recovered_endpoint.get("capabilities") != ["catalog"]
    ):
        raise RuntimeError("Agent ephemeral catalog recovery mismatch")

    direct_record = normalize_integration_record({
        "type": "mcp_server",
        "server_label": "Direct Search",
        "server_url": "http://192.0.2.40/mcp",
        "protocol": "auto",
        "capabilities": ["search"],
    })
    direct_round_trip = parse_integration_records(
        serialize_integration_records([direct_record])
    )
    if (
        len(direct_round_trip) != 1
        or direct_round_trip[0].get("type") != "mcp_server"
        or direct_round_trip[0].get("protocol") != "auto"
    ):
        raise RuntimeError("Agent direct MCP record round-trip mismatch")

    direct_add_storage = ConfigStorage()
    direct_add_storage.config.pop("local_mcp_servers", None)
    direct_add_storage.config["mcp_integrations"] = ""

    class DirectAddView:
        def __init__(self):
            self.storage = direct_add_storage
            self.alerts = []

        def alert(self, message, _back):
            self.alerts.append(message)
            return True

    direct_add_view = DirectAddView()
    if not agent_app._save_mcp_server(
        direct_add_view, "Direct Docs|http://192.0.2.41/mcp", False
    ):
        raise RuntimeError("Agent rejected a valid direct MCP server")
    added_records = parse_integration_records(
        Settings(direct_add_storage).mcp_integrations
    )
    if len(added_records) != 1 or added_records[0].get("type") != "mcp_server":
        raise RuntimeError("Agent Add MCP Server retained gateway semantics")

    class DirectResponse:
        def __init__(self, status_code=200, headers=None):
            self.status_code = status_code
            self.reason = b"OK"
            self.headers = headers or {}

        def close(self):
            return

    class DirectHTTP:
        def __init__(self, request_storage):
            self.storage = request_storage
            self.requests = []
            self.closed = False

        def close(self):
            self.closed = True

        def post(self, url, **kwargs):
            payload = kwargs.get("payload")
            send_file = kwargs.get("send_file")
            if send_file:
                payload = json.loads(self.storage.read(send_file, "r"))
            elif payload is None:
                payload = {}
            headers = kwargs.get("headers", {})
            self.requests.append((url, payload, dict(headers)))
            method = payload.get("method", "") if isinstance(payload, dict) else ""
            if url == llm.url and not method:
                result = {
                    "choices": [{
                        "message": {
                            "tool_calls": [{
                                "function": {
                                    "name": "mcp_0_0",
                                    "arguments": json.dumps({
                                        "query": "a good programming joke"
                                    }),
                                }
                            }]
                        }
                    }]
                }
            elif method == "server/discover":
                result = {
                    "jsonrpc": "2.0", "id": payload["id"],
                    "result": {"capabilities": {"tools": {}}},
                }
            elif method == "tools/list":
                result = {
                    "jsonrpc": "2.0", "id": payload["id"],
                    "result": {"tools": [{
                        "name": "web_search",
                        "description": "Search the web for current information",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    }]},
                }
            elif method == "tools/call":
                result = {
                    "jsonrpc": "2.0", "id": payload["id"],
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": "A programmer walks into a foo bar.",
                        }],
                        "isError": False,
                    },
                }
            else:
                result = {"error": {"message": "unexpected request"}}
            sink = kwargs["stream_sink"]
            sink.write(json.dumps(result).encode("utf-8"))
            sink.flush()
            return DirectResponse()

    direct_storage = ConfigStorage()
    direct_storage.config.pop("local_mcp_servers", None)
    direct_storage.config["mcp_integrations"] = serialize_integration_records([
        direct_record
    ])
    direct_view = ViewManager()
    direct_view.storage = direct_storage
    direct_llm = LLM(direct_storage, LOCAL_MCP, "qwen/qwen3.5-9b")
    direct_http = DirectHTTP(direct_storage)
    direct_client = MCPClient(direct_view, direct_http, direct_llm)
    direct_evidence, direct_error = direct_client.research(
        "research a good joke"
    )
    if direct_error or "foo bar" not in direct_evidence:
        raise RuntimeError(
            "Agent direct modern MCP research mismatch: "
            + direct_error + " | " + direct_evidence
        )
    if direct_client.direct.planner_path in direct_storage.writes:
        raise RuntimeError("Agent direct MCP planner scratch was not removed")
    _run_agent_direct_planner_limit_check(direct_http.requests, direct_llm.url)
    direct_tool_call = [
        request for request in direct_http.requests
        if isinstance(request[1], dict)
        and request[1].get("method") == "tools/call"
    ]
    if len(direct_tool_call) != 1:
        raise RuntimeError("Agent direct MCP did not execute exactly one tool")
    modern_headers = direct_tool_call[0][2]
    if (
        modern_headers.get("MCP-Protocol-Version") != MCP_PROTOCOL_MODERN
        or modern_headers.get("Mcp-Method") != "tools/call"
        or modern_headers.get("Mcp-Name") != "web_search"
    ):
        raise RuntimeError("Agent direct MCP modern routing headers mismatch")
    if any("/api/v1/chat" in request[0] for request in direct_http.requests):
        raise RuntimeError("Agent direct MCP was routed through LM Studio")
    scanned_direct, direct_scan_error = direct_client.scan_integrations()
    if (
        direct_scan_error
        or scanned_direct[0].get("allowed_tools") != ["web_search"]
        or "search" not in scanned_direct[0].get("capabilities", [])
    ):
        raise RuntimeError("Agent direct MCP tools/list scan mismatch")

    class LegacyHTTP:
        def __init__(self):
            self.requests = []

        def close(self):
            return

        def post(self, _url, **kwargs):
            payload = kwargs.get("payload", {})
            headers = dict(kwargs.get("headers", {}))
            self.requests.append((payload, headers))
            method = payload.get("method", "")
            response_headers = {}
            status = 200
            if headers.get("MCP-Protocol-Version") == MCP_PROTOCOL_MODERN:
                result = {
                    "jsonrpc": "2.0", "id": payload.get("id"),
                    "error": {"code": -32601, "message": "Method not found"},
                }
            elif method == "initialize":
                response_headers = {"Mcp-Session-Id": "legacy-session"}
                result = {
                    "jsonrpc": "2.0", "id": payload["id"],
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_LEGACY,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "legacy", "version": "1"},
                    },
                }
            elif method == "notifications/initialized":
                result = None
                status = 202
            elif method == "tools/list":
                result = {
                    "jsonrpc": "2.0", "id": payload["id"],
                    "result": {"tools": [{
                        "name": "legacy_search",
                        "description": "Search legacy data",
                        "inputSchema": {"type": "object", "properties": {}},
                    }]},
                }
            else:
                result = {"error": {"message": "unexpected legacy request"}}
            if result is not None:
                sink = kwargs["stream_sink"]
                sink.write(json.dumps(result).encode("utf-8"))
                sink.flush()
            return DirectResponse(status, response_headers)

    legacy_record = normalize_integration_record({
        "type": "mcp_server",
        "server_label": "Legacy Search",
        "server_url": "http://192.0.2.50/mcp",
        "protocol": "auto",
        "capabilities": ["search"],
    })
    legacy_http = LegacyHTTP()
    legacy_adapter = StandardMCPAdapter(direct_view, legacy_http, direct_llm)
    legacy_tools, legacy_context, legacy_error = legacy_adapter.list_tools(
        legacy_record
    )
    if (
        legacy_error or [tool["name"] for tool in legacy_tools]
        != ["legacy_search"]
        or legacy_context.get("protocol") != MCP_PROTOCOL_LEGACY
        or legacy_context.get("session") != "legacy-session"
    ):
        raise RuntimeError("Agent direct MCP legacy fallback mismatch")
    if not any(
        payload.get("method") == "tools/list"
        and headers.get("Mcp-Session-Id") == "legacy-session"
        for payload, headers in legacy_http.requests
    ):
        raise RuntimeError("Agent direct MCP legacy session was not reused")

    bounded_http = DirectHTTP(direct_storage)
    bounded_rpc_sink = BoundedJSONSink(bounded_http, 1024)
    bounded_rpc_sink.write(b"x" * 1025)
    if not bounded_rpc_sink.error or not bounded_http.closed:
        raise RuntimeError("Agent direct MCP response bound was not enforced")

    stage_storage = ConfigStorage()
    stage_storage.config.pop("local_mcp_servers", None)
    stage_storage.config["mcp_integrations"] = serialize_integration_records([
        protected_catalog, catalog[0],
    ])

    class StageView:
        def __init__(self):
            self.storage = stage_storage
            self.alerts = []

        def alert(self, message, _back):
            self.alerts.append(message)
            return True

    stage_view = StageView()
    agent_app._integration_ids = [catalog[0]]
    agent_app._integration_staged_records = parse_integration_records(
        stage_storage.config["mcp_integrations"]
    )
    agent_app._integration_initial_keys = [
        integration_key(item)
        for item in agent_app._integration_staged_records
    ]
    agent_app._integration_dirty = False
    persisted_before_toggle = stage_storage.config["mcp_integrations"]
    agent_app._set_integration_active(stage_view, 0, False)
    if stage_storage.config["mcp_integrations"] != persisted_before_toggle:
        raise RuntimeError("Agent MCP toggle wrote settings before confirmation")
    if not agent_app._integration_dirty:
        raise RuntimeError("Agent MCP staged toggle was not marked dirty")
    agent_app._commit_integration_changes(stage_view)
    committed_keys = [
        integration_key(item) for item in parse_integration_records(
            stage_storage.config["mcp_integrations"]
        )
    ]
    if committed_keys != ["plugin:mcp/picoware-integration-catalog"]:
        raise RuntimeError("Agent MCP confirmed toggle lost its catalog")
    agent_app._integration_ids = None
    agent_app._integration_staged_records = None
    agent_app._integration_initial_keys = None
    agent_app._integration_dirty = False

    class ProbeRTC:
        def datetime(self):
            return (2026, 8, 16, 6, 12, 34, 56, 0)

    class ProbeTime:
        is_set = True
        is_fetching = False
        rtc = ProbeRTC()

    clock_view = ViewManager()
    clock_view.time = ProbeTime()
    clock_view.gmt_offset = 2
    grounding = _current_time_grounding(clock_view)
    if "2026-08-16T12:34:56" not in grounding or "+02:00" not in grounding:
        raise RuntimeError("Agent MCP current-time grounding mismatch")

    class SinkHTTP:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    chat_http = SinkHTTP()
    chat_spool_path = "picoware/settings/agent_chat_stream.tmp"
    chat_sink = ChatCompletionStreamSink(
        chat_http, storage, chat_spool_path
    )
    reasoning_event = (
        "data: "
        + json.dumps({
            "choices": [{
                "delta": {
                    "reasoning_content": "x" * 12000,
                    "content": "A good ",
                },
                "finish_reason": None,
            }]
        })
        + "\n\n"
    ).encode()
    answer_event = (
        "data: "
        + json.dumps({
            "choices": [{
                "delta": {"content": "joke"},
                "finish_reason": "stop",
            }]
        })
        + "\n\ndata: [DONE]\n\n"
    ).encode()
    chat_sink.write(reasoning_event[:317])
    chat_sink.write(reasoning_event[317:] + answer_event)
    chat_sink.close()
    chat_message, chat_error = chat_sink.result()
    if chat_error or chat_message != {"content": "A good joke"}:
        raise RuntimeError("Agent Chat Completions answer streaming mismatch")
    if not storage.writes.get(chat_spool_path):
        raise RuntimeError("Agent Chat Completions SD spool was not written")
    storage.remove(chat_spool_path)
    if chat_spool_path in storage.writes:
        raise RuntimeError("Agent Chat Completions SD spool was not removed")
    _run_agent_large_stream_hardening_check()

    tool_sink = ChatCompletionStreamSink(SinkHTTP())
    tool_events = (
        b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,'
        b'"id":"call_1","type":"function","function":{"name":'
        b'"network_","arguments":"{\\"url\\":\\"https"}}]},'
        b'"finish_reason":null}]}\n\n'
        b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,'
        b'"function":{"name":"send_request","arguments":'
        b'"://example.com\\"}"}}]},"finish_reason":"tool_calls"}]}\n\n'
        b'data: [DONE]\n\n'
    )
    tool_sink.write(tool_events[:91])
    tool_sink.write(tool_events[91:])
    tool_message, tool_error = tool_sink.result()
    tool_calls = tool_message.get("tool_calls", []) if tool_message else []
    if tool_error or len(tool_calls) != 1:
        raise RuntimeError("Agent Chat Completions tool streaming mismatch")
    streamed_function = tool_calls[0].get("function", {})
    if (
        streamed_function.get("name") != "network_send_request"
        or streamed_function.get("arguments")
        != '{"url":"https://example.com"}'
    ):
        raise RuntimeError("Agent streamed tool-call assembly mismatch")
    oversized_sink = ChatCompletionStreamSink(SinkHTTP())
    oversized_sink._append_tool_calls([{
        "index": 0,
        "function": {
            "name": "storage_write",
            "arguments": "x" * (MAX_CHAT_TOOL_ARGUMENT_CHARS + 1),
        },
    }])
    if "exceeded the device limit" not in oversized_sink.error:
        raise RuntimeError("Agent streamed tool arguments were not memory-bounded")

    network_spool_path = "picoware/settings/agent_network_stream.tmp"
    network_sink = NetworkResponseStreamSink(storage, network_spool_path)
    network_sink.write(b"x" * 12000)
    network_sink.close()
    network_text = network_sink.text()
    if len(network_sink.body) != 8192 or not network_sink.truncated:
        raise RuntimeError("Agent network response was not RAM-bounded")
    if len(storage.writes.get(network_spool_path, b"")) != 12000:
        raise RuntimeError("Agent network response SD spool mismatch")
    if not network_text.endswith("[Response truncated to fit device memory.]"):
        raise RuntimeError("Agent network response truncation was not reported")
    storage.remove(network_spool_path)
    if network_spool_path in storage.writes:
        raise RuntimeError("Agent network response SD spool was not removed")
    invalid_utf8_sink = NetworkResponseStreamSink()
    invalid_utf8_sink.write(bytes((97, 255, 98)))
    invalid_text = invalid_utf8_sink.text()
    if not invalid_text.startswith("a") or not invalid_text.endswith("b"):
        raise RuntimeError("Agent network decoder discarded valid trailing text")

    class CountingStorage:
        def __init__(self):
            self.bytes_written = 0

        def remove(self, _path):
            return True

        def file_open(self, _path):
            return object()

        def file_write(self, _file_obj, data, _mode="wb"):
            self.bytes_written += len(data)
            return True

        def file_close(self, _file_obj):
            return

    capped_http = SinkHTTP()
    capped_storage = CountingStorage()
    capped_path = "picoware/settings/agent_network_cap.tmp"
    capped_sink = NetworkResponseStreamSink(
        capped_storage, capped_path, http=capped_http
    )
    remaining = MAX_NETWORK_SPOOL_BYTES + 1
    chunk = b"z" * 4096
    while remaining > 0:
        count = min(len(chunk), remaining)
        capped_sink.write(chunk[:count])
        remaining -= count
    capped_sink.close()
    if (
        capped_sink.total_bytes != MAX_NETWORK_SPOOL_BYTES
        or capped_sink.spooled_bytes != MAX_NETWORK_SPOOL_BYTES
        or capped_storage.bytes_written != MAX_NETWORK_SPOOL_BYTES
        or not capped_sink.truncated
        or not capped_http.closed
    ):
        raise RuntimeError("Agent network cap did not terminate the HTTP stream")
    capped_storage.remove(capped_path)

    class ReadStorage:
        def __init__(self):
            self.request = None

        def read(self, path, mode="r", index=0, count=0):
            self.request = (path, mode, index, count)
            return "x" * count

    class ReadView:
        def __init__(self):
            self.storage = ReadStorage()

    read_view = ReadView()
    if len(storage_read(read_view, "picoware/apps/large.py")) != 8192:
        raise RuntimeError("Agent storage read was not bounded")
    if read_view.storage.request[-1] != 8192:
        raise RuntimeError("Agent storage read did not request a bounded page")

    sink_http = SinkHTTP()
    sink = IntegrationStreamSink(sink_http, max_calls=1)
    events = (
        b'data: {"type":"tool_call.arguments","tool":"search",'
        b'"arguments":{"q":"picoware"}}\n\n'
        b'data: {"type":"tool_call.success","output":"bounded evidence"}\n\n'
    )
    sink.write(events[:37])
    sink.write(events[37:])
    if sink.call_count != 1 or sink.evidence != ["bounded evidence"]:
        raise RuntimeError("Agent MCP streaming evidence mismatch")
    if not sink.complete or not sink_http.closed:
        raise RuntimeError("Agent MCP streaming limit did not stop generation")

    browser_http = SinkHTTP()
    browser_sink = IntegrationStreamSink(
        browser_http, max_calls=MAX_BROWSER_MCP_CALLS
    )
    for index in range(MAX_BROWSER_MCP_CALLS):
        browser_sink.write(
            (
                'data: {"type":"tool_call.arguments","tool":"step_'
                + str(index) + '","arguments":{"step":' + str(index)
                + '}}\n\ndata: {"type":"tool_call.success","output":"page '
                + str(index) + '"}\n\n'
            ).encode("utf-8")
        )
        if index + 1 < MAX_BROWSER_MCP_CALLS and (
            browser_sink.complete or browser_http.closed
        ):
            raise RuntimeError("Agent browser MCP stopped before its bounded budget")
    if (
        browser_sink.call_count != MAX_BROWSER_MCP_CALLS
        or browser_sink.success_count != MAX_BROWSER_MCP_CALLS
        or browser_sink.evidence != ["page 0", "page 1", "page 2"]
        or not browser_sink.complete
        or not browser_http.closed
    ):
        raise RuntimeError("Agent browser MCP multi-step stream mismatch")

    trailing_http = SinkHTTP()
    trailing_sink = IntegrationStreamSink(trailing_http, max_calls=1)
    trailing_sink.write(
        b'data: {"type":"tool_call.success","output":"tail evidence"}'
    )
    trailing_sink.flush()
    if trailing_sink.evidence != ["tail evidence"] or trailing_sink.call_count != 1:
        raise RuntimeError("Agent MCP trailing SSE event was discarded")

    class Collector:
        def __init__(self):
            self.data = bytearray()

        def write(self, value):
            self.data.extend(value)

        def flush(self):
            return

    class ChunkSocket:
        def __init__(self):
            self.lines = [b"5\r\n", b"0\r\n", b"\r\n"]
            self.body = bytearray(b"hello\r\n")

        def readline(self):
            return self.lines.pop(0) if self.lines else b""

        def read(self, size=-1):
            if size < 0 or size > len(self.body):
                size = len(self.body)
            value = bytes(self.body[:size])
            self.body = self.body[size:]
            return value

        def close(self):
            return

    http = HTTP()
    http._running = True
    collector = Collector()
    body = http.read_chunked(ChunkSocket(), stream_sink=collector)
    if body != b"" or bytes(collector.data) != b"hello":
        raise RuntimeError("HTTP stream sink mixed protocol markers with body")
    if (
        _clean_model_content("<think>hidden</think>Visible answer")
        != "Visible answer"
        or _clean_model_content("Visible answer\n</think>")
        != "Visible answer"
    ):
        raise RuntimeError("Agent exposed hidden-reasoning markup")

    class EmptyThenVisibleHTTP:
        def __init__(self):
            self.requests = []

        def close(self):
            return

        def post(self, _url, **kwargs):
            request_bytes = storage.writes[kwargs["send_file"]]
            self.requests.append(json.loads(bytes(request_bytes).decode("utf-8")))
            sink = kwargs["stream_sink"]
            content = (
                "" if len(self.requests) == 1
                else "Visible answer\n</think>"
            )
            sink.write(
                (
                    "data: "
                    + json.dumps({
                        "choices": [{
                            "delta": {"content": content},
                            "finish_reason": "stop",
                        }]
                    })
                    + "\n\ndata: [DONE]\n\n"
                ).encode("utf-8")
            )
            return OKResponse()

    local_agent = Agent(
        ViewManager(), MODE_CHAT,
        LLM(storage, LOCAL, "qwen/qwen3.5-9b"),
        file_path="picoware/settings/agent-empty-request.json",
    )
    empty_http = EmptyThenVisibleHTTP()
    local_agent.http = empty_http
    empty_result = local_agent.run_payload({
        "message": "Reply visibly",
        "conversation": [],
    })
    if (
        empty_result.get("status") != "completed"
        or empty_result.get("message") != "Visible answer"
        or len(empty_http.requests) != 2
    ):
        raise RuntimeError("Agent blank completion retry mismatch")
    retry_messages = empty_http.requests[1].get("messages", [])
    if not any(
        "previous completion contained no visible answer" in (
            message.get("content", "").lower()
        )
        for message in retry_messages
        if isinstance(message, dict)
    ):
        raise RuntimeError("Agent blank completion retry lacked a visible-answer guard")
    if empty_result.get("conversation") != [
        {"role": "user", "content": "Reply visibly"},
        {"role": "assistant", "content": "Visible answer"},
    ]:
        raise RuntimeError("Agent blank completion polluted persisted conversation")
    _run_agent_request_limit_check(ConfigStorage, empty_http.requests)
    _run_agent_evidence_completion_hardening_check(storage, ViewManager)
    _run_agent_scratch_cleanup_check(ConfigStorage)
    print("[sim-check:ok] Agent Chat Completions MCP compatibility and streaming")


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
        _run_agent_check()
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
    if opts["agent_live_check"]:
        _run_agent_live_check()
        return
    if opts["agent_live_app_check"]:
        _run_agent_live_app_check()
        return
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
