from picoware.system.js import JS

js = JS()
failures = 0
RUN_ASYNC = False  # enable to test runAsync


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


def get(prop, extra:str=None):
    """Return the engine property named prop."""
    if extra is None:
        return js.run("engine.get('%s');" % prop)
    return js.run("let getter = engine.get('%s'); let result = getter.get('%s');" % (prop, extra))


js.run("let game = import('game', 'arena', {'x': 320, 'y': 240, 'z': 0}, '0x0000', '0xFFFF');")
js.run("let level = import('level', 'dungeon', {'x': 320, 'y': 240, 'z': 0}, game);")
print("\nEngine: %s" % js.run("let engine = import('engine', game, 60, true);"))

print("\n--- Initial getters ---")
check("clamp", get("clamp"), True)
print("input: %s" % get("input"))
check("engine.get('game').name", get('game', 'name'), "arena")
check("engine.get('game').size", get('game', 'size'), {"x": 320, "y": 240, "z": 0})
check("engine.get('game').isActive", get('game', 'isActive'), True)

print("\n--- Setters ---")
js.run("engine.set('clamp', false);")
check("clamp via set", get("clamp"), False)
js.run("engine.set('clamp', true);")
check("clamp via setClamp", get("clamp"), True)

js.run("engine.set('input', 5);")
check("input via set", get("input"), 5)
js.run("engine.updateGameInput(3);")
check("input via updateGameInput", get("input"), 3)
check("game.input matches engine.input", get("game", 'input'), 3)

print("\n--- Stop ---")
js.run("engine.stop();")
check("game.isActive after stop", get('game', 'isActive'), False)
js.run("engine.stop();")
print("PASS second stop is a no-op")

if RUN_ASYNC:
    print("\n--- runAsync ---")
    js.run("engine.runAsync(false);")
    print("game.isActive after runAsync: %s" % js.run("engine.get('game').get('isActive');"))
    js.run("engine.stop();")

print("\n--- Error paths ---")
expect_error("set non-string key", "engine.set(123, 1);")
expect_error("set input non-number", "engine.set('input', 'x');")
expect_error("updateGameInput non-number", "engine.updateGameInput('x');")
js.run("engine.set('not_a_property', 1);")
print("PASS unknown property ignored")

print("\n%s (%d failure(s))" % ("ALL PASSED" if failures == 0 else "FAILURES", failures))

# must delete engine when done
js.run("engine.destroy();")

del js
js = None