from picoware.system.js import JS

js = JS()

# Test array operations
result = js.run("""
let arr = [1, 2, 3];
let len = arr.push(4, 5);
let first = arr[0];
let third = arr[2];
let spliced = arr.splice(1, 2);
""")

print("Array length:", js.run("arr.length"))
print("First:", js.run("arr[0]"))
print("Spliced:", js.run("JSON.stringify(spliced)"))

del js
js = None
