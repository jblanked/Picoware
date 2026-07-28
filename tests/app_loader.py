from picoware.system.app_loader import AppLoader
from picoware.system.view_manager import ViewManager

v = ViewManager()
a = AppLoader(v)

print(a.list_available_apps())