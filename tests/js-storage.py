from picoware.system.js import JS

js = JS()

result = js.run('''
let storage = import('storage');
let success = storage.write("test.txt", "Hello World");
let data = "";
if(success) {
    data = storage.read("test.txt");
}
''')

print(result)