"""SD-installed PicoChess lifecycle."""

_app = None


def splash_enabled(view_manager):
    # Read only this preference before importing the game and its dependencies.
    import json
    storage=view_manager.storage
    for path in ('picoware/picochess/options.json','picoware/picochess/options.json.bak'):
        try:
            if not storage.exists(path): continue
            data=json.loads(storage.read(path))
            if isinstance(data,dict):
                value=data.get('splash',True)
                return value if isinstance(value,bool) else True
        except (OSError,ValueError,TypeError): pass
    return True


def start(view_manager):
    from time import ticks_ms, ticks_diff, sleep_ms
    enabled=splash_enabled(view_manager)
    if enabled:
        from .splash import show
        show(view_manager)
    started=ticks_ms()
    from .app import App
    if enabled:
        remaining=1500-ticks_diff(ticks_ms(),started)
        if remaining>0: sleep_ms(remaining)
    global _app
    _app=App(view_manager)
    return True


def run(view_manager):
    if _app is not None:
        _app.run()


def stop(view_manager):
    global _app
    if _app is not None:
        _app.close()
        _app = None
