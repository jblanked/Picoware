# Create a C module for Picoware PSRAM extension
add_library(usermod_picoware_psram INTERFACE)

target_sources(usermod_picoware_psram INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_psram.c
    ${CMAKE_CURRENT_LIST_DIR}/psram_spi.c
)

target_include_directories(usermod_picoware_psram INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_compile_definitions(usermod_picoware_psram INTERFACE
    MODULE_PICOWARE_PSRAM_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_psram)

# Link against the required Pico SDK libraries
target_link_libraries(usermod_picoware_psram INTERFACE
    pico_stdlib
    hardware_pio
    hardware_dma
    hardware_gpio
)
