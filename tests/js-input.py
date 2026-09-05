from picoware.system.js import JS

j = JS()

j.run('let input = import("input");')

print(f"button: {j.run('input.button;')}")
print(f"was_capatilized: {j.run('input.wasCapitalized;')}")

#j.run('input.read();')
print(f"char for button code 5 (BACK): {j.run('input.buttonToChar(5);')}")   # → "" (no mapping)
print(f"char for button code 38 (5 key): {j.run('input.buttonToChar(38);')}") # → "5"
print(f"char for button code 7 (A key): {j.run('input.buttonToChar(7);')}")   # → "a"
print(f"button read: {j.run('input.readNonBlocking();')}")
j.run('input.reset();')