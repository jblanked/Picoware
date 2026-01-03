# Combined Waveshare Modules for MicroPython

# Include waveshare_lcd module
add_library(usermod_waveshare_lcd INTERFACE)

# Generate PIO header from .pio file
pico_generate_pio_header(usermod_waveshare_lcd
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd/qspi.pio
)

target_sources(usermod_waveshare_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd/qspi_pio.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd/lcd.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd/waveshare_lcd.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd/font8.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd/font12.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd/font16.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd/font20.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd/font24.c
)

target_include_directories(usermod_waveshare_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd
)

target_compile_definitions(usermod_waveshare_lcd INTERFACE
    MODULE_WAVESHARE_LCD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_waveshare_lcd)

# Link against the required Pico SDK libraries for LCD
target_link_libraries(usermod_waveshare_lcd INTERFACE
    pico_stdlib
    pico_printf
    pico_float
    hardware_gpio
    hardware_spi
    hardware_pwm
    hardware_pio
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

# Include picoware_game module (fast raycasting and 3D rendering)
add_library(usermod_picoware_game INTERFACE)

target_sources(usermod_picoware_game INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_game/picoware_game.c
)

target_include_directories(usermod_picoware_game INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_game
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd
)

target_compile_definitions(usermod_picoware_game INTERFACE
    MODULE_PICOWARE_GAME_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_game)

# Link against the required Pico SDK libraries for picoware_game
target_link_libraries(usermod_picoware_game INTERFACE
    pico_stdlib
)


# Include waveshare_battery module
add_library(usermod_waveshare_battery INTERFACE)

target_sources(usermod_waveshare_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_battery/waveshare_battery.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_battery/battery.c
)

target_include_directories(usermod_waveshare_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_battery
)

target_compile_definitions(usermod_waveshare_battery INTERFACE
    MODULE_WAVESHARE_BATTERY_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_waveshare_battery)

# Link against the required Pico SDK libraries for battery
target_link_libraries(usermod_waveshare_battery INTERFACE
    pico_stdlib
    pico_printf
    pico_float
    hardware_gpio
    hardware_spi
    hardware_adc
)

# Include waveshare_touch module
add_library(usermod_waveshare_touch INTERFACE)

target_sources(usermod_waveshare_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_touch/waveshare_touch.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_touch/touch.c
)

target_include_directories(usermod_waveshare_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_touch
)

target_compile_definitions(usermod_waveshare_touch INTERFACE
    MODULE_WAVESHARE_TOUCH_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_waveshare_touch)

# Link against the required Pico SDK libraries for touch
target_link_libraries(usermod_waveshare_touch INTERFACE
    pico_stdlib
    pico_printf
    pico_float
    hardware_gpio
    hardware_i2c
)

# Include waveshare_sd module
add_library(usermod_waveshare_sd INTERFACE)

target_sources(usermod_waveshare_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_sd/waveshare_sd.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_sd/waveshare_vfs.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_sd/sdcard.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_sd/fat32.c
)

target_include_directories(usermod_waveshare_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_sd
)

target_compile_definitions(usermod_waveshare_sd INTERFACE
    MODULE_WAVESHARE_SD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_waveshare_sd)

# Link against the required Pico SDK libraries for SD card
target_link_libraries(usermod_waveshare_sd INTERFACE
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
    ${CMAKE_CURRENT_LIST_DIR}/../../auto_complete/auto_complete.c
    ${CMAKE_CURRENT_LIST_DIR}/../../auto_complete/auto_complete_mp.c
)

target_include_directories(usermod_auto_complete INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../auto_complete
)

target_link_libraries(usermod INTERFACE usermod_auto_complete)