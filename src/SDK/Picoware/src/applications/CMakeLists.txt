add_subdirectory(desktop)
add_subdirectory(library)
add_subdirectory(screensavers)
add_subdirectory(system)

file(GLOB APPLICATION_SOURCES "*.c" "*.cpp")
add_library(applications ${APPLICATION_SOURCES})

target_link_libraries(applications
        library
        desktop
        screensavers
        systemApp
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio    
        hardware_clocks
)