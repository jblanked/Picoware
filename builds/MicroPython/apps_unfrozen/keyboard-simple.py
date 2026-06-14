# picoware/apps/keyboard-simple.py


def __callback(result: str):
    """Optional callback"""

    # do something with the result
    print(result)


def start(view_manager) -> bool:
    """Start the app"""

    view_manager.input_manager.reset()  # reset input manager to clear any previous input state

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

    button = view_manager.button
    kb = view_manager.keyboard

    if button == BUTTON_BACK or not kb.run():
        view_manager.back()
    elif kb.is_finished:
        result: str = kb.response
        print("Final result:", result)
        view_manager.back()


def stop(view_manager) -> None:
    """Stop the app"""

    from gc import collect

    kb = view_manager.keyboard

    # reset for next use
    kb.reset()

    collect()
