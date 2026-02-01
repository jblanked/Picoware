from gc import collect

_textbox = None
_log_text = ""
_psram = None
_test_index = 0


def log(text):
    """Helper to append text to the log"""
    global _log_text
    _log_text += str(text) + "\n"
    if _textbox:
        _textbox.current_line += 4  # Auto-scroll a bit
        _textbox.set_text(_log_text)


def test_manual_del():
    if not _psram:
        return
    log("=== Test 1: Manual del ===")
    log(f"free before: {_psram.mem_free()}")
    data = _psram.malloc("hello")
    log(f"Created: {data}")
    log(f"Has del: {hasattr(data, '__del__')}")
    if hasattr(data, "__del__"):
        log("Calling __del__...")
        data.__del__()
    log(f"free after: {_psram.mem_free()}\n")


def test_gc_collect():
    if not _psram:
        return
    log("=== Test 2: GC collect ===")
    log(f"free before: {_psram.mem_free()}")

    data = _psram.malloc("world")
    log(f"Created: {data}")
    log(f"free: {_psram.mem_free()}")

    data += "test"
    log(str(data))

    data += "-new"
    log(str(data))

    del data
    log("Deleted reference")
    log(f"free before gc: {_psram.mem_free()}")

    log("Calling collect()...")
    collect()
    log(f"free after gc: {_psram.mem_free()}\n")


def test_scope():
    if not _psram:
        return
    log("=== Test 3: Scope exit ===")
    log(f"free before: {_psram.mem_free()}")

    def create_temp():
        temp = _psram.malloc("temporary")
        log(f"Created temp: {temp}")
        log(f"free: {_psram.mem_free()}")
        return None

    create_temp()
    log("Exited function scope")
    log(f"free before gc: {_psram.mem_free()}")
    collect()
    log(f"free after gc: {_psram.mem_free()}\n")


def test_threshold():
    if not _psram:
        return
    log("=== Test 4: Multiple alloc ===")
    log(f"free before: {_psram.mem_free()}")

    for i in range(25000):
        _psram.malloc(f"object_{i}")

    log(f"free w/ 25000: {_psram.mem_free()}")
    log(f"free before gc: {_psram.mem_free()}")
    collect()
    _psram.collect()
    log(f"free after gc: {_psram.mem_free()}\n")


def test_dict():
    if not _psram:
        return
    log("=== Test 5: Dictionary ===")
    log(f"free before: {_psram.mem_free()}")

    data_dict = _psram.malloc({"key1": "value1", "key2": 123})
    log(f"Created dict: {data_dict}")
    log(f"free: {_psram.mem_free()}")

    del data_dict
    log("Deleted dict ref")
    collect()
    log(f"free after gc: {_psram.mem_free()}\n")


def test_boolean():
    if not _psram:
        return
    log("=== Test 6: Boolean ===")
    log(f"free before: {_psram.mem_free()}")

    data_bool = _psram.malloc(True)
    log(f"Created bool: {data_bool}")
    log(f"free: {_psram.mem_free()}")

    del data_bool
    log("Deleted bool ref")
    collect()
    log(f"free after gc: {_psram.mem_free()}\n")


def random_func():
    log("random started!!")
    import random

    num = random.randint(1, 10)
    for i in range(num):
        log(str(i))


def test_function():
    if not _psram:
        return
    log("=== Test 7: Function ===")
    log(f"free before: {_psram.mem_free()}")

    func_obj = _psram.malloc(random_func)
    log(f"Created func: {func_obj}")
    log(f"free: {_psram.mem_free()}")

    # func_obj() would run it
    log("Function stored")

    del func_obj
    log("Deleted func ref")
    collect()
    log(f"free after gc: {_psram.mem_free()}\n")


def test_list():
    if not _psram:
        return
    log("=== Test 8: List ===")
    log(f"free before: {_psram.mem_free()}")

    _list = []
    for i in range(50):
        _list.append(i)

    data_list = _psram.malloc(_list)
    log(f"Created list: len {len(data_list)}")
    log(f"free: {_psram.mem_free()}")

    log(f"list[2]: {data_list[2]}")

    del data_list
    log("Deleted list ref")
    collect()
    log(f"free after gc: {_psram.mem_free()}\n")


def test_tuple():
    if not _psram:
        return
    log("=== Test 9: Tuple ===")
    log(f"free before: {_psram.mem_free()}")

    data_tuple = _psram.malloc((1, 2, 3, 4, 5))
    log(f"Created tuple: {data_tuple}")
    log(f"free: {_psram.mem_free()}")

    log(f"tuple[3]: {data_tuple[3]}")

    del data_tuple
    log("Deleted tuple ref")
    collect()
    log(f"free after gc: {_psram.mem_free()}\n")


def final_cleanup():
    if not _psram:
        return
    log("")
    log("=== Final cleanup ===")
    collect()
    _psram.collect()
    log(f"Final free: {_psram.mem_free()}")

    log("")
    log("Use UP/DOWN to scroll")
    log("Press BACK to exit")


def start(view_manager) -> bool:
    """Initialize PSRAM and run tests"""
    if not view_manager.has_psram:
        view_manager.alert("PSRAM not available...")
        return False

    global _textbox, _log_text, _psram, _test_index
    from picoware.gui.textbox import TextBox
    from picoware.system.psram import PSRAM

    _psram = PSRAM()

    draw = view_manager.draw
    draw.fill_screen()

    # Create TextBox for scrollable output
    _textbox = TextBox(draw, 0, draw.size.y)
    _log_text = ""
    _test_index = 0

    log("Starting PSRAM tests...")
    return _psram is not None


def run(view_manager) -> None:
    """Handle input"""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_UP, BUTTON_DOWN

    global _test_index

    inp = view_manager.input_manager

    if inp.button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
    elif inp.button == BUTTON_UP:
        inp.reset()
        if _textbox:
            _textbox.scroll_up()
    elif inp.button == BUTTON_DOWN:
        inp.reset()
        if _textbox:
            _textbox.scroll_down()

    if _test_index >= 10:
        return  # all tests done

    func_map = {
        0: test_manual_del,
        1: test_gc_collect,
        2: test_scope,
        3: test_threshold,
        4: test_dict,
        5: test_boolean,
        6: test_function,
        7: test_list,
        8: test_tuple,
        9: final_cleanup,
    }

    func_map.get(_test_index)()
    _test_index += 1


def stop(view_manager) -> None:
    """Cleanup PSRAM resources"""
    global _textbox, _log_text, _psram, _test_index
    if _textbox:
        del _textbox
        _textbox = None
    if _psram:
        del _psram
        _psram = None
    _log_text = ""
    _test_index = 0
    collect()
