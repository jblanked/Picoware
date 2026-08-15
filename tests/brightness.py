from picoware.gui.draw import Draw
import utime

d = Draw()

for i in range(1, 10):
    d.set_brightness(i * 10)
    utime.sleep_ms(100)

for i in reversed(range(0, 9)):
    d.set_brightness(i * 10)
    utime.sleep_ms(100)

del d
d = None