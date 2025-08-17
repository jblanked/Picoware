add_subdirectory(desktop)
add_subdirectory(games)
add_subdirectory(library)
add_subdirectory(screensavers)
add_subdirectory(system)
add_subdirectory(wifi)

file(GLOB APPLICATION_SOURCES "*.c" "*.cpp")
add_library(applications ${APPLICATION_SOURCES})

target_link_libraries(applications
        library
        desktop
        games
        screensavers
        systemApp
        wifiApp
        pico_stdlib
        pico_printf
        pico_float
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio    
        hardware_clocks
)