set(IDF_TARGET esp32p4)

set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    boards/sdkconfig.p4
    boards/sdkconfig.p4_wifi_common
    boards/sdkconfig.p4_wifi_c6
    boards/PICOCALC_ESP32_P4/sdkconfig.defaults
)

list(APPEND MICROPY_LINK_FLAGS
    "-Wl,--allow-multiple-definition"
)

list(APPEND MICROPY_DEF_BOARD
    MICROPY_HW_BOARD_NAME="Picoware PicoCalc ESP32-P4-WIFI6"
    MICROPY_PY_NETWORK_WLAN=1
    MICROPY_PY_BLUETOOTH=1
    MICROPY_PY_ESPNOW=0
)
