from picoware.system.js import JS

js = JS()

# function factorial(n) {
#     if (n <= 1) return 1;
#     return n * factorial(n - 1);
# }
# factorial(5)

print(js.exec("test.js")) # returns 120

del js
js = None