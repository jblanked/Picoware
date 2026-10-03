include(boards/mpconfigboard_esp32s3_common.cmake)

list(APPEND SDKCONFIG_DEFAULTS
    boards/sdkconfig.flash_qio_80m
    boards/sdkconfig.240mhz
    boards/sdkconfig.spiram_oct
    boards/PICOWARE_CROWPANEL_WATCH_2_01/sdkconfig.defaults
)

list(APPEND MICROPY_DEF_BOARD
    MICROPY_HW_BOARD_NAME="Elecrow CrowPanel Watch 2.01"
)
