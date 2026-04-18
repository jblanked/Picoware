# Combined Picoware Modules for MicroPython
# This file includes picoware_lcd, picoware_psram, romram, and other modules

# Define PICOCALC for all modules compiled via this file
add_compile_definitions(PICOCALC)

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
    ${CMAKE_CURRENT_LIST_DIR}/../picoware_boards/picoware_boards.c
)

target_include_directories(usermod_picoware_boards INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../picoware_boards
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
    ${CMAKE_CURRENT_LIST_DIR}/picoware_psram/psram_template.cpp
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

# Include sd module
add_library(usermod_sd INTERFACE)

target_sources(usermod_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../sd/fat32.c
    ${CMAKE_CURRENT_LIST_DIR}/../sd/sd_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/../sd/sdcard.c
    ${CMAKE_CURRENT_LIST_DIR}/../sd/vfs_mp.c
)

target_include_directories(usermod_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../sd
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
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl/picoware_lvgl_alert.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl/picoware_lvgl_choice.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl/picoware_lvgl_list.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl/picoware_lvgl_loading.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl/picoware_lvgl_textbox.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lvgl/picoware_lvgl_toggle.c
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


# Include lcd module
add_library(usermod_lcd INTERFACE)

target_sources(usermod_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../lcd/lcd_mp.c
)

target_include_directories(usermod_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../lcd
)

target_link_libraries(usermod INTERFACE usermod_lcd)

# Include jpeg module
add_library(usermod_jpeg INTERFACE)

target_sources(usermod_jpeg INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../jpeg/jpegdec_mp.c
)

target_include_directories(usermod_jpeg INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../jpeg
)

target_link_libraries(usermod INTERFACE usermod_jpeg) 

# Include vt module
add_library(usermod_vt INTERFACE)

target_sources(usermod_vt INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../vt/vt_mp.c
)

target_include_directories(usermod_vt INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../vt
)

target_link_libraries(usermod INTERFACE usermod_vt) 

# Include engine module
add_library(usermod_engine INTERFACE)

target_sources(usermod_engine INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../engine/camera_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/engine_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/entity_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/game_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/image_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/level_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/sprite3d_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/triangle3d_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/pico-game-engine/engine/draw.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/pico-game-engine/engine/entity.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/pico-game-engine/engine/game.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/pico-game-engine/engine/image.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/pico-game-engine/engine/level.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/pico-game-engine/engine/sprite3d.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/pico-game-engine/engine/triangle3d.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../engine/pico-game-engine/engine/vector.cpp
)

target_include_directories(usermod_engine INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../engine
)

target_link_libraries(usermod INTERFACE usermod_engine) 


# Include log module
add_library(usermod_log INTERFACE)

target_sources(usermod_log INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../log/log_mp.c
)

target_include_directories(usermod_log INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../log
)

target_link_libraries(usermod INTERFACE usermod_log) 


# Include textbox module
add_library(usermod_textbox INTERFACE)

target_sources(usermod_textbox INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../textbox/textbox_mp.c
)

target_include_directories(usermod_textbox INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../textbox
)

target_link_libraries(usermod INTERFACE usermod_textbox) 


# Include gameboy module
add_library(usermod_gameboy INTERFACE)

target_sources(usermod_gameboy INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/buffer.c
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/flash.c
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/gameboy_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/lcd.c
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/storage.c
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/PicoCalc-GameBoy/src/gb.c
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/PicoCalc-GameBoy/src/rom.c
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/PicoCalc-GameBoy/src/state.c
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/PicoCalc-GameBoy/src/ram_cart.c
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/PicoCalc-GameBoy/src/audio.c
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/PicoCalc-GameBoy/ext/minigb_apu/minigb_apu.c
)

target_include_directories(usermod_gameboy INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/PicoCalc-GameBoy/src
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/PicoCalc-GameBoy/ext/minigb_apu
    ${CMAKE_CURRENT_LIST_DIR}/../gameboy/PicoCalc-GameBoy/ext/Walnut-CGB
)

target_link_libraries(usermod INTERFACE usermod_gameboy) 

# Include audio module
add_library(usermod_audio INTERFACE)

target_sources(usermod_audio INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../audio/audio_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/../audio/audio.c
)

target_include_directories(usermod_audio INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../audio
)

target_link_libraries(usermod INTERFACE usermod_audio) 


# Include uf2loader module
add_library(usermod_uf2loader INTERFACE)
target_sources(usermod_uf2loader INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../uf2loader/uf2loader_mp.c
)
target_include_directories(usermod_uf2loader INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../uf2loader
)
target_link_libraries(usermod_uf2loader INTERFACE
    hardware_flash
    hardware_watchdog
    hardware_sync
)
target_link_libraries(usermod INTERFACE usermod_uf2loader)


# Include ghouls module
add_library(usermod_ghouls INTERFACE)

target_sources(usermod_ghouls INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/ghouls_mp.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/animation.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/dynamic_map.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/enemy.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/game.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/loading.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/player.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/projectile.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/sky.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/sound.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/time.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/weapon.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/pico-game-engine/engine/draw.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/pico-game-engine/engine/entity.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/pico-game-engine/engine/game.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/pico-game-engine/engine/image.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/pico-game-engine/engine/level.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/pico-game-engine/engine/sprite3d.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/pico-game-engine/engine/triangle3d.cpp
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/pico-game-engine/engine/vector.cpp
)

target_include_directories(usermod_ghouls INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/pico-game-engine
    ${CMAKE_CURRENT_LIST_DIR}/../ghouls/Ghouls/src/pico-game-engine/engine
)

target_link_libraries(usermod INTERFACE usermod_ghouls) 

# Include jsmn module
add_library(usermod_jsmn INTERFACE)

target_sources(usermod_jsmn INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../jsmn/jsmn_h.c
    ${CMAKE_CURRENT_LIST_DIR}/../jsmn/jsmn.c
    ${CMAKE_CURRENT_LIST_DIR}/../jsmn/jsmn_mp.c
)

target_include_directories(usermod_jsmn INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../jsmn
)

target_link_libraries(usermod INTERFACE usermod_jsmn) 

# Include http module
add_library(usermod_http INTERFACE)

target_sources(usermod_http INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../http/http_mp.c
)

target_include_directories(usermod_http INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../http
)

target_link_libraries(usermod INTERFACE usermod_http) 

# Include websocket module
add_library(usermod_websocket INTERFACE)

target_sources(usermod_websocket INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../websocket/websocket_mp.c
)

target_include_directories(usermod_websocket INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/../websocket
)

target_link_libraries(usermod INTERFACE usermod_websocket) 