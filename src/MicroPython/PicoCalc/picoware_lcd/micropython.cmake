# Create a C module for Picoware LCD extension
add_library(usermod_picoware_lcd INTERFACE)

# Generate PIO header for ST7789 LCD
pico_generate_pio_header(usermod_st7789_lcd_pio ${CMAKE_CURRENT_LIST_DIR}/st7789_lcd.pio)

target_sources(usermod_picoware_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lcd.c
    ${CMAKE_CURRENT_LIST_DIR}/lcd.c
)

target_include_directories(usermod_picoware_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_BINARY_DIR}
)

target_compile_definitions(usermod_picoware_lcd INTERFACE
    MODULE_PICOWARE_LCD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_lcd)
