add_library(usermod_lcd INTERFACE)

target_sources(usermod_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/lcd.c
)

target_include_directories(usermod_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
    ${CMAKE_CURRENT_LIST_DIR}/../../lcd
)

target_compile_definitions(usermod_lcd INTERFACE
    FLIPPER_ZERO
)

target_link_libraries(usermod INTERFACE usermod_lcd)
