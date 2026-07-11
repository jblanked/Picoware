from picoware.system.js import JS

js = JS()

# Test boolean logic, ternary, typeof
result = js.run("""
let a = true;
let b = false;
let and = a && b;
let or = a || b;
let not = !a;
let tern = (5 > 3) ? 'yes' : 'no';
let typeNum = typeof 42;
let typeStr = typeof 'hi';
let nan = isNaN('not a number');
""")

print("a && b:", js.run("and"))
print("a || b:", js.run("or"))
print("!a:", js.run("not"))
print("ternary:", js.run("tern"))
print("typeof 42:", js.run("typeNum"))
print("typeof 'hi':", js.run("typeStr"))
print("isNaN:", js.run("nan"))

del js
js = None
