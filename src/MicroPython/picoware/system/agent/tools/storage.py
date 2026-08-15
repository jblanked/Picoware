"""Validated, recoverable SD-card tools for the Picoware Agent."""
from picoware.system.agent.tools.tool import Tool, Parameters, Property

MAX_PATH_BYTES = 259
MAX_TOOL_DATA_BYTES = 65536
IO_CHUNK_BYTES = 2048
_INVALID_NAME_CHARS = '<>:"|?*'


def _result(ok: bool, path: str = "", error: str = "", message: str = "", **values):
    value = {"ok": bool(ok)}
    if path:
        value["path"] = path
    if error:
        value["error"] = error
    if message:
        value["message"] = message
    value.update(values)
    return value


def _normalize_path(path: str) -> str:
    """Return one FAT-relative path without limiting usable SD folders."""
    if not isinstance(path, str):
        raise ValueError("path must be a string")
    path = path.strip().replace("\\", "/")
    for prefix in ("/sdcard/", "/sd/", "sdcard/", "sd/"):
        if path.startswith(prefix):
            path = path[len(prefix):]
            break
    path = path.lstrip("/")
    if not path:
        raise ValueError("path is empty")

    parts = []
    for part in path.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if not parts:
                raise ValueError("path escapes the SD root")
            parts.pop()
            continue
        if any(ord(char) < 32 or char in _INVALID_NAME_CHARS for char in part):
            raise ValueError("path contains FAT-incompatible characters")
        if len(part.encode("utf-8")) > 255:
            raise ValueError("path component is longer than 255 bytes")
        parts.append(part)

    normalized = "/".join(parts)
    if not normalized or len(normalized.encode("utf-8")) > MAX_PATH_BYTES:
        raise ValueError("path is empty or longer than the FAT32 limit")
    return normalized


def _normalize_directory_path(path: str) -> str:
    """Normalize a directory path while allowing the SD-card root."""
    if not isinstance(path, str):
        raise ValueError("path must be a string")
    value = path.strip().replace("\\", "/")
    if value in ("", "/", ".", "/sd", "/sd/", "/sdcard", "/sdcard/"):
        return ""
    return _normalize_path(value)


def _ensure_parents(storage, path: str):
    parts = path.split("/")[:-1]
    current = ""
    for part in parts:
        current = part if not current else current + "/" + part
        if storage.exists(current):
            if not storage.is_directory(current):
                raise OSError("parent path is not a directory: " + current)
            continue
        if not storage.mkdir(current):
            raise OSError("could not create parent directory: " + current)


def _decode_data(data, mode: str, encoding: str):
    if not isinstance(data, str):
        raise ValueError("data must be a string")
    if mode not in ("w", "a", "wb", "ab"):
        raise ValueError("mode must be w, a, wb, or ab")
    if encoding not in ("utf-8", "base64"):
        raise ValueError("encoding must be utf-8 or base64")
    if encoding == "base64":
        try:
            from ubinascii import a2b_base64
            value = a2b_base64(data)
        except Exception as exc:
            raise ValueError("data is not valid base64") from exc
    else:
        value = data.encode("utf-8")
    if len(value) > MAX_TOOL_DATA_BYTES:
        raise ValueError("data exceeds the 65536-byte tool limit")
    return value


def _checksum_file(storage, path: str) -> tuple[int, int]:
    offset = 0
    checksum = 2166136261
    while True:
        chunk = storage.read_chunked(path, offset, IO_CHUNK_BYTES)
        if not chunk:
            break
        for value in chunk:
            checksum ^= value
            checksum = (checksum * 16777619) & 0xFFFFFFFF
        offset += len(chunk)
    return offset, checksum


def _write_chunks(storage, path: str, data, append: bool = False):
    file_obj = storage.file_open(path)
    if file_obj is None:
        raise OSError("could not open temporary file")
    try:
        if append and not storage.file_seek(file_obj, storage.size(path)):
            raise OSError("could not seek to append position")
        offset = 0
        while offset < len(data):
            chunk = data[offset : offset + IO_CHUNK_BYTES]
            if not storage.file_write(file_obj, chunk, "wb"):
                raise OSError("could not write file data")
            offset += len(chunk)
    finally:
        storage.file_close(file_obj)


def _install_temp_file(storage, path: str, temp_path: str):
    """Install a verified temporary file and retain the old file as backup."""
    backup_path = path + ".agent-bak"
    had_original = storage.exists(path)
    if storage.exists(backup_path) and not storage.remove(backup_path):
        raise OSError("could not remove stale backup")
    if had_original and not storage.rename(path, backup_path):
        raise OSError("could not preserve existing file")
    if not storage.rename(temp_path, path):
        if had_original:
            storage.rename(backup_path, path)
        raise OSError("could not install temporary file")
    return had_original, backup_path


def _restore_backup(storage, path: str, backup_path: str, had_original: bool):
    """Remove a failed replacement and restore the previous file if present."""
    storage.remove(path)
    if had_original and not storage.rename(backup_path, path):
        raise OSError("read-back failed and the original file could not be restored")


def storage_listdir(view_manager, dir_path):
    try:
        path = _normalize_directory_path(dir_path)
        storage = view_manager.storage
        if path and not storage.exists(path):
            return _result(False, path, "not_found", "directory does not exist")
        if path and not storage.is_directory(path):
            return _result(False, path, "not_directory", "path is not a directory")
        return _result(True, path or "/", entries=storage.listdir(path))
    except Exception as exc:
        return _result(False, error="invalid_path", message=str(exc))


def _human_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    unit = 0
    remainder = 0
    while value >= 1024 and unit < len(units) - 1:
        remainder = value % 1024
        value //= 1024
        unit += 1
    if unit and value < 10:
        return "%d.%d %s" % (value, (remainder * 10) // 1024, units[unit])
    return "%d %s" % (value, units[unit])


def storage_get_info(view_manager):
    """Return authoritative SD-card capacity counters from the storage driver."""
    try:
        storage = view_manager.storage
        free = max(0, int(storage.free_space))
        total = max(0, int(storage.total_space))
        used = max(0, total - free)
        if total <= 0:
            return _result(
                False, "/", "capacity_unavailable", "SD capacity is unavailable"
            )
        return _result(
            True,
            "/",
            free_bytes=free,
            used_bytes=used,
            total_bytes=total,
            free=_human_bytes(free),
            used=_human_bytes(used),
            total=_human_bytes(total),
        )
    except Exception as exc:
        return _result(False, "/", "capacity_failed", str(exc))


def storage_mkdir(view_manager, dir_path):
    try:
        path = _normalize_path(dir_path)
        storage = view_manager.storage
        _ensure_parents(storage, path)
        if storage.exists(path):
            if storage.is_directory(path):
                return _result(True, path, created=False)
            return _result(False, path, "path_exists", "path exists as a file")
        if not storage.mkdir(path):
            return _result(False, path, "mkdir_failed", "could not create directory")
        return _result(True, path, created=True)
    except ValueError as exc:
        return _result(False, error="invalid_path", message=str(exc))
    except Exception as exc:
        return _result(False, error="mkdir_failed", message=str(exc))


def storage_read(view_manager, file_path, mode: str = "r", index: int = 0, count: int = 0):
    try:
        path = _normalize_path(file_path)
        if mode not in ("r", "rb"):
            raise ValueError("mode must be r or rb")
        if not isinstance(index, int) or not isinstance(count, int) or index < 0 or count < 0:
            raise ValueError("index and count must be non-negative integers")
        storage = view_manager.storage
        if not storage.exists(path) or storage.is_directory(path):
            return _result(False, path, "not_found", "file does not exist")
        size = storage.size(path)
        requested = count if count else size - index
        if requested > MAX_TOOL_DATA_BYTES:
            return _result(
                False,
                path,
                "read_too_large",
                "request a partial read of at most 65536 bytes",
                size=size,
            )
        data = storage.read(path, mode, index, count)
        if mode == "rb":
            from ubinascii import b2a_base64
            encoded = b2a_base64(data).decode("ascii").strip()
            return _result(True, path, data=encoded, encoding="base64", size=len(data))
        return _result(True, path, data=data, encoding="utf-8", size=len(data.encode("utf-8")))
    except ValueError as exc:
        return _result(False, error="invalid_request", message=str(exc))
    except Exception as exc:
        return _result(False, error="read_failed", message=str(exc))


def storage_remove(view_manager, file_path):
    try:
        path = _normalize_path(file_path)
        storage = view_manager.storage
        if not storage.exists(path):
            return _result(True, path, removed=False)
        if not storage.remove(path):
            return _result(False, path, "remove_failed", "could not remove path")
        return _result(True, path, removed=True)
    except ValueError as exc:
        return _result(False, error="invalid_path", message=str(exc))
    except Exception as exc:
        return _result(False, error="remove_failed", message=str(exc))


def storage_write(view_manager, file_path, data, mode: str = "w", encoding: str = "utf-8"):
    temp_path = ""
    try:
        path = _normalize_path(file_path)
        if len((path + ".agent-bak").encode("utf-8")) > MAX_PATH_BYTES:
            raise ValueError("path is too long for recoverable writes")
        value = _decode_data(data, mode, encoding)
        storage = view_manager.storage
        _ensure_parents(storage, path)
        temp_path = path + ".agent-tmp"
        if storage.exists(temp_path) and not storage.remove(temp_path):
            raise OSError("could not remove stale temporary file")

        append = mode in ("a", "ab")
        if append and storage.exists(path):
            if not storage.copy(path, temp_path, IO_CHUNK_BYTES):
                raise OSError("could not copy existing file for append")
            _write_chunks(storage, temp_path, value, append=True)
        else:
            _write_chunks(storage, temp_path, value)

        expected_size, expected_checksum = _checksum_file(storage, temp_path)
        had_original, backup_path = _install_temp_file(storage, path, temp_path)
        actual_size, actual_checksum = _checksum_file(storage, path)
        if actual_size != expected_size or actual_checksum != expected_checksum:
            _restore_backup(storage, path, backup_path, had_original)
            raise OSError("read-back verification failed")
        backup_removed = True
        if had_original:
            backup_removed = storage.remove(backup_path)
        return _result(
            True,
            path,
            bytes_written=len(value),
            size=actual_size,
            checksum="%08x" % actual_checksum,
            mode=mode,
            backup_removed=backup_removed,
        )
    except ValueError as exc:
        return _result(False, error="invalid_request", message=str(exc))
    except Exception as exc:
        if temp_path:
            try:
                view_manager.storage.remove(temp_path)
            except Exception:
                pass
        return _result(False, error="write_failed", message=str(exc))


TOOL_STORAGE_LISTDIR = Tool(
    "storage_listdir",
    "List an SD-card directory and return a structured result.",
    Parameters([Property("dir_path", "string", "Directory path on the SD card.", True)]),
)
TOOL_STORAGE_GET_INFO = Tool(
    "storage_get_info",
    "Return authoritative free, used, and total SD-card space in bytes and human-readable units.",
    Parameters([]),
)
TOOL_STORAGE_MKDIR = Tool(
    "storage_mkdir",
    "Recursively create an SD-card directory and return a structured result.",
    Parameters([Property("dir_path", "string", "Directory path on the SD card.", True)]),
)
TOOL_STORAGE_READ = Tool(
    "storage_read",
    "Read an SD-card file. Binary data is returned as base64.",
    Parameters([
        Property("file_path", "string", "File path on the SD card.", True),
        Property("mode", "string", "Read mode.", enum=["r", "rb"]),
        Property("index", "integer", "Starting byte offset."),
        Property("count", "integer", "Bytes to read; zero means the remaining file."),
    ]),
)
TOOL_STORAGE_REMOVE = Tool(
    "storage_remove",
    "Remove any requested SD-card file or directory and return a structured result.",
    Parameters([Property("file_path", "string", "File or directory path on the SD card.", True)]),
)
TOOL_STORAGE_WRITE = Tool(
    "storage_write",
    "Reliably write or append an SD-card file, creating parents and verifying the result.",
    Parameters([
        Property("file_path", "string", "File path on the SD card.", True),
        Property("data", "string", "UTF-8 text or base64-encoded binary data.", True),
        Property("mode", "string", "Write or append mode.", enum=["w", "a", "wb", "ab"]),
        Property("encoding", "string", "Encoding of data.", enum=["utf-8", "base64"]),
    ]),
)
