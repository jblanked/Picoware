# Combined Waveshare Modules for MicroPython

# Define WAVESHARE_3_49 for all modules compiled via this file
add_compile_definitions(WAVESHARE_3_49)

# Include waveshare_lcd module
add_library(usermod_waveshare_lcd INTERFACE)

# Generate PIO header from .pio file
# pico_generate_pio_header(usermod_waveshare_lcd
#     ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd/qspi.pio
# )

target_sources(usermod_waveshare_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd/qspi_pio.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd/lcd.c
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
    ${CMAKE_CURRENT_LIST_DIR}/../../picoware_boards/picoware_boards.c
)

target_include_directories(usermod_picoware_boards INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../picoware_boards
)

target_link_libraries(usermod INTERFACE usermod_picoware_boards)

# link against the required Pico SDK libraries for board management
target_link_libraries(usermod_picoware_boards INTERFACE
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

# Include sd module
add_library(usermod_sd INTERFACE)

target_sources(usermod_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../sd/fat32.c
    ${CMAKE_CURRENT_LIST_DIR}/../../sd/sd_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/../../sd/sdcard.c
    ${CMAKE_CURRENT_LIST_DIR}/../../sd/vfs_mp.c
)

target_include_directories(usermod_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../sd
)

target_link_libraries(usermod INTERFACE usermod_sd)

# Link against the required Pico SDK libraries for SD card
target_link_libraries(usermod_sd INTERFACE
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


# Include vector module
add_library(usermod_vector INTERFACE)

target_sources(usermod_vector INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../vector/vector_mp.c
)

target_include_directories(usermod_vector INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../vector
)

target_link_libraries(usermod INTERFACE usermod_vector)


# Include response module
add_library(usermod_response INTERFACE)

target_sources(usermod_response INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../response/response_mp.c
)

target_include_directories(usermod_response INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../response
)

target_link_libraries(usermod INTERFACE usermod_response)

# Include font module
add_library(usermod_font INTERFACE)

target_sources(usermod_font INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../font/font_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/../../font/font8.c
    ${CMAKE_CURRENT_LIST_DIR}/../../font/font12.c
    ${CMAKE_CURRENT_LIST_DIR}/../../font/font16.c
    ${CMAKE_CURRENT_LIST_DIR}/../../font/font20.c
    ${CMAKE_CURRENT_LIST_DIR}/../../font/font24.c
)

target_include_directories(usermod_font INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../font
)

target_link_libraries(usermod INTERFACE usermod_font)

# Include lcd module
add_library(usermod_lcd INTERFACE)

target_sources(usermod_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../lcd/lcd_mp.c
)

target_include_directories(usermod_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../lcd
)

target_link_libraries(usermod INTERFACE usermod_lcd)


# Include jpeg module
add_library(usermod_jpeg INTERFACE)

target_sources(usermod_jpeg INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../jpeg/jpegdec_mp.c
)

target_include_directories(usermod_jpeg INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../jpeg
)

target_link_libraries(usermod INTERFACE usermod_jpeg)


# Include vt module
add_library(usermod_vt INTERFACE)

target_sources(usermod_vt INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../vt/vt_mp.c
)

target_include_directories(usermod_vt INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../vt
)

target_link_libraries(usermod INTERFACE usermod_vt)

# Include engine module
add_library(usermod_engine INTERFACE)

target_sources(usermod_engine INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/camera_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/engine_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/entity_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/game_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/image_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/level_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/sprite3d_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/triangle3d_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/pico-game-engine/engine/draw.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/pico-game-engine/engine/entity.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/pico-game-engine/engine/game.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/pico-game-engine/engine/image.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/pico-game-engine/engine/level.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/pico-game-engine/engine/sprite3d.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/pico-game-engine/engine/triangle3d.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../../engine/pico-game-engine/engine/vector.cpp
)

target_include_directories(usermod_engine INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../engine
)

target_link_libraries(usermod INTERFACE usermod_engine)


# Include log module
add_library(usermod_log INTERFACE)

target_sources(usermod_log INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../log/log_mp.c
)

target_include_directories(usermod_log INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../log
)

target_link_libraries(usermod INTERFACE usermod_log)


# Include textbox module
add_library(usermod_textbox INTERFACE)

target_sources(usermod_textbox INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../textbox/textbox_mp.c
)

target_include_directories(usermod_textbox INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../textbox
)

target_link_libraries(usermod INTERFACE usermod_textbox)


# Include uf2loader module
add_library(usermod_uf2loader INTERFACE)
target_sources(usermod_uf2loader INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../uf2loader/uf2loader_mp.c
)
target_include_directories(usermod_uf2loader INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../../uf2loader
)
target_link_libraries(usermod_uf2loader INTERFACE
    hardware_flash
    hardware_watchdog
    hardware_sync
)
target_link_libraries(usermod INTERFACE usermod_uf2loader)