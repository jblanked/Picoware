from picoware.system.js import JS

js = JS()
js.run("let time = import('time');")
js.run("let pin = import('pin', 28, 'OUT');")

result = js.run("pin.value();")

print(result)
result = js.run("pin.on(); time.sleepMs(100); pin.value()")

print(result)

result = js.run("pin.off(); time.sleepMs(100); pin.value()")

print(result)



result = js.run("pin.toggle(); time.sleepMs(100); pin.value()")

print(result)

result = js.run("pin.toggle(); time.sleepMs(100); pin.value()")

print(result)



result = js.run("pin.high(); time.sleepMs(100); pin.value()")

print(result)

result = js.run("pin.low(); time.sleepMs(100); pin.value()")

print(result)


result = js.run("pin.value(1); time.sleepMs(100); pin.value()")

print(result)

result = js.run("pin.value(0); time.sleepMs(100); pin.value()")

print(result)

del js
js = None

