from picoware.system.js import JS
from picoware.gui.draw import Draw
from picoware.system.vector import Vector
from utime import ticks_ms, ticks_diff, sleep_ms
import micropython

d = Draw()
j = JS()
j.run('let draw = import("draw");')

@micropython.viper
def draw_mp():
    for _ in range(0, 500):
        d.erase()
        d.text(Vector(10, 10), "Hello from MicroPython!")
        d.text(Vector(10, 30), "This is a test of the JS module.")
        d.text(Vector(10, 50), "Drawing with MicroPython and JS.")
        d.swap()

@micropython.viper
def draw_mp_fastest():
    for _ in range(0, 500):
        d._clear(d._background)
        d._text(10, 10, "Hello from MicroPython!", d._foreground)
        d._text(10, 30, "This is a test of the JS module.", d._foreground)
        d._text(10, 50, "Drawing with MicroPython and JS.", d._foreground)
        d.swap()

@micropython.viper
def draw_js():
    j.run("""
    for (let i = 0; i < 500; i++) {
        draw.clear();
        draw.text(10, 10, "Hello from JavaScript!");
        draw.text(10, 30, "This is a test of the JS module.");
        draw.text(10, 50, "Drawing with MicroPython and JS.");
        draw.swap();
    }
    """)


now = ticks_ms()
draw_mp()
print("MicroPython draw time:", ticks_diff(ticks_ms(), now), "ms")
sleep_ms(10)

now = ticks_ms()
draw_js()
print("JavaScript draw time:", ticks_diff(ticks_ms(), now), "ms")
sleep_ms(10)

now = ticks_ms()
draw_mp_fastest()
print("MicroPython draw time (fastest):", ticks_diff(ticks_ms(), now), "ms")
sleep_ms(10)
