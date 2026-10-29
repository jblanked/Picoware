from picoware.system.js import JS

js = JS()
failures = 0


def close(a, b):
    """Compare values with float tolerance. Dict expectations match by key; returns True on match."""
    if isinstance(b, dict):
        return isinstance(a, dict) and all(close(a.get(k), v) for k, v in b.items())
    if isinstance(b, (int, float)) and not isinstance(b, bool):
        return isinstance(a, (int, float)) and abs(a - b) < 1e-3
    return a == b


def check(label, actual, expected):
    """Print PASS or FAIL for actual versus expected and count failures."""
    global failures
    ok = close(actual, expected)
    failures += 0 if ok else 1
    print("%s %s: %s%s" % ("PASS" if ok else "FAIL", label, actual,
                           "" if ok else " (expected %s)" % (expected,)))


def expect_error(label, code):
    """Run JS code that must raise an error, and count a failure if it does not."""
    global failures
    try:
        result = js.run(code)
        failures += 1
        print("FAIL %s: no error, returned %s" % (label, result))
    except Exception as e:
        print("PASS %s raised: %s" % (label, e))


def get(prop):
    """Return the level property named prop."""
    return js.run("level.get('%s');" % prop)


def set_(key, value_js):
    """Set a level property from a JS value expression."""
    js.run("level.set('%s', %s);" % (key, value_js))

js.run("let game = import('game', 'dungeon', {'x': 320, 'y': 240, 'z': 0});")

print("\nLevel: %s" % js.run(
    "let level = import('level', 'dungeon', {'x': 320, 'y': 240, 'z': 0}, game);"))

print("\n--- Initial getters ---")
check("name", get("name"), "dungeon")
check("size", get("size"), {"x": 320, "y": 240, "z": 0})
check("entityCount", get("entityCount"), 0)
for g in ["lightDirection", "shadowColor", "clearAllowed"]:
    print("%s (default): %s" % (g, get(g)))

print("\n--- Setters ---")
set_("name", "'crypt'")
check("name", get("name"), "crypt")
set_("name", "'a_much_longer_level_name_to_test_reallocation'")
check("name (long)", get("name"), "a_much_longer_level_name_to_test_reallocation")

set_("size", "{'x': 640, 'y': 480, 'z': 8}")
check("size", get("size"), {"x": 640, "y": 480, "z": 8})

set_("lightDirection", "{'x': 0.5, 'y': -1, 'z': 0.25}")
print("lightDirection (may be normalized): %s" % get("lightDirection"))

set_("shadowColor", "'0x7BEF'")
check("shadowColor", get("shadowColor"), 0x7BEF)

for value in ["true", "false"]:
    set_("clearAllowed", value)
    check("clearAllowed=%s" % value, get("clearAllowed"), value == "true")

print("\n--- Entities (no game) ---")
js.run("let entity = import('entity', 'hero', 0, "
       "{'x': 10, 'y': 20, 'z': 0}, {'x': 8, 'y': 8, 'z': 2});")
js.run("level.entityAdd(entity);")
check("entityCount after add (expect 0)", get("entityCount"), 0)

print("\n--- Entities (game back-fit) ---")
js.run("let game = import('game', 'arena', {'x': 320, 'y': 240, 'z': 0}, '0x0000', '0xFFFF');")

js.run("level.entityAdd(entity);")
check("entityCount after add", get("entityCount"), 1)
check("getEntity(0) exists", js.run("level.get('entity', 0);") is not None, True)
check("getEntity(99) out of range", js.run("level.get('entity', 99);"), None)
check("getEntity(-1) out of range", js.run("level.get('entity', -1);"), None)
print("hasCollided(entity): %s" % js.run("level.hasCollided(entity);"))

# js.run("level.entityRemove(entity);")
check("entityCount after remove", get("entityCount"), 0)

# js.run("level.clear();")
check("entityCount after clear", get("entityCount"), 0)

print("\n--- Error paths ---")
expect_error("set non-string key", "level.set(123, 1);")
expect_error("entityAdd non-entity", "level.entityAdd(5);")
expect_error("entityRemove non-entity", "level.entityRemove('x');")
expect_error("hasCollided non-entity", "level.hasCollided(5);")
expect_error("getEntity non-number", "level.get('entity', 'a');")
js.run("level.set('not_a_property', 1);")
print("PASS unknown property ignored")

print("\n%s (%d failure(s))" % ("ALL PASSED" if failures == 0 else "FAILURES", failures))

# must destroy after
js.run('level.destroy()')

del js
js = None