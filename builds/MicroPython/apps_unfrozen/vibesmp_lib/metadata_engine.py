import json
import binascii
from gc import collect

_cover_decoder = None
_cover_decoder_size = None
_perf_counters = None


def set_perf_counters(counters):
    global _perf_counters
    _perf_counters = counters


def _perf_inc(name):
    if _perf_counters is not None:
        _perf_counters[name] = _perf_counters.get(name, 0) + 1

def get_track_hash(path):
    """Generate a consistent 8-char hex hash for a track path."""
    if isinstance(path, str):
        path = path.encode()
    return str(binascii.crc32(path) & 0xFFFFFFFF)

def get_meta_paths(library, path):
    """Return (meta_json_path, cover_jpg_path) for a track."""
    h = get_track_hash(path)
    return library.meta_dir + h + ".json", library.cover_dir + h + ".jpg"

def get_cached_title(storage, library, path):
    """Return ID3 title for path from cached meta JSON, or empty string."""
    try:
        meta_path, _ = get_meta_paths(library, path)
        n = meta_path
        if n.startswith("/sd/"): n = n[4:]
        elif n.startswith("sd/"): n = n[3:]
        if not storage.exists(n): return ""
        data = json.loads(storage.read(n))
        return data.get("title", "") or ""
    except (OSError, ValueError):
        return ""

def draw_cover(draw, cover_path, x, y, size=68):
    """Memory-efficient cover drawing with automatic scaling and zero persistence."""
    if not cover_path: return False

    # Normalize path for VFS
    sd_path = cover_path
    if sd_path.startswith("/sd/"): sd_path = sd_path[4:]
    elif sd_path.startswith("sd/"): sd_path = sd_path[3:]
    sd_path = sd_path.lstrip("/")

    try:
        from picoware.gui.jpeg import JPEG
        global _cover_decoder, _cover_decoder_size

        _perf_inc("cover_draw_attempts")
        res = False

        try:
            if _cover_decoder is None or _cover_decoder_size != size:
                _cover_decoder = JPEG(screen_width=size, screen_height=size)
                _cover_decoder_size = size
            res = _cover_decoder.draw(x, y, sd_path)
        except (ValueError, OSError, AttributeError) as e:
            print(f"[ERROR] draw_cover shared decoder exception: {e}")
            _cover_decoder = None
            _cover_decoder_size = None

        if not res:
            _perf_inc("cover_decoder_fallbacks")
            decoder = JPEG(screen_width=size, screen_height=size)
            try:
                res = decoder.draw(x, y, sd_path)
            finally:
                del decoder

        if res:
            _perf_inc("cover_draw_success")
        else:
            _perf_inc("cover_draw_fail")
        return res

    except (ImportError, ValueError, OSError) as e:
        print(f"[ERROR] draw_cover native exception: {e}")
        _perf_inc("cover_draw_fail")
        from gc import collect
        collect()
        return False

def cleanup_engine():
    global _cover_decoder, _cover_decoder_size
    _cover_decoder = None
    _cover_decoder_size = None
    from gc import collect
    collect()

def extract_metadata(storage, path, library):
    """Extract and save metadata/cover for a new track."""
    meta_path, cover_path = get_meta_paths(library, path)

    # Normalize paths for Storage API (no /sd/)
    n_meta = meta_path
    if n_meta.startswith("/sd/"): n_meta = n_meta[4:]
    elif n_meta.startswith("sd/"): n_meta = n_meta[3:]

    n_path = path
    if n_path.startswith("/sd/"): n_path = n_path[4:]
    elif n_path.startswith("sd/"): n_path = n_path[3:]

    # If meta exists, check if it has valid cover info.
    if storage.exists(n_meta):
        try:
            data = json.loads(storage.read(n_meta))
            # If we have a cover, verify the file still exists
            c_path = data.get("cover")
            if c_path:
                nc_path = c_path
                if nc_path.startswith("/sd/"): nc_path = nc_path[4:]
                elif nc_path.startswith("sd/"): nc_path = nc_path[3:]

                if storage.exists(nc_path):
                    return True
            else:
                # No cover info, but maybe the scanner previously failed.
                # If it's not an MP3, we don't expect a cover anyway.
                if not n_path.lower().endswith(".mp3"):
                    return True
        except (OSError, ValueError): pass

    try:
        from vibesmp_lib.id3 import parse_id3
        # ID3 parser handles its own /sd/ normalization for storage
        id3_data = parse_id3(storage, n_path, extract_cover=cover_path)
        if id3_data["title"] or id3_data["artist"] or id3_data["album"] or id3_data["cover"]:
            storage.write(n_meta, json.dumps(id3_data), "w")
        del id3_data; collect()
        return True
    except (OSError, ValueError) as e:
        print(f"[ERROR] extract_metadata {n_path}: {e}")
        return False
