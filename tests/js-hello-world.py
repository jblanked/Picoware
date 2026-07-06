from picoware.system.js import JS

js = JS()

js.run("""
    draw.clear();
    draw.text(10, 10, 'Hello World');
    draw.swap();
""")