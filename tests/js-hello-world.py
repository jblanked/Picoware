from picoware.system.js import JS

js = JS()

res = js.run("""
    let draw = import('draw');
    draw.clear();
    draw.text(10, 10, 'Hello World');
    let x = [30, 50, 70];
    let y = [30, 100, 50];
    draw.fillPolygon(x, y);
    draw.swap();
    draw.screenshot("js.bmp")
    let pixels = draw.len("Hello World");
""")

print(f"Hello world is {res} pixels long")