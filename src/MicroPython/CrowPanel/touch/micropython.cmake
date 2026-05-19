# Add the touch C module

add_library(usermod_touch INTERFACE)

target_sources(usermod_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/touch_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/touch.c
)

target_include_directories(usermod_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod_touch INTERFACE
    idf::espressif__esp_lcd_touch
    idf::espressif__esp_lcd_touch_gt911
    idf::esp_driver_i2c
)

target_link_libraries(usermod INTERFACE usermod_touch)
