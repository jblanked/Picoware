# CrowPanel 10.1 ESP32-P4-WIFI6 variant configuration
# ESP-Hosted WiFi/BT via external ESP32-C6

set(IDF_TARGET esp32p4)

set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    boards/sdkconfig.p4
    boards/sdkconfig.p4_wifi_common
    boards/sdkconfig.p4_wifi_c6
    boards/ESP32_GENERIC_P4/sdkconfig.defaults
)

# Allow multiple definitions for FatFS - MicroPython's oofatfs and ESP-IDF's fatfs
# both define the same symbols. MicroPython's version will be used (linked first).
list(APPEND MICROPY_LINK_FLAGS
    "-Wl,--allow-multiple-definition"
)

list(APPEND MICROPY_DEF_BOARD
    MICROPY_HW_BOARD_NAME="CrowPanel 10.1 ESP32-P4-WIFI6"
    MICROPY_PY_NETWORK_WLAN=1
    MICROPY_PY_BLUETOOTH=1
    # ESP-NOW requires native WiFi hardware, not available with ESP-Hosted
    MICROPY_PY_ESPNOW=0
)
