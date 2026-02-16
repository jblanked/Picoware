# Add the font C module

add_library(usermod_font INTERFACE)

target_sources(usermod_font INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/font_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/font8.c
    ${CMAKE_CURRENT_LIST_DIR}/font12.c
    ${CMAKE_CURRENT_LIST_DIR}/font16.c
    ${CMAKE_CURRENT_LIST_DIR}/font20.c
    ${CMAKE_CURRENT_LIST_DIR}/font24.c
)

target_include_directories(usermod_font INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_font)
