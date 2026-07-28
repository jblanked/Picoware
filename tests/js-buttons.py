from picoware.system.js import JS

js = JS()

js.run("let buttons = import('buttons');")

print(js.run("buttons.BUTTON_NONE"))
print(js.run("buttons.BUTTON_UP"))
print(js.run("buttons.BUTTON_DOWN"))
print(js.run("buttons.BUTTON_RIGHT"))
print(js.run("buttons.BUTTON_LEFT"))
print(js.run("buttons.BUTTON_CENTER"))
print(js.run("buttons.BUTTON_BACK"))
print(js.run("buttons.BUTTON_SPACE"))

print(js.run("buttons;"))