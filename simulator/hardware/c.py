"""Host C execution for the MicroPython simulator.

The device C module is an ARM compiler/runtime.  The simulator executes the
same source through the host C compiler and transports its display operations
back to the simulator framebuffer.  This keeps C applications executable in
the simulator without pretending that an ARM binary ran on the host.
"""

import os

import sim_runtime


def _quote(path):
    return "'" + str(path).replace("'", "'\"'\"'") + "'"


def _mkdir(path):
    try:
        os.mkdir(path)
    except OSError:
        pass


def _remove_tree(path):
    try:
        entries = os.listdir(path)
    except OSError:
        try:
            os.remove(path)
        except OSError:
            pass
        return
    for entry in entries:
        child = path.rstrip("/") + "/" + entry
        try:
            mode = os.stat(child)[0]
        except OSError:
            continue
        if mode & 0x4000:
            _remove_tree(child)
        else:
            try:
                os.remove(child)
            except OSError:
                pass
    try:
        os.rmdir(path)
    except OSError:
        pass


def _read(path, binary=False):
    mode = "rb" if binary else "r"
    with open(path, mode) as handle:
        return handle.read()


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _write(path, data, binary=False):
    mode = "wb" if binary else "w"
    with open(path, mode) as handle:
        handle.write(data)


def _c_string(path):
    return '"' + str(path).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _runner_source(event_path, result_path):
    return r'''#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/time.h>

static FILE *picoware_events;

static void picoware_event(const char *op, unsigned long a, unsigned long b,
                           unsigned long c, unsigned long d, unsigned long e)
{
    if (picoware_events)
        fprintf(picoware_events, "%s %lu %lu %lu %lu %lu\n", op, a, b, c, d, e);
}

static void picoware_text(unsigned long x, unsigned long y, const char *text,
                          unsigned long color, unsigned long size)
{
    size_t i;
    if (!picoware_events)
        return;
    fprintf(picoware_events, "T %lu %lu %lu %lu ", x, y, color, size);
    for (i = 0; text && text[i]; ++i)
        fprintf(picoware_events, "%02x", (unsigned int)(unsigned char)text[i]);
    fputc('\n', picoware_events);
}

void lcd_char(uint16_t x, uint16_t y, char c, uint16_t color)
{ picoware_event("C", x, y, (unsigned char)c, color, 0); }
void lcd_circle(uint16_t x, uint16_t y, uint16_t radius, uint16_t color)
{ picoware_event("O", x, y, radius, color, 0); }
void lcd_fill(uint16_t color)
{ picoware_event("F", color, 0, 0, 0, 0); }
void lcd_fill_circle(uint16_t x, uint16_t y, uint16_t radius, uint16_t color)
{ picoware_event("o", x, y, radius, color, 0); }
void lcd_fill_rectangle(uint16_t x, uint16_t y, uint16_t width,
                        uint16_t height, uint16_t color)
{ picoware_event("R", x, y, width, height, color); }
void lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width,
                              uint16_t height, uint16_t radius, uint16_t color)
{ picoware_event("Q", x, y, width, height, radius); picoware_event("q", color, 0, 0, 0, 0); }
void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2,
                       uint16_t x3, uint16_t y3, uint16_t color)
{ picoware_event("Y", x1, y1, x2, y2, x3); picoware_event("y", y3, color, 0, 0, 0); }
void lcd_fill_triangle_alpha(uint16_t x1, uint16_t y1, uint16_t x2,
                             uint16_t y2, uint16_t x3, uint16_t y3,
                             uint16_t color, uint8_t alpha)
{ picoware_event("A", x1, y1, x2, y2, x3); picoware_event("a", y3, color, alpha, 0, 0); }
void lcd_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2,
              uint16_t color)
{ picoware_event("L", x1, y1, x2, y2, color); }
void lcd_pixel(uint16_t x, uint16_t y, uint16_t color)
{ picoware_event("P", x, y, color, 0, 0); }
void lcd_rectangle(uint16_t x, uint16_t y, uint16_t width,
                   uint16_t height, uint16_t color)
{ picoware_event("r", x, y, width, height, color); }
void lcd_text(uint16_t x, uint16_t y, const char *text, uint16_t color)
{ picoware_text(x, y, text, color, 2); }
void lcd_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2,
                  uint16_t x3, uint16_t y3, uint16_t color)
{ picoware_event("t", x1, y1, x2, y2, x3); picoware_event("u", y3, color, 0, 0, 0); }
void lcd_swap(void)
{ picoware_event("S", 0, 0, 0, 0, 0); }

int screen_width(void) { return 320; }
int screen_height(void) { return 320; }
void wfi(void) { usleep(0); }
void sleep_ms(int value) { if (value > 0) usleep((useconds_t)value * 1000); }
void sleep_us(int value) { if (value > 0) usleep((useconds_t)value); }
uint32_t time_us_32(void)
{
    struct timeval now;
    gettimeofday(&now, NULL);
    return (uint32_t)(now.tv_sec * 1000000UL + now.tv_usec);
}
uint32_t get_rand_32(void)
{ return ((uint32_t)rand() << 16) ^ (uint32_t)rand(); }

#define main picoware_user_main
#include "user.c"
#undef main

int main(void)
{
    int result;
    FILE *status;
    picoware_events = fopen(EVENT_FILE, "wb");
    result = picoware_user_main();
    if (picoware_events)
        fclose(picoware_events);
    status = fopen(RESULT_FILE, "w");
    if (!status)
        return 2;
    fprintf(status, "%d\n", result);
    fclose(status);
    return 0;
}
'''.replace("EVENT_FILE", _c_string(event_path)).replace("RESULT_FILE", _c_string(result_path))


def _decode_hex(value):
    if not value:
        return b""
    out = bytearray()
    for index in range(0, len(value), 2):
        out.append(int(value[index : index + 2], 16))
    return bytes(out)


def _lcd_object():
    display = sim_runtime.get_lcd()
    if display is not None:
        return display
    import lcd

    return lcd.LCD()


def _apply_events(path):
    display = _lcd_object()
    with open(path, "r") as handle:
        for line in handle:
            fields = line.strip().split(" ")
            if not fields:
                continue
            op = fields[0]
            if op == "T":
                values = [int(value) for value in fields[1:5]]
            else:
                values = [int(value) for value in fields[1:] if value]
            if op == "F":
                display._clear(values[0])
            elif op == "P":
                display._pixel(values[0], values[1], values[2])
            elif op == "L":
                display._line(values[0], values[1], values[2], values[3], values[4])
            elif op == "r":
                display._rectangle(values[0], values[1], values[2], values[3], values[4])
            elif op == "R":
                display._fill_rectangle(values[0], values[1], values[2], values[3], values[4])
            elif op == "O":
                display._circle(values[0], values[1], values[2], values[3])
            elif op == "o":
                display._fill_circle(values[0], values[1], values[2], values[3])
            elif op == "Q":
                pending_round = values
            elif op == "q":
                display._fill_round_rectangle(
                    pending_round[0], pending_round[1], pending_round[2],
                    pending_round[3], pending_round[4], values[0]
                )
            elif op == "Y":
                pending_triangle = values
            elif op == "y":
                display._fill_triangle(
                    pending_triangle[0], pending_triangle[1], pending_triangle[2],
                    pending_triangle[3], pending_triangle[4], values[0], values[1]
                )
            elif op == "A":
                pending_alpha = values
            elif op == "a":
                display._fill_triangle_alpha(
                    pending_alpha[0], pending_alpha[1], pending_alpha[2],
                    pending_alpha[3], pending_alpha[4], values[0], values[1], values[2]
                )
            elif op == "t":
                pending_triangle = values
            elif op == "u":
                display._triangle(
                    pending_triangle[0], pending_triangle[1], pending_triangle[2],
                    pending_triangle[3], pending_triangle[4], values[0], values[1]
                )
            elif op == "C":
                display._char(values[0], values[1], chr(values[2]), values[3])
            elif op == "T":
                text = _decode_hex(fields[5] if len(fields) > 5 else "").decode("utf-8")
                display._text(values[0], values[1], text, values[2], values[3])
            elif op == "S":
                display.swap()


def _source_for_path(path):
    source = sim_runtime.host_path(path)
    try:
        os.stat(source)
        return source
    except OSError:
        mapped = sim_runtime.app_source_path(path)
        if mapped:
            try:
                os.stat(mapped)
                return mapped
            except OSError:
                pass
    raise OSError("C source file not found: " + str(path))


def run_source(source):
    if isinstance(source, bytes):
        source = source.decode("utf-8")
    if not isinstance(source, str):
        raise TypeError("C source must be text or bytes")

    stamp = 0
    try:
        from utime import ticks_ms

        stamp = ticks_ms()
    except (ImportError, AttributeError):
        stamp = 0
    work = "/tmp/picoware-c-{}-{}".format(stamp, id(source))
    _mkdir(work)
    event_path = work + "/events.log"
    result_path = work + "/result.txt"
    compile_log = work + "/compile.log"
    run_log = work + "/run.log"
    try:
        _write(work + "/user.c", source)
        _write(work + "/runner.c", _runner_source(event_path, result_path))
        compile_command = (
            "/usr/bin/cc -std=gnu99 -O0 -Wno-unused-parameter -I "
            + _quote(work)
            + " -o "
            + _quote(work + "/program")
            + " "
            + _quote(work + "/runner.c")
            + " -lm >"
            + _quote(compile_log)
            + " 2>&1"
        )
        if os.system(compile_command) != 0:
            detail = _read(compile_log) if _exists(compile_log) else ""
            raise RuntimeError("host C compilation failed\n" + detail)
        run_command = (
            "cd "
            + _quote(sim_runtime.sd_root)
            + " && timeout 20s "
            + _quote(work + "/program")
            + " >"
            + _quote(run_log)
            + " 2>&1"
        )
        if os.system(run_command) != 0:
            detail = _read(run_log) if _exists(run_log) else ""
            raise RuntimeError("host C program failed\n" + detail)
        if _exists(run_log):
            output = _read(run_log)
            if output:
                print(output, end="")
        if _exists(event_path):
            _apply_events(event_path)
        if not _exists(result_path):
            raise RuntimeError("host C program did not return a result")
        return int(_read(result_path).strip())
    finally:
        _remove_tree(work)


class C:
    """Execute Picoware C source using the host compiler and simulator LCD."""

    def __init__(self):
        self.is_initialized = True

    def __del__(self):
        self.is_initialized = False

    def run(self, c_code):
        return run_source(c_code)

    def exec(self, path):
        return run_source(_read(_source_for_path(path)))


__all__ = ["C", "run_source"]
