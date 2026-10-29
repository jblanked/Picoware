from picoware.system.js import JS

js = JS()


def get(prop):
    return js.run("entity.%s;" % prop)


def set_(name, value_js):
    js.run("entity.set('%s', %s);" % (name, value_js))


print("\nEntity: %s" % js.run(
    "let entity = import('entity', 'hero', 0, "
    "{'x': 10, 'y': 20, 'z': 30}, {'x': 8, 'y': 8, 'z': 2}, 0, 0);"))

# constants
print("\n--- Constants ---")
for const in [
    "ENTITY_PLAYER", "ENTITY_ENEMY", "ENTITY_ICON", "ENTITY_NPC", "ENTITY_3D_SPRITE",
    "ENTITY_IDLE", "ENTITY_MOVING", "ENTITY_MOVING_TO_START", "ENTITY_MOVING_TO_END",
    "ENTITY_ATTACKING", "ENTITY_ATTACKED", "ENTITY_DEAD",
    "SPRITE_3D_NONE", "SPRITE_3D_HUMANOID", "SPRITE_3D_TREE", "SPRITE_3D_HOUSE",
    "SPRITE_3D_PILLAR", "SPRITE_3D_CUSTOM",
]:
    print("%s: %s" % (const, get(const)))

# initial getters
print("\n--- Initial getters ---")
getters = [
    "name", "type", "state",
    "position", "oldPosition", "size", "direction", "plane",
    "startPosition", "endPosition", "aabbMin", "aabbMax",
    "is8bit", "isActive", "isVisible", "isPlayer",
    "aabbDirty", "moved", "has3DSprite", "hasChangedPosition",
    "moveTimer", "elapsedMoveTimer", "radius", "speed",
    "attackTimer", "elapsedAttackTimer", "strength",
    "health", "maxHealth", "level", "xp",
    "healthRegen", "elapsedHealthRegen",
    "spriteRotation", "spriteScale", "sprite3DType",
    "billboardPose", "billboardWorldHeight",
]
for g in getters:
    print("%s: %s" % (g, get(g)))

# vector setters (setter key == getter key)
print("\n--- Vector setters ---")
vectors = [
    ("position", (1, 2, 3)),
    ("oldPosition", (4, 5, 6)),
    ("size", (16, 16, 4)),
    ("direction", (0, 1, 0)),
    ("plane", (0.66, 0, 0)),
    ("startPosition", (7, 8, 9)),
    ("endPosition", (10, 11, 12)),
]
for key, (x, y, z) in vectors:
    set_(key, "{'x': %s, 'y': %s, 'z': %s}" % (x, y, z))
    print("New %s: %s" % (key, get(key)))

# scalar setters (camelCase on both sides)
print("\n--- Scalar setters ---")
scalars = [
    ("moveTimer", 1.5),
    ("elapsedMoveTimer", 0.25),
    ("radius", 12.5),
    ("speed", 3.0),
    ("attackTimer", 2.0),
    ("elapsedAttackTimer", 0.5),
    ("strength", 15),
    ("health", 80),
    ("maxHealth", 120),
    ("level", 5),
    ("xp", 250),
    ("healthRegen", 0.75),
    ("elapsedHealthRegen", 0.1),
    ("billboardWorldHeight", 2.5),  # default is 1.8, so a change is visible
]
for key, value in scalars:
    set_(key, str(value))
    print("New %s: %s" % (key, get(key)))

# boolean setters
print("\n--- Boolean setters ---")
for key in ["isActive", "isVisible", "isPlayer"]:
    set_(key, "false")
    print("%s=false -> %s" % (key, get(key)))
    set_(key, "true")
    print("%s=true  -> %s" % (key, get(key)))

# enum setters
print("\n--- Enum setters ---")
for const in ["ENTITY_IDLE", "ENTITY_MOVING", "ENTITY_MOVING_TO_START",
              "ENTITY_MOVING_TO_END", "ENTITY_ATTACKING", "ENTITY_ATTACKED",
              "ENTITY_DEAD"]:
    set_("state", "entity.%s" % const)
    print("state=%s -> %s" % (const, get("state")))

for const in ["ENTITY_PLAYER", "ENTITY_ENEMY", "ENTITY_ICON",
              "ENTITY_NPC", "ENTITY_3D_SPRITE"]:
    set_("type", "entity.%s" % const)
    print("type=%s -> %s" % (const, get("type")))

for const in ["SPRITE_3D_NONE", "SPRITE_3D_HUMANOID", "SPRITE_3D_TREE",
              "SPRITE_3D_HOUSE", "SPRITE_3D_PILLAR", "SPRITE_3D_CUSTOM"]:
    set_("sprite3DType", "entity.%s" % const)
    print("sprite3DType=%s -> sprite3DType: %s | has3DSprite: %s" % (
        const, get("sprite3DType"), get("has3DSprite")))

for pose in [0, 1, 2, 3]:
    set_("billboardPose", str(pose))
    print("billboardPose=%d -> %s" % (pose, get("billboardPose")))


print("\n--- 3D sprite transform ---")
set_("sprite3DType", "entity.SPRITE_3D_HUMANOID")
set_("rotation", "90")
print("New spriteRotation: %s" % get("spriteRotation"))
set_("scale", "2.5")
print("New spriteScale: %s" % get("spriteScale"))

print("\n--- Name ---")
set_("name", "'goblin'")
print("New name: %s" % get("name"))
set_("name", "'a_much_longer_entity_name_to_test_reallocation'")
print("New name (long): %s" % get("name"))

#update position
print("\n--- updatePosition / AABB ---")
set_("position", "{'x': 100, 'y': 200, 'z': 0}")
print("aabbDirty before update: %s" % get("aabbDirty"))
print("aabbMin before update: %s" % get("aabbMin"))
print("aabbMax before update: %s" % get("aabbMax"))
js.run("entity.updatePosition();")
print("aabbDirty after update: %s" % get("aabbDirty"))
print("aabbMin after update: %s" % get("aabbMin"))
print("aabbMax after update: %s" % get("aabbMax"))
print("hasChangedPosition: %s" % get("hasChangedPosition"))
print("moved: %s" % get("moved"))

# aabbMin/aabbMax are accepted by set() but never written
set_("aabbMin", "{'x': -999, 'y': -999, 'z': -999}")
print("aabbMin after set (should be unchanged): %s" % get("aabbMin"))
set_("aabbMax", "{'x': 999, 'y': 999, 'z': 999}")
print("aabbMax after set (should be unchanged): %s" % get("aabbMax"))

# read only getters
print("\n--- Read-only checks ---")
for key in ["is8bit", "aabbDirty", "moved", "has3DSprite", "hasChangedPosition"]:
    before = get(key)
    set_(key, "true")
    print("%s before/after set: %s / %s" % (key, before, get(key)))

# errors
print("\n--- Error paths ---")
for label, code in [
    ("non-string name", "entity.set(123, 1);"),
    ("vector prop with number", "entity.set('position', 5);"),
    ("unknown property", "entity.set('not_a_property', 1);"),
    ("wrong type for state", "entity.set('state', 'abc');"),
    ("snake_case scalar key (ignored)", "entity.set('move_timer', 9.9);"),
    ("snake_case bool key (ignored)", "entity.set('is_active', false);"),
    ("old spelling sprite3dType (ignored)", "entity.set('sprite3dType', 1);"),
]:
    try:
        print("%s: %s" % (label, js.run(code)))
    except Exception as e:
        print("%s raised: %s" % (label, e))

print("moveTimer unchanged by snake_case key (expect 1.5): %s" % get("moveTimer"))
print("isActive unchanged by snake_case key (expect True): %s" % get("isActive"))
print("sprite3DType unchanged by old spelling (expect 1): %s" % get("sprite3DType"))

# cleanup
del js
js = None