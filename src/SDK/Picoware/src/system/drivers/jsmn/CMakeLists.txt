file(GLOB JSMN_SOURCES "*.c" "*.cpp")
add_library(jsmn ${JSMN_SOURCES})

target_link_libraries(jsmn
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio    
        hardware_clocks
)