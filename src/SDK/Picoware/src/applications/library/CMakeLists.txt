file(GLOB LIBRARY_SOURCES "*.c" "*.cpp")
add_library(library ${LIBRARY_SOURCES})

target_link_libraries(library
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio    
        hardware_clocks
)