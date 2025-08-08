add_subdirectory(drivers)

file(GLOB SYSTEM_SOURCES "*.c" "*.cpp")
add_library(system ${SYSTEM_SOURCES})

target_link_libraries(system
        drivers 
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio
        hardware_clocks
)