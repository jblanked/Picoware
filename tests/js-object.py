from picoware.system.js import JS

js = JS()

# Test object operations
result = js.run("""

function test() {
    return "test";
}
let obj = {x: 10, y: 20};
let x = obj.x;
obj.z = 30;
let proto = {greeting: 'hi'};
let child = Object.create(proto);
let childVal = child.greeting;
""")

print("test", js.run("test();"))
print("obj.x:", js.run("obj.x;"))
print("obj.z:", js.run("obj.z;"))
print("child.greeting:", js.run("child.greeting;"))

del js
js = None
