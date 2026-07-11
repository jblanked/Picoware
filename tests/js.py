from picoware.system.js import JS

js = JS()

# Define a counter function
js.run("""
let count = 0;
function increment() {
    count += 1;
    return count;
}
""")

print(js.run("increment()"))  # 1
print(js.run("increment()"))  # 2
print(js.run("increment()"))  # 3

del js
js = None