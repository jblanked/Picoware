file(GLOB DRIVER_SOURCES "*.c" "*.cpp")
add_library(drivers ${DRIVER_SOURCES})

target_link_libraries(drivers
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio
        hardware_clocks
)