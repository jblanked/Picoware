"""CPython tests for dependency patching and portable System Info rendering."""
from pathlib import Path
import importlib.util
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PREPARE = ROOT / "tools/prepare-pimoroni-psram.py"
CONTEXT = """    // Initialise stack extents and GC heap.
    mp_cstack_init_with_top(&__StackTop, &__StackTop - &__StackBottom);

    #if MICROPY_HW_ENABLE_PSRAM
    size_t psram_size = psram_get_size(); // 0 if PSRAM was not brought up
    if (psram_size) {
        // Use PSRAM from the end of any __in_psram data up to the top of the chip.
"""


class HeapPatchTests(unittest.TestCase):
    def test_patch_is_idempotent_and_retains_original_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = Path(tmp) / "ports/rp2/main.c"
            main.parent.mkdir(parents=True)
            original = "// prefix\n" * 146 + CONTEXT + "// suffix\n"
            main.write_text(original)
            for _ in range(2):
                subprocess.run([sys.executable, str(PREPARE), tmp], check=True, capture_output=True)
            result = main.read_text()
            self.assertEqual(result.count("#if defined(PICOWARE_SRAM_ONLY_GC)"), 1)
            self.assertIn("#elif MICROPY_HW_ENABLE_PSRAM", result)
            self.assertTrue(result.endswith("// suffix\n"))
            # The patch is reversible with git apply; no unrelated edits are introduced.
            subprocess.run(["git", "-C", tmp, "apply", "-R", str(ROOT / "tools/patches/rp2-sram-only-gc.patch")], check=True)
            self.assertEqual(main.read_text(), original)

    def test_original_hardware_tested_branch_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = Path(tmp) / "ports/rp2/main.c"
            main.parent.mkdir(parents=True)
            original = CONTEXT.replace(
                "#if MICROPY_HW_ENABLE_PSRAM", "#if defined(PICOWARE_SRAM_ONLY_GC) && PICOWARE_SRAM_ONLY_GC\n"
                "    \t// Keep MicroPython's garbage-collected heap in internal SRAM.\n"
                "    \tgc_init(&__GcHeapStart, &__GcHeapEnd);\n"
                "    #elif MICROPY_HW_ENABLE_PSRAM"
            )
            main.write_text(original)
            subprocess.run([sys.executable, str(PREPARE), tmp], check=True, capture_output=True)
            self.assertEqual(main.read_text(), original)

    def test_unknown_source_is_not_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = Path(tmp) / "ports/rp2/main.c"
            main.parent.mkdir(parents=True)
            for original in ("unrelated source\n", "#define PICOWARE_SRAM_ONLY_GC 1\n"):
                main.write_text(original)
                result = subprocess.run([sys.executable, str(PREPARE), tmp], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(main.read_text(), original)


class SystemInfoTests(unittest.TestCase):
    def render(self, native):
        fake_system = types.ModuleType("picoware.system.system")
        fake_system.System = lambda: types.SimpleNamespace(
            board_name="board", device_name="device", freq=210,
            free_heap=1, used_heap=2, total_heap=3,
            free_psram=8384512, used_psram=4096, total_psram=8388608,
            free_flash=4, used_flash=5, total_flash=9,
        )
        spec = importlib.util.spec_from_file_location(
            "system_info_under_test", ROOT / "src/MicroPython/picoware/applications/system/system_info.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        captured = []
        module._system_info = types.SimpleNamespace(set_text=captured.append)
        view = types.SimpleNamespace(battery=types.SimpleNamespace(percentage=99, has_voltage=False))
        with patch.dict(sys.modules, {"picoware.system.system": fake_system, "pimoram": native}):
            getattr(module, "__set_text")(view)
        return captured[0]

    def test_non_pimoroni_layout_stays_generic(self):
        output = self.render(None)
        self.assertIn("Free PSRAM:", output)
        self.assertNotIn("Pimoroni PSRAM", output)
        self.assertNotIn("PicoCalc PSRAM", output)

    def test_onboard_stats_are_separate_and_allocate_no_buffers(self):
        native = types.SimpleNamespace(available=lambda: True, total=lambda: 8388608, free=lambda: 8384512)
        output = self.render(native)
        self.assertIn("Free PicoCalc PSRAM:", output)
        self.assertIn("Pimoroni PSRAM (pimoram)", output)
        self.assertIn("Used/reserved: 4096 bytes", output)

    def test_missing_chip_does_not_break_display(self):
        output = self.render(types.SimpleNamespace(available=lambda: False))
        self.assertIn("Pimoroni PSRAM (pimoram): unavailable", output)


if __name__ == "__main__":
    unittest.main()
