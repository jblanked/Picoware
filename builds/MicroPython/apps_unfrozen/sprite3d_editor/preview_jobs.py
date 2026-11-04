"""Reclaim disposable preview allocations at cooperative job boundaries."""
from gc import collect, mem_alloc, mem_free

# Shared across preview jobs so cached frames do not force a collection.
# This is a checkpoint trigger, not a hard limit on live or peak memory.
_collected = 0


def checkpoint():
    global _collected
    used=mem_alloc()
    if used-_collected>=131072 or mem_free()<131072:
        collect();_collected=mem_alloc()
    elif used<_collected:
        _collected=used


def bounded_job(method):
    def run(*args,**kwargs):
        job=method(*args,**kwargs)
        # Heap-stat scans are batched instead of running for every triangle/row.
        remaining=16
        try:
            checkpoint()
            while True:
                try:value=next(job)
                except StopIteration as done:return done.value
                remaining-=1
                if not remaining:
                    checkpoint();remaining=16
                yield value
        finally:
            job.close()
    return run
