file(GLOB GUI_SOURCES "*.c" "*.cpp")
add_library(gui ${GUI_SOURCES})

target_link_libraries(gui
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio    
        hardware_clocks
        hardware_dma
)