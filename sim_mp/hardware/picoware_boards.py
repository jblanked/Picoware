BOARD_PICOCALC_PICO = 0
BOARD_PICOCALC_PICOW = 1
BOARD_PICOCALC_PICO_2 = 2
BOARD_PICOCALC_PICO_2W = 3
BOARD_WAVESHARE_1_28_RP2350 = 4
BOARD_WAVESHARE_1_43_RP2350 = 5
BOARD_WAVESHARE_3_49_RP2350 = 6
BOARD_PICOCALC_PIMORONI_2W = 7
BOARD_CROWPANEL_10_1 = 8
BOARD_CARDPUTER = 9

try:
    import sim_runtime
    _name = sim_runtime.board
except Exception:
    _name = "picocalc-pico2w"

if _name == "picocalc-pico":
    BOARD_ID = BOARD_PICOCALC_PICO
elif _name == "picocalc-picow":
    BOARD_ID = BOARD_PICOCALC_PICOW
elif _name == "picocalc-pico2":
    BOARD_ID = BOARD_PICOCALC_PICO_2
else:
    BOARD_ID = BOARD_PICOCALC_PICO_2W

BOARD_HAS_PSRAM = 1 if BOARD_ID in (BOARD_PICOCALC_PICO_2, BOARD_PICOCALC_PICO_2W, BOARD_PICOCALC_PIMORONI_2W) else 0
BOARD_HAS_SD = 1
BOARD_HAS_TOUCH = 0
BOARD_HAS_WIFI = 1 if BOARD_ID in (BOARD_PICOCALC_PICOW, BOARD_PICOCALC_PICO_2W) else 0
BOARD_HAS_AUDIO = 1


def get_device_name():
    """Return the human-readable device name."""
    return "Simulator"


def get_current_name():
    """Return the full simulator device name."""
    return "Simulator"


def is_circular(board_id):
    """Return True if the board has a circular display."""
    return False


def has_psram(board_id=None):
    """Return True if the board has PSRAM."""
    return BOARD_HAS_PSRAM == 1
