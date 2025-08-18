file(GLOB ENGINE_SOURCES "*.c" "*.cpp")
add_library(engine ${ENGINE_SOURCES})

target_link_libraries(engine
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio    
        hardware_clocks
        gui
)