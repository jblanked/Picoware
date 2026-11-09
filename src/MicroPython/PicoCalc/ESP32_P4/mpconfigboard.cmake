set(IDF_TARGET esp32p4)

set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    boards/sdkconfig.p4
    boards/PICOCALC_ESP32_P4/sdkconfig.defaults
)

list(APPEND EXTRA_COMPONENT_DIRS
    "${CMAKE_CURRENT_LIST_DIR}/components/picoware_p4_kconfig"
)
list(APPEND IDF_COMPONENTS picoware_p4_kconfig)
