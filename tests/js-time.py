from picoware.system.js import JS

js = JS()

result = js.run("time.ticksMs();")
print(result)

del js
js = None
