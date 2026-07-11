from picoware.system.js import JS

js = JS()

# Test string operations
result = js.run("""
let s = 'Hello World';
let len = s.length;
let sl = s.slice(0, 5);
let idx = s.indexOf('World');
let code = s.charCodeAt(0);
let char = s[6];
""")

print("Length:", js.run("s.length"))
print("Slice:", js.run("s.slice(0, 5)"))
print("IndexOf:", js.run("s.indexOf('World')"))
print("CharCode:", js.run("s.charCodeAt(0)"))

del js
js = None
