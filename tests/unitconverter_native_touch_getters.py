"""Compile the production getter bodies with a deterministic touch-controller stub.

Run with host Python. This checks C binding ordering, not physical I2C behavior.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PRELUDE = r'''
#include <assert.h>
#include <stddef.h>
typedef int mp_obj_t;
typedef struct { int x, y; } TouchVector;
static TouchVector last_touch_point = {0, 0};
static TouchVector controller = {0, 0};
static int observed[2];
static TouchVector touch_get_point(void) { return controller; }
static mp_obj_t mp_obj_new_int(int value) { return value; }
static mp_obj_t mp_obj_new_tuple(size_t count, const mp_obj_t *items) {
    assert(count == 2);
    observed[0] = items[0]; observed[1] = items[1];
    return 0;
}
#define STATIC static
'''
CHECKS = r'''
int main(void) {
    controller = (TouchVector){42, 83};
    waveshare_touch_get_touch_point();
    assert(observed[0] == 42 && observed[1] == 83);
    controller = (TouchVector){117, 199};
    waveshare_touch_get_touch_point();
    assert(observed[0] == 117 && observed[1] == 199);
    controller = (TouchVector){0, 0};
    waveshare_touch_get_touch_point();
    assert(observed[0] == 0 && observed[1] == 0);
    controller = (TouchVector){42, 83};
    waveshare_touch_get_touch_point();
    assert(observed[0] == 42 && observed[1] == 83);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='unitconverter-native-touch-') as temp:
    for board in ('1.43', '1.69', '3.49'):
        source = (ROOT / ('src/MicroPython/Waveshare/RP2350-Touch-LCD-' + board)
                  / 'waveshare_touch/waveshare_touch.c').read_text()
        start = source.index('STATIC mp_obj_t waveshare_touch_get_touch_point(void)')
        end = source.index('STATIC MP_DEFINE_CONST_FUN_OBJ_0', start)
        program = Path(temp) / ('getter-' + board + '.c')
        binary = program.with_suffix('.test')
        program.write_text(PRELUDE + source[start:end] + CHECKS)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                        str(program), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
        print('PASS production C getter: current point and release', board)
