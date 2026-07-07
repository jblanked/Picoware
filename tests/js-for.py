from picoware.system.js import JS

js = JS()

# Test for loop
result = js.run("""
let sum = 0;
for (let i = 1; i <= 10; i++) {
    sum = sum + i;
}
let result = sum;
""")
print(result)

del js
js = None
