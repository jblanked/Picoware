# Picoware PSRAM MicroPython Module
# QSPI implementation for high-speed memory access

# Create interface library for module
add_library(usermod_picoware_psram INTERFACE)

# Add source files
target_sources(usermod_picoware_psram INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_psram.c
)

if(PICOCALC_ESP32_P4)
    target_sources(usermod_picoware_psram INTERFACE
        ${CMAKE_CURRENT_LIST_DIR}/psram_qspi_esp32.c
    )
    target_include_directories(usermod_picoware_psram INTERFACE
        ${CMAKE_CURRENT_LIST_DIR}/../ESP32_P4
    )
    target_link_libraries(usermod_picoware_psram INTERFACE
        idf::esp_driver_spi
        idf::esp_driver_gpio
        idf::esp_rom
        idf::log
    )
else()
    target_sources(usermod_picoware_psram INTERFACE
        ${CMAKE_CURRENT_LIST_DIR}/psram_qspi.c
    )
endif()

target_include_directories(usermod_picoware_psram INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_BINARY_DIR}
)

target_compile_definitions(usermod_picoware_psram INTERFACE
    MODULE_PICOWARE_PSRAM_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_psram)