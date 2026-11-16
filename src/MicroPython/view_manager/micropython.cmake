add_library(usermod_view_manager INTERFACE)

target_sources(usermod_view_manager INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/view_manager_mp.c
)

target_include_directories(usermod_view_manager INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_view_manager)