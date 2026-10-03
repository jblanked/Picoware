# Add the lcd C module

add_library(usermod_lcd_mp INTERFACE)

target_sources(usermod_lcd_mp INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/lcd_mp.c
)

target_include_directories(usermod_lcd_mp INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_lcd_mp)
