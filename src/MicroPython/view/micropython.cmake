add_library(usermod_view INTERFACE)

target_sources(usermod_view INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/view_mp.c
)

target_include_directories(usermod_view INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_view)