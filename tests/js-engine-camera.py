from picoware.system.js import JS

js = JS()

# init/getters
print("\nCamera: %s" % js.run("let camera = import('camera');"))

print("Direction: %s" % js.run("let direction = camera.get('direction');"))

print("Perspective: %s" % js.run("let perspective = camera.get('perspective');"))

print("Height: %s" % js.run("let height = camera.get('height');"))

print("Plane: %s" % js.run("let plane = camera.get('plane');"))

print("Position: %s\n" % js.run("let position = camera.get('position');"))

# setter
print(f"Setting Camera Direction returned: %s" % js.run("let set = camera.set('direction', {'x': 3, 'y': 2, 'z': 1})"))
print("New Direction: %s" % js.run("let direction = camera.get('direction');"))

js.run("camera.set('perspective', 1)")
print("New Perspective: %s" % js.run("let perspective = camera.get('perspective');"))

js.run("camera.set('height', 5)")
print("New Height: %s" % js.run("let height = camera.get('height');"))

js.run("camera.set('plane', {'x': 1, 'y': 2, 'z': 3})")
print("New Plane: %s" % js.run("let plane = camera.get('plane');"))

js.run("camera.set('position', {'x': 4, 'y': 5, 'z': 6})")
print("New Position: %s" % js.run("let position = camera.get('position');"))

# must delete when done
js.run('camera.destroy();')

try:
    # catch expected mjs error
    js.run("camera.set('position', {'x': 4, 'y': 5, 'z': 6})")
    print("New Position: %s" % js.run("let position = camera.get('position');"))
except Exception as e:
    print(e)

del js
js = None
