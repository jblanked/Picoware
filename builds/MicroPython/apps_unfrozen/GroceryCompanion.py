import sys

# VERSION 2.23
_app = None

def start(view_manager) -> bool:
    global _app

    # Initial Loading Screen
    try:
        from grocery_lib.loading import CartLoader
        _loading = CartLoader(view_manager.draw, "Grocery Companion...")
        _loading.animate()
    except:
        _loading = None

    try:
        from grocery_lib.app import GroceryApp
        _app = GroceryApp(view_manager, _loading)
        if _loading: _loading.stop()
        _app._initial_boot()
        if _loading: del _loading
        return True
    except Exception as e:
        sys.print_exception(e)
        if "_loading" in locals() and _loading:
            _loading.stop()
        return False

def run(view_manager) -> None:
    if _app:
        _app.run()

def stop(view_manager) -> None:
    global _app
    if _app:
        try: _app.stop()
        except Exception: pass
        _app = None

    from gc import collect
    collect()