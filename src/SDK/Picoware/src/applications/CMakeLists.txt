add_subdirectory(desktop)

file(GLOB APPLICATION_SOURCES "*.c" "*.cpp")
add_library(applications ${APPLICATION_SOURCES})

target_link_libraries(applications
        desktop
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio    
        hardware_clocks
)