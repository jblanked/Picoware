from picoware.system.view_manager import ViewManager
from picoware.system.app_loader import AppLoader
from picoware.system.view import View

def start(vm):
    return True

def stop(vm):
    pass

def run(vm):
    print('running: core 0')
    print('core 0 - done running')

vm = ViewManager()
s = vm.storage

TIMEOUT = 100 # doesnt really matter, just increase/lower to see if multi-core is really working

s.write("picoware/apps/test_script.py", "print('hi')")



s.write("picoware/apps/test.py",f"""
def start(vm):
    return True

def stop(vm):
    pass

def run(vm):
    from utime import sleep_ms
    print('running: app 1')
    steady = {TIMEOUT}
    i = steady
    while i > 0:
        i -= 1
        print('waiting: app 1')
""")
s.write("picoware/apps/test2.py",f"""
def start(vm):
    return True

def stop(vm):
    pass

def run(vm):
    from utime import sleep_ms
    print('running: app 2')
    steady = {TIMEOUT} / 2
    i = steady
    while i > 0:
        i -= 1
        print('waiting: app 2')
""")
try:
    vm.add(
        View(
            "app_tester",
            run,
            start,
            stop,
        )
    )
    vm.switch_to("app_tester")
    
    al = vm.app_loader
    
    if not al.run_script_task("picoware/apps/test_script.py", continuous=True):
        raise Exception("Failed to run script")
    
    apps = al.list_available_apps()
    print(apps)
    if not al.run_app_task(apps[-6], continuous=True): # test
        raise Exception("Failed to run app")
    if not al.run_app_task(apps[-5], continuous=True): # test2
        raise Exception("Failed to run app")
    while True:
        vm.run()
finally:
    vm.__cleanup()
    del vm
    vm = None