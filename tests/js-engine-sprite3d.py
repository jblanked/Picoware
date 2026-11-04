from picoware.system.js import JS

js = JS()

# init/getters
print("\nSprite3D: %s" % js.run("let sprite3d = import('sprite3d');"))

print("Position: %s" % js.run("let position = sprite3d.get('position');"))
print("Rotation: %s" % js.run("let rotation = sprite3d.get('rotation');"))
print("Scale: %s" % js.run("let scale = sprite3d.get('scale');"))
print("Triangle Count: %s" % js.run("let triangleCount = sprite3d.get('triangleCount');"))
print("Type: %s" % js.run("let type = sprite3d.get('type');"))
print("Active: %s\n" % js.run("let active = sprite3d.get('active');"))

# setters
js.run("sprite3d.set('active', false);")
print("New Active: %s" % js.run("let active2 = sprite3d.get('active');"))
js.run("sprite3d.set('active', true);")
print("Active Restored: %s" % js.run("let active3 = sprite3d.get('active');"))

js.run("sprite3d.set('position', {'x': 4, 'y': 5, 'z': 6});")
print("New Position: %s" % js.run("let position2 = sprite3d.get('position');"))

js.run("sprite3d.set('rotation', 45);")
print("New Rotation: %s" % js.run("let rotation2 = sprite3d.get('rotation');"))

js.run("sprite3d.set('scale', 2);")
print("New Scale: %s" % js.run("let scale2 = sprite3d.get('scale');"))

# no getter for wireframe, so just exercise both paths
js.run("sprite3d.set('wireframe', true);")
js.run("sprite3d.set('wireframe', false);")
js.run("sprite3d.set('wireframe', true);")

# unknown keys are ignored by the binding; make sure nothing crashes
js.run("sprite3d.set('not_a_property', 1);")

# triangle methods
print("\nReserve Triangles: %s" % js.run("sprite3d.reserveTriangles(32);"))

# addTriangle(x1,y1,z1, x2,y2,z2, x3,y3,z3, color?, wireframe?)
js.run("sprite3d.addTriangle(0, 0, 0, 1, 1, 1, 2, 2, 2, '0x0000', false);")
print("Count after addTriangle (defaults): %s" % js.run("sprite3d.get('triangleCount');"))

js.run("sprite3d.addTriangle(0, 0, 0, 1, 0, 0, 0, 1, 0, '0xF800', true);")
print("Count after addTriangle (color+wireframe): %s" % js.run("sprite3d.get('triangleCount');"))

# updateTriangle(index, 9 coords, color?, wireframe?)
print("Update Triangle 0: %s" % js.run(
    "sprite3d.updateTriangle(0, 0, 0, 0, 2, 0, 0, 0, 2, 0, '0x07E0', false);"))
print("Update Triangle (out of range): %s" % js.run(
    "sprite3d.updateTriangle(9999, 0, 0, 0, 1, 0, 0, 0, 1, 0);"))
print("Update Triangle (negative index): %s" % js.run(
    "sprite3d.updateTriangle(-1, 0, 0, 0, 1, 0, 0, 0, 1, 0);"))

js.run("sprite3d.bakeTransform();")
print("Position after bakeTransform: %s" % js.run("let position3 = sprite3d.get('position');"))
print("Scale after bakeTransform: %s" % js.run("let scale3 = sprite3d.get('scale');"))

js.run("sprite3d.clearTriangles();")
print("Count after clearTriangles: %s\n" % js.run("sprite3d.get('triangleCount');"))

# shape generator tests
shapes = [
    ("createHumanoid (defaults)", "sprite3d.createHumanoid();"),
    ("createHumanoid (height, color)", "sprite3d.createHumanoid(2.0, '0x001F');"),
    ("createTree (defaults)", "sprite3d.createTree();"),
    ("createTree (height, color)", "sprite3d.createTree(3.0, '0x07E0');"),
    ("createHouse (defaults)", "sprite3d.createHouse();"),
    ("createHouse (w, h, color)", "sprite3d.createHouse(3.0, 3.5, '0xFFE0');"),
    ("createPillar (defaults)", "sprite3d.createPillar();"),
    ("createPillar (h, r, color)", "sprite3d.createPillar(4.0, 0.5, '0xFFFF');"),
    ("createWall (xyz only)", "sprite3d.createWall(0, 0, 0);"),
    ("createWall (all args)", "sprite3d.createWall(1, 0, 1, 5.0, 2.0, 0.3, '0x7BEF');"),
    ("createCube", "sprite3d.createCube(0, 0, 0, 1, 1, 1, '0xF800');"),
    ("createCylinder (default segments)", "sprite3d.createCylinder(0, 0, 0, 0.5, 2, undefined, '0x07FF');"),
    ("createCylinder (12 segments)", "sprite3d.createCylinder(0, 0, 0, 0.5, 2, 12, '0x07FF');"),
    ("createSphere (default segments)", "sprite3d.createSphere(0, 0, 0, 1, undefined, '0xF81F');"),
    ("createSphere (8 segments)", "sprite3d.createSphere(0, 0, 0, 1, 8, '0xF81F');"),
    ("createTriangularPrism", "sprite3d.createTriangularPrism(0, 0, 0, 2, 2, 2, '0xFD20');"),
]

for label, code in shapes:
    js.run("sprite3d.clearTriangles();")
    js.run(code)
    print("%s -> triangles: %s" % (label, js.run("sprite3d.get('triangleCount');")))

js.run("sprite3d.clearTriangles();")

js.run("sprite3d.createCube(0, 0, 0, 1, 1, 1, '0xF800');")
count_before = js.run("sprite3d.get('triangleCount');")
print("\nTriangles before save: %s" % count_before)

path = "windmill.sprite3d"
# print("To Path: %s" % js.run("sprite3d.toPath('%s');" % path))

js.run("sprite3d.clearTriangles();")
print("Count after clear: %s" % js.run("sprite3d.get('triangleCount');"))

print("From Path (wireframe default): %s" % js.run("sprite3d.fromPath('%s');" % path))
print("Count after load: %s" % js.run("sprite3d.get('triangleCount');"))

print("From Path (wireframe false): %s" % js.run("sprite3d.fromPath('%s', false);" % path))
print("From Path (missing file): %s" % js.run("sprite3d.fromPath('/picoware/does_not_exist.bin');"))
# print("To Path (no args): %s" % js.run("sprite3d.toPath();"))

# cleanup
js.run("sprite3d.clearTriangles();")

del js
js = None