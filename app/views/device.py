"""Shared mpremote helpers for interacting with a Picoware device."""

import contextlib
import io
import os
import shutil
import string
import sys
import threading

from mpremote import main as mpremote_main
from mpremote.commands import CommandError, do_connect, do_disconnect
from mpremote.transport import TransportError, stdout_write_bytes

_LOCK = threading.Lock()
_ACTIVE_STATE = [None]

BOOTLOADER_VOLUMES = ("rpi-rp2", "rp2350", "rp2", "rp2040", "boot", "bootfs")


class _DeviceArgs:
    """Minimal argparse-like namespace for ``do_connect``."""

    def __init__(self, device: str):
        self.device = [device]


class _OutputCapture:
    """Captures both str and bytes output written to a stream."""

    def __init__(self):
        self.buffer = io.BytesIO()
        self.encoding = "utf-8"

    def write(self, data) -> int:
        if isinstance(data, bytes):
            return self.buffer.write(data)
        return self.buffer.write(data.encode(self.encoding, errors="replace"))

    def flush(self) -> None:
        pass

    def getvalue(self) -> str:
        return self.buffer.getvalue().decode("utf-8", errors="replace")


def run_mpremote(args: list[str]) -> tuple[int, str]:
    """Run an mpremote command chain; returns (exit_code, output)."""
    with _LOCK:
        old_argv = sys.argv
        sys.argv = ["mpremote", *args]
        cap = _OutputCapture()
        code = 0
        try:
            with contextlib.redirect_stdout(cap), contextlib.redirect_stderr(cap):
                code = mpremote_main.main()
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
        finally:
            sys.argv = old_argv
        return code, cap.getvalue()


def run_script(
    code: str,
    device: str = "auto",
    on_output=None,
    stop_event: threading.Event | None = None,
) -> int:
    """Execute *code* on the device, streaming output to *on_output*.

    Returns the exit code (0 for success). Pass *stop_event* and call
    :func:`stop_current` from another thread to interrupt a long run.
    """
    with _LOCK:
        state = mpremote_main.State()
        _ACTIVE_STATE[0] = state
        try:
            if device and device != "auto":
                do_connect(state, _DeviceArgs(device))
            else:
                state.ensure_connected()
            state.ensure_raw_repl()
            state.transport.exec_raw_no_follow(code.encode())
            if stop_event is not None and stop_event.is_set():
                return 1
            if on_output is not None:
                consumer = lambda b: on_output(b.decode("utf-8", errors="replace"))
            else:
                consumer = stdout_write_bytes
            _, ret_err = state.transport.follow(timeout=None, data_consumer=consumer)
            if ret_err:
                if on_output is not None:
                    on_output(ret_err.decode("utf-8", errors="replace"))
                return 1
            return 0
        except (TransportError, CommandError) as er:
            if on_output is not None:
                on_output(f"mpremote: {er}\n")
            return 1
        finally:
            _ACTIVE_STATE[0] = None
            try:
                do_disconnect(state)
            except Exception:
                pass


def stop_current() -> None:
    """Interrupt the running device session, if any."""
    state = _ACTIVE_STATE[0]
    if state is not None and state.transport is not None:
        try:
            state.transport.close()
        except Exception:
            pass


def save_to_device(
    local_path: str, remote_path: str, device: str = "auto"
) -> tuple[int, str]:
    """Copy a local file to the device filesystem."""
    return run_mpremote(["connect", device, "fs", "cp", local_path, ":" + remote_path])


def list_files(device: str = "auto") -> tuple[int, str]:
    """List files on the device filesystem."""
    return run_mpremote(["connect", device, "fs", "ls"])


def enter_bootloader(device: str = "auto") -> tuple[int, str]:
    """Put a connected device into bootloader mode via mpremote."""
    return run_mpremote(["connect", device, "bootloader"])


def list_ports() -> list[str]:
    """Return serial port device paths."""
    import serial.tools.list_ports

    return [p.device for p in serial.tools.list_ports.comports()]


def find_bootloader_drive() -> str | None:
    """Return the mount path of a device in bootloader mode, if mounted."""
    if sys.platform == "win32":
        return _find_bootloader_drive_windows()
    if sys.platform == "darwin":
        roots = ["/Volumes"]
    else:
        user = os.environ.get("USER", "")
        roots = ["/media/" + user, "/run/media/" + user, "/mnt"]
    for root in roots:
        if not os.path.isdir(root):
            continue
        try:
            names = os.listdir(root)
        except OSError:
            continue
        for name in names:
            if _is_bootloader_name(name):
                return os.path.join(root, name)
    return None


def _is_bootloader_name(name: str) -> bool:
    low = name.lower()
    return low in BOOTLOADER_VOLUMES or low.startswith("rp")


def _find_bootloader_drive_windows() -> str | None:
    import ctypes

    for letter in string.ascii_uppercase:
        root = letter + ":\\"
        if not os.path.exists(root):
            continue
        label = ctypes.create_unicode_buffer(512)
        if ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root), label, 512, None, None, None, None, 0
        ):
            if _is_bootloader_name(label.value):
                return root
    return None


def flash_uf2(uf2_path: str, drive: str) -> bool:
    """Copy *uf2_path* to the bootloader drive. Returns True on success."""
    try:
        dest = os.path.join(drive, os.path.basename(uf2_path))
        shutil.copyfile(uf2_path, dest)
        return True
    except OSError:
        return False
