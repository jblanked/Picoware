file(GLOB SCREENSAVERS_SOURCES "*.c" "*.cpp")
add_library(screensavers ${SCREENSAVERS_SOURCES})

target_link_libraries(screensavers
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio    
        hardware_clocks
)