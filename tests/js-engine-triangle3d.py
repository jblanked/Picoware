from picoware.system.js import JS

js = JS()

# init/getters
print("\nTriangle3D: %s" % js.run("""
let triangle3d = import('triangle3d', {
    "x1": 0, "y1": 0, "z1": 0,
    "x2": 1, "y2": 1, "z2": 1,
    "x3": 2, "y3": 2, "z3": 2
});
"""))

# setter
js.run("triangle3d.set('x1', 3)")
print("New x1: %s" % js.run("let x1 = triangle3d.x1;"))
js.run("triangle3d.set('y1', 4)")
print("New y1: %s" % js.run("let y1 = triangle3d.y1;"))
js.run("triangle3d.set('z1', 5)")
print("New z1: %s" % js.run("let z1 = triangle3d.z1;"))
js.run("triangle3d.set('x2', 6)")
print("New x2: %s" % js.run("let x2 = triangle3d.x2;"))
js.run("triangle3d.set('y2', 7)")
print("New y2: %s" % js.run("let y2 = triangle3d.y2;"))
js.run("triangle3d.set('z2', 8)")
print("New z2: %s" % js.run("let z2 = triangle3d.z2;"))
js.run("triangle3d.set('x3', 9)")
print("New x3: %s" % js.run("let x3 = triangle3d.x3;"))
js.run("triangle3d.set('y3', 10)")
print("New y3: %s" % js.run("let y3 = triangle3d.y3;"))
js.run("triangle3d.set('z3', 11)")
print("New z3: %s" % js.run("let z3 = triangle3d.z3;"))
js.run("triangle3d.set('color', '0xFFFF')")
print("New color: %s" % js.run("let color = triangle3d.color;"))
js.run("triangle3d.set('wireframe', true)")
print("New wireframe: %s" % js.run("let wireframe = triangle3d.wireframe;"))

del js
js = None

