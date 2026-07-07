from picoware.system.js import JS

js = JS()

result = js.run("let time = import('time'); let ticks = time.ticksMs();")
print(result)

del js
js = None
