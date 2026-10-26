"""Fixed-size stage tracing; exception output streams without StringIO."""
_stages=[None]*8
_cursor=0

def stage(name):
    global _cursor
    try:from gc import mem_free
    except ImportError:mem_free=lambda:0
    _stages[_cursor]=(name,mem_free());_cursor=(_cursor+1)%len(_stages)

def failure(exc):
    import sys
    for i in range(len(_stages)):
        entry=_stages[(_cursor+i)%len(_stages)]
        if entry is not None:print('Sprite3D stage',entry)
    if hasattr(sys,'print_exception'):sys.print_exception(exc)
