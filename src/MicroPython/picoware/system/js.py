import mjs

class JS(mjs.MJS):
    """A MicroPython wrapper for the MJS JavaScript engine.
    
    Methods:
        - exec(path): Executes the JavaScript code from the specified file path and returns the result.
        - run(js_code): Executes the provided JavaScript code and returns the result.
    """

    def __init__(self, view_manager):
        super().__init__()
        draw = view_manager.draw
        self.run(f'let _background = parseColor({draw.background});')
        self.run(f'let _foreground = parseColor({draw.foreground});')
        self.run("""
        let draw = {
            char: function(x, y, c, color, font_size) {
                if (typeof color === "undefined") { color = _foreground; }
                if (typeof font_size === "undefined") { font_size = 0; }
                lcd_char(x, y, c, parseColor(color), font_size);
            },
            circle: function(cx, cy, radius, color) {
                if (typeof color === "undefined") { color = _foreground; }
                lcd_circle(cx, cy, radius, parseColor(color));
            },
            clear: function(color) {
                if (typeof color === "undefined") { color = _background; }
                lcd_clear(parseColor(color));
            },
            fillCircle: function(cx, cy, radius, color) {
                if (typeof color === "undefined") { color = _foreground; }
                lcd_fill_circle(cx, cy, radius, parseColor(color));
            },
            fillRectangle: function(x, y, w, h, color) {
                if (typeof color === "undefined") { color = _foreground; }
                lcd_fill_rectangle(x, y, w, h, parseColor(color));
            },
            fillRoundRectangle: function(x, y, w, h, r, color) {
                if (typeof color === "undefined") { color = _foreground; }
                lcd_fill_round_rectangle(x, y, w, h, r, parseColor(color));
            },
            fillTriangle: function(x1, y1, x2, y2, x3, y3, color) {
                if (typeof color === "undefined") { color = _foreground; }
                lcd_fill_triangle(x1, y1, x2, y2, x3, y3, parseColor(color));
            },
            line: function(x1, y1, x2, y2, color) {
                if (typeof color === "undefined") { color = _foreground; }
                lcd_line(x1, y1, x2, y2, parseColor(color));
            },
            pixel: function(x, y, color) {
                if (typeof color === "undefined") { color = _foreground; }
                lcd_pixel(x, y, parseColor(color));
            },
            rectangle: function(x, y, w, h, color) {
                if (typeof color === "undefined") { color = _foreground; }
                lcd_rectangle(x, y, w, h, parseColor(color));
            },
            swap: function() {
                lcd_swap();
            },
            text: function(x, y, text, color, font_size) {
                if (typeof color === "undefined") { color = _foreground; }
                if (typeof font_size === "undefined") { font_size = 0; }
                lcd_text(x, y, text, parseColor(color), font_size);
            },
            triangle: function(x1, y1, x2, y2, x3, y3, color) {
                if (typeof color === "undefined") { color = _foreground; }
                lcd_triangle(x1, y1, x2, y2, x3, y3, parseColor(color));
            },
        };
        let math = {
            ceil: function(x) { return math_ceil(x); },
            cos: function(x) { return math_cos(x); },
            floor: function(x) { return math_floor(x); },
            pow: function(x, y) { return math_pow(x, y); },
            random: function() { return math_random(); },
            sin: function(x) { return math_sin(x); },
            sqrt: function(x) { return math_sqrt(x); },
        };
        """)