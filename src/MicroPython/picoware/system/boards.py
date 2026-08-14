"""Board constants for Picoware.

Attributes:
    BOARD_PICOCALC_PICO (int): Board ID for PicoCalc with a Raspberry Pi Pico.
    BOARD_PICOCALC_PICOW (int): Board ID for PicoCalc with a Raspberry Pi Pico W.
    BOARD_PICOCALC_PICO_2 (int): Board ID for PicoCalc with a Raspberry Pi Pico 2.
    BOARD_PICOCALC_PICO_2W (int): Board ID for PicoCalc with a Raspberry Pi Pico 2 W.
    BOARD_WAVESHARE_1_28_RP2350 (int): Board ID for Waveshare 1.28" RP2350.
    BOARD_WAVESHARE_1_43_RP2350 (int): Board ID for Waveshare 1.43" RP2350.
    BOARD_WAVESHARE_1_69_RP2350 (int): Board ID for Waveshare 1.69" RP2350.
    BOARD_WAVESHARE_3_49_RP2350 (int): Board ID for Waveshare 3.49" RP2350.
    BOARD_PICOCALC_PIMORONI_2W (int): Board ID for PicoCalc with a Pimoroni 2 W.
    BOARD_CROWPANEL_10_1 (int): Board ID for CrowPanel 10.1.
    BOARD_CARDPUTER (int): Board ID for Cardputer.
    BOARD_WAVESHARE_2_06 (int): Board ID for Waveshare 2.06.
    BOARD_PANCAKE (int): Board ID for Pancake.
    BOARD_V8 (int): Board ID for V8.
    BOARD_FLIPPER_ZERO (int): Board ID for Flipper Zero.
    BOARD_DESKTOP (int): Board ID for the Unix Desktop target.
    BOARD_ID (int): The current board ID.
    BOARD_HAS_PSRAM (bool): True if the board has an external PSRAM, False otherwise.
    BOARD_HAS_SD (bool): True if the board has an SD card, False otherwise.
    BOARD_HAS_TOUCH (bool): True if the board has a touch screen, False otherwise.
    BOARD_HAS_WIFI (bool): True if the board has Wi-Fi, False otherwise.
    BOARD_HAS_AUDIO (bool): True if the board has audio capabilities, False otherwise.
    BOARD_HAS_RP2040 (bool): True if the board uses an RP2040 microcontroller, False otherwise.
    BOARD_HAS_RP2350 (bool): True if the board uses an RP2350 microcontroller, False otherwise.
    BOARD_HAS_ESP32 (bool): True if the board uses an ESP32 microcontroller, False otherwise.
    BOARD_HAS_PICOCALC (bool): True if the board is a PicoCalc board, False otherwise.
"""


import picoware_boards

BOARD_PICOCALC_PICO = picoware_boards.BOARD_PICOCALC_PICO
BOARD_PICOCALC_PICOW = picoware_boards.BOARD_PICOCALC_PICOW
BOARD_PICOCALC_PICO_2 = picoware_boards.BOARD_PICOCALC_PICO_2
BOARD_PICOCALC_PICO_2W = picoware_boards.BOARD_PICOCALC_PICO_2W
BOARD_WAVESHARE_1_28_RP2350 = picoware_boards.BOARD_WAVESHARE_1_28_RP2350
BOARD_WAVESHARE_1_43_RP2350 = picoware_boards.BOARD_WAVESHARE_1_43_RP2350
BOARD_WAVESHARE_1_69_RP2350 = picoware_boards.BOARD_WAVESHARE_1_69_RP2350
BOARD_WAVESHARE_3_49_RP2350 = picoware_boards.BOARD_WAVESHARE_3_49_RP2350
BOARD_PICOCALC_PIMORONI_2W = picoware_boards.BOARD_PICOCALC_PIMORONI_2W
BOARD_CROWPANEL_10_1 = picoware_boards.BOARD_CROWPANEL_10_1
BOARD_CARDPUTER = picoware_boards.BOARD_CARDPUTER
BOARD_WAVESHARE_2_06 = picoware_boards.BOARD_WAVESHARE_2_06
BOARD_PANCAKE = picoware_boards.BOARD_PANCAKE
BOARD_V8 = picoware_boards.BOARD_V8
BOARD_FLIPPER_ZERO = picoware_boards.BOARD_FLIPPER_ZERO
BOARD_DESKTOP = picoware_boards.BOARD_DESKTOP

BOARD_ID = picoware_boards.BOARD_ID
BOARD_HAS_PSRAM = picoware_boards.BOARD_HAS_PSRAM
BOARD_HAS_SD = picoware_boards.BOARD_HAS_SD
BOARD_HAS_TOUCH = picoware_boards.BOARD_HAS_TOUCH
BOARD_HAS_WIFI = picoware_boards.BOARD_HAS_WIFI
BOARD_HAS_AUDIO = picoware_boards.BOARD_HAS_AUDIO
BOARD_HAS_RP2040 = picoware_boards.BOARD_HAS_RP2040
BOARD_HAS_RP2350 = picoware_boards.BOARD_HAS_RP2350
BOARD_HAS_ESP32 = picoware_boards.BOARD_HAS_ESP32
BOARD_HAS_PICOCALC = picoware_boards.BOARD_HAS_PICOCALC
