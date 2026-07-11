import picoware_keyboard


def init():
    return picoware_keyboard.init()


def deinit():
    return picoware_keyboard.deinit()


def poll():
    return picoware_keyboard.poll()


def key_available():
    return picoware_keyboard.key_available()


def get_key():
    return picoware_keyboard.get_key()


def get_key_nonblocking():
    return picoware_keyboard.get_key_nonblocking()
