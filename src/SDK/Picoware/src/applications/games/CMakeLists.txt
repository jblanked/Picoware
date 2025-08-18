file(GLOB_RECURSE GAMES_SOURCES "*.c" "*.cpp")
add_library(games ${GAMES_SOURCES})

target_link_libraries(games
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio    
        hardware_clocks
)