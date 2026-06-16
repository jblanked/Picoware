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
    return sim_runtime.host_path(path)


def _source_path(path):
    return sim_runtime.app_source_path(path)


def _stat(path):
    source = _source_path(path)
    if source:
        try:
            return os.stat(source), source
        except OSError:
            pass
    host = _path(path)
    return os.stat(host), host


def init():
    global _initialized
    _initialized = True
    sim_runtime.mkdir_p(sim_runtime.sd_root)
    return True


def is_initialized():
    return _initialized


def mount():
    return init()


def unmount():
    return True


def exists(path):
    try:
        _stat(path)
        return True
    except OSError:
        return False


def is_directory(path):
    try:
        stat, _ = _stat(path)
        return stat[0] & 0x4000 != 0
    except OSError:
        return False


def create_directory(path):
    sim_runtime.mkdir_p(_path(path))
    return True


def list_directory(path=""):
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
    out = []
    for name in list_directory(path):
        full = (path.rstrip("/") + "/" + name) if path else name
        size = get_file_size(full)
        out.append({"filename": name, "size": size, "date": "", "time": "", "attributes": 0, "is_directory": is_directory(full)})
    return out


def read(path, index=0, count=0):
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
    data = read(path, 0, len(buffer))
    buffer[: len(data)] = data
    return len(data)


def write(path, data, overwrite=True):
    target = _path(path)
    parent = target.rsplit("/", 1)[0] if "/" in target else "."
    sim_runtime.mkdir_p(parent)
    with open(target, "wb" if overwrite else "ab") as handle:
        handle.write(data)
    return True


def remove(path):
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
    os.rename(_path(old_path), _path(new_path))
    return True


def move(source_path, destination_path):
    return rename(source_path, destination_path)


def copy(source_path, destination_path, bytes_per_chunk=2048):
    data = read(source_path, 0, 0)
    write(destination_path, data, True)
    return True


def get_file_size(path):
    try:
        stat, _ = _stat(path)
        return stat[6]
    except OSError:
        return 0


def file_open(path):
    target = _path(path)
    parent = target.rsplit("/", 1)[0] if "/" in target else "."
    sim_runtime.mkdir_p(parent)
    try:
        open(target, "rb").close()
    except OSError:
        open(target, "wb").close()
    return fat32_file(path)


def file_close(file_obj):
    file_obj.is_open = False
    return True


def file_read(file_obj, index=0, count=0):
    pos = index if index else file_obj.position
    data = read(file_obj.path, pos, count)
    file_obj.position = pos + len(data)
    return data


def file_readinto(file_obj, buffer):
    data = file_read(file_obj, file_obj.position, len(buffer))
    buffer[: len(data)] = data
    return len(data)


def file_seek(file_obj, position):
    file_obj.position = position
    return True


def file_write(file_obj, data):
    current = b""
    if exists(file_obj.path):
        current = read(file_obj.path, 0, 0)
    pos = file_obj.position
    merged = current[:pos] + data
    if pos + len(data) < len(current):
        merged += current[pos + len(data) :]
    write(file_obj.path, merged, True)
    file_obj.position = pos + len(data)
    return True


def file_copy(source_file, destination_path, bytes_per_chunk=2048):
    return copy(source_file.path, destination_path, bytes_per_chunk)


def file_move(source_file, destination_path, bytes_per_chunk=2048):
    return move(source_file.path, destination_path)
