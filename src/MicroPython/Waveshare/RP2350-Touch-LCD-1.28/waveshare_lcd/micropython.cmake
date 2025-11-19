# Create a C module for Waveshare LCD extension
add_library(usermod_waveshare_lcd INTERFACE)

target_sources(usermod_waveshare_lcd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd.c
    ${CMAKE_CURRENT_LIST_DIR}/lcd.c
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
