# Include picoware_lcd module
add_library(usermod_picoware_lcd INTERFACE)

target_sources(usermod_picoware_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lcd.c
)

if(PICOCALC_ESP32_P4)
    target_sources(usermod_picoware_lcd INTERFACE
        ${CMAKE_CURRENT_LIST_DIR}/lcd_esp32.c
        ${CMAKE_CURRENT_LIST_DIR}/../ESP32_P4/picocalc_spi_bus.c
    )
    target_include_directories(usermod_picoware_lcd INTERFACE
        ${CMAKE_CURRENT_LIST_DIR}/../ESP32_P4
    )
    target_link_libraries(usermod_picoware_lcd INTERFACE
        idf::esp_driver_gpio
        idf::esp_driver_spi
        idf::esp_rom
        idf::hal
        idf::log
        idf::soc
    )
else()
    target_sources(usermod_picoware_lcd INTERFACE
        ${CMAKE_CURRENT_LIST_DIR}/lcd.c
    )
endif()

target_include_directories(usermod_picoware_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_BINARY_DIR}
)

target_compile_definitions(usermod_picoware_lcd INTERFACE
    MODULE_PICOWARE_LCD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_lcd)