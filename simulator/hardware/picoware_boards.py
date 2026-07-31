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
BOARD_WAVESHARE_2_06 = 10
BOARD_PANCAKE = 11
BOARD_FLIPPER_ZERO = 12
BOARD_V8 = 13

_BOARD_NAMES = (
    "PicoCalc - Pico",
    "PicoCalc - Pico W",
    "PicoCalc - Pico 2",
    "PicoCalc - Pico 2 W",
    "Waveshare 1.28",
    "Waveshare 1.43",
    "Waveshare 3.49",
    "PicoCalc - Pimoroni 2 W",
    "CrowPanel 10.1",
    "Cardputer",
    "Waveshare 2.06",
    "Pancake",
    "Flipper Zero",
    "V8",
)

_DISPLAY_SIZES = (
    (320, 320),
    (320, 320),
    (320, 320),
    (320, 320),
    (240, 240),
    (466, 466),
    (172, 640),
    (320, 320),
    (1024, 600),
    (240, 135),
    (410, 502),
    (320, 480),
    (128, 64),
    (240, 320),
)

try:
    import sim_runtime
    _name = str(sim_runtime.board).lower().replace("_", "-")
except Exception:
    _name = "picocalc-pico2w"

if _name == "picocalc-pico":
    BOARD_ID = BOARD_PICOCALC_PICO
elif _name == "picocalc-picow":
    BOARD_ID = BOARD_PICOCALC_PICOW
elif _name == "picocalc-pico2":
    BOARD_ID = BOARD_PICOCALC_PICO_2
elif _name in ("waveshare-1.28-rp2350", "waveshare-1-28-rp2350", "waveshare-128-rp2350"):
    BOARD_ID = BOARD_WAVESHARE_1_28_RP2350
elif _name in ("waveshare-1.43-rp2350", "waveshare-1-43-rp2350", "waveshare-143-rp2350"):
    BOARD_ID = BOARD_WAVESHARE_1_43_RP2350
elif _name in ("waveshare-3.49-rp2350", "waveshare-3-49-rp2350", "waveshare-349-rp2350"):
    BOARD_ID = BOARD_WAVESHARE_3_49_RP2350
elif _name in ("picocalc-pimoroni-2w", "pimoroni-2w"):
    BOARD_ID = BOARD_PICOCALC_PIMORONI_2W
elif _name in ("crowpanel-10.1", "crowpanel-10-1", "crowpanel"):
    BOARD_ID = BOARD_CROWPANEL_10_1
elif _name == "cardputer":
    BOARD_ID = BOARD_CARDPUTER
elif _name in ("waveshare-2.06-esp32s3", "waveshare-2-06-esp32s3", "waveshare-206-esp32s3", "waveshare-2.06"):
    BOARD_ID = BOARD_WAVESHARE_2_06
elif _name == "pancake":
    BOARD_ID = BOARD_PANCAKE
elif _name == "v8":
    BOARD_ID = BOARD_V8
elif _name in ("flipper-zero", "flipper"):
    BOARD_ID = BOARD_FLIPPER_ZERO
else:
    BOARD_ID = BOARD_PICOCALC_PICO_2W

BOARD_HAS_PSRAM = 1 if BOARD_ID in (BOARD_PICOCALC_PICO_2, BOARD_PICOCALC_PICO_2W, BOARD_PICOCALC_PIMORONI_2W) else 0
BOARD_HAS_SD = 0 if BOARD_ID in (BOARD_WAVESHARE_1_28_RP2350, BOARD_CROWPANEL_10_1) else 1
BOARD_HAS_TOUCH = 1 if BOARD_ID in (BOARD_WAVESHARE_1_28_RP2350, BOARD_WAVESHARE_1_43_RP2350, BOARD_WAVESHARE_3_49_RP2350, BOARD_CROWPANEL_10_1, BOARD_WAVESHARE_2_06, BOARD_PANCAKE, BOARD_V8) else 0
BOARD_HAS_WIFI = 1 if BOARD_ID in (BOARD_PICOCALC_PICOW, BOARD_PICOCALC_PICO_2W, BOARD_PICOCALC_PIMORONI_2W, BOARD_CARDPUTER, BOARD_WAVESHARE_2_06, BOARD_PANCAKE, BOARD_V8) else 0
BOARD_HAS_AUDIO = 1 if BOARD_ID in (BOARD_PICOCALC_PICO, BOARD_PICOCALC_PICOW, BOARD_PICOCALC_PICO_2, BOARD_PICOCALC_PICO_2W, BOARD_PICOCALC_PIMORONI_2W) else 0
BOARD_HAS_RP2040 = 1 if BOARD_ID in (BOARD_PICOCALC_PICO, BOARD_PICOCALC_PICOW) else 0
BOARD_HAS_RP2350 = 1 if BOARD_ID in (BOARD_PICOCALC_PICO_2, BOARD_PICOCALC_PICO_2W, BOARD_WAVESHARE_1_28_RP2350, BOARD_WAVESHARE_1_43_RP2350, BOARD_WAVESHARE_3_49_RP2350, BOARD_PICOCALC_PIMORONI_2W) else 0
BOARD_HAS_ESP32 = 1 if BOARD_ID in (BOARD_CROWPANEL_10_1, BOARD_CARDPUTER, BOARD_WAVESHARE_2_06, BOARD_PANCAKE, BOARD_V8) else 0


def _valid_board_id(board_id):
    return 0 <= int(board_id) < len(_BOARD_NAMES)


def get_device_name():
    """Return the human-readable device name."""
    if BOARD_ID == BOARD_FLIPPER_ZERO:
        return "Flipper Zero STM32WB55RG"
    if BOARD_ID == BOARD_CROWPANEL_10_1:
        return "CrowPanel 10.1 ESP32-P4"
    if BOARD_ID in (BOARD_PANCAKE, BOARD_V8):
        return "ESP32-C5"
    if BOARD_ID in (BOARD_CARDPUTER, BOARD_WAVESHARE_2_06):
        return "ESP32-S3"
    if BOARD_ID == BOARD_PICOCALC_PIMORONI_2W:
        return "Pimoroni Pico Plus 2 W"
    if BOARD_ID in (BOARD_PICOCALC_PICOW, BOARD_PICOCALC_PICO_2W):
        return "Raspberry Pi Pico W" if BOARD_HAS_RP2040 else "Raspberry Pi Pico 2 W"
    return "Raspberry Pi Pico" if BOARD_HAS_RP2040 else "Raspberry Pi Pico 2"


def get_current_name():
    """Return the full simulator device name."""
    return get_name(BOARD_ID)


def get_name(board_id):
    """Return the firmware board name for *board_id*."""
    return _BOARD_NAMES[int(board_id)] if _valid_board_id(board_id) else "Unknown Board"


def get_display_size(board_id):
    """Return the native display size for *board_id*."""
    return _DISPLAY_SIZES[int(board_id)] if _valid_board_id(board_id) else (0, 0)


def get_current_display_size():
    """Return the native display size for the selected simulator board."""
    return get_display_size(BOARD_ID)


def is_circular(board_id):
    """Return True if the board has a circular display."""
    return int(board_id) in (
        BOARD_WAVESHARE_1_28_RP2350,
        BOARD_WAVESHARE_1_43_RP2350,
        BOARD_WAVESHARE_2_06,
    )


def has_psram(board_id=None):
    """Return True if the board has PSRAM."""
    selected = BOARD_ID if board_id is None else int(board_id)
    return selected in (
        BOARD_PICOCALC_PICO_2,
        BOARD_PICOCALC_PICO_2W,
        BOARD_PICOCALC_PIMORONI_2W,
    )


def has_sd_card(board_id):
    """Return True if *board_id* has SD storage."""
    return int(board_id) not in (
        BOARD_WAVESHARE_1_28_RP2350,
        BOARD_CROWPANEL_10_1,
    )


def has_touch(board_id):
    """Return True if *board_id* has touch input."""
    return int(board_id) in (
        BOARD_WAVESHARE_1_28_RP2350,
        BOARD_WAVESHARE_1_43_RP2350,
        BOARD_WAVESHARE_3_49_RP2350,
        BOARD_CROWPANEL_10_1,
        BOARD_WAVESHARE_2_06,
        BOARD_PANCAKE,
        BOARD_V8,
    )


def has_wifi(board_id):
    """Return True if *board_id* has Wi-Fi."""
    return int(board_id) in (
        BOARD_PICOCALC_PICOW,
        BOARD_PICOCALC_PICO_2W,
        BOARD_PICOCALC_PIMORONI_2W,
        BOARD_CARDPUTER,
        BOARD_WAVESHARE_2_06,
        BOARD_PANCAKE,
        BOARD_V8,
    )


def has_audio(board_id):
    """Return True if *board_id* has audio support."""
    return int(board_id) in (
        BOARD_PICOCALC_PICO,
        BOARD_PICOCALC_PICOW,
        BOARD_PICOCALC_PICO_2,
        BOARD_PICOCALC_PICO_2W,
        BOARD_PICOCALC_PIMORONI_2W,
    )
