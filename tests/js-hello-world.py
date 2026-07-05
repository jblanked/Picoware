from picoware.system.view_manager import ViewManager
from picoware.system.js import JS

vm = ViewManager()
js = JS(vm)

js.run("draw.clear();")
js.run("draw.text(10, 10, 'Hello World');")
js.run("draw.swap();")
