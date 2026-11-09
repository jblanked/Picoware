# Create a C module for Picoware Keyboard extension
add_library(usermod_picoware_keyboard INTERFACE)

target_sources(usermod_picoware_keyboard INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_keyboard.c
    ${CMAKE_CURRENT_LIST_DIR}/keyboard.c
    ${CMAKE_CURRENT_LIST_DIR}/southbridge.c
)

target_include_directories(usermod_picoware_keyboard INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_compile_definitions(usermod_picoware_keyboard INTERFACE
    MODULE_PICOWARE_KEYBOARD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_keyboard)


# Include picoware_southbridge module (direct southbridge hardware access)
add_library(usermod_picoware_southbridge INTERFACE)

target_sources(usermod_picoware_southbridge INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_southbridge.c
    ${CMAKE_CURRENT_LIST_DIR}/southbridge.c
)

target_include_directories(usermod_picoware_southbridge INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_compile_definitions(usermod_picoware_southbridge INTERFACE
    MODULE_PICOWARE_SOUTHBRIDGE_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_southbridge)

if(PICOCALC_ESP32_P4)
    target_link_libraries(usermod_picoware_keyboard INTERFACE
        idf::esp_driver_i2c
        idf::esp_rom
        idf::log
        idf::esp_timer
    )
    target_link_libraries(usermod_picoware_southbridge INTERFACE
        idf::esp_driver_i2c
        idf::esp_rom
        idf::log
    )
endif()