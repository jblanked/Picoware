"""Battery - Battery monitoring for Picoware."""
from micropython import const
from picoware.system.boards import (
    BOARD_CARDPUTER,
    BOARD_CROWPANEL_10_1,
    BOARD_CROWPANEL_WATCH_2_01,
    BOARD_ID,
    BOARD_WAVESHARE_1_28_RP2350,
    BOARD_WAVESHARE_1_43_RP2350,
    BOARD_WAVESHARE_1_69_RP2350,
    BOARD_WAVESHARE_3_49_RP2350,
    BOARD_WAVESHARE_2_06,
    BOARD_WAVESHARE_C6_2_06,
    BOARD_PANCAKE,
    BOARD_WAVESHARE_C5_3_5,
    BOARD_V8,
    BOARD_FLIPPER_ZERO,
    BOARD_PICO_DUO,
    BOARD_POOM
)

CUTOFF_MV = const(3300) # battery is empty here
MIN_DROP_MV = const(5) # average drop per interval below this = "unknown"

class Battery:
    """Class for battery information and management."""
    def __init__(self, interval_ms: int = 5 * 60 * 1000):
        """Initialize the battery interface for the current board."""
        self._last_voltage = 0
        self._drop_avg = 0       # EMA of mV drop per interval, scaled x16
        self._minutes = 0
        self._interval_s = interval_ms // 1000
        if BOARD_ID == BOARD_FLIPPER_ZERO:
            from flipper_battery import init 

            init()
        elif BOARD_ID in (BOARD_WAVESHARE_2_06, BOARD_WAVESHARE_C6_2_06):
            from cardputer_battery import init

            init()
        elif BOARD_ID in (
            BOARD_WAVESHARE_1_28_RP2350, BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_1_69_RP2350, BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_battery import init

            init()
        elif BOARD_ID == BOARD_CROWPANEL_WATCH_2_01:
            from crowpanel_watch_battery import init

            init()

    def __del__(self):
        """Destructor to clean up resources."""
        if BOARD_ID == BOARD_FLIPPER_ZERO:
            from flipper_battery import deinit 
            deinit()
        elif BOARD_ID == BOARD_CROWPANEL_WATCH_2_01:
            from crowpanel_watch_battery import deinit

            deinit()

    @property
    def has_voltage(self) -> bool:
        """Returns True if the battery voltage can be read, False otherwise."""
        return BOARD_ID in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_1_69_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
            BOARD_CARDPUTER,
            BOARD_WAVESHARE_2_06,
            BOARD_WAVESHARE_C6_2_06,
            BOARD_CROWPANEL_WATCH_2_01,
            BOARD_PANCAKE,
            BOARD_WAVESHARE_C5_3_5,
            BOARD_V8,
            BOARD_FLIPPER_ZERO
        )
    
    @property
    def percentage(self) -> int:
        """Returns the current battery level as a percentage (0-100)."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_1_69_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_battery import get_percentage

            return get_percentage()

        if BOARD_ID in (BOARD_CROWPANEL_10_1, BOARD_PICO_DUO, BOARD_POOM):
            return 100

        if BOARD_ID in (
            BOARD_CARDPUTER,
            BOARD_WAVESHARE_2_06,
            BOARD_WAVESHARE_C6_2_06,
        ):
            from cardputer_battery import get_percentage

            return get_percentage()

        if BOARD_ID == BOARD_CROWPANEL_WATCH_2_01:
            from crowpanel_watch_battery import get_percentage

            return get_percentage()

        if BOARD_ID == BOARD_PANCAKE:
            from pancake_battery import get_percentage

            return get_percentage()

        if BOARD_ID == BOARD_WAVESHARE_C5_3_5:
            from ws_c5_35_battery import get_percentage

            return get_percentage()

        if BOARD_ID == BOARD_V8:
            from v8_battery import get_percentage

            return get_percentage()

        if BOARD_ID == BOARD_FLIPPER_ZERO:
            from flipper_battery import get_percentage

            return get_percentage()

        from picoware_southbridge import get_battery_percentage

        return get_battery_percentage()


    @property
    def time_remaining(self) -> int:
        """Estimated minutes remaining (0 = unknown)."""
        return self._minutes

    @property
    def voltage(self) -> int:
        """Returns the current battery voltage in millivolts."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_1_69_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_battery import get_voltage

            return int(get_voltage() * 1000)

        if BOARD_ID in (
            BOARD_CARDPUTER,
            BOARD_WAVESHARE_2_06,
            BOARD_WAVESHARE_C6_2_06,
        ):
            from cardputer_battery import get_voltage

            return int(get_voltage() * 1000)

        if BOARD_ID == BOARD_CROWPANEL_WATCH_2_01:
            from crowpanel_watch_battery import get_voltage

            return int(get_voltage() * 1000)

        if BOARD_ID == BOARD_PANCAKE:
            from pancake_battery import get_voltage

            return int(get_voltage() * 1000)

        if BOARD_ID == BOARD_WAVESHARE_C5_3_5:
            from ws_c5_35_battery import get_voltage

            return int(get_voltage() * 1000)

        if BOARD_ID == BOARD_V8:
            from v8_battery import get_voltage

            return int(get_voltage() * 1000)

        if BOARD_ID == BOARD_FLIPPER_ZERO:
            from flipper_battery import get_voltage_mv

            return get_voltage_mv()

        return 4200
    
    def sample(self):
        """Call once per interval from ViewManager."""
        last = self._last_voltage
        self._last_voltage = self.voltage
        if last <= 0:
            return
        drop = last - self._last_voltage
        if drop <= 0:  # charging or flat: discard history
            self._drop_avg = 0
            self._minutes = 0
            return
        avg = self._drop_avg
        if avg == 0:
            avg = drop << 4
        else:
            avg += ((drop << 4) - avg) >> 2   # alpha = 1/4
        self._drop_avg = avg

        usable = self._last_voltage - CUTOFF_MV
        if usable <= 0 or avg < (MIN_DROP_MV << 4):
            self._minutes = 0
            return
        intervals = (usable << 4) // avg
        self._minutes = intervals * self._interval_s // 60