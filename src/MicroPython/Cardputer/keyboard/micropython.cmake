# Add the keyboard C module for Cardputer.

add_library(usermod_cardputer_keyboard INTERFACE)

target_sources(usermod_cardputer_keyboard INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/keyboard.c
    ${CMAKE_CURRENT_LIST_DIR}/keyboard_mp.c
)

target_include_directories(usermod_cardputer_keyboard INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_compile_definitions(usermod_cardputer_keyboard INTERFACE
    MODULE_PICOWARE_KEYBOARD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_cardputer_keyboard)
