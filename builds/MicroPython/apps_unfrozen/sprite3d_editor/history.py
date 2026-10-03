"""SD-backed transform backups and exact Undo/Redo history."""

from binascii import crc32


class History:
    def __init__(self, storage, max_entries=16):
        self.storage = storage
        self.max_entries = max_entries
        self.directory = None
        self.owned = []
        self.serial = 0
        self.reset()

    def release(self, snapshot):
        path = snapshot[0]
        if path is None:
            return
        try:
            removed = not self.storage.exists(path) or self.storage.remove(path)
        except OSError:
            removed = False
        if removed and path in self.owned:
            self.owned.remove(path)

    def reset(self):
        for path in self.owned[:]:
            self.release((path,0,0))
        if self.directory and not self.owned:
            try:
                self.storage.rmdir(self.directory)
            except OSError:
                pass
            self.directory = None
        self.undo = []
        self.redo = []
        self.bytes_used = 0
        self.revision = 0
        self.saved_revision = 0
        self.next_revision = 1

    def prepare(self):
        if self.directory is not None:
            return
        for path in ("/picoware", "/picoware/cache", "/picoware/cache/sprite3d_editor"):
            if not self.storage.exists(path) and not self.storage.mkdir(path):
                raise OSError("Cannot create SD editor cache")
        index = 0
        while True:
            path = "/picoware/cache/sprite3d_editor/session-%d" % index
            if not self.storage.exists(path):
                break
            index += 1
        if not self.storage.mkdir(path):
            raise OSError("Cannot create SD editor session")
        self.directory = path

    def store(self, records):
        if not records:
            return (None,0,0)
        self.prepare()
        self.serial += 1
        path = self.directory + "/snap-%d.bin" % self.serial
        snapshot = (path,len(records),crc32(records))
        # Never overwrite or delete a file we did not create.
        if self.storage.exists(path):
            raise OSError("SD cache filename collision")
        self.owned.append(path)
        try:
            # Storage's binary writer appends: only write a new, unique file.
            if not self.storage.write(path,records,"wb"):
                raise OSError("Cannot write SD edit backup")
            if not self.matches(snapshot,records):
                raise OSError("SD edit backup verification failed")
            return snapshot
        except Exception:
            self.release(snapshot)
            raise

    def chunks(self, snapshot):
        if len(snapshot) == 4:
            source = memoryview(snapshot[3])
            for offset in range(0,len(source),800):
                yield source[offset:offset+800]
            return
        path,size,checksum = snapshot
        if path is None and size == 0:
            return
        if self.storage.size(path) != size:
            raise OSError("SD edit backup is missing or incomplete")
        crc = 0
        from .streams import chunks
        reader = chunks(self.storage,path,size)
        try:
            for data in reader:
                crc = crc32(data,crc)
                yield data
        finally:
            reader.close()
        if crc != checksum:
            raise OSError("SD edit backup checksum failed")

    def read(self, snapshot):
        records = bytearray()
        reader = self.chunks(snapshot)
        try:
            for data in reader:
                records.extend(data)
        finally:
            reader.close()
        return records

    def matches(self, snapshot, records):
        equal = len(records) == snapshot[1]
        offset = 0
        reader = self.chunks(snapshot)
        try:
            for data in reader:
                if data != records[offset:offset+len(data)]:
                    equal = False
                offset += len(data)
        finally:
            reader.close()
        return equal

    @property
    def dirty(self):
        return self.revision != self.saved_revision

    def mark_saved(self):
        self.saved_revision = self.revision

    def commit(self, before, label, replace=None, records=None):
        self.undo.append((before,self.revision,label))
        if replace is not None:
            try:
                replace(records)
            except Exception:
                self.undo.pop()
                raise
        self.bytes_used += before[1]
        for snapshot, revision, old_label in self.redo:
            self.bytes_used -= snapshot[1]
            self.release(snapshot)
        self.redo.clear()
        self.revision = self.next_revision
        self.next_revision += 1
        while len(self.undo) > self.max_entries:
            snapshot, revision, old_label = self.undo.pop(0)
            self.bytes_used -= snapshot[1]
            self.release(snapshot)

    def travel(self, current, replace, redo=False):
        source, destination = (self.redo,self.undo) if redo else (self.undo,self.redo)
        if not source:
            return None
        target, revision, label = source[-1]
        records = self.read(target)
        backup = self.store(current)
        try:
            destination.append((backup,self.revision,label))
        except Exception:
            self.release(backup)
            raise
        try:
            replace(records)
        except Exception:
            destination.pop()
            self.release(backup)
            raise
        source.pop()
        self.bytes_used += backup[1]-target[1]
        self.revision = revision
        self.release(target)
        return label
