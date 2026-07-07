from picoware.system.js import JS

js = JS()

# Test JSON stringify and parse
result = js.run("""
let obj = {name: 'test', value: 42};
let str = JSON.stringify(obj);
let parsed = JSON.parse(str);
let name = parsed.name;
let val = parsed.value;
""")

print("Stringified:", js.run("str"))
print("Parsed name:", js.run("parsed.name"))
print("Parsed value:", js.run("parsed.value"))

del js
js = None
