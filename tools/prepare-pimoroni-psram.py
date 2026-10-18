#!/usr/bin/env python3
"""Apply Picoware's narrowly scoped RP2 SRAM-heap option to MicroPython.

The branch only takes effect for boards defining PICOWARE_SRAM_ONLY_GC.
Already-patched checkouts (including the original hardware-tested variant) are
accepted without rewriting. Unknown source layouts fail before a build starts.
"""
from pathlib import Path
import re
import subprocess
import sys


def prepare(root):
    root = Path(root).resolve()
    main = root / "ports/rp2/main.c"
    if not main.is_file():
        raise SystemExit("MicroPython RP2 source not found: " + str(main))
    source = main.read_text()
    branch = re.compile(
        r"#if defined\(PICOWARE_SRAM_ONLY_GC\) && PICOWARE_SRAM_ONLY_GC\n"
        r"(?:[ \t]*//[^\n]*\n)*"
        r"[ \t]*gc_init\(&__GcHeapStart, &__GcHeapEnd\);\n"
        r"[ \t]*#elif MICROPY_HW_ENABLE_PSRAM"
    )
    if len(branch.findall(source)) == 1:
        print("MicroPython RP2 SRAM-only heap option is already installed.")
        return
    if "PICOWARE_SRAM_ONLY_GC" in source:
        raise SystemExit("Unrecognized existing SRAM-only heap edit; no changes made.")
    patch = Path(__file__).resolve().parent / "patches/rp2-sram-only-gc.patch"
    command = ["git", "-C", str(root), "apply"]
    checked = subprocess.run(command + ["--check", str(patch)], capture_output=True, text=True)
    if checked.returncode:
        raise SystemExit(
            "The RP2 heap patch does not match this MicroPython version; no changes made.\n"
            + checked.stderr
        )
    subprocess.run(command + [str(patch)], check=True)
    print("Installed MicroPython RP2 SRAM-only heap option.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: prepare-pimoroni-psram.py /path/to/micropython")
    prepare(sys.argv[1])
