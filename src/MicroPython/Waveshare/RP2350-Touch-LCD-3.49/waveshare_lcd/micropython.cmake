# Create a C module for Waveshare LCD extension
add_library(usermod_waveshare_lcd INTERFACE)

# Generate PIO header from .pio file
pico_generate_pio_header(usermod_waveshare_lcd ${CMAKE_CURRENT_LIST_DIR}/qspi.pio)

target_sources(usermod_waveshare_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/qspi_pio.c
    ${CMAKE_CURRENT_LIST_DIR}/lcd.c
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd.c
    ${CMAKE_CURRENT_LIST_DIR}/font8.c
    ${CMAKE_CURRENT_LIST_DIR}/font12.c
    ${CMAKE_CURRENT_LIST_DIR}/font16.c
    ${CMAKE_CURRENT_LIST_DIR}/font20.c
    ${CMAKE_CURRENT_LIST_DIR}/font24.c
)

target_include_directories(usermod_waveshare_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_compile_definitions(usermod_waveshare_lcd INTERFACE
    MODULE_WAVESHARE_LCD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_waveshare_lcd)

# Link required Pico SDK libraries
target_link_libraries(usermod_waveshare_lcd INTERFACE
    pico_stdlib
    pico_printf
    pico_float
    hardware_gpio
    hardware_spi
    hardware_pwm
    hardware_pio
    hardware_dma
)
