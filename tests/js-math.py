from picoware.system.js import JS

js = JS()

# Test math functions
result = js.run("""
let math = import('math');
let a = math.floor(3.7);
let b = math.ceil(3.2);
let c = math.sqrt(144);
let d = math.pow(2, 8);
let e = math.sin(0);
let f = math.cos(0);
""")

print("floor(3.7):", js.run("a"))
print("ceil(3.2):", js.run("b"))
print("sqrt(144):", js.run("c"))
print("pow(2,8):", js.run("d"))
print("sin(0):", js.run("e"))
print("cos(0):", js.run("f"))

del js
js = None
