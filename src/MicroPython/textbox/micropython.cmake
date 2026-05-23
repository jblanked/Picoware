# Add the textbox C module

add_library(usermod_textbox INTERFACE)

target_sources(usermod_textbox INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/textbox_mp.c
)

target_include_directories(usermod_textbox INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_textbox)
