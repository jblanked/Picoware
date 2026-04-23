from picoware.gui.draw import Draw
from picoware.gui.list import List
from gc import collect

d = Draw()
d.use_lvgl = True

l = List(
    d,
    0,
    d.size.x,
    d.foreground,
    d.background,
)

for i in range(20):
    l.add_item(f"test{i}")
l.draw()

del l
l = None

del d
d = None

collect()
collect()
collect()
collect()
