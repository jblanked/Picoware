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

# Include picoware_southbridge module (direct southbridge hardware access)
add_library(usermod_picoware_southbridge INTERFACE)

target_sources(usermod_picoware_southbridge INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_keyboard/picoware_southbridge.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_keyboard/southbridge.c
)

target_include_directories(usermod_picoware_southbridge INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_keyboard
)

target_compile_definitions(usermod_picoware_southbridge INTERFACE
    MODULE_PICOWARE_SOUTHBRIDGE_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_southbridge)

# Link against the required Pico SDK libraries for southbridge
target_link_libraries(usermod_picoware_southbridge INTERFACE
    pico_stdlib
    hardware_gpio
    hardware_i2c
)

# Include picoware_keyboard module (direct keyboard hardware access)
add_library(usermod_picoware_keyboard INTERFACE)

target_sources(usermod_picoware_keyboard INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_keyboard/picoware_keyboard.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_keyboard/keyboard.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_keyboard/southbridge.c
)

target_include_directories(usermod_picoware_keyboard INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_keyboard
)

target_compile_definitions(usermod_picoware_keyboard INTERFACE
    MODULE_PICOWARE_KEYBOARD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_keyboard)

# Link against the required Pico SDK libraries for keyboard
target_link_libraries(usermod_picoware_keyboard INTERFACE
    pico_stdlib
    hardware_gpio
    hardware_i2c
)

# Include picoware_game module (fast raycasting and 3D rendering)
add_library(usermod_picoware_game INTERFACE)

target_sources(usermod_picoware_game INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_game/picoware_game.c
)

target_include_directories(usermod_picoware_game INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_game
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lcd
)

target_compile_definitions(usermod_picoware_game INTERFACE
    MODULE_PICOWARE_GAME_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_game)

# Link against the required Pico SDK libraries for picoware_game
target_link_libraries(usermod_picoware_game INTERFACE
    pico_stdlib
)
