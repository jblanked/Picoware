"""Sprite3D validation, whole-model geometry, and transactional saving."""

from math import cos, sin, isfinite, pi
from struct import unpack_from, pack_into


def load_sprite(storage, path, records=None):
    """Read validated 40-byte triangles and return a native mesh and bounds."""
    from picoware.engine.sprite3d import Sprite3D

    size = storage.size(path)
    if not path.lower().endswith(".sprite3d"):
        raise ValueError("Choose a .sprite3d file")
    if size <= 0 or size % 40:
        raise ValueError("Invalid file size (40 bytes/triangle)")
    count = size // 40
    if count > Sprite3D.MAX_TRIANGLES_PER_SPRITE:
        raise ValueError("Too many triangles: %d (max %d)" % (
            count, Sprite3D.MAX_TRIANGLES_PER_SPRITE))

    mesh = Sprite3D()
    reserve = getattr(mesh, 'reserve_triangles', None)
    if reserve is not None:
        reserve(count)
    low = [float("inf")] * 3
    high = [-float("inf")] * 3
    from .streams import chunks
    reader = chunks(storage, path, size)
    try:
        load = getattr(mesh, 'load_buffer', None)
        if load is not None and records is not None and not records:
            for data in reader:
                records.extend(data)
            low,high = load(records)
            mesh.set_active(True)
            return mesh,low,high
        for data in reader:
            length = len(data)
            if records is not None:
                records.extend(data)
            for index in range(0, length, 40):
                values = unpack_from("<9fHB", data, index)
                if values[10] not in (0, 1):
                    raise ValueError("Invalid wireframe flag")
                for vertex in range(0, 9, 3):
                    for axis in range(3):
                        value = values[vertex + axis]
                        if not isfinite(value) or abs(value) > 1e12:
                            raise ValueError("Invalid vertex coordinate")
                        low[axis] = min(low[axis], value)
                        high[axis] = max(high[axis], value)
                mesh.add_triangle(*values)
        if mesh.triangle_count != count:
            raise MemoryError("Could not load every triangle")
        mesh.set_active(True)
        return mesh, low, high
    except OSError as exc:
        mesh.clear_triangles()
        raise ValueError(str(exc))
    except Exception:
        mesh.clear_triangles()
        raise
    finally:
        reader.close()


def transformed_records(source, kind, amounts, pivot, mask=None, base_vertex=0, result=None):
    """Transform original float32 vertices once; retain triangle metadata."""
    if result is None:
        result = bytearray(source)
    else:
        result[:] = source
    # Most edits rotate one axis. Skip the other axes even in the Python fallback.
    rx, ry, rz = (tuple((cos(v*pi/180), sin(v*pi/180)) if v else None
                       for v in amounts) if kind == "Rotate" else (None, None, None))
    for offset in range(0, len(source), 40):
        first = base_vertex+(offset//40)*3
        if mask is not None and not (mask[first] or mask[first+1] or mask[first+2]):
            continue
        values = unpack_from("<9f", source, offset)
        output = []
        for vertex in range(0, 9, 3):
            if mask is not None and not mask[base_vertex+(offset//40)*3+vertex//3]:
                output.extend(values[vertex:vertex+3])
                continue
            x, y, z = [values[vertex + i] - pivot[i] for i in range(3)]
            if kind == "Move":
                x, y, z = x + amounts[0], y + amounts[1], z + amounts[2]
            elif kind == "Scale":
                x, y, z = x * amounts[0], y * amounts[1], z * amounts[2]
            else:
                if rx is not None:
                    ca, sa = rx
                    y, z = y*ca-z*sa, y*sa+z*ca
                if ry is not None:
                    cb, sb = ry
                    x, z = x*cb+z*sb, -x*sb+z*cb
                if rz is not None:
                    cc, sc = rz
                    x, y = x*cc-y*sc, x*sc+y*cc
            point = (x+pivot[0], y+pivot[1], z+pivot[2])
            if any(not isfinite(v) or abs(v) > 1e12 for v in point):
                raise ValueError("Transform exceeds coordinate range")
            output.extend(point)
        pack_into("<9f", result, offset, *output)
    return result


def record_bounds(records):
    if not records:
        return [-.5,0,-.5],[.5,1,.5]
    low, high = [float("inf")]*3, [-float("inf")]*3
    for offset in range(0, len(records), 40):
        values = unpack_from("<9f", records, offset)
        for v in range(0, 9, 3):
            for i in range(3):
                low[i] = min(low[i], values[v+i])
                high[i] = max(high[i], values[v+i])
    return low, high


def save_sprite(storage, mesh, path):
    """Validate a temporary mesh file before replacing the destination."""
    if not path.lower().endswith(".sprite3d"):
        raise ValueError("Use a .sprite3d filename")
    if storage.is_directory(path):
        raise ValueError("Choose a filename, not a directory")
    parent = path.rsplit("/", 1)[0] or "/"
    if not storage.is_directory(parent):
        raise ValueError("Destination folder does not exist")
    stem = parent.rstrip("/") + "/.sprite3d-save-"
    index = 0
    while storage.exists(stem + str(index) + ".sprite3d") or storage.exists(stem + str(index) + ".bak"):
        index += 1
    temporary = stem + str(index) + ".sprite3d"
    backup = stem + str(index) + ".bak"
    moved = False
    try:
        if not mesh.to_path(temporary):
            raise OSError("Could not write temporary file")
        if storage.size(temporary) != mesh.triangle_count * 40:
            raise OSError("Incomplete save: %d/%d bytes" % (storage.size(temporary), mesh.triangle_count * 40))
        check, _low, _high = load_sprite(storage, temporary)
        check.clear_triangles()
        if storage.exists(path):
            if not storage.rename(path, backup):
                raise OSError("Could not preserve original file")
            moved = True
        if not storage.rename(temporary, path):
            if moved and not storage.rename(backup, path):
                raise OSError("Original retained at " + backup)
            moved = False
            raise OSError("Could not replace destination")
        if moved:
            storage.remove(backup)
    finally:
        if storage.exists(temporary):
            storage.remove(temporary)
