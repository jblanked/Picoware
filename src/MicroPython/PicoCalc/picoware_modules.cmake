# Combined Picoware Modules for MicroPython
# This file includes picoware_lcd, picoware_psram, romram, and other modules

# Generate PIO header from .pio file for LCD
# pico_generate_pio_header(usermod
#     ${CMAKE_CURRENT_LIST_DIR}/picoware_lcd/st7789_lcd.pio
# )
    
# Include picoware_lcd module
add_library(usermod_picoware_lcd INTERFACE)

target_sources(usermod_picoware_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lcd/picoware_lcd.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lcd/lcd.c
)

target_include_directories(usermod_picoware_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lcd
    ${CMAKE_BINARY_DIR}
)

target_compile_definitions(usermod_picoware_lcd INTERFACE
    MODULE_PICOWARE_LCD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_lcd)

# Link against the required Pico SDK libraries for LCD
target_link_libraries(usermod_picoware_lcd INTERFACE
    pico_stdlib
    hardware_pio
    hardware_gpio
    hardware_clocks
)


# include picoware_boards module
add_library(usermod_picoware_boards INTERFACE)

target_sources(usermod_picoware_boards INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_boards/picoware_boards.c
)

target_include_directories(usermod_picoware_boards INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_boards
)

target_link_libraries(usermod INTERFACE usermod_picoware_boards)

# link against the required Pico SDK libraries for board management
target_link_libraries(usermod_picoware_boards INTERFACE
    pico_stdlib
)


# Include picoware_psram module
add_library(usermod_picoware_psram INTERFACE)

# Generate PIO header from .pio file
pico_generate_pio_header(usermod_picoware_psram
    ${CMAKE_CURRENT_LIST_DIR}/picoware_psram/psram_qspi.pio
)

target_sources(usermod_picoware_psram INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_psram/picoware_psram.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_psram/psram_qspi.c
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


# Include picoware_sd module
add_library(usermod_picoware_sd INTERFACE)

target_sources(usermod_picoware_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_sd/picoware_sd.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_sd/picoware_vfs.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_sd/sdcard.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_sd/fat32.c
)

target_include_directories(usermod_picoware_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_sd
)

target_compile_definitions(usermod_picoware_sd INTERFACE
    MODULE_WAVESHARE_SD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_sd)

# Link against the required Pico SDK libraries for SD card
target_link_libraries(usermod_picoware_sd INTERFACE
    pico_stdlib
    pico_printf
    pico_float
    hardware_gpio
    hardware_i2c
    hardware_spi
    hardware_pio
)


# Include auto_complete module
add_library(usermod_auto_complete INTERFACE)

target_sources(usermod_auto_complete INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../auto_complete/auto_complete.c
    ${CMAKE_CURRENT_LIST_DIR}/../auto_complete/auto_complete_mp.c
)

target_include_directories(usermod_auto_complete INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../auto_complete
)

target_link_libraries(usermod INTERFACE usermod_auto_complete)


# Include picoware_lvgl module
add_library(usermod_picoware_lvgl INTERFACE)

target_sources(usermod_picoware_lvgl INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl/picoware_lvgl.c
)

target_include_directories(usermod_picoware_lvgl INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl/lvgl/
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl/lvgl/src
)

# Add LVGL library as subdirectory
add_subdirectory(${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl/lvgl)

target_link_libraries(usermod_picoware_lvgl INTERFACE lvgl_interface)

target_link_libraries(usermod INTERFACE usermod_picoware_lvgl)


# Include vector module
add_library(usermod_vector INTERFACE)

target_sources(usermod_vector INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../vector/vector_mp.c
)

target_include_directories(usermod_vector INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../vector
)

target_link_libraries(usermod INTERFACE usermod_vector)

# Include response module
add_library(usermod_response INTERFACE)

target_sources(usermod_response INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../response/response_mp.c
)

target_include_directories(usermod_response INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../response
)

target_link_libraries(usermod INTERFACE usermod_response)

# Include font module
add_library(usermod_font INTERFACE)

target_sources(usermod_font INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../font/font_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/../font/font8.c
    ${CMAKE_CURRENT_LIST_DIR}/../font/font12.c
    ${CMAKE_CURRENT_LIST_DIR}/../font/font16.c
    ${CMAKE_CURRENT_LIST_DIR}/../font/font20.c
    ${CMAKE_CURRENT_LIST_DIR}/../font/font24.c
)

target_include_directories(usermod_font INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../font
)

target_link_libraries(usermod INTERFACE usermod_font)

