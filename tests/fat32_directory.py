"""Run the real FAT32 driver against a host-only disk; no device is accessed."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="fat32-directory-") as work:
    work = Path(work)
    (work / "pico").mkdir()
    (work / "pico/stdlib.h").write_text("#include <stdint.h>\n#include <stdbool.h>\n")
    (work / "pico/mutex.h").write_text("#define auto_init_recursive_mutex(name) int name\n#define recursive_mutex_enter_blocking(p) ((void)(p))\n#define recursive_mutex_exit(p) ((void)(p))\n")
    (work / "pico/aon_timer.h").write_text("#include <stdbool.h>\n#include <time.h>\nstatic inline bool aon_timer_get_time_calendar(struct tm *t) {(void)t;return false;}\n")
    executable = work / "test"
    subprocess.run(["cc", "-std=gnu11", "-O1", "-g", "-fsanitize=address,undefined", "-I", str(work), str(root / "tests/native/fat32_directory.c"), "-o", str(executable)], check=True)
    subprocess.run([str(executable)], check=True)
