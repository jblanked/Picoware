from gc import collect
from picoware.system.view_manager import ViewManager
from pcioware.system.wifi import WiFiUART

u = "Your-username"
p = "Your-password"

vm = ViewManager()
w = WiFiUART()

if w.connect(u, p):
    print("Connected!")
    print("Scanning networks..")
    print(w.scan())
else:
    print("Failed to connect")

del vm, w
vm = None
w = None
collect()