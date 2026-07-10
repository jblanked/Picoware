from picoware.system.js import JS

js = JS()

# Test while loop
result = js.run("""
let count = 5;
let fact = 1;
while (count > 0) {
    fact = fact * count;
    count = count - 1;
}
""")

print("5 !=", js.run("fact"))

del js
js = None
