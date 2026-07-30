from picoware.gui.draw import Draw

d = Draw()

print(d.scale_y(10))
print(d.scale_x(10))
print(d.scale_y(0))
print(d.scale_x(0))
print(d.scale_y(-30))
print(d.scale_x(-30))
print(d.scale(0, 10))
print(d.scale(10, 0))