from picoware.system.js import JS

js = JS()

response = js.run('let http = import("http"); let response = http.request("https://catfact.ninja/fact", "GET");')

print(response)

del js
js = None
