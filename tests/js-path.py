from picoware.system.view_manager import ViewManager
from picoware.system.js import JS

vm = ViewManager()
js = JS(vm)

# function factorial(n) {
#     if (n <= 1) return 1;
#     return n * factorial(n - 1);
# }
# factorial(5)

print(js.exec("test.js")) # returns 120

del js
js = None