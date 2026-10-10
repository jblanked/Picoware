"""Reuse native triangle storage, with packed records for edit rollback."""

from array import array
from gc import collect
from math import isfinite
from struct import unpack_from
from picoware.engine.sprite3d import Sprite3D


class MeshBuffer:
    def __init__(self, mesh=None, records=b""):
        self.mesh = mesh
        self.records = records

    def prepare(self, records, validate=True):
        return MeshUpdate(self, records, validate)


class MeshUpdate:
    """Prepare replacements before writing to any mesh already on screen."""

    def __init__(self, buffer, records, validate=True, deferred=False):
        count = len(records)//40
        if len(records)%40 or count > Sprite3D.MAX_TRIANGLES_PER_SPRITE:
            raise ValueError("Triangle limit exceeded")
        self.buffer = buffer
        self.records = records
        self.mesh = buffer.mesh
        self.changed = array('H')
        self.applied = 0
        self.created = False
        self.reuse = (self.mesh is not None and self.mesh.triangle_count == count
                      and len(buffer.records) == len(records)
                      and hasattr(self.mesh, 'update_triangle'))
        if not deferred:
            from .topology import consume
            consume(self.prepare_steps(validate))

    def prepare_steps(self,validate=True):
        buffer,records=self.buffer,self.records
        # Validate before changing live geometry. Packed snapshots avoid keeping
        # one Python tuple and nine float objects per triangle on embedded heaps.
        if self.reuse and buffer.records == records:
            return
        buffer,records=self.buffer,self.records
        count=len(records)//40
        before = memoryview(buffer.records)
        after = memoryview(records)
        for offset in range(0, len(records), 40):
            if validate:
                values = unpack_from('<9fHB', records, offset)
                if values[10] not in (0, 1) or any(
                        not isfinite(v) or abs(v) > 1e12 for v in values[:9]):
                    raise ValueError("Invalid triangle record")
            if offset%320==0:yield None
            if self.reuse and before[offset:offset+39] != after[offset:offset+39]:
                self.changed.append(offset//40)
        if not self.reuse:
            # View preparation just released sort/projection temporaries.
            # Reclaim them before requesting a contiguous native allocation.
            from gc import collect,mem_free
            if mem_free()<262144:collect()
            self.mesh = Sprite3D()
            self.created = True
            try:
                reserve = getattr(self.mesh, 'reserve_triangles', None)
                if reserve is not None:reserve(count)
                for offset in range(0, len(records), 40):
                    if offset%320==0:yield None
                    self.mesh.add_triangle(*unpack_from('<9fHB', records, offset))
                if self.mesh.triangle_count != count:
                    raise MemoryError("Could not build complete mesh")
                self.mesh.set_active(True)
            except Exception:
                self.mesh.clear_triangles()
                raise

    def apply(self):
        for index in self.changed:
            self.mesh.update_triangle(index, *unpack_from('<9fHB', self.records, index*40))
            self.applied += 1

    def rollback(self):
        while self.applied:
            index = self.changed[self.applied-1]
            self.mesh.update_triangle(index, *unpack_from(
                '<9fHB', self.buffer.records, index*40))
            self.applied -= 1

    def discard(self):
        if self.created:
            self.mesh.clear_triangles()


def discard_updates(updates):
    for update in updates:
        update.discard()


def apply_updates(updates):
    """Publish new record snapshots only after every mesh update succeeds."""
    try:
        for update in updates:
            update.apply()
    except Exception:
        # Release prepared geometry before rollback so an allocation failure
        # does not leave the recovery path competing with abandoned buffers.
        for update in updates:
            update.records = None
        discard_updates(updates)
        collect()
        for update in reversed(updates):
            update.rollback()
        raise
    for update in updates:
        update.buffer.mesh = update.mesh
        update.buffer.records = update.records


def prepare_mesh(buffer, records, updates=None, validate=True):
    update = buffer.prepare(records, validate)
    if updates is None:
        apply_updates((update,))
    else:
        try:
            updates.append(update)
        except Exception:
            update.discard()
            raise
    return update.mesh


def prepare_mesh_steps(buffer,records,updates,validate=True):
    update=MeshUpdate(buffer,records,validate,deferred=True)
    kept=False
    try:
        yield from update.prepare_steps(validate)
        updates.append(update);kept=True
        return update.mesh
    finally:
        if not kept:update.discard()
