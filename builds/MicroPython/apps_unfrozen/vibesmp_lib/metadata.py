# VibesMP ID3 and cover metadata helpers.

# ---- id3.py ----

import time
_id3_cache = {}
_perf_counters = None


def set_perf_counters(counters):
    global _perf_counters
    _perf_counters = counters


def _perf_inc(name):
    if _perf_counters is not None:
        _perf_counters[name] = _perf_counters.get(name, 0) + 1

def clear_cache():
    global _id3_cache
    _id3_cache.clear()


def _extract_cover_chunked(storage, file_obj, img_offset, img_size, cover_path):
    chunk_size = 2048
    mounted_vfs = False
    temp_rel = cover_path + ".tmp"
    temp_vfs = None
    try:
        if cover_path.startswith("/sd/"):
            cover_path = cover_path[4:]
        elif cover_path.startswith("sd/"):
            cover_path = cover_path[3:]
        cover_path = cover_path.lstrip("/")
        temp_rel = cover_path + ".tmp"
        temp_vfs = storage.vfs_prefix.rstrip("/") + "/" + temp_rel.lstrip("/")

        if not storage.vfs_mounted:
            mounted_vfs = storage.mount_vfs()

        with open(temp_vfs, "wb") as out:
            remaining = img_size
            offset = img_offset
            while remaining > 0:
                chunk = storage.file_read(file_obj, offset, min(chunk_size, remaining), False)
                if not chunk:
                    raise OSError("short APIC read")
                out.write(chunk)
                offset += len(chunk)
                remaining -= len(chunk)

        if storage.exists(cover_path):
            storage.remove(cover_path)
        if not storage.rename(temp_rel, cover_path):
            raise OSError("cover rename failed")
        return True
    except Exception:
        if storage.exists(temp_rel):
            storage.remove(temp_rel)
        raise
    finally:
        if mounted_vfs:
            try:
                storage.unmount_vfs()
            except OSError:
                pass


def parse_id3(storage, file_path, extract_cover=False):
    """
    Optimized ID3 parser for RP2350.
    Uses chunked tag scanning to minimize SD bus lockout.
    """
    if not extract_cover and file_path in _id3_cache:
        return _id3_cache[file_path]

    if len(_id3_cache) > 100:
        _id3_cache.clear()

    sd_path = file_path
    if sd_path.startswith("/sd/"): sd_path = sd_path[4:]
    elif sd_path.startswith("sd/"): sd_path = sd_path[3:]

    # Ensure path starts with / for C driver consistency
    if not sd_path.startswith("/"):
        sd_path = "/" + sd_path

    from gc import collect
    res = {"title": "", "artist": "", "album": "", "year": "", "genre": "", "track": "", "cover": False}

    f = None
    try:
        f = storage.file_open(sd_path)
        if not f: return res

        # 1. Header (Fast check)
        header = storage.file_read(f, 0, 10, False)
        if len(header) == 10 and header[:3] == b"ID3":
            version = header[3]
            tag_size = (header[6] << 21) | (header[7] << 14) | (header[8] << 7) | header[9]

            # Scan entire ID3 tag frame by frame
            pos = 0
            while pos < tag_size - 10:
                # Read frame header (10 bytes for v3/v4, 6 bytes for v2)
                h_sz = 6 if version == 2 else 10
                h = storage.file_read(f, 10 + pos, h_sz, False)
                if len(h) < h_sz or h[0] == 0: break # End of frames or EOF

                fid = ""
                fs = 0
                if version == 2:
                    fid = h[0:3].decode('ascii', 'ignore')
                    fs = (h[3] << 16) | (h[4] << 8) | h[5]
                else:
                    fid = h[0:4].decode('ascii', 'ignore')
                    if version == 3:
                        fs = (h[4] << 24) | (h[5] << 16) | (h[6] << 8) | h[7]
                    else: # v2.4 (Synchsafe)
                        fs = (h[4] << 21) | (h[5] << 14) | (h[6] << 7) | h[7]

                if fs <= 0 or fs > tag_size: break

                norm_id = fid
                if version == 2:
                    if fid == "TT2": norm_id = "TIT2"
                    elif fid == "TP1": norm_id = "TPE1"
                    elif fid == "TAL": norm_id = "TALB"
                    elif fid == "TYE": norm_id = "TYER"
                    elif fid == "TCO": norm_id = "TCON"
                    elif fid == "TRK": norm_id = "TRCK"
                    elif fid == "PIC": norm_id = "APIC"

                text_frames = set(["TIT2", "TPE1", "TALB", "TYER", "TCON", "TRCK"])
                if norm_id in text_frames:
                    data = storage.file_read(f, 10 + pos + h_sz, min(fs, 128), False)
                    if data and len(data) > 1:
                        enc = data[0]
                        raw = data[1:]
                        try:
                            if enc == 1 or enc == 2:
                                val = raw.decode('utf-16', 'ignore').strip('\x00').strip()
                            else:
                                val = raw.decode('latin-1', 'ignore').strip('\x00').strip()
                        except (UnicodeError, LookupError):
                            val = ""
                        if norm_id == "TIT2": res["title"] = val
                        elif norm_id == "TPE1": res["artist"] = val
                        elif norm_id == "TALB": res["album"] = val
                        elif norm_id == "TYER": res["year"] = val
                        elif norm_id == "TCON": res["genre"] = val
                        elif norm_id == "TRCK": res["track"] = val

                elif norm_id == "APIC" and extract_cover:
                    if not res["cover"]:
                        apic_hdr = storage.file_read(f, 10 + pos + h_sz, min(fs, 64), False)
                        if apic_hdr:
                            # Find end of mime type (null terminator)
                            null1 = -1
                            for bi in range(len(apic_hdr)):
                                if apic_hdr[bi] == 0:
                                    null1 = bi
                                    break
                            if null1 >= 0:
                                # Skip: encoding(1) + mime + null(1) + picture_type(1) + description + null(1)
                                null2 = -1
                                for bi in range(null1 + 3, len(apic_hdr)):
                                    if apic_hdr[bi] == 0:
                                        null2 = bi
                                        break
                                if null2 >= 0:
                                    data_offset = null2 + 1
                                    img_offset = 10 + pos + h_sz + data_offset
                                    img_size = fs - data_offset
                                    # Some encoders store a non-empty APIC description and
                                    # malformed headers make the conservative offset land on
                                    # that description. Anchor extraction to the real image
                                    # signature so the JPEG decoder does not receive text
                                    # prefix bytes.
                                    probe = storage.file_read(f, img_offset, min(img_size, 256), False)
                                    sig_offset = -1
                                    for si in range(max(0, len(probe) - 2)):
                                        if probe[si] == 0xFF and probe[si + 1] == 0xD8 and probe[si + 2] == 0xFF:
                                            sig_offset = si
                                            break
                                    if sig_offset > 0:
                                        img_offset += sig_offset
                                        img_size -= sig_offset
                                    if img_size > 0 and isinstance(extract_cover, str):
                                        _perf_inc("cover_extract_attempts")
                                        cover_path = extract_cover
                                        try:
                                            if _extract_cover_chunked(storage, f, img_offset, img_size, cover_path):
                                                res["cover"] = extract_cover
                                                _perf_inc("cover_extract_success")
                                                collect()
                                        except Exception as e:
                                            print("[ERROR] parse_id3 cover extract:", e)
                                            _perf_inc("cover_extract_fail")

                pos += h_sz + fs

    except OSError as e:
        print("[ERROR] parse_id3:", e)
    finally:
        if f:
            try: storage.file_close(f)
            except OSError: pass

    if not extract_cover:
        _id3_cache[file_path] = res
    return res

# ---- metadata_engine.py ----

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

def _is_jpeg_file(storage, path):
    """Return True when path points at a JPEG file with a valid SOI marker."""
    if path.startswith("/sd/"):
        path = path[4:]
    elif path.startswith("sd/"):
        path = path[3:]
    path = path.lstrip("/")
    f = None
    try:
        f = storage.file_open("/" + path)
        if not f:
            return False
        data = storage.file_read(f, 0, 3, False)
        return len(data) >= 3 and data[0] == 0xFF and data[1] == 0xD8 and data[2] == 0xFF
    except OSError:
        return False
    finally:
        if f:
            try:
                storage.file_close(f)
            except OSError:
                pass

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
                    if _is_jpeg_file(storage, nc_path):
                        return True
                    try:
                        storage.remove(nc_path)
                    except OSError:
                        pass
            else:
                # No cover info, but maybe the scanner previously failed.
                # If it's not an MP3, we don't expect a cover anyway.
                if not n_path.lower().endswith(".mp3"):
                    return True
        except (OSError, ValueError): pass

    try:
        from vibesmp_lib.metadata import parse_id3
        # ID3 parser handles its own /sd/ normalization for storage
        id3_data = parse_id3(storage, n_path, extract_cover=cover_path)
        if id3_data["title"] or id3_data["artist"] or id3_data["album"] or id3_data["cover"]:
            storage.write(n_meta, json.dumps(id3_data), "w")
        del id3_data; collect()
        return True
    except (OSError, ValueError) as e:
        print(f"[ERROR] extract_metadata {n_path}: {e}")
        return False
