add_subdirectory(drivers)

file(GLOB SYSTEM_SOURCES "*.c" "*.cpp")

# Add UF2 loader source files explicitly
list(APPEND SYSTEM_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/uf2_loader.cpp")

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
    target_link_libraries(system 
    pico_cyw43_arch_lwip_threadsafe_background 
    pico_stdlib 
    pico_lwip_mbedtls
    pico_mbedtls
    )
    target_include_directories(system PRIVATE
        ${CMAKE_CURRENT_LIST_DIR}
        ${CMAKE_CURRENT_LIST_DIR}/../.. # for our common lwipopts
        )
    # Add lwIP HTTP client source
    target_sources(system PRIVATE ${PICO_SDK_PATH}/lib/lwip/src/apps/http/http_client.c)
    
    # Exclude problematic TLS files that have compatibility issues
    set_property(SOURCE ${PICO_SDK_PATH}/src/rp2_common/pico_lwip/altcp_tls_mbedtls.c PROPERTY COMPILE_FLAGS "-DSKIP_COMPILATION")
endif()