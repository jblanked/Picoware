file(GLOB DESKTOP_SOURCES "*.c" "*.cpp")
add_library(desktop ${DESKTOP_SOURCES})

target_link_libraries(desktop
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio    
        hardware_clocks
)