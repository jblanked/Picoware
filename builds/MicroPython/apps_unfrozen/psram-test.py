_psram = None


def start(view_manager) -> bool:
    """Initialize PSRAM and run tests"""
    global _psram
    from picoware.system.psram import PSRAM
    from picoware.system.vector import Vector

    _psram = PSRAM()

    draw = view_manager.get_draw()
    draw.fill_screen()

    # Display PSRAM info
    draw.text(Vector(10, 10), "PSRAM Test")
    draw.text(Vector(10, 30), f"Total: {_psram.total_size // 1024}KB")
    draw.text(Vector(10, 50), f"Ready: {_psram.is_ready}")
    draw.swap()

    test_addr = 0x200000

    # Write test data directly to PSRAM
    test_data = b"PSRAM Test"
    _psram.write(test_addr, test_data)

    draw.text(Vector(10, 90), "Data written")

    # Read back and verify
    read_data = _psram.read(test_addr, len(test_data))

    match = read_data == test_data
    draw.text(Vector(10, 110), f"Read: {read_data}")
    draw.text(Vector(10, 130), f"Match: {match}")

    # Test write/read with different data types
    _psram.write32(test_addr + 100, 0xDEADBEEF)
    value = _psram.read32(test_addr + 100)
    draw.text(Vector(10, 150), f"32-bit: 0x{value:X}")

    draw.text(Vector(10, 180), "Press BACK to exit")
    draw.swap()

    return True


def run(view_manager) -> None:
    """Handle input"""
    from picoware.system.buttons import BUTTON_BACK

    inp = view_manager.get_input_manager()
    if inp.button == BUTTON_BACK:
        inp.reset()
        view_manager.back()


def stop(view_manager) -> None:
    """Cleanup PSRAM resources"""
    global _psram
    from gc import collect

    if _psram:
        del _psram
        _psram = None
    collect()
