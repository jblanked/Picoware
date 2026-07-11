from picoware.system.js import JS

js = JS()

# Define functions
js.run("""
function add(a, b) {
    return a + b;
}
function fib(n) {
    if (n <= 1) return n;
    return fib(n - 1) + fib(n - 2);
}
function makeCounter() {
    let c = 0;
    return function() {
        c = c + 1;
        return c;
    };
}
let counter = makeCounter();
""")

print("add(3,4):", js.run("add(3, 4)"))
print("fib(10):", js.run("fib(10)"))
print("counter():", js.run("counter()"))
print("counter():", js.run("counter()"))

del js
js = None
