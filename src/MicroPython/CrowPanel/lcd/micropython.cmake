# Add the LCD C module

add_library(usermod_lcd INTERFACE)

target_sources(usermod_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/lcd_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/lcd.c
)

target_include_directories(usermod_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod_lcd INTERFACE
    idf::esp_lcd
    idf::espressif__esp_lcd_ek79007
    idf::esp_driver_gpio
    idf::esp_driver_ledc
    idf::esp_hw_support
)

target_link_libraries(usermod INTERFACE usermod_lcd)
