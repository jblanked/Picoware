from picoware.system.view_manager import ViewManager
from picoware.system.settings import Settings

vm = ViewManager()
w = vm.wifi
s = Settings(vm.storage)

results = []

def callback(result: list, available: int, dropped: int):
    global results
    results = []
    print("%d/%d frames/dropped" % (available, dropped))
    results = result

while not w.connect(s.wifi_settings["ssid"], s.wifi_settings["password"],):
    pass

print("wifi connected")
try:
    if not w.csi(True, callback=callback):
        raise Exception(w.error)

    while True:
        if w.error:
            raise Exception(w.error)
        vm.run()
        if results:
            print("RSSI (%d)\nChannel (%d)\nMac (%s)\nTimestamp (%d)\nLocal timestamp (%d)\nData: %s\n" % (results[0], results[1], results[2], results[3], results[4], results[5]))
except Exception as e:
    print(e)
finally:
    w.csi(False)
    vm.__cleanup()
    del vm
    vm = None
    