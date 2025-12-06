add_subdirectory(jsmn)
add_subdirectory(rp2040-psram)


file(GLOB DRIVER_SOURCES "*.c" "*.cpp")
add_library(drivers ${DRIVER_SOURCES})

# Generate PIO header from .pio file for LCD
pico_generate_pio_header(drivers
    ${CMAKE_CURRENT_LIST_DIR}/st7789_lcd.pio
)

target_link_libraries(drivers
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio
        hardware_clocks
        hardware_dma
        hardware_exception
        hardware_pio
        pico_multicore
        rp2040-psram
        jsmn
)