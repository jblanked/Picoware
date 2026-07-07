from picoware.system.js import JS

js = JS()

js.run("""
    let draw = import('draw');
    draw.clear();
    draw.text(10, 10, 'Hello World');
    draw.swap();
""")