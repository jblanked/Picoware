add_subdirectory(drivers)

file(GLOB SYSTEM_SOURCES "*.c" "*.cpp")
add_library(system ${SYSTEM_SOURCES})

target_link_libraries(system
        drivers 
        pico_stdlib
        pico_printf
        pico_float
        pico_bootrom
        hardware_watchdog
        hardware_gpio
        hardware_i2c
        hardware_spi
        hardware_pio
        hardware_clocks
)

if (PICO_CYW43_SUPPORTED)
    target_link_libraries(system pico_cyw43_arch_lwip_threadsafe_background pico_stdlib )
    target_include_directories(system PRIVATE
        ${CMAKE_CURRENT_LIST_DIR}
        ${CMAKE_CURRENT_LIST_DIR}/../.. # for our common lwipopts
        )
endif()