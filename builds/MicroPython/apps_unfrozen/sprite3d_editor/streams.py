"""Bounded sequential reads using one SD handle, including failure cleanup."""


def chunks(storage, path, size, chunk_size=800):
    # Some import/test storage adapters only implement positional reads.
    streaming = all(hasattr(storage, name) for name in
                    ('file_open', 'file_read', 'file_close'))
    handle = None
    try:
        if streaming and size:
            handle = storage.file_open(path)
            if handle is None:
                raise OSError('Cannot open editor data')
        for offset in range(0, size, chunk_size):
            length = min(chunk_size, size-offset)
            data = (storage.file_read(handle, offset, length, False) if streaming
                    else storage.read_chunked(path, offset, length))
            if len(data) != length:
                raise OSError('Incomplete editor data')
            yield data
    finally:
        if handle is not None:
            storage.file_close(handle)
