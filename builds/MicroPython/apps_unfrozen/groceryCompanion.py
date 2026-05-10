import sys
import gc
import os

# VERSION 2.23
_app = None

def start(view_manager) -> bool:
    global _app

    # Library Resolution: Priority to /apps, fallback to /apps_unfrozen
    found_path = None
    if not view_manager.storage.vfs_mounted:
        view_manager.storage.mount_vfs("/sd")

    for p in ["/sd/picoware/apps", "/sd/picoware/apps_unfrozen"]:
        try:
            os.stat(p + "/grocery_lib")
            found_path = p
            break
        except OSError:
            pass
            
    if found_path and found_path not in sys.path:
        sys.path.insert(0, found_path)

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
    
    for mod in list(sys.modules.keys()):
        if mod.startswith("grocery_lib"):
            del sys.modules[mod]
    
    gc.collect()

if __name__ == "__main__":
    from picoware.system.view_manager import ViewManager
    from picoware.system.view import View
    vm = None
    try:
        vm = ViewManager()
        vm.add(View("grocery", run, start, stop))
        vm.switch_to("grocery")
        while True: vm.run()
    except KeyboardInterrupt: pass
    finally:
        if vm: del vm
