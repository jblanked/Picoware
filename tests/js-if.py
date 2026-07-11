from picoware.system.js import JS

js = JS()

# Test if/else with comparisons
print(js.run("""
let x = 15;
let y = 20;
let result = '';
if (x > 10) {
    result = result + 'big';
} else {
    result = 'small';
}
if (y > x) {
    result = result + 'ger';
}
if (x === 15) {
    result = result + '!';
}
"""))

del js
js = None
