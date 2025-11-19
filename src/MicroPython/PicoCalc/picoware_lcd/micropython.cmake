# Create a C module for Picoware LCD extension
add_library(usermod_picoware_lcd INTERFACE)

target_sources(usermod_picoware_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_lcd.c
    ${CMAKE_CURRENT_LIST_DIR}/lcd.c
)

target_include_directories(usermod_picoware_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_compile_definitions(usermod_picoware_lcd INTERFACE
    MODULE_PICOWARE_LCD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_lcd)
