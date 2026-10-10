"""SD-backed transform backups and exact Undo/Redo history."""

from binascii import crc32


class History:
    def __init__(self, storage, max_entries=16):
        self.storage = storage
        self.max_entries = max_entries
        self.directory = None
        self.owned = []
        self.serial = 0
        self.context = None
        self.contexts = []
        self.metadata = {}
        self.documents = {}
        self.metadata_only = {}
        self.metadata_records = None
        self.encode_document = None
        self.replace_context = None
        self.reset()

    def release(self, snapshot):
        self.metadata_only.pop(id(snapshot),None)
        extra=self.documents.pop(id(snapshot),None)
        if extra is not None:self.release(extra)
        self.metadata.pop(id(snapshot),None)
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
        self.context = None
        self.contexts.clear()
        self.metadata.clear()
        self.documents.clear()
        self.metadata_only.clear()
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
            return tuple([None,0,0])
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

    def store_document(self,records,metadata=None,geometry=True):
        snapshot=self.store(records if geometry else b'')
        try:
            if not geometry:self.metadata_only[id(snapshot)]=len(records)
            if metadata is None and self.encode_document is not None:metadata=self.encode_document()
            if metadata is not None:self.documents[id(snapshot)]=self.store(metadata)
            return snapshot
        except Exception:
            self.release(snapshot);raise

    def document_data(self,snapshot):
        extra=self.documents.get(id(snapshot))
        return self.read(extra) if extra is not None else None

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
        self.metadata[id(before)] = self.context
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

        self.collect_contexts()

    def travel(self, current, replace, redo=False):
        source, destination = (self.redo,self.undo) if redo else (self.undo,self.redo)
        if not source:
            return None
        target, revision, label = source[-1]
        metadata_only=id(target) in self.metadata_only
        if metadata_only and self.metadata_records is not None:
            records=self.metadata_records(current,self.metadata.get(id(target)),self.metadata_only[id(target)])
        else:records = current if metadata_only else self.read(target)
        backup = self.store_document(current,geometry=not metadata_only)
        self.metadata[id(backup)] = self.context
        try:
            destination.append((backup,self.revision,label))
        except Exception:
            self.release(backup)
            raise
        try:
            if self.replace_context is not None:
                self.replace_context(records,self.metadata.get(id(target)),self.document_data(target))
            else:
                replace(records)
        except Exception:
            destination.pop()
            self.release(backup)
            raise
        source.pop()
        self.bytes_used += backup[1]-target[1]
        self.revision = revision
        self.release(target)
        self.collect_contexts()
        return label

    def collect_contexts(self):
        active=[self.context]+[self.metadata.get(id(item[0])) for item in self.undo+self.redo]
        for context in self.contexts[:]:
            if not any(c is context for c in active):
                self.release(context['hidden']);self.contexts.remove(context)
