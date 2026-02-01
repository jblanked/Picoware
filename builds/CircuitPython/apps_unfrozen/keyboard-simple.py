# picoware/apps/keyboard-simple.py


def __callback(result: str):
    """Optional callback"""

    # do something with the result
    print(result)


def start(view_manager) -> bool:
    """Start the app"""

    kb = view_manager.keyboard

    # optional set a callback
    kb.set_save_callback(__callback)

    # optionally set the initial text/response
    kb.response = ""

    # usually it waits to draw until input
    # so we force draw it first
    return kb.run(force=True)


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    inp = view_manager.input_manager
    but = inp.button
    kb = view_manager.keyboard

    if but == BUTTON_BACK or not kb.run():
        inp.reset()
        view_manager.back()


def stop(view_manager) -> None:
    """Stop the app"""

    from gc import collect

    kb = view_manager.keyboard

    # do something with the response optionally
    # if no callback is set
    result: str = kb.response

    # reset for next use
    kb.reset()

    collect()
