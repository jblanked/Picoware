from picoware.system.boards import (
    BOARD_CARDPUTER,
    BOARD_CROWPANEL_10_1,
    BOARD_ID,
    BOARD_WAVESHARE_1_28_RP2350,
    BOARD_WAVESHARE_1_43_RP2350,
    BOARD_WAVESHARE_1_69_RP2350,
    BOARD_WAVESHARE_3_49_RP2350,
    BOARD_WAVESHARE_2_06,
    BOARD_PANCAKE,
    BOARD_V8,
    BOARD_FLIPPER_ZERO
)


class Battery:
    """Class for battery information and management."""
    def __init__(self):
        if BOARD_ID == BOARD_FLIPPER_ZERO:
            from flipper_battery import init 

            init()

    def __del__(self):
        """Destructor to clean up resources."""
        if BOARD_ID == BOARD_FLIPPER_ZERO:
            from flipper_battery import deinit 
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
            BOARD_PANCAKE,
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

        if BOARD_ID == BOARD_CROWPANEL_10_1:
            return 100

        if BOARD_ID in (
            BOARD_CARDPUTER,
            BOARD_WAVESHARE_2_06,
        ):
            from cardputer_battery import get_percentage

            return get_percentage()

        if BOARD_ID == BOARD_PANCAKE:
            from pancake_battery import get_percentage

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
    def voltage(self) -> float:
        """Returns the current battery voltage in millivolts."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_1_69_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            from waveshare_battery import get_voltage

            return get_voltage()

        if BOARD_ID in (
            BOARD_CARDPUTER,
            BOARD_WAVESHARE_2_06,
        ):
            from cardputer_battery import get_voltage

            return get_voltage()

        if BOARD_ID == BOARD_PANCAKE:
            from pancake_battery import get_voltage

            return get_voltage()

        if BOARD_ID == BOARD_V8:
            from v8_battery import get_voltage

            return get_voltage()

        if BOARD_ID == BOARD_FLIPPER_ZERO:
            from flipper_battery import get_voltage_mv

            return get_voltage_mv()

        return 4200