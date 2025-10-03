# Combined Picoware Modules for MicroPython
# This file includes both picoware_lcd and picoware_psram modules

# Include picoware_lcd module
add_library(usermod_picoware_lcd INTERFACE)

target_sources(usermod_picoware_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lcd/picoware_lcd.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lcd/lcd.c
)

target_include_directories(usermod_picoware_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lcd
)

target_compile_definitions(usermod_picoware_lcd INTERFACE
    MODULE_PICOWARE_LCD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_lcd)

# Link against the required Pico SDK libraries for LCD
target_link_libraries(usermod_picoware_lcd INTERFACE
    pico_stdlib
    hardware_spi
    hardware_gpio
)

# Include picoware_psram module
add_library(usermod_picoware_psram INTERFACE)

# Generate PIO header from .pio file
pico_generate_pio_header(usermod_picoware_psram
    ${CMAKE_CURRENT_LIST_DIR}/picoware_psram/psram_spi.pio
)

target_sources(usermod_picoware_psram INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_psram/picoware_psram.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_psram/psram_spi.c
)

target_include_directories(usermod_picoware_psram INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_psram
)

target_compile_definitions(usermod_picoware_psram INTERFACE
    MODULE_PICOWARE_PSRAM_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_psram)

# Link against the required Pico SDK libraries for PSRAM
target_link_libraries(usermod_picoware_psram INTERFACE
    pico_stdlib
    hardware_pio
    hardware_dma
    hardware_gpio
)
