import os
import sim_runtime

_last_flash = None


def _resolve(path):
    """Map a UF2 path to its host filesystem location."""
    if path is None:
        return None
    text = str(path)
    if text.startswith("/") and sim_runtime.sd_root not in text:
        return text
    if text.startswith(sim_runtime.sd_root):
        return text
    return sim_runtime.host_path(text)


def _write_status(source, ok, message):
    """Write the last flash status to the simulated SD card."""
    global _last_flash
    _last_flash = {"source": source, "ok": ok, "message": message}
    status_dir = sim_runtime.sd_root + "/picoware/uf2loader"
    sim_runtime.mkdir_p(status_dir)
    with open(status_dir + "/last_flash.txt", "w") as handle:
        handle.write("source=" + str(source) + "\n")
        handle.write("ok=" + ("true" if ok else "false") + "\n")
        handle.write("message=" + str(message) + "\n")


def flash_uf2(filename):
    """Simulate flashing a UF2 file. Returns True on success."""
    source = _resolve(filename)
    if not source:
        _write_status(filename, False, "missing filename")
        raise OSError("missing UF2 filename")
    try:
        size = os.stat(source)[6]
    except OSError as exc:
        _write_status(filename, False, "file not found")
        raise exc
    if not str(source).lower().endswith(".uf2"):
        _write_status(filename, False, "not a UF2 file")
        raise ValueError("not a UF2 file: " + str(filename))
    _write_status(filename, True, "simulated flash, " + str(size) + " bytes")
    print("[sim:uf2] would flash " + str(filename) + " (" + str(size) + " bytes)")
    return True


def last_flash():
    """Return the result of the most recent flash operation."""
    return _last_flash


class UF2Loader:
    def __init__(self):
        pass

    def load(self, filename):
        return flash_uf2(filename)

    def flash(self, filename):
        return flash_uf2(filename)

    def reboot(self):
        print("[sim:uf2] reboot requested")
        return True
