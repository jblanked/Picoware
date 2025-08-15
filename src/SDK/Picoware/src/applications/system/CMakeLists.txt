file(GLOB SYSTEM_APP_SOURCES "*.c" "*.cpp")
add_library(systemApp ${SYSTEM_APP_SOURCES})

target_link_libraries(systemApp
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio    
        hardware_clocks
)