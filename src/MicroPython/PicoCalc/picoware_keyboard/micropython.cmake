# Create a C module for Picoware Keyboard extension
add_library(usermod_picoware_keyboard INTERFACE)

target_sources(usermod_picoware_keyboard INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_keyboard.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_southbridge.c
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
