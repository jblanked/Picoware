from picoware.system.js import JS

js = JS()

result = js.run('''
let success = storage.write("test.txt", "Hello World");
let data = "";
if(success) {
    data = storage.read("test.txt");
}
''')

print(result)