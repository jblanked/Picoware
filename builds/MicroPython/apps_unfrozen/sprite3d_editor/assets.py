"""Sprite3D validation, whole-model geometry, and transactional saving."""

from math import cos, sin, isfinite, pi
from struct import unpack_from, pack_into, pack


def record_stride(storage,path,size):
    """Recognize the former native Triangle3D layout without changing the file."""
    if size>0 and size%52==0:
        from .streams import chunks
        reader=chunks(storage,path,size,1040)
        try:
            legacy=True
            for data in reader:
                for offset in range(0,len(data),52):
                    # Old records contain visible, cached depth, initialized,
                    # color, wireframe at 36,40,44,46,48 (with C++ padding).
                    if (data[offset+36] not in (0,1) or data[offset+44]!=1
                            or data[offset+48] not in (0,1)
                            or not isfinite(unpack_from('<f',data,offset+40)[0])
                            or any(not isfinite(v) or abs(v)>1e12
                                   for v in unpack_from('<9f',data,offset))):
                        legacy=False;break
                if not legacy:break
            if legacy:return 52
        finally:reader.close()
    if size<=0 or size%40:
        raise ValueError('Invalid Sprite3D records (expected 40-byte or legacy 52-byte triangles)')
    return 40


def legacy_chunks(storage,path,size):
    from .streams import chunks
    reader=chunks(storage,path,size,1040)
    try:
        for data in reader:
            result=bytearray(len(data)//52*40)
            for index,offset in enumerate(range(0,len(data),52)):
                pack_into('<9fHBB',result,index*40,*unpack_from('<9f',data,offset),
                          unpack_from('<H',data,offset+46)[0],data[offset+48],0)
            yield result
    finally:reader.close()


def load_sprite(storage, path, records=None):
    """Read validated 40-byte triangles and return a native mesh and bounds."""
    from picoware.engine.sprite3d import Sprite3D

    if storage.exists(path+'.mesh-export-journal') or storage.exists(path+'.mesh-export-ready'):
        from .export_transaction import recover
        recover(storage,path,'mesh-export')
    size = storage.size(path)
    if not path.lower().endswith((".sprite3d", ".bin")):
        raise ValueError("Choose a .bin or .sprite3d file")
    stride=record_stride(storage,path,size)
    count = size // stride
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
    reader = chunks(storage,path,size) if stride==40 else legacy_chunks(storage,path,size)
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


def mesh_export_signature(storage,mesh,path,records=None):
    """Verify every serialized field against the source, in eight-triangle chunks."""
    from binascii import crc32
    from .streams import chunks
    size=mesh.triangle_count*40
    if storage.size(path)!=size:raise OSError('Incomplete staged mesh')
    if records is not None and len(records)!=size:raise ValueError('Mesh and source records disagree')
    reader=chunks(storage,path,size,320);position=0;crc=0
    try:
        for block in reader:
            for offset in range(0,len(block),40):
                if records is not None:expected=records[position:position+39]
                else:
                    triangle=mesh.get_triangle(position//40)
                    expected=pack('<9fHB',triangle.x1,triangle.y1,triangle.z1,
                        triangle.x2,triangle.y2,triangle.z2,triangle.x3,triangle.y3,triangle.z3,
                        triangle.color,int(triangle.wireframe))
                    del triangle
                # The final byte is native struct padding, not a serialized field.
                if block[offset:offset+39]!=expected:raise OSError('Staged mesh differs from source geometry')
                position+=40
            crc=crc32(block,crc)
            if records is None:
                from gc import collect
                collect()
    finally:reader.close()
    return size,crc


def save_sprite(storage, mesh, path, records=None):
    """Validate a temporary mesh file before replacing the destination."""
    if not path.lower().endswith((".sprite3d", ".bin")):
        raise ValueError("Use a .bin or .sprite3d filename")
    if storage.is_directory(path):
        raise ValueError("Choose a filename, not a directory")
    parent = path.rsplit("/", 1)[0] or "/"
    if not storage.is_directory(parent):
        raise ValueError("Destination folder does not exist")
    from .export_transaction import begin,commit,recover
    temporary,state=begin(storage,path,'mesh-export')
    try:
        if not mesh.to_path(temporary):
            raise OSError("Could not write temporary file")
        if storage.size(temporary) != mesh.triangle_count * 40:
            raise OSError("Incomplete save: %d/%d bytes" % (storage.size(temporary), mesh.triangle_count * 40))
        signature=mesh_export_signature(storage,mesh,temporary,records)
        check, _low, _high = load_sprite(storage, temporary)
        check.clear_triangles()
        commit(storage,path,'mesh-export',state,signature)
    finally:recover(storage,path,'mesh-export')
