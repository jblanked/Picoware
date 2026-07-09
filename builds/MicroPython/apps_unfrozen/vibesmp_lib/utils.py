import os

# Dynamic path resolution to avoid hardcoding /sd/...
_base_path = ""
try:
    _f = __file__
    if _f.startswith("/"):
        if "/" in _f:
            _base_path = _f.rsplit("/", 1)[0] + "/"
        else:
            _base_path = "/"
    else:
        _cwd = os.getcwd()
        if not _cwd.endswith("/"): _cwd += "/"
        if _f.startswith("./"): _f = _f[2:]
        if "/" in _f:
            _base_path = _cwd + _f.rsplit("/", 1)[0] + "/"
        else:
            _base_path = _cwd
except (NameError, AttributeError, OSError):
    # Fallback to standard path if __file__ resolution fails
    _base_path = "picoware/apps/vibesmp_lib/"

# Ensure _base_path doesn't have /sd/ for Storage API compatibility
if _base_path.startswith("/sd/"):
    _base_path = _base_path[4:]
elif _base_path.startswith("sd/"):
    _base_path = _base_path[3:]

def get_path(subpath):
    """Resolve an absolute path within the app package."""
    path = _base_path + subpath
    # Final safety check: remove leading / for Storage API
    if path.startswith("/"):
        path = path[1:]
    return path

def format_time(seconds):
    """Format seconds into MM:SS string."""
    seconds = int(seconds)
    return f"{seconds // 60:02}:{seconds % 60:02}"

def get_filename(path):
    """Get just the filename or folder name from a full path."""
    if not path:
        return ""
    p = path.rstrip("/")
    res = p.split("/")[-1]
    if res.lower().endswith(".mp3"):
        res = res[:-4]
    return res

def get_parent_path(path):
    """Get parent directory path with trailing slash."""
    if not path or path in ("/", "/sd/"):
        return "/sd/"
    parts = path.strip("/").split("/")
    if len(parts) <= 1:
        return "/sd/"
    return "/" + "/".join(parts[:-1]) + "/"

def mkdir_p(storage, path):
    """Create directory and its parents if they don't exist."""
    if not path or path == "/":
        return True

    clean_path = path.replace("\\", "/").strip("/")
    while "//" in clean_path:
        clean_path = clean_path.replace("//", "/")

    if not clean_path:
        return True

    if storage.is_directory(clean_path):
        return True

    parts = clean_path.split("/")
    for i in range(len(parts)):
        curr = "/".join(parts[:i+1])
        if not storage.is_directory(curr):
            if not storage.mkdir(curr):
                return False
    return True
