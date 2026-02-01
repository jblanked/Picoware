_loading = None


def start(view_manager):
    from picoware.gui.loading import Loading

    global _loading

    if not _loading:
        _loading = Loading(view_manager.draw)

    return True


def run(view_manager):

    from picoware.system.buttons import BUTTON_BACK

    inp = view_manager.input_manager
    but = inp.button

    if but == BUTTON_BACK:
        inp.reset()
        view_manager.back()
    else:
        _loading.animate()


def stop(view_manager):
    from gc import collect

    global _loading

    if _loading:
        _loading.stop()
        del _loading
        _loading = None

    collect()
