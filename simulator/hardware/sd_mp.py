import os
import sim_runtime

_initialized = False


class fat32_file:
    def __init__(self, path):
        self.path = path
        self.position = 0
        self.is_open = True
        self.last_entry_read = None
        self.attributes = 0
        self.start_cluster = 0
        self.current_cluster = 0
        self.file_size = get_file_size(path)
        self.dir_entry_sector = 0
        self.dir_entry_offset = 0

    def set_position(self, value):
        self.position = value


def _path(path):
    """Map a VFS path to the host SD root directory."""
    return sim_runtime.host_path(path)


def _source_path(path):
    """Map a VFS path to the apps source directory if applicable."""
    return sim_runtime.app_source_path(path)


def _stat(path):
    """Stat a VFS path, trying source path first then host path."""
    source = _source_path(path)
    if source:
        try:
            return os.stat(source), source
        except OSError:
            pass
    host = _path(path)
    return os.stat(host), host


def init():
    """Initialize the simulated SD card filesystem."""
    global _initialized
    _initialized = True
    sim_runtime.mkdir_p(sim_runtime.sd_root)
    return True


def is_initialized():
    """Return True if the SD card has been initialized."""
    return _initialized


def mount():
    """Mount the SD card (alias for init)."""
    return init()


def unmount():
    """Unmount the SD card (no-op in simulator)."""
    return True


def exists(path):
    """Return True if the given VFS path exists."""
    try:
        _stat(path)
        return True
    except OSError:
        return False


def is_directory(path):
    """Return True if the VFS path is a directory."""
    try:
        stat, _ = _stat(path)
        return stat[0] & 0x4000 != 0
    except OSError:
        return False


def create_directory(path):
    """Create a directory at the given VFS path."""
    sim_runtime.mkdir_p(_path(path))
    return True


def list_directory(path=""):
    """List entries in a VFS directory, merging source and host paths."""
    names = []
    seen = {}
    source = _source_path(path)
    if source:
        try:
            for name in os.listdir(source):
                if name not in seen:
                    names.append(name)
                    seen[name] = True
        except OSError:
            pass
    try:
        for name in os.listdir(_path(path)):
            if name not in seen:
                names.append(name)
                seen[name] = True
    except OSError:
        pass
    return names


def read_directory(path=""):
    """Return directory listing with metadata for each entry."""
    out = []
    for name in list_directory(path):
        full = (path.rstrip("/") + "/" + name) if path else name
        size = get_file_size(full)
        out.append({"filename": name, "size": size, "date": "", "time": "", "attributes": 0, "is_directory": is_directory(full)})
    return out


def read(path, index=0, count=0):
    """Read raw bytes from a VFS file at the given offset."""
    source = _source_path(path)
    target = _path(path)
    if source:
        try:
            os.stat(source)
            target = source
        except OSError:
            pass
    with open(target, "rb") as handle:
        if index:
            handle.seek(index)
        data = handle.read(count if count else -1)
    return data


def readinto(path, buffer):
    """Read file contents into a pre-allocated bytearray."""
    data = read(path, 0, len(buffer))
    buffer[: len(data)] = data
    return len(data)


def write(path, data, overwrite=True):
    """Write data to a VFS path, creating parent directories."""
    target = _path(path)
    parent = target.rsplit("/", 1)[0] if "/" in target else "."
    sim_runtime.mkdir_p(parent)
    with open(target, "wb" if overwrite else "ab") as handle:
        handle.write(data)
    return True


def remove(path):
    """Remove a file or directory tree at the VFS path."""
    target = _path(path)
    try:
        if is_directory(path):
            for name in os.listdir(target):
                remove(path.rstrip("/") + "/" + name)
            os.rmdir(target)
        else:
            os.remove(target)
    except OSError:
        pass
    return True


def rename(old_path, new_path):
    """Rename a VFS file or directory."""
    os.rename(_path(old_path), _path(new_path))
    return True


def move(source_path, destination_path):
    """Move a VFS file or directory (alias for rename)."""
    return rename(source_path, destination_path)


def copy(source_path, destination_path, bytes_per_chunk=2048):
    """Copy a file within the VFS."""
    data = read(source_path, 0, 0)
    write(destination_path, data, True)
    return True


def get_file_size(path):
    """Return the size in bytes of a VFS file."""
    try:
        stat, _ = _stat(path)
        return stat[6]
    except OSError:
        return 0


def file_open(path):
    """Open a file on the VFS, creating it if missing."""
    target = _path(path)
    parent = target.rsplit("/", 1)[0] if "/" in target else "."
    sim_runtime.mkdir_p(parent)
    try:
        open(target, "rb").close()
    except OSError:
        open(target, "wb").close()
    return fat32_file(path)


def file_close(file_obj):
    """Close an open VFS file handle."""
    file_obj.is_open = False
    return True


def file_read(file_obj, index=0, count=0):
    """Read bytes from an open VFS file handle."""
    pos = index if index else file_obj.position
    data = read(file_obj.path, pos, count)
    file_obj.position = pos + len(data)
    return data


def file_readinto(file_obj, buffer):
    """Read from an open file into a pre-allocated buffer."""
    data = file_read(file_obj, file_obj.position, len(buffer))
    buffer[: len(data)] = data
    return len(data)


def file_seek(file_obj, position):
    """Seek to a byte position in an open VFS file."""
    file_obj.position = position
    return True


def file_write(file_obj, data):
    """Write data at the current position of an open VFS file."""
    pos = file_obj.position
    target = _path(file_obj.path)
    parent = target.rsplit("/", 1)[0] if "/" in target else "."
    sim_runtime.mkdir_p(parent)
    try:
        handle = open(target, "r+b")
    except OSError:
        handle = open(target, "w+b")
    try:
        handle.seek(pos)
        handle.write(data)
        try:
            handle.flush()
        except Exception:
            pass
    finally:
        handle.close()
    file_obj.position = pos + len(data)
    file_obj.file_size = get_file_size(file_obj.path)
    return True


def file_copy(source_file, destination_path, bytes_per_chunk=2048):
    """Copy an open file to a new VFS path."""
    return copy(source_file.path, destination_path, bytes_per_chunk)


def file_move(source_file, destination_path, bytes_per_chunk=2048):
    """Move an open file to a new VFS path."""
    return move(source_file.path, destination_path)
