from picoware.system.view_manager import ViewManager
from picoware.gui.list import List
from gc import collect

vm = ViewManager()
d = vm.draw
d.use_lvgl = True

l = List(
    d,
    0,
    d.size.x,
    vm.foreground_color,
    vm.background_color,
)

for i in range(20):
    l.add_item(f"test{i}")
l.draw()

del l
l = None

del vm
vm = None

collect()
collect()
collect()
collect()
