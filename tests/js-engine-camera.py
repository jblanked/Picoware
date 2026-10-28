from picoware.system.js import JS

js = JS()

# init/getters
print("\nCamera: %s" % js.run("let camera = import('camera');"))

print("Direction: %s" % js.run("let direction = camera.direction;"))

print("Perspective: %s" % js.run("let perspective = camera.perspective;"))

print("Height: %s" % js.run("let height = camera.height;"))

print("Plane: %s" % js.run("let plane = camera.plane;"))

print("Position: %s\n" % js.run("let position = camera.position;"))

# setter
js.run("camera.set('direction', {'x': 3, 'y': 2, 'z': 1})")
print("New Direction: %s" % js.run("let direction = camera.direction;"))

js.run("camera.set('perspective', 1)")
print("New Perspective: %s" % js.run("let perspective = camera.perspective;"))

js.run("camera.set('height', 5)")
print("New Height: %s" % js.run("let height = camera.height;"))

js.run("camera.set('plane', {'x': 1, 'y': 2, 'z': 3})")
print("New Plane: %s" % js.run("let plane = camera.plane;"))

js.run("camera.set('position', {'x': 4, 'y': 5, 'z': 6})")
print("New Position: %s" % js.run("let position = camera.position;"))

del js
js = None

