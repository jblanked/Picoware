# Enumeration for the different board types.
BOARD_TYPE_PICO_CALC = 0
BOARD_TYPE_VGM = 1
BOARD_TYPE_JBLANKED = 2


# Enumeration for the different Pico types.
PICO_TYPE_PICO = 0  # Raspberry Pi Pico
PICO_TYPE_PICO_W = 1  # Raspberry Pi Pico W
PICO_TYPE_PICO_2 = 2  # Raspberry Pi Pico 2
PICO_TYPE_PICO_2_W = 3  # Raspberry Pi Pico 2 W


# Enumeration for the different library types.
LIBRARY_TYPE_PICO_DVI = 0
LIBRARY_TYPE_TFT = 1


class BoardPins:
    """Set of pins for the board"""

    def __init__(self, sck: int, mosi: int, miso: int, cs: int, dc: int, rst: int):
        self.sck = sck
        self.mosi = mosi
        self.miso = miso
        self.cs = cs
        self.dc = dc
        self.rst = rst


class Board:
    """Class to represent the board."""

    def __init__(
        self,
        board_type: int,
        pico_type: int,
        library_type: int,
        pins: BoardPins,
        width: int,
        height: int,
        rotation: int,
        name: str,
        has_wifi: bool,
        has_sd_card: bool,
    ):
        self.board_type = board_type
        self.pico_type = pico_type
        self.library_type = library_type
        self.pins = pins
        self.width = width
        self.height = height
        self.rotation = rotation
        self.name = name
        self.has_wifi = has_wifi
        self.has_sd_card = has_sd_card


# Define the board types
VGM_BOARD_CONFIG: Board = Board(
    board_type=BOARD_TYPE_VGM,
    pico_type=PICO_TYPE_PICO,
    library_type=LIBRARY_TYPE_PICO_DVI,
    pins=BoardPins(sck=8, mosi=11, miso=12, cs=13, dc=14, rst=15),
    width=320,
    height=240,
    rotation=0,
    name="Video Game Module",
    has_wifi=False,
    has_sd_card=False,
)

PICO_CALC_BOARD_CONFIG_PICO: Board = Board(
    board_type=BOARD_TYPE_PICO_CALC,
    pico_type=PICO_TYPE_PICO,
    library_type=LIBRARY_TYPE_TFT,
    pins=BoardPins(sck=10, mosi=11, miso=12, cs=13, dc=14, rst=15),
    width=320,
    height=320,
    rotation=0,
    name="PicoCalc - Pico",
    has_wifi=False,
    has_sd_card=True,
)

PICO_CALC_BOARD_CONFIG_PICO_W: Board = Board(
    board_type=BOARD_TYPE_PICO_CALC,
    pico_type=PICO_TYPE_PICO_W,
    library_type=LIBRARY_TYPE_TFT,
    pins=BoardPins(sck=10, mosi=11, miso=12, cs=13, dc=14, rst=15),
    width=320,
    height=320,
    rotation=0,
    name="PicoCalc - Pico W",
    has_wifi=True,
    has_sd_card=True,
)

PICO_CALC_BOARD_CONFIG_PICO_2: Board = Board(
    board_type=BOARD_TYPE_PICO_CALC,
    pico_type=PICO_TYPE_PICO_2,
    library_type=LIBRARY_TYPE_TFT,
    pins=BoardPins(sck=10, mosi=11, miso=12, cs=13, dc=14, rst=15),
    width=320,
    height=320,
    rotation=0,
    name="PicoCalc - Pico 2",
    has_wifi=False,
    has_sd_card=True,
)

PICO_CALC_BOARD_CONFIG_PICO_2W: Board = Board(
    board_type=BOARD_TYPE_PICO_CALC,
    pico_type=PICO_TYPE_PICO_2_W,
    library_type=LIBRARY_TYPE_TFT,
    pins=BoardPins(sck=10, mosi=11, miso=12, cs=13, dc=14, rst=15),
    width=320,
    height=320,
    rotation=0,
    name="PicoCalc - Pico 2 W",
    has_wifi=True,
    has_sd_card=True,
)

JBLANKED_BOARD_CONFIG: Board = Board(
    board_type=BOARD_TYPE_JBLANKED,
    pico_type=PICO_TYPE_PICO_W,
    library_type=LIBRARY_TYPE_TFT,
    pins=BoardPins(sck=6, mosi=7, miso=4, cs=5, dc=11, rst=10),
    width=320,
    height=240,
    rotation=3,
    name="JBlanked Pico",
    has_wifi=True,
    has_sd_card=False,
)
