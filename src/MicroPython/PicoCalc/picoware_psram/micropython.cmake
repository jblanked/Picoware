# Picoware PSRAM MicroPython Module
# QSPI implementation for high-speed memory access

# Create interface library for module
add_library(usermod_picoware_psram INTERFACE)

# Add source files
target_sources(usermod_picoware_psram INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_psram.c
    ${CMAKE_CURRENT_LIST_DIR}/psram_qspi.c
)

# Generate PIO header from PIO assembly file
pico_generate_pio_header(usermod_picoware_psram ${CMAKE_CURRENT_LIST_DIR}/psram_qspi.pio)

target_include_directories(usermod_picoware_psram INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_BINARY_DIR}
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
