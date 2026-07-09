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
