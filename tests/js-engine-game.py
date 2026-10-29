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
    """Return the game property named prop."""
    return js.run("game.get('%s');" % prop)


def set_(key, value_js):
    """Set a game property from a JS value expression."""
    js.run("game.set('%s', %s);" % (key, value_js))


print("\nGame: %s" % js.run(
    "let game = import('game', 'arena', {'x': 320, 'y': 240, 'z': 0}, '0x0000', '0xFFFF');"))

print("\n--- Initial getters ---")
check("name", get("name"), "arena")
check("size", get("size"), {"x": 320, "y": 240, "z": 0})
check("currentLevel (no level)", get("currentLevel"), None)
for g in ["position", "oldPosition", "input", "isActive", "camera"]:
    print("%s: %s" % (g, get(g)))

print("\n--- Setters ---")
set_("name", "'colosseum'")
check("name", get("name"), "colosseum")
set_("name", "'a_much_longer_game_name_to_test_reallocation'")
check("name (long)", get("name"), "a_much_longer_game_name_to_test_reallocation")

for key, v in [("size", (640, 480, 0)), ("position", (1, 2, 3)), ("oldPosition", (4, 5, 6))]:
    set_(key, "{'x': %s, 'y': %s, 'z': %s}" % v)
    check(key, get(key), {"x": v[0], "y": v[1], "z": v[2]})

for value in ["true", "false"]:
    set_("isActive", value)
    check("isActive=%s" % value, get("isActive"), value == "true")

print("\n--- Levels ---")
js.run("let level = import('level', 'dungeon', {'x': 320, 'y': 240, 'z': 0}, game);")
check("currentLevel after level import", get("currentLevel") is not None, True)
check("isActive after level import", get("isActive"), True)

js.run("game.levelRemove(level);")
check("currentLevel after levelRemove", get("currentLevel"), None)

js.run("game.levelAdd(level);")
check("currentLevel after levelAdd", get("currentLevel") is not None, True)

js.run("game.levelSwitch(0);")
check("currentLevel after levelSwitch(0)", get("currentLevel") is not None, True)
js.run("game.levelSwitch('dungeon');")
check("currentLevel after levelSwitch(name)", get("currentLevel") is not None, True)
js.run("game.levelSwitch('does_not_exist');")
print("currentLevel after missing name: %s" % get("currentLevel"))
js.run("game.levelSwitch(99);")
print("currentLevel after index 99: %s" % get("currentLevel"))

print("\n--- Error paths ---")
expect_error("set non-string key", "game.set(123, 1);")
expect_error("levelAdd non-level", "game.levelAdd(5);")
expect_error("levelRemove non-level", "game.levelRemove('x');")
js.run("game.set('not_a_property', 1);")
print("PASS unknown property ignored")
js.run("game.set('position', 5);")
check("position unchanged by non-vector", get("position"), {"x": 1, "y": 2, "z": 3})


print("\n%s (%d failure(s))" % ("ALL PASSED" if failures == 0 else "FAILURES", failures))

# must delete after
js.run('game.destroy()')

del js
js = None